"""Run the unchanged 59-method SVG source with finite native skip decisions."""
if not __debug__:
    raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
import argparse
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import pyexpat
import sys
import unittest
from unittest import mock
from xml.parsers import expat

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
NAME = "test_svg"
SYMLINK_REASON = "Native Windows symlink creation privilege unavailable"
FIFO_REASON = "POSIX FIFO case"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def contract():
    value = json.loads((TESTS / "SKIP-CONTRACT.json").read_text(encoding="utf-8"))
    assert (value["total_methods"], value["original_assertion_calls"], value["helper_methods"]) == (59, 99, 6)
    assert value["ast_hash_encoding"] == "python-ast-fields-json-v2"
    return value

def source_pins():
    expected = contract()
    files = dict(expected["published_test_source_sha256"], **expected["runtime_sha256"])
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in files.items()), "PRESERVED_SOURCE_PIN_DIFFERS"
    return files

def python_pin():
    assert tuple(pyexpat.version_info) == tuple(expat.version_info) >= (2, 10, 0), "ACTUAL_EXPAT_2_10_OR_NEWER_REQUIRED"
    assert pyexpat.EXPAT_VERSION == expat.EXPAT_VERSION == "expat_" + ".".join(map(str, pyexpat.version_info)), "ACTUAL_PARSER_VERSION_DIFFERS"
    extension = Path(pyexpat.__file__).resolve()
    executable = Path(sys._base_executable).resolve()
    assert isinstance(pyexpat.__spec__.loader, importlib.machinery.ExtensionFileLoader), "ACTUAL_NATIVE_PYEXPAT_IMPORT_REQUIRED"
    assert Path(pyexpat.__spec__.origin).resolve() == extension and extension.is_file() and executable.is_file()
    version = ".".join(map(str, sys.version_info[:3]))
    executable_sha, extension_sha = sha(executable.read_bytes()), sha(extension.read_bytes())
    assert version == os.environ["OUTLANDS_TEST_PYTHON_VERSION"], "PREPARED_PYTHON_VERSION_DIFFERS"
    assert executable_sha == os.environ["OUTLANDS_TEST_PYTHON_SHA256"], "PREPARED_PYTHON_EXECUTABLE_DIFFERS"
    assert extension_sha == os.environ["OUTLANDS_TEST_EXPAT_SHA256"], "PREPARED_PYEXPAT_EXTENSION_DIFFERS"
    return dict(python=version, expat_version=list(pyexpat.version_info),
        expat_version_text=pyexpat.EXPAT_VERSION, executable_sha256=executable_sha,
        pyexpat_sha256=extension_sha, actual_parser_import_verified=True)

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def _skip_hook(original, events, strict, fifo_code):
    def checked_skip(self, reason):
        if reason == SYMLINK_REASON:
            assert self.id() in {row["test"] for row in contract()["windows_optional_1314_skips"]}, "UNEXPECTED_NATIVE_SYMLINK_CASE"
            error = sys.exception()
            actual = os.name == "nt" and isinstance(error, OSError) and getattr(error, "winerror", None) == 1314
            events.append(dict(test=self.id(), reason=reason, policy="actual_windows_1314",
                               actual_windows_1314=actual, strict=strict))
            if strict or not actual:
                self.fail("APPLICABLE_NATIVE_SYMLINK_REQUIRED")
            return original(self, reason)
        if reason == FIFO_REASON:
            assert os.name == "nt" and self.id() == "test_svg.SvgTests.test_fifo_rejected_before_open", "UNEXPECTED_PLATFORM_SKIP"
            assert sys._getframe(1).f_code is fifo_code, "UNEXPECTED_PLATFORM_SKIP_CALLER"
            return original(self, reason)
        self.fail("UNEXPECTED_NATIVE_FIXTURE_SKIP")
    return checked_skip

def runtime_bindings(module):
    assert Path(module.s.__file__).resolve() == ROOT / "svg_inspector.py", "ORIGINAL_TEST_RUNTIME_IMPORT_DIFFERS"
    assert module.s.expat is expat and tuple(module.s.MIN_EXPAT) == (2, 10, 0), "ORIGINAL_RUNTIME_PARSER_BINDING_DIFFERS"
    assert Path(module.__file__).resolve() == TESTS / "test_svg.py", "ORIGINAL_FIXTURE_ROOT_DIFFERS"

def load_original_suite(strict=None):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_SVG_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    source_pins()
    python_pin()
    spec = importlib.util.spec_from_file_location(NAME, TESTS / (NAME + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[NAME] = module
    spec.loader.exec_module(module)
    runtime_bindings(module)
    events = []
    module.SvgTests.skipTest = _skip_hook(module.SvgTests.skipTest, events, strict,
                                        module.SvgTests.test_fifo_rejected_before_open.__code__)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    expected = contract()
    ids = [test.id() for test in flatten(suite)]
    assert len(ids) == len(set(ids)) == 59 and set(ids) == set(expected["test_ids"][NAME]), "ORIGINAL_TEST_SELECTION_DIFFERS"
    return suite, module, events

def run_originals(*, strict=None, log_stream=None):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_SVG_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    expected = contract()
    before = source_pins()
    parser = python_pin()
    suite, module, events = load_original_suite(strict)
    ids = [test.id() for test in flatten(suite)]
    additions = {"OUTLANDS_REQUIRE_SYMLINK_TEST": "1"} if strict else {}
    with mock.patch.dict(os.environ, additions):
        legacy_required = os.environ.get("OUTLANDS_REQUIRE_SYMLINK_TEST") == "1"
        result = unittest.TextTestRunner(stream=log_stream if log_stream is not None else io.StringIO(), verbosity=2).run(suite)
    runtime_bindings(module)
    assert source_pins() == before, "PRESERVED_SOURCES_CHANGED_DURING_TESTS"
    assert python_pin() == parser, "ACTUAL_PYTHON_PARSER_CHANGED_DURING_TESTS"
    skips = [dict(test=test.id(), reason=reason) for test, reason in result.skipped]
    pairs = lambda rows: {(row["test"], row["reason"]) for row in rows}
    required = pairs(expected["windows_required_skips"] if os.name == "nt" else expected["posix_required_skips"])
    allowed = set(required)
    if os.name == "nt" and not strict:
        allowed |= pairs(expected["windows_optional_1314_skips"])
    observed = pairs(skips)
    assert len(skips) == len(observed), "DUPLICATE_SKIP"
    unexpected = [row for row in skips if (row["test"], row["reason"]) not in allowed]
    missing = sorted(required-observed)
    failed = [test.id() for test, trace in result.failures+result.errors]
    good = result.wasSuccessful() and result.testsRun == 59 and not unexpected and not missing
    return dict(schema=1, status="PASS" if good else "FAIL", tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors), skipped=len(result.skipped),
        failures=len(result.failures), errors=len(result.errors), skips=skips, unexpected_skips=unexpected,
        missing_required_skips=[dict(test=t, reason=r) for t,r in missing], failed_tests=failed,
        module_counts=expected["module_counts"], test_ids=ids, native_links_required=strict,
        legacy_native_requirement_propagated=legacy_required, fixture_adapters_installed=True,
        fixture_adapter_policy="skipTest-only interceptor; original bodies execute unchanged",
        skip_adapter_events=events, runtime_imports_verified=True, original_fixture_roots_verified=True,
        runtime_mirror_required=False, runtime_mirror_test_only=False,
        runtime_sha256=expected["runtime_sha256"], baseline_runtime_sha256=expected["baseline_runtime_sha256"], runtime_unchanged_during_tests=True,
        published_test_source_sha256=expected["published_test_source_sha256"],
        original_test_bytes_unchanged=True, runtime_floor_only_change=True, full_runtime_raw_bytes_preserved=False,
        example_raw_bytes_preserved=True, original_method_bodies_preserved=True, original_methods=59, original_assertion_calls=99,
        original_test_method_assertion_calls=97, original_helper_assertion_calls=2, helper_methods=6,
        python_pin=dict(parser, bytes_unchanged=True), ast_hash_encoding="python-ast-fields-json-v2")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    assert args.report.is_absolute() and args.report.parent.is_dir()
    value = run_originals(log_stream=sys.stderr)
    with args.report.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2)+"\n")
    print(json.dumps({key:value[key] for key in ("status","tests","passed","skipped","failures","errors")}))
    raise SystemExit(0 if value["status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
