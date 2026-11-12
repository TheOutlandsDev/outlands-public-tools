"""Qualify an exact source ZIP with an offline hash-locked fresh dependency install."""
if not __debug__:
    raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
import argparse
import base64
import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SHA256 = {"markdown_docx.py": "c15dd21fc3acc2ea74cd67148e13701687d7077ff0d8571913684ed27a131a62",
                  "docx_windows.py": "d2072f8bdbaa48aa5718065961ec26902928e3c8704e0e11e4d88349cd2ae935"}
PROCESS_LINKS = {
    "test_download.Download.test_native_symlink_input_leaf_and_parent_are_refused",
    "test_download.Download.test_native_symlink_output_leaf_dangling_and_parent_preserve_targets",
}
PROCESS_WINDOWS_SKIPS = {("test_download.Download.test_native_posix_fifo_is_refused", "Native POSIX FIFO fixture")}
PROCESS_POSIX_SKIPS = {("test_download.Download.test_native_windows_junction_and_stream_spellings_preserve_input", "Native Windows junction and stream fixture")}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load_dependencies():
    spec = importlib.util.spec_from_file_location("qualified_docx_dependencies", ROOT / "packaging/dependencies.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def pairs(rows):
    return {(r["test"], r["reason"]) for r in rows}

def installed_dependencies():
    expected = {"python-docx": "1.2.0", "lxml": "6.1.3", "typing-extensions": "4.16.0"}
    distributions = list(importlib.metadata.distributions())
    normalize = lambda text: text.lower().replace("_", "-")
    actual = {normalize(d.metadata["Name"]): d.version for d in distributions}
    assert len(distributions) == 3 and actual == expected, "EXACT_THREE_RUNTIME_DISTRIBUTIONS_REQUIRED"
    counts = {}
    for distribution in distributions:
        checked = 0
        for row in csv.reader(io.StringIO(distribution.read_text("RECORD"))):
            if not row[1]:
                continue
            algorithm, digest = row[1].split("=", 1)
            assert algorithm == "sha256"
            path = Path(distribution.locate_file(row[0]))
            assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(Path(sys.prefix).resolve())
            data = path.read_bytes()
            actual_digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
            assert actual_digest == digest and len(data) == int(row[2]), "INSTALLED_RECORD_DIFFERS"
            checked += 1
        assert checked > 0
        counts[normalize(distribution.metadata["Name"])] = checked
    return actual, counts

def run_tests(report):
    assert report.is_absolute() and report.parent.is_dir() and not os.path.lexists(report)
    assert not report.resolve().is_relative_to(ROOT.resolve())
    assert sys.prefix != sys.base_prefix
    versions, records = installed_dependencies()
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    import markdown_docx
    import docx_windows
    import original_support
    assert Path(markdown_docx.__file__).resolve() == ROOT / "markdown_docx.py"
    assert Path(docx_windows.__file__).resolve() == ROOT / "docx_windows.py"
    assert Path(markdown_docx.windows_backend().__file__).resolve() == ROOT / "docx_windows.py"
    strict = os.name != "nt" or os.environ.get("OUTLANDS_DOCX_REQUIRE_NATIVE_LINKS") == "1"
    regression = original_support.run_originals(strict=strict, log_stream=sys.stderr)
    assert regression["tests"] == 72
    copied = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_download.py")
    selected = list(flatten(copied))
    ids = [t.id() for t in selected]
    assert len(ids) == len(set(ids)) == 30
    result = unittest.TextTestRunner(verbosity=2).run(copied)
    skips = [dict(test=t.id(), reason=reason) for t, reason in result.skipped]
    required = PROCESS_WINDOWS_SKIPS if os.name == "nt" else PROCESS_POSIX_SKIPS
    optional = {(name, "Native symlink privilege unavailable") for name in PROCESS_LINKS} if os.name == "nt" and not strict else set()
    observed = pairs(skips)
    unexpected = [r for r in skips if (r["test"], r["reason"]) not in required | optional]
    ok = result.wasSuccessful() and result.testsRun == 30 and len(observed) == len(skips) and required <= observed <= required | optional
    integration = dict(status="PASS" if ok else "FAIL", tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
        skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors), skips=skips,
        unexpected_skips=unexpected, failed_tests=[t.id() for t, trace in result.failures+result.errors],
        module_counts={"test_download": 30}, test_ids=ids, copied_runtime_only=True, copied_runtime_cli=True,
        fictional_docx_package_checks=True)
    unchanged = all(sha((ROOT / n).read_bytes()) == h for n, h in RUNTIME_SHA256.items())
    assert installed_dependencies() == (versions, records)
    import lxml.etree
    summary = dict(schema=1, package="document-builders", version="0.1.0",
        status="PASS" if regression["status"] == integration["status"] == "PASS" and unchanged else "FAIL",
        platform=sys.platform, python=".".join(map(str, sys.version_info[:3])),
        tests=regression["tests"]+integration["tests"], passed=regression["passed"]+integration["passed"],
        skipped=regression["skipped"]+integration["skipped"],
        failures=regression["failures"]+integration["failures"], errors=regression["errors"]+integration["errors"],
        unexpected_skips=regression["unexpected_skips"]+integration["unexpected_skips"],
        regression=regression, integration=integration, fresh_venv=True, extracted_import=True,
        native_links_required=strict, runtime_unchanged=unchanged, runtime_sha256=RUNTIME_SHA256,
        runtime_dependencies=3, dependency_versions=versions, installed_record_file_counts=records,
        installed_records_verified=True, pip_in_application=False, runtime_distributions_exact=True,
        libxml_version=list(lxml.etree.LIBXML_VERSION), libxslt_version=list(lxml.etree.LIBXSLT_VERSION),
        generated_docx_byte_determinism_claimed=False, visual_rendering_verified=False,
        real_or_historical_documents_used=False)
    report.write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8", newline="\n")
    return 0 if summary["status"] == "PASS" else 1

def qualify(packages, reference, wheelhouse, workspace, report):
    for path in (workspace, report):
        assert path.is_absolute() and path.parent.is_dir() and not os.path.lexists(path)
        assert not path.resolve().is_relative_to(ROOT.resolve())
    assert packages.is_absolute() and packages.is_dir()
    dependencies = load_dependencies()
    lane_key, lane, installer, artifacts = dependencies.check_wheelhouse(wheelhouse)
    receipt = json.loads((packages / "build-manifest.json").read_text())
    assert receipt["schema"] == 1 and receipt["package"] == "document-builders" and receipt["version"] == "0.1.0"
    assert receipt["filename"] == "document-builders-0.1.0.zip"
    archive = packages / receipt["filename"]
    assert archive.stat().st_size == receipt["bytes"] and sha(archive.read_bytes()) == receipt["sha256"]
    identical = False
    if reference is not None:
        assert reference.is_absolute() and reference.resolve() != packages.resolve()
        assert (reference / receipt["filename"]).read_bytes() == archive.read_bytes()
        assert (reference / "build-manifest.json").read_bytes() == (packages / "build-manifest.json").read_bytes()
        identical = True
    workspace.mkdir()
    prefix = "document-builders-0.1.0/"
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        manifest = json.loads(source.read(prefix + "SOURCE-MANIFEST.json"))
        assert len(names) == len(set(names)) == receipt["files"] == len(manifest["files"]) + 1
        assert set(names) == {prefix + r["path"] for r in manifest["files"]} | {prefix + "SOURCE-MANIFEST.json"}
        for name in names:
            assert name.startswith(prefix) and ".." not in name.split("/") and "\\" not in name and ":" not in name
            info = source.getinfo(name)
            assert info.external_attr >> 16 == 0o100644 and info.create_system == 3
            assert info.compress_type == zipfile.ZIP_STORED and info.date_time == (1980, 1, 1, 0, 0, 0)
        for row in manifest["files"]:
            data = source.read(prefix + row["path"])
            assert len(data) == row["bytes"] and sha(data) == row["sha256"]
            assert data == (ROOT / row["path"]).read_bytes(), "ARCHIVE_SOURCE_DIFFERS"
        assert source.read(prefix+"SOURCE-MANIFEST.json") == (ROOT/"SOURCE-MANIFEST.json").read_bytes()
        source.extractall(workspace)
    app = workspace / prefix
    temp = workspace / "temp"; temp.mkdir()
    inherited = {k:v for k,v in os.environ.items() if not k.upper().startswith(("PIP_", "PYTHON"))}
    env = dict(inherited, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1",
               TEMP=str(temp), TMP=str(temp), OUTLANDS_TEST_TEMP=str(temp), OUTLANDS_TEST_TEMP_ROOT=str(temp),
               PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_INPUT="1", PIP_NO_COMPILE="1")
    env.pop("PYTHONPATH", None)
    def command(args, log, timeout=300):
        done = subprocess.run(args, cwd=app, env=env, capture_output=True, timeout=timeout)
        (workspace / log).write_bytes(done.stdout + done.stderr)
        return done
    assert command([sys.executable, "-I", "-B", str(app/"source_check.py")], "source-check-private.log").returncode == 0
    for helper in ("source_check.py", "packaging/build.py", "packaging/qualify.py", "packaging/dependencies.py"):
        refused = command([sys.executable, "-O", "-B", str(app/helper), "--help"], helper.replace("/", "-")+"-optimized-private.log")
        assert refused.returncode != 0 and b"OPTIMIZED_PYTHON_UNSUPPORTED" in refused.stderr
    installer_env = workspace / "installer-venv"
    venv.EnvBuilder(with_pip=True).create(installer_env)
    installer_python = installer_env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    common = ["--disable-pip-version-check", "--no-cache-dir", "--no-index", "--no-deps", "--require-hashes", "--only-binary=:all:", "--no-compile", "--find-links", str(wheelhouse)]
    install = command([str(installer_python), "-I", "-B", "-m", "pip", "install", "--force-reinstall", *common,
                       "-r", str(app/"dependency-locks"/installer["lock"])], "installer-install-private.log")
    assert install.returncode == 0, "LOCKED_INSTALLER_INSTALL_FAILED"
    probe = command([str(installer_python), "-I", "-B", "-c", "import pip; print(pip.__version__)"], "installer-version-private.log")
    assert probe.returncode == 0 and probe.stdout.decode().strip() == installer["version"]
    environment = workspace / "fresh-venv"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    install = command([str(installer_python), "-I", "-B", "-m", "pip", "--python", str(python), "install", *common,
                       "-r", str(app/"dependency-locks"/lane["lock"])], "application-install-private.log")
    assert install.returncode == 0, "HASH_LOCKED_OFFLINE_INSTALL_FAILED"
    assert command([str(installer_python), "-I", "-B", "-m", "pip", "--python", str(python), "check"],
                   "dependency-check-private.log").returncode == 0
    done = command([str(python), "-I", "-B", "-W", "error", str(app/"packaging/qualify.py"),
                    "--tests", "--report", str(report)], "qualification-private.log", timeout=600)
    assert report.exists(), "QUALIFICATION_DID_NOT_REPORT"
    result = json.loads(report.read_text())
    assert not list(app.rglob("*.pyc")), "SOURCE_BYTECODE_UNEXPECTED"
    result.update(source_revision=receipt["source_revision"], zip_sha256=receipt["sha256"],
        archive_members=len(names), source_files=len(manifest["files"]), fresh_extraction=True,
        source_gate=True, source_manifest_verified=True, identical_zip=identical,
        identical_build_manifest=identical, optimization_refusal=True, source_bytecode_files=0,
        dependency_lane=lane_key, dependency_lock_sha256=lane["lock_sha256"],
        dependency_manifest_sha256=sha((app/"dependency-locks/DEPENDENCIES.json").read_bytes()),
        installer_version=installer["version"], installer_lock_sha256=installer["lock_sha256"],
        dependency_wheels=[{k:x[k] for k in ("project", "version", "filename", "bytes", "sha256")} for x in artifacts],
        offline_dependency_install=True, hashes_required=True, binary_only=True, dependency_resolution_disabled=True,
        dependency_check=True, dependency_wheelhouse_verified=True, inherited_pip_and_python_environment_removed=True)
    report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))
    return done.returncode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", type=Path)
    parser.add_argument("--reference-build", type=Path)
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--tests", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.tests:
        raise SystemExit(run_tests(args.report))
    if any(value is None for value in (args.packages, args.wheelhouse, args.workspace)):
        parser.error("--packages, --wheelhouse and --workspace are required")
    raise SystemExit(qualify(args.packages, args.reference_build, args.wheelhouse, args.workspace, args.report))
