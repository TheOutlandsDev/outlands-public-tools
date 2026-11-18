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
PACKAGE = 'scheduled-task-preview'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_dashboard_schedule.DashboardScheduleTests.test_dayz_schedule_shows_restart_after_warning_window',
    'test_dashboard_schedule.DashboardScheduleTests.test_running_restart_is_maintenance_not_an_outage',
}
FOCUSED_TESTS = {
    'test_preview.ScheduledTaskPreviewTests.test_omits_disabled_and_uninstalled_tasks',
    'test_preview.ScheduledTaskPreviewTests.test_rejects_naive_and_malformed_timestamps',
    'test_preview.ScheduledTaskPreviewTests.test_formats_warning_and_restart_across_date_rollover',
    'test_preview.ScheduledTaskPreviewTests.test_rejects_malformed_task_fields_and_display_offsets',
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
    warning = {
        'name': 'fictional notices',
        'label': 'Restart',
        'installed': True,
        'enabled': True,
        'state': 'Ready',
        'next_run': '2041-01-02T03:55:00Z',
        'warning_minutes': 15,
    }
    running = {
        'name': 'fictional refresh',
        'label': 'Fictional Refresh',
        'installed': True,
        'enabled': True,
        'state': 'RUNNING',
        'next_run': 'invalid time on already-running task',
    }
    disabled = {**warning, 'name': 'fictional disabled', 'label': 'Omitted Disabled', 'enabled': False}
    uninstalled = {**warning, 'name': 'fictional uninstalled', 'label': 'Omitted Uninstalled', 'installed': False}
    payload = {
        'runtime_status': 'MAINTENANCE',
        'automation_status': 'ready',
        'tasks': [warning, running, disabled, uninstalled],
    }

    def encode(value, encoding='utf-8'):
        return json.dumps(value, ensure_ascii=False).encode(encoding)

    def with_warning(**fields):
        return {**payload, 'tasks': [{**warning, **fields}]}

    fixtures = {
        'samples.json': encode(payload, 'utf-8-sig'),
        'samples-no-bom.json': encode(payload),
        'fallback.json': encode({'status': 'down', 'tasks': []}),
        'empty.json': encode({'tasks': []}),
        'filtered.json': encode({**payload, 'tasks': [disabled, uninstalled]}),
        'invalid-root.json': encode([]),
        'invalid-tasks.json': encode({**payload, 'tasks': {}}),
        'invalid-task.json': encode({**payload, 'tasks': [None]}),
        'invalid-enabled.json': encode(with_warning(enabled='true')),
        'invalid-warning.json': encode(with_warning(warning_minutes=-1)),
        'invalid-time.json': encode(with_warning(next_run='not a timestamp')),
        'naive-time.json': encode(with_warning(next_run='2041-01-02T03:55:00')),
        'out-of-range-time.json': encode(with_warning(next_run='2041-02-30T03:55:00Z')),
        'invalid-json.json': b'{',
        'invalid-encoding.json': b'\xff',
        'duplicate-key.json': b'{"tasks":[],"tasks":[]}',
        'nonfinite.json': b'{"tasks":[],"extra":NaN}',
        'overflow.json': b'{"tasks":[],"extra":1e999}',
        'oversized.json': b' ' * (4 * 1024 * 1024 + 1),
    }
    for name, raw in fixtures.items():
        (workspace / name).write_bytes(raw)

    example = source / 'examples/preview.json'
    initial = {path: digest(path) for path in [example, *(workspace / name for name in fixtures)]}
    before = set(workspace.iterdir())
    env = {'PYTHONPATH': str(source)}
    base = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*base, '-m', 'scheduled_task_preview']

    def output(process):
        assert not process.stderr
        response = json.loads(process.stdout)
        assert set(response) == {'runtime_status', 'next_action', 'schedule'}
        assert all(isinstance(value, str) for value in response.values())
        return response

    def invoke(name, *, offset='-04:00', expected=0):
        flags = ['--input', workspace / name, f'--display-offset={offset}']
        return run([*cli, *flags], expected=expected, extra_env=env)

    audit = """
import os
from pathlib import Path
import runpy
import sys


source = Path(sys.argv.pop(1))


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn'} or event.startswith('socket.'):
        raise AssertionError('Task preview attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Task preview attempted a write')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp'}:
        raise AssertionError('Task preview attempted a filesystem mutation')


sys.addaudithook(verify_offline)
import scheduled_task_preview
assert Path(scheduled_task_preview.__file__).resolve().parent == source / 'scheduled_task_preview'
runpy.run_module('scheduled_task_preview', run_name='__main__', alter_sys=True)
"""
    result = output(run(
        [*base, '-c', audit, source, '--input', workspace / 'samples.json', '--display-offset=-04:00'],
        extra_env=env,
    ))
    assert output(invoke('samples-no-bom.json')) == result
    assert result['runtime_status'] == 'maintenance' and result['next_action'].startswith('No outage')
    assert result['schedule'] == (
        'Restart Jan 2 12:10 AM (warnings Jan 1 11:55 PM) | Fictional Refresh: RUNNING'
    )
    utc = output(invoke('samples.json', offset='Z'))
    assert utc['schedule'] == (
        'Restart Jan 2 4:10 AM (warnings Jan 2 3:55 AM) | Fictional Refresh: RUNNING'
    )
    positive = output(invoke('samples.json', offset='+05:30'))
    assert positive['schedule'] == (
        'Restart Jan 2 9:40 AM (warnings Jan 2 9:25 AM) | Fictional Refresh: RUNNING'
    )
    fallback = output(invoke('fallback.json'))
    assert fallback['runtime_status'] == 'down' and fallback['next_action'].startswith('Verify')
    assert fallback['schedule'] == 'No timed controller'
    assert output(invoke('empty.json'))['runtime_status'] == 'online'
    assert output(invoke('filtered.json'))['schedule'] == 'No timed controller'

    packaged = output(run([*cli, '--input', example, '--display-offset=-04:00'], extra_env=env))
    assert packaged['runtime_status'] == 'maintenance' and packaged['next_action'].startswith('No outage')
    assert packaged['schedule'] == (
        'Restart Jul 28 12:00 PM (warnings Jul 28 11:45 AM) | Health refresh: RUNNING'
    )

    def refused(process):
        assert process.stderr and not process.stdout and 'Traceback' not in process.stderr

    for name in ('invalid-root.json', 'invalid-tasks.json', 'invalid-task.json', 'invalid-enabled.json',
                 'invalid-warning.json', 'invalid-json.json', 'invalid-encoding.json', 'duplicate-key.json',
                 'nonfinite.json', 'overflow.json', 'oversized.json', 'missing.json', '.'):
        refused(invoke(name, expected=2))
    for name in ('invalid-time.json', 'naive-time.json', 'out-of-range-time.json'):
        refused(invoke(name, expected=2))
    for offset in ('+24:00', '-04:60', '-0400', 'local'):
        refused(invoke('samples.json', offset=offset, expected=2))
    refused(run([*cli], expected=2, extra_env=env))
    refused(run([*cli, '--input', example], expected=2, extra_env=env))
    refused(run([*cli, '--input', example, '--display-offset=Z', '--unknown'], expected=2, extra_env=env))

    assert {path: digest(path) for path in initial} == initial and set(workspace.iterdir()) == before
    return [
        'copied_cli_utf8_bom',
        'packaged_fictional_preview',
        'warning_to_restart_interval',
        'running_task_and_maintenance_preview',
        'disabled_and_uninstalled_tasks_suppressed',
        'fixed_offset_date_rollover',
        'malformed_and_unaware_timestamps_refused',
        'invalid_offsets_and_cli_arguments_refused',
        'malformed_unreadable_or_oversized_input_refused',
        'preview_shape_and_runtime_fallback',
        'offline_preview_with_process_and_network_audit_guard',
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
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_scheduler_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('TASKPREVIEW_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
