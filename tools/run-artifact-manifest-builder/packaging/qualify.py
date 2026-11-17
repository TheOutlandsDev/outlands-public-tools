"""Qualify a source ZIP in a fresh, dependency-free application environment."""
import argparse,hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path

CHILD=r'''
import _elementtree,ast,hashlib,importlib.metadata,io,json,os,pathlib,pyexpat,sys,unittest,xml.etree.ElementTree as ET,zlib
root=pathlib.Path(sys.argv[1]);sys.path[:0]=[str(root),str(root/'tests')]
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
import artifacts,run_core,toolkit,native_windows,source_check
for module in (artifacts,run_core,toolkit,native_windows,source_check):assert pathlib.Path(module.__file__).resolve().parent==root
assert ET.XMLParser is _elementtree.XMLParser and ET.TreeBuilder is _elementtree.TreeBuilder
source_check.verify()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def identities():
 return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
before=identities();baseline=json.loads((root/'BASELINE.json').read_bytes())
assert baseline['original_tests']==44
original=[];copied=[]
for p in sorted((root/'tests').glob('test_*.py')):
 ids=[p.stem+'.'+c.name+'.'+n.name for c in ast.parse(p.read_bytes()).body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
 (copied if p.name=='test_copied_cli.py' else original).extend(ids)
assert len(original)==44 and len(copied)==20
class Result(unittest.TextTestResult):
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.started=[];self.succeeded=[]
 def startTest(self,test):self.started.append(test.id());super().startTest(test)
 def addSuccess(self,test):self.succeeded.append(test.id());super().addSuccess(test)
suite=unittest.defaultTestLoader.discover(str(root/'tests'))
assert suite.countTestCases()==64
result=unittest.TextTestRunner(stream=io.StringIO(),verbosity=2,resultclass=Result).run(suite)
expected=('test_boundaries.Files.test_posix_leaf_symlink_refused','POSIX-only leaf symlink fixture') if os.name=='nt' else ('test_boundaries.Files.test_windows_ambiguous_paths_refused','Windows-only path grammar fixtures')
skips=sorted((test.id(),reason) for test,reason in result.skipped)
ok=result.wasSuccessful() and skips==[expected] and set(result.started)==set(original+copied) and len(result.started)==64 and len(result.succeeded)==63
assert identities()==before and not list(root.rglob('__pycache__'))
facts=dict(python=sys.version.split()[0],platform=sys.platform,base_executable_sha256=sha(pathlib.Path(sys._base_executable).resolve().read_bytes()),distributions=0,pip_in_application=False,C_xml_bindings_verified=ET.XMLParser is _elementtree.XMLParser and ET.TreeBuilder is _elementtree.TreeBuilder,expat=pyexpat.EXPAT_VERSION,zlib_compile=zlib.ZLIB_VERSION,zlib_runtime=zlib.ZLIB_RUNTIME_VERSION)
value=dict(status='PASS' if ok else 'FAIL',tests=result.testsRun,passed=len(result.succeeded),skipped=len(skips),failures=len(result.failures),errors=len(result.errors),selected_test_ids=sorted(original+copied),started_test_ids=sorted(result.started),successful_test_ids=sorted(result.succeeded),skips=[dict(test=t,reason=r) for t,r in skips],failed_test_ids=[t.id() for t,_ in result.failures+result.errors],original_tests=44,copied_cli_tests=20,original_test_bytes_preserved=True,runtime_source_sha256={n:before[n] for n in ('artifacts.py','run_core.py','toolkit.py','native_windows.py')},source_before_after_unchanged=True,actual_manifest_hashes_checked=True,artifact_code_executed=False,content_privacy_verified=False,source_authority_verified=False,target_changes_performed=False,interpreter=facts)
pathlib.Path(sys.argv[2]).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
if not ok:
 for t,trace in result.failures+result.errors:print(t.id()+'\n'+trace,file=sys.stderr)
raise SystemExit(0 if ok else 1)
'''

def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('packages','python-root','python-receipt','workspace','report'):p.add_argument('--'+name,required=True,type=Path)
 p.add_argument('--reference-build',type=Path)
 a=p.parse_args();assert not a.workspace.exists() and a.workspace.parent.is_dir() and not a.report.exists()
 packages=a.packages;build=json.loads((packages/'build-manifest.json').read_bytes());archive=packages/build['filename'];raw=archive.read_bytes()
 assert sha(raw)==build['sha256'] and len(raw)==build['bytes'] and build['package']=='run-artifact-manifest-builder'
 if a.reference_build:
  for name in (build['filename'],'build-manifest.json','SHA256SUMS.txt'):assert (packages/name).read_bytes()==(a.reference_build/name).read_bytes(),'REFERENCE_REBUILD_DIFFERS'
 prep=json.loads(a.python_receipt.read_bytes());lock=json.loads((Path(__file__).parents[1]/'PYTHON-LOCK.json').read_bytes())
 executable=a.python_root/prep['executable_relative']
 assert executable.is_file()
 a.workspace.mkdir();app=a.workspace/'source'
 with zipfile.ZipFile(archive) as z:
  names=z.namelist();prefix='run-artifact-manifest-builder-0.1.0/'
  assert len(names)==len(set(names))==build['files'] and z.testzip() is None
  assert all(n.startswith(prefix) and '..' not in n.split('/') and '\\' not in n and ':' not in n for n in names)
  z.extractall(a.workspace);app=a.workspace/prefix
 manifest=json.loads((app/'SOURCE-MANIFEST.json').read_bytes())
 assert len(manifest['files'])+1==len(names)
 for row in manifest['files']:assert (app/row['path']).stat().st_size==row['bytes'] and sha((app/row['path']).read_bytes())==row['sha256']
 venv=a.workspace/'venv';subprocess.run([str(executable),'-I','-B','-m','venv','--without-pip',str(venv)],check=True)
 python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
 env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','PIP_'))}
 fixtures=a.workspace/'fixtures';fixtures.mkdir()
 env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',OUTLANDS_INTAKE_REQUIRE_LINKS='1',TEMP=str(fixtures),TMP=str(fixtures),TMPDIR=str(fixtures))
 child_report=a.workspace/'observed.json'
 done=subprocess.run([str(python),'-I','-B','-c',CHILD,str(app.resolve()),str(child_report)],cwd=app,env=env)
 value=json.loads(child_report.read_bytes());assert done.returncode==0 and value['status']=='PASS'
 version=value['interpreter']['python'];assert version in lock['python_versions'].values()
 expected=lock['python_archives'][sys.platform][version.rsplit('.',1)[0]]
 # Preparation receipts bind the whole SDK archive and actual interpreter.
 assert prep['status']=='PASS' and prep['python_version']==version and prep['archive']==expected
 assert prep['python_lock_sha256']==sha((app/'PYTHON-LOCK.json').read_bytes())
 assert prep['actual_interpreter_verified'] is prep['archive_sha256_verified'] is True
 assert value['interpreter']['base_executable_sha256']==prep['executable_sha256']==sha(executable.read_bytes())
 assert value['interpreter']['C_xml_bindings_verified'] is True
 value.update(schema=1,package=build['package'],version='0.1.0',source_revision=build['source_revision'],zip_sha256=build['sha256'],zip_bytes=build['bytes'],archive_members=len(names),source_files=len(manifest['files']),fresh_extraction=True,python_preparation=prep,python_lock_sha256=sha((app/'PYTHON-LOCK.json').read_bytes()),reference_rebuild_claimed=a.reference_build is not None)
 a.report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(value))
if __name__=='__main__':main()
