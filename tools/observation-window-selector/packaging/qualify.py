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
PACKAGE = 'observation-window-selector'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_original_offline.TestObservationDiscoveryTests.test_rows_preserve_descending_millisecond_timestamps_and_duplicates',
    'test_original_offline.TestObservationDiscoveryTests.test_rows_reject_bad_shapes_null_types_aware_or_excess_precision',
    'test_original_offline.TestObservationDiscoveryTests.test_rows_enforce_start_inclusive_end_exclusive_and_descending',
    'test_original_offline.TestObservationDiscoveryTests.test_select_case_uses_latest_returned_day_with_whole_second_midnights',
    'test_original_offline.TestObservationDiscoveryTests.test_select_case_returns_none_for_empty_and_revalidates_input',
}
FOCUSED_TESTS = {
    'test_selector.ObservationWindowTests.test_bounds_reject_equal_reversed_and_aware_ranges',
    'test_selector.ObservationWindowTests.test_partial_input_bounds_still_select_whole_day',
    'test_selector.ObservationWindowTests.test_last_representable_day_refuses_overflow',
    'test_selector.ObservationWindowTests.test_cli_refuses_ambiguous_iso_and_withholds_private_values',
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
    script = source / 'observation_window.py'
    cli = [sys.executable, '-I', '-B', '-S', '-W', 'error', script]
    examples = source / 'examples'
    start = '2042-12-01T00:00:00'
    end = '2043-01-01T00:00:00'
    latest = '2042-12-31T23:59:59.997'
    latest_window = {'start': '2042-12-31T00:00:00', 'end': end}
    sensitive = ('fictional-private-marker', str(workspace), str(source), 'Traceback')

    def select(path, *, lower=start, upper=end, expected=0):
        return run([*cli, '--input', path, '--start', lower, '--end', upper], expected=expected)

    def report(result, count, window):
        assert not result.stderr
        assert all(item not in result.stdout for item in sensitive)
        assert json.loads(result.stdout) == {'count': count, 'window': window}

    def refuse(path, **kwargs):
        result = select(path, expected=2, **kwargs)
        assert not result.stdout and result.stderr.strip()
        assert all(item not in result.stderr for item in (*sensitive, path.name))

    def sample(name, value):
        target = workspace / f'fictional-{name}.json'
        target.write_bytes((json.dumps(value) + '\n').encode('ascii'))
        return target

    help_text = run([*cli, '--help'])
    assert not help_text.stderr and all(flag in help_text.stdout for flag in ('--input', '--start', '--end'))

    valid = examples / 'observations.json'
    valid_rows = json.loads(valid.read_bytes())
    assert len(valid_rows) == 3 and valid_rows[:2] == [[latest], [latest]]
    baseline = select(valid)
    report(baseline, 3, latest_window)
    assert latest not in baseline.stdout
    assert select(valid).stdout == baseline.stdout
    report(select(examples / 'empty.json'), 0, None)

    start_only = sample('lower-bound', [[start]])
    report(select(start_only), 1, {'start': start, 'end': '2042-12-02T00:00:00'})
    invalid = examples / 'invalid.json'
    assert json.loads(invalid.read_bytes()) == [[end]]
    refuse(invalid)
    refuse(sample('before-lower-bound', [['2042-11-30T23:59:59.999']]))
    report(select(sample('hundred-rows', [[latest]] * 100)), 100, latest_window)
    refuse(sample('hundred-and-one-rows', [[latest]] * 101))
    refuse(sample('not-descending', [[start], [latest]]))
    refuse(sample('timezone', [[latest + 'Z']]))
    refuse(sample('microsecond', [[latest + '1']]))

    private = sample('fictional-private-marker', [['fictional-private-marker']])
    assert b'fictional-private-marker' in private.read_bytes()
    refuse(private)
    refuse(workspace / 'fictional-private-marker-missing.json')
    directory = workspace / 'fictional-private-marker-directory'
    directory.mkdir()
    refuse(directory)
    large = workspace / 'fictional-oversized-input.json'
    large.write_bytes(b' ' * (16 * 1024) + b'[]')
    refuse(large)
    refuse(valid, lower=end, upper=start)
    refuse(valid, lower=end, upper=end)
    refuse(valid, lower='fictional-private-marker', upper=end)

    audit = """
import os
from pathlib import Path
import runpy
import sys

script = Path(sys.argv[1]).resolve()
input_file = Path(sys.argv[2]).resolve()
start, end = sys.argv[3:]
sys.argv = [str(script), '--input', str(input_file), '--start', start, '--end', end]
observed_input = []


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
            if os.path.normcase(os.fsdecode(path)) == os.path.normcase(str(input_file)):
                observed_input.append(path)
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
assert len(observed_input) == 1
"""
    audited = run([sys.executable, '-I', '-B', '-W', 'error', '-c', audit, script,
                   valid, start, end])
    assert audited.stdout == baseline.stdout and not audited.stderr

    return [
        'selector_help',
        'year_end_midnight_rollover',
        'duplicate_rows_preserved',
        'deterministic_report',
        'empty_observations_return_null',
        'lower_inclusive_upper_exclusive',
        'hundred_row_limit',
        'descending_order_required',
        'timestamp_precision_and_timezone_guard',
        'invalid_input_withholds_private_paths',
        'bounded_file_input',
        'invalid_date_bounds',
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
    print('OBSERVATION_WINDOW_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
