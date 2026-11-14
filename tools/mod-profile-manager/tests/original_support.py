"""Run the unchanged 118 originals, including ten real withdrawn Tk widget tests. MIT."""
if not __debug__:
    raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
import argparse
import hashlib
import importlib
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
NAMES = ("test_cli", "test_engine", "test_support", "test_gui")
MODULE_COUNTS = {"test_cli": 12, "test_engine": 65, "test_support": 18, "test_gui": 23}
SYMLINK_REASONS = {
    "test_engine.EngineTests.test_symlink_source_and_linked_parent_are_refused": "Symlink creation unavailable",
    "test_engine.EngineTests.test_symlink_payload_entry_is_refused": "Symlink creation unavailable",
    "test_support.SupportTests.test_link_and_linked_parent_rejected": "Symlink creation requires platform privileges",
}
HARDLINK_REASONS = {
    "test_engine.EngineTests.test_hardlinked_source_is_refused": "Hardlink creation unavailable",
    "test_support.SupportTests.test_duplicate_path_and_hardlink_inputs_rejected": "Hardlinks unavailable in test environment",
}
CASEFOLD_ID = "test_engine.EngineTests.test_case_colliding_files_are_refused_where_representable"
CASEFOLD_REASON = "Filesystem cannot represent distinct case-colliding names"
SYMLINK_IDS = set(SYMLINK_REASONS)
HARDLINK_IDS = set(HARDLINK_REASONS)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def contract():
    value = json.loads((TESTS / "SKIP-CONTRACT.json").read_bytes())
    assert (value["total_methods"], value["original_assertion_calls"], value["original_test_method_assertion_calls"], value["original_helper_assertion_calls"], value["helper_methods"]) == (118, 262, 230, 32, 43)
    assert value["module_counts"] == MODULE_COUNTS and value["ast_hash_encoding"] == "python-ast-fields-json-v2"
    selected = {test for tests in value["test_ids"].values() for test in tests}
    assert len(selected) == 118, "ORIGINAL_SKIP_SELECTION_DIFFERS"
    for key in ("windows_required_skips", "posix_required_skips", "windows_optional_1314_skips", "windows_optional_casefold_skips"):
        rows = value[key]
        assert len(rows) == len({(row["test"], row["reason"]) for row in rows}) == len({row["test"] for row in rows}), "ORIGINAL_SKIP_POLICY_DUPLICATES"
        assert all(row["test"] in selected for row in rows), "ORIGINAL_SKIP_POLICY_HAS_UNSELECTED_TEST"
    return value


def source_pins():
    expected = contract()
    files = dict(expected["published_test_source_sha256"], **expected["runtime_sha256"], **expected["retained_doc_source_sha256"])
    assert len(files) == 14 and all(sha((ROOT / name).read_bytes()) == digest for name, digest in files.items()), "PRESERVED_SOURCE_PIN_DIFFERS"
    return files


def python_pin():
    executable = Path(sys._base_executable).resolve()
    version = ".".join(map(str, sys.version_info[:3]))
    digest = sha(executable.read_bytes())
    assert version == os.environ["OUTLANDS_TEST_PYTHON_VERSION"] and digest == os.environ["OUTLANDS_TEST_PYTHON_SHA256"], "PREPARED_PYTHON_PIN_DIFFERS"
    return dict(python=version, executable_sha256=digest, actual_interpreter_verified=True)


def tk_attest(pin):
    spec = importlib.util.spec_from_file_location("profile_original_tk_attestation", ROOT / "packaging/verify_tk.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper.attest(pin)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


class TrackedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_ids = set()
        self.successful_ids = set()

    def startTest(self, test):
        self.started_ids.add(test.id())
        super().startTest(test)

    def addSuccess(self, test):
        self.successful_ids.add(test.id())
        super().addSuccess(test)


def _skip_hook(original, events, strict, codes):
    def checked_skip(self, reason):
        identifier = self.id()
        caller = sys._getframe(1)
        if reason in SYMLINK_REASONS.values():
            assert identifier in SYMLINK_REASONS and reason == SYMLINK_REASONS[identifier] and caller.f_code is codes[identifier], "UNEXPECTED_NATIVE_SYMLINK_CASE"
            error = sys.exception()
            actual = os.name == "nt" and isinstance(error, OSError) and getattr(error, "winerror", None) == 1314
            events.append(dict(test=identifier, reason=reason, policy="actual_windows_1314", actual_windows_1314=actual, strict=strict))
            if strict or not actual:
                self.fail("APPLICABLE_NATIVE_SYMLINK_REQUIRED")
            return original(self, reason)
        if reason in HARDLINK_REASONS.values():
            assert identifier in HARDLINK_REASONS and reason == HARDLINK_REASONS[identifier] and caller.f_code is codes[identifier], "UNEXPECTED_NATIVE_HARDLINK_CASE"
            events.append(dict(test=identifier, reason=reason, policy="hardlinks_required", strict=strict))
            self.fail("APPLICABLE_NATIVE_HARDLINK_REQUIRED")
        if reason == CASEFOLD_REASON:
            assert identifier == CASEFOLD_ID and caller.f_code is codes[identifier], "UNEXPECTED_NATIVE_CASEFOLD_CASE"
            first, other = caller.f_locals["first"], caller.f_locals["other"]
            left, right = first.stat(), other.stat()
            actual = os.name == "nt" and os.path.samefile(first, other) and (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)
            events.append(dict(test=identifier, reason=reason, policy="actual_windows_casefold_alias", actual_casefold_alias=actual, strict=strict))
            if not actual:
                self.fail("APPLICABLE_CASE_COLLISION_FIXTURE_REQUIRED")
            return original(self, reason)
        self.fail("UNEXPECTED_NATIVE_FIXTURE_SKIP")
    return checked_skip


def runtime_bindings(modules, root=ROOT):
    for name, module in modules.items():
        assert Path(module.__file__).resolve() == root / "tests" / (name + ".py"), "ORIGINAL_FIXTURE_ROOT_DIFFERS"
    loaded = {name: importlib.import_module(name) for name in ("profile_manager", "profile_engine", "profile_fs", "profile_gui", "inspection_support", "examples.generate")}
    for name, module in loaded.items():
        relative = "examples/generate.py" if name == "examples.generate" else name + ".py"
        assert Path(module.__file__).resolve() == root / relative, "ORIGINAL_RUNTIME_IMPORT_DIFFERS"
    engine, fs, support = loaded["profile_engine"], loaded["profile_fs"], loaded["inspection_support"]
    assert modules["test_cli"].ROOT == root and modules["test_engine"].engine is engine and modules["test_engine"].fs is fs
    assert modules["test_gui"].gui is loaded["profile_gui"] and modules["test_support"].support is support
    assert engine.fs is fs and engine.ProfileError is fs.ProfileError, "ENGINE_FILESYSTEM_ALIAS_DIFFERS"
    assert all(getattr(fs, name) is getattr(support, name) for name in ("TextError", "canonical_directory", "identity", "linked", "local_path", "no_links", "strict_json")), "FILESYSTEM_SUPPORT_ALIAS_DIFFERS"
    generator = loaded["examples.generate"]
    assert all(getattr(generator, name) is getattr(support, name) for name in ("Parser", "TextError", "canonical_directory", "cli_error", "local_path", "no_links", "require")), "GENERATOR_SUPPORT_ALIAS_DIFFERS"


def selected_strict(strict):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_PROFILE_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    return strict


def load_original_suite(strict=None):
    assert os.environ.get("PROFILE_MANAGER_REQUIRE_TK") == "1", "ALL_TEN_NATIVE_TK_TESTS_REQUIRED"
    strict = selected_strict(strict)
    source_pins(); python_pin()
    sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(TESTS))
    modules = {}; suite = unittest.TestSuite()
    for name in NAMES:
        spec = importlib.util.spec_from_file_location(name, TESTS / (name + ".py"))
        module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); modules[name] = module
    events = []
    ids = set(SYMLINK_REASONS) | set(HARDLINK_REASONS) | {CASEFOLD_ID}
    codes = {identifier: getattr(getattr(modules[identifier.split(".")[0]], identifier.split(".")[1]), identifier.split(".")[2]).__code__ for identifier in ids}
    for cls in (modules["test_cli"].CliTests, modules["test_engine"].EngineTests, modules["test_support"].SupportTests, modules["test_gui"].ControllerTests, modules["test_gui"].TkWidgetTests):
        cls.skipTest = _skip_hook(cls.skipTest, events, strict, codes)
    runtime_bindings(modules)
    expected = contract()
    for name, module in modules.items():
        selected = unittest.defaultTestLoader.loadTestsFromModule(module)
        selected_ids = [test.id() for test in flatten(selected)]
        assert len(selected_ids) == len(set(selected_ids)) == MODULE_COUNTS[name] and set(selected_ids) == set(expected["test_ids"][name]), "ORIGINAL_TEST_SELECTION_DIFFERS"
        suite.addTests(selected)
    assert len(list(flatten(suite))) == 118
    return suite, modules, events


def run_originals(*, strict=None, log_stream=None):
    strict = selected_strict(strict)
    expected = contract(); before = source_pins(); interpreter = python_pin(); tk_before = tk_attest(interpreter)
    suite, modules, events = load_original_suite(strict)
    ids = [test.id() for test in flatten(suite)]
    tk_ids = {identifier for identifier in ids if identifier.startswith("test_gui.TkWidgetTests.")}
    assert len(tk_ids) == 10 and len(set(ids) - tk_ids) == 108
    result = unittest.TextTestRunner(stream=log_stream if log_stream is not None else io.StringIO(), verbosity=2, resultclass=TrackedResult).run(suite)
    runtime_bindings(modules)
    tk_after = tk_attest(interpreter)
    assert tk_before == tk_after, "TK_RESOURCES_CHANGED_DURING_ORIGINAL_TESTS"
    assert source_pins() == before and python_pin() == interpreter, "PRESERVED_SOURCES_OR_INTERPRETER_CHANGED"
    skips = [dict(test=test.id(), reason=reason) for test, reason in result.skipped]
    pairs = lambda rows: {(row["test"], row["reason"]) for row in rows}
    required = pairs(expected["windows_required_skips"] if os.name == "nt" else expected["posix_required_skips"])
    optional = pairs(expected["windows_optional_casefold_skips"]) if os.name == "nt" else set()
    if os.name == "nt" and not strict:
        optional |= pairs(expected["windows_optional_1314_skips"])
    observed = pairs(skips); assert len(observed) == len(skips), "DUPLICATE_SKIP"
    unexpected = [row for row in skips if (row["test"], row["reason"]) not in required | optional]
    missing = sorted(required - observed)
    failed_ids = sorted({getattr(test, "test_case", test).id() for test, trace in result.failures + result.errors})
    tk_skipped = sum(row["test"] in tk_ids for row in skips)
    successful = result.successful_ids
    started = result.started_ids
    tk_passed = len(successful & tk_ids)
    good = result.wasSuccessful() and result.testsRun == 118 and not unexpected and not missing and tk_skipped == 0 and tk_passed == 10
    return dict(schema=1, status="PASS" if good else "FAIL", tests=result.testsRun,
        passed=len(successful), skipped=len(skips), failures=len(result.failures), errors=len(result.errors),
        skips=skips, unexpected_skips=unexpected, missing_required_skips=[dict(test=test, reason=reason) for test, reason in missing], failed_tests=failed_ids,
        module_counts=MODULE_COUNTS, test_ids=ids, started_test_ids=sorted(started), successful_test_ids=sorted(successful), native_links_required=strict,
        nonwidget_tests=108, nonwidget_started=len(started - tk_ids), nonwidget_passed=len(successful - tk_ids), nonwidget_skipped=len(skips)-tk_skipped,
        native_tk_tests=10, native_tk_started=len(started & tk_ids), native_tk_passed=tk_passed, native_tk_skipped=tk_skipped, native_tk_test_ids=sorted(tk_ids),
        tk_attestation=tk_before, tk_attestation_before_after_identical=True, native_tk_widgets_checked=good,
        fictional_workspace_flow_checked=good, native_lock_and_rename_checked=good,
        fixture_adapters_installed=True, fixture_adapter_policy="skipTest-only; actual Win1314 local symlinks; hardlinks mandatory; actual Windows case alias separately recorded",
        skip_adapter_events=events, runtime_imports_verified=True, original_fixture_roots_verified=True, runtime_mirror_required=False, runtime_mirror_test_only=False,
        runtime_sha256=expected["runtime_sha256"], baseline_runtime_sha256=expected["baseline_runtime_sha256"], runtime_unchanged_during_tests=True,
        published_test_source_sha256=expected["published_test_source_sha256"], original_test_bytes_unchanged=True,
        retained_doc_source_sha256=expected["retained_doc_source_sha256"], retained_doc_bytes_preserved=True,
        full_runtime_raw_bytes_preserved=True, example_raw_bytes_preserved=True, original_method_bodies_preserved=True,
        original_methods=118, original_assertion_calls=262, original_test_method_assertion_calls=230, original_helper_assertion_calls=32, helper_methods=43,
        python_pin=dict(interpreter, bytes_unchanged=True), ast_hash_encoding="python-ast-fields-json-v2",
        real_game_files_used=False, real_mod_profiles_used=False, game_integrations_verified=False, gameplay_verified=False, saves_accessed=False,
        external_game_directories_modified=False, power_loss_durability_verified=False, full_metadata_preservation_verified=False)


def run(report_path, *, strict_links=None, log_stream=None):
    assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions()), "FRESH_NO_PIP_ENVIRONMENT_REQUIRED"
    value = run_originals(strict=strict_links, log_stream=log_stream)
    value.update(fresh_venv=True, runtime_dependencies=0)
    path = Path(report_path)
    assert path.is_absolute() and path.parent.is_dir()
    with path.open("x", encoding="utf-8", newline="\n") as out:
        out.write(json.dumps(value, indent=2) + "\n")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--strict-links", action="store_true", default=None)
    args = parser.parse_args()
    value = run(args.report, strict_links=args.strict_links, log_stream=sys.stderr)
    print(json.dumps({key: value[key] for key in ("status", "tests", "passed", "skipped", "failures", "errors", "native_tk_tests", "native_tk_passed", "native_tk_skipped")}))
    raise SystemExit(0 if value["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
