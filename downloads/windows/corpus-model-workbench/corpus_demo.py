"""Original CLI exercise with independent fictional SQL and export oracles."""
from contextlib import closing
import hashlib,json,os,sqlite3,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def encoded(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).encode()
def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def fixture(application):
    raw=(application/'examples/sample-corpus.jsonl').read_bytes();rows=[json.loads(x) for x in raw.splitlines()];assert len(rows)==5
    for row in rows:
        if 'messages' in row:row['messages']=[dict(role=x['role'],content=x['content']) for x in row['messages']]
    ids=[sha(encoded(row['messages']) if 'messages' in row else row['text'].encode()) for row in rows]
    assert ids[0]==ids[1] and len(set(ids))==4
    return dict(raw=raw,rows=rows,ids=ids)
def snapshot(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as c:
        assert c.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
        tables=[n for (n,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'record_fts%' ORDER BY name")]
        return {n:sorted(c.execute('SELECT * FROM "'+n+'"').fetchall(),key=repr) for n in tables}
def verify_exports(workspace,fixture):
    expected_train=encoded({'messages':fixture['rows'][0]['messages']})+b'\n';expected_test=encoded({'messages':fixture['rows'][2]['messages']})+b'\n';found={}
    for folder in (workspace/'exports').iterdir():
        manifest=json.loads((folder/'manifest.json').read_bytes());kind=manifest['kind']
        for name,row in manifest['files'].items():
            raw=(folder/name).read_bytes();assert row==dict(bytes=len(raw),sha256=sha(raw))
        assert manifest['human_approval_required'] and not manifest['context_truncated'] and manifest['groups_kept_together'] and manifest['exact_content_deduplicated']
        if kind=='sft':
            assert {p.name for p in folder.iterdir()}=={'train.jsonl','validation.jsonl','test.jsonl','manifest.json','provenance.json'}
            assert (folder/'train.jsonl').read_bytes()==expected_train and (folder/'test.jsonl').read_bytes()==expected_test and (folder/'validation.jsonl').read_bytes()==b''
            assert manifest['counts']=={'train.jsonl':1,'test.jsonl':1} and manifest['skipped']==[]
            provenance=json.loads((folder/'provenance.json').read_bytes());assert set(provenance)=={fixture['ids'][0],fixture['ids'][2]}
            assert provenance[fixture['ids'][0]]==dict(split='train',group_id='sample_training',context_mode='complete_supplied_messages')
            assert provenance[fixture['ids'][2]]==dict(split='test',group_id='benchmark:sample_case_0',context_mode='complete_supplied_messages')
        elif kind=='rag':
            assert {p.name for p in folder.iterdir()}=={'rag.jsonl','manifest.json'}
            rows=[json.loads(x) for x in (folder/'rag.jsonl').read_bytes().splitlines()];assert len(rows)==1
            item=rows[0];text=fixture['rows'][3]['text'];identifier=fixture['ids'][3]
            assert item['id']==sha((identifier+':0:'+text).encode()) and item['text']==text
            assert item['metadata']==dict(record_id=identifier,title='Fictional Python reference',domain='coding',language='',group_id='sample_document',split='train',source_paths=['inbox/sample-corpus.jsonl'],review_status='approved',chunk=0)
            assert manifest['counts']=={'rag_chunks':1}
        else:raise AssertionError('Unexpected export kind')
        found[kind]=tree(folder)
    assert set(found)=={'sft','rag'};return found
def verify_demo(workspace,application):
    f=fixture(application);db=workspace/'database/corpus.sqlite3'
    with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row;records={row['id']:dict(row) for row in c.execute('SELECT * FROM records')};assert len(records)==5
        for index,group,split in [(0,'sample_training','train'),(2,'benchmark:sample_case_0','test'),(3,'sample_document','train'),(4,'sample_document_holdout','test')]:
            row=records[f['ids'][index]];assert row['group_id']==group and row['status']=='approved'
            assert c.execute('SELECT split FROM groups WHERE group_id=?',(group,)).fetchone()[0]==split
            assert [row[k] for k in ('quality_reviewed','privacy_reviewed','rights_reviewed','context_reviewed')]==[1,1,1,1]
            review=json.loads(c.execute('SELECT checks_json FROM reviews WHERE record_id=? ORDER BY id DESC',(row['id'],)).fetchone()[0]);assert review['materialized_sha256']==sha(encoded(json.loads(row['messages_json'])))
        provenance=[dict(row) for row in c.execute('SELECT p.*,s.path,s.sha256,s.bytes FROM provenance p JOIN sources s USING(source_id) WHERE s.path=?',('inbox/sample-corpus.jsonl',))];assert len(provenance)==5
        for number,identifier in enumerate(f['ids'],1):assert any(p['record_id']==identifier and p['source_row']==number and p['sha256']==sha(f['raw']) and p['bytes']==len(f['raw']) for p in provenance)
        queued=[row for row in records.values() if row['id'] not in f['ids']];assert len(queued)==1 and queued[0]['status']=='pending' and not queued[0]['quality_reviewed']
        assert c.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]==4
        runs=[dict(x) for x in c.execute('SELECT * FROM benchmark_runs')];assert len(runs)==6 and all(x['status']=='complete' and x['answer']=='Fictional model response. No code or real inference was executed.' for x in runs)
        assert sum(x['score']==3 for x in runs)==3 and sum(x['score'] is None for x in runs)==3
        assert {x['model'] for x in runs}=={'fictional-model-a','fictional-model-b'}
        assert c.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0]==1 and c.execute('SELECT COUNT(*) FROM discussions').fetchone()[0]==1 and c.execute('SELECT COUNT(*) FROM discussion_turns').fetchone()[0]==4
        discussion=c.execute('SELECT id FROM discussions').fetchone()[0]
    outputs=verify_exports(workspace,f);before=snapshot(db)
    backups=list((workspace/'backups').glob('*.sqlite3'));assert len(backups)==1 and snapshot(backups[0])==before
    assert (workspace/'inbox/sample-corpus.jsonl').read_bytes()==f['raw']
    return dict(status='PASS',input_rows=5,imported_records=4,records=5,approved_records=4,pending_records=1,source_row_receipts=5,total_provenance_links=6,train_records=3,test_records=2,sft_train=1,sft_test=1,sft_validation=0,sft_files=5,rag_train_chunks=1,rag_files=2,simulated_responses=6,invented_scores=3,discussion_turns=4,pending_generated_candidates=1,embeddings=1,independent_ids_splits_provenance=True,exact_sft_rag_bytes_and_hashes=True,backup_integrity_and_logical_rows=True,real_inference_verified=False,model_trained=False,generated_code_executed=False,publication_authorized=False,complete_restore_performed=False),discussion,outputs
def exercise(workspace,application=None):
    development=application is not None;app=Path(application) if development else ROOT/'application';workspace=Path(workspace)
    if not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_PRIVATE_EXERCISE_REQUIRED')
    count=0
    def cli(*args,expected=0):
        nonlocal count
        entry=[str(app/'workbench.py')]
        if development:entry=['-c',"import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name='__main__')",str(app),str(app/'workbench.py')]
        result=subprocess.run([sys.executable,'-I','-B',*entry,'--workspace',str(workspace),*args],capture_output=True,text=True,encoding='utf-8',timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        count+=1;assert result.returncode==expected,(args,result.returncode,result.stdout,result.stderr);assert not result.stderr
        value=json.loads(result.stdout);assert not isinstance(value,dict) or 'error' not in value or expected!=0;return value
    result=cli('demo');assert result['mode']=='FICTIONAL_CORPUS_WORKBENCH_DEMO' and result['fake_client_calls']==dict(tags=4,chat=10,embed=2)
    report,discussion,exports=verify_demo(workspace,app);original_exports=tree(workspace/'exports');original_inbox=tree(workspace/'inbox');f=fixture(app)
    assert cli('status')['records']==5
    assert cli('search','docstring')['total']==1
    assert cli('show',f['ids'][0])['status']=='approved'
    assert cli('import-jsonl','inbox/sample-corpus.jsonl')==dict(duplicate_provenance=5)
    assert cli('status')['status']==dict(approved=4,pending=1)
    cli('export','sft');cli('export','rag');verify_exports(workspace,f)
    backup=cli('backup');assert sha((workspace/backup['file']).read_bytes())==backup['sha256'] and snapshot(workspace/backup['file'])==snapshot(workspace/'database/corpus.sqlite3')
    before=tree(workspace)
    cli('review',f['ids'][0],'approved','--actor','sample_reviewer','--note','Fictional missing checks',expected=2);assert tree(workspace)==before
    cli('models',expected=2);assert tree(workspace)==before
    cli('queue-discussion',discussion);assert cli('status')['records']==5
    cli('review',f['ids'][0],'pending','--actor','sample_reviewer','--note','Fictional revocation')
    revoked=cli('export','sft');folder=workspace/revoked['directory'];assert (folder/'train.jsonl').read_bytes()==b'' and (folder/'test.jsonl').read_bytes()==encoded(dict(messages=f['rows'][2]['messages']))+b'\n'
    assert cli('status')['status']==dict(approved=3,pending=2)
    cli('review',f['ids'][0],'approved','--actor','sample_reviewer','--note','Fictional renewed review',*[f'--{k}-reviewed' for k in ('quality','privacy','rights','context')])
    cli('export','sft');backup=cli('backup');assert snapshot(workspace/backup['file'])==snapshot(workspace/'database/corpus.sqlite3')
    final=cli('status');assert final['status']==dict(approved=4,pending=1) and final['records']==5
    before=tree(workspace);cli('init',expected=2);assert tree(workspace)==before and not (workspace/'.session-lock').exists()
    assert all(tree(workspace/'exports')[n]==h for n,h in original_exports.items()) and tree(workspace/'inbox')==original_inbox
    report.update(command_checks=count,missing_checks_refused=True,unconfigured_real_backend_refused=True,queue_idempotent=True,revocation_blocks_future_export=True,old_exports_unchanged=True,original_inputs_unchanged=True,reimport_preserves_reviews=True,existing_initialization_refused_without_writes=True,saved_records_reopened=True)
    return report
