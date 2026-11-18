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
PACKAGE = 'service-availability-incident-tracker'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_external_probe.ExternalProbeTests.test_overall_states',
    'test_external_probe.ExternalProbeTests.test_incident_open_and_recovery',
    'test_external_probe.ExternalProbeTests.test_atomic_json_round_trip',
}
FOCUSED_TESTS = {
    'test_tracker.TrackerTests.test_optional_checks_do_not_override_successful_required_checks',
    'test_tracker.TrackerTests.test_incident_retains_worst_state_until_recovery',
    'test_tracker.TrackerTests.test_failed_atomic_replace_preserves_existing_state',
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
    beginning = '2041-03-04T05:06:07Z'
    escalation = '2041-03-04T05:08:07Z'
    recovery = '2041-03-04T05:13:07Z'
    degraded = {
        'observedAt': beginning,
        'checks': [{'ok': False}, {'ok': True, 'required': False}],
    }
    offline = {
        'observedAt': escalation,
        'checks': [{'ok': False}, {'ok': False, 'required': False}],
    }
    online = {
        'observedAt': recovery,
        'checks': [{'ok': True}, {'ok': False, 'required': False}],
    }

    samples = {
        'complete.json': json.dumps([degraded, offline, online]).encode('utf-8-sig'),
        'opening.json': json.dumps([degraded]).encode(),
        'finishing.json': json.dumps([offline, online]).encode(),
        'invalid-observations.json': json.dumps([offline, dict(
            online, checks=[{'ok': 1}]
        )]).encode(),
        'invalid-required.json': json.dumps([dict(
            online, checks=[{'ok': True, 'required': 1}]
        )]).encode(),
        'unordered.json': json.dumps([offline, degraded]).encode(),
        'naive-time.json': json.dumps([dict(degraded, observedAt=beginning[:-1])]).encode(),
        'invalid-json.json': b'{',
        'invalid-encoding.json': b'\xff',
        'oversized.json': b' ' * (4 * 1024 * 1024 + 1),
    }
    for name, raw in samples.items():
        (workspace / name).write_bytes(raw)

    state_dir = workspace / 'owned-state'
    state_dir.mkdir()
    state_path = state_dir / 'state.json'
    invalid_state = state_dir / 'invalid-state.json'
    invalid_state.write_text('[]', encoding='utf-8')
    sibling = state_dir / 'sibling.json'
    sibling.write_text('{"fictional": true}', encoding='utf-8')
    example = source / 'examples/observations.json'
    paths = [example, *(workspace / name for name in samples), invalid_state, sibling]
    initial = {path: digest(path) for path in paths}
    before = set(workspace.iterdir())
    env = {'PYTHONPATH': str(source)}
    base = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*base, '-m', 'availability_tracker']

    def output(result):
        assert not result.stderr
        payload = json.loads(result.stdout)
        assert set(payload) == {'state', 'completedIncidents'}
        return payload

    audit_replay = """
import os
from pathlib import Path
import runpy
import sys


source = Path(sys.argv.pop(1))
state_arg = sys.argv.pop(1)
state = Path(state_arg).resolve() if state_arg else None


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn'} or event.startswith('socket.'):
        raise AssertionError('Offline replay attempted process or network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        assert state is not None, 'Replay without state attempted file writes'
        if not isinstance(args[0], int):
            target = Path(os.fsdecode(args[0])).resolve()
            # NamedTemporaryFile first audits the directory passed to its opener.
            assert target == state.parent or (target.parent == state.parent and target.suffix == '.tmp')
    if event == 'tempfile.mkstemp':
        assert state is not None, 'Replay without state attempted to create a temporary file'
        target = Path(os.fsdecode(args[0])).resolve()
        assert target.parent == state.parent and target.suffix == '.tmp'
    if event in {'os.rename', 'os.remove', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink', 'os.truncate'}:
        assert state is not None, 'Replay without state attempted directory changes'
        if event == 'os.rename':
            temporary = Path(os.fsdecode(args[0])).resolve()
            assert temporary.parent == state.parent and temporary.suffix == '.tmp'
            assert Path(os.fsdecode(args[1])).resolve() == state
        elif event == 'os.remove':
            temporary = Path(os.fsdecode(args[0])).resolve()
            assert temporary.parent == state.parent and temporary.suffix == '.tmp'
        elif event == 'os.mkdir':
            assert Path(os.fsdecode(args[0])).resolve() == state.parent
        else:
            raise AssertionError('Replay attempted an unapproved file operation')


sys.addaudithook(verify_offline)
import availability_tracker
assert Path(availability_tracker.__file__).resolve().parent == source / 'availability_tracker'
runpy.run_module('availability_tracker', run_name='__main__', alter_sys=True)
"""

    def audited(path, save_path=None):
        arguments = [*base, '-c', audit_replay, source, save_path or '', '--observations', path]
        if save_path is not None:
            arguments.extend(('--state', save_path))
        return run(arguments, extra_env=env)

    complete = output(audited(workspace / 'complete.json'))
    assert not state_path.exists()
    assert complete['state'] == {
        'schemaVersion': 1,
        'previousOverall': 'online',
        'previousObservedAt': recovery,
        'activeIncident': None,
        'lastTransition': {'from': 'offline', 'to': 'online', 'at': recovery},
    }
    assert complete['completedIncidents'] == [{
        'startedAt': beginning,
        'initialState': 'degraded',
        'worstState': 'offline',
        'recoveredAt': recovery,
        'durationSeconds': 420,
    }]
    packaged = output(run([*cli, '--observations', example], extra_env=env))
    assert packaged['state']['previousOverall'] == 'online' and packaged['state']['activeIncident'] is None
    assert len(packaged['completedIncidents']) == 1
    incident = packaged['completedIncidents'][0]
    assert (incident['initialState'], incident['worstState'], incident['durationSeconds']) == ('degraded', 'offline', 420)

    opening = output(audited(workspace / 'opening.json', state_path))
    assert not opening['completedIncidents']
    assert opening['state']['previousOverall'] == 'degraded'
    assert opening['state']['activeIncident'] == {
        'startedAt': beginning, 'initialState': 'degraded', 'worstState': 'degraded',
    }
    assert json.loads(state_path.read_bytes()) == opening['state']
    original_state = state_path.read_bytes()

    def reject(path, destination=None):
        arguments = [*cli, '--observations', path]
        if destination is not None:
            arguments.extend(('--state', destination))
        rejected = run(arguments, expected=2, extra_env=env)
        assert rejected.stderr and not rejected.stdout and 'Traceback' not in rejected.stderr

    for name in ('invalid-observations.json', 'invalid-required.json', 'unordered.json', 'naive-time.json',
                 'invalid-json.json', 'invalid-encoding.json', 'oversized.json', 'missing.json'):
        reject(workspace / name, state_path)
        assert state_path.read_bytes() == original_state
    reject(workspace, state_path)
    reject(workspace / 'opening.json', state_path)
    assert state_path.read_bytes() == original_state
    reject(workspace / 'finishing.json', invalid_state)
    reject(workspace / 'complete.json', workspace / 'complete.json')
    reject(workspace / 'complete.json', state_dir / '..' / 'complete.json')
    reject(workspace / 'finishing.json', workspace / 'missing-directory' / 'state.json')

    finishing = output(audited(workspace / 'finishing.json', state_path))
    assert finishing == complete
    assert json.loads(state_path.read_bytes()) == complete['state']
    assert set(state_dir.iterdir()) == {state_path, invalid_state, sibling}
    assert {path: digest(path) for path in initial} == initial and set(workspace.iterdir()) == before
    return [
        'copied_cli_utf8_bom',
        'required_and_optional_check_classification',
        'incident_escalation_and_recovery_duration',
        'packaged_fictional_example',
        'persisted_split_replay_matches_single_batch',
        'stale_saved_state_replay_refused',
        'invalid_observations_and_state_preserve_files',
        'malformed_unreadable_or_oversized_input_refused',
        'input_state_alias_and_missing_parent_refused',
        'offline_replay_with_process_and_network_audit_guard',
        'state_writes_scoped_to_named_file_only',
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
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_service_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('INCIDENTTRACKER_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
