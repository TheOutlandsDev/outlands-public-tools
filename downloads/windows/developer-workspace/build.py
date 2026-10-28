"""Build a deterministic, pinned application-local Windows distribution."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
APP_SOURCE = 'f67b3c5e686595336d243d44e85bc2b3ccc76b0d'
APP_SHA = 'f7e22be3bf8c53c5e9ea5843432e68128c9a643686d623a85665adaee759b0a2'
APP_URL = 'https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/developer-workspace-v0.1.1/developer-workspace-0.1.1.zip'
RUNTIME_VERSION = '3.14.10'
RUNTIME_SHA = '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
RUNTIME_URL = 'https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip'
TAG = 'developer-workspace-windows-v0.1.1-1'
FILENAME = 'developer-workspace-0.1.1-windows-x64.zip'
PREFIX = 'developer-workspace-0.1.1-windows-x64/'
EXTRAS = ('launch.py', 'Developer Demo.cmd', 'Developer Workspace.cmd', 'START-HERE.txt', 'THIRD-PARTY-NOTICES.txt')
PACKAGE_PATH = 'downloads/windows/developer-workspace/'


def sha(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return (json.dumps(value, indent=2) + '\n').encode()
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)


def download(url, digest, maximum, cached=None):
    if cached:
        body = cached.read_bytes()
    else:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Outlands-Developer-portable-build'}), timeout=60) as response:
            body = response.read(maximum + 1)
    if len(body) > maximum or sha(body) != digest: raise ValueError('UPSTREAM_DIGEST_MISMATCH')
    return body


def members(body):
    result = {}
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        for info in archive.infolist():
            name = info.orig_filename
            path = PurePosixPath(name)
            if info.is_dir() or '\\' in name or path.is_absolute() or '..' in path.parts or ':' in name or name in result:
                raise ValueError('UNEXPECTED_ARCHIVE_MEMBER')
            if info.file_size > 32 * 1024 * 1024: raise ValueError('MEMBER_BOUND_EXCEEDED')
            result[name] = archive.read(info)
    return result


def payload(runtime=None, source=None):
    upstream = members(download(APP_URL, APP_SHA, 4*1024*1024, source))
    outer = json.loads(upstream['developer-workspace-0.1.1/PACKAGE-MANIFEST.json'])
    if outer['source_revision'] != APP_SOURCE: raise ValueError('APP_SOURCE_MISMATCH')
    expected = {'developer-workspace-0.1.1/' + n for n in outer['files']} | {'developer-workspace-0.1.1/PACKAGE-MANIFEST.json'}
    if set(upstream) != expected: raise ValueError('APP_MEMBER_MISMATCH')
    for name,row in outer['files'].items():
        raw=upstream['developer-workspace-0.1.1/'+name]
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('OUTER_SOURCE_PIN_MISMATCH')
    files = {n.removeprefix('developer-workspace-0.1.1/'):b for n,b in upstream.items() if n.startswith('developer-workspace-0.1.1/application/')}
    manifest = json.loads(files['application/SOURCE-MANIFEST.json'])
    if set(files) != {'application/'+n for n in manifest['files']}|{'application/SOURCE-MANIFEST.json'}:raise ValueError('SOURCE_INVENTORY_MISMATCH')
    for name,row in manifest['files'].items():
        raw=files['application/'+name]
        if row!=dict(bytes=len(raw),sha256=sha(raw)) or raw!=git('show',APP_SOURCE+':systems/developer-workspace/'+name):raise ValueError('APP_BYTES_MISMATCH')
    runtime_files = members(download(RUNTIME_URL, RUNTIME_SHA, 20*1024*1024, runtime))
    if not {'python.exe', 'LICENSE.txt', 'python314._pth', '_sqlite3.pyd', 'sqlite3.dll'} <= set(runtime_files):
        raise ValueError('RUNTIME_INCOMPLETE')
    # Only the documented module-search configuration changes; binaries/notices stay exact.
    runtime_files['python314._pth'] = b'python314.zip\n.\n../application\n'
    files.update({'runtime/' + n: b for n, b in runtime_files.items()})
    for name in EXTRAS: files[name] = git('show', 'HEAD:'+PACKAGE_PATH + name)
    return files


def build(output, runtime=None, source=None):
    if not output.is_absolute() or output.exists() or not output.parent.is_dir() or ROOT == output or ROOT in output.parents:
        raise ValueError('NEW_EXTERNAL_ABSOLUTE_OUTPUT_REQUIRED')
    if git('diff', 'HEAD', '--name-only', '--', PACKAGE_PATH).strip(): raise ValueError('COMMIT_PACKAGING_FIRST')
    files = payload(runtime, source)
    revision = git('rev-parse', 'HEAD').decode().strip()
    files['PACKAGE-MANIFEST.json'] = encoded(dict(schema=1, package_version='0.1.1-windows.1',
        app_source=APP_SOURCE, packaging_source=revision, runtime=RUNTIME_VERSION,
        files=[dict(path=n, bytes=len(b), sha256=sha(b)) for n,b in sorted(files.items())]))
    output.mkdir()
    with zipfile.ZipFile(output / FILENAME, 'x', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(PREFIX + name, (1980,1,1,0,0,0))
            info.create_system = 3; info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    receipt = dict(schema=1, tag=TAG, filename=FILENAME, app_version='0.1.0', app_source=APP_SOURCE,
                   source_zip_sha256=APP_SHA, packaging_source=revision, runtime_version=RUNTIME_VERSION,
                   runtime_url=RUNTIME_URL, runtime_sha256=RUNTIME_SHA, files=len(files),
                   bytes=(output/FILENAME).stat().st_size, sha256=sha((output/FILENAME).read_bytes()))
    (output/'release-receipt.json').write_bytes(encoded(receipt))
    (output/'SHA256SUMS.txt').write_text(''.join(sha((output/n).read_bytes())+'  '+n+'\n' for n in [FILENAME,'release-receipt.json']), encoding='utf-8', newline='\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--runtime',type=Path); p.add_argument('--source',type=Path)
    a=p.parse_args(); build(a.output,a.runtime,a.source)
