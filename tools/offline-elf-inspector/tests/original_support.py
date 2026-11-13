"""Run unchanged ELF originals with finite native skips and a verified oracle."""
if not __debug__:
    raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
import argparse
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
NAMES = ("test_elf", "test_runtime_hints")
SYMLINK_ID = "test_elf.Graph.test_symlinks_are_not_followed_when_available"
SYMLINK_REASON = "Native symlink privilege unavailable"
ORACLE_ID = "test_elf.IndependentOracle.test_real_compiler_metadata_against_readelf"
ORACLE_REASON = "Independent gcc/readelf oracle requires Linux binutils and GCC"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def contract():
    value = json.loads((TESTS / "SKIP-CONTRACT.json").read_text(encoding="utf-8"))
    assert (value["total_methods"], value["original_assertion_calls"], value["helper_methods"]) == (73, 142, 8)
    assert value["module_counts"] == {"test_elf": 50, "test_runtime_hints": 23}
    assert value["ast_hash_encoding"] == "python-ast-fields-json-v2"
    return value

def source_pins():
    expected = contract()
    files = dict(expected["published_test_source_sha256"], **expected["runtime_sha256"])
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in files.items()), "PRESERVED_SOURCE_PIN_DIFFERS"
    return files

def python_pin():
    executable = Path(sys._base_executable).resolve()
    version = ".".join(map(str, sys.version_info[:3]))
    digest = sha(executable.read_bytes())
    assert version == os.environ["OUTLANDS_TEST_PYTHON_VERSION"], "PREPARED_PYTHON_VERSION_DIFFERS"
    assert digest == os.environ["OUTLANDS_TEST_PYTHON_SHA256"], "PREPARED_PYTHON_EXECUTABLE_DIFFERS"
    return dict(python=version, executable_sha256=digest, actual_interpreter_verified=True)

def _command(path, arguments):
    result = subprocess.run([str(path), *arguments], capture_output=True, text=True, env=compiler_environment(),
                            encoding="utf-8", errors="strict", timeout=30)
    assert result.returncode == 0, "ORACLE_VERSION_PROBE_FAILED"
    return result.stdout.strip()

def oracle_pin():
    report = Path(os.environ["OUTLANDS_ELF_ORACLE_REPORT"])
    assert report.is_absolute() and report.is_file(), "ORACLE_PREPARATION_RECEIPT_REQUIRED"
    raw = report.read_bytes()
    value = json.loads(raw)
    required = sys.platform == "linux"
    assert sys.platform in ("linux", "win32") and value["schema"] == 1 and value["status"] == "PASS"
    assert value["platform"] == sys.platform and value["oracle_required"] is required
    assert value["application_uses_oracle"] is value["fixture_binaries_executed"] is False
    assert value["binary_reproducibility_claimed"] is value["global_install_performed"] is False
    assert value["preparation_helper_sha256"] == sha((ROOT / "packaging/prepare_oracle.py").read_bytes()), "ORACLE_HELPER_PIN_DIFFERS"
    lock_raw = (ROOT / "ORACLE-LOCK.json").read_bytes()
    assert value["oracle_lock_sha256"] == sha(lock_raw), "ORACLE_LOCK_PIN_DIFFERS"
    lock = json.loads(lock_raw)
    assert lock["schema"] == 1 and lock["gcc_version"] == "15.2.0" and lock["readelf_version"] == "2.46", "ORACLE_LOGICAL_LOCK_DIFFERS"
    expected_names = {"gcc", "readelf"} if required else set()
    assert set(value["tools"]) == expected_names, "ORACLE_TOOL_SET_DIFFERS"
    tools = {}; paths = {}
    for name in sorted(expected_names):
        expected = value["tools"][name]
        assert set(expected) == {"basename", "bytes", "sha256", "version", "version_text"}, "ORACLE_TOOL_RECORD_FIELDS_DIFFER"
        path = Path(os.environ["OUTLANDS_ELF_" + name.upper()]).resolve(strict=True)
        assert path.is_absolute() and path.is_file(), "SELECTED_ORACLE_EXECUTABLE_REQUIRED"
        content = path.read_bytes()
        first_line = _command(path, ["--version"]).splitlines()[0]
        if name == "gcc":
            version = _command(path, ["-dumpfullversion", "-dumpversion"])
            assert version == "15.2.0", "LOCKED_GCC_VERSION_REQUIRED"
        else:
            match = re.fullmatch(r"GNU readelf .* (\d+\.\d+(?:\.\d+)?)", first_line)
            assert match, "GNU_READELF_VERSION_LINE_REQUIRED"
            version = match.group(1)
            assert version == "2.46", "LOCKED_READELF_VERSION_REQUIRED"
        actual = dict(basename=path.name, bytes=len(content), sha256=sha(content), version=version, version_text=first_line)
        assert actual == expected, "SELECTED_ORACLE_EXECUTABLE_PIN_DIFFERS"
        tools[name] = actual; paths[name] = path
    evidence = dict(required=required, tools=tools, oracle_lock_sha256=value["oracle_lock_sha256"],
                    preparation_helper_sha256=value["preparation_helper_sha256"], preparation_receipt_sha256=sha(raw),
                    application_uses_oracle=False, fixture_binaries_executed=False,
                    binary_reproducibility_claimed=False, global_install_performed=False)
    return evidence, paths

def compiler_environment():
    spec = importlib.util.spec_from_file_location("elf_verified_oracle_preparation", ROOT / "packaging/prepare_oracle.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper.compiler_environment()

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def _skip_hook(original, events, strict, symlink_code, oracle_code):
    def checked_skip(self, reason):
        caller = sys._getframe(1).f_code
        if reason == SYMLINK_REASON:
            assert self.id() == SYMLINK_ID and caller is symlink_code, "UNEXPECTED_NATIVE_SYMLINK_CASE"
            error = sys.exception()
            actual = os.name == "nt" and isinstance(error, OSError) and getattr(error, "winerror", None) == 1314
            events.append(dict(test=self.id(), reason=reason, policy="actual_windows_1314",
                               actual_windows_1314=actual, strict=strict))
            if strict or not actual:
                self.fail("APPLICABLE_NATIVE_SYMLINK_REQUIRED")
            return original(self, reason)
        if reason == ORACLE_REASON:
            assert os.name == "nt" and self.id() == ORACLE_ID and caller is oracle_code, "UNEXPECTED_ORACLE_SKIP"
            return original(self, reason)
        self.fail("UNEXPECTED_NATIVE_FIXTURE_SKIP")
    return checked_skip

def runtime_bindings(modules):
    for name, module in modules.items():
        assert Path(module.__file__).resolve() == TESTS / (name + ".py"), "ORIGINAL_FIXTURE_ROOT_DIFFERS"
        assert Path(module.e.__file__).resolve() == ROOT / "elf_inspector.py", "ORIGINAL_RUNTIME_IMPORT_DIFFERS"
        assert module.e.VERSION == "1.1.0", "ORIGINAL_RUNTIME_VERSION_DIFFERS"
        assert Path(sys.modules[module.create.__module__].__file__).resolve() == ROOT / "examples/make_demo.py", "ORIGINAL_EXAMPLE_IMPORT_DIFFERS"

def load_original_suite(strict=None):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_ELF_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    source_pins(); python_pin(); oracle_pin()
    modules = {}; suite = unittest.TestSuite(); events = []
    for name in NAMES:
        spec = importlib.util.spec_from_file_location(name, TESTS / (name + ".py"))
        module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
        modules[name] = module
    elf = modules["test_elf"]
    arguments = (events, strict, elf.Graph.test_symlinks_are_not_followed_when_available.__code__,
                 elf.IndependentOracle.test_real_compiler_metadata_against_readelf.__code__)
    elf.Fixture.skipTest = _skip_hook(elf.Fixture.skipTest, *arguments)
    hints = modules["test_runtime_hints"]
    hints.RuntimeHints.skipTest = _skip_hook(hints.RuntimeHints.skipTest, *arguments)
    runtime_bindings(modules)
    expected = contract()
    for name, module in modules.items():
        selected = unittest.defaultTestLoader.loadTestsFromModule(module)
        ids = [test.id() for test in flatten(selected)]
        assert len(ids) == len(set(ids)) == expected["module_counts"][name] and set(ids) == set(expected["test_ids"][name]), "ORIGINAL_TEST_SELECTION_DIFFERS"
        suite.addTests(selected)
    assert len(list(flatten(suite))) == 73
    return suite, modules, events

def run_originals(*, strict=None, log_stream=None):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_ELF_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    expected = contract(); before = source_pins(); interpreter = python_pin()
    oracle, paths = oracle_pin(); suite, modules, events = load_original_suite(strict)
    ids = [test.id() for test in flatten(suite)]; selections = []; actual_which = shutil.which
    def selected_which(command, *args, **kwargs):
        if command in paths:
            assert not args and not kwargs, "UNEXPECTED_ORACLE_SELECTION_ARGUMENTS"
            selections.append(command)
            return str(paths[command])
        return actual_which(command, *args, **kwargs)
    environment = compiler_environment()
    if oracle["required"]:
        environment["ELF_REQUIRE_ORACLE"] = "1"
    with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(shutil, "which", side_effect=selected_which):
        required_oracle_propagated = os.environ.get("ELF_REQUIRE_ORACLE") == "1"
        result = unittest.TextTestRunner(stream=log_stream if log_stream is not None else io.StringIO(), verbosity=2).run(suite)
    runtime_bindings(modules)
    assert source_pins() == before, "PRESERVED_SOURCES_CHANGED_DURING_TESTS"
    assert python_pin() == interpreter, "ACTUAL_PYTHON_CHANGED_DURING_TESTS"
    after_oracle, after_paths = oracle_pin()
    assert after_oracle == oracle and after_paths == paths, "ORACLE_EXECUTABLES_OR_RECEIPT_CHANGED_DURING_TESTS"
    skips = [dict(test=test.id(), reason=reason) for test, reason in result.skipped]
    pairs = lambda rows: {(row["test"], row["reason"]) for row in rows}
    required = pairs(expected["windows_required_skips"] if os.name == "nt" else expected["posix_required_skips"])
    allowed = required | (pairs(expected["windows_optional_1314_skips"]) if os.name == "nt" and not strict else set())
    observed = pairs(skips); assert len(skips) == len(observed), "DUPLICATE_SKIP"
    unexpected = [row for row in skips if (row["test"], row["reason"]) not in allowed]; missing = sorted(required-observed)
    failed = [test.id() for test, trace in result.failures+result.errors]
    executed = oracle["required"] and ORACLE_ID in ids and ORACLE_ID not in failed and ORACLE_ID not in {row["test"] for row in skips}
    oracle_selection_verified = sorted(selections) == ["gcc", "readelf"] if oracle["required"] else selections == []
    good = result.wasSuccessful() and result.testsRun == 73 and not unexpected and not missing and oracle_selection_verified and executed is oracle["required"]
    return dict(schema=1, status="PASS" if good else "FAIL", tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors), skipped=len(result.skipped),
        failures=len(result.failures), errors=len(result.errors), skips=skips, unexpected_skips=unexpected,
        missing_required_skips=[dict(test=test, reason=reason) for test,reason in missing], failed_tests=failed,
        module_counts=expected["module_counts"], test_ids=ids, native_links_required=strict,
        oracle_requirement_propagated=required_oracle_propagated, fixture_adapters_installed=True,
        fixture_adapter_policy="skipTest-only native interceptor; verified exact-name gcc/readelf selector; original bodies unchanged",
        skip_adapter_events=events, runtime_imports_verified=True, original_fixture_roots_verified=True,
        runtime_mirror_required=False, runtime_mirror_test_only=False,
        runtime_sha256=expected["runtime_sha256"], baseline_runtime_sha256=expected["baseline_runtime_sha256"], runtime_unchanged_during_tests=True,
        published_test_source_sha256=expected["published_test_source_sha256"], original_test_bytes_unchanged=True,
        full_runtime_raw_bytes_preserved=True, example_raw_bytes_preserved=True, original_method_bodies_preserved=True,
        original_methods=73, original_assertion_calls=142, original_test_method_assertion_calls=142, original_helper_assertion_calls=0, helper_methods=8,
        python_pin=dict(interpreter, bytes_unchanged=True), ast_hash_encoding="python-ast-fields-json-v2",
        oracle_evidence=dict(oracle, executed=executed, selected_executables_unchanged=True,
                             selection_adapter="verified exact gcc/readelf names only", selection_verified=oracle_selection_verified))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    assert args.report.is_absolute() and args.report.parent.is_dir()
    assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions()), "FRESH_NO_PIP_ENVIRONMENT_REQUIRED"
    value = run_originals(log_stream=sys.stderr)
    value.update(fresh_venv=True, runtime_dependencies=0)
    with args.report.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2)+"\n")
    print(json.dumps({key:value[key] for key in ("status","tests","passed","skipped","failures","errors")}))
    raise SystemExit(0 if value["status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
