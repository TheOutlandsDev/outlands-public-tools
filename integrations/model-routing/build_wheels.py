"""Build four isolated Python wheels and a collection wheel from pinned public tool files."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
VERSION = '1.0.0'
TOOLS = {
    'model-capability-checker': 'models',
    'request-routing-checker': 'routes',
    'fallback-chain-checker': 'fallbacks',
    'inference-receipt-reconciler': 'receipts',
}
SHARED = ('toolkit.py', 'native_windows.py', 'decision_core.py', 'routing_core.py')


def verified_source(directory: Path, filename: str) -> bytes:
    manifest = json.loads((directory / 'SOURCE-MANIFEST.json').read_text(encoding='utf-8'))
    expected = manifest['files'][filename]
    raw = (directory / filename).read_bytes()
    if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
        raise ValueError(f'SOURCE_MANIFEST_MISMATCH: {directory.name}/{filename}')
    return raw


def isolated_source(raw: bytes) -> bytes:
    text = raw.decode('utf-8')
    for module, alias in (('toolkit', 't'), ('decision_core', 'c'), ('routing_core', 'r')):
        text = text.replace(f'import {module} as {alias}', f'from . import {module} as {alias}')
    text = text.replace('        import native_windows\n', '        from . import native_windows\n')
    return text.encode('utf-8')


def wheel(project: Path, output: Path) -> None:
    subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-build-isolation', '--no-deps',
                    '--wheel-dir', str(output), str(project)], check=True,
                   env={**os.environ, 'PIP_NO_INDEX': '1', 'PYTHONNOUSERSITE': '1'})


def build(output: Path) -> dict:
    output = output.resolve()
    if not output.is_dir() or output == ROOT or ROOT in output.parents:
        raise ValueError('OUTPUT_MUST_BE_EXISTING_DIRECTORY_OUTSIDE_REPOSITORY')
    if any(output.iterdir()):
        raise ValueError('OUTPUT_MUST_BE_EMPTY')
    if sys.version_info[:2] not in ((3, 12), (3, 13)):
        raise ValueError('PYTHON_312_OR_313_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='outlands-routing-wheels-') as temporary:
        stage = Path(temporary)
        for tool, entry in TOOLS.items():
            source = ROOT / 'tools' / tool
            project = stage / tool
            package_name = 'outlands_' + tool.replace('-', '_')
            package = project / package_name
            package.mkdir(parents=True)
            (package / '__init__.py').write_text('"""OUTLANDS model routing tool."""\n', encoding='utf-8')
            for filename in (*SHARED, entry + '.py'):
                (package / filename).write_bytes(isolated_source(verified_source(source, filename)))
            examples = package / 'examples'
            examples.mkdir()
            for filename in ('input.json', 'needs-review.json'):
                (examples / filename).write_bytes(verified_source(source, 'examples/' + filename))
            (package / 'demo.py').write_text(
                '"""Run the bundled fictional example without reading project data."""\n'
                'import json\nfrom importlib.resources import files\n'
                'from . import ' + entry + '\n'
                'def main():\n'
                '    raw = files(__package__).joinpath("examples", "input.json").read_bytes()\n'
                '    report = ' + entry + '.check(raw)\n'
                '    print(json.dumps(report, sort_keys=True))\n'
                '    return 0 if report["status"] == "PASS" else 1\n', encoding='utf-8')
            source_readme = verified_source(source, 'README.md').decode('utf-8')
            (project / 'README.md').write_text(
                '# Installed ' + tool + '\n\n'
                'This wheel installs the `outlands-' + tool + '` command and the '
                '`' + package_name + '.' + entry + '.check(raw_json_bytes)` Python API. '
                'Run `outlands-' + tool + '-demo` for an embedded fictional example. '
                'Pass an explicit private JSON input file to the command. See the original '
                'source guide below for the schema, examples and limits. Its `python -B '
                + entry + '.py` commands apply to a complete extracted source folder.\n\n'
                + source_readme, encoding='utf-8')
            (project / 'LICENSE').write_bytes(verified_source(source, 'LICENSE'))
            (project / 'pyproject.toml').write_text(
                '[build-system]\nrequires = ["setuptools>=70", "wheel"]\n'
                'build-backend = "setuptools.build_meta"\n\n'
                '[project]\nname = "outlands-' + tool + '"\nversion = "' + VERSION + '"\n'
                'description = "Offline model routing declaration checker"\n'
                'readme = "README.md"\nrequires-python = ">=3.12,<3.14"\n'
                'license = {file = "LICENSE"}\n\n'
                '[project.scripts]\n"outlands-' + tool + '" = "' + package_name + '.' + entry + ':main"\n'
                '"outlands-' + tool + '-demo" = "' + package_name + '.demo:main"\n\n'
                '[tool.setuptools.packages.find]\nwhere = ["."]\ninclude = ["' + package_name + '"]\n\n'
                '[tool.setuptools.package-data]\n"' + package_name + '" = ["examples/*.json"]\n',
                encoding='utf-8')
            wheel(project, output)

        collection = stage / 'collection'
        package = collection / 'outlands_model_routing_collection'
        package.mkdir(parents=True)
        (package / '__init__.py').write_text('"""Model routing collection metadata."""\n', encoding='utf-8')
        (package / 'catalog.py').write_text(
            '"""List installed model routing entry points."""\n'
            'TOOLS = ' + repr(tuple('outlands-' + name for name in TOOLS)) + '\n'
            'def main():\n    print("\\n".join(TOOLS))\n', encoding='utf-8')
        (collection / 'README.md').write_text(
            '# OUTLANDS Model Routing Collection\n\nInstalls four independent offline Python tools. '
            'Run `outlands-model-routing` to list their commands. See the repository integration guide.\n',
            encoding='utf-8')
        (collection / 'LICENSE').write_bytes(
            verified_source(ROOT / 'tools' / 'model-capability-checker', 'LICENSE'))
        dependencies = '\n'.join('    "outlands-' + name + '==' + VERSION + '",' for name in TOOLS)
        (collection / 'pyproject.toml').write_text(
            '[build-system]\nrequires = ["setuptools>=70", "wheel"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            '[project]\nname = "outlands-model-routing-collection"\nversion = "' + VERSION + '"\n'
            'description = "Install the four OUTLANDS model routing tools"\n'
            'readme = "README.md"\nrequires-python = ">=3.12,<3.14"\n'
            'license = {file = "LICENSE"}\n'
            'dependencies = [\n' + dependencies + '\n]\n\n'
            '[project.scripts]\noutlands-model-routing = "outlands_model_routing_collection.catalog:main"\n\n'
            '[tool.setuptools.packages.find]\nwhere = ["."]\n'
            'include = ["outlands_model_routing_collection"]\n', encoding='utf-8')
        wheel(collection, output)

    files = sorted(output.glob('*.whl'))
    if len(files) != 5:
        raise RuntimeError('EXPECTED_FIVE_WHEELS')
    manifest = {'format': 'outlands-model-routing-wheel-pilot-v1', 'version': VERSION,
                'source_revision': 'c9316edab10709a715b056cd6169827617ea404c',
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
