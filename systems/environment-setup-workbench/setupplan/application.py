"""Complete private profile, evaluation, reviewed plan and evidence workflow."""
from contextlib import closing
import copy
import re
import sqlite3
import uuid
from . import contracts as c,runtime as r,journal as j,artifacts as a,engine

def seed_fictional(root):
    for name in ('profile.json','observations.json'):r.write_new(root/'inbox'/name,r.read_bytes(r.SOURCE/'examples'/name))

def example():return {name:r.decode(r.read_bytes(r.SOURCE/'examples'/(name+'.json'))) for name in ('profile','observations')}

def overview():
    state,_=j.read();return dict(sequence=state['sequence'],head=state['head'],jobs=list(state['jobs'].values()),profiles=list(state['profiles'].values()),evaluations=list(state['evaluations'].values()),plans=list(state['plans'].values()),unfinished_jobs=sum(row['status']=='started' for row in state['jobs'].values()),plan_only=True)

def history():
    state,events=j.read();return dict(head=state['head'],events=events)

def job(identifier):
    c.identifier(identifier);state,_=j.read()
    if identifier not in state['jobs']:c.fail('JOB_NOT_FOUND')
    return state['jobs'][identifier]

def inspect(kind,identifier):
    state,_=j.read();value=a.read(state,kind,identifier);return dict(result=state[a.COLLECTION[kind]][identifier],content=value)

def compare(kind,first,second):
    c.choice(kind,('profile','evaluation'));state,_=j.read();return engine.differences(a.read(state,kind,first),a.read(state,kind,second))

def _code(error):return str(error) if isinstance(error,r.WorkbenchError) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',str(error)) else 'OPERATION_REFUSED'

def _head(state,pin):
    c.pin(pin)
    if state['head']!=pin:c.fail('JOURNAL_HEAD_CONFLICT')

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

def save_profile(raw):return _run('profile',raw)
def evaluate(raw):return _run('evaluation',raw)
def make_plan(raw):return _run('plan',raw)

def recover(raw):
    value=r.decode(raw);c.fields(value,('actor','reason'));c.text(value['actor'],160);c.text(value['reason']);recovered=[]
    with r.DATABASE_LOCK:
        state,_=j.read()
        for row in list(state['jobs'].values()):
            if row['status']=='started':state=j.append(dict(operation='job_interrupted',actor=value['actor'],reason=value['reason'],data=dict(job_id=row['job_id'],code='INTERRUPTED_NO_AUTOREPLAY')),state['head']);recovered.append(row['job_id'])
    return dict(head=state['head'],interrupted_jobs=recovered,partial_outputs_retained=True,automatically_replayed=False,plan_only=True)

def export(raw):
    value=r.decode(raw);c.envelope(value,('plan_id','checks'));c.identifier(value['plan_id']);c.checks(value['checks'])
    with r.DATABASE_LOCK:
        state,_=j.read();_head(state,value['expected_head']);plan=a.read(state,'plan',value['plan_id']);selected=state['evaluations'][plan['evaluation_id']];evaluation=a.read(state,'evaluation',plan['evaluation_id']);profile=a.read(state,'profile',selected['profile_id'])
        data={'profile.json':r.encode(profile),'evaluation.json':r.encode(evaluation),'plan.json':r.encode(plan),'review.json':r.encode(value),'journal.json':r.encode(history())}
        manifest=dict(format='outlands-private-setup-handoff-v1',journal_head=state['head'],contains_private_inputs=True,public_release_authorized=False,execution_authorized=False,plan_only=True,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())});directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        for name,content in sorted(data.items()):r.write_new(directory/name,content)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)

def backup_index():
    with r.DATABASE_LOCK:
        target=r.local_path('index-backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
        with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
            with closing(sqlite3.connect(target)) as destination:source.backup(destination);r.validate_schema(destination);j.load(destination)
        raw=r.read_bytes(target,r.MAX_STORE)
    return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),contains_private_inputs=True,includes_artifact_files=False,private_index_backup=True)

def demo():
    fixtures=example();checks=dict(quality=True,privacy=True,rights=True,context=True)
    def run(fn,request):return fn(r.encode(dict(expected_head=overview()['head'],actor='sample_operator',reason='Fictional setup review',request=request)))['job']['result']
    first=run(save_profile,dict(parent_id=None,profile=fixtures['profile']));blocked=copy.deepcopy(fixtures['observations']);blocked['prerequisites']['sample_runtime']='MISSING'
    bad=run(evaluate,dict(profile_id=first['profile_id'],profile_sha256=first['profile_sha256'],observations=blocked));good=run(evaluate,dict(profile_id=first['profile_id'],profile_sha256=first['profile_sha256'],observations=fixtures['observations']));comparison=compare('evaluation',bad['evaluation_id'],good['evaluation_id'])
    revision=copy.deepcopy(fixtures['profile']);revision['label']='Fictional revision two';revision['steps'][0]['label']='Review declared prerequisites';run(save_profile,dict(parent_id=first['profile_id'],profile=revision));planned=run(make_plan,dict(evaluation_id=good['evaluation_id'],evaluation_sha256=good['evaluation_sha256'],checks=checks));inspect('plan',planned['plan_id']);report=export(r.encode(dict(expected_head=overview()['head'],actor='sample_operator',reason='Fictional private handoff',plan_id=planned['plan_id'],checks=checks)));backup=backup_index();state=overview()
    return dict(mode='FICTIONAL_ENVIRONMENT_SETUP_DEMO',profiles=len(state['profiles']),evaluations=len(state['evaluations']),plans=len(state['plans']),journal_events=state['sequence'],checks=good['summary']['checks'],blocked_steps_before=bad['summary']['blocked_steps'],blocked_steps_after=good['summary']['blocked_steps'],changed_checks=comparison['changes']['checks']['changed'],private_report_files=len(report['manifest']['files'])+1,index_backup_verified=backup['bytes']>0,index_contains_private_inputs=True,index_includes_artifact_files=False,plan_only=True,programs_executed=False,network_probed=False,host_inventory_collected=False,configuration_modified=False)
