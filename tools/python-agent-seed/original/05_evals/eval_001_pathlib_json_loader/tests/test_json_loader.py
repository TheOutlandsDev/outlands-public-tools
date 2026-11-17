from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from starter.json_loader import JsonLoaderError, load_json_object


class JsonLoaderEvalTests(TestCase):
    def test_loads_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text('{"mode": "test", "count": 2}', encoding="utf-8")
            self.assertEqual(load_json_object(path), {"mode": "test", "count": 2})

    def test_rejects_array(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text('[1, 2, 3]', encoding="utf-8")
            with self.assertRaises(JsonLoaderError):
                load_json_object(path)

    def test_wraps_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text('{bad json}', encoding="utf-8")
            with self.assertRaises(JsonLoaderError):
                load_json_object(path)

    def test_wraps_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(JsonLoaderError):
                load_json_object(Path(tmp) / "missing.json")
