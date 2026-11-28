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
PACKAGE = 'sql-driver-diagnostic-classifier'
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
    "tests/test_driver_diagnostics.py::ConnectionDiagnosticTests::test_driver_diagnostics_do_not_echo_credentials",
    "tests/test_driver_diagnostics.py::ConnectionDiagnosticTests::test_tls_diagnostics_classify_allowlisted_causes_without_raw_text",
    "tests/test_driver_diagnostics.py::ConnectionDiagnosticTests::test_tls_native_codes_support_localized_messages",
    "tests/test_driver_diagnostics.py::ConnectionDiagnosticTests::test_tls_messages_without_native_codes_and_unknown_fallback",
    "tests/test_driver_diagnostics.py::ConnectionDiagnosticTests::test_windows_security_context_keeps_priority_over_tls_wording",
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
        self.subtests = 0
        self.problem = False

    def pytest_collection_finish(self, session):
        self.collected = [item.nodeid for item in session.items]

    def pytest_runtest_logreport(self, report):
        if report.failed or report.skipped or hasattr(report, 'wasxfail'):
            self.problem = True
        elif report.when == 'call' and report.passed:
            if isinstance(report, pytest.SubtestReport):
                self.subtests += 1
            else:
                self.passed.append(report.nodeid)


source = Path(sys.argv[1])
sys.path.insert(0, str(source))
proof = Evidence()
exit_code = pytest.main(['-q', '-p', 'no:cacheprovider', 'tests'], plugins=[proof])
assert exit_code == 0 and not proof.problem
assert sorted(proof.collected) == sorted(proof.passed)
assert proof.subtests == 27
print(json.dumps({'test_ids': sorted(proof.passed), 'subtests': proof.subtests}))
"""
    result = run([python, '-I', '-B', '-W', 'error', '-c', code, source], cwd=source)
    assert not result.stderr
    evidence = json.loads(result.stdout.strip().splitlines()[-1])
    identifiers = evidence['test_ids']
    assert len(identifiers) == len(ORIGINAL_TESTS)
    assert set(identifiers) == ORIGINAL_TESTS
    return identifiers, evidence['subtests']


def check_offline_cli(run, python, source, workspace):
    script = source / 'sql_driver_diagnostic_classifier.py'
    probe = workspace / 'cli-probe'
    probe.mkdir()
    copied = probe / script.name
    copied.write_bytes(script.read_bytes())
    fixture = source / 'examples/diagnostic.json'
    sample = json.loads(fixture.read_bytes())
    candidate = probe / 'diagnostic.json'
    private = ('sample-host.invalid', 'fictional-login', 'fictional-password',
               'DO-NOT-ECHO', '0x80090322', '-2146893022', '2148074274')

    def invoke(data=sample, *, expected=0):
        candidate.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode('utf-8'))
        before = {item.name: digest(item) for item in probe.iterdir()}
        result = run([python, '-I', '-B', '-W', 'error', copied, '--input', candidate],
                     cwd=probe, expected=expected)
        assert {item.name: digest(item) for item in probe.iterdir()} == before
        assert all(value not in result.stdout + result.stderr for value in private)
        if expected:
            assert not result.stdout and result.stderr
            assert 'Traceback' not in result.stderr and str(probe) not in result.stderr
            return result.stderr
        assert not result.stderr
        return json.loads(result.stdout)

    first = invoke()
    assert set(first) == {'sqlstate', 'category', 'reason', 'guidance'}
    assert first['sqlstate'] == '08001' and first['category'] == 'tls_validation'
    assert first['reason'] == 'certificate_hostname_mismatch'
    assert 'Encryption remains enabled' in first['guidance']
    for state, text, category in (
        ('28000', 'Login failed for fictional-login; PWD=fictional-password', 'authentication'),
        ('HYT00', 'Network timeout at sample-host.invalid', 'connectivity'),
        ('08001', 'Unreachable sample-host.invalid', 'connectivity'),
        ('IM002', 'Driver missing: DO-NOT-ECHO', 'driver'),
        ('IM003', 'Driver unavailable: DO-NOT-ECHO', 'driver'),
        ('42000', 'Example query failed: DO-NOT-ECHO', 'database_error'),
    ):
        result = invoke({'sqlstate': state, 'message': text})
        assert result['category'] == category and result['sqlstate'] == state
        assert set(result) == {'sqlstate', 'category', 'guidance'}

    for token, reason in (
        ('0x80090322', 'certificate_hostname_mismatch'),
        ('-2146893022', 'certificate_hostname_mismatch'),
        ('2148074274', 'certificate_hostname_mismatch'),
        ('0x80090325', 'untrusted_certificate_chain'),
        ('-2146893016', 'certificate_expired'),
        ('0x80090326', 'protocol_or_handshake'),
    ):
        result = invoke({'sqlstate': '08001', 'message': f'SSL Provider: Ejemplo ({token})'})
        assert result['reason'] == reason and token not in json.dumps(result)
    for text, reason in (
        ('SSL: certificate hostname mismatch', 'certificate_hostname_mismatch'),
        ('certificate verify failed: self-signed certificate', 'untrusted_certificate_chain'),
        ('certificate has expired', 'certificate_expired'),
        ('TLS handshake failed', 'protocol_or_handshake'),
        ('SSL Provider: invalid token x0x80090322z', 'unknown_tls_error'),
        ('TLS diagnostic DO-NOT-ECHO', 'unknown_tls_error'),
    ):
        assert invoke({'sqlstate': '08001', 'message': text})['reason'] == reason

    priority = invoke({'sqlstate': '28000', 'message': 'SSL Provider: No credentials are available'})
    assert priority['category'] == 'windows_security_context' and 'reason' not in priority
    tls_first = invoke({'sqlstate': '28000', 'message': 'TLS handshake failed; login failed'})
    assert tls_first['category'] == 'tls_validation'

    for invalid in (None, '', 'hy000', 'DO-NOT-ECHO', '08001\n'):
        result = invoke({'sqlstate': invalid, 'message': 'Example database failure'})
        assert result['sqlstate'] == 'UNKNOWN'
    assert invoke({'message': ''})['sqlstate'] == 'UNKNOWN'
    assert invoke({'sqlstate': 'ZZ999', 'message': 'Example database failure'})['sqlstate'] == 'ZZ999'
    for data, error in (
        ({'message': 'DO-NOT-ECHO', 'sqlstate': []}, 'SQLSTATE must be text or null'),
        ({'message': ['DO-NOT-ECHO']}, 'Message must be text'),
        ({'message': 'DO-NOT-ECHO', 'user': 'fictional-login'}, 'must be an object'),
        ({}, 'must be an object'),
        (b'{"message":"DO-NOT-ECHO","message":"duplicate"}', 'valid UTF-8 JSON'),
        (b'{"message":NaN}', 'valid UTF-8 JSON'),
        (b'\xff', 'valid UTF-8 JSON'),
    ):
        assert error in invoke(data, expected=2)

    sample_bytes = json.dumps(sample).encode('utf-8')
    exact = sample_bytes.ljust(65_536, b' ')
    assert invoke(exact) == first
    assert 'exceeds 65,536 bytes' in invoke(exact + b' ', expected=2)
    assert invoke(bytes.fromhex('efbbbf') + sample_bytes) == first
    missing = run([python, '-I', '-B', copied, '--input', probe / 'DO-NOT-ECHO.json'],
                  cwd=probe, expected=2)
    assert not missing.stdout and 'readable regular file' in missing.stderr
    assert 'DO-NOT-ECHO' not in missing.stderr
    assert invoke() == first and copied.read_bytes() == script.read_bytes()
    return [
        'fictional_diagnostic_redacts_message_and_identity',
        'non_tls_categories_and_projected_fields',
        'native_code_forms_and_omission',
        'tls_phrases_and_unknown_fallback',
        'security_context_and_tls_priority',
        'sqlstate_projection_and_safe_invalid_input',
        'bounded_utf8_and_repeatable_read_only_output',
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
    test_ids, subtests = run_tests(run, python, source)

    run([sys.executable, '-I', '-B', source / 'source_check.py'])
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} == names
    assert {name: digest(source / name) for name in names} == before_source
    assert all(digest(wheels / pin['filename']) == pin['sha256'] for pin in selected.values())
    evidence = dict(
        status='PASS', package=PACKAGE, version=VERSION, platform=sys.platform, python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_test_functions=len(ORIGINAL_TESTS), original_test_cases=len(ORIGINAL_TESTS), passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, original_subtests_passed=subtests, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=[], dependencies=selected, test_runner='pytest',
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), pip_version=bootstrap['pip'],
        offline_wheel_install=True, fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('SQL_DRIVER_DIAGNOSTIC_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
