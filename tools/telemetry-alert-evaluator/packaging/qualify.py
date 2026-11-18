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
ARCHIVE = 'telemetry-alert-evaluator-0.1.0.zip'


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
    assert tuple(int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')) == (3, 0, 0, 0)
    test_ids = [node.get('classname') + '.' + node.get('name') for node in suite.findall('testcase')]
    assert len(set(test_ids)) == len(test_ids) == 3

    env['PYTHONPATH'] = str(source)
    report = run([python, '-B', '-W', 'error', '-c', '''
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

from sentinel_monitor import alerts, config, models


root = Path(sys.argv[1]).resolve() / 'sentinel_monitor'
assert all(Path(module.__file__).resolve() == root / name
           for module, name in ((alerts, 'alerts.py'), (config, 'config.py'), (models, 'models.py')))
start = datetime(2040, 1, 1, tzinfo=UTC)


def snapshot(second=0, *, cpu=10.0, memory=20.0, gpus=(), sensors=()):
    return models.SystemSnapshot(
        timestamp=start + timedelta(seconds=second),
        cpu_percent=cpu,
        per_cpu_percent=[cpu],
        cpu_frequency_mhz=None,
        memory_total_bytes=100,
        memory_used_bytes=20,
        memory_available_bytes=80,
        memory_percent=memory,
        swap_total_bytes=0,
        swap_used_bytes=0,
        swap_percent=0.0,
        disks=[],
        disk_read_bps=0.0,
        disk_write_bps=0.0,
        network_receive_bps=0.0,
        network_send_bps=0.0,
        gpus=list(gpus),
        hardware_sensors=list(sensors),
        processes=[],
        uptime_seconds=100.0 + second,
    )


def engine(sustain=1):
    return alerts.AlertEngine(dict(config.DEFAULT_CONFIG, alert_sustain_samples=sustain))


def gpu(temperature):
    return models.GpuReading(
        index=0,
        uuid='synthetic-gpu',
        name='Synthetic GPU',
        temperature_c=temperature,
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
    )


def sensor(name, value, *, sensor_type='Temperature'):
    return models.HardwareSensor(
        identifier='synthetic-' + name,
        hardware='Synthetic SSD',
        sensor_type=sensor_type,
        name=name,
        value=value,
        unit='°C',
        source='synthetic',
    )


sustained = engine(sustain=3)
assert sustained.evaluate(snapshot(0, cpu=95.0)) == []
assert sustained.evaluate(snapshot(1, cpu=95.0)) == []
assert sustained.evaluate(snapshot(2)) == []
assert sustained.evaluate(snapshot(3, cpu=95.0)) == []
assert sustained.evaluate(snapshot(4, cpu=95.0)) == []
event, = sustained.evaluate(snapshot(5, cpu=95.0))
assert (event.key, event.severity, event.threshold, event.unit) == ('cpu:usage', 'critical', 95.0, '%')
assert sustained.overall_severity() == 'critical'

recovery = engine()
assert recovery.evaluate(snapshot(0, cpu=85.0))
assert recovery.evaluate(snapshot(1)) == []
assert recovery.overall_severity() == 'normal' and not recovery.active
event, = recovery.evaluate(snapshot(2, cpu=85.0))
assert event.severity == 'warning'

repeating = engine()
assert repeating.evaluate(snapshot(0, cpu=85.0))
assert repeating.evaluate(snapshot(1, cpu=86.0)) == []
assert repeating.active['cpu:usage'].value == 86.0
assert repeating.evaluate(snapshot(899, cpu=85.0)) == []
event, = repeating.evaluate(snapshot(900, cpu=85.0))
assert event.timestamp == start + timedelta(minutes=15)
assert repeating.evaluate(snapshot(901, cpu=85.0)) == []

escalation = engine()
warning, = escalation.evaluate(snapshot(0, cpu=94.0))
critical, = escalation.evaluate(snapshot(1, cpu=95.0))
assert (warning.severity, critical.severity) == ('warning', 'critical')
assert escalation.overall_severity() == 'critical'

multiple = engine()
events = multiple.evaluate(snapshot(0, cpu=86.0, gpus=(gpu(90.0),)))
assert [(item.key, item.severity) for item in events] == [
    ('cpu:usage', 'warning'), ('gpu:synthetic-gpu:temperature', 'critical'),
]
assert multiple.overall_severity() == 'critical'
assert multiple.evaluate(snapshot(1, cpu=86.0, gpus=(gpu(40.0),))) == []
assert multiple.overall_severity() == 'warning'

missing = engine(sustain=2)
assert missing.evaluate(snapshot(0, gpus=(gpu(90.0),))) == []
assert missing.evaluate(snapshot(1, gpus=(gpu(90.0),)))
assert missing.evaluate(snapshot(2)) == []
assert missing.overall_severity() == 'normal' and not missing.active
assert missing.evaluate(snapshot(3, gpus=(gpu(90.0),))) == []
assert missing.evaluate(snapshot(4, gpus=(gpu(90.0),)))

limits = tuple(sensor(name, 99.0) for name in (
    'Warning Temperature', 'Critical Temperature', 'Temperature Limit',
    'Temperature Threshold', 'Trip Point', 'TjMax',
))
limits += (sensor('Temperature Label on Load', 99.0, sensor_type='Load'),)
assert not any(models.is_live_temperature_sensor(item) for item in limits)
with_limits = snapshot(sensors=(sensor('Composite Temperature', 42.0), *limits))
assert with_limits.highest_temperature == ('Synthetic SSD / Composite Temperature', 42.0)
assert engine().evaluate(with_limits) == []

storage = engine()
warning, = storage.evaluate(snapshot(0, sensors=(sensor('Composite Temperature', 65.0),)))
critical, = storage.evaluate(snapshot(1, sensors=(sensor('Composite Temperature', 75.0),)))
assert warning.key == critical.key == 'sensor:synthetic-Composite Temperature'
assert warning.label == 'Synthetic SSD / Composite Temperature'
assert (warning.severity, warning.threshold, warning.unit) == ('warning', 65.0, '°C')
assert (critical.severity, critical.threshold, critical.unit) == ('critical', 75.0, '°C')

print(json.dumps([
    'sustained_threshold_and_streak_reset',
    'normal_sample_clears_active_alert',
    'repeat_throttle_interval_boundary',
    'severity_escalation_bypasses_throttle',
    'overall_severity_across_metrics',
    'missing_gpu_clears_active_state',
    'static_temperature_limits_ignored',
    'live_storage_temperature_thresholds',
]))
''', source], workspace)
    api_checks = json.loads(report.stdout)
    assert len(api_checks) == len(set(api_checks)) == 8 and not report.stderr
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    evidence = dict(status='PASS', package='telemetry-alert-evaluator', version='0.1.0', platform=sys.platform,
        python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=3, passed=3, failures=0, errors=0, skipped=0, test_ids=test_ids,
        api_checks=api_checks, synthetic_samples=True, dependencies=installed, pip_version=versions['pip'],
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with receipt_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('TELEMETRYALERT_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
