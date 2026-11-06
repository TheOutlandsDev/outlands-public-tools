"""Build a deterministic offline ZIP containing forty reviewed tools and a selector."""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
VERSION = '1.8.0'
ZIP_NAME = 'outlands-public-tools-40-1.8.0.zip'
SELECTOR = 'outlands_public_tools_collection-1.8.0-py3-none-any.whl'
GROUPS = {
    'routing': ('integrations/model-routing/release.json', 'integrations/model-routing/components.json',
                'outlands-model-routing-collection==1.0.0'),
    'probability': ('integrations/probability-integrity/release.json', 'integrations/probability-integrity/components.json',
                    'outlands-probability-integrity-collection==1.0.0'),
    'cache': ('integrations/cache-retry/release.json', 'integrations/cache-retry/components.json',
              'outlands-cache-retry-collection==1.0.0'),
    'review': ('integrations/review-change/release.json', 'integrations/review-change/components.json',
               'outlands-review-change-collection==1.0.0'),
    'test': ('integrations/test-evidence/release.json', 'integrations/test-evidence/components.json',
             'outlands-test-evidence-collection==1.0.0'),
    'reliability': ('integrations/reliability-incident/release.json', 'integrations/reliability-incident/components.json',
                    'outlands-reliability-incident-collection==1.0.0'),
    'metrics': ('integrations/metrics-traces/release.json', 'integrations/metrics-traces/components.json',
                'outlands-metrics-traces-collection==1.0.0'),
    'documents': ('integrations/document-evidence/release.json', 'integrations/document-evidence/components.json',
                  'outlands-document-evidence-collection==1.0.0'),
    'relational': ('integrations/relational-review/release.json', 'integrations/relational-review/components.json',
                   'outlands-relational-review-collection==1.0.0'),
    'ai': ('integrations/ai-decision-contracts/release.json', 'integrations/ai-decision-contracts/components.json',
           'outlands-ai-decision-contracts-collection==1.0.0'),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode('ascii')


def inputs():
    wheels = {}
    components = []
    releases = []
    for group, (plan_path, guide_path, collection_package) in GROUPS.items():
        plan = json.loads((ROOT / plan_path).read_text(encoding='utf-8'))
        guide = json.loads((ROOT / guide_path).read_text(encoding='utf-8'))
        selected = {name: sha for name, sha in plan['assets'].items() if name.endswith('.whl')}
        if len(selected) != 5 or len(guide['components']) != 4 or guide['collection']['package'] != collection_package:
            raise ValueError('COHORT_PLAN_INVALID')
        if {row['id'] for row in guide['components']} != set(guide['collection']['members']):
            raise ValueError('COHORT_MEMBERSHIP_INVALID')
        for row in guide['components']:
            filename = row['package'].split('==')[0].replace('-', '_') + '-1.0.0-py3-none-any.whl'
            if filename not in selected or not row['purpose'] or not row['use_case'] or not row['establishes']:
                raise ValueError('INDIVIDUAL_WHEEL_MISSING')
            components.append({key: row[key] for key in ('id', 'purpose', 'use_case', 'package', 'command',
                'python_api', 'input_format', 'result_format', 'example_input', 'result_fields',
                'dependencies', 'establishes', 'does_not_establish')} | {
                    'group': group, 'filename': filename, 'sha256': selected[filename]})
        for name, sha in selected.items():
            if Path(name).name != name or name in wheels:
                raise ValueError('WHEEL_NAME_DUPLICATE_OR_UNSAFE')
            wheels[name] = sha
        releases.append({'group': group, 'tag': plan['tag'], 'source_revision': plan['source_revision'],
                         'collection_package': collection_package})
    if len(components) != 40 or len(wheels) != 50:
        raise ValueError('FORTY_COMPONENTS_FIFTY_INPUT_WHEELS_REQUIRED')
    return wheels, {'format': 'outlands-public-tools-forty-components-v1', 'version': VERSION,
                    'python': '>=3.12,<3.14', 'selection': {
                        'one': 'Install one individual wheel by filename',
                        'routing': 'outlands-public-tools-collection[routing]==1.8.0',
                        'ai': 'outlands-public-tools-collection[ai]==1.8.0',
                        'probability': 'outlands-public-tools-collection[probability]==1.8.0',
                        'cache': 'outlands-public-tools-collection[cache]==1.8.0',
                        'review': 'outlands-public-tools-collection[review]==1.8.0',
                        'test': 'outlands-public-tools-collection[test]==1.8.0',
                        'reliability': 'outlands-public-tools-collection[reliability]==1.8.0',
                        'metrics': 'outlands-public-tools-collection[metrics]==1.8.0',
                        'documents': 'outlands-public-tools-collection[documents]==1.8.0',
                        'relational': 'outlands-public-tools-collection[relational]==1.8.0',
                        'all': 'outlands-public-tools-collection[all]==1.8.0'},
                    'releases': releases, 'components': components,
                    'boundary': 'Install choices only; no application adapter or live model behavior'}


def normalize_wheel(path):
    with zipfile.ZipFile(path) as source:
        if source.comment:
            raise ValueError('WHEEL_COMMENT_REFUSED')
        names = source.namelist()
        if len(names) != len(set(names)) or any(name.endswith('/') for name in names):
            raise ValueError('WHEEL_MEMBER_LAYOUT_INVALID')
        members = {name: source.read(name) for name in names}
    metadata = [name for name in members if name.endswith('.dist-info/METADATA')]
    records = [name for name in members if name.endswith('.dist-info/RECORD')]
    if len(metadata) != 1 or len(records) != 1:
        raise ValueError('WHEEL_METADATA_LAYOUT_INVALID')
    members[metadata[0]] = members[metadata[0]].replace(b'\r\n', b'\n')
    rows = io.StringIO(newline='')
    writer = csv.writer(rows, lineterminator='\n')
    for name, raw in sorted(members.items()):
        if name != records[0]:
            value = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode('ascii')
            writer.writerow((name, 'sha256=' + value, str(len(raw))))
    writer.writerow((records[0], '', ''))
    members[records[0]] = rows.getvalue().encode('utf-8')
    temporary = path.with_suffix('.normalized')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as target:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            target.writestr(info, raw, compress_type=zipfile.ZIP_STORED)
    temporary.replace(path)


def selector_wheel(output, component_bytes):
    with tempfile.TemporaryDirectory(prefix='outlands-public-selector-') as directory:
        project = Path(directory)
        package = project / 'outlands_public_tools_collection'
        package.mkdir()
        (package / '__init__.py').write_text('"""OUTLANDS public install selector."""\n', encoding='utf-8', newline='\n')
        (package / 'COMPONENTS.json').write_bytes(component_bytes)
        (package / 'catalog.py').write_text(
            '"""Show reviewed components and actual installed-package state."""\n'
            'import json\nfrom importlib import metadata\nfrom importlib.resources import files\n'
            'def main():\n'
            '    rows = json.loads(files(__package__).joinpath("COMPONENTS.json").read_text(encoding="ascii"))["components"]\n'
            '    result = []\n'
            '    for row in rows:\n'
            '        name, version = row["package"].split("==")\n'
            '        try:\n            installed = metadata.version(name) == version\n'
            '        except metadata.PackageNotFoundError:\n            installed = False\n'
            '        result.append({"id": row["id"], "group": row["group"], "command": row["command"], "installed": installed})\n'
            '    print(json.dumps({"format": "outlands-public-tools-selector-v1", "components": result}, sort_keys=True))\n',
            encoding='utf-8', newline='\n')
        (project / 'README.md').write_text(
            '# OUTLANDS Public Tools Collection\n\n'
            'Install one of ten reviewed extras, `routing`, `ai`, `probability`, `cache`, `review`, `test`, `reliability`, `metrics`, `documents` or `relational`, or `all` for forty tools. '
            'Run `outlands-public-tools` to list components and installed state. '
            'The selector installs packages and does not connect tools to any application.\n',
            encoding='utf-8', newline='\n')
        (project / 'LICENSE').write_bytes((ROOT / 'tools/model-capability-checker/LICENSE').read_bytes())
        (project / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["setuptools>=70", "wheel"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            '[project]\nname = "outlands-public-tools-collection"\nversion = "1.8.0"\n'
            'description = "Select forty reviewed OUTLANDS Python tools"\n'
            'readme = "README.md"\nrequires-python = ">=3.12,<3.14"\n'
            'license = {file = "LICENSE"}\n\n'
            '[project.optional-dependencies]\n'
            'routing = ["outlands-model-routing-collection==1.0.0"]\n'
            'ai = ["outlands-ai-decision-contracts-collection==1.0.0"]\n'
            'probability = ["outlands-probability-integrity-collection==1.0.0"]\n'
            'cache = ["outlands-cache-retry-collection==1.0.0"]\n'
            'review = ["outlands-review-change-collection==1.0.0"]\n'
            'test = ["outlands-test-evidence-collection==1.0.0"]\n'
            'reliability = ["outlands-reliability-incident-collection==1.0.0"]\n'
            'metrics = ["outlands-metrics-traces-collection==1.0.0"]\n'
            'documents = ["outlands-document-evidence-collection==1.0.0"]\n'
            'relational = ["outlands-relational-review-collection==1.0.0"]\n'
            'all = ["outlands-model-routing-collection==1.0.0", '
            '"outlands-ai-decision-contracts-collection==1.0.0", "outlands-probability-integrity-collection==1.0.0", "outlands-cache-retry-collection==1.0.0", "outlands-review-change-collection==1.0.0", "outlands-test-evidence-collection==1.0.0", "outlands-reliability-incident-collection==1.0.0", "outlands-metrics-traces-collection==1.0.0", "outlands-document-evidence-collection==1.0.0", "outlands-relational-review-collection==1.0.0"]\n\n'
            '[project.scripts]\noutlands-public-tools = "outlands_public_tools_collection.catalog:main"\n\n'
            '[tool.setuptools.packages.find]\nwhere = ["."]\n'
            'include = ["outlands_public_tools_collection"]\n\n'
            '[tool.setuptools.package-data]\n'
            '"outlands_public_tools_collection" = ["COMPONENTS.json"]\n',
            encoding='utf-8', newline='\n')
        subprocess.run([sys.executable, '-B', '-c',
            'import setuptools.build_meta as backend,sys; backend.build_wheel(sys.argv[1])',
            str(output)], cwd=project, check=True, stdout=subprocess.DEVNULL,
            env={**os.environ, 'PIP_NO_INDEX': '1', 'PYTHONNOUSERSITE': '1',
                 'SOURCE_DATE_EPOCH': '315532800', 'PYTHONHASHSEED': '0'})
    path = output / SELECTOR
    if not path.is_file():
        raise ValueError('SELECTOR_WHEEL_MISSING')
    normalize_wheel(path)
    return path.read_bytes()


def build(input_dir, output):
    if sys.version_info[:2] not in ((3, 12), (3, 13)):
        raise ValueError('PYTHON_312_OR_313_REQUIRED')
    input_dir = input_dir.resolve(); output = output.resolve()
    if (not input_dir.is_dir() or output == ROOT or ROOT in output.parents
        or not output.is_dir() or any(output.iterdir())):
        raise ValueError('INPUT_OR_EMPTY_EXTERNAL_OUTPUT_INVALID')
    expected, components = inputs()
    if {p.name for p in input_dir.iterdir()} != set(expected):
        raise ValueError('FORTY_INPUT_WHEELS_REQUIRED')
    for name, sha in expected.items():
        path = input_dir / name
        if not path.is_file() or path.is_symlink() or digest(path.read_bytes()) != sha:
            raise ValueError('INPUT_WHEEL_DIGEST_MISMATCH')
    wheels_dir = output / 'wheels'; wheels_dir.mkdir()
    for name in sorted(expected):
        (wheels_dir / name).write_bytes((input_dir / name).read_bytes())
    component_bytes = encoded(components)
    selector_wheel(wheels_dir, component_bytes)
    wheel_files = sorted(wheels_dir.iterdir())
    if len(wheel_files) != 51:
        raise ValueError('FIFTY_ONE_WHEELS_REQUIRED')
    members = {'COMPONENTS.json': component_bytes,
               'START-HERE.md': (HERE / 'START-HERE.md').read_bytes()}
    members.update({'wheels/' + p.name: p.read_bytes() for p in wheel_files})
    members['SHA256SUMS.txt'] = ''.join(
        digest(members['wheels/' + p.name]) + '  wheels/' + p.name + '\n'
        for p in wheel_files).encode('ascii')
    manifest = {'format': 'outlands-public-tools-forty-bundle-v1', 'version': VERSION,
                'wheels': len(wheel_files), 'components': len(components['components']),
                'members': {name: {'bytes': len(raw), 'sha256': digest(raw)}
                            for name, raw in sorted(members.items())}}
    members['MANIFEST.json'] = encoded(manifest)
    archive = output / ZIP_NAME
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as target:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            target.writestr(info, raw, compress_type=zipfile.ZIP_STORED)
    (output / 'SHA256SUMS.txt').write_text(digest(archive.read_bytes()) + '  ' + ZIP_NAME + '\n',
                                            encoding='ascii', newline='\n')
    return {'status': 'PASS', 'zip': ZIP_NAME, 'sha256': digest(archive.read_bytes()),
            'members': len(members), 'wheels': len(wheel_files), 'components': 40}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.inputs, args.output)))
