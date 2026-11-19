from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from opskit.cli import main


class CLITests(unittest.TestCase):
    def test_incident_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "incident.zip"
            (root / "doctor.json").write_text('{"status":"demo"}\n', encoding="utf-8")
            (root / "inventory.json").write_text('{"fixtures":[]}\n', encoding="utf-8")
            (root / "ports.json").write_text('{"rows":[]}\n', encoding="utf-8")
            output = io.StringIO()
            code = main(
                [
                    "--home",
                    str(root),
                    "incident",
                    "bundle",
                    "--doctor",
                    "doctor.json",
                    "--inventory",
                    "inventory.json",
                    "--ports",
                    "ports.json",
                    "--output",
                    str(bundle),
                    "--json",
                ],
                stdout=output,
                stderr=io.StringIO(),
            )
            self.assertEqual(0, code)
            self.assertTrue(bundle.is_file())
            with zipfile.ZipFile(bundle) as archive:
                self.assertEqual(
                    {
                        "doctor.json",
                        "inventory.json",
                        "ports.json",
                        "manifest.json",
                    },
                    set(archive.namelist()),
                )


if __name__ == "__main__":
    unittest.main()
