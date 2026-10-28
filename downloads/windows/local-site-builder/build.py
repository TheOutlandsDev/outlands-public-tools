"""Build a deterministic portable Windows app from unchanged pinned public inputs."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
APP_SOURCE = '42d4490e62c7ffb5d4d40a19e0c27e3ceb2d8897'
APP_SHA = 'd5253bcff738c69b4f60a5b2c4ecf94f3044512ed41b9f4a91d6897af029ff11'
APP_URL = 'https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/local-site-builder-v1.0.2/local-site-builder-1.0.2.zip'
RUNTIME_VERSION = '24.22.2'
RUNTIME_SHA = 'ca1bff5d8ead13c9f2ea404a176db46bd430704d5b5113734049fa365e7799e2'
RUNTIME_URL = 'https://nodejs.org/dist/v24.22.2/node-v24.22.2-win-x64.zip'
TAG = 'local-site-builder-windows-v1.0.2-1'
FILENAME = 'local-site-builder-1.0.2-windows-x64.zip'
PREFIX = 'local-site-builder-1.0.2-windows-x64/'
PACKAGE_PATH = 'downloads/windows/local-site-builder/'
EXTRAS = ('launch.js', 'Local Site Builder.cmd', 'START-HERE.txt', 'THIRD-PARTY-NOTICES.txt')
NATIVE = 'application/node_modules/better-sqlite3/prebuilds/win32-x64.node'


def sha(b): return hashlib.sha256(b).hexdigest()
def encoded(x): return (json.dumps(x, indent=2)+'\n').encode()
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def safe(name):
    p=PurePosixPath(name)
    if not name or p.is_absolute() or '\\' in name or ':' in name or any(x in ('','..','.') for x in name.split('/')):
        raise ValueError('UNSAFE_MEMBER')
    return name

def download(url,digest,maximum,cached=None,algorithm='sha256'):
    if cached: body=cached.read_bytes()
    else:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Outlands-Site-Portable'}),timeout=60) as r:body=r.read(maximum+1)
    actual=hashlib.new(algorithm,body).hexdigest()
    if len(body)>maximum or actual!=digest:raise ValueError('UPSTREAM_DIGEST_MISMATCH')
    return body

def members(body):
    result={}
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        for info in z.infolist():
            if info.is_dir():continue
            n=safe(info.orig_filename)
            if n.casefold() in {x.casefold() for x in result} or info.file_size>128*1024*1024:raise ValueError('UNEXPECTED_ARCHIVE_MEMBER')
            result[n]=z.read(info)
    return result

def tar_members(body,root="package"):
    result={};seen=set()
    with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz') as t:
        for i in t:
            if i.isdir():continue
            n=safe(i.name)
            if not i.isfile() or not n.startswith(root+'/') or n.casefold() in seen or i.size>32*1024*1024:raise ValueError('UNSAFE_NPM_MEMBER')
            seen.add(n.casefold());result[n[len(root)+1:]]=t.extractfile(i).read()
    return result

def payload(runtime=None,source=None):
    upstream=members(download(APP_URL,APP_SHA,4*1024*1024,source));pre='local-site-builder-1.0.2/'
    manifest=json.loads(upstream[pre+'SOURCE-MANIFEST.json'])
    if set(upstream)!={pre+r['path'] for r in manifest['files']}|{pre+'SOURCE-MANIFEST.json'}:raise ValueError('SOURCE_INVENTORY_MISMATCH')
    files={}
    for n,b in upstream.items():
        local=n.removeprefix(pre)
        if b!=git('show',APP_SOURCE+':tools/local-site-builder/'+local):raise ValueError('SOURCE_BYTES_MISMATCH')
        files['application/'+local]=b
    for r in manifest['files']:
        b=files['application/'+r['path']]
        if len(b)!=r['bytes'] or sha(b)!=r['sha256']:raise ValueError('SOURCE_HASH_MISMATCH')
    lock=json.loads(files['application/package-lock.json'])['packages']
    def dependency(pair):
        name,row=pair
        if not name:return {}
        if not name.startswith('node_modules/') or row.get('dev') or row.get('link') or not row['resolved'].startswith('https://registry.npmjs.org/'):
            raise ValueError('LOCK_BOUNDARY')
        alg,digest=row['integrity'].split('-',1)
        if alg!='sha512':raise ValueError('SHA512_REQUIRED')
        body=download(row['resolved'],base64.b64decode(digest).hex(),32*1024*1024,algorithm=alg)
        root={'node_modules/busboy':'mscdex-busboy-9aadb7a','node_modules/streamsearch':'mscdex-streamsearch-b9e9b39'}.get(name,'package')
        extracted=tar_members(body,root)
        if json.loads(extracted['package.json'])['version']!=row['version']:raise ValueError('DEPENDENCY_VERSION_MISMATCH')
        return {'application/'+name+'/'+n:b for n,b in extracted.items()}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for extra in pool.map(dependency,lock.items()):
            if set(extra)&set(files):raise ValueError('DEPENDENCY_COLLISION')
            files.update(extra)
    rt=members(download(RUNTIME_URL,RUNTIME_SHA,64*1024*1024,runtime));rp='node-v'+RUNTIME_VERSION+'-win-x64/'
    # npm/node-gyp are build tools only. Deliver official executable and full notices.
    for n in ('node.exe','LICENSE','README.md','CHANGELOG.md'):
        files['runtime/'+n]=rt[rp+n]
    for n in EXTRAS:files[n]=git('show','HEAD:'+PACKAGE_PATH+n)
    return files

def validate_native(b):
    if len(b)<1024 or b[:2]!=b'MZ':raise ValueError('NATIVE_PE_REQUIRED')
    offset=int.from_bytes(b[60:64],'little')
    if b[offset:offset+6]!=b'PE\0\0d\x86':raise ValueError('NATIVE_X64_REQUIRED')

def write_files(files,root):
    for n,b in files.items():
        p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)

def build(output,runtime=None,source=None):
    if not output.is_absolute() or output.exists() or not output.parent.is_dir() or ROOT in output.parents:raise ValueError('NEW_EXTERNAL_OUTPUT_REQUIRED')
    if git('diff','HEAD','--name-only','--',PACKAGE_PATH).strip():raise ValueError('COMMIT_PACKAGING_FIRST')
    files=payload(runtime,source);native=files[NATIVE];validate_native(native)
    info=dict(method='unchanged prebuild from SHA512-locked npm package',package='better-sqlite3',version='13.0.3',node_api=10,path=NATIVE,native_sha256=sha(native))
    files['NATIVE-ORIGIN.json']=encoded(info)
    revision=git('rev-parse','HEAD').decode().strip()
    files['PACKAGE-MANIFEST.json']=encoded(dict(schema=1,package_version='1.0.2-windows.1',app_source=APP_SOURCE,packaging_source=revision,runtime=RUNTIME_VERSION,files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())]))
    output.mkdir()
    with zipfile.ZipFile(output/FILENAME,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(files.items()):
            i=zipfile.ZipInfo(PREFIX+n,(1980,1,1,0,0,0));i.create_system=3;i.external_attr=0o100644<<16;i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,b,compresslevel=9)
    receipt=dict(schema=1,tag=TAG,filename=FILENAME,app_version='1.0.2',app_source=APP_SOURCE,source_zip_sha256=APP_SHA,packaging_source=revision,runtime_version=RUNTIME_VERSION,runtime_url=RUNTIME_URL,runtime_sha256=RUNTIME_SHA,files=len(files),bytes=(output/FILENAME).stat().st_size,sha256=sha((output/FILENAME).read_bytes()),dependencies=86,native=info)
    (output/'release-receipt.json').write_bytes(encoded(receipt))
    (output/'SHA256SUMS.txt').write_text(''.join(sha((output/n).read_bytes())+'  '+n+'\n' for n in (FILENAME,'release-receipt.json')),encoding='utf-8',newline='\n')
    print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--runtime',type=Path);p.add_argument('--source',type=Path);a=p.parse_args();build(a.output,a.runtime,a.source)
