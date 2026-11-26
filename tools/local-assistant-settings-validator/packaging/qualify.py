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
PACKAGE = 'local-assistant-settings-validator'
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
    'tests/test_local_assistant_settings.py::ConfigTests::test_only_loopback_ollama_is_allowed',
    'tests/test_local_assistant_settings.py::ConfigTests::test_settings_are_bounded',
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
    script = source / 'local_assistant_settings.py'
    fixture = source / 'examples/settings.json'
    fixture_hash = digest(fixture)
    probe = workspace / 'cli-probe'
    probe.mkdir()
    candidate = probe / 'settings.json'

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

    def values(**settings):
        return json.loads(check(json.dumps(settings).encode('utf-8')))

    output = invoke(fixture)
    sample = json.loads(output)
    assert sample['ollama_url'] == 'http://[::1]:11434'
    assert sample['owner_name'] == 'Example Operator' and sample['model'] == 'fictional-main'
    assert sample['temperature'] == 2.0 and sample['context_window'] == 4096
    assert sample['fast_context_window'] == 16384 and sample['max_tool_rounds'] == 30
    assert sample['max_output_tokens'] == 128 and sample['history_messages'] == 100
    assert sample['reasoning'] == 'auto' and sample['settings_version'] == 3

    for url in ('http://127.0.0.1', 'http://localhost:11434/api/', 'http://LOCALHOST:80', 'http://[::1]:11434/'):
        assert values(ollama_url=url)['ollama_url'] == url.rstrip('/')

    refused = (
        ('https://localhost', 'must use local HTTP'),
        ('http://192.0.2.20:11434', 'loopback'),
        ('http://localhost.example.invalid', 'loopback'),
        ('http://DO-NOT-ECHO:p@localhost:11434', 'credentials'),
        ('http://@localhost', 'credentials'),
        ('http://localhost/api?secret=DO-NOT-ECHO', 'query data'),
        ('http://localhost/api?', 'query data'),
        ('http://localhost/#DO-NOT-ECHO', 'fragment'),
        ('http://localhost:DO-NOT-ECHO', 'address or port'),
        ('http://localhost:65536', 'address or port'),
        ('http://[::1]suffix:80', 'address or port'),
        ('http://localhost/\nDO-NOT-ECHO', 'spaces or control characters'),
    )
    for url, error in refused:
        check(json.dumps({'ollama_url': url}).encode(), expected=2, error=error)

    limits = {
        'temperature': (0.0, 2.0), 'context_window': (4096, 131072),
        'fast_context_window': (2048, 16384), 'max_tool_rounds': (1, 30),
        'max_output_tokens': (128, 8192), 'history_messages': (8, 100),
    }
    for index, delta in ((0, -1), (1, 1)):
        bound = {name: pair[index] for name, pair in limits.items()}
        exact = values(**bound)
        clipped = values(**{name: str(number + delta) for name, number in bound.items()})
        assert {name: exact[name] for name in limits} == {name: clipped[name] for name in limits} == bound

    fallback = values(owner_name='   ', model=None, fast_model='', reasoning='unknown',
                      approval_mode='unknown', settings_version='1', fast_routing=False,
                      show_thinking=True)
    assert fallback['owner_name'] == 'Example Owner'
    assert fallback['model'] == 'fictional-main' and fallback['fast_model'] == 'fictional-fast'
    assert fallback['reasoning'] == 'auto' and fallback['approval_mode'] == 'ask'
    assert fallback['settings_version'] == 3
    assert fallback['fast_routing'] is False and fallback['show_thinking'] is True
    assert values(reasoning='high', approval_mode='autonomous')['approval_mode'] == 'autonomous'

    for raw, error in (
        (b'[]', 'JSON object'), (b'{"DO-NOT-ECHO":1}', 'Unknown settings'),
        (b'{"fast_routing":"false"}', 'JSON boolean'),
        (b'{"context_window":true}', 'must be numeric'),
        (b'{"temperature":"NaN"}', 'must be finite'),
        (b'{"temperature":1e999}', 'Invalid UTF-8 JSON'),
        (b'{"temperature":NaN}', 'standard JSON numbers'),
        (b'{"owner_name":"\\ud800"}', 'Invalid UTF-8 JSON'),
        (b'{"model":"","model":""}', 'Duplicate JSON key'),
        (b'{"owner_name":DO-NOT-ECHO', 'Invalid UTF-8 JSON'),
        (bytes([255]), 'Invalid UTF-8 JSON'),
    ):
        check(raw, expected=2, error=error)
    invoke(probe / 'missing.json', expected=2, error='regular file')
    exact = b'{}'.ljust(2_000_000, b' ')
    assert json.loads(check(exact))['context_window'] == 8192
    check(exact + b' ', expected=2, error='exceeds 2,000,000 bytes')

    utf8 = json.dumps({'owner_name': '  Caf\u00e9 Demo  '}, ensure_ascii=False).encode()
    assert check(b'\xef\xbb\xbf' + utf8) == check(utf8)
    assert json.loads(check(utf8))['owner_name'] == 'Caf\u00e9 Demo'
    assert invoke(fixture) == output and digest(fixture) == fixture_hash
    assert {entry.name for entry in probe.iterdir()} == {candidate.name}
    return [
        'fictional_ipv6_sample_and_original_normalization',
        'loopback_http_and_url_refusals',
        'exact_bounds_and_numeric_coercion',
        'fictional_defaults_enums_and_owner_trimming',
        'malformed_duplicate_and_oversized_input_refused',
        'repeatable_utf8_no_input_writes',
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
    print('LOCAL_ASSISTANT_SETTINGS_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
