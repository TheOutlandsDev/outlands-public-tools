"""Build four annotation and geometry wheels from pinned public source."""
from __future__ import annotations

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
VERSION = '1.0.0'
TOOLS = {'annotation-manifest-checker': 'manifest', 'polygon-geometry-checker': 'polygons', 'bounding-box-converter': 'boxes', 'annotation-export-handoff-checker': 'handoff'}
DESCRIPTIONS = {'annotation-manifest-checker': 'Check declared image, taxonomy, and annotation snapshot references without reading image assets.', 'polygon-geometry-checker': 'Check declared polygon geometry against supplied image dimensions.', 'bounding-box-converter': 'Convert explicitly declared box conventions without clipping or asset updates.', 'annotation-export-handoff-checker': 'Review a declared annotation export handoff without exporting a dataset.'}
OPERATIONS = {tool: 'check' for tool in TOOLS}
EXTRA = {}
SHARED = ('toolkit.py', 'native_windows.py', 'decision_core.py', 'visual_core.py')



def verified_source(directory: Path, filename: str) -> bytes:
    manifest = json.loads((directory / 'SOURCE-MANIFEST.json').read_text(encoding='utf-8'))
    expected = manifest['files'][filename]
    raw = (directory / filename).read_bytes()
    if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
        raise ValueError(f'SOURCE_MANIFEST_MISMATCH: {directory.name}/{filename}')
    return raw


def isolated_source(raw: bytes) -> bytes:
    text = raw.decode('utf-8')
    for module, alias in (('toolkit', 't'), ('decision_core', 'c'), ('visual_core', 'v')):
        text = text.replace(f'import {module} as {alias}', f'from . import {module} as {alias}')
    text = text.replace('        import native_windows\n', '        from . import native_windows\n')
    return text.encode('utf-8')


def wheel(project: Path, output: Path) -> None:
    subprocess.run([sys.executable, '-B', '-c',
                    'import setuptools.build_meta as backend,sys; backend.build_wheel(sys.argv[1])',
                    str(output)], cwd=project, check=True, stdout=subprocess.DEVNULL,
                   env={**os.environ, 'PIP_NO_INDEX': '1', 'PYTHONNOUSERSITE': '1',
                        'SOURCE_DATE_EPOCH': '315532800', 'PYTHONHASHSEED': '0'})


def normalize_wheel(path: Path) -> None:
    """Replace build-time ZIP headers without changing any wheel member bytes."""
    with zipfile.ZipFile(path) as source:
        assert source.comment == b''
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
            digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode('ascii')
            writer.writerow((name, 'sha256=' + digest, str(len(raw))))
    writer.writerow((records[0], '', ''))
    members[records[0]] = rows.getvalue().encode('utf-8')
    temporary = path.with_suffix('.normalized')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_STORED,
                         allowZip64=False) as target:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            target.writestr(info, raw, compress_type=zipfile.ZIP_STORED)
    temporary.replace(path)


def build(output: Path) -> dict:
    output = output.resolve()
    if not output.is_dir() or output == ROOT or ROOT in output.parents:
        raise ValueError('OUTPUT_MUST_BE_EXISTING_DIRECTORY_OUTSIDE_REPOSITORY')
    if any(output.iterdir()):
        raise ValueError('OUTPUT_MUST_BE_EMPTY')
    if sys.version_info[:2] not in ((3, 12), (3, 13)):
        raise ValueError('PYTHON_312_OR_313_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='outlands-annotation-geometry-wheels-') as temporary:
        stage = Path(temporary)
        for tool, entry in TOOLS.items():
            source = ROOT / 'tools' / tool
            project = stage / tool
            package_name = 'outlands_' + tool.replace('-', '_')
            package = project / package_name
            package.mkdir(parents=True)
            (package / '__init__.py').write_text('"""OUTLANDS annotation and geometry tool."""\n', encoding='utf-8', newline='\n')
            for filename in (*SHARED, *EXTRA.get(tool, ()), entry + '.py'):
                (package / filename).write_bytes(isolated_source(verified_source(source, filename)))
            examples = package / 'examples'
            examples.mkdir()
            pinned = json.loads((source / 'SOURCE-MANIFEST.json').read_text(encoding='utf-8'))['files']
            example_names = sorted(name for name in pinned if name.startswith('examples/') and name.endswith('.json'))
            if not {'examples/input.json', 'examples/needs-review.json'} <= set(example_names):
                raise ValueError('FICTIONAL_EXAMPLES_REQUIRED')
            for name in example_names:
                (examples / Path(name).name).write_bytes(verified_source(source, name))
            (package / 'demo.py').write_text(
                '"""Run the bundled fictional example without reading project data."""\n'
                'import json\nfrom importlib.resources import files\n'
                'from . import ' + entry + '\n'
                'def main():\n'
                '    raw = files(__package__).joinpath("examples", "input.json").read_bytes()\n'
                '    report = ' + entry + '.' + OPERATIONS[tool] + '(raw)\n'
                '    print(json.dumps(report, sort_keys=True))\n'
                '    return 0 if report["status"] == "PASS" else 1\n', encoding='utf-8', newline='\n')
            source_readme = verified_source(source, 'README.md').decode('utf-8')
            (project / 'README.md').write_text(
                '# Installed ' + tool + '\n\n'
                'This wheel installs the `outlands-' + tool + '` command and the '
                '`' + package_name + '.' + entry + '.' + OPERATIONS[tool] + '(raw_json_bytes)` Python API. '
                'Run `outlands-' + tool + '-demo` for an embedded fictional example. '
                'Pass an explicit private JSON input file to the command. See the original '
                'source guide below for the schema, examples and limits. Its `python -B '
                + entry + '.py` commands apply to a complete extracted source folder.\n\n'
                + source_readme, encoding='utf-8', newline='\n')
            (project / 'LICENSE').write_bytes(verified_source(source, 'LICENSE'))
            (project / 'pyproject.toml').write_text(
                '[build-system]\nrequires = ["setuptools>=70", "wheel"]\n'
                'build-backend = "setuptools.build_meta"\n\n'
                '[project]\nname = "outlands-' + tool + '"\nversion = "' + VERSION + '"\n'
                'description = ' + json.dumps(DESCRIPTIONS[tool]) + '\n'
                'readme = "README.md"\nrequires-python = ">=3.12,<3.14"\n'
                'license = {file = "LICENSE"}\n\n'
                '[project.scripts]\n"outlands-' + tool + '" = "' + package_name + '.' + entry + ':main"\n'
                '"outlands-' + tool + '-demo" = "' + package_name + '.demo:main"\n\n'
                '[tool.setuptools.packages.find]\nwhere = ["."]\ninclude = ["' + package_name + '"]\n\n'
                '[tool.setuptools.package-data]\n"' + package_name + '" = ["examples/*.json"]\n',
                encoding='utf-8', newline='\n')
            wheel(project, output)

        collection = stage / 'collection'
        package = collection / 'outlands_annotation_geometry_collection'
        package.mkdir(parents=True)
        (package / '__init__.py').write_text('"""Annotation and geometry collection metadata."""\n', encoding='utf-8', newline='\n')
        (package / 'catalog.py').write_text(
            '"""List installed annotation and geometry entry points."""\n'
            'TOOLS = ' + repr(tuple('outlands-' + name for name in TOOLS)) + '\n'
            'def main():\n    print("\\n".join(TOOLS))\n', encoding='utf-8', newline='\n')
        (collection / 'README.md').write_text(
            '# OUTLANDS Annotation and Geometry Collection\n\nInstalls four independent offline Python tools. '
            'Run `outlands-annotation-geometry` to list their commands. See the repository integration guide.\n',
            encoding='utf-8', newline='\n')
        (collection / 'LICENSE').write_bytes(
            verified_source(ROOT / 'tools' / 'form-definition-contract-checker', 'LICENSE'))
        dependencies = '\n'.join('    "outlands-' + name + '==' + VERSION + '",' for name in TOOLS)
        (collection / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["setuptools>=70", "wheel"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            '[project]\nname = "outlands-annotation-geometry-collection"\nversion = "' + VERSION + '"\n'
            'description = "Install the four OUTLANDS annotation and geometry tools"\n'
            'readme = "README.md"\nrequires-python = ">=3.12,<3.14"\n'
            'license = {file = "LICENSE"}\n'
            'dependencies = [\n' + dependencies + '\n]\n\n'
            '[project.scripts]\noutlands-annotation-geometry = "outlands_annotation_geometry_collection.catalog:main"\n\n'
            '[tool.setuptools.packages.find]\nwhere = ["."]\n'
            'include = ["outlands_annotation_geometry_collection"]\n', encoding='utf-8', newline='\n')
        wheel(collection, output)

    files = sorted(output.glob('*.whl'))
    if len(files) != 5:
        raise RuntimeError('EXPECTED_FIVE_WHEELS')
    for path in files:
        normalize_wheel(path)
    manifest = {'format': 'outlands-annotation-geometry-wheel-v1', 'version': VERSION,
                'source_revision': 'cf1366d6a77b34c6fb7bc8d191191e00b55c595f',
                'wheels': [{'filename': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                           for path in files]}
    (output / 'SHA256SUMS.txt').write_text(
        ''.join(row['sha256'] + '  ' + row['filename'] + '\n' for row in manifest['wheels']),
        encoding='ascii', newline='\n')
    (output / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n',
                                          encoding='utf-8', newline='\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(build(parser.parse_args().output)))
