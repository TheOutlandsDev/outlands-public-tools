"""Validate a fresh extraction with the public Python API."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import pyexpat
import stat
import subprocess
import sys
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'flow-xml-catalog-0.1.0.zip'


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
    assert tuple(int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')) == (19, 0, 0, 0)
    test_ids = [node.get('classname') + '::' + node.get('name') for node in suite.findall('testcase')]
    assert len(set(test_ids)) == len(test_ids) == 19

    env['PYTHONPATH'] = str(source)
    report = run([python, '-B', '-W', 'error', '-c', '''
import json
from pathlib import Path
import shutil
import sys
from xml.etree import ElementTree as ET
from production_planning.flow_catalog import FlowCatalogError, compare_flows, load_verified_catalog
from production_planning.flow_xml import export_normalized_flow_xml

data = Path(sys.argv[1])
manifest = data / 'flow_xml_manifest.json'
inputs = data / 'flow_xml_inputs'
catalog = load_verified_catalog(manifest, inputs)
by_name = {entry.filename: catalog.documents[entry.sha256] for entry in catalog.manifest.sources}
assert len(by_name) == 5 and sum(entry.active for entry in catalog.manifest.sources) == 4
left, right = by_name['demo-panel-7.xml'], by_name['demo-panel-9.xml']
comparison = compare_flows(left, right)
assert comparison == compare_flows(left, right)
assert comparison['step_count_delta'] == 4 and comparison['rework_path_count_delta'] == 3
assert [row['position'] for row in comparison['changed_positions']] == [2, 39, 40, 41, 42]
repeated = [step for step in by_name['demo-circuit-6.xml'].steps if step.step_name == 'Repeated_Check']
assert [step.position for step in repeated] == [15, 26, 28]
assert len({step.step_ref_id for step in repeated}) == 1
xml = export_normalized_flow_xml(right)
assert xml == export_normalized_flow_xml(right)
assert b'CreatedBy' not in xml and b'ModifiedBy' not in xml
tree = ET.fromstring(xml)
assert tree.get('mesImportCompatible') == 'False'
assert len(tree.findall('./Flow/ReworkPaths/ReworkPath')) == 4
assert tree.find('./Flow/ReworkPaths/ReworkPath').get('returnStep') == 'Resume'

def rejected(manifest_path, directory, message):
    try:
        load_verified_catalog(manifest_path, directory)
    except FlowCatalogError as error:
        assert message in str(error)
    else:
        raise AssertionError('Invalid catalog was accepted')

copy = Path('fictional source copy')
shutil.copytree(inputs, copy)
changed = copy / 'demo-panel-7.xml'
changed.write_bytes(changed.read_bytes() + b' ')
rejected(manifest, copy, 'does not match')
changed.unlink()
rejected(manifest, copy, 'missing or invalid')
duplicate = json.loads(manifest.read_bytes())
duplicate['sources'][1]['catalog_status'] = 'ACTIVE_DEVELOPMENT_REFERENCE'
duplicate_path = Path('duplicate-active.json')
duplicate_path.write_text(json.dumps(duplicate), encoding='utf-8')
rejected(duplicate_path, inputs, 'manifest is invalid')
print(json.dumps(['verify_catalog', 'repeatable_position_comparison', 'repeated_steps',
    'normalized_rework_export', 'changed_source_refusal', 'missing_source_refusal', 'duplicate_active_refusal']))
''', source / 'data'], workspace)
    api_checks = json.loads(report.stdout)
    assert len(api_checks) == len(set(api_checks)) == 7 and not report.stderr
    run([python, '-I', '-B', source / 'source_check.py'], workspace)
    actual_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    assert actual_files == {item.filename.split('/', 1)[1] for item in members}
    evidence = dict(status='PASS', package='flow-xml-catalog', version='0.1.0', platform=sys.platform,
        python=platform.python_version(), expat=pyexpat.EXPAT_VERSION,
        source_revision=build['source_revision'], zip_sha256=build['sha256'], zip_bytes=build['bytes'],
        archive_members=build['files'], source_manifest_sha256=digest(source / 'SOURCE-MANIFEST.json'),
        original_tests=19, passed=19, failures=0, errors=0, skipped=0, test_ids=test_ids,
        api_checks=api_checks, fictional_sources=5, dependencies=installed, pip_version=versions['pip'],
        dependency_wheel_lock_sha256=digest(source / 'WHEEL-LOCK.json'), fresh_extraction=True, fresh_venv=True,
        source_bytes_unchanged=True, independent_rebuild_verified=reference is not None, python_sdk=sdk)
    with receipt_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(evidence, indent=2) + '\n')
    print('FLOWXML_QUALIFICATION ' + json.dumps(evidence))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packages', 'workspace', 'report', 'python-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--reference-build', type=Path)
    args = parser.parse_args()
    qualify(args.packages, args.workspace, args.report, args.python_receipt, args.reference_build)
