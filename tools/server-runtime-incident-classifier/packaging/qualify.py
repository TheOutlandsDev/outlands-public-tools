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
PACKAGE = 'server-runtime-incident-classifier'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_runtime_classifier.OriginalServerRuntimeTests.test_scheduled_maintenance_is_warning_not_critical_outage',
    'test_runtime_classifier.OriginalServerRuntimeTests.test_online_runtime_scheduler_warning_is_not_labeled_outage',
    'test_runtime_classifier.OriginalServerRuntimeTests.test_planned_off_runtime_keeps_automation_warning_separate',
}
FOCUSED_TESTS = {
    'test_classifier.ServerRuntimeClassifierTests.test_missing_runtime_status_falls_back_to_down',
    'test_classifier.ServerRuntimeClassifierTests.test_quiet_planned_off_runtime_is_suppressed',
    'test_classifier.ServerRuntimeClassifierTests.test_rejects_malformed_server_rows_and_issue_arrays',
    'test_classifier.ServerRuntimeClassifierTests.test_unexpected_online_runtime_reports_planned_off_mismatch',
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
    down_issues = ['listener absent', 'process missing', 'probe failed', 'no restart yet', 'fifth issue']
    samples = [
        {'id': 'fixture-down', 'name': 'Fictional archive', 'status': 'down', 'issues': down_issues},
        {
            'id': 'fixture-maintenance', 'name': 'Fictional schedule', 'status': 'warning',
            'runtime_status': 'MAINTENANCE', 'observed_runtime_status': 'down',
            'issues': ['scheduled test window'],
        },
        {
            'id': 'fixture-retired', 'name': 'Fictional retired', 'status': 'warning',
            'runtime_status': 'planned_off', 'expected_state': 'planned_off',
            'issues': ['intentional idle'], 'automation_issues': [],
        },
        {
            'id': 'fixture-mismatch', 'name': 'Fictional mismatch', 'status': 'warning',
            'runtime_status': 'online', 'observed_runtime_status': 'ONLINE',
            'expected_state': 'PLANNED_OFF',
        },
        {
            'id': 'fixture-scheduler', 'name': 'Fictional scheduler', 'status': 'warning',
            'runtime_status': 'online', 'issues': ['scheduler check warning'],
            'automation_issues': ['fixture automation warning'],
        },
        {
            'id': 'fixture-retired-automation', 'name': 'Fictional retirement', 'status': 'warning',
            'runtime_status': 'planned_off', 'expected_state': 'planned_off',
            'automation_issues': ['fixture approval pending'],
        },
        {'id': 'fixture-healthy', 'name': 'Fictional healthy', 'status': 'healthy', 'issues': ['ignored issue']},
    ]
    samples[0]['extra'] = 'fixture server extra field'
    payload = {'servers': samples, 'extra': 'fixture root extra field'}

    def encode(value, encoding='utf-8', *, sort_keys=False):
        return json.dumps(value, ensure_ascii=False, sort_keys=sort_keys).encode(encoding)

    bad_row = {'id': 'fixture', 'name': 'Fictional invalid', 'status': 'warning'}
    fixtures = {
        'samples.json': encode(payload, 'utf-8-sig'),
        'reordered-keys.json': encode(payload, sort_keys=True),
        'empty.json': encode({'servers': []}),
        'suppressed.json': encode({'servers': [samples[2], samples[-1]]}),
        'invalid-root.json': encode([]),
        'missing-servers.json': encode({}),
        'invalid-servers.json': encode({'servers': {}}),
        'invalid-row.json': encode({'servers': [None]}),
        'invalid-identity.json': encode({'servers': [{**bad_row, 'id': ''}]}),
        'invalid-issues.json': encode({'servers': [{**bad_row, 'issues': 'fixture issue'}]}),
        'invalid-issue-member.json': encode({'servers': [{**bad_row, 'issues': [12]}]}),
        'invalid-automation.json': encode({'servers': [{**bad_row, 'automation_issues': None}]}),
        'invalid-automation-member.json': encode({'servers': [{**bad_row, 'automation_issues': [False]}]}),
        'invalid-json.json': b'{',
        'invalid-encoding.json': b'\xff',
        'duplicate-key.json': b'{"servers":[],"servers":[]}',
        'nonfinite.json': b'{"servers":[],"extra":NaN}',
        'overflow.json': b'{"servers":[],"extra":1e999}',
        'oversized.json': b' ' * (4 * 1024 * 1024 + 1),
    }
    for name, raw in fixtures.items():
        (workspace / name).write_bytes(raw)

    example = source / 'examples/servers.json'
    initial = {path: digest(path) for path in [example, *(workspace / name for name in fixtures)]}
    before = set(workspace.iterdir())
    env = {'PYTHONPATH': str(source)}
    base = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*base, '-m', 'server_runtime']

    def output(process):
        assert not process.stderr
        response = json.loads(process.stdout)
        assert set(response) == {'incidents'}
        assert isinstance(response['incidents'], list)
        assert 'fixture root extra field' not in process.stdout
        assert 'fixture server extra field' not in process.stdout
        for incident in response['incidents']:
            assert set(incident) == {'source', 'code', 'severity', 'summary', 'evidence', 'fingerprint'}
            assert set(incident['evidence']) == {
                'issues', 'automation_issues', 'notes', 'runtime_status', 'observed_runtime_status',
                'expected_state', 'expected_state_reason', 'impact', 'suggested_action',
            }
            assert incident['code'] == 'health'
            fingerprint_input = '{source}|{code}|{summary}'.format(**incident).encode('utf-8')
            assert incident['fingerprint'] == hashlib.sha256(fingerprint_input).hexdigest()
        return response['incidents']

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
        raise AssertionError('Server classification attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('Server classification attempted a write')
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkstemp'}:
        raise AssertionError('Server classification attempted a filesystem mutation')


sys.addaudithook(verify_offline)
import server_runtime
assert Path(server_runtime.__file__).resolve().parent == source / 'server_runtime'
runpy.run_module('server_runtime', run_name='__main__', alter_sys=True)
"""
    incidents = output(run([*base, '-c', audit, source, '--input', workspace / 'samples.json'], extra_env=env))
    assert output(invoke('reordered-keys.json')) == incidents
    assert output(invoke('empty.json')) == output(invoke('suppressed.json')) == []
    assert [entry['source'] for entry in incidents] == [
        'server:fixture-down', 'server:fixture-maintenance', 'server:fixture-mismatch',
        'server:fixture-scheduler', 'server:fixture-retired-automation',
    ]
    down, maintenance, mismatch, online_warning, retired_warning = incidents
    assert down['severity'] == 'critical' and down['evidence']['runtime_status'] == 'down'
    assert down['evidence']['issues'] == down_issues
    assert down['summary'].startswith('Fictional archive runtime is DOWN:')
    assert all(issue in down['summary'] for issue in down_issues[:4])
    assert down_issues[-1] not in down['summary']
    assert down['evidence']['impact'].startswith('OUTAGE -')
    assert maintenance['severity'] == 'warning' and 'SCHEDULED MAINTENANCE' in maintenance['summary']
    assert maintenance['evidence']['observed_runtime_status'] == 'down'
    assert maintenance['evidence']['impact'].startswith('SCHEDULED MAINTENANCE -')
    assert mismatch['severity'] == 'warning' and 'ONLINE but configured PLANNED OFF' in mismatch['summary']
    assert mismatch['evidence']['expected_state'] == 'planned_off'
    assert mismatch['evidence']['observed_runtime_status'] == 'online'
    assert mismatch['evidence']['impact'].startswith('STATE MISMATCH -')
    assert online_warning['severity'] == 'warning' and 'runtime is ONLINE' in online_warning['summary']
    assert online_warning['evidence']['automation_issues'] == ['fixture automation warning']
    assert online_warning['evidence']['impact'].startswith('NO OUTAGE -')
    assert retired_warning['severity'] == 'warning' and 'runtime is PLANNED OFF' in retired_warning['summary']
    assert retired_warning['evidence']['automation_issues'] == ['fixture approval pending']
    assert retired_warning['evidence']['impact'].startswith('NO OUTAGE -')

    packaged = output(run([*cli, '--input', example], extra_env=env))
    assert [entry['source'] for entry in packaged] == [
        'server:fictional-archive', 'server:fictional-scheduled',
        'server:fictional-mismatch', 'server:fictional-scheduler',
    ]
    assert [entry['severity'] for entry in packaged] == ['critical', 'warning', 'warning', 'warning']
    assert [entry['evidence']['runtime_status'] for entry in packaged] == ['down', 'maintenance', 'online', 'online']

    def refused(result):
        assert result.stderr and not result.stdout and 'Traceback' not in result.stderr

    for name in ('invalid-root.json', 'missing-servers.json', 'invalid-servers.json', 'invalid-row.json',
                 'invalid-identity.json', 'invalid-json.json', 'invalid-encoding.json', 'duplicate-key.json',
                 'nonfinite.json', 'overflow.json', 'oversized.json', 'missing.json', '.'):
        refused(invoke(name, expected=2))
    for name in ('invalid-issues.json', 'invalid-issue-member.json',
                 'invalid-automation.json', 'invalid-automation-member.json'):
        refused(invoke(name, expected=2))
    refused(run([*cli], expected=2, extra_env=env))
    refused(run([*cli, '--input', example, '--unknown'], expected=2, extra_env=env))

    assert {path: digest(path) for path in initial} == initial and set(workspace.iterdir()) == before
    return [
        'copied_cli_utf8_bom',
        'packaged_fictional_servers',
        'runtime_outage_and_missing_status_fallback',
        'scheduled_maintenance_warning',
        'quiet_planned_off_and_healthy_suppressed',
        'planned_off_online_mismatch',
        'automation_warnings_separate_from_outage',
        'incident_shape_and_stable_fingerprint',
        'malformed_unreadable_or_oversized_input_refused',
        'invalid_issue_lists_and_cli_arguments_refused',
        'offline_classification_with_process_and_network_audit_guard',
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
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_runtime_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('SERVERRUNTIME_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
