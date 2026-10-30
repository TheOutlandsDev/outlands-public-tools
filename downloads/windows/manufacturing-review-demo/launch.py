"""Run both unchanged fictional exercises with bundled isolated Python and retain private results."""
import argparse,hashlib,json,os,re,struct,subprocess,sys,uuid
from pathlib import Path
from viewer import render

ROOT=Path(__file__).resolve().parent
SOURCE='5ace0cacafe0874fa4db816a11c5cc0cf04089d2'

def require(ok,code):
 if not ok:raise ValueError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode('utf-8')
def fresh(path,raw):
 with path.open('xb') as f:f.write(raw)
def ordinary(path):
 require(not path.is_symlink() and not path.is_junction(),'ORDINARY_PATH_REQUIRED')
 for parent in path.parents:require(not parent.is_symlink() and not parent.is_junction(),'ORDINARY_PARENT_REQUIRED')
 if path.is_file():require(path.stat().st_nlink==1,'ORDINARY_FILE_REQUIRED')
def private_path(path):
 require(path.is_absolute() and '..' not in path.parts and path.resolve()==path and not path.is_relative_to(ROOT),'ABSOLUTE_EXTERNAL_PRIVATE_PATH_REQUIRED')
 require(not str(path).startswith(('\\\\','//')) and ':' not in ''.join(path.parts[1:]),'ORDINARY_LOCAL_PATH_REQUIRED')
 ordinary(path)
def runtime_check():
 require(os.name=='nt' and struct.calcsize('P')==8,'WINDOWS_X64_REQUIRED')
 require(sys.version.split()[0]=='3.14.10' and Path(sys.executable).resolve()==ROOT/'runtime/python.exe','BUNDLED_RUNTIME_REQUIRED')
 require(sys.flags.isolated==1 and sys.flags.no_user_site==1,'ISOLATED_RUNTIME_REQUIRED')
 require(all(Path(p).is_absolute() and Path(p).resolve().is_relative_to(ROOT) for p in sys.path),'EXTERNAL_IMPORT_PATH_REFUSED')
 return dict(runtime='3.14.10',bundled_runtime=True,isolated=True,user_site_disabled=True,external_import_paths=False,executable='runtime/python.exe')
def bundle_check():
 manifest_path=ROOT/'PACKAGE-MANIFEST.json';ordinary(manifest_path)
 require(manifest_path.stat().st_size<1024*1024,'MANIFEST_BOUND')
 manifest=json.loads(manifest_path.read_bytes());require(manifest['source_revision']==SOURCE and manifest['runtime']=='3.14.10','BUNDLE_IDENTITY_MISMATCH')
 seen=set()
 for row in manifest['files']:
  name=row['path'];require(re.fullmatch(r'[A-Za-z0-9_ ./-]+',name) is not None and all(p not in ('','.','..') for p in name.split('/')) and not name.startswith('/'),'MANIFEST_PATH_INVALID')
  require(name not in seen,'DUPLICATE_MANIFEST_MEMBER');seen.add(name);p=ROOT/name;ordinary(p)
  require(p.is_file() and p.stat().st_size==row['bytes'] and sha(p.read_bytes())==row['sha256'],'BUNDLE_FILE_MISMATCH')
 require({p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}==seen|{'PACKAGE-MANIFEST.json'},'BUNDLE_INVENTORY_MISMATCH')
 return manifest,sha(manifest_path.read_bytes())
def run_tree(root):
 result={}
 for p in root.rglob('*'):
  ordinary(p)
  if p.is_file():
   require(p.stat().st_size<=16*1024*1024,'RUN_FILE_BOUND');result[p.relative_to(root).as_posix()]=dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
 require(len(result)<=256,'RUN_INVENTORY_BOUND');return result
def open_run(path):
 private_path(path);require(path.is_dir(),'RUN_DIRECTORY_REQUIRED')
 p=path/'RUN-MANIFEST.json';ordinary(p);require(p.stat().st_size<1024*1024,'RUN_MANIFEST_BOUND')
 manifest=json.loads(p.read_bytes());require(manifest['status']=='PASS' and manifest['source_revision']==SOURCE,'COMPLETED_RUN_REQUIRED')
 actual=run_tree(path);actual.pop('RUN-MANIFEST.json');require(actual==manifest['files'],'SAVED_RUN_CHANGED')
 require('report.html' in actual and 'result.json' in actual,'SAVED_REPORT_REQUIRED')
 return path/'report.html'
def default_workspace():
 base=Path(os.environ.get('LOCALAPPDATA',''))
 require(base.is_absolute() and base.is_dir(),'LOCAL_APP_DATA_REQUIRED');ordinary(base)
 for part in ('Outlands','ManufacturingReviewDemo','runs'):
  base=base/part;ordinary(base)
  if not base.exists():base.mkdir()
  require(base.is_dir(),'PRIVATE_RUN_PARENT_REQUIRED')
 return base/('run-'+uuid.uuid4().hex)
def validate_receipts(folder,value,number,reviews):
 require(value['status']=='PASS' and value['operator_review']=='REQUIRED' and value['command_checks']==number and value['expected_review_outcomes']==reviews,'EXERCISE_ORACLE_FAILED')
 require(len(value['receipts'])==number and sum(r['exit_code']==1 for r in value['receipts'])==reviews,'EXERCISE_ACCOUNTING_FAILED')
 for row in value['receipts']:
  require(re.fullmatch('[a-z0-9-]+',row['case']) is not None and row['exit_code'] in (0,1),'RECEIPT_FORMAT_CHANGED')
  for kind in ('input','report'):
   p=folder/(row['case']+'-'+kind+'.json');ordinary(p);require(sha(p.read_bytes())==row[kind+'_sha256'],'RECEIPT_HASH_MISMATCH')
 require(value['original_inputs_unchanged'] and value['report_hashes_recomputed'],'PRESERVATION_ORACLE_FAILED')
 require(value['execution_authorized'] is False and value['publication_authorized'] is False,'AUTHORITY_BOUNDARY_CHANGED')
 require(json.loads((folder/'observed-results.json').read_bytes())==value,'RETAINED_SUMMARY_MISMATCH')
def run(path,runtime,manifest,manifest_pin):
 private_path(path);require(not path.exists() and path.parent.is_dir(),'NEW_PRIVATE_RUN_REQUIRED');path.mkdir(mode=0o700)
 try:
  env={k:v for k,v in os.environ.items() if k not in ('GH_TOKEN','GITHUB_TOKEN','OUTLANDS_CATALOG_READ_TOKEN')}
  outcomes={}
  for name,script,number,reviews in [('capacity','manufacturing_review.py',12,4),('material-quality','material_quality_review.py',24,13)]:
   result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'application/workshops'/script),'--workspace',str(path/name)],capture_output=True,env=env,timeout=240)
   fresh(path/(name+'-private.log'),result.stdout+result.stderr)
   require(result.returncode==0 and not result.stderr,'EXERCISE_FAILED_PRIVATE_STATE_RETAINED')
   value=json.loads(result.stdout);validate_receipts(path/name,value,number,reviews);outcomes[name]=value
  capacity=outcomes['capacity'];material=outcomes['material-quality']
  require([capacity[k] for k in ('eligible_before','eligible_after','peak_units_before','peak_units_after','total_closing')]==[2,3,3,2,21],'CAPACITY_ARITHMETIC_FAILED')
  require(capacity['duration_ticks']==dict(elapsed_ticks=12,active_ticks=9,hold_ticks=3,hold_count=1),'DURATION_ARITHMETIC_FAILED')
  require([material[k] for k in ('kits','motor_requirement','filter_requirement','overreserved_motor_units','filter_shortage_before','initial_within_limits','later_within_limits','inspection_attempts','rework_events')]==[4,4,8,1,1,2,3,5,1],'MATERIAL_ORACLE_FAILED')
  require(material['final_counts']==dict(closed_cohort=True,cohort=4,first_pass_good=2,good=3,pending=0,reworked_good=1,scrap=1),'COHORT_ORACLE_FAILED')
  require(material['exact_fractions']==dict(eventual_yield='3/4',first_pass_yield='1/2',pending_fraction='0/1',scrap_fraction='1/4'),'EXACT_FRACTION_ORACLE_FAILED')
  mapping=path/'material-quality/authored-mapping.json';require(sha(mapping.read_bytes())==material['mapping_sha256'],'MAPPING_HASH_MISMATCH')
  summary=dict(schema=1,status='PASS',mode='FICTIONAL_MANUFACTURING_REVIEW_DEMO',version='0.1.0',command_checks=36,expected_review_outcomes=17,
               operator_review='REQUIRED',source_revision=SOURCE,packaging_revision=manifest['packaging_revision'],bundle_manifest_sha256=manifest_pin,
               runtime=runtime,exercises=outcomes,network_required=False,physical_operations_performed=False,publication_authorized=False)
  fresh(path/'result.json',encoded(summary));fresh(path/'report.html',render(summary).encode('utf-8'))
  fresh(path/'RUN-MANIFEST.json',encoded(dict(schema=1,status='PASS',source_revision=SOURCE,files=run_tree(path))))
  require(open_run(path)==path/'report.html','SAVED_REPORT_VERIFICATION_FAILED')
  return summary,path/'report.html'
 except (ValueError,OSError,subprocess.SubprocessError):
  fresh(path/'FAILED.txt',b'Run incomplete. Keep all private files and use a new directory after reviewing the failure.\n')
  raise

def main():
 p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group();group.add_argument('--workspace',type=Path);group.add_argument('--open',type=Path);group.add_argument('--check',action='store_true');p.add_argument('--no-browser',action='store_true');a=p.parse_args()
 try:
  runtime=runtime_check();manifest,pin=bundle_check()
  if a.check:print(json.dumps(dict(status='PASS',**runtime,source_revision=SOURCE,bundle_files=len(manifest['files'])+1)));return 0
  if a.open:report=open_run(a.open);summary=json.loads((a.open/'result.json').read_bytes())
  else:summary,report=run(a.workspace if a.workspace is not None else default_workspace(),runtime,manifest,pin)
  print(json.dumps(dict(status=summary['status'],command_checks=36,expected_review_outcomes=17,operator_review='REQUIRED',runtime='3.14.10',report=str(report))))
  if not a.no_browser:
   try:os.startfile(report)
   except OSError:print('The report is saved. Open report.html from the private run directory.')
  return 0
 except (ValueError,OSError,subprocess.SubprocessError,KeyError) as error:
  print(json.dumps(dict(error=str(error) if isinstance(error,ValueError) and re.fullmatch('[A-Z_]+',str(error)) else 'DEMO_FAILED_PRIVATE_STATE_RETAINED')));return 2

if __name__=='__main__':raise SystemExit(main())
