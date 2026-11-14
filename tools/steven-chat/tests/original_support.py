"""Run the unchanged Steven Chat originals with finite, actual native-fixture skip rules."""
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
NAMES=('test_cli', 'test_client', 'test_sessions')
SYMLINK_REASONS={'test_sessions.SessionTests.test_symlink_input_and_output_refused': 'Creating symlinks is unavailable for this test account', 'test_sessions.SessionTests.test_symlink_parent_input_and_output_refused': 'Creating symlinks is unavailable for this test account'}
SYMLINK_IDS = set(SYMLINK_REASONS)
HARDLINK_REASONS={}
HARDLINK_IDS = set(HARDLINK_REASONS)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def contract():
    value = json.loads((TESTS / "SKIP-CONTRACT.json").read_text(encoding="utf-8"))
    assert (value["total_methods"], value["original_assertion_calls"], value["helper_methods"]) == (75, 137, 6)
    assert value["module_counts"] == {"test_cli":17,"test_client":31,"test_sessions":27}
    assert value["ast_hash_encoding"] == "python-ast-fields-json-v2"
    selected = {test for tests in value["test_ids"].values() for test in tests}
    assert len(selected) == 75, "ORIGINAL_SKIP_SELECTION_DIFFERS"
    for key in ("windows_required_skips", "posix_required_skips", "windows_optional_1314_skips"):
        rows = value[key]
        assert len(rows) == len({(row["test"], row["reason"]) for row in rows}) == len({row["test"] for row in rows}), "ORIGINAL_SKIP_POLICY_DUPLICATES"
        assert all(row["test"] in selected for row in rows), "ORIGINAL_SKIP_POLICY_HAS_UNSELECTED_TEST"
    return value


def source_pins():
    expected = contract()
    files = dict(expected["published_test_source_sha256"], **expected["runtime_sha256"], **expected["fixture_source_sha256"], **expected["retained_doc_source_sha256"])
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


def _skip_hook(original, events, strict, symlink_codes, hardlink_codes):
    def checked_skip(self, reason):
        caller = sys._getframe(1).f_code
        if reason in SYMLINK_REASONS.values():
            assert self.id() in SYMLINK_IDS and reason == SYMLINK_REASONS[self.id()] and caller is symlink_codes[self.id()], "UNEXPECTED_NATIVE_SYMLINK_CASE"
            error = sys.exception()
            actual = os.name == "nt" and isinstance(error, OSError) and getattr(error, "winerror", None) == 1314
            events.append(dict(test=self.id(), reason=reason, policy="actual_windows_1314",
                               actual_windows_1314=actual, strict=strict))
            if strict or not actual:
                self.fail("APPLICABLE_NATIVE_SYMLINK_REQUIRED")
            return original(self, reason)
        if reason in HARDLINK_REASONS.values():
            assert self.id() in HARDLINK_IDS and reason == HARDLINK_REASONS[self.id()] and caller is hardlink_codes[self.id()], "UNEXPECTED_NATIVE_HARDLINK_CASE"
            events.append(dict(test=self.id(), reason=reason, policy="hardlinks_required", strict=strict))
            self.fail("APPLICABLE_NATIVE_HARDLINK_REQUIRED")
        self.fail("UNEXPECTED_NATIVE_FIXTURE_SKIP")
    return checked_skip


def runtime_bindings(modules, root=ROOT):
    tests = root / "tests"
    for name, module in modules.items():
        assert Path(module.__file__).resolve() == tests / (name + ".py"), "ORIGINAL_FIXTURE_ROOT_DIFFERS"
    package = importlib.import_module("steven")
    core = importlib.import_module("steven.core")
    cli = importlib.import_module("steven.cli")
    fixture = importlib.import_module("http_fixture")
    for module, name in ((package, "steven/__init__.py"), (core, "steven/core.py"), (cli, "steven/cli.py"), (fixture, "tests/http_fixture.py")):
        assert Path(module.__file__).resolve() == root / name, "ORIGINAL_RUNTIME_IMPORT_DIFFERS"
    assert package.__version__ == "1.0.0", "PRESERVED_RUNTIME_VERSION_DIFFERS"
    assert set(package.__all__) == {"ChatError", "Conversation", "OllamaClient", "canonical_endpoint", "load_session", "safe_text", "save_session", "validate_model"}
    assert all(getattr(package, name) is getattr(core, name) for name in package.__all__), "PUBLIC_PACKAGE_ALIAS_DIFFERS"
    assert all(getattr(cli, name) is getattr(core, name) for name in ("ChatError", "Conversation", "OllamaClient", "load_session", "safe_text", "save_session")), "CLI_CORE_ALIAS_DIFFERS"
    assert all(getattr(modules["test_client"], name) is getattr(core, name) for name in ("ChatError", "OllamaClient", "canonical_endpoint", "safe_text", "validate_model")), "ORIGINAL_CLIENT_ALIAS_DIFFERS"
    assert all(getattr(modules["test_sessions"], name) is getattr(core, name) for name in ("ChatError", "Conversation", "load_session", "save_session")), "ORIGINAL_SESSION_ALIAS_DIFFERS"
    for name in ("test_cli", "test_client"):
        assert all(getattr(modules[name], item) is getattr(fixture, item) for item in ("http_fixture", "chat_reply")), "ORIGINAL_HTTP_FIXTURE_ALIAS_DIFFERS"
    assert modules["test_cli"].ROOT == root, "ORIGINAL_CLI_WORKING_ROOT_DIFFERS"
    for name in ("main.py", "chatbot.py", "stephen.py"):
        spec = importlib.util.spec_from_file_location("steven_original_" + Path(name).stem, root / name)
        wrapper = importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
        assert Path(wrapper.__file__).resolve() == root / name and wrapper.main is cli.main, "ORIGINAL_WRAPPER_MAIN_DIFFERS"
    assert (Path(package.__file__).resolve().parent / "__main__.py") == root / "steven/__main__.py", "ORIGINAL_PACKAGE_ENTRY_ROOT_DIFFERS"


def selected_strict(strict):
    if strict is None:
        strict = os.name != "nt" or os.environ.get("OUTLANDS_STEVEN_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    return strict


def load_original_suite(strict=None):
    strict = selected_strict(strict)
    source_pins(); python_pin()
    sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(TESTS))
    modules = {}; suite = unittest.TestSuite(); events = []
    for name in NAMES:
        spec = importlib.util.spec_from_file_location(name, TESTS / (name + ".py"))
        module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); modules[name] = module
    sessions = modules["test_sessions"]
    symlinks = {"test_sessions.SessionTests." + name: getattr(sessions.SessionTests, name).__code__ for name in ("test_symlink_input_and_output_refused", "test_symlink_parent_input_and_output_refused")}
    for cls in (modules["test_cli"].CliTests, modules["test_client"].EndpointTests, modules["test_client"].HttpTests, sessions.ConversationTests, sessions.SessionTests):
        cls.skipTest = _skip_hook(cls.skipTest, events, strict, symlinks, {})
    runtime_bindings(modules)
    expected = contract()
    for name, module in modules.items():
        selected = unittest.defaultTestLoader.loadTestsFromModule(module); ids = [test.id() for test in flatten(selected)]
        assert len(ids) == len(set(ids)) == expected["module_counts"][name] and set(ids) == set(expected["test_ids"][name]), "ORIGINAL_TEST_SELECTION_DIFFERS"
        suite.addTests(selected)
    assert len(list(flatten(suite))) == 75
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
    good = result.wasSuccessful() and result.testsRun == 75 and not unexpected and not missing
    return dict(schema=1, status="PASS" if good else "FAIL", tests=result.testsRun,
        passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors), skipped=len(result.skipped),
        failures=len(result.failures), errors=len(result.errors), skips=skips, unexpected_skips=unexpected,
        missing_required_skips=[dict(test=test, reason=reason) for test,reason in missing],
        failed_tests=[test.id() for test,trace in result.failures+result.errors],
        module_counts=expected["module_counts"], test_ids=ids, native_links_required=strict,
        fixture_adapters_installed=True, fixture_adapter_policy="skipTest-only interceptor; actual Win1314 local symlinks only; applicable symlinks mandatory",
        skip_adapter_events=events, runtime_imports_verified=True, original_fixture_roots_verified=True,
        runtime_mirror_required=False, runtime_mirror_test_only=False,
        runtime_sha256=expected["runtime_sha256"], baseline_runtime_sha256=expected["baseline_runtime_sha256"], runtime_unchanged_during_tests=True,
        fixture_source_sha256=expected["fixture_source_sha256"], offline_demo_checked=True, loopback_fixture_used=True,
        published_test_source_sha256=expected["published_test_source_sha256"], original_test_bytes_unchanged=True,
        retained_doc_source_sha256=expected["retained_doc_source_sha256"], retained_doc_bytes_preserved=True,
        full_runtime_raw_bytes_preserved=True, fixture_raw_bytes_preserved=True, original_method_bodies_preserved=True,
        original_methods=75, original_assertion_calls=137, original_test_method_assertion_calls=137, original_helper_assertion_calls=0, helper_methods=6,
        python_pin=dict(interpreter, bytes_unchanged=True), ast_hash_encoding="python-ast-fields-json-v2",
        actual_ollama_used=False, real_model_inference_verified=False, model_quality_verified=False, gpu_compatibility_verified=False, backend_cloud_isolation_verified=False, models_downloaded=False, ollama_servers_installed_or_started=False, real_conversations_used=False)


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
