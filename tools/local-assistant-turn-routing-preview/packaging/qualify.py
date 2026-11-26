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
PACKAGE = 'local-assistant-turn-routing-preview'
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
    'tests/test_turn_routing_preview.py::RoutingTests::test_short_chat_uses_fast_local_model_without_tools',
    'tests/test_turn_routing_preview.py::RoutingTests::test_operations_request_stays_on_main_model',
    'tests/test_turn_routing_preview.py::RoutingTests::test_iw4x_and_zomboid_requests_route_to_operations_profiles',
    'tests/test_turn_routing_preview.py::RoutingTests::test_program_fix_routes_read_tools_and_workspace_proposal_tools',
    'tests/test_turn_routing_preview.py::RoutingTests::test_management_request_routes_guarded_control_tools',
    'tests/test_turn_routing_preview.py::RoutingTests::test_workspace_edit_routes_only_workspace_tools',
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
    script = source / 'turn_routing_preview.py'
    fixtures = source / 'examples'
    routes = {
        'fast-chat.json': ('fast_chat', 'fast_model', 'fast_context_window', False, None),
        'workspace.json': ('workspace', 'main_model', 'main_context_window', 'medium', None),
        'operations.json': ('operations', 'main_model', 'main_context_window', 'low', 'rust'),
    }
    assert {p.name for p in fixtures.iterdir()} == routes.keys()
    before = {p: digest(p) for p in fixtures.iterdir()}
    probe = workspace / 'cli-probe'
    probe.mkdir()
    candidate = probe / 'route-input.json'
    result_keys = {'kind', 'label', 'model', 'reasoning', 'tool_names', 'context_window', 'operations_program'}
    operations_tools = [
        'operations_status', 'program_log_tail', 'program_inventory', 'program_read_file',
        'program_search_text', 'program_control_capabilities', 'program_control',
    ]
    workspace_tools = [
        'environment_info', 'list_files', 'read_file', 'write_file', 'replace_text', 'make_directory',
        'move_path', 'move_to_trash', 'search_text', 'run_python', 'run_process',
    ]
    base = {
        'main_model': 'qualification-main', 'fast_model': 'qualification-fast', 'fast_routing': True,
        'main_context_window': 8192, 'fast_context_window': 2048, 'configured_reasoning': 'auto',
    }
    marker = 'PRIVATE_VALUE_MUST_STAY_LOCAL'

    def invoke(path, *, expected=0):
        result = run([python, '-I', '-B', '-W', 'error', script, '--input', path], cwd=probe, expected=expected)
        if expected == 2:
            assert result.stderr and not result.stdout
            assert 'Traceback' not in result.stderr and marker not in result.stderr
            assert str(path) not in result.stderr
            return result.stderr
        assert not result.stderr and marker not in result.stdout
        report = json.loads(result.stdout)
        assert set(report) == result_keys
        return report, result.stdout

    def check(raw, *, expected=0):
        candidate.write_bytes(raw)
        previous = digest(candidate)
        result = invoke(candidate, expected=expected)
        assert digest(candidate) == previous
        return result

    def preview(user_text, **settings):
        return check(json.dumps({**base, 'user_text': user_text, **settings}).encode('utf-8'))[0]

    expected_tools = {'fast_chat': [], 'workspace': workspace_tools, 'operations': operations_tools}
    for filename, (kind, model_field, window_field, reasoning, program) in routes.items():
        path = fixtures / filename
        payload = json.loads(path.read_bytes())
        report, _ = invoke(path)
        assert report['kind'] == kind and report['operations_program'] == program
        assert report['model'] == payload[model_field] and report['context_window'] == payload[window_field]
        assert report['reasoning'] == reasoning and report['tool_names'] == expected_tools[kind]
        assert isinstance(report['label'], str) and report['label']

    operation = preview('Fix the Rust server and write a proposed patch to the workspace.')
    assert operation['kind'] == 'operations' and operation['operations_program'] == 'rust'
    assert operation['tool_names'] == operations_tools + workspace_tools
    attached = preview('[attached local file: imaginary.txt] ' + 'q' * 220, context_hint='Rust')
    assert attached['kind'] == 'workspace' and attached['operations_program'] is None
    assert attached['tool_names'] == workspace_tools + operations_tools
    assert attached['reasoning'] == 'medium' and attached['model'] == base['main_model']

    for setting in ({'fast_routing': False}, {'fast_model': ''}):
        main = preview('Hello!', **setting)
        assert main['kind'] == 'main_chat' and main['model'] == base['main_model']
        assert main['context_window'] == base['main_context_window'] and main['reasoning'] == 'low'
        assert main['tool_names'] == [] and main['operations_program'] is None
    assert preview('q' * 180)['kind'] == 'fast_chat'
    assert preview('q' * 181)['kind'] == 'main_chat'
    assert preview('q\nq\nq')['kind'] == 'fast_chat'
    assert preview('q\nq\nq\nq')['kind'] == 'main_chat'
    assert preview('q' * 219, context_hint='Rust')['kind'] == 'operations'
    assert preview('q' * 220, context_hint='Rust')['kind'] == 'main_chat'
    assert preview('Hello!', fast_routing=False, configured_reasoning='high')['reasoning'] == 'high'

    ambiguous = preview('Are DayZ and Rust servers healthy?')
    assert ambiguous['kind'] == 'operations' and ambiguous['operations_program'] == 'all'
    for prompt, program in (
        ('Is the IW4x server running?', 'modern_warfare'),
        ('Is the Project Zomboid server healthy?', 'zomboid'),
    ):
        unique = preview(prompt)
        assert unique['kind'] == 'operations' and unique['operations_program'] == program
    contextual = preview('Is it healthy?', context_hint=' ' * 1000 + 'Rust')
    assert contextual['kind'] == 'operations' and contextual['operations_program'] == 'all'
    assert preview('Is it healthy?', context_hint='Rust' + ' ' * 1000)['kind'] == 'fast_chat'

    prefix = {**base, 'user_text': marker}
    for bad in (
        {key: value for key, value in prefix.items() if key != 'main_model'},
        {**prefix, marker: 'unrecognized'},
        {**prefix, 'user_text': [marker]},
        {**prefix, 'fast_routing': 'false'},
        {**prefix, 'fast_context_window': True},
        {**prefix, 'main_context_window': 0},
        {**prefix, 'context_hint': None},
    ):
        check(json.dumps(bad).encode('utf-8'), expected=2)
    valid_json = json.dumps(prefix).encode('utf-8')
    boundary = valid_json.ljust(2_000_000, b' ')
    assert check(boundary)[0]['kind'] == 'fast_chat'
    for raw in (
        b'[]', b'{"user_text":', valid_json.replace(marker.encode(), bytes([255])), boundary + b' ',
        valid_json[:-1] + b', "fast_routing": false}',
        valid_json.replace(b'"fast_context_window": 2048', b'"fast_context_window": NaN'),
    ):
        check(raw, expected=2)
    invoke(probe / 'missing-route-request.json', expected=2)
    invoke(probe, expected=2)

    request = {
        **base, 'user_text': f'Fix a Rust server draft and write a workspace file named {marker}.',
    }
    raw = json.dumps(request).encode('utf-8')
    candidate.write_bytes(raw)
    report, first = invoke(candidate)
    _, second = invoke(candidate)
    assert first == second and report['tool_names'] == operations_tools + workspace_tools
    assert candidate.read_bytes() == raw
    assert {p.name for p in probe.iterdir()} == {candidate.name}
    assert {p: digest(p) for p in fixtures.iterdir()} == before
    return [
        'fictional_examples_preserve_route_fields',
        'operations_and_attachment_precedence',
        'fast_routing_disable_empty_and_thresholds',
        'context_tail_and_ambiguous_operations_fallback',
        'malformed_oversized_missing_and_invalid_fields',
        'repeatable_read_only_inert_tool_labels',
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
    print('LOCAL_ASSISTANT_TURN_ROUTING_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
