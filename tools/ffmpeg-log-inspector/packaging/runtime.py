"""Explicit maintainer prerequisite download; never imported by ZIP inspection."""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def provision(version, out):
    records=json.loads((ROOT/'docs/RUNTIMES.json').read_text())['releases']
    releases=[row for row in records if row['version']==version]
    assert len(releases)==1 and sys.platform in ('win32','linux')
    assets=[row for row in releases[0]['assets'] if row['platform']==sys.platform]
    assert len(assets)==1
    asset=assets[0]
    assert out.is_absolute() and not out.exists() and not out.is_relative_to(ROOT)
    expected='https://github.com/PowerShell/PowerShell/releases/download/v'+version+'/'+asset['filename']
    assert asset['url']==expected and 0<asset['bytes']<256*1024*1024
    out.mkdir()
    archive=out/asset['filename']
    digest=hashlib.sha256();size=0
    with urllib.request.urlopen(urllib.request.Request(expected,headers={'User-Agent':'OUTLANDS-runtime-qualification'}),timeout=60) as response, archive.open('xb') as target:
        while block:=response.read(1024*1024):
            size+=len(block)
            if size>asset['bytes']: raise ValueError('RUNTIME_SIZE_EXCEEDED')
            target.write(block);digest.update(block)
    assert size==asset['bytes'] and digest.hexdigest()==asset['sha256'], 'RUNTIME_HASH_MISMATCH'
    install=out/'runtime';install.mkdir()
    if sys.platform=='win32':
        with zipfile.ZipFile(archive) as source:
            names=source.namelist()
            assert len(names)==len(set(names))
            for name in names:
                assert not name.startswith(('/','\\')) and '..' not in name.split('/') and '\\' not in name and ':' not in name
            source.extractall(install)
        executable=install/'pwsh.exe'
    else:
        with tarfile.open(archive) as source: source.extractall(install,filter='data')
        executable=install/'pwsh';executable.chmod(executable.stat().st_mode|0o111)
    actual=subprocess.check_output([str(executable),'-NoLogo','-NoProfile','-Command','$PSVersionTable.PSVersion.ToString()'],text=True,timeout=30).strip()
    assert actual==version,'RUNTIME_VERSION_MISMATCH'
    receipt=dict(status='PASS',version=version,platform=sys.platform,filename=asset['filename'],sha256=asset['sha256'],bytes=size,source=releases[0]['source'])
    (out/'runtime-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(receipt))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',choices=('7.6.10','7.7.0'),required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();provision(args.version,args.out)
