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
PACKAGE = 'order-workbook-patch-exporter'
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



EXPECTED_TESTS = {
    "tests/test_workbook_patch.py::test_patches_typed_cells_and_preserves_other_package_parts",
    "tests/test_workbook_patch.py::test_manual_rows_can_set_extra_fields_and_preserve_numeric_row_order",
    "tests/test_workbook_patch.py::test_checksum_is_checked_before_opening_zip",
    "tests/test_workbook_patch.py::test_duplicate_row_and_bad_count_are_rejected",
    "tests/test_workbook_patch.py::test_formula_in_target_cell_refuses_even_a_clear",
    "tests/test_workbook_patch.py::test_workbook_rejects_unsafe_parts_doctype_and_macro_project",
    "tests/test_workbook_patch.py::test_publishing_cannot_overwrite_existing_output",
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


def check_offline_cli(run, python, source, workspace):
    from xml.etree import ElementTree as ET

    demo = workspace / 'fictional'
    run([python, '-I', '-B', '-W', 'error', source / 'examples/make_demo_workbook.py', demo])
    template, snapshot = demo / 'template.xlsx', demo / 'orders.json'
    originals = {path: path.read_bytes() for path in (template, snapshot)}
    script = source / 'order_workbook_patch.py'
    copied, refused = demo / 'patched.xlsx', demo / 'refused.xlsx'
    sheet = 'xl/worksheets/sheet1.xml'
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

    def invoke(book, orders, destination, error=None):
        result = run([python, '-I', '-B', '-W', 'error', script, book, orders, destination], expected=2 if error else 0)
        if error:
            assert not result.stdout and error in result.stderr
            return None
        assert not result.stderr
        return json.loads(result.stdout)

    assert invoke(template, snapshot, copied) == {'patched_rows': 1, 'sha256': digest(copied)}
    with zipfile.ZipFile(copied) as output, zipfile.ZipFile(template) as input_zip:
        assert output.namelist() == input_zip.namelist()
        assert {name for name in output.namelist() if output.read(name) != input_zip.read(name)} == {sheet}
        tree = ET.fromstring(output.read(sheet))
        assert tree.findtext(".//s:c[@r='F4']/s:v", namespaces=ns) == '120'
        assert tree.findtext(".//s:c[@r='D4']/s:is/s:t", namespaces=ns) == ' =DEMO '
        assert tree.findtext(".//s:c[@r='A4']/s:f", namespaces=ns) == '1+1'

    alternate = demo / 'alternate.xlsx'
    alternate.write_bytes(b'not a workbook')
    invoke(alternate, snapshot, refused, 'checksum does not match')
    assert not refused.exists()

    changed = demo / 'changed.json'
    data = json.loads(originals[snapshot])
    data['orders'].append(data['orders'][0])
    changed.write_text(json.dumps(data), encoding='utf-8')
    invoke(template, changed, refused, 'row count')
    data['source_row_count'] = 2
    changed.write_text(json.dumps(data), encoding='utf-8')
    invoke(template, changed, refused, 'duplicate sheet and row')
    assert not refused.exists()

    data = json.loads(originals[snapshot])
    data['orders'][0]['fields'] = {'part_number': 'DEMO-NEW'}
    changed.write_text(json.dumps(data), encoding='utf-8')
    invoke(template, changed, refused, 'approved editable fields')
    assert not refused.exists()

    with zipfile.ZipFile(template) as input_zip, zipfile.ZipFile(alternate, mode='w') as modified:
        for name in input_zip.namelist():
            payload = input_zip.read(name)
            if name == sheet:
                payload = payload.replace(b'<c r="F4"><v>3</v></c>', b'<c r="F4"><f>1+2</f><v>3</v></c>')
            modified.writestr(name, payload)
    data = json.loads(originals[snapshot])
    data['source_sha256'] = digest(alternate)
    changed.write_text(json.dumps(data), encoding='utf-8')
    invoke(alternate, changed, refused, 'contains a formula')
    assert not refused.exists()

    previous = copied.read_bytes()
    invoke(template, snapshot, copied, 'output workbook already exists')
    invoke(template, snapshot, template, 'output workbook already exists')
    assert copied.read_bytes() == previous
    assert {path: path.read_bytes() for path in originals} == originals
    assert not list(demo.glob('.order-patch-*'))
    return ['typed_copy_and_other_parts_unchanged', 'template_checksum_checked_before_parse',
            'row_total_and_duplicate_refusal', 'editable_column_allowlist', 'target_formula_protection',
            'existing_destinations_and_inputs_unchanged']


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
        original_test_functions=0, original_test_cases=0, added_test_functions=len(EXPECTED_TESTS),
        passed=len(test_ids), failures=0, errors=0, skipped=0,
        test_ids=test_ids, cli_checks=cli_checks, synthetic_samples=True, live_activity_checks_used=False,
        runtime_dependencies=[], dependencies=selected, test_runner='pytest',
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), pip_version=bootstrap['pip'],
        offline_wheel_install=True, fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=True, python_sdk=sdk,
    )
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('ORDER_WORKBOOK_PATCHS_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
