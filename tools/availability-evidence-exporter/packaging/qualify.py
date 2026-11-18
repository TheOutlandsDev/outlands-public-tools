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
PACKAGE = 'availability-evidence-exporter'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_availability_export.AvailabilityExportTests.test_safety_projects_only_bounded_guardian_fields',
    'test_availability_export.AvailabilityExportTests.test_signal_contains_only_hash_not_raw_result',
}
FOCUSED_TESTS = {
    'test_exporter.AvailabilityEvidenceTests.test_stale_system_data_is_suppressed',
    'test_exporter.AvailabilityEvidenceTests.test_hash_is_stable_for_reordered_nested_keys',
    'test_exporter.AvailabilityEvidenceTests.test_numeric_bounds_and_malformed_snapshot_sections',
    'test_exporter.AvailabilityEvidenceTests.test_rejects_invalid_signal_state_and_nonfinite_results',
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
    observed = '2040-01-02T03:04:05Z'
    status = 'active: fictional storage coverage'
    system = {
        'disks': [{'percent': 50.0}, {'percent': 80.0}],
        'hardware_sensors': [
            {'hardware': 'Fictional CPU', 'name': 'Package', 'sensor_type': 'Temperature', 'value': 73.25},
            {'hardware': 'Fictional CPU', 'name': 'Fan', 'sensor_type': 'Fan', 'value': 91},
            {'hardware': 'Fictional GPU', 'name': 'Edge', 'sensor_type': 'Temperature', 'value': 94},
        ],
        'hardware_events': [
            {'category': 'Disk Warning', 'severity': 'warning'},
            {'category': 'Storage', 'severity': 'critical'},
            {'category': 'Display', 'severity': 'critical'},
            {'category': 'NVIDIA', 'severity': 'warning'},
            {'category': 'WHEA', 'severity': 'warning'},
            {'category': 'Application crash', 'severity': 'critical'},
        ],
        'source_status': {'Windows diagnostics': status},
        'notes': 'fixture snapshot private field',
    }
    snapshot = {
        'source_health': {'system': {'state': 'fresh'}},
        'system': system,
        'gpus': [{'temperature_c': 62.5}, {'temperature_c': 68.5}],
        'ai': {'hardware_quarantine': {'latched': True}},
    }
    result = {'z': 1, 'nested': {'z': 6, 'a': 'caf\u00e9'}, 'sentinel': 'fixture raw result'}
    reordered_result = {'sentinel': 'fixture raw result', 'nested': {'a': 'caf\u00e9', 'z': 6}, 'z': 1}
    signal = {'state': 'proven', 'method': 'fictional probe', 'observedAtUtc': observed, 'result': result}
    payload = {'snapshot': snapshot, 'signals': [signal]}

    def encode(value, encoding='utf-8'):
        return json.dumps(value, ensure_ascii=False).encode(encoding)

    stale_snapshot = {**snapshot, 'source_health': {'system': {'state': 'stale'}}}
    no_coverage_system = {**system, 'source_status': {'Windows diagnostics': 'active: fictional diagnostics'}}
    no_coverage_snapshot = {**snapshot, 'system': no_coverage_system}
    info_events = [*system['hardware_events'], {'category': 'disk', 'severity': 'information'}]
    info_only = {**snapshot, 'system': {**system, 'hardware_events': info_events[-1:]}}
    samples = {
        'fresh.json': encode(payload, 'utf-8-sig'),
        'stale.json': encode({**payload, 'snapshot': stale_snapshot}),
        'no-coverage.json': encode({**payload, 'snapshot': no_coverage_snapshot}),
        'info-only.json': encode({**payload, 'snapshot': info_only}),
        'reordered.json': encode({'signals': [{**signal, 'result': reordered_result}], 'snapshot': snapshot}),
        'invalid-signal.json': encode({**payload, 'signals': [{**signal, 'state': 'unknown'}]}),
        'missing-result.json': encode({**payload, 'signals': [{key: value for key, value in signal.items() if key != 'result'}]}),
        'invalid-time.json': encode({**payload, 'signals': [{**signal, 'observedAtUtc': '2040-01-02T03:04:05'}]}),
        'invalid-method.json': encode({**payload, 'signals': [{**signal, 'method': None}]}),
        'invalid-snapshot.json': encode({**payload, 'snapshot': []}),
        'invalid-section.json': encode({**payload, 'snapshot': {**snapshot, 'gpus': {}}}),
        'invalid-json.json': b'{',
        'invalid-encoding.json': b'\xff',
        'duplicate-key.json': b'{"snapshot":{},"signals":[],"signals":[]}',
        'nonfinite.json': b'{"snapshot":{},"signals":[{"state":"proven","method":"fixture","observedAtUtc":"2040-01-02T03:04:05Z","result":NaN}]}',
        'overflow.json': b'{"snapshot":{},"signals":[{"state":"proven","method":"fixture","observedAtUtc":"2040-01-02T03:04:05Z","result":1e999}]}',
        'oversized.json': b' ' * (4 * 1024 * 1024 + 1),
    }
    for name, raw in samples.items():
        (workspace / name).write_bytes(raw)

    example = source / 'examples/availability.json'
    initial = {path: digest(path) for path in [example, *(workspace / name for name in samples)]}
    before = set(workspace.iterdir())
    env = {'PYTHONPATH': str(source)}
    base = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*base, '-m', 'availability_evidence']

    def output(process):
        assert not process.stderr
        response = json.loads(process.stdout)
        assert set(response) == {'safety', 'signals'}
        assert isinstance(response['safety'], dict) and isinstance(response['signals'], list)
        assert 'fixture snapshot private field' not in process.stdout
        assert 'fixture raw result' not in process.stdout
        return response

    def invoke(name, *, expected=0):
        return run([*cli, '--input', workspace / name], expected=expected, extra_env=env)

    audit = """
import os
from pathlib import Path
import runpy
import sys


source = Path(sys.argv.pop(1))


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn'} or event.startswith('socket.'):
        raise AssertionError('Availability export attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Availability export attempted a write')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp'}:
        raise AssertionError('Availability export attempted a filesystem mutation')


sys.addaudithook(verify_offline)
import availability_evidence
assert Path(availability_evidence.__file__).resolve().parent == source / 'availability_evidence'
runpy.run_module('availability_evidence', run_name='__main__', alter_sys=True)
"""
    fresh = output(run([*base, '-c', audit, source, '--input', workspace / 'fresh.json'], extra_env=env))
    expected_safety = {
        'diskFreePercent': 20.0,
        'hardwareQuarantine': 'latched',
        'maximumGpuTemperatureC': 68.5,
        'maximumCpuTemperatureC': 73.25,
        'criticalHardwareEvents': ['nvidia', 'storage', 'whea'],
    }
    canonical = '{"nested":{"a":"caf\u00e9","z":6},"sentinel":"fixture raw result","z":1}'.encode('utf-8')
    expected_signal = {
        'state': 'proven',
        'method': 'fictional probe',
        'observedAtUtc': observed,
        'resultSha256': hashlib.sha256(canonical).hexdigest(),
    }
    assert fresh == {'safety': expected_safety, 'signals': [expected_signal]}
    assert output(invoke('reordered.json')) == fresh
    assert output(invoke('stale.json')) == {
        'safety': {
            'diskFreePercent': None,
            'hardwareQuarantine': 'unavailable',
            'maximumGpuTemperatureC': None,
            'maximumCpuTemperatureC': None,
            'criticalHardwareEvents': [],
        },
        'signals': [expected_signal],
    }
    assert output(invoke('no-coverage.json')) == {
        'safety': {**expected_safety, 'hardwareQuarantine': 'unavailable'},
        'signals': [expected_signal],
    }
    assert output(invoke('info-only.json')) == {
        'safety': {**expected_safety, 'criticalHardwareEvents': []},
        'signals': [expected_signal],
    }

    packaged = output(run([*cli, '--input', example], extra_env=env))
    example_canonical = b'{"check":"fictional sample","metrics":{"count":2,"score":8}}'
    assert packaged == {
        'safety': {
            'diskFreePercent': 23.25,
            'hardwareQuarantine': 'clear',
            'maximumGpuTemperatureC': 57.5,
            'maximumCpuTemperatureC': 61.0,
            'criticalHardwareEvents': ['storage'],
        },
        'signals': [{
            'state': 'proven',
            'method': 'fictional availability check',
            'observedAtUtc': observed,
            'resultSha256': hashlib.sha256(example_canonical).hexdigest(),
        }],
    }

    def refused(result):
        assert result.stderr and not result.stdout and 'Traceback' not in result.stderr

    for name in ('invalid-snapshot.json', 'invalid-section.json', 'invalid-json.json',
                 'invalid-encoding.json', 'duplicate-key.json', 'nonfinite.json', 'overflow.json',
                 'oversized.json', 'missing.json', '.'):
        refused(invoke(name, expected=2))
    for name in ('invalid-signal.json', 'missing-result.json', 'invalid-time.json', 'invalid-method.json'):
        refused(invoke(name, expected=2))
    refused(run([*cli], expected=2, extra_env=env))
    refused(run([*cli, '--input', example, '--unknown'], expected=2, extra_env=env))

    assert {path: digest(path) for path in initial} == initial and set(workspace.iterdir()) == before
    return [
        'copied_cli_utf8_bom',
        'packaged_fictional_snapshot',
        'fresh_safety_projection_matches_allowlist',
        'stale_system_suppresses_measurements_and_events',
        'quarantine_requires_storage_coverage',
        'hardware_events_filtered_and_deduplicated',
        'signal_shape_omits_raw_result',
        'canonical_digest_stable_under_nested_key_reordering',
        'malformed_unreadable_or_oversized_input_refused',
        'invalid_signal_or_cli_arguments_refused',
        'offline_export_with_process_and_network_audit_guard',
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
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_availability_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('AVAILABILITYEVIDENCE_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
