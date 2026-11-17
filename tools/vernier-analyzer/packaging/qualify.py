"""Validate the downloaded source in a new hash-locked project environment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()

def qualify(packages,workspace,report,receipt,reference=None):
    assert __debug__ and workspace.is_absolute() and not workspace.exists() and workspace.parent.is_dir()
    assert report.is_absolute() and not report.exists() and report.parent.is_dir()
    build=json.loads((packages/'build-manifest.json').read_bytes());archive=packages/build['filename']
    assert archive.stat().st_size==build['bytes'] and sha(archive.read_bytes())==build['sha256']
    if reference:
        assert archive.read_bytes()==(reference/archive.name).read_bytes()
        assert (packages/'build-manifest.json').read_bytes()==(reference/'build-manifest.json').read_bytes()
    sdk=json.loads(receipt.read_bytes());lock_raw=(ROOT/'PYTHON-LOCK.json').read_bytes();lock=json.loads(lock_raw)
    assert sdk['status']=='PASS' and sdk['python_version']==sys.version.split()[0] and sdk['platform']==sys.platform
    assert sdk['python_lock_sha256']==sha(lock_raw) and sdk['preparation_helper_sha256']==sha((ROOT/'packaging/prepare_python.py').read_bytes())
    assert sdk['archive']==lock['python_archives'][sys.platform]['.'.join(map(str,sys.version_info[:2]))]
    assert sdk['executable_sha256']==sha(Path(sys._base_executable).read_bytes())
    workspace.mkdir();source=workspace/'vernier-analyzer-0.1.0'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==build['files']
        for info in z.infolist():
            parts=info.filename.split('/');assert parts[0]==source.name and all(p not in ('','..','.') for p in parts) and '\\' not in info.filename
            assert not info.is_dir() and info.file_size<1048576 and info.date_time==(1980,1,1,0,0,0)
        z.extractall(workspace)
    inventory=json.loads((source/'SOURCE-MANIFEST.json').read_bytes())
    assert len(inventory['files'])+1==build['files']
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}=={r['path'] for r in inventory['files']}|{'SOURCE-MANIFEST.json'}
    for row in inventory['files']:
        raw=(source/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','PIP_','LD_','DYLD_','MPL'))}
    env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg',MPLCONFIGDIR=str(workspace/'mpl-cache'),PYTHONPYCACHEPREFIX=str(workspace/'pycache'))
    def run(args,cwd=workspace):
        r=subprocess.run(list(map(str,args)),cwd=cwd,env=env,capture_output=True,timeout=600)
        with (workspace/'qualification-private.log').open('ab') as stream:stream.write(r.stdout+r.stderr)
        assert r.returncode==0,'OWNED_STEP_FAILED_SEE_PRIVATE_LOG'
        return r.stdout.decode('utf-8')
    run([sys.executable,'-I','-B','-m','venv',workspace/'venv'])
    py=workspace/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    run([py,'-I','-B','-m','pip','install','--disable-pip-version-check','--require-hashes','--only-binary=:all:','-r',source/'requirements.lock'])
    run([py,'-I','-B','-m','pip','check'])
    distributions=json.loads(run([py,'-I','-B','-c',"import importlib.metadata,json;print(json.dumps({d.metadata['Name'].lower():d.version for d in importlib.metadata.distributions()}))"]))
    expected={line.split('==')[0]:line.split('==')[1].split()[0] for line in (source/'requirements.lock').read_text().splitlines() if '==' in line and not line.startswith(' ')}
    assert {k:v for k,v in distributions.items() if k not in {'pip','setuptools'}}==expected
    output=run([py,'-B',source/'run_checks.py','--report',workspace/'tests.json'])
    tests=json.loads((workspace/'tests.json').read_bytes())
    assert tests['status']=='PASS' and tests['tests']==tests['executed']==tests['passed']==len(set(tests['test_ids']))==17
    assert tests['skipped']==tests['failures']==tests['errors']==0 and tests['warnings']==[]
    run([py,'-B',source/'synthetic.py','--out',workspace/'invented'])
    result=json.loads(run([py,'-B',source/'vernier.py',workspace/'invented/positive.png']))
    assert result['quality_approved'] is False and abs(result['results']['delta_verniers']-.1)<.002
    for row in inventory['files']:assert sha((source/row['path']).read_bytes())==row['sha256']
    value=dict(schema=1,status='PASS',package='vernier-analyzer',version='0.1.0',platform=sys.platform,python=sys.version.split()[0],source_revision=build['source_revision'],zip_sha256=build['sha256'],zip_bytes=build['bytes'],source_files=len(inventory['files']),archive_members=build['files'],source_manifest_sha256=sha((source/'SOURCE-MANIFEST.json').read_bytes()),fresh_venv=True,extracted_source=True,original_files_unchanged=True,pip_check_passed=True,exact_dependencies=expected,python_sdk=sdk,tests=tests,independent_rebuild_verified=reference is not None,cli_outside_source_directory=True,synthetic_only=True,calibration_verified=False,interactive_file_picker_verified=False)
    report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('VERNIER_QUALIFICATION '+json.dumps(value))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('packages','workspace','report','python-receipt'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--reference-build',type=Path);a=p.parse_args()
    qualify(a.packages,a.workspace,a.report,a.python_receipt,a.reference_build)
