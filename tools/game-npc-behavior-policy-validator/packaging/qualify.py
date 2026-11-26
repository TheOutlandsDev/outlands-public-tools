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
PACKAGE = 'game-npc-behavior-policy-validator'
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
    'tests/test_npc_behavior_policy_validator.py::ComputeBackendTests::test_policy_validator_rejects_unsafe_ranges_and_warns_on_robotic_mix',
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
    script = source / 'npc_behavior_policy_validator.py'
    fixtures = source / 'examples'
    assert {path.name for path in fixtures.iterdir()} == {'balanced.json', 'warning.json', 'invalid.json'}
    before = {path: digest(path) for path in fixtures.iterdir()}
    candidate = workspace / 'candidate.json'

    def invoke(path, *, program='rust', code=0, error=None):
        result = run([python, '-I', '-B', '-W', 'error', script, program, '--input', path], expected=code)
        if error is not None:
            assert not result.stdout and error in result.stderr
            return None
        assert not result.stderr
        return json.loads(result.stdout)

    def check(raw, *, code=0, error=None, program='rust'):
        candidate.write_bytes(raw)
        previous = digest(candidate)
        result = invoke(candidate, code=code, error=error, program=program)
        assert digest(candidate) == previous
        return result

    def policy(values, *, code=0):
        return check(json.dumps({'policy': values}).encode(), code=code)

    valid = invoke(fixtures / 'balanced.json')
    warning = invoke(fixtures / 'warning.json', program='dayz')
    rejected = invoke(fixtures / 'invalid.json', code=1)
    assert valid['valid'] and not valid['warnings'] and not valid['errors']
    assert warning['valid'] and not warning['errors'] and len(warning['warnings']) == 3
    assert not rejected['valid'] and len(rejected['errors']) == 2
    for report in (valid, warning, rejected):
        assert report['schema_version'] == 1 and report['live_activation_allowed'] is False
        assert all(report[flag] is True for flag in (
            'requires_offline_simulation', 'requires_game_specific_review', 'requires_user_approval',
        ))

    limits = {
        'reaction_ms': (150, 2000), 'aim_error_deg': (0.5, 30), 'aggressiveness': (0, 1),
        'coordination': (0, 1), 'retreat_health_percent': (1, 100), 'pursuit_seconds': (0, 300),
        'decision_interval_ms': (100, 5000), 'perception_range_m': (5, 500),
    }
    for index in range(2):
        boundary = {key: value[index] for key, value in limits.items()}
        assert policy(boundary)['normalized_policy'] == boundary
        offset = -0.25 if index == 0 else 0.25
        out_of_range = policy({key: number + offset for key, number in boundary.items()}, code=1)
        assert len(out_of_range['errors']) == len(limits)
    thresholds = {'reaction_ms': 200, 'aim_error_deg': 1, 'aggressiveness': 0.9, 'retreat_health_percent': 5}
    assert not policy(thresholds)['warnings']
    assert not policy({**thresholds, 'aggressiveness': 0.95, 'retreat_health_percent': 10})['warnings']

    assert policy({'reaction_ms': ' 350 ', 'aim_error_deg': '3.50'})['normalized_policy'] == {
        'reaction_ms': 350.0, 'aim_error_deg': 3.5,
    }
    malformed = policy({
        'reaction_ms': 'NaN', 'aim_error_deg': 'Infinity', 'coordination': True,
        'aggressiveness': None, 'perception_range_m': 10**400,
    }, code=1)
    assert len(malformed['errors']) == 5 and not malformed['normalized_policy']
    huge = check(b'{"policy":{"coordination":1e500}}', code=1)
    assert huge['errors'] == ['coordination must be a finite number.']

    unknown = policy({'spare': 1, 'alternate': 2, 'coordination': 0.5}, code=1)
    assert unknown['errors'] == ['Unsupported policy fields: alternate, spare']
    assert unknown['normalized_policy'] == {'coordination': 0.5}
    check(b'{"execute":"unused","policy":{}}', code=2, error='forbidden execution fields')

    check(b'{"policy":[]}', code=2, error='policy must be a JSON object')
    check(b'[]', code=2, error='Policy input must be a JSON object')
    check(b'{"policy":{"reaction_ms":150,"reaction_ms":200}}', code=2, error='Duplicate JSON key')
    check(b'{"policy":{"coordination":NaN}}', code=2, error='Use standard JSON numbers')
    check(b'{"policy":', code=2, error='Invalid UTF-8 JSON')
    check(bytes([255]), code=2, error='Invalid UTF-8 JSON')
    check(b' ' * 2_000_001, code=2, error='exceeds 2,000,000 bytes')
    invoke(workspace / 'missing.json', code=2, error='regular JSON file')

    for program in ('rust', 'dayz', 'main_spt', 'modern_warfare', 'zomboid'):
        assert check(b'{}', program=program)['program'] == program
    arguments = [python, '-I', '-B', '-W', 'error', script, 'rust', '--input', fixtures / 'balanced.json']
    assert run(arguments).stdout == run(arguments).stdout
    assert {path: digest(path) for path in fixtures.iterdir()} == before

    return [
        'fictional_examples_warning_and_error_outcomes',
        'inclusive_bounds_and_warning_thresholds',
        'numeric_normalization_and_nonfinite_refusal',
        'unknown_policy_and_execution_fields',
        'malformed_duplicate_oversized_and_missing_input',
        'all_five_profiles_repeatable_read_only',
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
    print('GAME_NPC_BEHAVIOR_POLICY_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
