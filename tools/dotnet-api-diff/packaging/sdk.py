"""Explicit maintainer download of a pinned official SDK; never used by the API Diff CLI."""
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

def provision(version,out):
    records=json.loads((ROOT/'docs/SDKS.json').read_text())['releases']
    selected=[r for r in records if r['version']==version]
    assert len(selected)==1 and sys.platform in ('win32','linux')
    assets=[a for a in selected[0]['assets'] if a['platform']==sys.platform]
    assert len(assets)==1 and out.is_absolute() and not out.exists() and not out.is_relative_to(ROOT)
    asset=assets[0]
    assert asset['url']=='https://builds.dotnet.microsoft.com/dotnet/Sdk/'+version+'/'+asset['filename']
    out.mkdir();archive=out/asset['filename'];digest=hashlib.sha512();size=0
    with urllib.request.urlopen(urllib.request.Request(asset['url'],headers={'User-Agent':'OUTLANDS-sdk-qualification'}),timeout=60) as response,archive.open('xb') as target:
        while block:=response.read(1024*1024):
            size+=len(block)
            if size>512*1024*1024:raise ValueError('SDK_ARCHIVE_SIZE_LIMIT')
            digest.update(block);target.write(block)
    assert digest.hexdigest()==asset['sha512'],'SDK_HASH_MISMATCH'
    install=out/'runtime';install.mkdir()
    if os.name=='nt':
        with zipfile.ZipFile(archive) as source:
            names=source.namelist();assert len(names)==len(set(names))
            for name in names:assert not name.startswith(('/','\\')) and '..' not in name.split('/') and '\\' not in name and ':' not in name
            source.extractall(install)
        host=install/'dotnet.exe'
    else:
        with tarfile.open(archive) as source:source.extractall(install,filter='data')
        host=install/'dotnet';host.chmod(host.stat().st_mode|0o111)
    home=out/'home';home.mkdir()
    env=dict(os.environ,DOTNET_ROOT=str(install),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_CLI_HOME=str(home),
        DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true',
        DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_CLI_USE_MSBUILD_SERVER='0',MSBUILDDISABLENODEREUSE='1')
    (out/'global.json').write_text(json.dumps({'sdk':{'version':version,'rollForward':'disable','allowPrerelease':False}}),encoding='utf-8')
    actual=subprocess.check_output([str(host),'--version'],cwd=out,env=env,text=True,timeout=45).strip()
    assert actual==version,'SDK_VERSION_MISMATCH'
    receipt=dict(status='PASS',version=version,framework=selected[0]['framework'],platform=sys.platform,filename=asset['filename'],
        bytes=size,sha512=asset['sha512'],source=selected[0]['source'])
    (out/'sdk-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version',required=True,choices=('10.0.404','11.0.100'));p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();provision(a.version,a.out)
