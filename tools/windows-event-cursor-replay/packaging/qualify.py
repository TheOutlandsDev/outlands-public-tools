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
PACKAGE = 'windows-event-cursor-replay'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
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



ORIGINAL_TESTS = {
    'tests/test_event_cursor.py::test_windows_diagnostics_cursor_prevents_restart_replay',
    'tests/test_event_cursor.py::test_windows_diagnostics_corrupt_cursor_uses_bounded_startup_window',
}


def installed_versions(run, python, prefix):
    code = """
from importlib.metadata import distributions
import json
from pathlib import Path
import sys

assert Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve()
assert sys.prefix != sys.base_prefix
print(json.dumps({d.metadata['Name'].lower().replace('_', '-'): d.version for d in distributions()}))
"""
    result = run([python, '-I', '-B', '-W', 'error', '-c', code, prefix])
    assert not result.stderr
    return json.loads(result.stdout)


def install_offline(run, python, source, prefix, wheels, selected, requirement, expected):
    report = prefix / f'{requirement}-pip-private.json'
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'install',
         '--no-index', '--find-links', wheels, '--only-binary=:all:', '--require-hashes',
         '--no-deps', '--no-cache-dir', '--report', report, '-r', source / f'requirements-{requirement}.txt'])
    from urllib.parse import urlsplit
    from urllib.request import url2pathname

    receipt = json.loads(report.read_bytes())
    added = set()
    for item in receipt['install']:
        name = item['metadata']['name'].lower().replace('_', '-')
        pin = selected[name]
        download = item['download_info']
        uri = urlsplit(download['url'])
        assert name not in added and item['metadata']['version'] == pin['version']
        assert uri.scheme == 'file' and not uri.netloc and not uri.query and not uri.fragment
        assert Path(url2pathname(uri.path)).resolve() == (wheels / pin['filename']).resolve()
        assert download['archive_info']['hashes']['sha256'] == pin['sha256']
        added.add(name)
    assert added == set(expected)
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'check'])


def verify_installs(run, python, prefix, bootstrap, selected, names):
    expected = dict(bootstrap)
    expected.update({name: selected[name]['version'] for name in names})
    assert installed_versions(run, python, prefix) == expected


def run_tests(run, python, source):
    code = """
import json
from pathlib import Path
import sys

import pytest


class Evidence:
    def __init__(self):
        self.collected = []
        self.passed = []
        self.problem = False

    def pytest_collection_finish(self, session):
        self.collected = [item.nodeid for item in session.items]

    def pytest_runtest_logreport(self, report):
        if report.failed or report.skipped or hasattr(report, 'wasxfail'):
            self.problem = True
        elif report.when == 'call' and report.passed:
            self.passed.append(report.nodeid)


source = Path(sys.argv[1])
sys.path.insert(0, str(source))
proof = Evidence()
exit_code = pytest.main(['-q', '-p', 'no:cacheprovider', 'tests'], plugins=[proof])
assert exit_code == 0 and not proof.problem
assert sorted(proof.collected) == sorted(proof.passed)
print(json.dumps(sorted(proof.passed)))
"""
    result = run([python, '-I', '-B', '-W', 'error', '-c', code, source], cwd=source)
    assert not result.stderr
    identifiers = json.loads(result.stdout.strip().splitlines()[-1])
    assert len(identifiers) == len(ORIGINAL_TESTS)
    assert set(identifiers) == ORIGINAL_TESTS
    return identifiers


def check_offline_cli(run, python, source, workspace):
    script = source / 'windows_event_cursor_replay.py'
    probe = workspace / 'cli-probe'
    probe.mkdir()
    copied = probe / script.name
    copied.write_bytes(script.read_bytes())
    events_path = probe / 'events.json'
    cursor_path = probe / 'cursor.json'
    now = '2020-01-02T08:00:00Z'
    fixture = json.loads((source / 'examples/events.json').read_bytes())
    saved = json.loads((source / 'examples/cursor.json').read_bytes())

    def invoke(events=fixture, cursor=saved, *, observed_at=now, lookback='10', expected=0):
        raw = events if isinstance(events, bytes) else json.dumps(events).encode('utf-8')
        events_path.write_bytes(raw)
        args = [
            python, '-I', '-B', '-W', 'error', copied, '--events', events_path,
            '--observed-at', observed_at, '--startup-lookback-seconds', lookback,
        ]
        if cursor is not None:
            raw_cursor = cursor if isinstance(cursor, bytes) else json.dumps(cursor).encode('utf-8')
            cursor_path.write_bytes(raw_cursor)
            args.extend(['--cursor', cursor_path])
        before = {item.name: digest(item) for item in probe.iterdir()}
        result = run(args, cwd=probe, expected=expected)
        assert {item.name: digest(item) for item in probe.iterdir()} == before
        if expected:
            assert not result.stdout and result.stderr
            assert all(value not in result.stderr for value in ('Traceback', 'DO-NOT-ECHO', str(probe)))
            return result.stderr
        assert not result.stderr
        return json.loads(result.stdout)

    first = invoke()
    assert first['cursor_loaded'] is True
    assert first['last_query'] == '2020-01-02T07:59:50+00:00'
    assert first['query_since'] == '2020-01-02T07:59:48+00:00'
    assert first['new_events'] == [
        {'channel': 'Application', 'record_id': 101, 'timestamp': '2020-01-02T07:59:51+00:00'},
        {'channel': 'System', 'record_id': 102, 'timestamp': '2020-01-02T07:59:59+00:00'},
    ]
    second = invoke(cursor=first['next_cursor'])
    assert second['new_events'] == [] and second['next_cursor'] == first['next_cursor']

    for timestamp, loaded in (
        ('2020-01-02T08:04:59.999999Z', True),
        ('2020-01-02T08:05:00Z', True),
        ('2020-01-02T08:05:00.000001Z', False),
        ('2020-01-02T03:05:00-05:00', True),
    ):
        result = invoke(cursor={**saved, 'last_query': timestamp})
        assert result['cursor_loaded'] is loaded
        assert len(result['new_events']) == (2 if loaded else 3)
    legacy = invoke(cursor={**saved, 'last_query': '2020-01-02T03:00:00'},
                    observed_at='2020-01-02T03:00:00-05:00')
    assert legacy['last_query'] == '2020-01-02T08:00:00+00:00'

    for cursor in (None, b'{invalid', b'\xff', {**saved, 'seen': {}},
                   {**saved, 'last_query': '0001-01-01T00:00:00+01:00'}):
        result = invoke(events=[], cursor=cursor, lookback='15')
        assert result['cursor_loaded'] is False
        assert result['last_query'] == '2020-01-02T07:59:45+00:00'
    for lookback, cutoff in (('0', '07:59:58'), ('2', '07:59:58'),
                             ('300', '07:55:00'), ('301', '07:55:00')):
        result = invoke(cursor=None, lookback=lookback)
        assert result['last_query'] == f'2020-01-02T{cutoff}+00:00'
    missing_result = run([python, '-I', '-B', copied, '--events', events_path,
                          '--observed-at', now, '--cursor', probe / 'missing.json'], cwd=probe)
    assert json.loads(missing_result.stdout)['cursor_loaded'] is False
    assert not (probe / 'missing.json').exists()

    def key(number):
        return {'channel': 'System', 'record_id': number}

    def row(number):
        return {**key(number), 'timestamp': now}

    history = [key(number) for number in range(5_001)]
    large = invoke(events=[], cursor={**saved, 'seen': history})
    assert large['next_cursor']['seen'] == history[1:]
    eviction = invoke(events=[row(number) for number in (1, 5_001, 1)],
                      cursor={**saved, 'seen': history})
    assert [event['record_id'] for event in eviction['new_events']] == [5_001, 1]
    assert eviction['next_cursor']['seen'] == history[3:] + [key(5_001), key(1)]
    repeated = invoke(events=[row(1)], cursor={**saved, 'seen': [key(1), {}, key(2), key(1)]})
    assert repeated['new_events'] == []
    assert repeated['next_cursor']['seen'] == [key(2), key(1)]

    exact = json.dumps(fixture).encode('utf-8').ljust(2_000_000, b' ')
    assert invoke(events=exact) == first
    assert 'exceeds' in invoke(events=exact + b' ', expected=2)
    assert 'exceeds' in invoke(cursor=b' ' * 2_000_001, expected=2)
    assert '10,000' in invoke(events=[row(100)] * 10_001, expected=2)
    for raw in (b'\xff', b'[NaN]', b'[{"channel":1,"channel":2}]', b'{invalid'):
        assert 'valid UTF-8 JSON' in invoke(events=raw, expected=2)
    for record in ({}, {**row(3), 'record_id': True},
                   {**row(3), 'record_id': 2**63}, {**row(3), 'channel': ' '},
                   {**row(3), 'timestamp': '2020-01-02T08:00:00'}):
        assert 'Invalid event record at position 1' in invoke(events=[record], expected=2)
    assert 'ISO 8601' in invoke(observed_at='DO-NOT-ECHO', expected=2)
    assert 'finite' in invoke(lookback='nan', expected=2)

    bom = bytes.fromhex('efbbbf')
    assert invoke(events=bom + json.dumps(fixture).encode(),
                  cursor=bom + json.dumps(saved).encode()) == first
    assert invoke(observed_at='2020-01-02T03:00:00-05:00') == first
    assert invoke() == first and copied.read_bytes() == script.read_bytes()
    return [
        'restart_suppresses_previously_seen_records',
        'timestamp_order_and_channel_scoped_identity',
        'inclusive_five_minute_future_skew',
        'corrupt_and_missing_cursor_with_clamped_startup_lookback',
        '5000_key_window_and_repeated_saved_keys',
        'malformed_inputs_and_file_and_batch_limits',
        'utc_normalization_bom_and_read_only_determinism',
    ]



def qualify(packages, workspace, report, receipt, reference):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    workspace = workspace.resolve()
    sdk = check_interpreter(receipt)
    build, source, names = unpack(packages, workspace, reference)
    before_source = {name: digest(source / name) for name in names}
    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PYTEST_', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')

    def run(args, *, cwd=workspace, expected=0):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                capture_output=True, encoding='utf-8', timeout=180)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    wheels = workspace / 'wheels'
    selected = json.loads(run([sys.executable, '-I', '-B', source / 'packaging/prepare_wheels.py',
                               '--out', wheels]).stdout)
    assert {path.name for path in wheels.iterdir()} == {pin['filename'] for pin in selected.values()}
    assert all(digest(wheels / pin['filename']) == pin['sha256'] for pin in selected.values())
    prefix = workspace / 'venv'
    run([sys.executable, '-I', '-B', '-m', 'venv', prefix])
    python = prefix / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    bootstrap = installed_versions(run, python, prefix)
    assert 'pip' in bootstrap and bootstrap.keys() <= {'pip', 'setuptools'}

    verify_installs(run, python, prefix, bootstrap, selected, ())
    cli_checks = check_offline_cli(run, python, source, workspace)
    install_offline(run, python, source, prefix, wheels, selected, 'test', selected.keys())
    verify_installs(run, python, prefix, bootstrap, selected, selected.keys())
    test_ids = run_tests(run, python, source)

    run([sys.executable, '-I', '-B', source / 'source_check.py'])
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} == names
    assert {name: digest(source / name) for name in names} == before_source
    assert all(digest(wheels / pin['filename']) == pin['sha256'] for pin in selected.values())
    evidence = dict(
        status='PASS', package=PACKAGE, version=VERSION, platform=sys.platform, python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_test_functions=len(ORIGINAL_TESTS), original_test_cases=len(ORIGINAL_TESTS), passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=[], dependencies=selected, test_runner='pytest',
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), pip_version=bootstrap['pip'],
        offline_wheel_install=True, fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('WINDOWS_EVENT_CURSOR_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
