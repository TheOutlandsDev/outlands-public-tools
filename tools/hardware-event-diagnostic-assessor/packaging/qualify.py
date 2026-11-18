"""Validate a fresh extraction with the public Python API."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'hardware-event-diagnostic-assessor-0.1.0.zip'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(packages, workspace, receipt_path, receipt, reference=None):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    archive = packages / ARCHIVE
    manifest = packages / 'build-manifest.json'
    build = json.loads(manifest.read_bytes())
    assert build['filename'] == ARCHIVE and build['version'] == '0.1.0'
    assert build['sha256'] == digest(archive) and build['bytes'] == archive.stat().st_size
    if reference is not None:
        assert archive.read_bytes() == (reference / ARCHIVE).read_bytes()
        assert manifest.read_bytes() == (reference / manifest.name).read_bytes()
    sdk = json.loads(receipt.read_bytes())
    lock = json.loads((ROOT / 'PYTHON-LOCK.json').read_bytes())
    minor = f'{sys.version_info.major}.{sys.version_info.minor}'
    pin = lock['python_archives'][sys.platform][minor]
    assert sdk['status'] == 'PASS' and sdk['archive'] == pin
    assert sdk['platform'] == sys.platform and sdk['python_version'] == platform.python_version() == pin['python']
    assert sdk['python_lock_sha256'] == digest(ROOT / 'PYTHON-LOCK.json')
    assert sdk['preparation_helper_sha256'] == digest(ROOT / 'packaging/prepare_python.py')
    assert sdk['executable_sha256'] == digest(Path(sys._base_executable))

    workspace = workspace.resolve()
    workspace.mkdir()
    source = workspace / ARCHIVE.removesuffix('.zip')
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        assert len({item.filename.casefold() for item in members}) == len(members) == build['files']
        for item in members:
            name = item.filename
            parts = name.split('/')
            assert len(parts) > 1 and parts[0] == source.name
            assert str(PurePosixPath(name)) == name and all(part not in ('', '.', '..') for part in parts)
            assert ':' not in name and '\\' not in name and item.file_size < 1024 * 1024
            assert stat.S_ISREG(item.external_attr >> 16)
        assert bundle.testzip() is None
        bundle.extractall(workspace)

    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1')

    def run(args, cwd, expected=0):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                capture_output=True, encoding='utf-8', timeout=90)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    run([sys.executable, '-I', '-B', '-m', 'venv', workspace / 'venv'], workspace)
    python = workspace / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    report_path = workspace / 'pip-private.json'
    wheel_lock = json.loads((source / 'WHEEL-LOCK.json').read_bytes())
    expected_packages = dict(wheel_lock['packages'])
    if os.name != 'nt':
        expected_packages.pop('colorama')
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'install',
         '--index-url', wheel_lock['index'], '--only-binary=:all:', '--require-hashes',
         '--report', report_path, '-r', source / 'requirements-test.txt'], workspace)
    receipt = json.loads(report_path.read_bytes())
    installed = {}
    for item in receipt['install']:
        name = item['metadata']['name'].lower().replace('_', '-')
        pin = expected_packages[name]
        assert name not in installed and item['metadata']['version'] == pin['version']
        download = item['download_info']
        sha256 = download['archive_info']['hashes']['sha256']
        wheel, = [record for record in pin['wheels'] if record['sha256'] == sha256 and record['url'] == download['url']]
        installed[name] = dict(version=pin['version'], filename=wheel['filename'], sha256=sha256)
    assert installed.keys() == expected_packages.keys()
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'check'], workspace)
    versions = json.loads(run([python, '-I', '-B', '-c',
        'import importlib.metadata as m,json; print(json.dumps({d.metadata["Name"].lower().replace("_", "-"): d.version for d in m.distributions()}))'], workspace).stdout)
    assert {n: v for n, v in versions.items() if n not in {'pip', 'setuptools'}} == {n: d['version'] for n, d in installed.items()}
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    junit = workspace / 'pytest-results.xml'
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    run([python, '-B', '-W', 'error', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
         '--junitxml', junit, 'tests'], source)
    suite = ET.parse(junit).getroot().find('testsuite')
    assert tuple(int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')) == (5, 0, 0, 0)
    test_ids = [node.get('classname') + '.' + node.get('name') for node in suite.findall('testcase')]
    assert len(set(test_ids)) == len(test_ids) == 5

    env['PYTHONPATH'] = str(source)
    report = run([python, '-B', '-W', 'error', '-c', '''
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from sentinel_monitor import diagnostic_engine, models


root = Path(sys.argv[1]).resolve() / 'sentinel_monitor'
assert Path(diagnostic_engine.__file__).resolve() == root / 'diagnostic_engine.py'
assert Path(models.__file__).resolve() == root / 'models.py'
zone = timezone(timedelta(hours=-4))
start = datetime(2041, 2, 4, 10, 0, tzinfo=zone)


def assessor(samples=2):
    return diagnostic_engine.DiagnosticEngine(auto_clear_samples=samples, session_started=start)


def gpu(replays):
    return models.GpuReading(
        index=0,
        uuid='synthetic-gpu',
        name='Synthetic GPU',
        temperature_c=40.0,
        utilization_percent=None,
        memory_utilization_percent=None,
        memory_used_mb=None,
        memory_total_mb=None,
        power_draw_w=None,
        power_limit_w=None,
        fan_percent=None,
        pstate='',
        graphics_clock_mhz=None,
        memory_clock_mhz=None,
        pcie_replays_since_reset=replays,
    )


def event(instant, category, event_id, *, provider, message='Synthetic event'):
    return models.HardwareEvent(
        channel='System',
        record_id=event_id,
        timestamp=instant,
        category=category,
        severity='critical',
        provider=provider,
        event_id=event_id,
        message=message,
    )


def snapshot(second=0, *, events=(), replays=0, diagnostics='Active: Windows System log',
             storage='Active: SQLite WAL'):
    return models.SystemSnapshot(
        timestamp=start + timedelta(seconds=second),
        cpu_percent=10.0,
        per_cpu_percent=[10.0],
        cpu_frequency_mhz=None,
        memory_total_bytes=1000,
        memory_used_bytes=200,
        memory_available_bytes=800,
        memory_percent=20.0,
        swap_total_bytes=0,
        swap_used_bytes=0,
        swap_percent=0.0,
        disks=[],
        disk_read_bps=0.0,
        disk_write_bps=0.0,
        network_receive_bps=0.0,
        network_send_bps=0.0,
        gpus=[gpu(replays)],
        hardware_sensors=[],
        processes=[],
        uptime_seconds=100.0 + second,
        source_status={'Windows diagnostics': diagnostics, 'SQLite storage': storage},
        hardware_events=list(events),
    )


historical = assessor()
old_restart = event(start - timedelta(hours=1), 'Unexpected restart', 41,
                    provider='Microsoft-Windows-Kernel-Power')
assessment = historical.evaluate(snapshot(events=(old_restart,)))
assert (assessment.status, assessment.severity) == ('monitoring', 'warning')
assert 'Historical unexpected restart' in assessment.title
cleared = historical.evaluate(snapshot(1))
assert cleared.status == 'resolved' and cleared.auto_cleared
assert cleared.evidence == assessment.evidence

current = assessor()
current_restart = event(start, 'Unexpected restart', 41, provider='Microsoft-Windows-Kernel-Power')
assessment = current.evaluate(snapshot(events=(current_restart,)))
assert (assessment.status, assessment.severity, assessment.confidence) == ('active', 'critical', 'Low')
assert 'during monitoring' in assessment.title and not assessment.automatic_action_taken

whea = assessor()
current_whea = event(start, 'WHEA PCIe', 17, provider='Microsoft-Windows-WHEA-Logger')
assessment = whea.evaluate(snapshot(events=(current_whea,)))
assert (assessment.status, assessment.severity, assessment.confidence) == ('active', 'critical', 'High')
checking = whea.evaluate(snapshot(1, events=(current_whea,)))
assert checking.status == 'monitoring' and '1/2' in checking.verification
assert whea.evaluate(snapshot(2, events=(current_whea,))).auto_cleared

replays = assessor()
first_counter = replays.evaluate(snapshot(replays=2))
assert first_counter.status == 'monitoring' and 'Historical non-zero' in first_counter.title
assert replays.evaluate(snapshot(1, replays=0)).status == 'normal'
assert replays.evaluate(snapshot(2, replays=0)).status == 'normal'
increase = replays.evaluate(snapshot(3, replays=1))
assert (increase.status, increase.severity, increase.confidence) == ('active', 'critical', 'High')
assert increase.evidence == ('GPU 0 PCIe replay counter increased 0 -> 1',)

collector = assessor()
error = collector.evaluate(snapshot(diagnostics='Unavailable: synthetic collector'))
assert error.status == 'active' and error.severity == 'warning'
assert error.automatic_action_taken and 'retrying' in error.recommended_action
acknowledged = collector.acknowledge()
assert acknowledged.status == 'acknowledged' and acknowledged.evidence == error.evidence
assert collector.evaluate(snapshot(1)) == acknowledged
assert collector.evaluate(snapshot(2, events=(current_whea,))).status == 'active'

storage = assessor()
error = storage.evaluate(snapshot(storage='Read error: synthetic SQLite input'))
assert error.evidence == ('Read error: synthetic SQLite input',)
assert error.severity == 'warning'
checking = storage.evaluate(snapshot(1))
assert checking.status == 'monitoring' and '1/2' in checking.verification
recovered = storage.evaluate(snapshot(2))
assert recovered.status == 'resolved' and recovered.auto_cleared

message = 'The previous system shutdown at 4:03:02 PM on 2/3/2041 was unexpected.'
shutdown = event(start - timedelta(hours=1), 'Unexpected shutdown', 6008, provider='EventLog', message=message)
reported = diagnostic_engine.DiagnosticEngine._reported_shutdown_time([shutdown])
assert reported == datetime(2041, 2, 3, 16, 3, 2, tzinfo=zone)
assert reported.utcoffset() == timedelta(hours=-4)

malformed = event(start, 'Unexpected shutdown', 6008, provider='EventLog',
                  message='The previous system shutdown at invalid time on impossible date was unexpected.')
assert diagnostic_engine.DiagnosticEngine._reported_shutdown_time([malformed]) is None
assert diagnostic_engine.DiagnosticEngine._reported_shutdown_time([malformed, shutdown]) == reported

print(json.dumps([
    'historical_restart_auto_clear',
    'current_restart_at_session_boundary',
    'whea_deduplication_and_verified_recovery',
    'pcie_replay_baseline_reset_and_increase',
    'collector_error_acknowledgement_and_reactivation',
    'storage_error_verified_recovery',
    'shutdown_timestamp_parsing',
    'malformed_shutdown_timestamp_ignored',
]))
''', source], workspace)
    api_checks = json.loads(report.stdout)
    assert len(api_checks) == len(set(api_checks)) == 8 and not report.stderr
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    evidence = dict(status='PASS', package='hardware-event-diagnostic-assessor', version='0.1.0', platform=sys.platform,
        python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=5, passed=5, failures=0, errors=0, skipped=0, test_ids=test_ids,
        api_checks=api_checks, synthetic_samples=True, dependencies=installed, pip_version=versions['pip'],
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with receipt_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('HARDWAREDIAG_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
