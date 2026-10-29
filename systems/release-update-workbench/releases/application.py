"""Private immutable release capture, comparison, review/revocation and evidence handoff."""
from contextlib import closing
import re
import sqlite3
import uuid
from . import contracts as c,runtime as r,journal as j,artifacts as a

def example():return {name:r.decode(r.read_bytes(r.SOURCE/'examples'/('capture-'+name+'.json'))) for name in ('v1','v2')}
def seed_fictional(root):
    for version,request in example().items():
        r.write_new(root/'inbox'/('capture-'+version+'.json'),r.encode(dict(expected_head=c.ZERO,actor='sample_operator',reason='Fictional package snapshot',request=request)))
        target=root/request['source'];r.mkdir(target)
        folders=sorted({'/'.join(row['path'].split('/')[:i]) for row in request['manifest']['inventory'] for i in range(1,len(row['path'].split('/')))},key=lambda n:(n.count('/'),n))
        for name in folders:r.mkdir(target/name)
        for row in request['manifest']['inventory']:r.write_new(target/row['path'],r.read_bytes(r.SOURCE/'examples'/('package-'+version)/row['path']))
def overview():
    state,_=j.read();return dict(sequence=state['sequence'],head=state['head'],jobs=list(state['jobs'].values()),candidates=list(state['candidates'].values()),comparisons=list(state['comparisons'].values()),plans=list(state['plans'].values()),reviews=state['reviews'],unfinished_jobs=sum(row['status']=='started' for row in state['jobs'].values()),target_updates_plan_only=True)
def history():
    state,events=j.read();return dict(head=state['head'],events=events)
def job(identifier):
    c.identifier(identifier);state,_=j.read()
    if identifier not in state['jobs']:c.fail('JOB_NOT_FOUND')
    return state['jobs'][identifier]
def inspect(kind,identifier):
    state,_=j.read();value=a.read(state,kind,identifier);return dict(result=state[a.COLLECTION[kind]][identifier],content=value,review=state['reviews'].get(identifier) if kind=='plan' else None)
def _head(state,pin):
    c.pin(pin)
    if state['head']!=pin:c.fail('JOURNAL_HEAD_CONFLICT')
def _clean(state):
    if any(row['status']=='started' for row in state['jobs'].values()):c.fail('UNFINISHED_JOB_REVIEW_REQUIRED')
def _code(error):return str(error) if isinstance(error,r.WorkbenchError) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',str(error)) else 'OPERATION_REFUSED'
def _run(kind,raw):
    value=r.decode(raw);c.envelope(value,('request',));c.request(kind,value['request'])
    with r.DATABASE_LOCK:
        state,_=j.read();_head(state,value['expected_head']);identifier=uuid.uuid4().hex;state=j.append(dict(operation='job_started',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,kind=kind,request=value['request'])),state['head'])
        try:
            result=a.write(state,identifier,kind,value['request']);state=j.append(dict(operation='job_completed',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,result=result)),state['head'])
        except Exception as error:
            code=_code(error);current,_=j.read()
            if current['jobs'][identifier]['status']=='started':j.append(dict(operation='job_failed',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,code=code)),current['head'])
            raise r.WorkbenchError(code) from None
    return dict(head=state['head'],job=state['jobs'][identifier])
def capture(raw):return _run('candidate',raw)
def compare(raw):return _run('comparison',raw)
def make_plan(raw):return _run('plan',raw)
def review(raw):
    value=r.decode(raw);c.envelope(value,('plan_id','plan_sha256','approve','checks'))
    with r.DATABASE_LOCK:
        state,_=j.read();_head(state,value['expected_head']);_clean(state);a.read(state,'plan',value['plan_id']);data={key:value[key] for key in ('plan_id','plan_sha256','approve','checks')};state=j.append(dict(operation='plan_review',actor=value['actor'],reason=value['reason'],data=data),state['head'])
    return dict(head=state['head'],review=state['reviews'][value['plan_id']],target_updates_performed=False)
def recover(raw):
    value=r.decode(raw);c.fields(value,('actor','reason'));c.text(value['actor'],160);c.text(value['reason']);recovered=[]
    with r.DATABASE_LOCK:
        state,_=j.read()
        for row in list(state['jobs'].values()):
            if row['status']=='started':state=j.append(dict(operation='job_interrupted',actor=value['actor'],reason=value['reason'],data=dict(job_id=row['job_id'],code='INTERRUPTED_NO_AUTOREPLAY')),state['head']);recovered.append(row['job_id'])
    return dict(head=state['head'],interrupted_jobs=recovered,partial_outputs_retained=True,automatically_replayed=False,target_updates_performed=False)
def export(raw):
    value=r.decode(raw);c.envelope(value,('plan_id','checks'));c.identifier(value['plan_id']);c.checks(value['checks'])
    with r.DATABASE_LOCK:
        state,_=j.read();_head(state,value['expected_head']);_clean(state);plan=a.read(state,'plan',value['plan_id']);review=state['reviews'].get(value['plan_id'])
        if review is None or review['status']!='APPROVED_FOR_PRIVATE_HANDOFF' or review['plan_sha256']!=state['plans'][value['plan_id']]['plan_sha256']:c.fail('CURRENT_PLAN_APPROVAL_REQUIRED')
        comparison=a.read(state,'comparison',plan['comparison_id']);baseline=a.read(state,'candidate',plan['baseline_id']);candidate=a.read(state,'candidate',plan['candidate_id'])
        data={'baseline.json':r.encode(baseline),'candidate.json':r.encode(candidate),'comparison.json':r.encode(comparison),'plan.json':r.encode(plan),'approval.json':r.encode(review),'export-review.json':r.encode(value),'journal.json':r.encode(history())}
        manifest=dict(format='outlands-private-release-handoff-v1',journal_head=state['head'],contains_private_inputs=True,payload_files_included=False,public_release_authorized=False,execution_authorized=False,target_updates_plan_only=True,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())});directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        for name,content in sorted(data.items()):r.write_new(directory/name,content)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)
def backup_index():
    with r.DATABASE_LOCK:
        target=r.local_path('index-backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
        with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
            with closing(sqlite3.connect(target)) as destination:source.backup(destination);r.validate_schema(destination);j.load(destination)
        raw=r.read_bytes(target,r.MAX_STORE)
    return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),contains_private_inputs=True,includes_payload_or_artifact_files=False,private_index_backup=True)
def demo():
    fixtures=example();checks=dict(quality=True,privacy=True,rights=True,context=True)
    def run(fn,request):return fn(r.encode(dict(expected_head=overview()['head'],actor='sample_operator',reason='Fictional release review',request=request)))['job']['result']
    baseline=run(capture,fixtures['v1']);next_request=dict(fixtures['v2'],parent_id=baseline['candidate_id']);candidate=run(capture,next_request);policy=dict(backup_confirmed=False,target_stopped_confirmed=False,readiness_confirmed=False,allow_removals=False,dependency_reviewed=False);request=dict(baseline_id=baseline['candidate_id'],baseline_sha256=baseline['candidate_sha256'],candidate_id=candidate['candidate_id'],candidate_sha256=candidate['candidate_sha256'],policy=policy);blocked=run(compare,request);ready=run(compare,dict(request,policy={key:True for key in policy}));planned=run(make_plan,dict(comparison_id=ready['comparison_id'],comparison_sha256=ready['comparison_sha256']));review(r.encode(dict(expected_head=overview()['head'],actor='sample_operator',reason='Fictional scoped approval',plan_id=planned['plan_id'],plan_sha256=planned['plan_sha256'],approve=True,checks=checks)));report=export(r.encode(dict(expected_head=overview()['head'],actor='sample_operator',reason='Fictional private handoff',plan_id=planned['plan_id'],checks=checks)));backup=backup_index();state=overview();lock=inspect('comparison',ready['comparison_id'])['content']['dependency_lock']
    return dict(mode='FICTIONAL_RELEASE_UPDATE_DEMO',candidates=len(state['candidates']),comparisons=len(state['comparisons']),plans=len(state['plans']),journal_events=state['sequence'],file_counts=ready['counts'],blockers_before=blocked['blocker_count'],blockers_after=ready['blocker_count'],lock_version_changes=lock['counts']['version_text_changed'],private_report_files=len(report['manifest']['files'])+1,index_backup_verified=backup['bytes']>0,index_contains_private_inputs=True,index_includes_payload_or_artifact_files=False,target_updates_performed=False,programs_executed=False,network_probed=False)
