"""Run 94 preserved transfer fixtures through finite native skip decisions.

The selected 39 shared methods, fixtures and entry helper are copied verbatim.
The original 55-method I/O file remains byte-identical. Only inherited skipTest
is intercepted; original methods, helpers and native assertions execute.
"""
if not __debug__:
    raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
import argparse
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
NAMES = ("test_original_transfers", "test_io_safety")
SYMLINK_REASON = "Native symlink creation unavailable"
SHORT_REASON = "Optional short-name alias unavailable"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def contract():
    value = json.loads((TESTS / "SKIP-CONTRACT.json").read_text(encoding="utf-8"))
    assert (value["total_methods"], value["original_assertion_calls"], value["helper_methods"]) == (94, 130, 16)
    assert value["ast_hash_encoding"] == "python-ast-fields-json-v2"
    return value

def source_pins():
    expected = contract()
    files = dict(expected["published_test_source_sha256"], **expected["runtime_sha256"])
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in files.items()), "PRESERVED_SOURCE_PIN_DIFFERS"
    raw = (TESTS / "test_original_transfers.py").read_bytes()
    selected = {node.name: sha(b"".join(raw.splitlines(keepends=True)[node.lineno-1:node.end_lineno]))
                for node in ast.parse(raw).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                and node.name in expected["selected_shared_source_sha256"]}
    assert selected == expected["selected_shared_source_sha256"], "SELECTED_ORIGINAL_FIXTURE_BYTES_DIFFER"
    return files

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def _skip_hook(original, events, strict, short_code):
    def checked_skip(self, reason):
        if reason == SYMLINK_REASON:
            error = sys.exception()
            actual = os.name == "nt" and isinstance(error, OSError) and getattr(error, "winerror", None) == 1314
            events.append(dict(test=self.id(), reason=reason, policy="actual_windows_1314",
                               actual_windows_1314=actual, strict=strict))
            if strict or not actual:
                self.fail("APPLICABLE_NATIVE_SYMLINK_REQUIRED")
            return original(self, reason)
        if reason == SHORT_REASON:
            caller = sys._getframe(1)
            values = caller.f_locals
            valid = caller.f_code is short_code
            if valid:
                size, buffer, source = values.get("size"), values.get("buffer"), values.get("source")
                valid = (type(size) is int and 0 < size < len(buffer)
                         and buffer.value.casefold() == str(source).casefold())
            events.append(dict(test=self.id(), reason=reason, policy="successful_same_path_short_name_absence",
                               successful_same_path=bool(valid), strict=strict))
            if not valid:
                self.fail("SHORT_PATH_API_MUST_SUCCEED_BEFORE_CAPABILITY_SKIP")
            return original(self, reason)
        self.fail("UNEXPECTED_OR_MANDATORY_NATIVE_FIXTURE_SKIP")
    return checked_skip

def runtime_bindings(modules):
    regression = modules["test_original_transfers"]
    inputs = modules["test_io_safety"]
    actual = {
        "regression_transfer": Path(regression.transfer.__file__).resolve(),
        "io_transfer": Path(inputs.m.__file__).resolve(),
        "regression_windows_backend": Path(regression.transfer._windows().__file__).resolve() if os.name == "nt" else None,
        "io_windows_backend": Path(inputs.w.__file__).resolve() if os.name == "nt" else None,
    }
    assert actual == {
        "regression_transfer": ROOT / "transfer.py",
        "io_transfer": ROOT / "transfer.py",
        "regression_windows_backend": ROOT / "transfer_windows.py" if os.name == "nt" else None,
        "io_windows_backend": ROOT / "transfer_windows.py" if os.name == "nt" else None,
    }, "ORIGINAL_TEST_RUNTIME_IMPORT_DIFFERS"
    assert regression.MODULE == ROOT and regression.ROOT == regression.transfer.REPOSITORY and inputs.MODULE == ROOT / "transfer.py", "ORIGINAL_FIXTURE_ROOT_DIFFERS"
    assert regression.transfer.REPOSITORY == inputs.m.REPOSITORY, "ORIGINAL_REPOSITORY_BOUNDARIES_DIFFER"
    for module in tuple(sys.modules.values()):
        origin = getattr(module, "__file__", None)
        if isinstance(origin, str):
            assert "/tools/server-maintenance/" not in origin.replace("\\", "/"), "UNRELATED_MAINTENANCE_RUNTIME_LOADED"
    return actual

def load_original_suite(strict=None):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_TRANSFERS_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    source_pins()
    modules = {}
    for name in NAMES:
        spec = importlib.util.spec_from_file_location(name, TESTS / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules[name] = module
    runtime_bindings(modules)
    events = []
    inputs = modules["test_io_safety"]
    short_code = inputs.WindowsIO.test_short_name_alias_is_refused_when_available.__code__
    for fixture in (modules["test_original_transfers"].Fixture, inputs.Fixture):
        fixture.skipTest = _skip_hook(fixture.skipTest, events, strict, short_code)
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(modules[name]) for name in NAMES)
    expected = contract()
    ids = [test.id() for test in flatten(suite)]
    wanted = {test_id for names in expected["test_ids"].values() for test_id in names}
    assert len(ids) == len(set(ids)) == 94 and set(ids) == wanted, "ORIGINAL_TEST_SELECTION_DIFFERS"
    return suite, modules, events

def run_originals(*, strict=None, log_stream=None):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_TRANSFERS_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    expected = contract()
    before = source_pins()
    suite, modules, events = load_original_suite(strict)
    ids = [test.id() for test in flatten(suite)]
    result = unittest.TextTestRunner(stream=log_stream if log_stream is not None else io.StringIO(), verbosity=2).run(suite)
    runtime_bindings(modules)
    assert source_pins() == before, "PRESERVED_SOURCES_CHANGED_DURING_TESTS"
    skips = [dict(test=test.id(), reason=reason) for test, reason in result.skipped]
    pairs = lambda rows: {(r["test"], r["reason"]) for r in rows}
    required = pairs(expected["windows_required_skips"] if os.name == "nt" else expected["posix_required_skips"])
    allowed = set(required)
    if os.name == "nt":
        allowed |= pairs(expected["windows_short_name_absence_skips"])
        if not strict:
            allowed |= pairs(expected["windows_optional_1314_skips"])
    observed = pairs(skips)
    assert len(skips) == len(observed), "DUPLICATE_SKIP"
    unexpected = [r for r in skips if (r["test"], r["reason"]) not in allowed]
    missing = sorted(required-observed)
    failed = [test.id() for test, trace in result.failures+result.errors]
    good = result.wasSuccessful() and result.testsRun == 94 and not unexpected and not missing
    return dict(schema=1, status="PASS" if good else "FAIL", tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors), skipped=len(result.skipped),
        failures=len(result.failures), errors=len(result.errors), skips=skips, unexpected_skips=unexpected,
        missing_required_skips=[dict(test=t, reason=r) for t,r in missing], failed_tests=failed,
        module_counts=expected["module_counts"], test_ids=ids, native_links_required=strict,
        fixture_adapters_installed=True, fixture_adapter_policy="skipTest-only interceptor; original bodies execute unchanged",
        skip_adapter_events=events, runtime_imports_verified=True, original_fixture_roots_verified=True,
        unrelated_maintenance_runtime_loaded=False, runtime_mirror_required=False, runtime_mirror_test_only=False,
        runtime_sha256=expected["runtime_sha256"], runtime_unchanged_during_tests=True,
        baseline_runtime_sha256=expected["baseline_runtime_sha256"], runtime_boundary_only_change=True,
        full_runtime_raw_bytes_preserved=False, native_backend_bytes_preserved=True,
        published_test_source_sha256=expected["published_test_source_sha256"],
        selected_shared_bytes_preserved=True, original_io_test_bytes_unchanged=True,
        original_method_bodies_preserved=True, original_methods=94, original_assertion_calls=130,
        original_test_method_assertion_calls=125, original_helper_assertion_calls=5, helper_methods=16,
        ast_hash_encoding="python-ast-fields-json-v2")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    assert args.report.is_absolute() and args.report.parent.is_dir()
    value = run_originals(log_stream=sys.stderr)
    with args.report.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2)+"\n")
    print(json.dumps({k:value[k] for k in ("status","tests","passed","skipped","failures","errors")}))
    raise SystemExit(0 if value["status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
