"""Fresh source install, original/new tests and actual loopback HTTP."""
import argparse,hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path

CHILD=r'''
import hashlib,importlib.metadata,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);work=pathlib.Path(sys.argv[2]);report=pathlib.Path(sys.argv[3])
import app,app.main,app.config,app.logging_config,pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
base=pathlib.Path(sys.prefix).resolve();assert sys.prefix!=sys.base_prefix
assert pathlib.Path(app.__file__).resolve().is_relative_to(base)
baseline=json.loads((root/'BASELINE.json').read_bytes())
for name,pin in baseline['source_sha256'].items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pin
 if name.startswith('app/'):
  installed=pathlib.Path(app.__file__).resolve().parent/name.split('/',1)[1]
  assert hashlib.sha256(installed.read_bytes()).hexdigest()==pin
expected={}
for line in (root/'requirements-validation.lock').read_text().splitlines():
 if not line or line[0].isspace() or line.startswith('#'):continue
 requirement=Requirement(line.rstrip(' \\'))
 if requirement.marker is None or requirement.marker.evaluate():expected[canonicalize_name(requirement.name)]=str(requirement.specifier).removeprefix('==')
versions={canonicalize_name(d.metadata['Name']):d.version for d in importlib.metadata.distributions()}
assert all(versions.get(name)==version for name,version in expected.items())
assert set(versions)==set(expected)|{'pip','python-control-layer'} and versions['python-control-layer']=='0.1.0'
class Recorder:
 def __init__(self):self.selected=[];self.started=[];self.passed=[];self.skips=[];self.failures=[];self.errors=[];self.warnings=[]
 def pytest_collection_finish(self,session):self.selected=[item.nodeid for item in session.items]
 def pytest_runtest_logstart(self,nodeid,location):self.started.append(nodeid)
 def pytest_runtest_logreport(self,report):
  if report.skipped:self.skips.append(report.nodeid)
  if report.failed:(self.failures if report.when=='call' else self.errors).append(report.nodeid)
  if report.when=='call' and report.passed:self.passed.append(report.nodeid)
 def pytest_warning_recorded(self,warning_message,when,nodeid,location):self.warnings.append(dict(category=warning_message.category.__name__,message=str(warning_message.message)))
recorder=Recorder()
result=pytest.main(['-q','-c',str(root/'pyproject.toml'),'-o','pythonpath=','--import-mode=importlib','-p','no:cacheprovider','--basetemp',str(work/'pytest'),str(root/'tests')],plugins=[recorder])
assert result==0 and len(recorder.selected)==len(recorder.started)==len(recorder.passed)==16
assert set(recorder.selected)==set(recorder.started)==set(recorder.passed) and not recorder.skips and not recorder.failures and not recorder.errors
assert sum('/test_health.py::' in value or value.startswith('tests/test_health.py::') for value in recorder.selected)==2
assert len(recorder.warnings)==1 and recorder.warnings[0]['category']=='StarletteDeprecationWarning'
assert recorder.warnings[0]['message']=='Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.'
value=dict(status='PASS',profile='fresh-installed-source',python=sys.version.split()[0],platform=sys.platform,tests=16,passed=16,skipped=0,failures=0,errors=0,original_tests=2,added_tests=14,selected_test_ids=sorted(recorder.selected),started_test_ids=sorted(recorder.started),successful_test_ids=sorted(recorder.passed),warnings=recorder.warnings,installed_package_verified=True,installed_app_raw_bytes_verified=True,original_source_sha256=baseline['source_sha256'],dependencies=versions,locked_dependencies_verified=True,source_only=True,actual_database_operations_verified=False,external_dependency_readiness_verified=False,production_workflows_verified=False)
report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
'''

def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(python,args,cwd,env,log):
    result=subprocess.run([str(python),'-I','-B',*map(str,args)],cwd=cwd,env=env,capture_output=True,timeout=600)
    with log.open('ab') as handle:handle.write(result.stdout+result.stderr)
    assert result.returncode==0,'OWNED_QUALIFICATION_STEP_FAILED'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('packages','python-root','python-receipt','workspace','report'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--reference-build',type=Path);a=p.parse_args()
    assert not a.workspace.exists() and a.workspace.parent.is_dir() and not a.report.exists()
    build=json.loads((a.packages/'build-manifest.json').read_bytes());archive=a.packages/build['filename']
    assert build['package']=='python-control-layer' and archive.stat().st_size==build['bytes'] and sha(archive.read_bytes())==build['sha256']
    if a.reference_build:
        for name in (build['filename'],'build-manifest.json','SHA256SUMS.txt'):assert (a.packages/name).read_bytes()==(a.reference_build/name).read_bytes()
    a.workspace.mkdir();prefix='python-control-layer-0.1.0/'
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();assert len(names)==len(set(names))==build['files'] and z.testzip() is None
        assert all(n.startswith(prefix) and '..' not in n.split('/') and '\\' not in n and ':' not in n for n in names)
        z.extractall(a.workspace)
    source=(a.workspace/prefix).resolve();manifest=json.loads((source/'SOURCE-MANIFEST.json').read_bytes())
    before={row['path']:sha((source/row['path']).read_bytes()) for row in manifest['files']}
    assert set(names)=={prefix+name for name in before}|{prefix+'SOURCE-MANIFEST.json'}
    assert all(before[row['path']]==row['sha256'] and (source/row['path']).stat().st_size==row['bytes'] for row in manifest['files'])
    prep=json.loads(a.python_receipt.read_bytes());executable=a.python_root/prep['executable_relative'];lock=json.loads((source/'PYTHON-LOCK.json').read_bytes())
    assert prep['status']=='PASS' and prep['python_version']=='3.12.16' and prep['archive']==lock['python_archives'][sys.platform]['3.12']
    assert prep['python_lock_sha256']==sha((source/'PYTHON-LOCK.json').read_bytes()) and prep['executable_sha256']==sha(executable.read_bytes())
    assert prep['archive_sha256_verified'] is prep['actual_interpreter_verified'] is True
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','PIP_','LD_','DYLD_'))}
    for key in ('APP_NAME','APP_ENVIRONMENT','APP_VERSION','LOG_LEVEL','CONTROL_DB_URL','DATA_ROOT','MANIFEST_ROOT','STAGING_ROOT','RESULTS_ROOT'):env.pop(key,None)
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',NO_COLOR='1')
    work=a.workspace/'work';work.mkdir();venv=a.workspace/'venv';log=a.workspace/'qualification-private.log'
    run(executable,['-m','venv',venv],work,env,log)
    python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    run(python,['-m','pip','--isolated','install','--disable-pip-version-check','--no-cache-dir','--index-url','https://pypi.org/simple','--require-hashes','--only-binary=:all:','-r',source/'requirements-validation.lock'],work,env,log)
    run(python,['-m','pip','--isolated','install','--disable-pip-version-check','--no-deps','--no-build-isolation',source],work,env,log)
    run(python,['-m','pip','check'],work,env,log)
    observed=work/'tests.json';run(python,['-c',CHILD,source,work,observed],work,env,log)
    smoke=work/'http.json';run(python,[source/'packaging/smoke_http.py','--workspace',work/'http','--report',smoke],work,env,log)
    value=json.loads(observed.read_bytes());value.update(schema=1,package='python-control-layer',version='0.1.0',source_revision=build['source_revision'],zip_sha256=build['sha256'],zip_bytes=build['bytes'],source_files=len(before),archive_members=len(names),python_preparation=prep,reference_rebuild_claimed=a.reference_build is not None,fresh_extraction=True,loopback_http=json.loads(smoke.read_bytes()),pip_check_passed=True)
    assert before=={name:sha((source/name).read_bytes()) for name in before}
    a.report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(value))
if __name__=='__main__':main()
