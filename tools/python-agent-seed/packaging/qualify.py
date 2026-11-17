"""Validate copied kit source using a new dependency-free project interpreter."""
import argparse,hashlib,importlib.metadata,json,os,subprocess,sys,zipfile
from pathlib import Path
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
    workspace.mkdir();source=workspace/'python-agent-seed-0.2.0'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==build['files']
        for info in z.infolist():
            parts=info.filename.split('/');assert parts[0]==source.name and all(p not in ('','..','.') for p in parts) and '\\' not in info.filename
            assert not info.is_dir() and info.file_size<1048576 and info.date_time==(1980,1,1,0,0,0)
        z.extractall(workspace)
    inventory=json.loads((source/'SOURCE-MANIFEST.json').read_bytes());assert len(inventory['files'])+1==build['files']
    assert {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}=={r['path'] for r in inventory['files']}|{'SOURCE-MANIFEST.json'}
    for row in inventory['files']:
        raw=(source/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','PIP_','LD_','DYLD_'))}
    env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_COLORS='0',NO_COLOR='1',PYTHONPYCACHEPREFIX=str(workspace/'pycache'))
    def run(args,cwd=workspace):
        r=subprocess.run(list(map(str,args)),cwd=cwd,env=env,capture_output=True,timeout=600)
        with (workspace/'qualification-private.log').open('ab') as stream:stream.write(r.stdout+r.stderr)
        assert r.returncode==0,'OWNED_STEP_FAILED_SEE_PRIVATE_LOG';return r.stdout.decode('utf-8')
    run([sys.executable,'-I','-B','-m','venv','--without-pip',workspace/'venv'])
    py=workspace/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    distributions=json.loads(run([py,'-I','-B','-c',"import importlib.metadata,json;print(json.dumps({d.metadata['Name']:d.version for d in importlib.metadata.distributions()}))"]))
    assert distributions=={},'DEPENDENCY_FREE_VENV_REQUIRED'
    run([py,'-I','-B',source/'run_checks.py','--report',workspace/'tests.json'])
    tests=json.loads((workspace/'tests.json').read_bytes())
    assert tests['status']=='PASS' and tests['positive_methods']==tests['positive_passed']==44 and tests['positive_failures']==tests['positive_errors']==tests['skipped']==0
    assert tests['release']['tests']==tests['release']['passed']==13 and tests['release']['warnings']==[]
    k=tests['kit'];assert k['examples']['passed']==8 and sum(v['passed'] for v in k['references'])==23 and k['starter_outcomes_match'] is True
    assert (k['starter_declared_methods'],k['starter_actual_methods'],k['starter_framework_entries'],k['starter_passed'],k['starter_failures'],k['starter_errors'],k['starter_import_failures'])==(23,13,15,1,4,10,2)
    for v in [k['examples'],*k['references'],*k['starters']]:assert v['warnings']==[] and v['unreviewed_runtime_attempts']==[] and v['audit_canaries_refused']==3
    prepared=json.loads(run([py,'-I','-B',source/'kit.py','prepare','--task','eval_001_pathlib_json_loader','--out',workspace/'private-exercise']))
    assert prepared['files']==5 and prepared['executed_code'] is False and prepared['originals_changed'] is False
    for row in inventory['files']:assert sha((source/row['path']).read_bytes())==row['sha256']
    value=dict(schema=1,status='PASS',package='python-agent-seed',version='0.2.0',platform=sys.platform,python=sys.version.split()[0],source_revision=build['source_revision'],zip_sha256=build['sha256'],zip_bytes=build['bytes'],source_files=len(inventory['files']),archive_members=build['files'],source_manifest_sha256=sha((source/'SOURCE-MANIFEST.json').read_bytes()),fresh_venv=True,dependency_distributions={},runtime_dependencies=0,extracted_source=True,original_files_unchanged=True,python_sdk=sdk,tests=tests,independent_rebuild_verified=reference is not None,cli_outside_source_directory=True,prepared_exercise_verified=True,model_or_training_performed=False,third_party_content_fetched=False)
    report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n');print('SEED_QUALIFICATION '+json.dumps(value))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('packages','workspace','report','python-receipt'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--reference-build',type=Path);a=p.parse_args();qualify(a.packages,a.workspace,a.report,a.python_receipt,a.reference_build)
