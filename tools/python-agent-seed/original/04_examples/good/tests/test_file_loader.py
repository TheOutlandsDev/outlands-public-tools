from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from agent_seed_examples.file_loader import JsonLoadError, load_json_object


class LoadJsonObjectTests(TestCase):
    def test_loads_json_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text('{"enabled": true, "limit": 3}', encoding="utf-8")
            self.assertEqual(load_json_object(path), {"enabled": True, "limit": 3})

    def test_rejects_json_array(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text('[1, 2, 3]', encoding="utf-8")
            with self.assertRaises(JsonLoadError):
                load_json_object(path)

    def test_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text('{not json}', encoding="utf-8")
            with self.assertRaises(JsonLoadError):
                load_json_object(path)
