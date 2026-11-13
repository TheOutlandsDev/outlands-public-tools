"""Extract one hash-pinned standalone CPython into a new owned prefix; no installation."""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
FACTS="""import hashlib,json,sys
from pathlib import Path
p=Path(sys._base_executable).resolve()
print(json.dumps(dict(python_version=sys.version.split()[0],executable=str(p),executable_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),executable_bytes=p.stat().st_size)))
"""

def clean_environment():
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','PIP_','LD_','DYLD_'))}
    env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_COLORS='0',NO_COLOR='1')
    return env


def sha(raw):return hashlib.sha256(raw).hexdigest()

def destination(path):
    assert path.is_absolute() and path.parent.is_dir() and not os.path.lexists(path)
    assert path.parent.resolve()==path.parent and not path.parent.is_symlink() and not getattr(path.parent,'is_junction',lambda:False)()
    assert not path.resolve().is_relative_to(ROOT.resolve())

def prepare(version,out,report):
    assert sys.platform in {'win32','linux'} and platform.machine().lower() in {'amd64','x86_64'},'WINDOWS_OR_LINUX_X64_REQUIRED'
    destination(out);destination(report)
    lock_raw=(ROOT/'PYTHON-LOCK.json').read_bytes();lock=json.loads(lock_raw)
    assert lock['schema']==1 and lock['python_build_release']=='20261110'
    minors=[minor for minor,value in lock['python_versions'].items() if value==version];assert len(minors)==1
    row=lock['python_archives'][sys.platform][minors[0]];assert row['python']==version
    filename=row['filename'];assert Path(filename).name==filename and '\\' not in filename and ':' not in filename
    assert row['url']=='https://github.com/astral-sh/python-build-standalone/releases/download/20261110/'+filename.replace('+','%2B')
    request=urllib.request.Request(row['url'],headers={'User-Agent':'OUTLANDS-pinned-Python-qualification'})
    with urllib.request.urlopen(request,timeout=60) as response:
        final=urllib.parse.urlsplit(response.url)
        assert final.scheme=='https' and final.hostname in {'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}
        raw=response.read(row['bytes']+1)
    assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],'PINNED_PYTHON_ARCHIVE_DIFFERS'
    out.mkdir()
    archive=out/filename
    with archive.open('xb') as target:target.write(raw)
    with tarfile.open(archive,'r:*') as source:
        members=source.getmembers();assert len(members)<60000 and sum(m.size for m in members)<1_500_000_000
        assert all(m.name=='python' or m.name.startswith('python/') for m in members)
        source.extractall(out,filter='data')
    executable=(out/'python'/('python.exe' if os.name=='nt' else 'bin/python'+minors[0])).resolve()
    assert executable.is_relative_to(out.resolve()) and executable.is_file() and not executable.is_symlink()
    before=sha(executable.read_bytes())
    result=subprocess.run([str(executable),'-I','-B','-c',FACTS],env=clean_environment(),capture_output=True,timeout=30)
    with (out/'python-probe-private.log').open('xb') as target:target.write(result.stdout+result.stderr)
    assert result.returncode==0 and not result.stderr,'PREPARED_PYTHON_PROBE_FAILED'
    facts=json.loads(result.stdout)
    assert facts['python_version']==version and Path(facts['executable']).resolve()==executable
    assert facts['executable_sha256']==before==sha(executable.read_bytes()) and facts['executable_bytes']==executable.stat().st_size
    value=dict(schema=1,status='PASS',platform=sys.platform,python_version=version,build_release='20261110',archive=row,
        executable_relative=executable.relative_to(out).as_posix(),executable_sha256=before,executable_bytes=executable.stat().st_size,
        preparation_helper_sha256=sha(Path(__file__).read_bytes()),python_lock_sha256=sha(lock_raw),archive_sha256_verified=True,
        actual_interpreter_verified=True,global_install_performed=False,binary_reproducibility_claimed=False)
    with report.open('x',encoding='utf-8',newline='\n') as target:target.write(json.dumps(value,indent=2)+'\n')
    return value,executable

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',required=True);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path);parser.add_argument('--github-env',action='store_true')
    args=parser.parse_args();value,executable=prepare(args.version,args.out,args.report)
    if args.github_env:
        assert os.environ.get('GITHUB_ACTIONS')=='true'
        target=Path(os.environ['GITHUB_ENV'])
        assert target.is_absolute() and target.is_file() and not target.is_symlink() and target.parent.resolve()==target.parent and target.stat().st_size<32768
        env=dict(OUTLANDS_GPT_PYTHON=str(executable),OUTLANDS_GPT_PYTHON_ROOT=str(args.out),OUTLANDS_GPT_PYTHON_RECEIPT=str(args.report))
        assert all('\n' not in text and '\r' not in text for text in env.values())
        with target.open('a',encoding='utf-8',newline='\n') as output:
            for key,text in env.items():output.write(key+'='+text+'\n')
    print(json.dumps(value))

if __name__=='__main__':main()
