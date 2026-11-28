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
PACKAGE = 'query-capture-archive-verifier'
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
    "tests/test_archive_reader.py::CaptureArchiveTests::test_boundary_previous_capture_checks_internal_projection_only",
    "tests/test_archive_reader.py::CaptureArchiveTests::test_fixed_case_reader_rejects_other_case_dates",
    "tests/test_archive_reader.py::CaptureArchiveTests::test_boundary_rejects_projection_claims_or_missing_projection_state",
    "tests/test_archive_reader.py::CaptureArchiveTests::test_boundary_rejects_inconsistent_counts_or_projection_digest",
    "tests/test_archive_reader.py::CaptureArchiveTests::test_previous_manifest_rehydrates_nulls_empty_strings_and_microseconds",
    "tests/test_archive_reader.py::CaptureArchiveTests::test_previous_rejects_tampering_and_wrong_case_or_source",
    "tests/test_archive_reader.py::CaptureArchiveTests::test_previous_rejects_invalid_null_coordinates",
    "tests/test_archive_reader.py::CaptureArchiveTests::test_previous_rejects_timestamps_beyond_six_digits_or_with_timezone",
    "tests/test_archive_reader.py::CaptureArchiveTests::test_previous_rejects_oversized_files_and_duplicate_json_keys",
    "tests/test_archive_reader.py::CaptureArchiveTests::test_previous_rejects_wrong_header_even_with_updated_hash",
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
assert proof.subtests == 0
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
    import csv
    import io

    script = source / 'query_capture_archive_verifier.py'
    probe = workspace / 'cli-probe'
    probe.mkdir()
    copied = probe / script.name
    copied.write_bytes(script.read_bytes())
    template = source / 'examples/detail-template.sql'
    contract_path = source / 'examples/contract.json'
    fixture_contract = json.loads(contract_path.read_bytes())
    local_template = probe / 'template.sql'
    local_contract = probe / 'contract.json'
    manifest_path = probe / 'manifest.json'
    raw_path = probe / 'raw.csv'
    original = {
        name: (json.loads((source / 'examples' / name / 'manifest.json').read_bytes()),
               (source / 'examples' / name / 'raw.csv').read_bytes())
        for name in ('primary', 'boundary')
    }

    def invoke(*, case='primary', manifest=None, raw=None, contract=None, template_bytes=None, expected=0):
        saved_manifest, saved_raw = original[case]
        for path, value in (
            (manifest_path, saved_manifest if manifest is None else manifest),
            (raw_path, saved_raw if raw is None else raw),
            (local_contract, fixture_contract if contract is None else contract),
            (local_template, template.read_bytes() if template_bytes is None else template_bytes),
        ):
            data = value if isinstance(value, bytes) else json.dumps(value).encode()
            path.write_bytes(data)
        before = {entry.name: digest(entry) for entry in probe.iterdir()}
        result = run(
            [python, '-I', '-B', '-W', 'error', copied, '--contract', local_contract,
             '--manifest', manifest_path, '--template', local_template, '--case', case],
            cwd=probe, expected=expected,
        )
        assert {entry.name: digest(entry) for entry in probe.iterdir()} == before
        assert all(value not in result.stdout + result.stderr for value in (
            'Example item', 'example-instance-', 'DEMO-A', 'example-sql.invalid',
            'ExampleInventory', 'Example reviewer', 'DO-NOT-ECHO', 'Traceback', str(probe),
        ))
        if expected:
            assert result.stderr.strip() == 'Capture archive or reviewed contract failed verification'
            assert not result.stdout
            return
        assert not result.stderr
        return json.loads(result.stdout)

    first = invoke()
    assert set(first) == {'status', 'case', 'manifest_sha256', 'raw_csv_sha256',
                          'projection_multiset_sha256', 'row_count', 'null_cell_count',
                          'previous_type_metadata_available', 'historical_projection_digest_available',
                          'projection_digest_check'}
    assert first['status'] == 'verified' and first['case'] == 'primary'
    assert first['row_count'] == 36 and first['null_cell_count'] == 3
    assert first['historical_projection_digest_available'] is True
    assert first['projection_multiset_sha256'] == fixture_contract['cases']['primary']['expected_projection_sha256']
    assert first['raw_csv_sha256'] == digest(raw_path).upper()
    assert first['manifest_sha256'] == digest(manifest_path).upper()
    boundary = invoke(case='boundary')
    assert boundary['row_count'] == 13 and boundary['null_cell_count'] == 2
    assert boundary['historical_projection_digest_available'] is False

    primary, primary_csv = original['primary']
    invoke(raw=primary_csv + b'corrupt', expected=2)
    invoke(template_bytes=template.read_bytes() + b' ', expected=2)
    invoke(manifest={**primary, 'bound_sql_sha256': 'A' * 64}, expected=2)
    invoke(manifest={**primary, 'source_rdl_sha256': 'B' * 64}, expected=2)
    invoke(manifest={**primary, 'parameters': {**primary['parameters'], 'EndDate': '2000-01-02'}}, expected=2)
    invoke(manifest={**primary, 'actual_connection': {**primary['actual_connection'], 'database': 'DO-NOT-ECHO'}}, expected=2)
    invoke(manifest={**primary, 'row_count': True}, expected=2)
    invoke(manifest={**primary, 'projection_multiset_sha256': 'C' * 64}, expected=2)
    invoke(case='boundary', manifest=primary, raw=primary_csv, expected=2)

    def modified_artifact(changes, *, raw=primary_csv, expected=2):
        altered = copy.deepcopy(primary)
        artifact = altered['raw_artifacts']['detail']
        artifact.update(sha256=hashlib.sha256(raw).hexdigest().upper(), **changes)
        return invoke(manifest=altered, raw=raw, expected=expected)

    for path in ('../raw.csv', 'DO-NOT-ECHO.csv', 'other/raw.csv', 'raw.csv:stream'):
        modified_artifact({'path': path})
    portable = modified_artifact({'path': str(raw_path.resolve())}, expected=0)
    assert portable['raw_csv_sha256'] == first['raw_csv_sha256']
    modified_artifact({}, raw=primary_csv.replace(b'RecordedBy', b'ChangedBy', 1))
    modified_artifact({}, raw=primary_csv.replace(b'.456789', b'.4567891', 1))
    modified_artifact({}, raw=primary_csv.replace(b'.456789', b'.456789+00:00', 1))
    modified_artifact({'null_cells': [[0, 7], [0, 7]]})
    modified_artifact({'null_cells': [[0, 0]]})
    modified_artifact({'null_cells': [[False, 7]]})
    modified_artifact({'null_cells_index_base': False})
    modified_artifact({'null_cells_data_rows_exclude_header': 1})
    assert modified_artifact({}, raw=bytes.fromhex('efbbbf') + primary_csv, expected=0)['row_count'] == 36

    for case, expected in (('primary', 2), ('boundary', 0)):
        manifest, raw = original[case]
        altered = copy.deepcopy(manifest)
        changed = raw.replace(b'Example item', b'Changed item', 1)
        rows = list(csv.reader(io.StringIO(changed.decode(), newline='')))[1:]
        encoded = sorted(json.dumps([row[i] for i in (0, 6, 4, 1)], separators=(',', ':')) for row in rows)
        altered['projection_multiset_sha256'] = hashlib.sha256(('[' + ','.join(encoded) + ']').encode()).hexdigest().upper()
        altered['raw_artifacts']['detail']['sha256'] = hashlib.sha256(changed).hexdigest().upper()
        result = invoke(case=case, manifest=altered, raw=changed, expected=expected)
        if expected == 0:
            assert result['projection_multiset_sha256'] == altered['projection_multiset_sha256']

    invoke(manifest=b'{"status":"a","status":"b","raw":"DO-NOT-ECHO"}', expected=2)
    invoke(manifest=b'{"value":NaN}', expected=2)
    invoke(manifest=b'\xff', expected=2)
    invoke(contract={**fixture_contract, 'source_hashes': {}}, expected=2)
    oversized_manifest = 5 * 1024 * 1024 + 1
    valid = json.dumps(primary).encode()
    assert invoke(manifest=valid.ljust(oversized_manifest - 1))['row_count'] == 36
    invoke(manifest=valid.ljust(oversized_manifest), expected=2)
    invoke(contract=b' ' * 65_537, expected=2)

    if os.name != 'nt':
        raw_path.unlink()
        external = workspace / 'outside.csv'
        external.write_bytes(primary_csv)
        raw_path.symlink_to(external)
        result = run(
            [python, '-I', '-B', copied, '--contract', contract_path, '--manifest', manifest_path,
             '--template', template],
            cwd=probe, expected=2,
        )
        assert not result.stdout and raw_path.is_symlink() and external.read_bytes() == primary_csv
        raw_path.unlink()
    assert invoke() == first and copied.read_bytes() == script.read_bytes()
    return [
        'primary_and_boundary_projection_evidence',
        'manifest_template_hash_and_identity_gates',
        'csv_sibling_and_header_safeguards',
        'null_coordinates_and_datetime_precision',
        'independent_projection_rejects_recomputed_tampering',
        'bounded_strict_json_and_optional_bom_csv',
        'read_only_count_and_digest_reporting',
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
    print('QUERY_CAPTURE_ARCHIVE_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
