"""Original MIT entry-point checks. Offline commands launch no target program."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from helpers import ROOT, cli


class CliTests(unittest.TestCase):
    def test_no_arguments_shows_help(self):
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout.lower())

    def test_help_does_not_need_native_backend(self):
        result = cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plan", result.stdout)
        self.assertIn("launch", result.stdout)

    def test_demo_is_explicitly_simulated(self):
        result = cli("demo")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIs(data["simulated"], True)

    def test_script_entry_point_demo(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        result = subprocess.run([sys.executable, "-B", str(ROOT / "launcher.py"), "demo"],
                                cwd=ROOT, env=env, capture_output=True, text=True,
                                encoding="utf-8", timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIs(json.loads(result.stdout)["simulated"], True)

    def test_launch_requires_explicit_executable_and_cpu_selection(self):
        result = cli("launch")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_plan_requires_explicit_cpu_selection(self):
        result = cli("plan", "--exe", str(Path(sys.executable).absolute()))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_core_selection_is_user_facing_error(self):
        result = cli("plan", "--exe", str(Path(sys.executable).absolute()), "--cores", "0,,1")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_demo_creates_no_application_data(self):
        with tempfile.TemporaryDirectory(prefix="affinity-offline-") as folder:
            before = set(Path(folder).iterdir())
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT), PYTHONUTF8="1")
            result = subprocess.run([sys.executable, "-B", "-m", "app_affinity", "demo"],
                                    cwd=folder, env=env, capture_output=True, text=True,
                                    encoding="utf-8", timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(Path(folder).iterdir()), before)

    @unittest.skipIf(os.name == "nt", "Non-Windows refusal is checked on Linux")
    def test_real_launch_backend_is_refused_on_non_windows(self):
        with tempfile.TemporaryDirectory(prefix="affinity-platform-") as folder:
            fake = Path(folder) / "fixture.exe"
            fake.write_bytes(b"Generated file, not an executable.")
            result = cli("launch", "--exe", str(fake), "--mask", "0x1")
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
