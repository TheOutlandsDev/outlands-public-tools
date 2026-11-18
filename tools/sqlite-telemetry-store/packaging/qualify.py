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
ARCHIVE = 'sqlite-telemetry-store-0.1.0.zip'


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
    assert tuple(int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')) == (2, 0, 0, 0)
    test_ids = [node.get('classname') + '.' + node.get('name') for node in suite.findall('testcase')]
    assert len(set(test_ids)) == len(test_ids) == 2

    env['PYTHONPATH'] = str(source)
    report = run([python, '-B', '-W', 'error', '-c', r'''
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory

from sentinel_monitor import models, storage

root = Path(sys.argv[1]).resolve() / 'sentinel_monitor'
assert Path(storage.__file__).resolve() == root / 'storage.py'
assert Path(models.__file__).resolve() == root / 'models.py'
epoch = datetime(2000, 2, 1, 10, 0, tzinfo=timezone.utc)
boot = epoch - timedelta(hours=1)
tables = ('samples', 'disk_metrics', 'gpu_metrics', 'sensor_metrics', 'process_metrics',
          'alerts', 'hardware_events')


def event(instant, *, channel='Synthetic System'):
    return models.HardwareEvent(
        channel=channel, record_id=7, timestamp=instant, category='Synthetic hardware',
        severity='warning', provider='Synthetic Provider', event_id=99,
        message='Synthetic hardware event',
    )


def alert(instant, *, value=82.0):
    return models.AlertEvent(
        timestamp=instant, severity='warning', key='synthetic:temperature', label='Synthetic sensor',
        value=value, threshold=80.0, unit='C', message='Synthetic temperature warning',
    )


def snapshot(instant, *, events=None):
    gpu = models.GpuReading(
        index=0, uuid='synthetic-gpu', name='Synthetic GPU', temperature_c=42.0,
        utilization_percent=5.0, memory_utilization_percent=None, memory_used_mb=100.0,
        memory_total_mb=1024.0, power_draw_w=None, power_limit_w=None, fan_percent=None,
        pstate='', graphics_clock_mhz=None, memory_clock_mhz=None,
    )
    return models.SystemSnapshot(
        timestamp=instant, cpu_percent=24.0, per_cpu_percent=[24.0], cpu_frequency_mhz=None,
        memory_total_bytes=1024, memory_used_bytes=256, memory_available_bytes=768,
        memory_percent=25.0, swap_total_bytes=0, swap_used_bytes=0, swap_percent=0.0,
        disks=[models.DiskReading('synthetic-disk', '/sample-volume', 'Synthetic', 1024, 256, 768, 25.0)],
        disk_read_bps=0.0, disk_write_bps=0.0, network_receive_bps=0.0, network_send_bps=0.0,
        gpus=[gpu],
        hardware_sensors=[models.HardwareSensor('synthetic-temp', 'Synthetic SSD', 'Temperature',
                                               'Composite', 40.0, 'C')],
        processes=[models.ProcessReading(9, 'synthetic-worker', 1.0, 1.0, 102)],
        uptime_seconds=3600.0,
        hardware_events=[event(instant)] if events is None else list(events),
    )


@contextmanager
def opened(path, **kwargs):
    store = storage.SqliteStore(path, **kwargs)
    try:
        yield store
    finally:
        store.close()


def counts(connection):
    return tuple(connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                 for table in tables)


def rejects_integrity_error(operation):
    try:
        operation()
    except sqlite3.IntegrityError:
        return
    raise AssertionError('Expected SQLite to reject the invalid record')


with TemporaryDirectory(prefix='telemetry-sqlite-', dir=Path.cwd()) as temporary:
    work = Path(temporary)

    wal_path = work / 'wal.db'
    with opened(wal_path) as store:
        session = store.start_session(boot)
        assert session.session_id and not session.previous_unclean
        store.log_snapshot(snapshot(epoch), [alert(epoch)])
        with closing(sqlite3.connect(wal_path)) as reader:
            assert reader.execute('PRAGMA journal_mode').fetchone() == ('wal',)
            assert counts(reader) == (1, 1, 1, 1, 1, 1, 1)
            assert reader.execute('SELECT cpu_percent FROM samples').fetchone() == (24.0,)
            assert reader.execute('SELECT uuid FROM gpu_metrics').fetchone() == ('synthetic-gpu',)
            assert reader.execute('SELECT last_sample_at FROM sessions').fetchone() == (epoch.isoformat(),)
    with opened(wal_path) as reopened:
        assert not reopened.start_session(boot).previous_unclean
    with closing(sqlite3.connect(wal_path)) as reader:
        rows = reader.execute('SELECT clean_exit, ended_at FROM sessions').fetchall()
        assert len(rows) == 2 and all(clean == 1 and ended_at for clean, ended_at in rows)
        assert counts(reader) == (1, 1, 1, 1, 1, 1, 1)

    dedup_path = work / 'hardware-events.db'
    with opened(dedup_path) as store:
        store.log_snapshot(snapshot(epoch), [])
        later = epoch + timedelta(seconds=1)
        store.log_snapshot(snapshot(later, events=(event(later), event(later, channel='Synthetic Application'))), [])
    with closing(sqlite3.connect(dedup_path)) as reader:
        assert reader.execute('SELECT COUNT(*) FROM samples').fetchone() == (2,)
        rows = reader.execute('SELECT channel, timestamp FROM hardware_events ORDER BY channel').fetchall()
        assert rows == [('Synthetic Application', later.isoformat()), ('Synthetic System', epoch.isoformat())]

    unique_path = work / 'unique-samples.db'
    with opened(unique_path) as store:
        store.log_snapshot(snapshot(epoch), [alert(epoch)])
        rejects_integrity_error(lambda: store.log_snapshot(snapshot(epoch), [alert(epoch)]))
    with closing(sqlite3.connect(unique_path)) as reader:
        assert counts(reader) == (1, 1, 1, 1, 1, 1, 1)

    rollback_path = work / 'transaction-rollback.db'
    with opened(rollback_path) as store:
        store.start_session(boot)
        store.log_snapshot(snapshot(epoch), [])
        later = epoch + timedelta(seconds=1)
        rejects_integrity_error(lambda: store.log_snapshot(snapshot(later), [alert(later, value=None)]))
        with closing(sqlite3.connect(rollback_path)) as reader:
            assert counts(reader) == (1, 1, 1, 1, 1, 0, 1)
            assert reader.execute('SELECT last_sample_at FROM sessions').fetchone() == (epoch.isoformat(),)
        store.log_snapshot(snapshot(later), [alert(later)])
    with closing(sqlite3.connect(rollback_path)) as reader:
        assert counts(reader) == (2, 2, 2, 2, 2, 1, 1)
        assert reader.execute('SELECT last_sample_at FROM sessions').fetchone() == (later.isoformat(),)

    for name, next_boot, description in (
        ('same-boot.db', boot, 'application interruption'),
        ('different-boot.db', boot + timedelta(hours=2), 'system restart'),
    ):
        path = work / name
        with opened(path) as store:
            store.start_session(boot)
            store.log_snapshot(snapshot(epoch), [])
            store.close(clean_exit=False)
        with opened(path) as reopened:
            diagnostic = reopened.start_session(next_boot)
            assert diagnostic.previous_unclean and description in diagnostic.message
            assert epoch.isoformat() in diagnostic.message

    retention_path = work / 'retention.db'
    with opened(retention_path, retention_days=1) as store:
        store.start_session(boot)
        store.log_snapshot(snapshot(epoch), [alert(epoch)])
        middle = epoch + timedelta(days=1)
        store.log_snapshot(snapshot(middle, events=(event(middle, channel='Synthetic Middle'),)), [alert(middle)])
        with closing(sqlite3.connect(retention_path)) as reader:
            assert counts(reader) == (2, 2, 2, 2, 2, 2, 2)
        latest = epoch + timedelta(days=2)
        store.log_snapshot(snapshot(latest, events=(event(latest, channel='Synthetic Latest'),)), [alert(latest)])
    with closing(sqlite3.connect(retention_path)) as reader:
        kept = [(middle.isoformat(),), (latest.isoformat(),)]
        assert counts(reader) == (2, 2, 2, 2, 2, 2, 2)
        assert reader.execute('PRAGMA foreign_key_check').fetchall() == []
        for table in ('samples', 'alerts', 'hardware_events'):
            assert reader.execute(f'SELECT timestamp FROM {table} ORDER BY timestamp').fetchall() == kept
        assert reader.execute('SELECT COUNT(*) FROM sessions').fetchone() == (1,)

    disabled_path = work / 'disabled' / 'storage.db'
    with opened(disabled_path, enabled=False) as disabled:
        assert disabled.status == 'Disabled'
        session = disabled.start_session(boot)
        assert not session.session_id and not session.previous_unclean
        disabled.log_snapshot(snapshot(epoch), [alert(epoch)])
    assert not disabled_path.exists() and not disabled_path.parent.exists()

print(json.dumps({
    'checks': [
        'wal_snapshot_persistence_and_clean_session',
        'hardware_event_deduplication_by_channel',
        'duplicate_snapshot_rejected',
        'invalid_child_insert_rolls_back_snapshot',
        'same_boot_application_interruption',
        'different_boot_system_restart',
        'retention_cutoff_and_child_cascades',
        'disabled_storage_creates_no_file',
    ],
    'sqlite_version': sqlite3.sqlite_version,
}))
''', source], workspace)
    probe = json.loads(report.stdout)
    api_checks = probe['checks']
    assert isinstance(probe['sqlite_version'], str) and probe['sqlite_version']
    assert len(api_checks) == len(set(api_checks)) == 8 and not report.stderr
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    evidence = dict(status='PASS', package='sqlite-telemetry-store', version='0.1.0', platform=sys.platform,
        python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=2, passed=2, failures=0, errors=0, skipped=0, test_ids=test_ids,
        api_checks=api_checks, synthetic_samples=True, sqlite_version=probe['sqlite_version'], dependencies=installed, pip_version=versions['pip'],
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with receipt_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('SQLITETELEMETRY_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
