"""Qualify fresh SVG Content & Reference Inspector source ZIPs with no-pip, zero-distribution environments."""
if not __debug__:
    raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SHA256={"svg_inspector.py":"2aab9ed6059a457490f4097c9855ce5a92e3e1e528559920369b84b1a0e12569","examples/make_demo.py":"69ec45dad73d36e4b392341289d3b653436b6fd3d1a0f57f30179f5feda5d068"}
PROCESS_LINKS={"test_download.Download.test_native_symlink_input_and_output_parents_refused"}
PROCESS_WINDOWS_SKIPS={("test_download.Download.test_native_posix_fifo_and_socket_inputs_refused","Native POSIX FIFO and socket fixture")}
PROCESS_POSIX_SKIPS={("test_download.Download.test_native_windows_junction_stream_and_device_paths_refused","Native Windows junction and stream fixture")}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def pairs(rows):
    return {(r["test"], r["reason"]) for r in rows}

def run_tests(report):
    assert len(PROCESS_LINKS) == len(PROCESS_WINDOWS_SKIPS) == len(PROCESS_POSIX_SKIPS) == 1, "CLI_SKIP_CONTRACT_NOT_FINAL"
    assert report.is_absolute() and report.parent.is_dir() and not os.path.lexists(report)
    assert not report.resolve().is_relative_to(ROOT.resolve())
    assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions()), "FRESH_EMPTY_VENV_REQUIRED"
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    import svg_inspector as inspector
    import original_support
    assert Path(inspector.__file__).resolve() == ROOT / "svg_inspector.py"
    strict = os.name != "nt" or os.environ.get("OUTLANDS_SVG_REQUIRE_LINKS") == "1"
    regression = original_support.run_originals(strict=strict, log_stream=sys.stderr)
    assert regression["tests"] == 59
    copied = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_download.py")
    selected = list(flatten(copied)); ids = [t.id() for t in selected]
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
        skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors),
        skips=skips, unexpected_skips=unexpected, failed_tests=[t.id() for t, trace in result.failures+result.errors],
        module_counts={"test_download": 30}, test_ids=ids, copied_runtime_only=True, copied_runtime_cli=True,
        static_svg_reports_checked=True, fictional_inputs_only=True, source_svg_rendered=False, references_opened=False)
    unchanged = all(sha((ROOT / n).read_bytes()) == h for n, h in RUNTIME_SHA256.items())
    assert not list(importlib.metadata.distributions())
    summary = dict(schema=1, package="svg-content-inspector", version="0.1.0",
        status="PASS" if regression["status"] == integration["status"] == "PASS" and unchanged else "FAIL",
        platform=sys.platform, python=".".join(map(str, sys.version_info[:3])),
        tests=regression["tests"]+integration["tests"], passed=regression["passed"]+integration["passed"],
        skipped=regression["skipped"]+integration["skipped"],
        failures=regression["failures"]+integration["failures"], errors=regression["errors"]+integration["errors"],
        unexpected_skips=regression["unexpected_skips"]+integration["unexpected_skips"],
        regression=regression, integration=integration, fresh_venv=True, extracted_import=True,
        native_links_required=strict, runtime_unchanged=unchanged, runtime_sha256=RUNTIME_SHA256,
        runtime_dependencies=0, runtime_distributions=0, pip_in_application=False,
        real_artwork_used=False, inspection_performed=True, source_svg_rendered=False, references_opened=False, python_pin=regression["python_pin"])
    report.write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8", newline="\n")
    return 0 if summary["status"] == "PASS" else 1

def qualify(packages, reference, workspace, report, runtime_root, runtime_receipt):
    runtime_dependency=json.loads(runtime_receipt.read_text())
    assert runtime_dependency["platform"]==sys.platform and runtime_dependency["global_install_performed"] is False and runtime_dependency["binary_reproducibility_claimed"] is False
    lock=json.loads((ROOT/"RUNTIME-LOCK.json").read_text());minor=runtime_dependency["minor"]
    assert runtime_dependency["archives"]==dict(python=lock["python_archives"][sys.platform][minor],cpython_source=lock["cpython_sources"][minor],expat_source=lock["expat_source"])
    assert runtime_dependency["preparation_helper_sha256"]==sha((ROOT/"packaging/prepare_runtime.py").read_bytes()) and runtime_dependency["recipe_sha256"]==sha((ROOT/"packaging/expat-overlay/CMakeLists.txt").read_bytes()) and runtime_dependency["lock_sha256"]==sha((ROOT/"RUNTIME-LOCK.json").read_bytes())
    pin=runtime_dependency["python_pin"];assert pin["expat_version"]==[2,10,0] and pin["python"]==lock["python_archives"][sys.platform][minor]["python"]
    base_python=runtime_root/runtime_dependency["executable_relative"];extension=runtime_root/runtime_dependency["pyexpat_relative"]
    for file,digest in ((base_python,pin["executable_sha256"]),(extension,pin["pyexpat_sha256"])):
        assert file.resolve().is_relative_to(runtime_root.resolve()) and file.is_file() and not file.is_symlink() and sha(file.read_bytes())==digest
    assert Path(sys._base_executable).resolve()==base_python.resolve(),"USE_PREPARED_INTERPRETER_FOR_QUALIFICATION"
    for path in (workspace, report):
        assert path.is_absolute() and path.parent.is_dir() and not os.path.lexists(path)
        assert not path.resolve().is_relative_to(ROOT.resolve())
    assert packages.is_absolute() and packages.is_dir()
    receipt = json.loads((packages / "build-manifest.json").read_text())
    assert receipt["schema"] == 1 and receipt["package"] == "svg-content-inspector" and receipt["version"] == "0.1.0"
    assert receipt["filename"] == "svg-content-inspector-0.1.0.zip"
    archive = packages / receipt["filename"]
    assert archive.stat().st_size == receipt["bytes"] and sha(archive.read_bytes()) == receipt["sha256"]
    identical = False
    if reference is not None:
        assert reference.is_absolute() and reference.resolve() != packages.resolve()
        assert (reference / receipt["filename"]).read_bytes() == archive.read_bytes()
        assert (reference / "build-manifest.json").read_bytes() == (packages / "build-manifest.json").read_bytes()
        identical = True
    workspace.mkdir(); prefix = "svg-content-inspector-0.1.0/"
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
    if os.name == "nt":
        temp = workspace / "temp"; temp.mkdir()
    else:
        # Keep mandatory AF_UNIX fixtures below their native pathname limit.
        temp = Path(tempfile.mkdtemp(prefix="v-", dir="/tmp"))
        assert temp.resolve() == temp and not temp.is_symlink()
    fixture_temp_mode = "workspace_owned_windows" if os.name == "nt" else "short_owned_posix"
    inherited = {k:v for k,v in os.environ.items() if not k.upper().startswith(("PIP_", "PYTHON"))}
    env = dict(inherited, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1",
               TEMP=str(temp), TMP=str(temp), OUTLANDS_TEST_TEMP=str(temp), OUTLANDS_TEST_TEMP_ROOT=str(temp))
    env.update(OUTLANDS_TEST_EXPAT_SHA256=pin["pyexpat_sha256"],OUTLANDS_TEST_PYTHON_SHA256=pin["executable_sha256"],OUTLANDS_TEST_PYTHON_VERSION=pin["python"])
    def command(args, log, timeout=300):
        done = subprocess.run(args, cwd=app, env=env, capture_output=True, timeout=timeout)
        (workspace / log).write_bytes(done.stdout + done.stderr)
        return done
    assert command([sys.executable, "-I", "-B", str(app/"source_check.py")], "source-check-private.log").returncode == 0
    for helper in ("source_check.py", "packaging/build.py", "packaging/qualify.py", "packaging/prepare_runtime.py", "tests/original_support.py"):
        refused = command([sys.executable, "-O", "-B", str(app/helper), "--help"], helper.replace("/", "-")+"-optimized-private.log")
        assert refused.returncode != 0 and b"OPTIMIZED_PYTHON_UNSUPPORTED" in refused.stderr
    environment = workspace / "fresh-venv"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    done = command([str(python), "-I", "-B", "-W", "error", str(app/"packaging/qualify.py"),
                    "--tests", "--report", str(report)], "qualification-private.log", timeout=600)
    assert report.exists(), "QUALIFICATION_DID_NOT_REPORT"
    result = json.loads(report.read_text())
    assert not list(app.rglob("*.pyc")), "SOURCE_BYTECODE_UNEXPECTED"
    result.update(source_revision=receipt["source_revision"], zip_sha256=receipt["sha256"],
        archive_members=len(names), source_files=len(manifest["files"]), fresh_extraction=True,
        source_gate=True, source_manifest_verified=True, identical_zip=identical,
        identical_build_manifest=identical, optimization_refusal=True, source_bytecode_files=0,
        inherited_pip_and_python_environment_removed=True, fixture_temp_mode=fixture_temp_mode, runtime_dependency=runtime_dependency)
    report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))
    return done.returncode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", type=Path)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--runtime-receipt", type=Path)
    parser.add_argument("--reference-build", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--tests", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.tests:
        raise SystemExit(run_tests(args.report))
    if any(value is None for value in (args.packages, args.workspace,args.runtime_root,args.runtime_receipt)):
        parser.error("--packages, --workspace, --runtime-root and --runtime-receipt are required")
    raise SystemExit(qualify(args.packages, args.reference_build, args.workspace, args.report,args.runtime_root,args.runtime_receipt))
