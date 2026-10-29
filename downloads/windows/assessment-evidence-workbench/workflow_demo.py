"""Original public CLI exercise and independent revision, receipt, export and backup readers."""
import base64,copy,csv,hashlib,io,json,os,re,sqlite3,subprocess,sys
from contextlib import closing
from pathlib import Path
ROOT=Path(__file__).resolve().parent
KIND='assessment'
ID_KEY='assessment_id' if KIND=='assessment' else 'case_id'
ID='sample_assessment' if KIND=='assessment' else 'sample_reliability'
FLAG='--assessment' if KIND=='assessment' else '--case'
FIXTURE='sample-assessment.json' if KIND=='assessment' else 'sample-recording.json'
CHECKS=dict.fromkeys(('quality','privacy','rights','context'),True)
def sha(b):return hashlib.sha256(b).hexdigest()
def encode(v):return json.dumps(v,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def require(v,code):
    if not v:raise ValueError(code)
def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def snapshot(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as con:
        require(con.execute('PRAGMA integrity_check').fetchall()==[('ok',)],'BACKUP_INTEGRITY_FAILED')
        names=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        require(set(names)=={'meta','revisions'},'BACKUP_TABLES_UNEXPECTED')
        return {n:sorted(con.execute('SELECT * FROM '+n).fetchall(),key=repr) for n in names}
def verify_record(row):
    payload={k:row[k] for k in (ID_KEY,'version','parent_sha256','event','document')}
    require(row[ID_KEY]==ID and sha(encode(payload))==row['sha256'] and row['operator_assertions_unverified'] is True,'REVISION_HASH_OR_SCOPE_FAILED')
    if KIND=='assessment':
        require(row['execution_performed'] is False,'ASSESSMENT_EXECUTION_SCOPE_FAILED')
        for item in row['document']['submissions']:
            receipt=item['receipt'];raw=base64.b64decode(receipt['content_base64'],validate=True)
            require(len(raw)==receipt['bytes'] and sha(raw)==receipt['sha256'],'RECEIPT_HASH_FAILED')
    return row
def verify_export(workspace,result,selected,count):
    folder=workspace/result['directory'];manifest=json.loads((folder/'manifest.json').read_bytes());require(manifest==result['manifest'] and manifest['version']==selected['version'] and not manifest['public_release_authorized'],'EXPORT_SCOPE_FAILED')
    require({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}==set(manifest['files'])|{'manifest.json'} and len(manifest['files'])+1==count,'EXPORT_MEMBERS_FAILED')
    for name,row in manifest['files'].items():
        b=(folder/name).read_bytes();require(row==dict(bytes=len(b),sha256=sha(b)),'EXPORT_HASH_FAILED')
    saved=json.loads((folder/('assessment.json' if KIND=='assessment' else 'case.json')).read_bytes());require(saved==selected,'EXPORTED_REVISION_MISMATCH')
    if KIND=='assessment':
        for item in selected['document']['submissions']:require((folder/'receipts'/(item['id']+'.bin')).read_bytes()==base64.b64decode(item['receipt']['content_base64']),'EXPORTED_RECEIPT_MISMATCH')
    else:
        rows=list(csv.DictReader(io.StringIO((folder/'availability.csv').read_text(encoding='utf-8'))));row=next(r for r in rows if r['service_id']=='sample_service');require({k:int(row[k]) for k in ('healthy','degraded','down','unknown','maintenance','planned_off')}==dict(healthy=30,degraded=0,down=25,unknown=25,maintenance=20,planned_off=0),'CSV_COVERAGE_ORACLE_FAILED')
    return tree(folder)
class CLI:
    def __init__(self,workspace,application):self.workspace=workspace;self.app=application;self.count=0;self.requests=0
    def call(self,*args,expected=0,error=None):
        self.count+=1
        bridge='import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name="__main__")'
        cmd=[sys.executable,'-I','-B','-c',bridge,str(self.app),str(self.app/'workbench.py'),'--workspace',str(self.workspace),*map(str,args)]
        p=subprocess.run(cmd,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1'})
        if p.returncode!=expected or p.stderr:
            if self.workspace.exists():(self.workspace/'private-command-failure.log').write_bytes(p.stdout+p.stderr)
            raise ValueError('ORIGINAL_CLI_FAILED_PRIVATE_LOG_RETAINED')
        value=json.loads(p.stdout)
        if error:require(value==dict(error=error),'EXPECTED_REFUSAL_MISSING')
        return value
    def request(self,command,value,expected=0,error=None):
        self.requests+=1;name='inbox/exercise-'+str(self.requests)+'.json'
        with (self.workspace/name).open('xb') as f:f.write(encode(value))
        before=tree(self.workspace);result=self.call(command,'--file',name,expected=expected,error=error)
        if expected:require(tree(self.workspace)==before,'REFUSAL_CHANGED_SAVED_STATE')
        return result
    def show(self,version=None):return verify_record(self.call('show',FLAG,ID,*(['--version',str(version)] if version else [])))
    def act(self,current,command,expected=0,error=None):return self.request('act',{ID_KEY:ID,'expected_sha256':current['sha256'],'command':command},expected,error)
    def review(self,current,checks=CHECKS,expected=0,error=None):return self.request('export',{ID_KEY:ID,'expected_sha256':current['sha256'],'actor':'sample_reviewer','reason':'Fictional private handoff only','checks':checks},expected,error)
def exercise(workspace,application=None):
    workspace=Path(workspace);app=Path(application) if application else ROOT/'application'
    require(workspace.is_absolute() and not workspace.exists() and workspace.parent.is_dir(),'NEW_PRIVATE_EXERCISE_REQUIRED')
    fixture_raw=(app/'examples'/FIXTURE).read_bytes();fixture=json.loads(fixture_raw);e=CLI(workspace,app);e.call('init');require(e.call('list')==({'assessments':[]} if KIND=='assessment' else {'cases':[]}),'EMPTY_INSTANCE_REQUIRED')
    result,latest,exported,old_export=scenario(e,fixture)
    history=e.call('history',FLAG,ID)['versions'];previous=None
    for index,item in enumerate(history,1):
        row=e.show(index);require(row['version']==index and row['parent_sha256']==previous and item['sha256']==row['sha256'] and item['command_sha256']==sha(encode(row['event'])),'HISTORY_CHAIN_ORACLE_FAILED');previous=row['sha256']
    backup=e.call('backup');b=workspace/backup['file'];require(sha(b.read_bytes())==backup['sha256'] and snapshot(b)==snapshot(workspace/'database/workbench.sqlite3'),'BACKUP_ROWS_ORACLE_FAILED')
    before=snapshot(workspace/'database/workbench.sqlite3');require(e.show()==latest and snapshot(workspace/'database/workbench.sqlite3')==before,'REOPEN_CHANGED_STATE')
    require(tree(workspace/exported['directory'])==old_export and (workspace/'inbox'/FIXTURE).read_bytes()==fixture_raw and (app/'examples'/FIXTURE).read_bytes()==fixture_raw,'PRESERVED_BYTES_CHANGED')
    before=tree(workspace);e.call('init',expected=2);require(tree(workspace)==before and not (workspace/'.session-lock').exists(),'EXISTING_INITIALIZATION_CHANGED_STATE')
    return dict(status='PASS',command_checks=e.count,**result,independent_revision_and_receipt_hashes=True,independent_export_members_and_hashes=True,stale_change_refused_without_writes=True,review_refused_without_writes=True,original_inputs_unchanged=True,old_exports_unchanged=True,database_backup_integrity_and_rows=True,state_reopened_without_replay=True,existing_initialization_refused_without_writes=True,operator_assertions_unverified=True,execution_performed=False,network_probed=False,publication_authorized=False,complete_restore_performed=False)

def scenario(e,fixture):
    current=e.request('create',fixture['create']);commands=fixture['commands'];e.act(current,commands[0]);current=e.show();stale=current
    e.act(current,commands[2]);current=e.show();require(current['document']['findings'][0]['state']=='New','NEW_FINDING_REQUIRED')
    invalid=copy.deepcopy(commands[3]);invalid['data']['state']='Resolved';e.act(current,invalid,2,'TRANSITION_REFUSED')
    e.act(stale,commands[3],2,'ASSESSMENT_REVISION_CONFLICT');e.act(current,commands[3]);current=e.show()
    e.act(current,commands[1]);current=e.show();e.act(current,commands[4]);pending=e.show()
    require(pending['document']['findings'][0]['state']=='Retesting' and pending['document']['retests'][0]['review_state']=='pending','MANUAL_RETEST_PENDING_REQUIRED')
    e.act(pending,commands[5]);latest=e.show();require(latest['version']==7 and latest['document']['findings'][0]['state']=='Resolved' and latest['document']['retests'][0]['review_state']=='accept','EXPLICIT_REVIEW_REQUIRED')
    e.review(pending,expected=2,error='ASSESSMENT_REVISION_CONFLICT');e.review(latest,dict.fromkeys(CHECKS,False),2,'EXPORT_REVIEW_REQUIRED')
    exported=e.review(latest);old=verify_export(e.workspace,exported,latest,6);e.call('compare',FLAG,ID,'--left','3','--right','7')
    return dict(versions=7,submissions=2,finding_state='Resolved',manual_retest_review='accept',direct_resolution_refused=True,private_export_files=6),latest,exported,old
