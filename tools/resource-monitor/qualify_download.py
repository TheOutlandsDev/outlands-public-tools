"""Qualify one extracted source ZIP in separate fresh demo/live environments.

Writes only private disposable workspace data and a sanitized result report.
Live metrics and capability tokens are captured in memory, never in the report.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import venv
import zipfile

ROOT = Path(__file__).resolve().parent
VERSION = "0.1.2"
LIVE_TEST = "test_live_aggregate_sampling_when_dependency_available"


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def run_mode(mode, report):
    sys.path.insert(0, str(ROOT))
    import resource_monitor
    assert Path(resource_monitor.__file__).resolve().is_relative_to(ROOT)
    assert resource_monitor.__version__ == VERSION
    assert sys.prefix != sys.base_prefix
    if mode == "demo":
        assert importlib.util.find_spec("psutil") is None, "DEMO_MUST_HAVE_NO_PSUTIL"
    else:
        import psutil
        assert psutil.__version__ == "7.2.2"
        assert Path(psutil.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    all_tests = list(flatten(unittest.defaultTestLoader.discover(str(ROOT / "tests"))))
    def is_live(test):
        return test.__class__.__module__ == "test_live_modes" or test._testMethodName == LIVE_TEST
    selected = [test for test in all_tests if is_live(test) == (mode == "live")]
    assert selected, "NO_TESTS_SELECTED"
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
    summary = dict(mode=mode, tests=result.testsRun,
                   passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
                   skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors),
                   psutil="absent" if mode == "demo" else "7.2.2",
                   extracted_import=True, fresh_venv=True,
                   failed_tests=[test.id() for test, trace in result.failures + result.errors])
    if mode == "demo":
        assert "psutil" not in sys.modules, "DEMO_IMPORTED_PSUTIL"
    summary["status"] = "PASS" if result.wasSuccessful() and not result.skipped else "FAIL"
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0 if summary["status"] == "PASS" else 1


def execute(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding="utf-8", timeout=240)
    if result.returncode:
        # Keep diagnostics local; do not echo native metrics, URLs or raw output.
        raise RuntimeError("QUALIFICATION_CHILD_FAILED")
    return result.stdout


def qualify(packages, workspace, report):
    assert workspace.is_absolute() and not workspace.exists() and not report.exists()
    assert ROOT not in workspace.parents
    matrix = json.loads((packages / "release-matrix.json").read_text(encoding="utf-8"))
    items = [item for item in matrix["applications"] if item["app"] == "resource-monitor" and item["version"] == VERSION]
    assert len(items) == 1
    item = items[0]
    archive = packages / item["filename"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == item["sha256"]
    workspace.mkdir()
    prefix = "resource-monitor-" + VERSION + "/"
    expected_manifest = json.loads((ROOT / "SOURCE-MANIFEST.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        expected = {prefix + row["path"] for row in expected_manifest["files"]} | {prefix + "SOURCE-MANIFEST.json"}
        assert set(names) == expected and len(names) == len(expected) == item["files"]
        for name in names:
            assert source.read(name) == (ROOT / name.removeprefix(prefix)).read_bytes(), "ZIP_SOURCE_DIFFERS"
        source.extractall(workspace)
    app = workspace / prefix
    base_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
                    RESOURCE_MONITOR_REQUIRE_LIVE="1", RESOURCE_MONITOR_REQUIRE_NATIVE="1",
                    TEMP=str(workspace), TMP=str(workspace))
    base_env.pop("PYTHONPATH", None)
    reports = []
    for mode in ("demo", "live"):
        environment = workspace / (mode + "-venv")
        venv.EnvBuilder(with_pip=mode == "live").create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = dict(base_env, RESOURCE_MONITOR_PYTHON=str(python))
        if mode == "live":
            execute([str(python), "-I", "-m", "pip", "--isolated", "install", "--require-hashes",
                     "--only-binary=:all:", "--no-deps", "-r", str(app / "requirements-live.txt")], app, env)
        result_path = workspace / (mode + ".json")
        execute([str(python), "-I", "-B", "-W", "error", str(app / "qualify_download.py"),
                 "--mode", mode, "--report", str(result_path)], app, env)
        reports.append(json.loads(result_path.read_text(encoding="utf-8")))
        if mode == "demo":
            execute([str(python), "-I", "-B", str(app / "examples/download_check.py"),
                     "--workspace", str(workspace / "fictional-download-check")], app, env)
    frontend = execute(["node", "--test", "--test-reporter=tap", "tests/frontend.test.mjs"], app, base_env)
    assert "# fail 0" in frontend and "# skipped 0" in frontend
    node_tests = int(next(line.split()[-1] for line in frontend.splitlines() if line.startswith("# tests ")))
    result = dict(schema=1, app="resource-monitor", version=VERSION, status="PASS",
                  source_revision=item["source_revision"], zip_sha256=item["sha256"],
                  python=".".join(map(str, sys.version_info[:3])), platform=sys.platform,
                  modes=reports, demo_download_check=True, frontend_tests=node_tests,
                  frontend_failures=0, frontend_skips=0, exact_extracted_source=True,
                  native_features_required=True, live_values_published=False)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--mode", choices=("demo", "live"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.mode:
        raise SystemExit(run_mode(args.mode, args.report))
    if args.packages is None or args.workspace is None:
        parser.error("--packages and --workspace are required")
    try:
        qualify(args.packages, args.workspace, args.report)
    except Exception:
        modes = []
        for mode in ("demo", "live"):
            result = args.workspace / (mode + ".json")
            if result.is_file():
                modes.append(json.loads(result.read_text(encoding="utf-8")))
        failure = dict(status="FAIL", code="DOWNLOAD_QUALIFICATION_FAILED", modes=modes)
        if not args.report.exists():
            args.report.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure))
        raise SystemExit(1)
