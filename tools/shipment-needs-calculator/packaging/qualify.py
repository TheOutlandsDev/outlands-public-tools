"""Validate a fresh extraction with the public Python API."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'shipment-needs-calculator-0.1.0.zip'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(packages, workspace, receipt_path, receipt, reference=None):
    if not __debug__:
        raise RuntimeError('Qualification requires assertions')
    archive = packages / ARCHIVE
    manifest = packages / 'build-manifest.json'
    build = json.loads(manifest.read_bytes())
    assert build['filename'] == ARCHIVE and build['version'] == '0.1.0'
    assert build['sha256'] == digest(archive) and build['bytes'] == archive.stat().st_size
    if reference is not None:
        assert archive.read_bytes() == (reference / ARCHIVE).read_bytes()
        assert manifest.read_bytes() == (reference / manifest.name).read_bytes()
    sdk = json.loads(receipt.read_bytes())
    lock = json.loads((ROOT / 'PYTHON-LOCK.json').read_bytes())
    minor = f'{sys.version_info.major}.{sys.version_info.minor}'
    pin = lock['python_archives'][sys.platform][minor]
    assert sdk['status'] == 'PASS' and sdk['archive'] == pin
    assert sdk['platform'] == sys.platform and sdk['python_version'] == platform.python_version() == pin['python']
    assert sdk['python_lock_sha256'] == digest(ROOT / 'PYTHON-LOCK.json')
    assert sdk['preparation_helper_sha256'] == digest(ROOT / 'packaging/prepare_python.py')
    assert sdk['executable_sha256'] == digest(Path(sys._base_executable))

    workspace = workspace.resolve()
    workspace.mkdir()
    source = workspace / ARCHIVE.removesuffix('.zip')
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        assert len({item.filename.casefold() for item in members}) == len(members) == build['files']
        for item in members:
            name = item.filename
            parts = name.split('/')
            assert len(parts) > 1 and parts[0] == source.name
            assert str(PurePosixPath(name)) == name and all(part not in ('', '.', '..') for part in parts)
            assert ':' not in name and '\\' not in name and item.file_size < 1024 * 1024
            assert stat.S_ISREG(item.external_attr >> 16)
        assert bundle.testzip() is None
        bundle.extractall(workspace)

    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith(('PYTHON', 'PIP_', 'LD_', 'DYLD_'))}
    env.update(PYTHONUTF8='1', PYTHON_COLORS='0', NO_COLOR='1')

    def run(args, cwd, expected=0):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                capture_output=True, encoding='utf-8', timeout=90)
        if result.returncode != expected:
            (workspace / 'qualification-private.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            raise RuntimeError(f'Qualification command exited {result.returncode}, expected {expected}')
        return result

    run([sys.executable, '-I', '-B', '-m', 'venv', workspace / 'venv'], workspace)
    python = workspace / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    report_path = workspace / 'pip-private.json'
    wheel_lock = json.loads((source / 'WHEEL-LOCK.json').read_bytes())
    expected_packages = dict(wheel_lock['packages'])
    if os.name != 'nt':
        expected_packages.pop('colorama')
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'install',
         '--index-url', wheel_lock['index'], '--only-binary=:all:', '--require-hashes',
         '--report', report_path, '-r', source / 'requirements-test.txt'], workspace)
    receipt = json.loads(report_path.read_bytes())
    installed = {}
    for item in receipt['install']:
        name = item['metadata']['name'].lower().replace('_', '-')
        pin = expected_packages[name]
        assert name not in installed and item['metadata']['version'] == pin['version']
        download = item['download_info']
        sha256 = download['archive_info']['hashes']['sha256']
        wheel, = [record for record in pin['wheels'] if record['sha256'] == sha256 and record['url'] == download['url']]
        installed[name] = dict(version=pin['version'], filename=wheel['filename'], sha256=sha256)
    assert installed.keys() == expected_packages.keys()
    run([python, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'check'], workspace)
    versions = json.loads(run([python, '-I', '-B', '-c',
        'import importlib.metadata as m,json; print(json.dumps({d.metadata["Name"].lower().replace("_", "-"): d.version for d in m.distributions()}))'], workspace).stdout)
    assert {n: v for n, v in versions.items() if n not in {'pip', 'setuptools'}} == {n: d['version'] for n, d in installed.items()}
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    junit = workspace / 'pytest-results.xml'
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    run([python, '-B', '-W', 'error', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
         '--junitxml', junit, 'tests'], source)
    suite = ET.parse(junit).getroot().find('testsuite')
    assert tuple(int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')) == (12, 0, 0, 0)
    test_ids = [node.get('classname') + '.' + node.get('name') for node in suite.findall('testcase')]
    assert len(set(test_ids)) == len(test_ids) == 12

    env['PYTHONPATH'] = str(source)
    report = run([python, '-B', '-W', 'error', '-c', r'''
from datetime import date
import json
from pathlib import Path
import sys

from production_planning.what_is_needed import (
    DueProductInput, ShipmentNeedInput, WhatIsNeededValidationError,
    determine_parts_to_ship, evaluate_comparison_case, load_part_modality_configuration,
)

root = Path(sys.argv[1])
mapping_path = root / 'demo_part_modality.json'
case_path = root / 'comparison_cases/demo_shipment_needs.json'
case = json.loads(case_path.read_bytes())
inputs = case['input_contract']
shipments = tuple(ShipmentNeedInput.model_validate(item) for item in inputs['shipment_records'])
due = tuple(DueProductInput.model_validate(item) for item in inputs['due_products'])
mapping = load_part_modality_configuration(mapping_path)
report = evaluate_comparison_case(case_path=case_path, mapping_path=mapping_path).result
assert report.input_count == 5 and report.open_need_count == 2 and report.retained_demand_quantity == 325
assert report.active_cutoff_date == date(2000, 8, 17)
assert report.active_products == ('7000011-DEMO',)
assert tuple(row.source_id for row in report.parts_to_ship) == ('DEMO-SHIP-001', 'DEMO-SHIP-002')

def calculate(shipment_rows=shipments, due_rows=due):
    return determine_parts_to_ship(shipment_records=shipment_rows, due_products=due_rows, mapping=mapping)

assert calculate(tuple(reversed(shipments)), tuple(reversed(due))) == report
assert report.excluded_shipped_count == report.excluded_docked_count == report.excluded_nonpositive_count == 1
assert next(record for record in shipments if record.source_id == 'DEMO-SHIP-003').ship_quantity == 0

at_cutoff = DueProductInput(source_id='DEMO-AT', due_date=report.active_cutoff_date, part_number=8400021)
assert calculate(due_rows=(*due, at_cutoff)).active_products == ('7000011-DEMO', '8400021')

def refused(operation, message):
    try:
        operation()
    except WhatIsNeededValidationError as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError('Invalid shipment data was accepted')

refused(lambda: calculate((*shipments, shipments[0])), 'duplicate shipment source ID')
refused(lambda: calculate(due_rows=(*due, due[0])), 'duplicate due/product source ID')
unknown = ShipmentNeedInput(source_id='UNMAPPED', date_to_ship=date(2000, 8, 20),
                            quantity_due=10, part_number='UNKNOWN-DEMO')
refused(lambda: calculate((*shipments, unknown)), 'unsupported retained part')

case['expected']['retained_demand_quantity'] += 1
changed_case = Path('changed-expected.json')
changed_case.write_text(json.dumps(case), encoding='utf-8')
refused(lambda: evaluate_comparison_case(case_path=changed_case, mapping_path=mapping_path),
        'expected result does not match')
changed_mapping = json.loads(mapping_path.read_bytes())
changed_mapping['legacy_source_sha256'] = '0' * 64
changed_path = Path('changed-mapping.json')
changed_path.write_text(json.dumps(changed_mapping), encoding='utf-8')
refused(lambda: load_part_modality_configuration(changed_path), 'configuration is invalid')

print(json.dumps(['verified_comparison_result', 'stable_ordering', 'shipment_exclusions',
    'inclusive_active_cutoff', 'duplicate_id_refusal', 'unmapped_part_refusal',
    'expected_result_drift_refusal', 'mapping_provenance_refusal']))
''', source / 'data/flex_planning'], workspace)
    api_checks = json.loads(report.stdout)
    assert len(api_checks) == len(set(api_checks)) == 8 and not report.stderr
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    evidence = dict(status='PASS', package='shipment-needs-calculator', version='0.1.0', platform=sys.platform,
        python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=12, passed=12, failures=0, errors=0, skipped=0, test_ids=test_ids,
        api_checks=api_checks, fictional_shipments=5, dependencies=installed, pip_version=versions['pip'],
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with receipt_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('SHIPNEEDS_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
