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
PACKAGE = 'sql-result-metadata-validator'
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
    "tests/test_metadata.py::MetadataTests::test_metadata_supports_representable_sql_datetime_types",
    "tests/test_metadata.py::MetadataTests::test_metadata_rejects_datetime2_seventh_fractional_digit",
    "tests/test_metadata.py::MetadataTests::test_metadata_rejects_wrong_columns_types_and_describe_errors",
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
assert proof.subtests == 8
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
    import copy

    script = source / 'sql_result_metadata_validator.py'
    probe = workspace / 'cli-probe'
    probe.mkdir()
    copied = probe / script.name
    copied.write_bytes(script.read_bytes())
    contract_path = probe / 'contract.json'
    metadata_path = probe / 'metadata.json'
    contract = json.loads((source / 'examples/contract.json').read_bytes())
    sample = json.loads((source / 'examples/metadata.json').read_bytes())

    def invoke(rows=sample, reviewed=contract, *, error=None):
        for path, value in ((metadata_path, rows), (contract_path, reviewed)):
            path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
        before = {item.name: digest(item) for item in probe.iterdir()}
        result = run(
            [python, '-I', '-B', '-W', 'error', copied, '--contract', contract_path,
             '--metadata', metadata_path], cwd=probe, expected=2 if error else 0,
        )
        assert {item.name: digest(item) for item in probe.iterdir()} == before
        assert all(value not in result.stdout + result.stderr for value in (
            'DO-NOT-ECHO', 'Traceback', str(probe), *contract['columns'],
        ))
        if error:
            assert not result.stdout
            assert json.loads(result.stderr) == {'status': 'rejected', 'category': error}
            return
        assert not result.stderr
        return json.loads(result.stdout)

    first = invoke()
    assert first == {'status': 'validated', 'column_count': 8}

    def modify(row_index, changes, *, error=None):
        rows = copy.deepcopy(sample)
        for column_index, value in changes.items():
            rows[row_index][column_index] = value
        return invoke(rows, error=error)

    for sql_type, scale in [
        ('datetime', 3), ('smalldatetime', 0), *((f'datetime2({scale})', scale) for scale in range(7)),
    ]:
        assert modify(2, {2: sql_type, 5: scale}) == first
    modify(2, {2: 'datetime2(7)', 5: 7}, error='unsupported_precision')
    for sql_type, scale in (('datetime2(8)', 8), ('datetime2(3)', 6), ('datetimeoffset(6)', 6),
                            ('datetime', 0), ('smalldatetime', 3), ('datetime2(6)', True)):
        modify(2, {2: sql_type, 5: scale}, error='result_shape')
    modify(2, {7: 'DO-NOT-ECHO'}, error='result_shape')

    invoke([sample[1], sample[0], *sample[2:]], error='result_shape')
    invoke(sample[:-1], error='result_shape')
    invoke([{}, *sample[1:]], error='result_shape')
    for changes in ({0: True}, {0: 2}, {1: 'DO-NOT-ECHO'}, {2: 'integer'},
                    {8: 11526}, {9: 'DO-NOT-ECHO'}, {3: False}):
        modify(0, changes, error='result_shape')

    for nullability in (False, True, 0, 1):
        assert modify(0, {6: nullability}) == first
    for nullability in (0.0, 2, '1', None):
        modify(0, {6: nullability}, error='result_shape')
    for sql_type in ('varchar(1)', 'nvarchar(max)', 'char(4)', 'nchar(10)'):
        assert modify(0, {2: sql_type, 3: -1 if sql_type.endswith('(max)') else 8}) == first
    for changes in ({3: -2}, {3: 0}, {4: 1}, {5: 1}, {7: None}, {2: 'nvarchar(0)'}):
        modify(0, changes, error='result_shape')

    labels = [f'Example field {number}' for number in range(1, 9)]
    renamed = [[row[0], label, *row[2:]] for row, label in zip(sample, labels)]
    assert invoke(renamed, {'columns': labels}) == first
    invoke(renamed, error='result_shape')
    for columns in (labels[:-1], [labels[0]] * 8, [*labels[:-1], ''], [*labels[:-1], True]):
        invoke(reviewed={'columns': columns}, error='invalid_contract')
    invoke(reviewed={'columns': labels, 'unexpected': 'DO-NOT-ECHO'}, error='invalid_contract')

    for raw in (b'\xff', b'[NaN]', b'{"column":"DO-NOT-ECHO","column":1}'):
        invoke(raw, error='invalid_input')
    invoke({'columns': []}, error='result_shape')
    raw = json.dumps(sample).encode()
    exact = raw.ljust(1_048_576, b' ')
    assert invoke(exact) == first
    invoke(exact + b' ', error='invalid_input')
    invoke(reviewed=b' ' * 1_048_577, error='invalid_input')
    assert invoke(bytes.fromhex('efbbbf') + raw) == first
    assert invoke() == first and copied.read_bytes() == script.read_bytes()
    return [
        'reviewed_eight_column_layout_and_fixed_report',
        'datetime_scales_zero_through_six',
        'seventh_fractional_digit_rejected',
        'ordinal_metadata_shape_and_describe_errors',
        'character_types_lengths_and_nullability',
        'independent_contract_order_and_reviewed_names',
        'bounded_utf8_safe_diagnostics_and_read_only_inputs',
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
    print('SQL_RESULT_METADATA_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
