"""Run the unchanged Android sparse originals with finite, actual native-fixture skip rules."""
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
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
NAMES = ("test_sparse", "test_support")
SYMLINK_REASON = "Symlink creation requires platform privileges"
SYMLINK_IDS = {
    "test_sparse.SparseTests.test_reader_regular_and_link_paths",
    "test_support.SupportTests.test_link_and_linked_parent_rejected",
}
HARDLINK_ID = "test_support.SupportTests.test_duplicate_path_and_hardlink_inputs_rejected"
HARDLINK_REASON = "Hardlinks unavailable in test environment"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def contract():
    value = json.loads((TESTS / "SKIP-CONTRACT.json").read_text(encoding="utf-8"))
    assert (value["total_methods"], value["original_assertion_calls"], value["helper_methods"]) == (45, 96, 9)
    assert value["module_counts"] == {"test_sparse": 27, "test_support": 18}
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


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def _skip_hook(original, events, strict, symlink_codes, hardlink_code):
    def checked_skip(self, reason):
        caller = sys._getframe(1).f_code
        if reason == SYMLINK_REASON:
            assert self.id() in SYMLINK_IDS and caller is symlink_codes[self.id()], "UNEXPECTED_NATIVE_SYMLINK_CASE"
            error = sys.exception()
            actual = os.name == "nt" and isinstance(error, OSError) and getattr(error, "winerror", None) == 1314
            events.append(dict(test=self.id(), reason=reason, policy="actual_windows_1314",
                               actual_windows_1314=actual, strict=strict))
            if strict or not actual:
                self.fail("APPLICABLE_NATIVE_SYMLINK_REQUIRED")
            return original(self, reason)
        if reason == HARDLINK_REASON:
            assert self.id() == HARDLINK_ID and caller is hardlink_code, "UNEXPECTED_NATIVE_HARDLINK_CASE"
            events.append(dict(test=self.id(), reason=reason, policy="hardlinks_required", strict=strict))
            self.fail("APPLICABLE_NATIVE_HARDLINK_REQUIRED")
        self.fail("UNEXPECTED_NATIVE_FIXTURE_SKIP")
    return checked_skip


def runtime_bindings(modules):
    for name, module in modules.items():
        assert Path(module.__file__).resolve() == TESTS / (name + ".py"), "ORIGINAL_FIXTURE_ROOT_DIFFERS"
    native = modules["test_sparse"]
    assert Path(native.tool.__file__).resolve() == ROOT / "sparse_inspector.py", "ORIGINAL_RUNTIME_IMPORT_DIFFERS"
    assert Path(native.binary_reader.__file__).resolve() == ROOT / "binary_reader.py", "ORIGINAL_READER_IMPORT_DIFFERS"
    assert Path(sys.modules["inspection_support"].__file__).resolve() == ROOT / "inspection_support.py", "SHARED_RUNTIME_IMPORT_DIFFERS"
    assert Path(modules["test_support"].support.__file__).resolve() == ROOT / "inspection_support.py", "ORIGINAL_SUPPORT_IMPORT_DIFFERS"


def selected_strict(strict):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_SPARSE_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    return strict


def load_original_suite(strict=None):
    strict = selected_strict(strict)
    source_pins(); python_pin()
    modules = {}; suite = unittest.TestSuite(); events = []
    for name in NAMES:
        spec = importlib.util.spec_from_file_location(name, TESTS / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules[name] = module
    native, support = modules["test_sparse"], modules["test_support"]
    symlinks = {
        "test_sparse.SparseTests.test_reader_regular_and_link_paths": native.SparseTests.test_reader_regular_and_link_paths.__code__,
        "test_support.SupportTests.test_link_and_linked_parent_rejected": support.SupportTests.test_link_and_linked_parent_rejected.__code__,
    }
    hardlink = support.SupportTests.test_duplicate_path_and_hardlink_inputs_rejected.__code__
    for cls in (native.SparseTests, support.SupportTests):
        cls.skipTest = _skip_hook(cls.skipTest, events, strict, symlinks, hardlink)
    runtime_bindings(modules)
    expected = contract()
    for name, module in modules.items():
        selected = unittest.defaultTestLoader.loadTestsFromModule(module)
        ids = [test.id() for test in flatten(selected)]
        assert len(ids) == len(set(ids)) == expected["module_counts"][name] and set(ids) == set(expected["test_ids"][name]), "ORIGINAL_TEST_SELECTION_DIFFERS"
        suite.addTests(selected)
    assert len(list(flatten(suite))) == 45
    return suite, modules, events


def run_originals(*, strict=None, log_stream=None):
    strict = selected_strict(strict)
    expected = contract(); before = source_pins(); interpreter = python_pin()
    suite, modules, events = load_original_suite(strict)
    ids = [test.id() for test in flatten(suite)]
    result = unittest.TextTestRunner(stream=log_stream if log_stream is not None else io.StringIO(), verbosity=2).run(suite)
    runtime_bindings(modules)
    assert source_pins() == before, "PRESERVED_SOURCES_CHANGED_DURING_TESTS"
    assert python_pin() == interpreter, "ACTUAL_PYTHON_CHANGED_DURING_TESTS"
    skips = [dict(test=test.id(), reason=reason) for test, reason in result.skipped]
    pairs = lambda rows: {(row["test"], row["reason"]) for row in rows}
    required = pairs(expected["windows_required_skips"] if os.name == "nt" else expected["posix_required_skips"])
    allowed = required | (pairs(expected["windows_optional_1314_skips"]) if os.name == "nt" and not strict else set())
    observed = pairs(skips); assert len(skips) == len(observed), "DUPLICATE_SKIP"
    unexpected = [row for row in skips if (row["test"], row["reason"]) not in allowed]
    missing = sorted(required - observed)
    good = result.wasSuccessful() and result.testsRun == 45 and not unexpected and not missing
    return dict(schema=1, status="PASS" if good else "FAIL", tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors), skipped=len(result.skipped),
        failures=len(result.failures), errors=len(result.errors), skips=skips, unexpected_skips=unexpected,
        missing_required_skips=[dict(test=test, reason=reason) for test,reason in missing],
        failed_tests=[test.id() for test,trace in result.failures+result.errors],
        module_counts=expected["module_counts"], test_ids=ids, native_links_required=strict,
        fixture_adapters_installed=True, fixture_adapter_policy="skipTest-only interceptor; actual Win1314 local symlinks only; hardlinks mandatory",
        skip_adapter_events=events, runtime_imports_verified=True, original_fixture_roots_verified=True,
        runtime_mirror_required=False, runtime_mirror_test_only=False,
        runtime_sha256=expected["runtime_sha256"], baseline_runtime_sha256=expected["baseline_runtime_sha256"], runtime_unchanged_during_tests=True,
        published_test_source_sha256=expected["published_test_source_sha256"], original_test_bytes_unchanged=True,
        full_runtime_raw_bytes_preserved=True, example_raw_bytes_preserved=True, original_method_bodies_preserved=True,
        original_methods=45, original_assertion_calls=96, original_test_method_assertion_calls=94, original_helper_assertion_calls=2, helper_methods=9,
        python_pin=dict(interpreter, bytes_unchanged=True), ast_hash_encoding="python-ast-fields-json-v2",
        payload_crc_checked=False, whole_image_hashed=False, fixture_images_executed=False, physical_devices_opened=False, real_user_images_used=False)


def run(report_path, *, strict_links=None, log_stream=None):
    assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions()), "FRESH_NO_PIP_ENVIRONMENT_REQUIRED"
    value = run_originals(strict=strict_links, log_stream=log_stream)
    value.update(fresh_venv=True, runtime_dependencies=0)
    path = Path(report_path)
    assert path.is_absolute() and path.parent.is_dir()
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2)+"\n")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--strict-links", action="store_true", default=None)
    args = parser.parse_args()
    value = run(args.report, strict_links=args.strict_links, log_stream=sys.stderr)
    print(json.dumps({key:value[key] for key in ("status","tests","passed","skipped","failures","errors")}))
    raise SystemExit(0 if value["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
