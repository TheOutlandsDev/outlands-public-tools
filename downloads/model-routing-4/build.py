"""Build one deterministic, source-only ZIP from four exact public Git trees."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ALLOWED = {'.py', '.json', '.md', '.gitattributes', 'LICENSE'}
DATE = (2020, 1, 1, 0, 0, 0)
MAX_FILE = 100_000
MAX_TOTAL = 5_000_000
SENSITIVE = {
    'EMAIL': re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I),
    'WINDOWS_ABSOLUTE': re.compile(r'\b[A-Z]:[\\/][^\s"\x27<>]+', re.I),
    'USER_HOME': re.compile(r'/home/|/Users/|\\Users\\|AppData|OneDrive', re.I),
    'IPV4': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    'MAC': re.compile(r'\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b', re.I),
    'KEY_MATERIAL': re.compile(r'BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|api[_-]?key\s*[:=]\s*["\x27][^"\x27]+|token\s*[:=]\s*["\x27][^"\x27]+', re.I),
    'UNC_PATH': re.compile(r'\\\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+'),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode('ascii')


def plan():
    value = json.loads((HERE / 'plan.json').read_text(encoding='utf-8'))
    if (value['format'] != 'outlands-model-routing-selection-v1' or value['version'] != '1.0.0'
            or not re.fullmatch(r'[0-9a-f]{40}', value['source_revision'])
            or value['expected_source_files'] != 73 or len(value['tools']) != 4):
        raise ValueError('PLAN_INVALID')
    names = [row['id'] for row in value['tools']]
    if len(set(names)) != 4 or any(not re.fullmatch(r'[a-z0-9-]+', name) for name in names):
        raise ValueError('TOOL_SELECTION_INVALID')
    if any(not re.fullmatch(r'[a-z][a-z0-9_]*\.py', row['entry']) for row in value['tools']):
        raise ValueError('ENTRY_SELECTION_INVALID')
    return value


def safe_name(name):
    parts = PurePosixPath(name).parts
    if (not parts or name.startswith('/') or '\\' in name or ':' in name
            or any(part in ('.', '..', '.git', '__pycache__', 'node_modules') for part in parts)
            or not name.isascii()):
        raise ValueError('SOURCE_PATH_REFUSED')
    if PurePosixPath(name).suffix not in ALLOWED and parts[-1] not in ALLOWED:
        raise ValueError('SOURCE_TYPE_REFUSED')


def source_files(value):
    paths = ['tools/' + row['id'] for row in value['tools']]
    revision = value['source_revision']
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', revision, '--', *paths], cwd=ROOT)
    result = {}
    for record in tree.split(b'\0'):
        if not record:
            continue
        meta, raw_name = record.split(b'\t', 1)
        mode, kind, _oid = meta.decode('ascii').split()
        name = raw_name.decode('utf-8')
        safe_name(name)
        if mode != '100644' or kind != 'blob' or not any(name.startswith(prefix + '/') for prefix in paths):
            raise ValueError('SOURCE_TREE_REFUSED')
        body = subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)
        if len(body) > MAX_FILE or b'\x00' in body or b'\r\n' in body:
            raise ValueError('SOURCE_BYTES_REFUSED')
        try:
            text = body.decode('utf-8')
        except UnicodeError:
            raise ValueError('SOURCE_TEXT_REFUSED') from None
        if any(pattern.search(text) for pattern in SENSITIVE.values()):
            raise ValueError('SOURCE_PRIVACY_REVIEW_REQUIRED')
        result[name] = body
    if len(result) != value['expected_source_files'] or sum(map(len, result.values())) > MAX_TOTAL:
        raise ValueError('SOURCE_COVERAGE_REFUSED')
    for row in value['tools']:
        prefix = 'tools/' + row['id'] + '/'
        if prefix + row['entry'] not in result or prefix + 'LICENSE' not in result:
            raise ValueError('TOOL_ENTRY_MISSING')
        manifest = json.loads(result[prefix + 'SOURCE-MANIFEST.json'])
        expected = {name.removeprefix(prefix) for name in result if name.startswith(prefix)} - {'SOURCE-MANIFEST.json'}
        if manifest['format'] != 'outlands-source-pins-v1' or set(manifest['files']) != expected:
            raise ValueError('SOURCE_MANIFEST_REFUSED')
        for name, pin in manifest['files'].items():
            raw = result[prefix + name]
            if pin != {'bytes': len(raw), 'sha256': digest(raw)}:
                raise ValueError('SOURCE_PIN_MISMATCH')
    return result


def payload(value, files):
    readme = (
        '# OUTLANDS Model Routing 4\n\n'
        'Four independent MIT Python source tools with invented examples. Python 3.12 or 3.13 '
        'must be supplied separately. This archive contains no runtime, private instance, Git history, '
        'user profile, environment file or network configuration.\n\n'
        'Each `tools/NAME/README.md` documents its input contract and limits. From that directory, '
        'run `python -B source_check.py` to verify its exact source files, then use the example command '
        'in its README. Keep real inputs and reports outside this source folder and private. '
        'All bundled examples are fictional and report PASS. '
        'A matching hash does not prove real-world correctness.\n\n'
        'The archive manifest lists only member names, sizes and SHA-256 hashes for verification. '
        'All ZIP timestamps and mode bits are fixed synthetic values. '
        'The MIT licenses retain the public TheOutlandsDev attribution.\n'
    ).encode('ascii')
    files = dict(files)
    files['README.md'] = readme
    manifest = {'format': 'outlands-model-routing-manifest-v1', 'version': value['version'],
                'tools': [row['id'] for row in value['tools']],
                'files': {name: {'bytes': len(raw), 'sha256': digest(raw)} for name, raw in sorted(files.items())}}
    files['MANIFEST.json'] = encode(manifest)
    return files


def archive_bytes(value, files):
    prefix = 'outlands-model-routing-4-' + value['version'] + '/'
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name, raw in sorted(files.items()):
            safe_name(name)
            info = zipfile.ZipInfo(prefix + name, DATE)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.extra = b''
            info.comment = b''
            archive.writestr(info, raw)
    return stream.getvalue()


def build(output):
    value = plan()
    files = payload(value, source_files(value))
    raw = archive_bytes(value, files)
    pin = digest(raw)
    if value['expected_zip_sha256'] is not None and pin != value['expected_zip_sha256']:
        raise ValueError('ZIP_PIN_MISMATCH')
    output = Path(output).resolve()
    if not output.is_dir() or output.is_relative_to(ROOT.resolve()):
        raise ValueError('EXTERNAL_EXISTING_OUTPUT_DIRECTORY_REQUIRED')
    filename = 'outlands-model-routing-4-' + value['version'] + '.zip'
    with (output / filename).open('xb') as handle:
        handle.write(raw)
    with (output / 'SHA256SUMS.txt').open('x', encoding='ascii', newline='\n') as handle:
        handle.write(pin + '  ' + filename + '\n')
    return {'status': 'PASS', 'filename': filename, 'sha256': pin,
            'tools': len(value['tools']), 'source_files': value['expected_source_files'],
            'archive_members': len(files)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), sort_keys=True))
