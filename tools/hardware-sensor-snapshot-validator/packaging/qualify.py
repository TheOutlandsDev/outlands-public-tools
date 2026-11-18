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
PACKAGE = 'hardware-sensor-snapshot-validator'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_sensor_bridge.SensorBridgeTests.test_sensor_bridge_accepts_fresh_elevated_cpu_temperatures',
    'test_sensor_bridge.SensorBridgeTests.test_sensor_bridge_rejects_stale_output',
    'test_sensor_bridge.SensorBridgeTests.test_sensor_bridge_rejects_non_admin_output',
}
FOCUSED_TESTS = {
    'test_validator.ValidatorTests.test_rejects_malformed_snapshots_without_echoing_payload_errors',
    'test_validator.ValidatorTests.test_preserves_freshness_boundaries_with_explicit_reference_time',
    'test_validator.ValidatorTests.test_filters_non_temperature_nonfinite_and_out_of_range_readings',
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
    generated = '2040-01-02T03:04:05Z'
    observed = '2040-01-02T03:04:10Z'

    def temperature(identifier, hardware, name, value):
        return {
            'identifier': identifier,
            'hardware': hardware,
            'sensor_type': 'Temperature',
            'name': name,
            'value': value,
        }

    retained = [
        temperature('fictional/probe/package', 'Fictional CPU', 'CPU Package', -50.0),
        temperature('fictional/probe/core', 'Fictional CPU', 'Core 0', 200.0),
        temperature('fictional/probe/gpu', 'Fictional GPU', 'GPU Edge', '44.5'),
    ]
    snapshot = {
        'schema_version': 1,
        'administrator': True,
        'status': 'active',
        'generated': generated,
        'sensors': retained + [
            temperature('fictional/probe/cold', 'Fictional GPU', 'Too cold', -50.01),
            temperature('fictional/probe/hot', 'Fictional GPU', 'Too hot', 200.01),
            temperature('fictional/probe/overflow', 'Fictional GPU', 'Overflow', 10 ** 400),
            temperature('fictional/probe/infinite', 'Fictional GPU', 'Infinite', 99990001),
            temperature('fictional/probe/malformed', 'Fictional GPU', 'Malformed', 'unavailable'),
            {**retained[0], 'sensor_type': 'Fan', 'value': 42.0},
            None,
        ],
    }
    false_marker = {**snapshot, 'administrator': False}
    string_marker = {**snapshot, 'administrator': 'true'}
    no_marker = {key: value for key, value in snapshot.items() if key != 'administrator'}
    inactive = {**snapshot, 'status': 'inactive', 'error': 'fixture details must not appear'}
    samples = {
        'active.json': json.dumps(snapshot).replace('99990001', '1e400').encode('utf-8-sig'),
        'administrator-false.json': json.dumps(false_marker).encode(),
        'administrator-string.json': json.dumps(string_marker).encode(),
        'administrator-missing.json': json.dumps(no_marker).encode(),
        'inactive.json': json.dumps(inactive).encode(),
        'null-sensors.json': json.dumps({**snapshot, 'sensors': None}).encode(),
        'object-sensors.json': json.dumps({**snapshot, 'sensors': {'value': 42}}).encode(),
        'insufficient-cpu.json': json.dumps({**snapshot, 'sensors': retained[1:]}).encode(),
        'wrong-schema.json': json.dumps({**snapshot, 'schema_version': 2}).encode(),
        'invalid-time.json': json.dumps({**snapshot, 'generated': 'invalid'}).encode(),
        'scalar.json': b'true',
        'invalid-json.json': b'{',
        'invalid-encoding.json': b'\xff',
        'oversized.json': b' ' * (4 * 1024 * 1024 + 1),
    }
    for name, raw in samples.items():
        (workspace / name).write_bytes(raw)

    example = source / 'examples/snapshot.json'
    initial = {path: digest(path) for path in [example, *(workspace / name for name in samples)]}
    before = set(workspace.iterdir())
    env = {'PYTHONPATH': str(source)}
    base = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*base, '-m', 'sensor_snapshot']

    def output(result):
        assert not result.stderr
        payload = json.loads(result.stdout)
        assert set(payload) == {'readings', 'status'}
        assert isinstance(payload['readings'], list) and isinstance(payload['status'], str)
        return payload

    def invoke(name, *, timestamp=observed, extra=(), expected=0):
        return run([*cli, '--input', workspace / name, '--now', timestamp, *extra],
                   expected=expected, extra_env=env)

    def unavailable(name, reason, *, timestamp=observed, extra=()):
        payload = output(invoke(name, timestamp=timestamp, extra=extra, expected=1))
        assert not payload['readings'] and payload['status'].startswith('Unavailable:')
        assert reason in payload['status'].lower()
        return payload

    audit = """
import os
from pathlib import Path
import runpy
import sys


source = Path(sys.argv.pop(1))


def verify_offline(event, args):
    process_or_network = (
        event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn'}
        or event.startswith('socket.')
    )
    if process_or_network:
        raise AssertionError('Snapshot validation attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Snapshot validation attempted to write a file')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp'}:
        raise AssertionError('Snapshot validation attempted a filesystem mutation')


sys.addaudithook(verify_offline)
import sensor_snapshot
assert Path(sensor_snapshot.__file__).resolve().parent == source / 'sensor_snapshot'
runpy.run_module('sensor_snapshot', run_name='__main__', alter_sys=True)
"""
    active = output(run([*base, '-c', audit, source, '--input', workspace / 'active.json',
                         '--now', observed], extra_env=env))
    expected_rows = [
        {**item, 'value': float(item['value']), 'unit': 'C', 'source': 'Hardware Sensor Bridge'}
        for item in retained
    ]
    assert active['readings'] == expected_rows
    assert active['status'].startswith('Active:') and '2 CPU' in active['status']

    packaged = output(run([*cli, '--input', example, '--now', observed], extra_env=env))
    assert packaged['status'].startswith('Active:') and '2 CPU' in packaged['status']
    assert [
        (item['identifier'], item['hardware'], item['name'], item['value'], item['unit'])
        for item in packaged['readings']
    ] == [
        ('fictional/cpu/package', 'Fictional CPU', 'CPU Package', 42.0, 'C'),
        ('fictional/cpu/core', 'Fictional CPU', 'Core 0', 48.0, 'C'),
        ('fictional/gpu/edge', 'Fictional GPU', 'GPU Edge', 55.0, 'C'),
    ]

    for name in ('administrator-false.json', 'administrator-string.json', 'administrator-missing.json'):
        unavailable(name, 'administrator')
    inactive_status = unavailable('inactive.json', 'inactive')
    assert 'fixture details' not in inactive_status['status']
    unavailable('wrong-schema.json', '')
    unavailable('scalar.json', '')
    unavailable('invalid-time.json', 'timestamp')
    for name in ('null-sensors.json', 'object-sensors.json'):
        unavailable(name, 'sensor collection')
    unavailable('insufficient-cpu.json', 'cpu')

    exact_age = '2040-01-02T03:04:25Z'
    after_age = '2040-01-02T03:04:25.001Z'
    assert output(invoke('active.json', timestamp=exact_age)) == active
    unavailable('active.json', 'stale', timestamp=after_age)
    unavailable('active.json', 'stale', extra=('--max-age-seconds', '4'))
    assert output(invoke('active.json', extra=('--max-age-seconds', '5'))) == active

    exact_future = '2040-01-02T03:04:00Z'
    beyond_future = '2040-01-02T03:03:59.999Z'
    assert output(invoke('active.json', timestamp=exact_future)) == active
    unavailable('active.json', 'stale', timestamp=beyond_future)

    def invalid(result):
        assert result.stderr and not result.stdout and 'Traceback' not in result.stderr

    for name in ('invalid-json.json', 'invalid-encoding.json', 'oversized.json', 'missing.json', '.'):
        invalid(invoke(name, expected=2))
    for timestamp in ('invalid', observed.removesuffix('Z')):
        invalid(invoke('active.json', timestamp=timestamp, expected=2))
    for age in ('-1', 'nan', 'inf'):
        invalid(invoke('active.json', extra=('--max-age-seconds', age), expected=2))

    assert {path: digest(path) for path in initial} == initial and set(workspace.iterdir()) == before
    return [
        'copied_cli_utf8_bom',
        'packaged_fictional_snapshot',
        'declared_admin_and_bridge_status_required',
        'maximum_age_boundary_and_override',
        'future_timestamp_tolerance',
        'invalid_sensor_collection_unavailable',
        'temperature_range_and_finite_values',
        'two_cpu_readings_required',
        'malformed_unreadable_or_oversized_input_refused',
        'invalid_cli_time_or_limit_refused',
        'offline_validation_with_process_and_network_audit_guard',
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
    print('SENSORSNAPSHOT_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
