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
PACKAGE = 'host-readiness-report-builder'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_cli.CLITests.test_doctor_json_flag_can_follow_command',
}
FOCUSED_TESTS = {
    'test_host_readiness.HostReadinessTests.test_disk_absolute_thresholds',
    'test_host_readiness.HostReadinessTests.test_disk_percentage_threshold',
    'test_host_readiness.HostReadinessTests.test_memory_absolute_and_percentage_thresholds',
    'test_host_readiness.HostReadinessTests.test_original_severity_precedence_and_summary',
    'test_host_readiness.HostReadinessTests.test_platform_python_workspace_and_missing_observations',
    'test_host_readiness.HostReadinessTests.test_uncalculated_disk_for_invalid_workspace',
    'test_host_readiness.HostReadinessTests.test_report_is_deterministic_allowlisted_and_preserves_saved_input',
    'test_host_readiness.HostReadinessTests.test_assessment_uses_no_live_host_probes',
    'test_host_readiness.HostReadinessTests.test_invalid_observation_schema_withholds_report',
    'test_host_readiness.HostReadinessTests.test_bad_json_withholds_report_without_echoing_private_values',
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
assert not loader.errors, loader.errors
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


def check_offline_cli(run, source, workspace, incident_tool):
    python = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*python, '-m', 'opskit', 'doctor']
    env = {'PYTHONPATH': str(source)}
    examples = source / 'examples'
    sensitive = ('fictional-private-marker', str(workspace), str(source), 'Traceback')

    def available(result, status, counts):
        assert not result.stderr
        assert all(item not in result.stdout for item in sensitive)
        value = json.loads(result.stdout)
        assert set(value) == {'command', 'schema_version', 'ok', 'warnings', 'data'}
        assert value['command'] == 'doctor' and value['schema_version'] == '1'
        assert value['ok'] is (status != 'fail')
        data = value['data']
        assert set(data) == {'status', 'summary', 'checks', 'read_only', 'duration_hint'}
        assert data['status'] == status and data['read_only'] is True
        assert data['summary'] == dict(zip(('pass', 'warn', 'fail'), counts, strict=True))
        checks = {row['name']: row['status'] for row in data['checks']}
        assert len(checks) == len(data['checks']) == sum(counts)
        assert set(checks) == {
            'supported_os', 'python', 'opskit_home', 'disk_space', 'memory',
            'temporary_directory', 'hostname_resolution',
        }
        return checks

    help_text = run([*cli, '--help'], extra_env=env)
    assert not help_text.stderr and '--observations' in help_text.stdout
    expected = run([*cli, '--observations', examples / 'pass.json', '--json'], extra_env=env)
    assert set(available(expected, 'pass', (7, 0, 0)).values()) == {'pass'}
    repeated = run([*cli, '--observations', examples / 'pass.json', '--json'], extra_env=env)
    assert repeated.stdout == expected.stdout

    warning = run([*cli, '--observations', examples / 'warning.json', '--json'], extra_env=env)
    warning_checks = available(warning, 'warn', (5, 2, 0))
    assert {name for name, status in warning_checks.items() if status == 'warn'} == {
        'disk_space', 'hostname_resolution',
    }
    failing = run([*cli, '--observations', examples / 'failure.json', '--json'], expected=1, extra_env=env)
    failing_checks = available(failing, 'fail', (4, 1, 2))
    assert {name for name, status in failing_checks.items() if status == 'fail'} == {
        'disk_space', 'memory',
    }
    assert failing_checks['temporary_directory'] == 'warn'
    human = run([*cli, '--observations', examples / 'pass.json'], extra_env=env)
    assert human.stdout.strip() and not human.stdout.lstrip().startswith('{')
    assert not human.stderr and all(item not in human.stdout for item in sensitive)

    def refused(path):
        result = run([*cli, '--observations', path, '--json'], expected=2, extra_env=env)
        assert not result.stdout and result.stderr
        assert all(item not in result.stderr for item in (*sensitive, path.name))

    oversized = workspace / 'fictional-private-marker-large.json'
    oversized.write_bytes(b' ' * (16 * 1024 + 1))
    extra = workspace / 'fictional-private-marker-unsupported.json'
    observations = json.loads((examples / 'pass.json').read_bytes())
    observations['hostname'] = 'fictional-private-marker'
    extra.write_text(json.dumps(observations), encoding='utf-8')
    duplicate = workspace / 'fictional-private-marker-duplicate.json'
    duplicate.write_bytes((examples / 'pass.json').read_bytes().replace(b'{', b'{"os":"other",', 1))
    assert duplicate.read_bytes().count(b'"os"') == 2
    refused(examples / 'malformed.json')
    refused(extra)
    refused(duplicate)
    refused(oversized)
    refused(workspace / 'fictional-private-marker-missing.json')

    audit = """
import os
from pathlib import Path
import runpy
import sys

source = Path(sys.argv[1])
sys.path.insert(0, str(source))
sys.argv = ['opskit', *sys.argv[2:]]


def verify_offline(event, args):
    if event.startswith(('socket.', 'ctypes.', 'winreg.')):
        raise AssertionError('Unexpected network or platform probe')
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn',
                 'os.startfile', 'os.kill'}:
        raise AssertionError('Unexpected process invocation')
    writes = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    if event == 'open' and args[2] & writes:
        raise AssertionError('Unexpected file write')
    if event in {'os.rename', 'os.link', 'os.remove', 'os.rmdir', 'os.mkdir', 'os.symlink',
                 'os.truncate', 'os.chmod', 'os.utime', 'tempfile.mkdtemp', 'tempfile.mkstemp',
                 'shutil.rmtree'}:
        raise AssertionError('Unexpected filesystem mutation')


sys.addaudithook(verify_offline)
import opskit
assert Path(opskit.__file__).parent == source / 'opskit'
runpy.run_module('opskit', run_name='__main__', alter_sys=True)
"""
    audited = run([sys.executable, '-I', '-B', '-W', 'error', '-c', audit, source,
                   'doctor', '--observations', examples / 'pass.json', '--json'])
    assert audited.stdout == expected.stdout and not audited.stderr

    run([sys.executable, '-I', '-B', '-W', 'error', source / 'packaging/check_compatibility.py',
         '--incident-tool', incident_tool])

    return [
        'fictional_doctor_help',
        'passing_readiness_json',
        'deterministic_report',
        'warnings_preserve_success_exit',
        'failure_overrides_warning',
        'human_readiness_output',
        'malformed_json_refused',
        'unexpected_fields_refused_without_echo',
        'duplicate_keys_refused',
        'oversized_input_refused',
        'unreadable_input_refused_without_path',
        'offline_read_only_audit_guard',
        'incident_bundle_round_trip',
        'extracted_source_and_inputs_unchanged',
    ]


def qualify(packages, workspace, report, receipt, reference, incident_tool):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    workspace = workspace.resolve()
    sdk = check_interpreter(receipt)
    build, source, names = unpack(packages, workspace, reference)
    before_source = {name: digest(source / name) for name in names}
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
    cli_checks = check_offline_cli(run, source, workspace, incident_tool.resolve())
    run([sys.executable, '-I', '-B', source / 'source_check.py'])
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} == names
    assert {name: digest(source / name) for name in names} == before_source
    evidence = dict(
        status='PASS', package=PACKAGE, version=VERSION, platform=sys.platform, python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=len(ORIGINAL_TESTS), passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=[], dependencies={}, test_runner='unittest',
        fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('HOST_READINESS_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    parser.add_argument('--incident-tool', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build, args.incident_tool)
