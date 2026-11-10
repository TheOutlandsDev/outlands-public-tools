"""Install a supplied wheel in a fresh venv; run copied tests outside the checkout.

Only generated disposable data is changed. The workspace and raw output are
private. --report contains host-neutral counts, versions, hashes and import proof.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]


def installed(report):
    fixture_root = Path(__file__).resolve().parent
    if (fixture_root / "safe_file_mover").exists():
        raise RuntimeError("SOURCE_SHADOWING")
    sys.path.insert(0, str(fixture_root))  # tests only; no package source is copied
    import safe_file_mover
    from safe_file_mover.core import SafeMoveEngine

    prefix = Path(sys.prefix).resolve()
    imported = Path(safe_file_mover.__file__).resolve()
    if sys.prefix == sys.base_prefix or not imported.is_relative_to(prefix):
        raise RuntimeError("NOT_AN_INSTALLED_VENV_IMPORT")
    dist = importlib.metadata.distribution("safe-file-mover")
    if Path(dist.locate_file("safe_file_mover/__init__.py")).resolve() != imported:
        raise RuntimeError("DISTRIBUTION_IMPORT_MISMATCH")
    command = prefix / ("Scripts/safe-move.exe" if os.name == "nt" else "bin/safe-move")

    class InstalledWheelTests(unittest.TestCase):
        def setUp(self):
            temporary = tempfile.TemporaryDirectory(prefix="mover-cli-", dir=fixture_root)
            self.addCleanup(temporary.cleanup)
            self.root = Path(temporary.name)
            self.state = self.root / "state"
            self.source = self.root / "fictional.txt"
            self.payload = b"Fictional installed-wheel fixture\x00\xff"
            self.source.write_bytes(self.payload)
            self.destination = self.root / "destination"
            self.destination.mkdir()

        def cli(self, *args, status=0):
            result = subprocess.run([str(command), "--state-dir", str(self.state), *map(str, args)],
                                    cwd=fixture_root, capture_output=True, text=True,
                                    encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, status, result.stderr)
            return result

        def move(self):
            self.cli("move", self.source, self.destination)
            operations = SafeMoveEngine(self.state).list_operations()
            self.assertEqual(len(operations), 1)
            operation = operations[0]
            self.assertEqual(operation.status, "backup_retained")
            self.assertEqual(Path(operation.destination).read_bytes(), self.payload)
            self.assertEqual(Path(operation.recovery_copy).read_bytes(), self.payload)
            self.assertFalse(self.source.exists())
            return operation

        def test_installed_metadata_and_entrypoint(self):
            self.assertEqual(dist.version, "0.2.1")
            self.assertEqual(safe_file_mover.__version__, dist.version)
            self.assertEqual(set(dist.metadata["Requires-Python"].split(",")), {">=3.12.7", "<3.16"})
            self.assertFalse(dist.requires)
            self.assertEqual(dist.metadata["License-Expression"], "MIT")
            self.assertIn("usage: safe-move", self.cli("--help").stdout)
            self.assertFalse(self.state.exists())

        def test_installed_plan_has_no_mutation(self):
            self.cli("plan", self.source, self.destination)
            self.assertEqual(self.source.read_bytes(), self.payload)
            self.assertEqual(list(self.destination.iterdir()), [])
            self.assertFalse(self.state.exists())

        def test_installed_move_history_recover_restore(self):
            operation = self.move()
            self.assertIn(operation.operation_id, self.cli("list").stdout)
            self.cli("history", operation.operation_id)
            self.cli("recover", "--id", operation.operation_id)
            self.cli("restore", operation.operation_id)
            self.assertEqual(self.source.read_bytes(), self.payload)
            self.assertEqual(Path(operation.destination).read_bytes(), self.payload)

        def test_installed_purge_removes_only_verified_recovery(self):
            operation = self.move()
            self.cli("purge", operation.operation_id)
            self.assertFalse(Path(operation.recovery_copy).exists())
            self.assertEqual(Path(operation.destination).read_bytes(), self.payload)

        def test_installed_purge_refuses_changed_destination(self):
            operation = self.move()
            Path(operation.destination).write_bytes(b"Changed fictional destination")
            self.cli("purge", operation.operation_id, status=2)
            self.assertEqual(Path(operation.recovery_copy).read_bytes(), self.payload)
            self.assertEqual(Path(operation.destination).read_bytes(), b"Changed fictional destination")

    names = ("tests.test_core", "tests.test_cli", "tests.test_public_safety",
             "tests.test_remote_support", "tests.test_windows_streams", "tests.test_windows_safety")
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(InstalledWheelTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    # Opposite-platform cases are explicit skips; unavailable native Windows
    # features fail qualification in strict mode.
    native_skips = [(test, reason) for test, reason in result.skipped if os.name == "nt" and (
        test.__class__.__module__ == "tests.test_windows_streams" or
        test.__class__.__name__ == "NativeWindowsSafety")]
    strict = os.environ.get("OUTLANDS_MOVER_REQUIRE_NATIVE_FEATURES") == "1"
    summary = dict(status="PASS" if result.wasSuccessful() and not (strict and native_skips) else "FAIL",
                   python=".".join(map(str, sys.version_info[:3])), platform=sys.platform,
                   version=dist.version, installed_import=True, source_shadowing=False,
                   installed_console_script=True, tests=result.testsRun,
                   passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
                   skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors),
                   native_feature_skips=len(native_skips), strict_native=strict,
                   skip_reasons=sorted({reason.split(": [WinError", 1)[0]
                                        for test, reason in result.skipped}))
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return 0 if summary["status"] == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--installed", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.installed:
        return installed(args.report)
    if args.wheel is None or args.work_root is None:
        parser.error("--wheel and --work-root are required")
    wheel = args.wheel.resolve(strict=True)
    report = args.report.absolute()
    if report.exists():
        raise RuntimeError("FRESH_REPORT_REQUIRED")
    # A unique workspace is retained for private review; no recursive removal.
    work = Path(tempfile.mkdtemp(prefix="mover-wheel-", dir=args.work_root))
    env_root = work / "venv"
    venv.EnvBuilder(with_pip=True).create(env_root)
    python = env_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
               SAFE_FILE_MOVER_STATE_DIR=str(work / "unused-default-state"),
               TEMP=str(work), TMP=str(work), OUTLANDS_TEST_TEMP=str(work))
    env.pop("PYTHONPATH", None)
    subprocess.run([str(python), "-I", "-m", "pip", "--isolated", "install", "--no-index",
                    "--no-deps", str(wheel)], cwd=work, env=env, check=True)
    fixtures = work / "fixtures"
    fixtures.mkdir()
    shutil.copytree(ROOT / "tests", fixtures / "tests", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(__file__, fixtures / "qualify_wheel.py")
    result = subprocess.run([str(python), "-I", "-B", str(fixtures / "qualify_wheel.py"),
                             "--installed", "--report", str(report)], cwd=fixtures, env=env)
    if report.exists():
        summary = json.loads(report.read_text(encoding="utf-8"))
        summary["wheel_sha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()
        report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
