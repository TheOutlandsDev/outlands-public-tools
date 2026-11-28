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
PACKAGE = 'query-capture-result-verifier'
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
    'tests/test_capture_summary.py::CaptureSummaryTests::test_summary_requires_full_nonempty_match_without_order_check',
    'tests/test_capture_summary.py::CaptureSummaryTests::test_summary_does_not_accept_inconsistent_comparison_status',
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
    script = source / 'query_capture_result_verifier.py'
    probe = workspace / 'cli-probe'
    probe.mkdir()
    copied = probe / script.name
    copied.write_bytes(script.read_bytes())
    manifest_path = probe / 'manifest.json'
    contract_path = probe / 'contract.json'
    fixture = json.loads((source / 'examples/manifest.json').read_bytes())
    contract = json.loads((source / 'examples/contract.json').read_bytes())
    comparison = fixture['comparison']

    def invoke(manifest=fixture, policy=contract, *, expected=0):
        for path, value in ((manifest_path, manifest), (contract_path, policy)):
            path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode('utf-8'))
        before = {item.name: digest(item) for item in probe.iterdir()}
        result = run(
            [python, '-I', '-B', '-W', 'error', copied, '--contract', contract_path, '--manifest', manifest_path],
            cwd=probe, expected=expected,
        )
        assert {item.name: digest(item) for item in probe.iterdir()} == before
        if expected:
            assert not result.stdout and result.stderr
            assert all(value not in result.stderr for value in ('Traceback', 'DO-NOT-ECHO', str(probe)))
            return result.stderr
        assert not result.stderr
        assert 'DO-NOT-ECHO' not in result.stdout
        return json.loads(result.stdout)

    def evaluate(changes, *, policy=contract):
        return invoke({**fixture, 'comparison': {**comparison, **changes}}, policy)

    first = invoke()
    assert first['status'] == 'matched' and first['matched_rows'] == 2
    assert first['parity_status'] == 'not_established'
    assert first['parameters'] == fixture['parameters']
    assert first['columns_compared'] == 9 and first['elapsed_seconds'] == 0.25
    assert evaluate(dict.fromkeys(('expected_rows', 'actual_rows', 'matched_rows'), 0))['status'] == 'empty_not_validated'

    for count, status in ((1, 'matched'), (9_999, 'matched'), (10_000, 'matched'),
                          (10_001, 'mismatch'), (-1, 'mismatch'), (False, 'mismatch'), (2.0, 'mismatch')):
        result = evaluate(dict.fromkeys(('expected_rows', 'actual_rows', 'matched_rows'), count))
        assert result['status'] == status and result['parity_status'] == 'not_established'

    for changes in (
        {'status': 'mismatch'}, {'status': None}, {'columns_compared': 8},
        {'actual_rows': 1}, {'matched_rows': 1}, {'expected_only_rows': 1},
        {'actual_only_rows': 1}, {'sql_metadata_match': False},
        {'all_values_match': False}, {'sql_metadata_match': 'true'}, {'all_values_match': 1},
    ):
        assert evaluate(changes)['status'] == 'mismatch'
    assert invoke({**fixture, 'comparison': []})['status'] == 'mismatch'
    missing_status = dict(comparison)
    del missing_status['status']
    assert invoke({**fixture, 'comparison': missing_status})['status'] == 'mismatch'

    ordered = {**contract, 'ordered': True}
    order_evidence = {'order_check_applicable': True, 'ordered_group_keys_match': True}
    assert evaluate(order_evidence, policy=ordered)['status'] == 'matched'
    assert evaluate(order_evidence)['status'] == 'mismatch'
    assert invoke(policy=ordered)['status'] == 'mismatch'
    assert evaluate({**order_evidence, 'ordered_group_keys_match': False}, policy=ordered)['status'] == 'mismatch'
    for enabled in (True, False):
        missing_order = {**comparison, 'order_check_applicable': enabled}
        del missing_order['ordered_group_keys_match']
        assert invoke({**fixture, 'comparison': missing_order}, {**contract, 'ordered': enabled})['status'] == 'mismatch'

    invalid = invoke({**fixture, 'parameters': {**fixture['parameters'], 'EndDate': 'DO-NOT-ECHO'}})
    assert invalid['status'] == 'failed' and invalid['error_category'] == 'invalid_window'
    for start, end in (
        (contract['start'], contract['start']),
        (contract['start'], '2020-04-02T00:00:01'),
        ('1752-12-31T23:59:59', '1753-01-01T00:00:00'),
        ('2020-04-01T00:00:00Z', contract['end']),
        ('DO-NOT-ECHO', contract['end']),
    ):
        assert '24 hours' in invoke(policy={**contract, 'start': start, 'end': end}, expected=2)
    early = {**contract, 'start': '1753-01-01T00:00:00', 'end': '1753-01-01T00:00:01'}
    assert invoke({**fixture, 'parameters': {'StartDate': early['start'], 'EndDate': early['end']}}, early)['status'] == 'matched'

    failed = invoke({'status': 'failed', 'manifest_path': 'DO-NOT-ECHO',
                     'error': {'category': 'authentication', 'sqlstate': '28000', 'raw': 'DO-NOT-ECHO',
                               'evidence_stage': 'manifest_read', 'evidence_failure': 'missing'}})
    assert failed['status'] == 'failed' and failed['error_category'] == 'authentication'
    assert failed['error_sqlstate'] == '28000' and failed['evidence_stage'] == 'manifest_read'
    assert failed['evidence_failure'] == 'missing' and 'manifest_path' not in failed
    unknown = invoke({'status': 'failed', 'error': dict.fromkeys(
        ('category', 'sqlstate', 'guidance', 'evidence_stage', 'evidence_failure'), 'DO-NOT-ECHO',
    )})
    assert unknown['error_category'] == 'capture_failed' and unknown['error_sqlstate'] == 'N/A'
    assert 'evidence_stage' not in unknown and 'evidence_failure' not in unknown

    exact = json.dumps(fixture).encode('utf-8').ljust(1_048_576, b' ')
    assert invoke(exact) == first
    assert 'exceeds' in invoke(exact + b' ', expected=2)
    assert 'exceeds' in invoke(policy=b' ' * 1_048_577, expected=2)
    bom = bytes.fromhex('efbbbf')
    assert invoke(bom + json.dumps(fixture).encode(), bom + json.dumps(contract).encode()) == first
    for raw in (b'\xff', b'{"value":NaN}', b'{"status":1,"status":2}', b'{invalid'):
        assert 'valid UTF-8 JSON' in invoke(raw, expected=2)
    assert 'JSON object' in invoke(b'[]', expected=2)
    assert 'JSON boolean' in invoke(policy={**contract, 'ordered': 1}, expected=2)
    assert 'positive integer' in invoke(policy={**contract, 'expected_columns': False}, expected=2)
    assert invoke() == first and copied.read_bytes() == script.read_bytes()
    return [
        'nonempty_match_and_empty_not_validated',
        'inclusive_10000_row_cap',
        'reject_inconsistent_count_value_metadata_or_status',
        'required_and_absent_ordering_evidence',
        'date_window_and_parameter_agreement',
        'allowlisted_errors_without_raw_evidence',
        'bounded_strict_json_and_read_only_output',
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
    print('QUERY_CAPTURE_RESULT_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
