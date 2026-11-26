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
PACKAGE = 'scheduler-recovery-evidence-classifier'
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
    'tests/test_scheduler_recovery_evidence.py::SchedulerRecoveryTests::test_stale_logon_recovery_failure_becomes_advisory_after_success',
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
    script = source / 'scheduler_recovery_evidence.py'
    fixture = source / 'examples/recovery.json'
    fixture_hash = digest(fixture)
    probe = workspace / 'cli-probe'
    probe.mkdir()
    candidate = probe / 'evidence.json'
    sample = json.loads(fixture.read_bytes())
    failed, healthy = sample['tasks']

    def invoke(path, *, expected=0, error=None):
        result = run([python, '-I', '-B', '-W', 'error', script, '--input', path], cwd=probe, expected=expected)
        if expected:
            assert not result.stdout and 'Traceback' not in result.stderr
            assert error in result.stderr, f'Expected diagnostic containing {error!r}'
            assert str(path) not in result.stderr and 'DO-NOT-ECHO' not in result.stderr
            return ''
        assert not result.stderr
        return result.stdout

    def check(raw, *, expected=0, error=None):
        candidate.write_bytes(raw)
        output = invoke(candidate, expected=expected, error=error)
        assert candidate.read_bytes() == raw
        return output

    def classify(**changes):
        return json.loads(check(json.dumps({**sample, **changes}).encode('utf-8')))

    output = invoke(fixture)
    report = json.loads(output)
    assert report['status'] == 'healthy' and report['automation_status'] == 'advisory'
    assert report['automation_issues'] == []
    assert len(report['automation_notices']) == 1 and 'superseded' in report['automation_notices'][0]
    assert report['tasks'][0]['healthy'] is False and report['tasks'][1]['healthy'] is True
    assert report['tasks'][0]['last_result'] == failed['last_result']

    newest = {**healthy, 'name': 'ExampleFollowUp', 'last_run': '2020-01-03T02:30:00-07:00'}
    unrelated = {**healthy, 'name': 'AnotherProfilesTask', 'last_run': '2020-01-04T00:00:00Z'}
    chosen = classify(expected_tasks=[*sample['expected_tasks'], newest['name']], tasks=[
        newest, unrelated, {**failed, 'name': failed['name'].upper(), 'action': 'DO-NOT-ECHO'}, healthy,
    ])
    assert chosen['automation_status'] == 'advisory'
    assert 'ExampleFollowUp at 2020-01-03T09:30:00+00:00' in chosen['automation_notices'][0]
    assert [task['name'] for task in chosen['tasks']] == [*sample['expected_tasks'], newest['name']]
    assert 'DO-NOT-ECHO' not in json.dumps(chosen)

    for when in ('2020-01-02T22:31:00+01:00', '2020-01-02T21:30:59Z', 'malformed', None):
        warning = classify(tasks=[failed, {**healthy, 'last_run': when}])
        assert warning['automation_status'] == 'attention'
        assert warning['automation_notices'] == [] and len(warning['automation_issues']) == 1
    invalid_failed = classify(tasks=[{**failed, 'last_run': '0001-01-01T00:00:00+01:00'}, healthy])
    assert invalid_failed['automation_status'] == 'attention' and invalid_failed['automation_notices'] == []
    naive = classify(tasks=[failed, {**healthy, 'last_run': '2020-01-03T08:00:00'}])
    assert '08:00:00+00:00' in naive['automation_notices'][0]

    for gates in ({'runtime_status': 'down'}, {'runtime_status': 'maintenance'},
                  {'runtime_status': 'planned_off'}, {'state_healthy': False}, {'state_healthy': None}):
        blocked = classify(**gates)
        assert blocked['automation_status'] == 'attention'
        assert len(blocked['automation_issues']) == 1 and blocked['automation_notices'] == []
    assert classify(runtime_status='down')['status'] == 'down'
    assert classify(state_healthy=False, tasks=[healthy, {**failed, 'last_result': '0x00000000'}])['status'] == 'warning'

    missing = classify(tasks=[failed, unrelated])
    assert missing['automation_status'] == 'attention' and missing['automation_notices'] == []
    assert missing['tasks'][1] == {'name': 'ExampleDailyRestart', 'installed': False}
    assert any('not installed' in issue for issue in missing['automation_issues'])
    disabled = classify(tasks=[failed, {**healthy, 'enabled': False, 'state': 'Running'}])
    assert disabled['tasks'][1]['healthy'] is False and disabled['automation_notices'] == []
    for result in ('0x00000000', '0x00041300', '0x00041301', '0x00041303'):
        assert classify(tasks=[failed, {**healthy, 'last_result': result}])['tasks'][1]['healthy'] is True
    assert classify(tasks=[failed, {**healthy, 'state': 'running', 'last_result': '0x00000001'}])['tasks'][1]['healthy'] is True

    for extra, error in (
        ({'runtime_status': 'bogus'}, 'Unsupported runtime status'),
        ({'state_healthy': 1}, 'JSON boolean'),
        ({'expected_tasks': ['Example', 'example']}, 'Duplicate expected task'),
        ({'tasks': [healthy, {**healthy, 'name': healthy['name'].swapcase()}]}, 'Duplicate observed task'),
        ({'tasks': [{}]}, 'nonempty name'),
        ({'tasks': [{**healthy, 'enabled': 'DO-NOT-ECHO'}]}, 'JSON boolean'),
    ):
        check(json.dumps({**sample, **extra}).encode(), expected=2, error=error)
    for raw, error in (
        (b'[]', 'must contain runtime_status'),
        (b'{"tasks":[],"tasks":[]}', 'Duplicate JSON key'),
        (b'{"tasks":DO-NOT-ECHO', 'Invalid UTF-8 JSON'),
        (b'{"tasks":[],"value":NaN}', 'standard JSON numbers'),
        (bytes([255]), 'Invalid UTF-8 JSON'),
    ):
        check(raw, expected=2, error=error)
    invoke(probe / 'missing.json', expected=2, error='regular file')
    exact = json.dumps(sample).encode().ljust(2_000_000, b' ')
    assert check(exact) == output
    check(exact + b' ', expected=2, error='exceeds 2,000,000 bytes')
    assert invoke(fixture) == output and digest(fixture) == fixture_hash
    assert {entry.name for entry in probe.iterdir()} == {candidate.name}
    return [
        'fictional_recovery_and_original_failed_task_retained',
        'newest_profile_scoped_healthy_run_selected',
        'strict_timestamp_order_and_malformed_refusal_to_downgrade',
        'runtime_and_readiness_gates',
        'task_health_codes_and_missing_or_disabled_tasks',
        'strict_input_and_repeatable_read_only_reporting',
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
    print('SCHEDULER_RECOVERY_EVIDENCE_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
