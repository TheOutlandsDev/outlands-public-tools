"""Build deterministic source downloads from a fixed public Git tree. No installs."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SUPPLEMENTS = (
    'packages/build.py', 'packages/catalog.json', 'packages/README.md',
    'packages/RELEASE.md', 'packages/REVIEW.md', 'packages/tests/test_packages.py',
    'methodology/worked-examples/README.md',
    'methodology/worked-examples/run_examples.py',
    'methodology/worked-examples/release-review.md',
    'methodology/worked-examples/change-review.md',
    'methodology/worked-examples/document-handoff.md',
)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def safe_name(name):
    parts = PurePosixPath(name).parts
    if not parts or name.startswith('/') or '\\' in name or ':' in name or any(p in ('..', '.') for p in parts):
        raise ValueError('UNSAFE_MEMBER')
    if any(p.lower() in ('.git', '__pycache__', 'node_modules') for p in parts):
        raise ValueError('RUNTIME_MEMBER')

def public_tree(revision):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('EXACT_REVISION_REQUIRED')
    result = {}
    with tarfile.open(fileobj=io.BytesIO(git('archive', '--format=tar', revision))) as archive:
        for entry in archive:
            if entry.isdir():
                continue
            if not entry.isfile():
                raise ValueError('ORDINARY_GIT_FILES_REQUIRED')
            safe_name(entry.name)
            result[entry.name] = archive.extractfile(entry).read()
    return result

def validate_catalog(catalog, source):
    names = [name for group in catalog['groups'] for name in group['tools']]
    actual = {p.split('/')[1] for p in source if p.startswith('tools/')}
    systems = {p.split('/')[1] for p in source if p.startswith('systems/') and p.count('/') > 1}
    if len(names) != len(set(names)) or set(names) != actual:
        raise ValueError('TOOL_COVERAGE_MISMATCH')
    if set(catalog['systems']) != systems:
        raise ValueError('SYSTEM_COVERAGE_MISMATCH')
    if len({g['id'] for g in catalog['groups']}) != len(catalog['groups']):
        raise ValueError('DUPLICATE_PACKAGE')
    for name in names + catalog['systems']:
        if not re.fullmatch('[a-z0-9-]+', name):
            raise ValueError('INVALID_COMPONENT')

def zip_bytes(files, prefix):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, body in sorted(files.items()):
            safe_name(name)
            info = zipfile.ZipInfo(prefix + '/' + name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, body)
    return out.getvalue()

def verify_archive(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP_CRC_MISMATCH')
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('DUPLICATE_MEMBER')
        prefix = names[0].split('/')[0] + '/'
        for name in names:
            safe_name(name)
            if not name.startswith(prefix):
                raise ValueError('MULTIPLE_ROOTS')
        manifest = json.loads(archive.read(prefix + 'PACKAGE-MANIFEST.json'))
        expected = {prefix + p for p in manifest['files']} | {prefix + 'PACKAGE-MANIFEST.json'}
        if set(names) != expected:
            raise ValueError('INVENTORY_MISMATCH')
        for path, record in manifest['files'].items():
            body = archive.read(prefix + path)
            if len(body) != record['bytes'] or digest(body) != record['sha256']:
                raise ValueError('FILE_HASH_MISMATCH')
        return manifest

def title(source, path):
    first = source[path].decode('utf-8-sig').splitlines()[0].lstrip('# ').strip()
    return re.sub(r'^OUTLANDS\s*\|\s*', '', first)

def component_records(catalog, source):
    records = []
    for group in catalog['groups']:
        for name in group['tools']:
            path = 'tools/' + name
            records.append({'id': name, 'title': title(source, path + '/README.md'),
                            'path': path, 'group': group['id'], 'kind': 'tool'})
    for name in catalog['systems']:
        path = 'systems/' + name
        records.append({'id': name, 'title': title(source, path + '/README.md'),
                        'path': path, 'group': 'systems', 'kind': 'application'})
    return records

def start_here(catalog, label, components, full):
    repo = 'https://github.com/' + catalog['repository']
    lines = ['# OUTLANDS Toolkit ' + catalog['version'] + ' — ' + label, '',
             'Source snapshot: `' + catalog['source_revision'] + '`.', '',
             'Download source, read the requirements, then run one fictional workflow.',
             'Python, Node.js, PowerShell, .NET, Tk and optional dependencies are supplied separately.',
             'Each module README remains the authority for versions, platforms, licenses and test scope.',
             'No installer starts automatically. No live services, account settings or real data are bundled.', '',
             '## Included components', '']
    for c in components:
        lines.append('- [' + c['title'] + '](' + c['path'] + '/README.md)')
    lines += ['', '## Methodology and examples', '',
              '- [Completed examples and runnable checks](methodology/worked-examples/README.md)',
              '- [Reusable templates](methodology/README.md)',
              '- [Verify this download](packages/README.md)', '',
              'Run from the extracted package root. Pick an existing private scratch parent outside this package.',
              'The complete and release-QA packages include the automated three-example walkthrough:', '',
              '```text', 'python -B methodology/worked-examples/run_examples.py --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY', '```', '',
              'The other families include the same records and link to their own fictional examples.',
              'The three-example runner needs the release-QA package or complete package.', '',
              'Expected results are documented separately from results observed on your machine.',
              'Native operation, production suitability and live integrations retain their documented limitations.']
    if not full:
        lines += ['', '## Related documentation', '',
                  'This family preserves the original source layout and includes shared collection documents.',
                  'Those documents may reference other families. Use the complete package for the full offline tree,',
                  'or open the [pinned online collection](' + repo + '/tree/' + catalog['source_revision'] + ').',
                  'The complete six-system application set is included in the complete package.']
    return ('\n'.join(lines) + '\n').encode('utf-8')

def build(output):
    catalog = json.loads((ROOT / 'packages/catalog.json').read_text(encoding='utf-8'))
    source = public_tree(catalog['source_revision'])
    validate_catalog(catalog, source)
    revision = git('rev-parse', 'HEAD').decode().strip()
    supplements = {p: git('show', revision + ':' + p) for p in SUPPLEMENTS}
    components = component_records(catalog, source)
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(ROOT) or not output.parent.is_dir():
        raise ValueError('NEW_EXTERNAL_OUTPUT_REQUIRED')
    output.mkdir()
    assets = []
    root_files = {p for p in source if '/' not in p}
    shared = root_files | {p for p in source if p.startswith(('docs/', 'methodology/'))}
    definitions = [('complete', 'Complete source collection', None)] + [(g['id'], g['title'], g['tools']) for g in catalog['groups']]
    for package_id, label, tools in definitions:
        selected = set(source) if tools is None else shared | {p for p in source if any(p.startswith('tools/' + name + '/') for name in tools)}
        files = {p: source[p] for p in sorted(selected)}
        files.update(supplements)
        included = components if tools is None else [c for c in components if c['id'] in tools]
        files['START-HERE.md'] = start_here(catalog, label, included, tools is None)
        name = 'outlands-' + package_id + '-' + catalog['version']
        manifest = {'schema': 1, 'package': package_id, 'source_revision': catalog['source_revision'],
                    'packaging_revision': revision, 'components': [c['path'] for c in included],
                    'files': {p: {'bytes': len(b), 'sha256': digest(b),
                                   'origin': 'published-source' if p in source and b == source[p] else 'packaging-and-examples'}
                              for p, b in sorted(files.items())}}
        files['PACKAGE-MANIFEST.json'] = encode(manifest)
        body = zip_bytes(files, name)
        verify_archive(body)
        filename = name + '.zip'
        (output / filename).write_bytes(body)
        assets.append({'id': package_id, 'title': label, 'filename': filename, 'bytes': len(body),
                       'sha256': digest(body), 'files': len(files), 'components': len(included),
                       'url': 'https://github.com/' + catalog['repository'] + '/releases/download/' + catalog['tag'] + '/' + filename})
    download_catalog = dict(catalog, packaging_revision=revision, components=components, downloads=assets)
    (output / 'catalog.json').write_bytes(encode(download_catalog))
    (output / 'release-matrix.json').write_bytes(encode({'source_revision': catalog['source_revision'], 'packaging_revision': revision, 'downloads': assets}))
    sums = ''.join(digest(p.read_bytes()) + '  ' + p.name + '\n' for p in sorted(output.iterdir()) if p.is_file())
    (output / 'SHA256SUMS.txt').write_text(sums, encoding='ascii', newline='\n')
    print(json.dumps({'packages': len(assets), 'tools': sum(len(g['tools']) for g in catalog['groups']),
                      'systems': len(catalog['systems']), 'source_revision': catalog['source_revision']}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    build(parser.parse_args().output)
