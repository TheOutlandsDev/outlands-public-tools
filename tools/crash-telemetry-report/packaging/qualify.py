"""Validate the released source ZIP on a verified interpreter and a fresh test environment."""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'crash-telemetry-report'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_crash_telemetry.CrashTelemetryTests.test_reads_existing_sources_without_hardware_polling',
}
FOCUSED_TESTS = {
    'test_report.ReportTests.test_latest_snapshot_and_freshness_boundary',
    'test_report.ReportTests.test_handles_missing_and_malformed_inputs',
    'test_report.ReportTests.test_filters_invalid_readings_and_shapes',
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
assert not loader.errors
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
    observed = '2040-01-02T03:04:20Z'
    fixture = workspace / 'fictional sample #1'
    run([sys.executable, '-I', '-B', '-W', 'error', source / 'examples/make_fixture.py', fixture])
    paths = {
        'database': fixture / 'snapshots.db',
        'sensors': fixture / 'sensors.json',
        'thermal-guard': fixture / 'thermal-guard.json',
        'quarantine': fixture / 'quarantine.json',
    }
    assert set(fixture.iterdir()) == set(paths.values())

    invalid_sqlite = workspace / 'invalid.db'
    invalid_sqlite.write_bytes(b'not a SQLite database')
    missing_table = workspace / 'missing-table.db'
    with closing(sqlite3.connect(missing_table)) as connection:
        connection.execute('CREATE TABLE unrelated(id INTEGER PRIMARY KEY)')
        connection.commit()
    wal_database = workspace / 'wal.db'
    with closing(sqlite3.connect(wal_database)) as connection:
        assert connection.execute('PRAGMA journal_mode=WAL').fetchone() == ('wal',)
        connection.execute('CREATE TABLE snapshots(id INTEGER PRIMARY KEY, captured_at TEXT, payload_json TEXT)')
        connection.execute('INSERT INTO snapshots VALUES (?, ?, ?)', (1, observed, '{}'))
        connection.commit()
    assert wal_database.read_bytes()[18:20] == b'\x02\x02'
    assert not wal_database.with_name(wal_database.name + '-wal').exists()
    assert not wal_database.with_name(wal_database.name + '-shm').exists()
    sidecar_inputs = []
    for suffix in ('-wal', '-shm', '-journal'):
        candidate = workspace / f'closed{suffix}.db'
        shutil.copyfile(paths['database'], candidate)
        candidate.with_name(candidate.name + suffix).write_bytes(b'fictional sidecar sentinel')
        sidecar_inputs.append(candidate)

    bad_json = workspace / 'malformed.json'
    bad_json.write_bytes(b'{"fixture error details":')
    bad_utf8 = workspace / 'invalid-encoding.json'
    bad_utf8.write_bytes(b'\xff')
    large_json = workspace / 'oversized.json'
    large_json.write_bytes(b' ' * (4 * 1024 * 1024 + 1))

    bad_readings = workspace / 'readings.json'
    rows = [
        {'hardware': 'Fictional CPU', 'sensor_type': 'Temperature', 'name': 'CPU Package', 'value': value}
        for value in (41, 'nonfinite-marker', 10**400, True, 'unavailable', {'value': 9999})
    ]
    bad_readings.write_text(
        json.dumps({'sensors': [*rows, None]}).replace('"nonfinite-marker"', '1e400'), encoding='utf-8'
    )

    def tree_facts():
        return {
            path.relative_to(workspace).as_posix(): digest(path) if path.is_file() else None
            for path in workspace.rglob('*')
        }

    before = tree_facts()
    env = {'PYTHONPATH': str(source)}
    base = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*base, '-m', 'crash_telemetry']

    def arguments(changes=None, now=observed):
        values = {**paths, **(changes or {})}
        return [element for key, value in values.items() for element in ('--' + key, value)] + ['--now-utc', now]

    def invalid_constant(value):
        raise AssertionError(f'CLI emitted nonfinite JSON constant: {value}')

    def output(result):
        assert not result.stderr
        payload = json.loads(result.stdout, parse_constant=invalid_constant)
        assert set(payload) == {
            'schema_version', 'generated_utc', 'source', 'cac_snapshot', 'system',
            'temperatures', 'gpus', 'thermal_guard', 'hardware_quarantine', 'errors',
        }
        assert payload['schema_version'] == 1
        assert payload['source'] == 'saved telemetry snapshots and JSON records'
        assert isinstance(payload['errors'], list)
        return payload

    def invoke(changes=None, *, now=observed, expected=0):
        result = run([*cli, *arguments(changes, now)], expected=expected, extra_env=env)
        return output(result)

    audit = """
import os
from pathlib import Path
import runpy
import sys
from urllib.parse import parse_qs


source = Path(sys.argv.pop(1)).resolve()
database = Path(sys.argv.pop(1)).resolve().as_uri()
connections = []


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn'} or event.startswith('socket.'):
        raise AssertionError('Crash telemetry reporting attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Crash telemetry reporting attempted to write a file')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp'}:
        raise AssertionError('Crash telemetry reporting attempted a filesystem mutation')
    if event == 'sqlite3.connect':
        target, _, query = args[0].partition('?')
        assert target == database and parse_qs(query, strict_parsing=True) == {
            'mode': ['ro'], 'immutable': ['1'],
        }, 'Crash telemetry opened an unexpected or writable SQLite input'
        connections.append(target)
    if event in {'sqlite3.enable_load_extension', 'sqlite3.load_extension'}:
        raise AssertionError('Crash telemetry reporting attempted to load a SQLite extension')


sys.addaudithook(verify_offline)
import crash_telemetry
assert Path(crash_telemetry.__file__).resolve().parent == source / 'crash_telemetry'
try:
    runpy.run_module('crash_telemetry', run_name='__main__', alter_sys=True)
except SystemExit as error:
    assert error.code == 0
assert connections == [database]
"""
    report = output(run([*base, '-c', audit, source, paths['database'], *arguments()], extra_env=env))
    assert invoke() == report
    assert report['errors'] == []
    assert report['generated_utc'] == '2040-01-02T03:04:20+00:00'
    assert report['cac_snapshot']['captured_utc'] == '2040-01-02T03:04:00+00:00'
    assert report['cac_snapshot']['overall_status'] == 'warning'
    assert report['cac_snapshot']['age_seconds'] == 20 and report['cac_snapshot']['fresh'] is True
    assert report['system']['cpu_percent'] == 37
    assert report['temperatures']['maximum_cpu_temperature_c'] == 49
    assert report['temperatures']['maximum_storage_temperature_c'] == 32
    assert report['gpus']['count'] == 2 and report['gpus']['maximum_temperature_c'] == 41
    assert [gpu['temperature_c'] for gpu in report['gpus']['items']] == [36, 41]
    assert report['thermal_guard']['status'] == 'armed'
    assert report['thermal_guard']['maximum_temperature_c'] == 41
    assert report['hardware_quarantine']['latched'] is False

    boundary = invoke(now='2040-01-02T03:07:00Z')['cac_snapshot']
    assert boundary['age_seconds'] == 180 and boundary['fresh'] is True
    stale = invoke(now='2040-01-02T03:07:00.001Z')['cac_snapshot']
    assert stale['age_seconds'] == 180.001 and stale['fresh'] is False

    cleaned = invoke({'sensors': bad_readings})['temperatures']
    assert cleaned['maximum_cpu_temperature_c'] == 41

    def refusal(changes):
        report = invoke(changes, expected=1)
        assert report['errors'] and all(isinstance(error, str) for error in report['errors'])
        assert 'fixture error details' not in str(report['errors'])
        assert all(path.name not in str(report['errors']) for path in changes.values())
        assert str(workspace) not in str(report['errors'])
        return report

    refusal({'sensors': bad_json})
    refusal({'thermal-guard': bad_utf8})
    refusal({'quarantine': large_json})
    refusal({'thermal-guard': workspace / 'missing.json'})
    for database in (invalid_sqlite, missing_table, workspace / 'missing.db', wal_database, *sidecar_inputs):
        unavailable = refusal({'database': database})
        assert unavailable['gpus']['count'] == 0
        assert unavailable['cac_snapshot']['captured_utc'] is None

    for args in (arguments(now='not-a-date'), ['--database', paths['database']]):
        result = run([*cli, *args], expected=2, extra_env=env)
        assert result.stderr and not result.stdout and 'Traceback' not in result.stderr

    assert tree_facts() == before, 'Read-only reporting mutated inputs or created sidecar files'
    return [
        'packaged_fictional_fixture',
        'latest_snapshot_selected_by_id',
        'snapshot_freshness_boundary',
        'saved_thermal_guard_and_quarantine',
        'nonfinite_and_malformed_readings_filtered',
        'missing_and_malformed_json_reported',
        'invalid_or_missing_sqlite_reported',
        'nonportable_sqlite_state_refused',
        'invalid_cli_options_refused',
        'read_only_sqlite_connection_audited',
        'offline_reporting_with_process_and_network_audit_guard',
        'source_and_input_files_unchanged',
    ]


def qualify(packages, workspace, report, receipt, reference):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    workspace = workspace.resolve()
    sdk = check_interpreter(receipt)
    build, source, names = unpack(packages, workspace, reference)
    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1')

    def run(args, *, cwd=workspace, expected=0, extra_env=None):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env | (extra_env or {}),
                                capture_output=True, encoding='utf-8', timeout=90)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    test_ids = run_tests(run, source, workspace)
    cli_checks = check_offline_cli(run, source, workspace)
    run([sys.executable, '-I', '-B', source / 'source_check.py'])
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} == names
    evidence = dict(
        status='PASS', package=PACKAGE, version=VERSION, platform=sys.platform, python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=len(ORIGINAL_TESTS), passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_hardware_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('CRASHTELEMETRY_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
