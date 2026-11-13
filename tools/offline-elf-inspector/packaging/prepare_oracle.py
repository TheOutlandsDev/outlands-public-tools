"""Attest existing qualification-only GCC/readelf; never install or run inspected ELF."""
if not __debug__:
    raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BLOCKED={'LD_LIBRARY_PATH','LD_PRELOAD','LD_AUDIT','DYLD_LIBRARY_PATH',
    'DYLD_FALLBACK_LIBRARY_PATH','DYLD_INSERT_LIBRARIES','GCC_EXEC_PREFIX',
    'COMPILER_PATH','LIBRARY_PATH','CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH',
    'GCC_SPECS','CC','CXX','CPP','CFLAGS','CPPFLAGS','LDFLAGS','LIBS','MAKEFLAGS',
    'MFLAGS','MAKEFILES','DESTDIR','CONFIG_SITE'}

def compiler_environment():
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','PIP_')) and k.upper() not in BLOCKED}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHON_COLORS='0',NO_COLOR='1',LC_ALL='C')
    return env

def sha(raw):return hashlib.sha256(raw).hexdigest()

def execute(command):
    result=subprocess.run(command,env=compiler_environment(),capture_output=True,timeout=20)
    assert result.returncode==0 and not result.stderr and len(result.stdout)<16384,'ORACLE_VERSION_PROBE_FAILED'
    return result.stdout.decode('utf-8').strip()

def describe(name,selected,wanted):
    path=Path(selected).resolve()
    assert path.is_absolute() and path.is_file() and not path.is_symlink() and not getattr(path,'is_junction',lambda:False)()
    assert os.access(path,os.X_OK) and re.fullmatch(r'[A-Za-z0-9_.+-]{1,128}',path.name)
    raw=path.read_bytes();assert 0<len(raw)<=32*1024*1024
    before=sha(raw);banner=execute([str(path),'--version']).splitlines()[0]
    if name=='gcc':
        assert 'gcc' in banner.lower() or 'GNU' in banner,'GNU_GCC_REQUIRED'
        version=execute([str(path),'-dumpfullversion','-dumpversion'])
    else:
        assert banner.startswith('GNU readelf'),'GNU_READELF_REQUIRED'
        found=re.search(r' ([0-9]+\.[0-9]+(?:\.[0-9]+)?)$',banner);assert found,'READELF_VERSION_REQUIRED'
        version=found.group(1)
    assert version==wanted,'ORACLE_VERSION_DIFFERS_FROM_LOCK'
    assert sha(path.read_bytes())==before and path.stat().st_size==len(raw),'ORACLE_CHANGED_DURING_PREPARATION'
    return dict(basename=path.name,bytes=len(raw),sha256=before,version=version,version_text=banner),path

def destination(path):
    assert path.is_absolute() and path.parent.is_dir() and not os.path.lexists(path)
    assert path.parent.resolve()==path.parent and not path.parent.is_symlink() and not getattr(path.parent,'is_junction',lambda:False)()
    assert not path.resolve().is_relative_to(ROOT.resolve())

def prepare(report,gcc=None,readelf=None):
    assert sys.platform in {'win32','linux'},'WINDOWS_OR_LINUX_REQUIRED'
    destination(report)
    lock_raw=(ROOT/'ORACLE-LOCK.json').read_bytes();lock=json.loads(lock_raw)
    assert lock['schema']==1 and lock['gcc_version']=='15.2.0' and lock['readelf_version']=='2.46'
    tools={};paths={}
    if sys.platform=='linux':
        for name,selected in (('gcc',gcc),('readelf',readelf)):
            selected=selected or shutil.which(name);assert selected,'EXISTING_GCC_AND_READELF_REQUIRED'
            tools[name],paths[name]=describe(name,selected,lock[name+'_version'])
    else:assert gcc is None and readelf is None,'LINUX_ORACLE_NOT_SELECTED_ON_WINDOWS'
    value=dict(schema=1,status='PASS',platform=sys.platform,oracle_required=sys.platform=='linux',tools=tools,
        oracle_lock_sha256=sha(lock_raw),preparation_helper_sha256=sha(Path(__file__).read_bytes()),
        application_uses_oracle=False,fixture_binaries_executed=False,binary_reproducibility_claimed=False,global_install_performed=False)
    with report.open('x',encoding='utf-8',newline='\n') as out:out.write(json.dumps(value,indent=2)+'\n')
    return value,paths

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--gcc');parser.add_argument('--readelf')
    parser.add_argument('--github-env',action='store_true')
    args=parser.parse_args();value,paths=prepare(args.report,args.gcc,args.readelf)
    if args.github_env:
        assert os.environ.get('GITHUB_ACTIONS')=='true','GITHUB_ACTION_ENVIRONMENT_REQUIRED'
        target=Path(os.environ['GITHUB_ENV'])
        assert target.is_absolute() and target.is_file() and not target.is_symlink() and target.stat().st_size<32768
        assert target.parent.resolve()==target.parent and not getattr(target,'is_junction',lambda:False)()
        env=dict(OUTLANDS_ELF_ORACLE_REPORT=str(args.report),ELF_REQUIRE_ORACLE='1' if paths else '0')
        env.update({'OUTLANDS_ELF_'+name.upper():str(path) for name,path in paths.items()})
        assert all('\n' not in text and '\r' not in text for text in env.values())
        with target.open('a',encoding='utf-8',newline='\n') as out:
            for key,text in env.items():out.write(key+'='+text+'\n')
    print(json.dumps(value))

if __name__=='__main__':main()
