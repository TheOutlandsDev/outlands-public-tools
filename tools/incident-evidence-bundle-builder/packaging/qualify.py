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
PACKAGE = 'incident-evidence-bundle-builder'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
ORIGINAL_TESTS = {
    'test_cli.CLITests.test_incident_bundle',
}
FOCUSED_TESTS = {
    'test_incident_bundle_safety.IncidentBundleSafetyTests.test_redacts_known_fields_and_assignment_lines',
    'test_incident_bundle_safety.IncidentBundleSafetyTests.test_manifest_matches_written_members',
    'test_incident_bundle_safety.IncidentBundleSafetyTests.test_binary_attachment_refused_without_output',
    'test_incident_bundle_safety.IncidentBundleSafetyTests.test_oversized_attachment_refused_without_output',
    'test_incident_bundle_safety.IncidentBundleSafetyTests.test_late_destination_is_not_overwritten',
    'test_incident_bundle_safety.IncidentBundleSafetyTests.test_existing_destination_is_not_overwritten',
    'test_incident_bundle_safety.IncidentBundleSafetyTests.test_input_files_remain_unchanged',
    'test_incident_bundle_safety.IncidentBundleSafetyTests.test_force_refuses_output_alias',
    'test_incident_bundle_safety.IncidentBundleSafetyTests.test_invalid_diagnostic_refused_without_output',
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


def check_offline_cli(run, source, workspace):
    python = [sys.executable, '-B', '-S', '-W', 'error']
    cli = [*python, '-m', 'opskit']
    env = {'PYTHONPATH': str(source)}
    home = workspace / 'fixture home'
    home.mkdir()
    saved = ('doctor.json', 'inventory.json', 'ports.json', 'note.txt')
    for name in saved:
        (home / name).write_bytes((source / 'examples' / name).read_bytes())
    saved_before = {home / name: digest(home / name) for name in saved}

    options = (
        '--home', home, 'incident', 'bundle', '--doctor', 'doctor.json',
        '--inventory', 'inventory.json', '--ports', 'ports.json', '--json',
    )

    def valid(result):
        assert not result.stderr
        value = json.loads(result.stdout)
        assert value['ok'] is True and value['command'] == 'incident-bundle'
        return value['data']

    def invoke(output, *args):
        return valid(run([*cli, *options, '--output', output, *args], extra_env=env))

    def refused(output, *args, selected=options):
        result = run([*cli, *selected, '--output', output, *args], expected=2, extra_env=env)
        assert not result.stdout and result.stderr
        assert all(mark not in result.stderr for mark in ('Traceback', secret_marker, str(workspace), str(source)))

    def read_bundle(path, receipt, expected_names):
        assert receipt['sha256'] == digest(path)
        assert receipt['bytes'] == path.stat().st_size
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            assert len(archive.namelist()) == len(expected_names) + 1
            assert set(archive.namelist()) == set(expected_names) | {'manifest.json'}
            members = {name: archive.read(name) for name in expected_names}
            manifest = json.loads(archive.read('manifest.json'))
        assert set(manifest) == {'created_at', 'opskit_version', 'privacy', 'files'}
        assert len(manifest['files']) == len(expected_names)
        rows = {row['name']: row for row in manifest['files']}
        assert rows.keys() == members.keys()
        for name, raw in members.items():
            row = rows[name]
            assert row['bytes'] == len(raw) and row['sha256'] == hashlib.sha256(raw).hexdigest()
            assert row['generated'] is (not name.startswith('attachments/'))
            assert isinstance(row['redacted'], bool)
        assert receipt['generated_files'] == 3
        assert receipt['included_attachments'] == sum(name.startswith('attachments/') for name in members)
        return members, rows

    help_text = run([*cli, 'incident', 'bundle', '--help'], extra_env=env)
    assert not help_text.stderr
    assert all(flag in help_text.stdout for flag in ('--doctor', '--inventory', '--ports', '--output', '--include', '--max-file-bytes'))

    diagnostic_names = {'doctor.json', 'inventory.json', 'ports.json'}
    output = workspace / 'saved-diagnostics.zip'
    receipt = invoke(output)
    members, _ = read_bundle(output, receipt, diagnostic_names)
    for name in ('inventory.json', 'ports.json'):
        assert json.loads(members[name]) == json.loads((home / name).read_bytes())

    def secret_values(value, *, field):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == field:
                    yield item
                else:
                    yield from secret_values(item, field=field)
        elif isinstance(value, list):
            for item in value:
                yield from secret_values(item, field=field)

    doctor = json.loads((home / 'doctor.json').read_bytes())
    doctor_backup = json.loads(members['doctor.json'])
    secrets = list(secret_values(doctor, field='api_key'))
    assert secrets and all(secret != '[REDACTED]' for secret in secrets)
    assert list(secret_values(doctor_backup, field='api_key')) == ['[REDACTED]'] * len(secrets)

    extra = home / 'fictional note #2.txt'
    secret_marker = 'invented-nonoperational-marker'
    extra.write_text(f'password={secret_marker}\nPlain evidence line.\n', encoding='utf-8', newline='\n')
    saved_before[extra] = digest(extra)
    output = workspace / 'saved-with-text.zip'
    receipt = invoke(output, '--include', 'note.txt', '--include', extra.name)
    attachment_names = {'attachments/01-note.txt', 'attachments/02-fictional_note_2.txt'}
    members, rows = read_bundle(output, receipt, diagnostic_names | attachment_names)
    assert rows['doctor.json']['redacted'] is True
    assert rows['attachments/01-note.txt']['redacted'] is True
    assert rows['attachments/02-fictional_note_2.txt']['redacted'] is True
    exported_note = members['attachments/01-note.txt'].decode()
    assert '[REDACTED]' in exported_note
    kept = [line for line in (home / 'note.txt').read_text(encoding='utf-8').splitlines()
            if not line.strip().lower().startswith('password')]
    assert kept and all(line in exported_note for line in kept)
    assert members['attachments/02-fictional_note_2.txt'] == b'password=[REDACTED]\nPlain evidence line.\n'
    assert all(secret.encode() not in members['doctor.json'] for secret in secrets)

    binary = home / f'{secret_marker}-binary.txt'
    binary.write_bytes(b'fictional\x00invalid\xff')
    large = home / 'oversized.txt'
    large.write_bytes(b'note\n' * (2 * 1024 * 1024 // 5 + 1))
    invalid = home / f'{secret_marker}-invalid.json'
    invalid.write_text(f'{{"fictional": {secret_marker}}}', encoding='utf-8')
    invalid_options = (*options[:5], invalid.name, *options[6:])
    saved_before.update({path: digest(path) for path in (binary, large, invalid)})

    initial = set(workspace.iterdir())
    failure = workspace / 'refused.zip'
    refused(failure, '--include', binary.name)
    refused(failure, '--include', large.name)
    refused(failure, selected=invalid_options)
    refused(failure, f'--{secret_marker}')
    assert set(workspace.iterdir()) == initial
    assert not failure.exists()

    occupied = workspace / 'occupied.zip'
    sentinel = b'pre-existing unrelated fictional bytes'
    occupied.write_bytes(sentinel)
    refused(occupied)
    assert occupied.read_bytes() == sentinel
    alias = home / 'doctor.json'
    refused(alias, '--force')
    assert digest(alias) == saved_before[alias]
    receipt = invoke(occupied, '--force')
    assert receipt['forced_replace'] is True
    read_bundle(occupied, receipt, diagnostic_names)

    audit = """
import os
from pathlib import Path
import runpy
import sys

source, sandbox = map(Path, sys.argv[1:3])
sys.path.insert(0, str(source))
sys.argv = ['opskit', *sys.argv[3:]]


def require_output_path(path, descriptor=None):
    candidate = Path(os.fsdecode(path))
    if not candidate.is_absolute() and descriptor is not None and descriptor >= 0 and sys.platform.startswith('linux'):
        candidate = Path(os.readlink(f'/proc/self/fd/{descriptor}')) / candidate
    assert candidate.is_absolute() and '..' not in candidate.parts
    relative = candidate.relative_to(sandbox)
    assert not relative.parts or relative == Path('checked.zip') or relative.parts[0].startswith('.opskit-incident-')


def verify_offline(event, args):
    if event in {'subprocess.Popen', 'os.exec', 'os.system', 'os.spawn', 'os.posix_spawn', 'os.startfile',
                 'os.kill', 'ctypes.dlopen', 'winreg.OpenKey', 'winreg.QueryValue'}:
        raise AssertionError('Unexpected process, registry, or installer access')
    if event.startswith('socket.'):
        raise AssertionError('Incident builder attempted network access')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        require_output_path(args[0])
    if event in {'os.rename', 'os.link'}:
        require_output_path(args[0], args[2])
        require_output_path(args[1], args[3])
    if event in {'os.remove', 'os.rmdir'}:
        require_output_path(args[0], args[1])
    if event == 'os.mkdir':
        require_output_path(args[0], args[2])
    if event in {'tempfile.mkdtemp', 'tempfile.mkstemp', 'shutil.rmtree'}:
        require_output_path(args[0])
    if event in {'os.symlink', 'os.truncate', 'os.chmod', 'os.utime'}:
        raise AssertionError('Unexpected filesystem mutation')


sys.addaudithook(verify_offline)
import opskit
assert Path(opskit.__file__).parent == source / 'opskit'
runpy.run_module('opskit', run_name='__main__', alter_sys=True)
"""
    sandbox = workspace / 'audit-output'
    sandbox.mkdir()
    audited_output = sandbox / 'checked.zip'
    report = valid(run([sys.executable, '-I', '-B', '-W', 'error', '-c', audit, source, sandbox,
                        *options, '--output', audited_output, '--include', 'note.txt']))
    read_bundle(audited_output, report, diagnostic_names | {'attachments/01-note.txt'})
    assert list(sandbox.iterdir()) == [audited_output]
    assert {path: digest(path) for path in saved_before} == saved_before

    return [
        'fictional_bundle_help',
        'saved_diagnostics_archive_members',
        'attachment_member_names',
        'manifest_hashes_and_receipt',
        'known_line_redaction',
        'known_json_key_redaction',
        'binary_attachment_refused',
        'oversized_input_refused',
        'invalid_json_opaque_diagnostics',
        'existing_output_no_overwrite',
        'explicit_force_input_alias_safeguard',
        'offline_scoped_zip_audit_guard',
        'extracted_source_and_inputs_unchanged',
    ]


def qualify(packages, workspace, report, receipt, reference):
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
    cli_checks = check_offline_cli(run, source, workspace)
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
    print('INCIDENT_BUNDLE_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
