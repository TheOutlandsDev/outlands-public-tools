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
PACKAGE = 'last-lot-workbook-extractor'
VERSION = '0.1.0'
ARCHIVE = f'{PACKAGE}-{VERSION}.zip'
RECONCILER_RELEASE = 'lot-start-identity-reconciler-v0.1.0'
RECONCILER_SHA256 = 'e32b8f421f0c767332f82e572214cb04d7dcfe90afb53714e5167928cc9907ed'
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



EXPECTED_TESTS = {
    "tests/test_last_lot_workbook.py::test_fictional_rows_preserve_order_and_normalize_text",
    "tests/test_last_lot_workbook.py::test_one_sheet_and_an_explicit_custom_name",
    "tests/test_last_lot_workbook.py::test_headers_keep_the_original_normalization_case_and_blank_column",
    "tests/test_last_lot_workbook.py::test_row_count_and_fixed_table_boundary",
    "tests/test_last_lot_workbook.py::test_duplicate_prefix_is_rejected_after_normalization",
    "tests/test_last_lot_workbook.py::test_duplicate_last_and_next_lot_values_are_rejected",
    "tests/test_last_lot_workbook.py::test_invalid_xlsx_and_macro_package_are_rejected",
}
RUNTIME_DEPENDENCIES = {
    "openpyxl", "et-xmlfile", "defusedxml", "pydantic", "pydantic-core",
    "annotated-types", "typing-inspection", "typing-extensions",
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
    assert len(identifiers) == len(EXPECTED_TESTS)
    assert set(identifiers) == EXPECTED_TESTS
    return identifiers


def check_offline_cli(run, python, source, workspace, reconciler):
    assert digest(reconciler) == RECONCILER_SHA256, 'The reconciler must match the published v0.1.0 source'
    examples = source / 'examples'
    prefix = [python, '-E', '-s', '-B', '-W', 'error']
    script = source / 'last_lot_workbook.py'
    workbook = workspace / 'fictional.xlsx'
    run([*prefix, examples / 'make_workbook.py', workbook])
    original = workbook.read_bytes()

    def invoke(path=workbook, *args, error=None):
        result = run([*prefix, script, path, *args], expected=2 if error else 0)
        if error:
            assert not result.stdout and error in result.stderr
            return None
        assert not result.stderr
        return result.stdout

    first = invoke()
    assert first == invoke() and workbook.read_bytes() == original
    report = json.loads(first)
    assert set(report) == {'last_lots'}
    rows = report['last_lots']
    assert [row['prefix'] for row in rows] == [f'DEMO-{number:02d}-' for number in range(1, 22)]
    assert rows[0] == {'product': 'DEMO-ITEM-01', 'material_template': 'Fictional Template 01',
                       'prefix': 'DEMO-01-', 'last_lot_started': 'DEMO-01-AAAZ', 'next_lot_to_start': 'DEMO-01-AABA'}
    assert rows[1]['material_template'] is None and rows[1]['product'] is None

    edit = """
import sys

from openpyxl import load_workbook

kind = sys.argv[3]
with open(sys.argv[1], 'rb') as stream:
    work = load_workbook(stream)
sheet = work.active
if kind == 'sheet':
    sheet.title = 'Fictional Ledger'
elif kind == 'header':
    sheet['E2'] = 'Wrong heading in a blank column'
elif kind == 'count':
    sheet['C23'] = None
    sheet['C24'] = 'OUTSIDE-TABLE-'
else:
    sheet[kind + '4'] = sheet[kind + '3'].value
work.save(sys.argv[2])
work.close()
"""
    for kind, error in (
        ('sheet', 'only the selected last-lot worksheet'),
        ('header', 'headers changed'),
        ('count', 'record count changed'),
        ('C', 'prefix is not unique'),
        ('D', 'last_lot_started is not unique'),
        ('F', 'next_lot_to_start is not unique'),
    ):
        changed = workspace / f'demo-{kind}.xlsx'
        run([*prefix, '-c', edit, workbook, changed, kind])
        before = changed.read_bytes()
        invoke(changed, error=error)
        if kind == 'sheet':
            assert invoke(changed, '--sheet', 'Fictional Ledger') == first
        assert changed.read_bytes() == before

    unreadable = workspace / 'unreadable.xlsx'
    unreadable.write_bytes(b'fictional bytes outside the XLSX format')
    invoke(unreadable, error='not a readable XLSX workbook')

    request = workspace / 'reconciliation.json'
    saved_queue = json.loads((examples / 'fictional-queue.json').read_bytes())
    request.write_text(json.dumps(saved_queue | report), encoding='utf-8')
    before_request = request.read_bytes()
    result = run([python, '-I', '-B', '-W', 'error', reconciler, '--input', request])
    assert not result.stderr
    reconciliation = json.loads(result.stdout)
    assert reconciliation['status'] == 'reconciled' and reconciliation['row_count'] == 21
    queued = reconciliation['rows'][0]
    assert queued['lot_prefix'] == 'DEMO-01-'
    assert queued['queue_status'] == 'ACTIVE' and queued['recommended_lot_ids'] == ['DEMO-01-AABA', 'DEMO-01-AABB']
    assert all(row['queue_status'] == 'REFERENCE_ONLY' for row in reconciliation['rows'][1:])
    assert request.read_bytes() == before_request and workbook.read_bytes() == original
    assert digest(reconciler) == RECONCILER_SHA256
    return ['typed_rows_repeatable_and_source_unchanged', 'worksheet_and_header_contract',
            'fixed_21_row_boundary', 'duplicate_prefix_and_lot_id_refusal', 'malformed_archive_refusal',
            'released_reconciler_accepts_output']


def qualify(packages, workspace, report, receipt, reference, reconciler):
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

    install_offline(run, python, source, prefix, wheels, selected, 'runtime', RUNTIME_DEPENDENCIES)
    verify_installs(run, python, prefix, bootstrap, selected, RUNTIME_DEPENDENCIES)
    cli_checks = check_offline_cli(run, python, source, workspace, reconciler.resolve())
    install_offline(run, python, source, prefix, wheels, selected, 'test',
                    selected.keys() - RUNTIME_DEPENDENCIES)
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
        original_test_functions=0, original_test_cases=0, added_test_functions=len(EXPECTED_TESTS),
        passed=len(test_ids), failures=0, errors=0, skipped=0,
        reconciler_release=RECONCILER_RELEASE, reconciler_source_sha256=digest(reconciler),
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=sorted(RUNTIME_DEPENDENCIES), dependencies=selected, test_runner='pytest',
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), pip_version=bootstrap['pip'],
        offline_wheel_install=True, fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('LAST_LOT_WORKBOOK_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    parser.add_argument('--reconciler', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build, args.reconciler)
