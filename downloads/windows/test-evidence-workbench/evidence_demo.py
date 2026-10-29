"""Original CLI exercise and independent fictional case/result/export readers."""
from collections import Counter
from contextlib import closing
import base64,hashlib,html,json,os,sqlite3,subprocess,sys
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TRUST=('code_reviewed','authority','input_reviewed','effects_reviewed')
REVIEW=('quality','privacy','rights','context')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(v):return json.dumps(v,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def fixtures(application):
    raw=(application/'examples/sample-cases.json').read_bytes();values=json.loads(raw)['cases'];assert len(values)==4
    definitions={v['case_id']:v for v in values};assert set(definitions)=={'sample-total','sample-nonzero','sample-mismatch','sample-timeout'}
    assert definitions['sample-total']['input']==definitions['sample-mismatch']['input']=={'values':[3,5]}
    assert definitions['sample-total']['expected']==dict(exit_code=0,stdout=dict(total=8),stderr='')
    assert definitions['sample-mismatch']['expected']==dict(exit_code=0,stdout=dict(total=9),stderr='')
    assert definitions['sample-nonzero']['expected']==dict(exit_code=3,stdout=dict(accepted=False),stderr='fictional refusal\n')
    assert definitions['sample-timeout']['timeout_ms']==500
    pins={n:sha(encode(dict(version=1,parent_sha256=None,definition=d))) for n,d in definitions.items()}
    return dict(raw=raw,definitions=definitions,pins=pins)
def snapshot(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as c:
        assert c.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
        return {n:sorted(c.execute('SELECT * FROM '+n).fetchall(),key=repr) for n in ('meta','cases','trusts','artifacts','reviews')}
def verify_artifact(record,fixture,case_ids):
    payload=record['payload'];assert record['artifact_id']==payload['artifact_id'] and sha(encode(payload))==record['artifact_sha256']
    assert {v['case_id'] for v in payload['suite']}==set(case_ids)
    for v in payload['suite']:
        n=v['case_id'];assert v['version']==1 and v['definition']==fixture['definitions'][n] and v['case_sha256']==fixture['pins'][n]
        trust=v['trust_at_start'];assert trust['status']=='approved' and trust['row_version']==1 and trust['case_sha256']==fixture['pins'][n] and trust['checks']==dict.fromkeys(TRUST,True)
    result=payload['result'];assert result['status']=='completed' and result['complete'] and result['planned']==result['attempted']==len(case_ids) and result['not_started']==0
    verdicts={};raw_streams={}
    for row in result['cases']:
        n=row['case_id'];definition=fixture['definitions'][n];observed=row['observed'];assert row['case_sha256']==fixture['pins'][n] and observed['owned_child_started'] and observed['descendant_containment'] is False
        assert observed['script_sha256']==sha(definition['script'].encode()) and observed['input_sha256']==sha(encode(definition['input'])) and observed['expected']==definition['expected']
        streams={}
        for key in ('stdout','stderr'):
            value=observed['streams'][key];raw=base64.b64decode(value['base64'],validate=True);assert len(raw)==value['bytes'] and sha(raw)==value['sha256'] and not value['truncated'] and value['utf8_valid'];assert value['text']==raw.decode('utf-8');streams[key]=raw;raw_streams[n,key]=raw
        if n=='sample-timeout':
            assert observed['status']=='timeout' and streams==dict(stdout=b'',stderr=b'');passed=False
        else:
            stdout=json.loads(streams['stdout']);assert stdout==({'accepted':False} if n=='sample-nonzero' else {'total':sum([3,5])})
            independent=dict(exit_code=observed['exit_code']==definition['expected']['exit_code'],stdout=stdout==definition['expected']['stdout'],stderr=streams['stderr'].decode().replace('\r\n','\n')==definition['expected']['stderr'])
            assert observed['status']=='completed' and observed['matches']==independent;passed=all(independent.values())
        assert observed['passed']==passed;verdicts[n]=passed
    assert set(verdicts)==set(case_ids) and result['matched']==sum(verdicts.values()) and result['unmatched']==len(case_ids)-sum(verdicts.values())
    return raw_streams
class Pre(HTMLParser):
    def __init__(self):super().__init__();self.inside=False;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='pre':self.inside=True
    def handle_endtag(self,tag):
        if tag=='pre':self.inside=False
    def handle_data(self,data):
        if self.inside:self.parts.append(data)
def verify_export(workspace,receipt,record,fixture):
    streams=verify_artifact(record,fixture,fixture['definitions']);folder=workspace/receipt['directory'];manifest=json.loads((folder/'manifest.json').read_bytes());assert manifest==receipt['manifest']
    expected={'run.json','cases.json','review.json','summary.html'}|{'captures/'+n+'/'+stream+'.bin' for n,stream in streams}
    assert set(tree(folder))==expected|{'manifest.json'} and set(manifest['files'])==expected and len(expected)==12
    for name,row in manifest['files'].items():
        raw=(folder/name).read_bytes();assert row==dict(bytes=len(raw),sha256=sha(raw))
    assert manifest['artifact_id']==record['artifact_id'] and manifest['artifact_sha256']==record['artifact_sha256'] and manifest['review_version']==record['review']['row_version']
    assert [manifest[k] for k in ('complete','planned','attempted','matched','unmatched','not_started','public_release_authorized')]==[True,4,4,2,2,0,False]
    assert (folder/'run.json').read_bytes()==encode(record) and (folder/'cases.json').read_bytes()==encode(record['payload']['suite']) and (folder/'review.json').read_bytes()==encode(record['review'])
    for (n,stream),raw in streams.items():assert (folder/'captures'/n/(stream+'.bin')).read_bytes()==raw
    parsed=Pre();parsed.feed((folder/'summary.html').read_text(encoding='utf-8'));summary=json.loads(''.join(parsed.parts));assert summary['matched']==2 and summary['unmatched']==2
    assert {x['case_id']:x['matched'] for x in summary['cases']}==dict.fromkeys(('sample-total','sample-nonzero'),True)|dict.fromkeys(('sample-mismatch','sample-timeout'),False)
    return tree(folder)
def exercise(workspace,application=None):
    development=application is not None;app=Path(application) if development else ROOT/'application';workspace=Path(workspace)
    if not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_PRIVATE_EXERCISE_REQUIRED')
    fixture=fixtures(app);count=0;requests=0
    def cli(*args,expected=0,error=None):
        nonlocal count
        entry=[str(app/'workbench.py')]
        if development:entry=['-c',"import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name='__main__')",str(app),str(app/'workbench.py')]
        p=subprocess.run([sys.executable,'-I','-B',*entry,'--workspace',str(workspace),*args],capture_output=True,text=True,encoding='utf-8',timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});count+=1
        assert p.returncode==expected,(args,p.returncode,p.stdout,p.stderr);assert not p.stderr;value=json.loads(p.stdout)
        if error:assert value==dict(error=error)
        return value
    def request(command,value,expected=0,error=None):
        nonlocal requests
        requests+=1;name='inbox/request-'+str(requests)+'.json'
        with (workspace/name).open('xb') as h:h.write(encode(value))
        before=tree(workspace);result=cli(command,'--file',name,expected=expected,error=error)
        if expected:assert tree(workspace)==before
        return result
    cli('init');assert cli('cases')==dict(cases=[])
    cli('import','--file','inbox/sample-cases.json');registry=cli('cases')['cases'];assert len(registry)==4 and not list((workspace/'runs').iterdir())
    for case in registry:assert case['sha256']==fixture['pins'][case['case_id']] and case['trust']==dict(status='pending',row_version=0)
    plan=dict(cases=[dict(case_id=n,expected_sha256=fixture['pins'][n],trust_version=1) for n in fixture['definitions']])
    request('run',plan,2,'EXECUTION_TRUST_REQUIRED')
    trust=lambda n,**updates:dict(case_id=n,case_sha256=fixture['pins'][n],expected_version=0,status='approved',actor='sample_operator',note='Explicit fictional script trust',checks=dict.fromkeys(TRUST,True),**updates)
    invalid=trust('sample-total');invalid['checks']['effects_reviewed']=False;request('trust',invalid,2,'TRUST_CHECKS_REQUIRED')
    for n in fixture['definitions']:request('trust',trust(n))
    started=request('run',plan);first=cli('artifact','--id',started['artifact_id']);verify_artifact(first,fixture,fixture['definitions']);assert first['review']==dict(status='pending',row_version=0)
    review=lambda version,status='approved',checked=True:dict(artifact_id=first['artifact_id'],artifact_sha256=first['artifact_sha256'],expected_version=version,status=status,actor='sample_reviewer',note='Fictional failure evidence; verdicts unchanged',checks=dict.fromkeys(REVIEW,checked))
    request('review',review(0,checked=False),2,'REVIEW_CHECKS_REQUIRED');request('review',review(0));first['review']={k:v for k,v in review(0).items() if k!='expected_version'}|dict(row_version=1)
    exported=cli('export','--artifact',first['artifact_id']);old_export=verify_export(workspace,exported,first,fixture);first_payload=encode(first['payload'])
    small=dict(cases=[dict(case_id=n,expected_sha256=fixture['pins'][n],trust_version=1) for n in ('sample-total','sample-nonzero')]);second_id=request('run',small)['artifact_id'];second=cli('artifact','--id',second_id);verify_artifact(second,fixture,('sample-total','sample-nonzero'));assert second['review']==dict(status='pending',row_version=0) and second_id!=first['artifact_id']
    before=tree(workspace);cli('export','--artifact',second_id,expected=2,error='APPROVAL_REQUIRED');assert tree(workspace)==before
    comparison=cli('compare','--left',first['artifact_id'],'--right',second_id);assert not comparison['same_case_set'] and comparison['both_complete'];assert sum(x['present_left'] and x['present_right'] for x in comparison['cases'])==2
    request('review',review(0),2,'REVIEW_VERSION_CONFLICT');request('review',review(1,'pending',False));before=tree(workspace);cli('export','--artifact',first['artifact_id'],expected=2,error='APPROVAL_REQUIRED');assert tree(workspace)==before
    request('review',review(2));first['review']={k:v for k,v in review(2).items() if k!='expected_version'}|dict(row_version=3);fresh=cli('export','--artifact',first['artifact_id']);verify_export(workspace,fresh,first,fixture);assert fresh['directory']!=exported['directory']
    changed={**fixture['definitions']['sample-total'],'title':'Fictional revised total check'};saved=request('save-case',dict(definition=changed,expected_sha256=fixture['pins']['sample-total']));assert saved['version']==2
    latest=cli('show','--case','sample-total');expected_sha=sha(encode(dict(version=2,parent_sha256=fixture['pins']['sample-total'],definition=changed)));assert latest['sha256']==expected_sha and latest['trust']==dict(status='pending',row_version=0)
    request('run',plan,2,'CASE_REVISION_CONFLICT');request('run',dict(cases=[dict(case_id='sample-total',expected_sha256=expected_sha,trust_version=1)]),2,'EXECUTION_TRUST_REQUIRED')
    backup=cli('backup');assert sha((workspace/backup['file']).read_bytes())==backup['sha256'] and snapshot(workspace/backup['file'])==snapshot(workspace/'database/workbench.sqlite3')
    assert len(cli('cases')['cases'])==4 and len(cli('artifacts')['artifacts'])==2
    reopened=cli('artifact','--id',first['artifact_id']);assert encode(reopened['payload'])==first_payload and reopened['review']['status']=='approved';verify_artifact(reopened,fixture,fixture['definitions'])
    expected_staging=Counter((sha(v['script'].encode()),sha(encode(v['input']))) for n in list(fixture['definitions'])+['sample-total','sample-nonzero'] for v in [fixture['definitions'][n]])
    actual_staging=Counter((sha((folder/'check.py').read_bytes()),sha((folder/'input.json').read_bytes())) for folder in (workspace/'runs').iterdir());assert actual_staging==expected_staging
    assert tree(workspace/exported['directory'])==old_export and (workspace/'inbox/sample-cases.json').read_bytes()==fixture['raw']
    before=tree(workspace);cli('init',expected=2);assert tree(workspace)==before and not (workspace/'.session-lock').exists()
    return dict(status='PASS',command_checks=count,cases=4,case_revisions=5,planned=4,attempted=4,matched=2,unmatched=2,timeouts=1,expected_nonzero_matched=True,artifacts=2,owned_children_started=6,export_files=13,export_data_files=12,independent_case_artifact_script_input_hashes=True,independent_raw_capture_verdicts=True,independent_export_members_and_hashes=True,untrusted_plan_refused_without_children=True,missing_trust_checks_refused=True,missing_review_checks_refused=True,fresh_run_review_pending=True,pending_export_refused=True,stale_review_refused=True,review_revocation_blocks_future_export=True,new_case_revision_requires_trust=True,stale_plan_refused_without_children=True,old_artifact_payload_unchanged=True,old_exports_unchanged=True,original_inputs_unchanged=True,backup_integrity_and_logical_rows=True,saved_records_reopened=True,existing_initialization_refused_without_writes=True,execution_sandbox=False,descendant_containment=False,original_operational_checks_executed=False,external_services_used=False,publication_authorized=False,complete_restore_performed=False)
