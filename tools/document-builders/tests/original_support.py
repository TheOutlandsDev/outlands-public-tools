"""Run all untouched original tests with strict, test-only skip decisions.

The two historical test files remain byte-identical. Only their classes'
inherited skipTest hook is intercepted; original methods and helpers execute.
The hook validates the active native exception or original short-path helper
locals before allowing the finite documented local/capability skips.
"""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')

import argparse
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
NAMES = ('test_markdown_docx', 'test_docx_windows')
SYMLINK_REASONS = {
    'This environment does not permit synthetic symlinks',
    'Native symlink privilege unavailable',
}
SHORT_REASON = 'Native alternate short spelling unavailable'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def contract():
    value = json.loads((TESTS / 'SKIP-CONTRACT.json').read_text(encoding='utf-8'))
    assert value['total_methods'] == 72 and value['original_assertion_calls'] == 187
    assert value['helper_methods'] == 10 and value['ast_hash_encoding'] == 'python-ast-fields-json-v2'
    return value

def source_pins():
    expected = contract()
    files = dict(expected['original_test_source_sha256'], **expected['runtime_sha256'])
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in files.items()), 'ORIGINAL_SOURCE_PIN_DIFFERS'
    return files

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def _skip_hook(original, events, strict, short_code=None):
    def checked_skip(self, reason):
        test_id = self.id()
        if reason in SYMLINK_REASONS:
            error = sys.exception()
            actual = os.name == 'nt' and isinstance(error, OSError) and getattr(error, 'winerror', None) == 1314
            events.append(dict(test=test_id, reason=reason, policy='actual_windows_1314',
                               actual_windows_1314=actual, strict=strict))
            if strict or not actual:
                self.fail('APPLICABLE_NATIVE_SYMLINK_REQUIRED')
            return original(self, reason)
        if reason == SHORT_REASON:
            caller = sys._getframe(1)
            values = caller.f_locals
            valid = caller.f_code is short_code
            if valid:
                size, output, path = values.get('size'), values.get('output'), values.get('path')
                valid = (type(size) is int and 0 < size < len(output)
                         and output.value.casefold() == str(path).casefold())
            events.append(dict(test=test_id, reason=reason, policy='successful_same_path_short_name_absence',
                               successful_same_path=bool(valid), strict=strict))
            if not valid:
                self.fail('SHORT_PATH_API_MUST_SUCCEED_BEFORE_CAPABILITY_SKIP')
            return original(self, reason)
        self.fail('UNEXPECTED_NATIVE_FIXTURE_SKIP')
    return checked_skip

def runtime_bindings(modules):
    regression, native = (modules[name] for name in NAMES)
    actual = {
        'regression_builder': Path(regression.builder.__file__).resolve(),
        'native_builder': Path(native.tool.__file__).resolve(),
        'native_windows_backend': Path(native.win.__file__).resolve(),
        'regression_windows_backend': Path(regression.builder.windows_backend().__file__).resolve(),
    }
    assert actual == {
        'regression_builder': ROOT / 'markdown_docx.py',
        'native_builder': ROOT / 'markdown_docx.py',
        'native_windows_backend': ROOT / 'docx_windows.py',
        'regression_windows_backend': ROOT / 'docx_windows.py',
    }, 'ORIGINAL_TEST_RUNTIME_IMPORT_DIFFERS'
    assert regression.ROOT == native.HERE == ROOT, 'ORIGINAL_FIXTURE_ROOT_DIFFERS'
    assert regression.builder._DOCX_AVAILABLE and native.tool._DOCX_AVAILABLE, 'DECLARED_DOCUMENT_DEPENDENCIES_REQUIRED'
    return actual

def load_original_suite(strict=None):
    if strict is None:
        strict = os.environ.get('OUTLANDS_DOCX_REQUIRE_NATIVE_LINKS') == '1'
    assert type(strict) is bool
    source_pins()
    location = str(ROOT)
    if location not in sys.path:
        sys.path.insert(0, location)
    modules = {}
    for name in NAMES:
        spec = importlib.util.spec_from_file_location(name, TESTS / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules[name] = module
    runtime_bindings(modules)
    events = []
    regression = modules['test_markdown_docx'].DocumentBuilderTests
    native = modules['test_docx_windows'].NativeWindowsTests
    regression.skipTest = _skip_hook(regression.skipTest, events, strict)
    native.skipTest = _skip_hook(native.skipTest, events, strict, native.short_path.__code__)
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(modules[name]) for name in NAMES)
    expected = contract()
    tests = list(flatten(suite))
    ids = [test.id() for test in tests]
    wanted = [test_id for name in NAMES for test_id in expected['test_ids'][name]]
    assert len(ids) == len(set(ids)) == 72 and set(ids) == set(wanted), 'ORIGINAL_TEST_SELECTION_DIFFERS'
    return suite, modules, events

def run_originals(*, strict=None, log_stream=None):
    if strict is None:
        strict = os.environ.get('OUTLANDS_DOCX_REQUIRE_NATIVE_LINKS') == '1'
    assert type(strict) is bool
    expected = contract()
    before = source_pins()
    suite, modules, events = load_original_suite(strict)
    ids = [test.id() for test in flatten(suite)]
    stream = log_stream if log_stream is not None else io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    runtime_bindings(modules)
    assert source_pins() == before, 'ORIGINAL_SOURCES_CHANGED_DURING_TESTS'
    skips = [dict(test=test.id(), reason=reason) for test, reason in result.skipped]
    pairs = lambda rows: {(row['test'], row['reason']) for row in rows}
    required = pairs(expected['windows_required_skips'] if os.name == 'nt' else expected['posix_required_skips'])
    allowed = set(required)
    if os.name == 'nt':
        allowed |= pairs(expected['windows_short_name_absence_skips'])
        if not strict:
            allowed |= pairs(expected['windows_optional_1314_skips'])
    observed = pairs(skips)
    unexpected = [row for row in skips if (row['test'], row['reason']) not in allowed]
    missing = sorted(required - observed)
    assert len(skips) == len(observed), 'DUPLICATE_SKIP'
    failed = [test.id() for test, _ in result.failures + result.errors]
    good = result.wasSuccessful() and result.testsRun == 72 and not unexpected and not missing
    return dict(schema=1, status='PASS' if good else 'FAIL', tests=result.testsRun,
                passed=result.testsRun - len(result.skipped) - len(result.failures) - len(result.errors),
                skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors),
                skips=skips, unexpected_skips=unexpected, missing_required_skips=[dict(test=a, reason=b) for a, b in missing],
                failed_tests=failed, module_counts=expected['module_counts'], test_ids=ids,
                native_links_required=strict, fixture_adapters_installed=True,
                fixture_adapter_policy='skipTest-only interceptors; original bodies execute unchanged',
                skip_adapter_events=events, runtime_imports_verified=True, original_fixture_roots_verified=True,
                runtime_mirror_test_only=False, runtime_mirror_required=False,
                runtime_sha256=expected['runtime_sha256'], runtime_unchanged=True,
                original_test_source_sha256=expected['original_test_source_sha256'], original_test_bytes_unchanged=True,
                original_methods=72, original_assertion_calls=187,
                original_test_method_assertion_calls=174, original_helper_assertion_calls=13,
                helper_methods=10, ast_hash_encoding='python-ast-fields-json-v2')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    assert args.report.is_absolute() and args.report.parent.is_dir()
    value = run_originals(log_stream=sys.stderr)
    with args.report.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, indent=2) + '\n')
    print(json.dumps({key: value[key] for key in ('status', 'tests', 'passed', 'skipped', 'failures', 'errors')}))
    raise SystemExit(0 if value['status'] == 'PASS' else 1)

if __name__ == '__main__':
    main()
