"""Validate the released source ZIP on a verified interpreter and a fresh test environment."""

import argparse
import hashlib
import json
import os
from io import BytesIO
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'game-log-snapshot-exporter'
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
    'tests/test_telemetry_exporters.py::TelemetryExporterTests::test_all_five_sanitized_fixtures_parse_expected_events',
    'tests/test_telemetry_exporters.py::TelemetryExporterTests::test_snapshot_contains_no_raw_names_ids_ips_chat_or_log_lines',
    'tests/test_telemetry_exporters.py::TelemetryExporterTests::test_source_files_are_unchanged_by_collect_and_export',
    'tests/test_telemetry_exporters.py::TelemetryExporterTests::test_unsafe_source_pattern_is_rejected',
    'tests/test_telemetry_exporters.py::TelemetryExporterTests::test_denied_and_non_log_files_are_not_discovered',
}


def installed_versions(run, python, prefix):
    code = """
from importlib.metadata import distributions
import json
from pathlib import Path
import sys
from urllib.request import urlopen

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
from urllib.request import urlopen

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


def prepare_verifier(source, workspace):
    pin = json.loads((source / 'VERIFIER-LOCK.json').read_bytes())
    with urlopen(pin['url'], timeout=30) as response:
        data = response.read(pin['bytes'] + 1)
    assert len(data) == pin['bytes'] and hashlib.sha256(data).hexdigest() == pin['sha256']
    target = workspace / 'published-verifier'
    target.mkdir()
    with zipfile.ZipFile(BytesIO(data)) as archive:
        stem = pin['filename'].removesuffix('.zip')
        for name in pin['files']:
            assert Path(name).name == name and name.endswith('.py')
            (target / name).write_bytes(archive.read(f'{stem}/{name}'))
    return target / 'telemetry_snapshot_replay.py', pin['sha256']


def check_offline_cli(run, python, source, workspace, verifier):
    script = source / 'game_log_snapshot_exporter.py'
    fixtures = source / 'examples'
    programs = {
        'rust': ('rust.log', 4), 'dayz': ('dayz.RPT', 4), 'main_spt': ('main_spt.log', 5),
        'modern_warfare': ('modern_warfare.log', 4), 'zomboid': ('zomboid.log', 4),
    }
    assert {path.name for path in fixtures.iterdir()} == {name for name, _ in programs.values()}

    def export(program, pattern, *options, root=fixtures, error=None):
        result = run([
            python, '-I', '-B', '-W', 'error', script, program, '--source-root', root,
            '--pattern', pattern, '--at', '2020-01-02T03:00:00Z', *options
        ], expected=2 if error else 0)
        if error:
            assert error in result.stderr and not result.stdout
            return None
        assert not result.stderr
        return result.stdout

    def check_verifier(mode, path, *, error=None):
        result = run([python, '-E', '-s', '-B', '-W', 'error', verifier, mode, path],
                     expected=2 if error else 0)
        if error:
            assert error in result.stderr and not result.stdout
            return None
        assert not result.stderr
        return json.loads(result.stdout)

    before = {path: digest(path) for path in fixtures.iterdir()}
    snapshot_path = workspace / 'candidate.json'
    for program, (name, count) in programs.items():
        encoded = export(program, name)
        assert encoded == export(program, name)
        snapshot = json.loads(encoded)
        snapshot_path.write_text(encoded, encoding='utf-8', newline='\n')
        expected_label = f'log-001{Path(name).suffix.lower()}'
        assert {record['source_file'] for record in snapshot['records']} == {expected_label}
        assert [row['path'] for row in snapshot['sources']] == [expected_label]
        assert snapshot['record_count'] == count
        assert snapshot['generated_utc'] == '2020-01-02T03:00:00+00:00'
        assert not any(key in record for record in snapshot['records'] for key in ('line', 'message', 'text', 'chat'))
        assert not any(snapshot['runtime'].values())
        assert check_verifier('verify', snapshot_path) == {
            'ok': True, 'program': program, 'record_count': count,
            'snapshot_sha256': snapshot['snapshot_sha256'],
        }
        replay = check_verifier('replay', snapshot_path)
        assert replay['record_count'] == count and replay['program'] == program
        assert not any(replay['runtime'].values())

    changed = json.loads(snapshot_path.read_bytes())
    changed['records'][0]['event'] = 'changed'
    snapshot_path.write_text(json.dumps(changed), encoding='utf-8')
    check_verifier('verify', snapshot_path, error='snapshot hash validation failed')

    output = workspace / 'snapshots'
    stdout = json.loads(export('rust', 'rust.log'))
    receipt = json.loads(export('rust', 'rust.log', '--output-root', output))
    destination = Path(receipt['path'])
    assert destination.parent == output / 'rust'
    assert json.loads(destination.read_bytes()) == stdout
    assert receipt['snapshot_sha256'] == stdout['snapshot_sha256']
    assert check_verifier('verify', destination)['ok']
    written = digest(destination)
    export('rust', 'rust.log', '--output-root', output, error='already exists')
    assert list(destination.parent.iterdir()) == [destination] and digest(destination) == written

    input_root = workspace / 'saved'
    input_root.mkdir()
    for pattern in ('../outside.log', r'..\outside.log', r'C:\saved\*.log', '/saved/*.log'):
        export('zomboid', pattern, root=input_root, error='Unsafe source pattern')
    (input_root / 'secret-token.log').write_bytes(b'user Excluded connected\n')
    (input_root / 'state.sqlite').write_bytes(b'user Excluded connected\n')
    (input_root / 'fixture-name.log').write_bytes(b'user Hazel connected\n')
    export('zomboid', '*', '--output-root', input_root / 'bad', root=input_root,
           error='outside the source tree')
    assert not (input_root / 'bad').exists()
    if sys.platform != 'win32':
        (input_root / 'linked.log').symlink_to(fixtures / 'zomboid.log')
    filtered = json.loads(export('zomboid', '*', root=input_root))
    assert filtered['source_file_count'] == filtered['record_count'] == 1
    assert filtered['sources'][0]['path'] == 'log-001.log'

    tail_root = workspace / 'large'
    tail_root.mkdir()
    payloads = [
        b'player Retired died\n',
        b'user First connected\n',
        b'user Second disconnected\n',
        b'player Forgotten died\n' + b'0' * (512 * 1024) + b'\nuser Latest connected\n',
    ]
    for index, payload in enumerate(payloads):
        path = tail_root / f'batch-{index}.log'
        path.write_bytes(payload)
        os.utime(path, (100 + index, 100 + index))
    tail = json.loads(export('zomboid', '*.log', root=tail_root))
    assert [record['event'] for record in tail['records']] == ['player_join', 'player_leave', 'player_join']
    assert tail['source_file_count'] == 3
    assert tail['sources'][0]['tail_sha256'] == hashlib.sha256(b'user Latest connected\n').hexdigest()
    assert {path: digest(path) for path in fixtures.iterdir()} == before

    return [
        'all_five_profiles_pass_published_verifier_and_replay',
        'fixed_clock_deterministic_and_fixtures_unchanged',
        'absolute_traversal_and_sensitive_sources_refused',
        'bounded_tail_and_newest_three_files',
        'file_output_verified_and_overwrite_refused',
        'published_verifier_refuses_changed_snapshot',
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
    verifier, verifier_digest = prepare_verifier(source, workspace)
    cli_checks = check_offline_cli(run, python, source, workspace, verifier)
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
        test_ids=test_ids, cli_checks=cli_checks, verifier_zip_sha256=verifier_digest, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=[], dependencies=selected, test_runner='pytest',
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), pip_version=bootstrap['pip'],
        offline_wheel_install=True, fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('GAME_TELEMETRY_SNAPSHOT_REPLAY_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
