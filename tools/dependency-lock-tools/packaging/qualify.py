"""Run all regression and copied-runtime CLI tests from a fresh extracted ZIP."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run_tests(report):
    sys.path.insert(0, str(ROOT))
    import lock_common
    assert Path(lock_common.__file__).resolve() == ROOT / "lock_common.py"
    assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    allowed = []
    unexpected = []
    for test, reason in result.skipped:
        platform_case = (os.name == "nt" and reason in ("POSIX FIFO fixture", "Unsupported-platform check runs on POSIX")) or (
            os.name != "nt" and reason == "Native Windows fixture")
        short_alias = os.name == "nt" and reason == "Native alternate short spelling unavailable" and "test_short_" in test.id()
        (allowed if platform_case or short_alias else unexpected).append(dict(test=test.id(), reason=reason))
    summary = dict(schema=1, status="PASS" if result.wasSuccessful() and not unexpected and result.testsRun == 81 else "FAIL",
                   python=".".join(map(str, sys.version_info[:3])), platform=sys.platform,
                   tests=result.testsRun, passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
                   skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors),
                   skips=allowed, unexpected_skips=unexpected,
                   failed_tests=[test.id() for test, trace in result.failures + result.errors],
                   fresh_venv=True, extracted_import=True, runtime_dependencies=0,
                   native_links_required=True, copied_runtime_cli_tests=5)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0 if summary["status"] == "PASS" else 1


def qualify(packages, workspace, report):
    assert workspace.is_absolute() and not workspace.exists() and not workspace.is_relative_to(ROOT) and not report.exists()
    receipt = json.loads((packages / "build-manifest.json").read_text(encoding="utf-8"))
    assert receipt["package"] == "dependency-lock-tools" and receipt["version"] == "0.1.0"
    archive = packages / receipt["filename"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt["sha256"]
    workspace.mkdir()
    prefix = "dependency-lock-tools-0.1.0/"
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        manifest = json.loads(source.read(prefix + "SOURCE-MANIFEST.json"))
        expected = {prefix + row["path"] for row in manifest["files"]} | {prefix + "SOURCE-MANIFEST.json"}
        assert len(names) == len(set(names)) == receipt["files"] == 19 and set(names) == expected
        for name in names:
            assert name.startswith(prefix) and ".." not in name.split("/") and "\\" not in name and ":" not in name
        for row in manifest["files"]:
            data = source.read(prefix + row["path"])
            assert len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"]
            assert data == (ROOT / row["path"]).read_text(encoding="utf-8").replace("\r\n", "\n").encode(), "ARCHIVE_SOURCE_DIFFERS"
        source.extractall(workspace)
    app = workspace / prefix
    environment = workspace / "fresh-venv"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
               TEMP=str(workspace), TMP=str(workspace), OUTLANDS_TEST_TEMP=str(workspace), OUTLANDS_LOCK_REQUIRE_NATIVE_LINKS="1")
    env.pop("PYTHONPATH", None)
    result = subprocess.run([str(python), "-I", "-B", "-W", "error", str(app / "packaging/qualify.py"), "--tests", "--report", str(report)],
                            cwd=app, env=env, capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert report.exists(), "QUALIFICATION_DID_NOT_REPORT"
    summary = json.loads(report.read_text(encoding="utf-8"))
    summary.update(source_revision=receipt["source_revision"], zip_sha256=receipt["sha256"], version="0.1.0")
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--tests", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.tests:
        raise SystemExit(run_tests(args.report))
    if args.packages is None or args.workspace is None:
        parser.error("--packages and --workspace are required")
    raise SystemExit(qualify(args.packages, args.workspace, args.report))
