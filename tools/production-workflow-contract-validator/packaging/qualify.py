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
ARCHIVE = 'production-workflow-contract-validator-0.1.0.zip'


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
    assert tuple(int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')) == (15, 0, 0, 0)
    test_ids = [node.get('classname') + '.' + node.get('name') for node in suite.findall('testcase')]
    assert len(set(test_ids)) == len(test_ids) == 15

    env['PYTHONPATH'] = str(source)
    report = run([python, '-B', '-W', 'error', '-c', r'''
import hashlib
import json
from pathlib import Path
import sys

from production_planning.internal_panel_flex_contract import (
    CONTRACT_RELATIVE_PATH, EXPECTED_EVENT_IDENTITIES, EXPECTED_PRODUCTS,
    EXPECTED_STATES, EXPECTED_TRANSITIONS, MAX_CONTRACT_BYTES,
    InternalPanelFlexContractError, internal_panel_flex_contract_sha256,
    load_internal_panel_flex_contract,
)

contract_path = Path(sys.argv[1]) / CONTRACT_RELATIVE_PATH
contract = load_internal_panel_flex_contract()
assert contract == load_internal_panel_flex_contract(contract_path)
assert len(contract.products) == 5
assert {
    product.canonical_modality: (product.display_modality, product.assembly, product.lot_prefix)
    for product in contract.products
} == EXPECTED_PRODUCTS
assert contract.state_model.states == EXPECTED_STATES
assert {
    (transition.action, transition.from_state, transition.to_state)
    for transition in contract.state_model.transitions
} == EXPECTED_TRANSITIONS
assert {
    identity.event_type: identity.identity_fields for identity in contract.event_identities
} == EXPECTED_EVENT_IDENTITIES
assert contract.production_included is contract.activation.production_included is False
assert contract.state_model.hla_consumption_transition_executable is False

checksum = hashlib.sha256(contract_path.read_bytes()).hexdigest()
assert internal_panel_flex_contract_sha256() == checksum
assert internal_panel_flex_contract_sha256(contract_path) == checksum

def reject(operation, cause_message=None):
    try:
        operation()
    except InternalPanelFlexContractError as error:
        if cause_message is not None:
            assert error.__cause__ is not None
            assert cause_message in str(error.__cause__), str(error.__cause__)
    else:
        raise AssertionError('Invalid workflow contract was accepted')

def invalid(name, mutate, cause_message):
    payload = json.loads(contract_path.read_bytes())
    mutate(payload)
    path = Path(name + '.json')
    path.write_text(json.dumps(payload), encoding='utf-8')
    reject(lambda: load_internal_panel_flex_contract(path), cause_message)

def change_product(payload):
    payload['products'][0]['assembly'] = payload['products'][1]['assembly']

invalid('mapping-drift', change_product, 'scope drifted')
invalid('duplicate-event', lambda payload: payload['event_identities'].append(
    payload['event_identities'][0]), 'event identity type must be unique')
invalid('authority-expansion', lambda payload: payload.update(production_included=True),
        'production_included')
invalid('duplicate-transition', lambda payload: payload['state_model']['transitions'].append(
    payload['state_model']['transitions'][0]), 'state transition must be unique')
invalid('reversed-baseline', lambda payload: payload['historical_baseline'].update(
    declared_window_start='2000-01-02', declared_window_end='2000-01-01'), 'baseline window is reversed')

oversized = Path('oversized-contract.json')
oversized.write_bytes(b'{' + b' ' * MAX_CONTRACT_BYTES)
try:
    load_internal_panel_flex_contract(oversized)
except InternalPanelFlexContractError as error:
    assert 'size is invalid' in str(error), str(error)
else:
    raise AssertionError('Oversized workflow contract was accepted')

print(json.dumps(['valid_fictional_contract', 'stable_checksum', 'mapping_drift_refusal',
    'duplicate_event_identity_refusal', 'authority_expansion_refusal', 'oversized_contract_refusal',
    'duplicate_transition_refusal', 'reversed_baseline_refusal']))
''', source], workspace)
    api_checks = json.loads(report.stdout)
    assert len(api_checks) == len(set(api_checks)) == 8 and not report.stderr
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    evidence = dict(status='PASS', package='production-workflow-contract-validator', version='0.1.0', platform=sys.platform,
        python=platform.python_version(),
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=15, passed=15, failures=0, errors=0, skipped=0, test_ids=test_ids,
        api_checks=api_checks, fictional_products=5, dependencies=installed, pip_version=versions['pip'],
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with receipt_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('WORKFLOWCONTRACT_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
