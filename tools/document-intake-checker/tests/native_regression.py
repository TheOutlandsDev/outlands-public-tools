"""Run all unchanged Document Intake Checker originals with mandatory native fixtures."""
if not __debug__: raise RuntimeError("OPTIMIZED_PYTHON_UNSUPPORTED")
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
NAMES = ("test_docx_core", "test_intake", "test_boundaries")
FIXTURE_IDS = {
    "test_boundaries.Files.test_native_hardlink_input_refused": "hardlink",
    "test_boundaries.Files.test_native_linked_parent_read_and_write_refused": "windows_junction" if os.name == "nt" else "posix_parent_symlink",
    "test_boundaries.Files.test_posix_leaf_symlink_refused": "posix_leaf_symlink",
}
NATIVE_SKIP_REASON = "Native link fixture unavailable on selected local volume"
FLAGS = ("real_documents_used", "document_properties_exported", "external_resources_followed", "document_executed", "office_processes_started", "archives_extracted", "visible_layout_verified", "general_word_compatibility_verified", "production_workflows_verified")

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def contract():
    value = json.loads((TESTS / "SKIP-CONTRACT.json").read_text(encoding="utf-8"))
    assert (value["total_methods"], value["original_assertion_calls"], value["original_test_method_assertion_calls"], value["original_helper_assertion_calls"], value["helper_methods"]) == (53, 85, 85, 0, 3)
    assert value["module_counts"] == {"test_docx_core": 23, "test_intake": 8, "test_boundaries": 22}
    assert value["class_counts"] == {"Docx": 23, "Intake": 8, "Buffers": 8, "Files": 14}
    assert value["ast_hash_encoding"] == "python-ast-fields-json-v2"
    selected = {test for tests in value["test_ids"].values() for test in tests}
    assert len(selected) == 53, "ORIGINAL_SKIP_SELECTION_DIFFERS"
    for key in ("windows_required_skips", "posix_required_skips", "windows_optional_1314_skips"):
        rows = value[key]
        assert len(rows) == len({(row["test"], row["reason"]) for row in rows}) == len({row["test"] for row in rows}), "ORIGINAL_SKIP_POLICY_DUPLICATES"
        assert all(row["test"] in selected for row in rows), "ORIGINAL_SKIP_POLICY_HAS_UNSELECTED_TEST"
    assert value["windows_required_skips"] == [dict(test="test_boundaries.Files.test_posix_leaf_symlink_refused", reason="POSIX-only leaf symlink fixture")]
    assert value["posix_required_skips"] == [dict(test="test_boundaries.Files.test_windows_ambiguous_paths_refused", reason="Windows-only path grammar fixtures")]
    assert value["windows_optional_1314_skips"] == [], "OPTIONAL_NATIVE_FIXTURE_SKIPS_FORBIDDEN"
    assert set(value["runtime_definitions"]) == set(value["runtime_sha256"]) == {"docx_core.py", "document_intake.py", "intake.py", "toolkit.py", "fictional_docx.py", "native_windows.py"}
    assert sum(map(len, value["runtime_definitions"].values())) == 65
    assert value["runtime_sha256"]["native_windows.py"] == "db7d61707e7218ebf7601e92d441f4cda8cb84fde7d566edc4561aa2be57def7"
    assert value["baseline_runtime_sha256"]["native_windows.py"] == "7aa8507dfcfcdba008642d53c9ba6453fd171a3e15327e7f1af7e8d8efc84537"
    assert all(value["runtime_sha256"][name] == value["baseline_runtime_sha256"][name] for name in value["runtime_sha256"] if name != "native_windows.py")
    exception = value["runtime_source_exception"]
    assert exception["path"] == "native_windows.py" and exception["changed_definitions"] == ["exclusive_write"]
    assert exception["baseline_sha256"] == value["baseline_runtime_sha256"]["native_windows.py"] and exception["qualified_sha256"] == value["runtime_sha256"]["native_windows.py"]
    assert value["full_runtime_raw_bytes_preserved"] is False and value["five_unmodified_runtime_files_preserved"] is value["native_backend_change_verified"] is True
    return value

def source_pins():
    expected = contract()
    files = dict(expected["published_test_source_sha256"], **expected["runtime_sha256"], **expected["retained_doc_source_sha256"], **expected["original_fixture_source_sha256"])
    assert len(files) == 13 and all(sha((ROOT/name).read_bytes()) == digest for name, digest in files.items()), "PRESERVED_SOURCE_PIN_DIFFERS"
    return files

def python_pin():
    executable = Path(sys._base_executable).resolve()
    version = ".".join(map(str, sys.version_info[:3])); digest = sha(executable.read_bytes())
    assert version == os.environ["OUTLANDS_TEST_PYTHON_VERSION"], "PREPARED_PYTHON_VERSION_DIFFERS"
    assert digest == os.environ["OUTLANDS_TEST_PYTHON_SHA256"], "PREPARED_PYTHON_EXECUTABLE_DIFFERS"
    return dict(python=version, executable_sha256=digest, actual_interpreter_verified=True)

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite): yield from flatten(item)
        else: yield item

def _skip_hook(original, events, fixture_code):
    def checked_skip(self, reason):
        caller = sys._getframe(1).f_code
        assert self.id() in FIXTURE_IDS and reason == NATIVE_SKIP_REASON and caller is fixture_code, "UNEXPECTED_NATIVE_FIXTURE_SKIP"
        error = sys.exception()
        assert isinstance(error, (OSError, NotImplementedError)), "NATIVE_FIXTURE_EXCEPTION_REQUIRED"
        events.append(dict(test=self.id(), reason=reason, policy="applicable_native_fixture_mandatory", operation=FIXTURE_IDS[self.id()], actual_exception_type=type(error).__name__, winerror=getattr(error, "winerror", None)))
        self.fail("APPLICABLE_NATIVE_FIXTURE_REQUIRED")
    return checked_skip

def runtime_bindings(modules):
    for name, module in modules.items():
        assert Path(module.__file__).resolve() == TESTS/(name+".py"), "ORIGINAL_FIXTURE_ROOT_DIFFERS"
    expected = contract(); loaded = {}
    for filename, names in expected["runtime_definitions"].items():
        module = importlib.import_module(Path(filename).stem); loaded[Path(filename).stem] = module
        assert Path(module.__file__).resolve() == ROOT/filename, "ORIGINAL_RUNTIME_IMPORT_DIFFERS"
        for name in names:
            obj = getattr(module, name)
            assert obj.__module__ == module.__name__ and sys.modules[obj.__module__] is module, "RUNTIME_DEFINITION_IMPORT_DIFFERS"
    core=loaded["docx_core"];tables=loaded["document_intake"];typed=loaded["intake"];generator=loaded["fictional_docx"];shared=loaded["toolkit"]
    assert modules["test_docx_core"].d is core and modules["test_intake"].a is tables, "ORIGINAL_RUNTIME_ALIAS_DIFFERS"
    assert modules["test_docx_core"].f is modules["test_intake"].f is generator, "ORIGINAL_GENERATOR_ALIAS_DIFFERS"
    assert modules["test_docx_core"].t is modules["test_intake"].t is modules["test_boundaries"].t is core.t is tables.t is generator.t is shared, "SHARED_RUNTIME_ALIAS_DIFFERS"
    assert tables.docx_core is core and tables.intake is typed and typed.t is shared, "DOCX_INTAKE_CORE_ALIAS_DIFFERS"
    assert modules["test_intake"].MAPPING == (ROOT/"examples/mapping.json").read_bytes(), "ORIGINAL_MAPPING_FIXTURE_DIFFERS"
    assert core.zlib is importlib.import_module("zlib") and core.zipfile is generator.zipfile is typed.zipfile is importlib.import_module("zipfile"), "SELECTED_STDLIB_ALIAS_DIFFERS"
    assert shared.ET is importlib.import_module("xml.etree.ElementTree"), "SELECTED_XML_ALIAS_DIFFERS"
    accelerator=importlib.import_module("_elementtree")
    assert shared.ET.XMLParser is accelerator.XMLParser and shared.ET.TreeBuilder is accelerator.TreeBuilder, "EXPECTED_XML_ACCELERATOR_REQUIRED"


def selected_strict(strict):
    if strict is None: strict = os.name != "nt" or os.environ.get("OUTLANDS_DOCUMENT_INTAKE_REQUIRE_LINKS") == "1"
    assert type(strict) is bool
    return strict

def load_original_suite(strict=None):
    selected_strict(strict); source_pins(); python_pin()
    sys.path[:0] = [str(ROOT), str(TESTS)]
    modules = {}; suite = unittest.TestSuite(); events = []
    for name in NAMES:
        spec = importlib.util.spec_from_file_location(name, TESTS/(name+".py"))
        module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); modules[name] = module
    boundary = modules["test_boundaries"]
    for cls in (modules["test_docx_core"].Docx, modules["test_intake"].Intake, boundary.Buffers, boundary.Files):
        cls.skipTest = _skip_hook(cls.skipTest, events, boundary.Files.fixture.__code__)
    runtime_bindings(modules); expected = contract()
    for name, module in modules.items():
        selected = unittest.defaultTestLoader.loadTestsFromModule(module)
        ids = [test.id() for test in flatten(selected)]
        assert len(ids) == len(set(ids)) == expected["module_counts"][name] and set(ids) == set(expected["test_ids"][name]), "ORIGINAL_TEST_SELECTION_DIFFERS"
        suite.addTests(selected)
    assert len(list(flatten(suite))) == 53
    return suite, modules, events

class TrackingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.started_ids = []; self.successful_ids = []
    def startTest(self, test):
        self.started_ids.append(test.id()); super().startTest(test)
    def addSuccess(self, test):
        self.successful_ids.append(test.id()); super().addSuccess(test)

def run_originals(*, strict=None, log_stream=None):
    strict = selected_strict(strict); expected = contract(); before = source_pins(); interpreter = python_pin()
    suite, modules, events = load_original_suite(strict)
    ids = [test.id() for test in flatten(suite)]
    result = unittest.TextTestRunner(stream=log_stream if log_stream is not None else io.StringIO(), verbosity=2, resultclass=TrackingResult).run(suite)
    runtime_bindings(modules)
    assert source_pins() == before, "PRESERVED_SOURCES_CHANGED_DURING_TESTS"
    assert python_pin() == interpreter, "ACTUAL_PYTHON_CHANGED_DURING_TESTS"
    skips = [dict(test=test.id(), reason=reason) for test, reason in result.skipped]
    pairs = lambda rows: {(row["test"],row["reason"]) for row in rows}
    required = pairs(expected["windows_required_skips"] if os.name == "nt" else expected["posix_required_skips"])
    observed = pairs(skips)
    assert len(skips) == len(observed), "DUPLICATE_SKIP"
    unexpected = [row for row in skips if (row["test"],row["reason"]) not in required]; missing = sorted(required-observed)
    started = result.started_ids; successful = result.successful_ids
    all_started = len(started) == len(set(started)) == 53 and set(started) == set(ids)
    all_finished = len(successful) == len(set(successful)) == 52 and set(successful) == set(ids)-{row["test"] for row in skips}
    good = result.wasSuccessful() and result.testsRun == 53 and all_started and all_finished and not unexpected and not missing and not events
    fictional_ids = {"test_intake.Intake.test_fictional_typed_rows_duplicate_accounting_and_provenance", "test_intake.Intake.test_conflicts_withhold_entire_identity_group", "test_intake.Intake.test_invalid_row_payload_is_not_retained"}
    guard_ids = {test for test in ids if test.startswith("test_boundaries.Files.")} - {test for test,reason in required}
    return dict(schema=1, status="PASS" if good else "FAIL", tests=result.testsRun, passed=len(successful), skipped=len(skips), failures=len(result.failures), errors=len(result.errors), skips=skips, unexpected_skips=unexpected, missing_required_skips=[dict(test=test,reason=reason) for test,reason in missing], failed_tests=[test.id() for test,trace in result.failures+result.errors], module_counts=expected["module_counts"], test_ids=ids, started_test_ids=started, successful_test_ids=successful, all_selected_tests_started=all_started, successful_ids_exclude_setup_failures=True, native_links_required=strict, native_fixtures_mandatory=True, fixture_adapters_installed=True, fixture_adapter_policy="skipTest-only fail-closed interceptor; applicable hardlinks and junctions/symlinks mandatory", skip_adapter_events=events, runtime_imports_verified=True, original_fixture_roots_verified=True, runtime_mirror_required=False, runtime_mirror_test_only=False, runtime_sha256=expected["runtime_sha256"], baseline_runtime_sha256=expected["baseline_runtime_sha256"], runtime_unchanged_during_tests=True, published_test_source_sha256=expected["published_test_source_sha256"], original_test_bytes_unchanged=True, retained_doc_source_sha256=expected["retained_doc_source_sha256"], retained_doc_bytes_preserved=True, original_fixture_source_sha256=expected["original_fixture_source_sha256"], original_fixture_bytes_preserved=True, full_runtime_raw_bytes_preserved=False, five_unmodified_runtime_files_preserved=True, native_backend_change_verified=True, runtime_source_exception=expected["runtime_source_exception"], example_raw_bytes_preserved=True, original_method_bodies_preserved=True, original_methods=53, original_assertion_calls=85, original_test_method_assertion_calls=85, original_helper_assertion_calls=0, helper_methods=3, python_pin=dict(interpreter,bytes_unchanged=True), ast_hash_encoding="python-ast-fields-json-v2", fictional_document_intake_flow_checked=fictional_ids <= set(successful), native_file_guards_checked=guard_ids <= set(successful), positive_asserted_test_ids=dict(fictional_document_intake_flow_checked=sorted(fictional_ids),native_file_guards_checked=sorted(guard_ids)), **{key:False for key in FLAGS})

def run(report_path, *, strict_links=None, log_stream=None):
    assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions()), "FRESH_NO_PIP_ENVIRONMENT_REQUIRED"
    value = run_originals(strict=strict_links, log_stream=log_stream)
    value.update(fresh_venv=True, runtime_dependencies=0, runtime_distributions=0)
    path=Path(report_path); assert path.is_absolute() and path.parent.is_dir()
    with path.open("x",encoding="utf-8",newline="\n") as handle: handle.write(json.dumps(value,indent=2)+"\n")
    return value

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--report",required=True,type=Path); parser.add_argument("--strict-links",action="store_true",default=None); args=parser.parse_args()
    value=run(args.report,strict_links=args.strict_links,log_stream=sys.stderr)
    print(json.dumps({key:value[key] for key in ("status","tests","passed","skipped","failures","errors")}))
    raise SystemExit(0 if value["status"] == "PASS" else 1)

if __name__ == "__main__": main()
