"""PAE button availability must agree with the plot endpoint's validation."""
import gzip
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote

from mineprot import settings
from mineprot.app import decorate_search, pae_page, templates, token


class Buttons(HTMLParser):
    def __init__(self):
        super().__init__()
        self.enabled = []
        self.disabled = []
        self.score_links = []
        self.score_disabled = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href", "").endswith(".json"):
            self.score_links.append(attrs)
        if tag == "button" and attrs.get("title") == "Score JSON file is unavailable":
            self.score_disabled.append(attrs)
        if tag == "a" and "/api/plot/pae.php?" in attrs.get("href", ""):
            self.enabled.append(attrs)
        if tag == "button" and attrs.get("title") == "PAE data is unavailable or invalid":
            self.disabled.append(attrs)


class PaeAvailabilityTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(settings, "REPO_ROOT", Path(directory) / "repo"))
        self.enterContext(patch.object(settings, "CACHE_ROOT", Path(directory) / "cache"))
        self.repo = settings.REPO_ROOT / "demo"
        self.repo.mkdir(parents=True)
        self.enterContext(patch("mineprot.search.datasets", return_value=["demo"]))

    def search_button(self):
        hit = {"_index": "demo", "_source": {"name": "model"}}
        hit = decorate_search(hit)
        markup = templates.get_template("search_card.html").render(Search_Result=hit)
        parser = Buttons()
        parser.feed(markup)
        return parser

    def test_missing_or_invalid_pae_disables_button_without_a_link(self):
        cases = [None, b'invalid json', b'[]', b'null', b'{}',
                 b'{"plddt": [90]}', b'{"pae": []}', b'{"pae": [[1, 2]]}',
                 b'{"pae": [[-1]]}', b'{"pae": [["NaN"]]}',
                 b'{"pae": [[0]], "max_pae": 0}']
        for data in cases:
            with self.subTest(data=data):
                path = self.repo / "model.json"
                if data is not None:
                    path.write_bytes(data)
                parser = self.search_button()
                self.assertEqual(len(parser.score_links), int(data is not None))
                self.assertEqual(len(parser.score_disabled), int(data is None))
                if data is None:
                    self.assertIn("disabled", parser.score_disabled[0])
                    self.assertNotIn("href", parser.score_disabled[0])
                self.assertEqual(parser.enabled, [])
                self.assertEqual(len(parser.disabled), 1)
                self.assertIn("disabled", parser.disabled[0])
                self.assertEqual(parser.disabled[0]["aria-disabled"], "true")
                self.assertNotIn("href", parser.disabled[0])
                path.unlink(missing_ok=True)

    def test_plain_and_compressed_pae_enable_button_and_plot(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed):
                data = json.dumps({"pae": [[0, 1], [2, 0]]}).encode()
                path = self.repo / ("model.json.gz" if compressed else "model.json")
                path.write_bytes(gzip.compress(data) if compressed else data)
                parser = self.search_button()
                self.assertEqual(len(parser.score_links), 1)
                self.assertEqual(parser.score_disabled, [])
                self.assertEqual(len(parser.enabled), 1)
                self.assertEqual(parser.disabled, [])
                # Mapping the structure is optional for displaying a valid matrix.
                with patch("mineprot.app.render", side_effect=lambda request, name, values: values):
                    result = pae_page(None, unquote(token('/api/file/demo/model.json')))
                self.assertEqual(result["pae_data"]["matrix"], [[0., 1.], [2., 0.]])
                path.unlink()
