"""Run the unchanged 54-method reporter source with finite native skip decisions."""
if not __debug__:
    raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
NAME = "test_git_reporter"
SYMLINK_REASON = "Native Windows symlink privilege unavailable"
SHORT_REASON = "8.3 aliases unavailable on the selected fixture volume"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def contract():
    value = json.loads((TESTS / "SKIP-CONTRACT.json").read_text(encoding="utf-8"))
    assert (value["total_methods"], value["original_assertion_calls"], value["helper_methods"]) == (54, 64, 5)
    assert value["ast_hash_encoding"] == "python-ast-fields-json-v2"
    return value

def source_pins():
    expected = contract()
    files = dict(expected["published_test_source_sha256"], **expected["runtime_sha256"])
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in files.items()), "PRESERVED_BASE_SOURCE_PIN_DIFFERS"
    return files

def git_pin():
    expected = contract()
    executable = Path(os.environ["OUTLANDS_TEST_GIT"])
    assert executable.is_absolute() and executable.is_file() and not executable.is_symlink(), "PINNED_GIT_EXECUTABLE_REQUIRED"
    assert not getattr(executable, "is_junction", lambda: False)(), "PINNED_GIT_EXECUTABLE_REQUIRED"
    wanted = os.environ["OUTLANDS_TEST_GIT_SHA256"]
    assert re.fullmatch("[a-f0-9]{64}", wanted) and sha(executable.read_bytes()) == wanted, "PINNED_GIT_EXECUTABLE_DIFFERS"
    version = subprocess.check_output([str(executable), "--version"], stderr=subprocess.PIPE, timeout=15).decode("ascii").strip()
    assert version == os.environ["OUTLANDS_TEST_GIT_VERSION"] == expected["git_versions"][sys.platform], "PINNED_GIT_VERSION_DIFFERS"
    return dict(version=version, executable_sha256=wanted, explicit_executable=True)

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
                size, buffer, repo = values.get("size"), values.get("buffer"), values.get("repo")
                valid = (type(size) is int and 0 < size < len(buffer)
                         and os.path.normcase(buffer.value) == os.path.normcase(str(repo / ".git")))
            events.append(dict(test=self.id(), reason=reason, policy="successful_same_path_short_name_absence",
                               successful_same_path=bool(valid), strict=strict))
            if not valid:
                self.fail("SHORT_PATH_API_MUST_SUCCEED_BEFORE_CAPABILITY_SKIP")
            return original(self, reason)
        self.fail("UNEXPECTED_NATIVE_FIXTURE_SKIP")
    return checked_skip

def runtime_bindings(module):
    actual = {"reporter": Path(module.r.__file__).resolve(),
              "demo": Path(sys.modules[module.create.__module__].__file__).resolve()}
    assert actual == {"reporter": ROOT / "git_worktree_report.py", "demo": ROOT / "examples/make_demo.py"}, "ORIGINAL_TEST_RUNTIME_IMPORT_DIFFERS"
    assert sys.modules[module.create.__module__].r is module.r, "ORIGINAL_EXAMPLE_RUNTIME_IMPORT_DIFFERS"
    assert module.GIT == Path(os.environ["OUTLANDS_TEST_GIT"]).absolute(), "ORIGINAL_TEST_GIT_EXECUTABLE_DIFFERS"
    module.r.no_links(module.GIT)
    return actual

def load_original_suite(strict=None):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_GIT_REPORTER_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    source_pins()
    git_pin()
    spec = importlib.util.spec_from_file_location(NAME, TESTS / (NAME + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[NAME] = module
    spec.loader.exec_module(module)
    runtime_bindings(module)
    events = []
    short_code = module.Reporter.test_native_windows_short_alias_common_output_refused.__code__
    for fixture in (module.Reporter, module.Porcelain):
        fixture.skipTest = _skip_hook(fixture.skipTest, events, strict, short_code)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    expected = contract()
    ids = [test.id() for test in flatten(suite)]
    assert len(ids) == len(set(ids)) == 54 and set(ids) == set(expected["test_ids"][NAME]), "ORIGINAL_TEST_SELECTION_DIFFERS"
    return suite, module, events

def run_originals(*, strict=None, log_stream=None):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_GIT_REPORTER_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    expected = contract()
    before = source_pins()
    git = git_pin()
    suite, module, events = load_original_suite(strict)
    ids = [test.id() for test in flatten(suite)]
    result = unittest.TextTestRunner(stream=log_stream if log_stream is not None else io.StringIO(), verbosity=2).run(suite)
    runtime_bindings(module)
    assert source_pins() == before, "PRESERVED_SOURCES_CHANGED_DURING_TESTS"
    assert git_pin() == git, "PINNED_GIT_CHANGED_DURING_TESTS"
    skips = [dict(test=test.id(), reason=reason) for test, reason in result.skipped]
    pairs = lambda rows: {(row["test"], row["reason"]) for row in rows}
    required = pairs(expected["windows_required_skips"] if os.name == "nt" else expected["posix_required_skips"])
    allowed = set(required)
    if os.name == "nt":
        allowed |= pairs(expected["windows_short_name_absence_skips"])
        if not strict:
            allowed |= pairs(expected["windows_optional_1314_skips"])
    observed = pairs(skips)
    assert len(skips) == len(observed), "DUPLICATE_SKIP"
    unexpected = [row for row in skips if (row["test"], row["reason"]) not in allowed]
    missing = sorted(required-observed)
    failed = [test.id() for test, trace in result.failures+result.errors]
    good = result.wasSuccessful() and result.testsRun == 54 and not unexpected and not missing
    return dict(schema=1, status="PASS" if good else "FAIL", tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors), skipped=len(result.skipped),
        failures=len(result.failures), errors=len(result.errors), skips=skips, unexpected_skips=unexpected,
        missing_required_skips=[dict(test=t, reason=r) for t,r in missing], failed_tests=failed,
        module_counts=expected["module_counts"], test_ids=ids, native_links_required=strict,
        fixture_adapters_installed=True, fixture_adapter_policy="skipTest-only interceptor; original bodies execute unchanged",
        skip_adapter_events=events, runtime_imports_verified=True, original_fixture_roots_verified=True,
        runtime_mirror_required=False, runtime_mirror_test_only=False,
        runtime_sha256=expected["runtime_sha256"], runtime_unchanged_during_tests=True,
        published_test_source_sha256=expected["published_test_source_sha256"],
        original_test_bytes_unchanged=True, runtime_raw_bytes_preserved=True, example_raw_bytes_preserved=True,
        original_method_bodies_preserved=True, original_methods=54, original_assertion_calls=64,
        original_test_method_assertion_calls=60, original_helper_assertion_calls=4, helper_methods=5,
        git_pin=dict(git, executable_bytes_unchanged=True), ast_hash_encoding="python-ast-fields-json-v2")

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
