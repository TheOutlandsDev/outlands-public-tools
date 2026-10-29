"""Build a deterministic, pinned application-local Windows distribution."""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import stat
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
APP_SOURCE = '83c280b6c9f769376c634f67b1caeddeb9c4c427'
APP_SHA = '30ede891b1408effe56b607783a4b6fa083f61974786d44627ecbcdf86fc4263'
APP_URL = 'https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/production-planning-workbench-v0.1.1/production-planning-workbench-source.zip'
RUNTIME_VERSION = '3.14.10'
RUNTIME_SHA = '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
RUNTIME_URL = 'https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip'
TAG = 'production-planning-workbench-windows-v0.1.1-1'
FILENAME = 'production-planning-workbench-0.1.1-windows-x64.zip'
PREFIX = 'production-planning-workbench-0.1.1-windows-x64/'
EXTRAS = ('launch.py', 'planning_demo.py', 'Planning Demo.cmd', 'Planning Exercise.cmd', 'START-HERE.txt', 'FIVE-MINUTE.txt', 'THIRD-PARTY-NOTICES.txt')
PACKAGE_PATH = 'downloads/windows/production-planning-workbench/'


def sha(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return (json.dumps(value, indent=2) + '\n').encode()
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)


def download(url, digest, maximum, cached=None):
    if cached:
        body = cached.read_bytes()
    else:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Outlands-Data-Services-portable-build'}), timeout=60) as response:
            body = response.read(maximum + 1)
    if len(body) > maximum or sha(body) != digest: raise ValueError('UPSTREAM_DIGEST_MISMATCH')
    return body


def members(body):
    result = {}
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        for info in archive.infolist():
            name = info.orig_filename
            path = PurePosixPath(name)
            if info.is_dir() or any(x in ('','.','..') for x in name.split('/')) or '\\' in name or path.is_absolute() or '..' in path.parts or ':' in name or name.casefold() in {n.casefold() for n in result} or stat.S_IFMT(info.external_attr >> 16) not in (0,stat.S_IFREG):
                raise ValueError('UNEXPECTED_ARCHIVE_MEMBER')
            if info.file_size > 32 * 1024 * 1024: raise ValueError('MEMBER_BOUND_EXCEEDED')
            result[name] = archive.read(info)
    return result


def verify_record(wheel):
    records=[n for n in wheel if n.endswith('.dist-info/RECORD')]
    if len(records)!=1 or any('.data/' in n for n in wheel):raise ValueError('WHEEL_LAYOUT_REFUSED')
    record=records[0];rows=list(csv.reader(io.StringIO(wheel[record].decode('utf-8'))));seen=set()
    for row in rows:
        if len(row)!=3 or row[0] in seen or row[0] not in wheel:raise ValueError('WHEEL_RECORD_REFUSED')
        name,digest,size=row;seen.add(name)
        if name==record:
            if digest or size:raise ValueError('WHEEL_RECORD_SELF_HASH_REFUSED')
        elif digest!='sha256='+base64.urlsafe_b64encode(hashlib.sha256(wheel[name]).digest()).decode().rstrip('=') or size!=str(len(wheel[name])):raise ValueError('WHEEL_RECORD_HASH_MISMATCH')
    if seen!=set(wheel):raise ValueError('WHEEL_RECORD_INVENTORY_MISMATCH')


def payload(runtime=None, source=None, wheels=None):
    upstream = members(download(APP_URL, APP_SHA, 2*1024*1024, source))
    pre='production-planning-workbench/'
    manifest=json.loads(upstream[pre+'SOURCE-MANIFEST.json'])
    if set(upstream)!={pre+name for name in manifest['files']}|{pre+'SOURCE-MANIFEST.json'}:raise ValueError('SOURCE_INVENTORY_MISMATCH')
    files={}
    for name,body in upstream.items():
        local=name.removeprefix(pre)
        if body!=git('show',APP_SOURCE+':systems/production-planning-workbench/'+local):raise ValueError('APP_BYTES_MISMATCH')
        files['application/'+local]=body
    for name,row in manifest['files'].items():
        body=files['application/'+name]
        if row != dict(bytes=len(body),sha256=sha(body)):raise ValueError('SOURCE_HASH_MISMATCH')
    lock=json.loads(git('show','HEAD:'+PACKAGE_PATH+'dependencies-lock.json'))
    dependencies={}
    for package in lock['packages']:
        wheel=members(download(package['url'],package['sha256'],8*1024*1024, wheels/package['filename'] if wheels else None))
        verify_record(wheel)
        for name,body in wheel.items():
            if name.casefold() in {n.casefold() for n in dependencies}:raise ValueError('DEPENDENCY_COLLISION')
            dependencies[name]=body
    files.update({'dependencies/'+n:b for n,b in dependencies.items()})
    files['dependencies-lock.json']=encoded(lock)
    runtime_files = members(download(RUNTIME_URL, RUNTIME_SHA, 20*1024*1024, runtime))
    if not {'python.exe', 'LICENSE.txt', 'python314._pth', '_sqlite3.pyd', 'sqlite3.dll'} <= set(runtime_files):
        raise ValueError('RUNTIME_INCOMPLETE')
    # Only the documented module-search configuration changes; binaries/notices stay exact.
    runtime_files['python314._pth'] = b'python314.zip\n.\n../dependencies\n../application\n'
    files.update({'runtime/' + n: b for n, b in runtime_files.items()})
    for name in EXTRAS: files[name] = git('show', 'HEAD:'+PACKAGE_PATH + name)
    return files


def build(output, runtime=None, source=None, wheels=None):
    if not output.is_absolute() or output.exists() or not output.parent.is_dir() or ROOT == output or ROOT in output.parents:
        raise ValueError('NEW_EXTERNAL_ABSOLUTE_OUTPUT_REQUIRED')
    if git('diff', 'HEAD', '--name-only', '--', PACKAGE_PATH).strip(): raise ValueError('COMMIT_PACKAGING_FIRST')
    files = payload(runtime, source, wheels)
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
    receipt = dict(schema=1, tag=TAG, filename=FILENAME, app_version='0.1.1', app_source=APP_SOURCE,
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
    p.add_argument('--wheels',type=Path);a=p.parse_args(); build(a.output,a.runtime,a.source,a.wheels)
