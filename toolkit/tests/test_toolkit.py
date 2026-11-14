"""Offline regression checks for package imports, grouped CLIs and data workflows."""

import argparse
import contextlib
import gzip
import importlib
import io
import json
import os
import pkgutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

import mineprot_toolkit
from mineprot_toolkit import cli
from mineprot_toolkit.common import defaults, uploads
from mineprot_toolkit.common.naming import move_predictions

ROOT = Path(__file__).resolve().parents[1]


def command_modules(commands=cli.COMMANDS):
    for command in commands.values():
        if isinstance(command, dict):
            yield from command_modules(command)
        else:
            yield command


class EntrypointTests(unittest.TestCase):
    def test_implementation_imports_have_no_command_side_effects(self):
        with (
            patch.object(
                argparse.ArgumentParser, "parse_args", side_effect=AssertionError("parsed args")
            ),
            patch(
                "requests.sessions.Session.request", side_effect=AssertionError("network request")
            ),
            patch("builtins.input", side_effect=AssertionError("interactive prompt")),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            for spec in pkgutil.walk_packages(mineprot_toolkit.__path__, "mineprot_toolkit."):
                if not spec.name.endswith(".__main__"):
                    importlib.reload(importlib.import_module(spec.name))
        self.assertEqual(output.getvalue(), "")

    def test_all_grouped_command_help_pages(self):
        def paths(commands, prefix=()):
            for name, command in commands.items():
                if isinstance(command, dict):
                    yield from paths(command, (*prefix, name))
                else:
                    yield (*prefix, name)

        for path in paths(cli.COMMANDS):
            with (
                self.subTest(command=path),
                contextlib.redirect_stdout(io.StringIO()),
                self.assertRaises(SystemExit) as exited,
            ):
                cli.main([*path, "--help"])
            self.assertEqual(exited.exception.code, 0)

    def test_all_source_entrypoints_work_outside_the_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            for module in command_modules():
                entrypoint = ROOT / "scripts" / (module.replace(".", "/") + ".py")
                result = subprocess.run(
                    [sys.executable, str(entrypoint), "--help"],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 0, f"{entrypoint}: {result.stderr}")
                self.assertIn("usage:", result.stdout)

    def test_shared_server_defaults(self):
        from mineprot_toolkit.batch.import_repo import parser
        from mineprot_toolkit.import_single import ask_url

        self.assertEqual(parser().parse_args(["-i", "."]).url, defaults.IMPORT_URL)
        with patch("builtins.input", return_value=""):
            self.assertEqual(ask_url(), defaults.BASE_URL)

    def test_cancellation_and_request_errors_have_nonzero_status(self):
        with (
            patch("mineprot_toolkit.cli.import_module") as module,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            module.return_value.main.side_effect = requests.ConnectionError("offline")
            self.assertEqual(cli.execute("batch.import_repo", []), 1)
            module.return_value.main.side_effect = KeyboardInterrupt
            self.assertEqual(cli.execute("import_single", []), 130)


class DataWorkflowTests(unittest.TestCase):
    def test_renaming_keeps_prediction_companions_together(self):
        for mode in (0, 1, 2):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                staged, output = Path(directory) / "staged", Path(directory) / "output"
                staged.mkdir()
                output.mkdir()
                (staged / "protein.a3m").write_text("# metadata\n>sequence_id description\nAG\n")
                (staged / "protein.pdb").write_text("ATOM\n")
                (staged / "protein.json").write_text(
                    json.dumps({"plddt": [90, 80], "pae": [[1.4, 2.6]]})
                )
                names = move_predictions(staged, output, mode)
                self.assertEqual(len(names), 1)
                self.assertEqual(
                    {path.name for path in output.iterdir()},
                    {names[0] + suffix for suffix in (".pdb", ".a3m", ".json")},
                )
                self.assertEqual(
                    json.loads((output / (names[0] + ".json")).read_text())["pae"], [[1, 3]]
                )
                if mode == 1:
                    self.assertEqual(names, ["sequence_id"])

    def test_colabfold_transform_uses_the_shared_package(self):
        from mineprot_toolkit.ai.colabfold.transform import main

        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "input", Path(directory) / "output"
            source.mkdir()
            (source / "test_unrelaxed_rank_001_model.pdb").write_text("ATOM\n")
            (source / "test_scores_rank_001_model.json").write_text('{"plddt":[90],"pae":[[0.4]]}')
            (source / "test.a3m").write_text(">target\nA\n")
            with patch("mineprot_toolkit.ai.colabfold.transform.pdb2cif") as convert:
                self.assertEqual(main(["-i", str(source), "-o", str(output), "-n", "1"]), 0)
            self.assertEqual({p.stem for p in output.iterdir()}, {"target"})
            convert.assert_called_once_with(str(output), "target", defaults.CONVERSION_URL)

    def test_alphafold2_transform_keeps_ranking_scores_and_msa(self):
        import pickle

        import numpy as np

        from mineprot_toolkit.ai.alphafold2.transform import main

        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "input", Path(directory) / "output"
            prediction = source / "protein"
            (prediction / "msas").mkdir(parents=True)
            (prediction / "ranking_debug.json").write_text('{"order":["model_1"]}')
            (prediction / "ranked_0.pdb").write_text("ATOM\n")
            (prediction / "msas/bfd_uniref_hits.a3m").write_text(">target\nAA\n")
            (prediction / "result_model_1.pkl").write_bytes(
                pickle.dumps(
                    {
                        "plddt": np.array([90, 80]),
                        "predicted_aligned_error": np.array([[0, 1], [2, 0]]),
                        "max_predicted_aligned_error": 31.75,
                        "ptm": 0.8,
                    }
                )
            )
            with patch("mineprot_toolkit.ai.alphafold2.transform.pdb2cif") as convert:
                self.assertEqual(main(["-i", str(source), "-o", str(output), "-n", "1"]), 0)
            self.assertEqual(json.loads((output / "target.json").read_text())["plddt"], [90, 80])
            self.assertEqual((output / "target.pdb").read_text(), "ATOM\n")
            convert.assert_called_once_with(str(output), "target", defaults.CONVERSION_URL)

    def test_alphafold3_preparation_preserves_sequences_and_handles_empty_lists(self):
        from mineprot_toolkit.ai.alphafold3.prepare_complex import main

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "proteins.fasta").write_text(">a\nAG\n>b\nST\n")
            (root / "pairs.txt").write_text("a b\n")
            args = [
                "--list",
                str(root / "pairs.txt"),
                "--fasta",
                str(root / "proteins.fasta"),
                "-o",
                str(root / "output"),
                "-t",
                "2",
            ]
            self.assertEqual(main(args), 0)
            data = json.loads((root / "output/a_x_b.json").read_text())
            self.assertEqual(
                [entry["protein"]["sequence"] for entry in data["sequences"]], ["AG", "ST"]
            )
            (root / "pairs.txt").write_text("")
            self.assertEqual(main(args), 0)

    def test_extract_plddt_runs_in_spawned_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scores.json.gz").write_bytes(gzip.compress(b'{"plddt":[80,100]}'))
            # Spawn reimports package worker functions in a fresh interpreter.
            code = (
                "import multiprocessing; multiprocessing.set_start_method('spawn'); "
                "from mineprot_toolkit.misc.extract_plddt import main; "
                "main(['-i', __import__('sys').argv[1], '-t', '2'])"
            )
            result = subprocess.run(
                [sys.executable, "-c", code, str(root)], capture_output=True, text=True, timeout=20
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("scores\t90.0", result.stdout)

    def test_batch_preparation_and_upload_splitting_preserve_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a.pdb"
            path.write_bytes(b"ATOM\n")
            item, payload = uploads.prepare(path, 3, False)
            self.assertEqual(gzip.decompress(payload), path.read_bytes())
            self.assertEqual(item["storage"], "plain")
        batch = [({"name": name + ".pdb", "size": 1200}, b"x" * 1200) for name in ("a", "b")]

        def respond(url, **kwargs):
            if url.endswith("/check"):
                return {
                    "results": [{"name": item["name"], "status": "upload"} for item, _ in batch],
                    "max_body_bytes": 8000,
                }
            manifest = json.loads(kwargs["data"]["manifest"])
            return {
                "results": [
                    {"name": item["name"], "status": "imported"} for item in manifest["files"]
                ]
            }

        with patch.object(uploads, "request", side_effect=respond) as request:
            result = uploads.upload_batch(
                SimpleNamespace(n="demo", f=False, url=defaults.IMPORT_URL), batch
            )
        self.assertEqual([entry["status"] for entry in result], ["imported", "imported"])
        self.assertEqual(request.call_count, 3)  # One preflight, two bounded uploads.

    def test_single_model_import_still_uses_shared_upload_transport(self):
        from mineprot_toolkit import import_single

        self.assertIs(import_single.upload_batch, uploads.upload_batch)
        self.assertEqual(import_single.normalize_url("127.0.0.1:8081/"), defaults.BASE_URL)

    def test_metadata_worker_errors_are_returned_to_the_cli(self):
        from mineprot_toolkit.batch.import_es import main

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "a.pdb").write_text("ATOM\n")
            with (
                patch(
                    "mineprot_toolkit.batch.import_es.import_protein",
                    side_effect=ValueError("invalid model"),
                ),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(main(["-i", directory]), 1)

    def test_pdb_conversion_reads_the_requested_input_and_output(self):
        from mineprot_toolkit.misc.convert_pdb import main

        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "input", Path(directory) / "output"
            source.mkdir()
            (source / "a.pdb").write_text("ATOM\n")
            with (
                patch("mineprot_toolkit.misc.convert_pdb.pdb2cif") as convert,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                main(["-i", str(source), "-o", str(output)])
            self.assertEqual((output / "a.pdb").read_text(), "ATOM\n")
            convert.assert_called_once_with(str(output), "a", defaults.CONVERSION_URL)

    def test_cal_nf_converts_compressed_a3m_and_propagates_process_failure(self):
        from mineprot_toolkit.misc.calculate_neff import decompress_and_convert, run_cal_nf

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a.a3m.gz"
            path.write_bytes(gzip.compress(b">a\nACde-F\n>b\nAC--F\n"))
            result = Path(decompress_and_convert(str(path), directory))
            self.assertEqual(result.read_text(), "AC-F\nAC--F")
            with (
                patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "calNf")),
                self.assertRaises(subprocess.CalledProcessError),
            ):
                run_cal_nf(str(result), "calNf", 0.8, 0, 0, None)

    def test_failed_cif_response_does_not_create_a_file(self):
        from mineprot_toolkit.common.api import pdb2cif

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "a.pdb").write_text("ATOM\n")
            response = Mock(text="invalid CIF")
            with (
                patch("mineprot_toolkit.common.api.session") as session,
                self.assertRaises(ValueError),
            ):
                session.return_value.post.return_value = response
                pdb2cif(directory, "a", defaults.CONVERSION_URL)
            self.assertFalse((Path(directory) / "a.cif").exists())


class ShellTests(unittest.TestCase):
    def test_ai_pipeline_quotes_paths_and_stops_on_failure(self):
        for system in ("alphafold2", "colabfold"):
            for fail in (False, True):
                with (
                    self.subTest(system=system, fail=fail),
                    tempfile.TemporaryDirectory(prefix="toolkit test ") as directory,
                ):
                    root = Path(directory)
                    source = root / "input models"
                    source.mkdir()
                    interpreter = root / "fake python"
                    log = root / "calls.jsonl"
                    interpreter.write_text(
                        f"#!{sys.executable}\n"
                        + """import json, os, sys
from pathlib import Path
with Path(os.environ['TOOLKIT_TEST_LOG']).open('a') as stream:
    stream.write(json.dumps(sys.argv[1:]) + '\\n')
if os.environ['TOOLKIT_TEST_FAIL'] == '1':
    raise SystemExit(7)
"""
                    )
                    interpreter.chmod(0o755)
                    result = subprocess.run(
                        [
                            "bash",
                            str(ROOT / f"scripts/ai/{system}/import.sh"),
                            str(source),
                            "--repo",
                            "demo",
                            "--python",
                            str(interpreter),
                        ],
                        cwd=root,
                        env=dict(
                            os.environ,
                            TOOLKIT_TEST_LOG=str(log),
                            TOOLKIT_TEST_FAIL=str(int(fail)),
                            TMPDIR=str(root),
                        ),
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    calls = [json.loads(line) for line in log.read_text().splitlines()]
                    self.assertEqual(len(calls), 1 if fail else 3, result.stderr)
                    self.assertEqual(result.returncode == 0, not fail)
                    self.assertEqual(calls[0][calls[0].index("-i") + 1], str(source))
                    temporary = Path(calls[0][calls[0].index("-o") + 1])
                    self.assertFalse(temporary.exists())
                    if not fail:
                        self.assertTrue(calls[1][0].endswith("batch/import_es.py"))
                        self.assertTrue(calls[2][0].endswith("batch/import_repo.py"))


if __name__ == "__main__":
    unittest.main()
