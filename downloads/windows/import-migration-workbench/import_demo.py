"""New-only fictional import exercise through the unchanged application CLI."""
from decimal import Decimal
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
APP=ROOT/'application'
CHECKS=dict(quality=True,privacy=True,rights=True,context=True)

def require(ok,code):
    if not ok:raise ValueError(code)


def hashes(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


class Exercise:
    def __init__(self,name,workspace):
        self.source=APP;self.workspace=workspace;self.calls=0;self.requests=0
        self.call('init')
    def call(self,*args,error=None):
        self.calls+=1
        result=subprocess.run([sys.executable,'-B',str(self.source/'workbench.py'),'--workspace',str(self.workspace),*map(str,args)],cwd=self.source,capture_output=True,text=True,encoding='utf-8',timeout=90)
        require(result.returncode==(2 if error else 0),'EXERCISE_COMMAND_FAILED')
        value=json.loads(result.stdout)
        if error:require(value==dict(error=error),'EXPECTED_REFUSAL_MISSING')
        return value
    def mutate(self,command,request,error=None):
        self.requests+=1;head=self.call('overview')['head'];name='inbox/toolkit-request-'+str(self.requests)+'.json'
        body=dict(expected_head=head,actor='sample_operator',reason='Fictional Windows import exercise',request=request)
        with (self.workspace/name).open('x',encoding='utf-8') as f:json.dump(body,f)
        value=self.call(command,'--file',name,error=error)
        return value if error else value['job']['result']


def imports(workspace):
    e=Exercise('import-migration-workbench',workspace)
    selected=['orders.csv','supplement.jsonl','conflicts.jsonl','contract.json']
    before={n:(workspace/'inbox'/n).read_bytes() for n in selected}
    contract=json.loads(before['contract.json']);sources=[dict(path='inbox/orders.csv',format='csv'),dict(path='inbox/supplement.jsonl',format='jsonl')]
    plan=e.mutate('plan',dict(sources=sources,contract=contract));s=plan['summary']
    require([s[k] for k in ('input_rows','accepted_rows','duplicate_rows','rejected_rows','conflict_rows')]==[7,3,2,2,0],'IMPORT_PREVIEW_ORACLE_FAILED')
    request=dict(plan_id=plan['plan_id'],plan_sha256=plan['plan_sha256'],accept_rejections=False,checks=CHECKS)
    e.mutate('import',request,error='REJECTED_ROWS_REVIEW_REQUIRED')
    require(not list((workspace/'stores').iterdir()),'REFUSED_IMPORT_CREATED_STORE')
    imported=e.mutate('import',dict(request,accept_rejections=True));store=workspace/imported['target'];db=store/'data.sqlite3'
    with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as con:
        con.execute('PRAGMA query_only=ON')
        records=[json.loads(row[0]) for row in con.execute('SELECT data_json FROM records ORDER BY record_id')]
        counts=[con.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('records','provenance','rejected')]
    require(counts==[3,5,2],'SQLITE_READBACK_COUNTS_FAILED')
    expected=[('sample-a',3,'12.50',True,'alpha'),('sample-b',7,'2.00',False,'=SUM(1)'),('sample-c',0,'0',True,None)]
    for row,(key,quantity,amount,active,note) in zip(records,expected):
        require(row['id']==key and row['quantity']==quantity and Decimal(row['amount'])==Decimal(amount) and row['active'] is active and row['note']==note,'SQLITE_VALUE_ORACLE_FAILED')
    e.call('inspect-import','--id',imported['import_id']);saved=hashes(store)
    e.mutate('import',dict(request,accept_rejections=True),error='EXACT_PLAN_ALREADY_IMPORTED')
    conflict=e.mutate('plan',dict(sources=[sources[0],dict(path='inbox/conflicts.jsonl',format='jsonl')],contract=contract))
    require(conflict['summary']['conflict_rows']==3,'CONFLICT_ORACLE_FAILED')
    e.mutate('import',dict(request,plan_id=conflict['plan_id'],plan_sha256=conflict['plan_sha256'],accept_rejections=True),error='CONFLICTING_KEYS_REQUIRE_NEW_PLAN')
    require(hashes(store)==saved and len(list((workspace/'stores').iterdir()))==1,'EXISTING_STORE_CHANGED')
    state=e.call('overview');require(len(state['imports'])==1 and state['unfinished_jobs']==0,'IMPORT_REOPEN_FAILED')
    require(all((workspace/'inbox'/n).read_bytes()==b for n,b in before.items()),'INPUT_CHANGED')
    return dict(status='PASS',input_rows=7,accepted_records=3,duplicate_rows=2,rejected_rows=2,provenance_rows=5,
                quantities=[3,7,0],rejection_without_review='REJECTED_ROWS_REVIEW_REQUIRED',repeat_refused=True,
                conflicting_rows=3,conflict_refused=True,sqlite_independently_read=True,input_bytes_unchanged=True,
                existing_store_unchanged=True,registered_stores=1,command_checks=e.calls)


def exercise(workspace):
    if not workspace.is_absolute() or '..' in workspace.parts or workspace.exists() or not workspace.parent.is_dir():
        raise ValueError('EXERCISE_REQUIRES_NEW_ABSOLUTE_INSTANCE')
    if workspace.resolve().is_relative_to(ROOT):raise ValueError('EXTERNAL_INSTANCE_REQUIRED')
    return dict(mode='FICTIONAL_IMPORT_EXERCISE',**imports(workspace))
