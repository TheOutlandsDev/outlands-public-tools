from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from opskit.cli import main


class CLITests(unittest.TestCase):
    def test_doctor_json_flag_can_follow_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            observations = Path(directory) / "observations.json"
            observations.write_text(
                json.dumps({
                    "os": "windows",
                    "python_version": "3.15.2",
                    "workspace": "writable",
                    "disk_total_bytes": 40 * 1024**3,
                    "disk_free_bytes": 8 * 1024**3,
                    "memory_total_bytes": 8 * 1024**3,
                    "memory_available_bytes": 2 * 1024**3,
                    "temporary_directory_writable": True,
                    "hostname_resolution": True,
                }),
                encoding="utf-8",
            )
            output = io.StringIO()
            code = main(
                ["doctor", "--observations", str(observations), "--json"],
                stdout=output,
                stderr=io.StringIO(),
            )
            report = json.loads(output.getvalue())
            self.assertIn(code, {0, 1})
            self.assertEqual("doctor", report["command"])
            self.assertEqual("1", report["schema_version"])
            self.assertTrue(report["data"]["read_only"])
