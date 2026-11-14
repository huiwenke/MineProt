"""Run with: PYTHONPATH=web python -m unittest discover -s web/tests -v."""
import asyncio
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from mineprot import settings
from mineprot.app import app, WriteAccessMiddleware


ROOT = Path(__file__).resolve().parents[2]


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        for name, value in (("REPO_ROOT", root / "repo"), ("CACHE_ROOT", root / "cache"),
                            ("READ_ONLY", True)):
            replacement = patch.object(settings, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.client = self.enterContext(TestClient(app))

    def test_management_aliases_and_methods_are_blocked(self):
        paths = ["/import.php", "/api/import2repo/", "/api/import2repo/index.php",
                 "/api/import2repo/check.php", "/api/import2repo/batch/check",
                 "/api/import2repo/batch", "/api/cache/clear.php", "/api/cache/update.php",
                 "/api/es/demo/add/id", "/api/es/demo/del/", "/api/es/demo/del/id",
                 "/api/es/demo/%61dd/id", "/api/es/demo/unknown"]
        with patch("mineprot.imports.commit") as commit, patch("mineprot.search.es_request") as es:
            for path in paths:
                for method in ("GET", "POST", "DELETE"):
                    with self.subTest(path=path, method=method):
                        response = self.client.request(method, path, content=b"invalid upload",
                                                       headers={"X-Forwarded-For": "127.0.0.1"})
                        self.assertEqual(response.status_code, 403)
            commit.assert_not_called()
            es.assert_not_called()
        self.assertEqual(list(settings.REPO_ROOT.iterdir()), [])

    def test_rejection_does_not_read_the_body(self):
        async def run():
            async def unexpected(*args):
                self.fail("Blocked request read its body or reached the application")

            messages = []

            async def send(message):
                messages.append(message)

            await WriteAccessMiddleware(unexpected)(
                {"type": "http", "path": "/api/import2repo/batch"}, unexpected, send)
            self.assertEqual(messages[0]["status"], 403)
        asyncio.run(run())

    def test_public_queries_and_pages_remain_available(self):
        with patch("mineprot.search.datasets", return_value=["demo"]), \
                patch("mineprot.search.browse_cache", return_value=[]), \
                patch("mineprot.search.search", return_value=[]):
            for path in ("/", "/browse.php?repo=demo", "/salign/", "/healthz"):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, path)
                self.assertNotIn('href="import.php"', response.text)
                self.assertNotIn('href="../import.php"', response.text)
                self.assertNotIn("Refresh cache", response.text)
            response = self.client.post("/api/es/demo/search/dGVzdA==")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
        response = httpx.Response(200, json={"_source": {}}, request=httpx.Request("GET", "http://es"))
        with patch("mineprot.search.es_request", return_value=response):
            self.assertEqual(self.client.post("/api/es/demo/get/id").status_code, 200)
        (settings.REPO_ROOT / "demo").mkdir()
        (settings.REPO_ROOT / "demo" / "model.json").write_text("{}")
        self.assertEqual(self.client.get("/api/file/demo/model.json").status_code, 200)
        self.assertEqual(self.client.get("/repo/demo/model.json").status_code, 200)
        with patch("mineprot.search.datasets", return_value=[]):
            self.assertNotIn('href="import.php"', self.client.get("/").text)

    def test_writable_service_preserves_import_and_index_operations(self):
        with patch.object(settings, "READ_ONLY", False), \
                patch("mineprot.imports.commit", return_value={"results": [{"status": "imported"}]}), \
                patch("mineprot.search.clear_browse"), \
                patch("mineprot.search.es_request", return_value=httpx.Response(200, json={})) as es, \
                patch("mineprot.search.datasets", return_value=[]):
            for path in ("/api/import2repo/", "/api/import2repo/index.php"):
                payload = {"repo": "demo", "name": "a.json", "text": base64.b64encode(b"{}").decode()}
                response = self.client.post(path, content=gzip.compress(json.dumps(payload).encode()))
                self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.client.post("/api/es/demo/add/id", json={}).status_code, 200)
            self.assertEqual(self.client.get("/api/es/demo/del/").status_code, 200)
            self.assertEqual(es.call_args.args[0], "DELETE")
            self.assertEqual(self.client.get("/import.php").status_code, 200)
            self.assertIn('href="import.php"', self.client.get("/").text)

    def test_public_conversion_and_salign_posts_remain_available(self):
        with patch("mineprot.app.pdb_to_alphacif", return_value="data_model"), \
                patch("mineprot.search.datasets", return_value=[]), \
                patch("mineprot.jobs.submit", return_value="abc123") as submit:
            for path in ("/api/pdb2alphacif/", "/api/pdb2alphacif/index.php"):
                response = self.client.post(path, json={"data": base64.b64encode(b"PDB").decode()})
                self.assertEqual(response.status_code, 200)
            for path in ("/api/salign/", "/api/salign/index.php"):
                response = self.client.post(path, data={"structure": "PDB"}, follow_redirects=False)
                self.assertEqual(response.status_code, 302)
            self.assertEqual(submit.call_count, 2)


class SetupTests(unittest.TestCase):
    def test_modes_persistence_and_local_admin_port_without_a_container_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("toolkit", "web/mineprot", "app/bin", "app/python", "app/elasticsearch/init"):
                (root / name).mkdir(parents=True)
            script = root / "toolkit/setup.sh"
            script.write_text((ROOT / "toolkit/setup.sh").read_text())
            (root / "docker-compose.yml").write_text((ROOT / "docker-compose.yml").read_text())
            archive = root / "app/bin/usalign.tar.xz"
            archive.write_bytes(b"fake archive; engine calls are mocked")
            (root / "app/python/tools.sha256").write_text(
                hashlib.sha256(archive.read_bytes()).hexdigest() + "  app/bin/usalign.tar.xz\n")
            engine = root / "fake-engine"
            engine.write_text(f"#!{sys.executable}\n" + '''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path('engine.log').open('a') as log:
    log.write(json.dumps({'args': args, 'readonly': os.getenv('MP_READ_ONLY'),
        'access': os.getenv('MP_REPO_ACCESS'), 'profiles': os.getenv('COMPOSE_PROFILES')}) + '\\n')
if args[0] == 'info': print('x86_64')
elif args[0] == '--version': print('Docker mock')
elif args[:2] == ['exec', 'elasticsearch']: print('yellow')
''')
            engine.chmod(0o755)
            environment = dict(os.environ, MP_READ_ONLY="false", MP_REPO_ACCESS="rw",
                               COMPOSE_PROFILES="unrelated")

            def run(*args):
                result = subprocess.run(["bash", str(script), "-c", str(engine), *args],
                                        cwd=root, env=environment, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                entries = [json.loads(line) for line in (root / "engine.log").read_text().splitlines()]
                (root / "engine.log").unlink()
                return entries

            for args in (("--production", "-a", "8082", "-p", "8080"), ()):
                entries = run(*args)
                config = (root / ".env").read_text()
                for value in ("MP_MODE=production", "MP_ADMIN_PORT=8082", "MP_READ_ONLY=true",
                              "MP_REPO_ACCESS=ro", "COMPOSE_PROFILES=production"):
                    self.assertIn(value, config)
                self.assertTrue(any(entry["args"][-2:] == ["web", "admin"] for entry in entries))
                self.assertTrue(any(entry["args"][:2] == ["exec", "MineAdmin"] for entry in entries))
                self.assertTrue(all(entry["readonly"] == "true" for entry in entries))
            entries = run("--development")
            self.assertIn("MP_READ_ONLY=false", (root / ".env").read_text())
            self.assertTrue(any(entry["args"] == ["compose", "--profile", "production", "rm", "-sf", "admin"]
                                for entry in entries))
            self.assertFalse(any(entry["args"][:2] == ["exec", "MineAdmin"] for entry in entries))
            result = subprocess.run(["bash", str(script), "--production", "-p", "8081", "-a", "8081"],
                                    cwd=root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be different", result.stderr)


if __name__ == "__main__":
    unittest.main()
