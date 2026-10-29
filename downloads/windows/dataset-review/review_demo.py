"""Original CLI exercise and independent fictional store/export verification."""
from contextlib import closing
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def fixture_ids(application):
    raw=(application/'examples/sample-records.jsonl').read_bytes();rows=[json.loads(line) for line in raw.decode().splitlines() if line.strip()];assert len(rows)==5
    ids=[sha(encode(dict(text=row['text'].replace('\r\n','\n').strip()))) for row in rows];assert len(set(ids))==4 and ids[1]==ids[2]
    return dict(raw=raw,rows=rows,ids=ids,train=ids[0],duplicate=ids[1],linked=ids[3],validation=ids[4])

def logical(path):
    columns={'groups':('id','split'),'aliases':('id','target'),'records':('id','group_id','body','status','checks'),'provenance':('source_sha256','source_row','record_id'),'reviews':('record_id','decision','actor','note','checks','created_utc')}
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as con:
        assert con.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
        value={table:[dict(zip(names,row)) for row in con.execute('SELECT '+','.join(names)+' FROM '+table+' ORDER BY '+','.join(names))] for table,names in columns.items()}
    return value,sha(encode(value))

def verify_store(workspace,fixture,approved=False):
    value,head=logical(workspace/'database/review.sqlite3');records={row['id']:row for row in value['records']};assert set(records)==set(fixture['ids'])
    assert value['groups']==[dict(id='sample-alpha',split='train'),dict(id='sample-beta',split='test'),dict(id='sample-delta',split='validation')]
    assert value['aliases']==[dict(id='sample-gamma',target='sample-beta')]
    for index,(row,identifier) in enumerate(zip(fixture['rows'],fixture['ids']),1):
        assert records[identifier]['body'].encode()==encode(dict(text=row['text'].strip())) and dict(source_sha256=sha(fixture['raw']),source_row=index,record_id=identifier) in value['provenance']
    assert len(value['provenance'])==5 and records[fixture['duplicate']]['group_id']==records[fixture['linked']]['group_id']=='sample-beta'
    assert sum(row['status']=='approved' for row in records.values())==int(approved)
    if approved:
        assert records[fixture['train']]['status']=='approved' and json.loads(records[fixture['train']]['checks'])==dict.fromkeys(('quality','privacy','rights','context'),True)
    for row in value['reviews']:assert datetime.fromisoformat(row['created_utc']).utcoffset().total_seconds()==0
    return value,head

def verify_export(workspace,result,fixture,approved):
    folder=workspace/result['directory'];manifest=json.loads((folder/'manifest.json').read_bytes());raw=(folder/'approved.jsonl').read_bytes()
    expected=encode(dict(id=fixture['train'],text=fixture['rows'][0]['text'],split='train'))+b'\n' if approved else b''
    assert raw==expected and manifest==result['manifest'] and manifest['records']==int(approved) and manifest['public_release_authorized'] is False
    assert {p.name for p in folder.iterdir()}=={'approved.jsonl','manifest.json'} and manifest['files']=={'approved.jsonl':dict(bytes=len(raw),sha256=sha(raw))}
    return tree(folder)

def exercise(workspace,application=None):
    development=application is not None;app=Path(application) if development else ROOT/'application';workspace=Path(workspace)
    if not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_PRIVATE_EXERCISE_REQUIRED')
    fixture=fixture_ids(app);count=0
    def cli(*args,expected=0):
        nonlocal count
        entry=[str(app/'workbench.py')]
        if development:entry=['-c',"import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name='__main__')",str(app),str(app/'workbench.py')]
        p=subprocess.run([sys.executable,'-I','-B','-X','utf8',*entry,'--workspace',str(workspace),*map(str,args)],capture_output=True,timeout=90,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        if p.returncode!=expected:
            if workspace.is_dir():(workspace/'failed-command.log').write_bytes(p.stdout+p.stderr)
            raise AssertionError('Original CLI exercise failed; preserve the workspace.')
        count+=1;return json.loads(p.stdout)
    def request(name,value):
        path=workspace/'inbox'/name;path.write_bytes(encode(value));return 'inbox/'+name
    def mutate(operation,name,body,expected=0):return cli(operation,'--request',request(name,body),expected=expected)
    def review(head,identifier,approved):return dict(expected=head,id=identifier,decision='approved' if approved else 'pending',actor='sample_reviewer',note='Fictional practice evidence',checks=dict.fromkeys(('quality','privacy','rights','context'),approved))
    cli('init');empty=cli('status');assert empty['total']==0 and empty['counts']==dict(pending=0,approved=0,rejected=0)
    exported=mutate('export','empty-export.json',dict(expected=empty['head']))['result'];verify_export(workspace,exported,fixture,False)
    imported=mutate('import','import.json',dict(expected=empty['head'],file='inbox/sample-records.jsonl'));assert imported['result']['rows']==5 and imported['result']['added']==4
    state=cli('status');assert state['total']==4 and state['counts']==dict(pending=4,approved=0,rejected=0);_,head=verify_store(workspace,fixture);assert state['head']==head
    before=tree(workspace);path=request('stale-export.json',dict(expected=empty['head']));before=tree(workspace);cli('export','--request',path,expected=2);assert tree(workspace)==before
    missing=review(head,fixture['train'],True);missing['checks']['rights']=False;path=request('missing.json',missing);before=tree(workspace);cli('review','--request',path,expected=2);assert tree(workspace)==before
    old=head;mutate('review','parallel.json',review(head,fixture['validation'],False))
    stale=request('stale.json',review(old,fixture['train'],True));before=tree(workspace);cli('review','--request',stale,expected=2);assert tree(workspace)==before
    refreshed=cli('status');assert refreshed['head']!=old and refreshed['counts']['approved']==0
    mutate('review','approved.json',review(refreshed['head'],fixture['train'],True));approved=cli('status');assert approved['counts']==dict(pending=3,approved=1,rejected=0)
    records,head=verify_store(workspace,fixture,True);assert head==approved['head'] and len(records['reviews'])==2
    result=mutate('export','export.json',dict(expected=head))['result'];old_export=verify_export(workspace,result,fixture,True);assert result['manifest']['store_head']==head
    inputs=tree(workspace/'inbox');replay=mutate('import','reimport.json',dict(expected=head,file='inbox/sample-records.jsonl'));assert replay['result']['added']==0 and replay['head']==head;assert cli('status')==approved
    before=tree(workspace);cli('review','--request',stale,expected=2);assert tree(workspace)==before
    backup=mutate('backup','backup.json',dict(expected=head))['result'];assert backup['database_only'] and sha((workspace/backup['file']).read_bytes())==backup['sha256'];assert logical(workspace/backup['file'])==logical(workspace/'database/review.sqlite3')
    path=request('late-stale-export.json',dict(expected=refreshed['head']));before=tree(workspace);cli('export','--request',path,expected=2);assert tree(workspace)==before
    (workspace/'inbox/invalid.jsonl').write_bytes(encode(dict(text='Fictional extra row',group='sample-extra'))+b'\nnull\n');path=request('invalid-request.json',dict(expected=head,file='inbox/invalid.jsonl'));before=tree(workspace);cli('import','--request',path,expected=2);assert tree(workspace)==before and cli('status')==approved
    path=request('stale-backup.json',dict(expected=refreshed['head']));before=tree(workspace);cli('backup','--request',path,expected=2);assert tree(workspace)==before
    again=mutate('export','second-export.json',dict(expected=head))['result'];assert again['directory']!=result['directory'];verify_export(workspace,again,fixture,True);assert tree(workspace/result['directory'])==old_export
    saved=tree(workspace);assert cli('status')==approved and tree(workspace)==saved;cli('init',expected=2);assert tree(workspace)==saved
    for name,digest in inputs.items():assert sha((workspace/'inbox'/name).read_bytes())==digest
    assert count==24
    return dict(status='PASS',command_checks=count,input_rows=5,records=4,train_records=1,validation_records=1,test_records=2,approved_records=1,pending_records=3,provenance_rows=5,reviews=2,exported_records=1,export_files=2,empty_export_records=0,duplicate_linked_records_in_test=2,independent_record_ids_and_group_splits_checked=True,provenance_source_rows_independently_checked=True,logical_state_pin_independently_checked=True,stale_review_refused=True,missing_review_checks_refused=True,stale_export_and_backup_refused=True,invalid_batch_atomicity_checked=True,reimport_preserves_reviews_and_pin=True,export_bytes_and_hashes_independently_verified=True,fresh_export_destinations=True,old_export_unchanged=True,original_inputs_unchanged=True,backup_integrity_and_logical_rows_checked=True,saved_records_reopened=True,existing_initialization_refused_without_writes=True,public_release_authorized=False,export_automatically_training_only=False,model_executed=False,complete_restore_performed=False)
