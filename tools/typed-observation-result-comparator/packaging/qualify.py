"""Validate the released source ZIP on a verified interpreter and a fresh test environment."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'typed-observation-result-comparator'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_original_offline.TestObservationComparisonTests.test_typed_rows_preserve_nulls_text_and_both_microsecond_values',
    'test_original_offline.TestObservationComparisonTests.test_typed_rows_reject_wrong_types_aware_timestamps_and_cap',
    'test_original_offline.TestObservationComparisonTests.test_comparison_uses_all_five_fields_and_retains_duplicates',
    'test_original_offline.TestObservationComparisonTests.test_comparison_distinguishes_null_empty_and_leading_zeros',
}
FOCUSED_TESTS = {
    'test_cli.TypedComparisonCLITests.test_matches_reordered_rows_and_preserves_files',
    'test_cli.TypedComparisonCLITests.test_distinguishes_microsecond_changes_in_either_column',
    'test_cli.TypedComparisonCLITests.test_rejects_malformed_or_imprecise_input_without_disclosing_it',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unpack(packages, workspace, reference):
    archive = packages / ARCHIVE
    build = json.loads((packages / 'build-manifest.json').read_bytes())
    assert build['schema'] == 1 and build['package'] == PACKAGE
    assert build['filename'] == ARCHIVE and build['version'] == VERSION
    assert isinstance(build['source_revision'], str)
    assert re.fullmatch('[0-9a-f]{40}', build['source_revision'])
    assert build['sha256'] == digest(archive) and build['bytes'] == archive.stat().st_size
    line = f"{build['sha256']}  {ARCHIVE}\n"
    assert (packages / 'SHA256SUMS.txt').read_bytes() == line.encode('ascii')
    assert packages.resolve() != reference.resolve(), 'Independent rebuild must use a separate directory'
    for filename in (ARCHIVE, 'build-manifest.json', 'SHA256SUMS.txt'):
        assert (packages / filename).read_bytes() == (reference / filename).read_bytes()

    workspace.mkdir()
    source = workspace / ARCHIVE.removesuffix('.zip')
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        assert len({item.filename.casefold() for item in members}) == len(members) == build['files']
        assert 0 < len(members) < 100
        names = set()
        for item in members:
            name = item.filename
            parts = name.split('/')
            assert len(parts) > 1 and parts[0] == source.name
            assert str(PurePosixPath(name)) == name and all(part not in ('', '.', '..') for part in parts)
            assert ':' not in name and '\\' not in name and item.file_size < 1024 * 1024
            assert stat.S_ISREG(item.external_attr >> 16)
            names.add('/'.join(parts[1:]))
        assert bundle.testzip() is None
        bundle.extractall(workspace)
    return build, source, names


def check_interpreter(receipt):
    sdk = json.loads(receipt.read_bytes())
    lock = json.loads((ROOT / 'PYTHON-LOCK.json').read_bytes())
    minor = f'{sys.version_info.major}.{sys.version_info.minor}'
    pin = lock['python_archives'][sys.platform][minor]
    assert sdk['status'] == 'PASS' and sdk['archive'] == pin
    assert sdk['platform'] == sys.platform and sdk['python_version'] == platform.python_version() == pin['python']
    assert sdk['python_lock_sha256'] == digest(ROOT / 'PYTHON-LOCK.json')
    assert sdk['preparation_helper_sha256'] == digest(ROOT / 'packaging/prepare_python.py')
    assert sdk['executable_sha256'] == digest(Path(sys._base_executable))
    return sdk


def run_tests(run, source, workspace):
    prefix = workspace / 'venv'
    run([sys.executable, '-I', '-B', '-m', 'venv', '--without-pip', prefix])
    python = prefix / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    test_code = """
import importlib.metadata
import json
from pathlib import Path
import sys
import unittest


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item.id()


source = Path(sys.argv[1])
assert Path(sys.prefix) == Path(sys.argv[2])
assert sys.prefix != sys.base_prefix
assert not list(importlib.metadata.distributions())
sys.path.insert(0, str(source))
loader = unittest.TestLoader()
suite = loader.discover(str(source / 'tests'))
identifiers = sorted(cases(suite))
assert not loader.errors, loader.errors
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun == len(identifiers)
assert result.wasSuccessful()
assert not (result.skipped or result.expectedFailures or result.unexpectedSuccesses)
print(json.dumps(identifiers))
"""
    result = run([python, '-I', '-B', '-W', 'error', '-c', test_code, source, prefix], cwd=source)
    identifiers = json.loads(result.stdout)
    assert len(identifiers) == len(ORIGINAL_TESTS) + len(FOCUSED_TESTS)
    assert set(identifiers) == ORIGINAL_TESTS | FOCUSED_TESTS
    return identifiers


def check_offline_cli(run, source, workspace):
    script = source / 'typed_observation_compare.py'
    cli = [sys.executable, '-I', '-B', '-S', '-W', 'error', script]
    examples = source / 'examples'
    left = examples / 'expected.json'
    matching = examples / 'matching.json'
    mismatch = examples / 'mismatch.json'
    sensitive = ('fictional-private-marker', str(workspace), str(source), 'Traceback')
    samples = {}

    def sample(name, data):
        path = workspace / f'fictional-{name}.json'
        path.write_bytes(data)
        samples[path] = digest(path)
        return path

    def rows(name, value):
        return sample(name, (json.dumps(value, ensure_ascii=True) + '\n').encode('ascii'))

    def compare(expected_file, actual_file, *, expected=0):
        return run([*cli, '--expected', expected_file, '--actual', actual_file], expected=expected)

    def check_report(result, *, row_counts, matched, left_distinct=0, right_distinct=0):
        assert not result.stderr
        assert all(value not in result.stdout for value in sensitive)
        report = json.loads(result.stdout)
        basis = report.pop('comparison_basis')
        assert basis == 'Exact typed five-field multiset with nulls and duplicates.'
        expected_count, actual_count = row_counts
        is_match = matched == expected_count == actual_count
        assert report['all_values_match'] is is_match
        assert report == {
            'status': 'match' if is_match else 'mismatch',
            'all_values_match': is_match,
            'columns_compared': 5,
            'expected_rows': expected_count,
            'actual_rows': actual_count,
            'matched_rows': matched,
            'expected_only_rows': expected_count - matched,
            'actual_only_rows': actual_count - matched,
            'expected_only_distinct_rows': left_distinct,
            'actual_only_distinct_rows': right_distinct,
        }
        assert all(type(value) is int for key, value in report.items() if key.endswith('_rows'))

    def refused(expected_file, actual_file):
        result = compare(expected_file, actual_file, expected=2)
        assert not result.stdout and result.stderr.strip()
        assert all(value not in result.stderr for value in (*sensitive, expected_file.name, actual_file.name))

    help_text = run([*cli, '--help'])
    assert not help_text.stderr and all(flag in help_text.stdout for flag in ('--expected', '--actual'))

    source_rows = json.loads(left.read_bytes())
    assert len(source_rows) == 4 and len({tuple(row) for row in source_rows}) == 3
    assert json.loads(matching.read_bytes()) == list(reversed(source_rows))
    baseline = compare(left, matching)
    check_report(baseline, row_counts=(4, 4), matched=4)
    assert compare(left, matching).stdout == baseline.stdout
    check_report(compare(left, mismatch, expected=1), row_counts=(4, 4), matched=3,
                 left_distinct=1, right_distinct=1)

    original = ['fictional-private-marker', 'caf\u00e9', '001', '2042-12-31T23:59:59.123456',
                '2043-01-01T00:00:00.654321']
    reference = rows('reference', [original])
    for index, timestamp in ((3, '2042-12-31T23:59:59.123457'), (4, '2043-01-01T00:00:00.654322')):
        changed = original.copy()
        changed[index] = timestamp
        result = compare(reference, rows(f'microsecond-column-{index}', [changed]), expected=1)
        check_report(result, row_counts=(1, 1), matched=0, left_distinct=1, right_distinct=1)
        assert original[index] not in result.stdout and timestamp not in result.stdout

    double = rows('one-duplicate', [original, original])
    check_report(compare(double, reference, expected=1), row_counts=(2, 1), matched=1, left_distinct=1)

    variants = (
        ([None, '', None, None, None], [None, '', '', None, None]),
        (original, [*original[:2], '1', *original[3:]]),
        (original, [original[0], 'cafe\u0301', *original[2:]]),
    )
    for index, (left_row, right_row) in enumerate(variants):
        result = compare(rows(f'variant-{index}-left', [left_row]),
                         rows(f'variant-{index}-right', [right_row]), expected=1)
        check_report(result, row_counts=(1, 1), matched=0, left_distinct=1, right_distinct=1)

    empty = rows('empty', [])
    check_report(compare(empty, empty), row_counts=(0, 0), matched=0)
    short = rows('short-row', [original[:-1]])
    wrong = rows('wrong-cell-type', [[17, *original[1:]]])
    object_input = rows('object-input', {'values': [original]})
    for path in (short, wrong, object_input):
        refused(reference, path)
    at_limit = rows('row-count-limit', [original] * 10_000)
    check_report(compare(at_limit, at_limit), row_counts=(10_000, 10_000), matched=10_000)
    refused(reference, rows('over-row-count-limit', [original] * 10_001))

    invalid_timestamps = (
        '2042-12-31T23:59:59.1234567',
        '2042-12-31T23:59:59Z',
        '2042-12-31T23:59:59+01:00',
        '2042-12-31 23:59:59',
        '2042-02-30T23:59:59',
        '2042-12-31',
    )
    for index, timestamp in enumerate(invalid_timestamps):
        changed = original.copy()
        changed[3 if index % 2 else 4] = timestamp
        refused(reference, rows(f'invalid-timestamp-{index}', [changed]))

    malformed = sample('fictional-private-marker-malformed', b'[fictional-private-marker')
    refused(malformed, reference)
    refused(reference, sample('invalid-utf8', b'"\xff"'))
    refused(reference, workspace / 'fictional-private-marker-missing.json')
    directory = workspace / 'fictional-private-marker-directory'
    directory.mkdir()
    refused(reference, directory)
    limit = 16 * 1024 * 1024
    exact_size = sample('file-size-limit', b' ' * (limit - 2) + b'[]')
    check_report(compare(empty, exact_size), row_counts=(0, 0), matched=0)
    refused(reference, sample('over-file-size-limit', b' ' * limit + b'[]'))

    audit = """
import os
from pathlib import Path
import runpy
import sys

script, expected, actual = map(lambda item: Path(item).resolve(), sys.argv[1:])
sys.argv = [str(script), '--expected', str(expected), '--actual', str(actual)]
selected = {os.path.normcase(str(path)) for path in (expected, actual)}
observed = []


def verify_offline(event, args):
    if event.startswith(('socket.', 'ctypes.', 'winreg.')):
        raise AssertionError('Unexpected network or platform probe')
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn',
                 'os.startfile', 'os.kill'}:
        raise AssertionError('Unexpected process invocation')
    if event == 'open':
        flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        if args[2] & flags:
            raise AssertionError('Unexpected file write')
        path = args[0]
        if isinstance(path, (bytes, str)):
            normalized = os.path.normcase(os.fsdecode(path))
            if normalized in selected:
                observed.append(normalized)
    if event in {'os.rename', 'os.link', 'os.remove', 'os.rmdir', 'os.mkdir', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkdtemp', 'tempfile.mkstemp',
                 'shutil.rmtree'}:
        raise AssertionError('Unexpected filesystem mutation')


sys.addaudithook(verify_offline)
try:
    runpy.run_path(str(script), run_name='__main__')
except SystemExit as exc:
    if exc.code not in (0, None):
        raise
assert len(observed) == 2 and set(observed) == selected
"""
    audited = run([sys.executable, '-I', '-B', '-W', 'error', '-c', audit, script, left, matching])
    assert audited.stdout == baseline.stdout and not audited.stderr
    assert all(digest(path) == before for path, before in samples.items())

    return [
        'comparator_help',
        'matching_reordered_rows',
        'fixed_report_shape_no_raw_values',
        'deterministic_report',
        'fixture_mismatch',
        'both_microsecond_fields',
        'duplicate_counts',
        'null_empty_leading_zero',
        'empty_input_matches',
        'row_shape_and_count',
        'strict_datetime',
        'invalid_private_diagnostics',
        'bounded_file_input',
        'offline_read_only_audit_guard',
        'extracted_source_and_inputs_unchanged',
    ]


def qualify(packages, workspace, report, receipt, reference):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    workspace = workspace.resolve()
    sdk = check_interpreter(receipt)
    build, source, names = unpack(packages, workspace, reference)
    before_source = {name: digest(source / name) for name in names}
    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1')

    def run(args, *, cwd=workspace, expected=0):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                capture_output=True, encoding='utf-8', timeout=90)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    test_ids = run_tests(run, source, workspace)
    cli_checks = check_offline_cli(run, source, workspace)
    run([sys.executable, '-I', '-B', source / 'source_check.py'])
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} == names
    assert {name: digest(source / name) for name in names} == before_source
    evidence = dict(
        status='PASS', package=PACKAGE, version=VERSION, platform=sys.platform, python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=len(ORIGINAL_TESTS), passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('TYPED_OBSERVATION_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
