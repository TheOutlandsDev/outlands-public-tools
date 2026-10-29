"""Typed replay recomputes descriptors/comparisons/plans; never reads payloads or updates targets."""
import copy
import re
from . import contracts as c,engine,runtime as r

def empty():return dict(sequence=0,head=c.ZERO,jobs={},candidates={},comparisons={},plans={},reviews={})
def candidate_value(state,identifier):return engine.candidate(state['jobs'][identifier]['request'])
def comparison(state,request):
    for role in ('baseline','candidate'):
        row=state['candidates'].get(request[role+'_id'])
        if row is None or row['candidate_sha256']!=request[role+'_sha256']:c.fail('CANDIDATE_NOT_REGISTERED_OR_PIN_MISMATCH')
    return engine.compare(candidate_value(state,request['baseline_id']),candidate_value(state,request['candidate_id']),request,state['jobs'][request['baseline_id']]['request'],state['jobs'][request['candidate_id']]['request'])
def plan_value(state,request):
    row=state['comparisons'].get(request['comparison_id'])
    if row is None or row['comparison_sha256']!=request['comparison_sha256']:c.fail('COMPARISON_NOT_REGISTERED_OR_PIN_MISMATCH')
    return engine.plan(comparison(state,state['jobs'][request['comparison_id']]['request']),request)
def result_for(state,identifier,kind,request):
    if kind=='candidate':
        value=engine.candidate(request);return dict(candidate_id=identifier,target='candidates/'+identifier,candidate_sha256=r.digest(r.encode(value)),manifest_sha256=request['manifest_sha256'],parent_id=request['parent_id'],label=request['label'],files=value['files'],payload_bytes=value['payload_bytes'])
    if kind=='comparison':
        value=comparison(state,request);return dict(comparison_id=identifier,target='comparisons/'+identifier,comparison_sha256=r.digest(r.encode(value)),baseline_id=request['baseline_id'],candidate_id=request['candidate_id'],status=value['status'],counts=value['counts'],blocker_count=len(value['blockers']))
    value=plan_value(state,request);return dict(plan_id=identifier,target='plans/'+identifier,plan_sha256=r.digest(r.encode(value)),comparison_id=request['comparison_id'],comparison_sha256=request['comparison_sha256'],status=value['status'])
def apply(state,event):
    c.fields(event,('operation','actor','reason','data'));c.text(event['actor'],160);c.text(event['reason']);op=c.choice(event['operation'],('job_started','job_completed','job_failed','job_interrupted','plan_review'));data=event['data'];result=copy.deepcopy(state)
    if op=='plan_review':
        c.fields(data,('plan_id','plan_sha256','approve','checks'));c.identifier(data['plan_id']);c.pin(data['plan_sha256'])
        if type(data['approve']) is not bool:c.fail('APPROVE_BOOLEAN_INVALID')
        c.assertions(data['checks'],data['approve']);row=state['plans'].get(data['plan_id'])
        if row is None or row['plan_sha256']!=data['plan_sha256']:c.fail('PLAN_NOT_REGISTERED_OR_PIN_MISMATCH')
        if any(j['status']=='started' for j in state['jobs'].values()):c.fail('UNFINISHED_JOB_REVIEW_REQUIRED')
        if data['approve'] and row['status']!='READY_FOR_MANUAL_REVIEW':c.fail('BLOCKED_PLAN_CANNOT_BE_APPROVED')
        result['reviews'][data['plan_id']]=dict(plan_id=data['plan_id'],plan_sha256=data['plan_sha256'],status='APPROVED_FOR_PRIVATE_HANDOFF' if data['approve'] else 'REVOKED',sequence=state['sequence']+1,actor=event['actor'],reason=event['reason'],checks=copy.deepcopy(data['checks']))
    elif op=='job_started':
        c.fields(data,('job_id','kind','request'));identifier=c.identifier(data['job_id']);kind=c.choice(data['kind'],('candidate','comparison','plan'));request=c.request(kind,data['request'])
        if identifier in state['jobs']:c.fail('JOURNAL_JOB_ID_REUSED')
        if any(row['status']=='started' for row in state['jobs'].values()):c.fail('UNFINISHED_JOB_REVIEW_REQUIRED')
        if len(state['jobs'])>=c.MAX_JOBS or state['sequence']>=c.MAX_EVENTS-1:c.fail('JOURNAL_LIMIT')
        if kind=='candidate':
            if request['parent_id'] is not None and request['parent_id'] not in state['candidates']:c.fail('PARENT_NOT_REGISTERED')
        else:result_for(state,identifier,kind,request)
        result['jobs'][identifier]=dict(job_id=identifier,kind=kind,request=copy.deepcopy(request),actor=event['actor'],reason=event['reason'],status='started',started_sequence=state['sequence']+1,result=None,error=None)
    else:
        c.fields(data,('job_id','result') if op=='job_completed' else ('job_id','code'));identifier=c.identifier(data['job_id']);job=result['jobs'].get(identifier)
        if job is None or job['status']!='started':c.fail('JOURNAL_JOB_NOT_PENDING')
        if op!='job_interrupted' and event['actor']!=job['actor']:c.fail('JOURNAL_ACTOR_MISMATCH')
        if op=='job_completed':
            expected=result_for(state,identifier,job['kind'],job['request'])
            if r.encode(data['result'])!=r.encode(expected):c.fail('JOURNAL_RESULT_INVALID')
            result[{'candidate':'candidates','comparison':'comparisons','plan':'plans'}[job['kind']]][identifier]=copy.deepcopy(expected);job.update(status='completed',result=expected)
        else:
            if type(data['code']) is not str or not re.fullmatch('[A-Z][A-Z0-9_]{0,79}',data['code']):c.fail('JOURNAL_ERROR_CODE_INVALID')
            job.update(status='interrupted' if op=='job_interrupted' else 'failed',error=data['code'])
        job['finished_sequence']=state['sequence']+1
    return result
def load(con):
    state=empty();events=[];rows=con.execute('SELECT sequence,sha256,parent_sha256,payload_json FROM events ORDER BY sequence LIMIT 257').fetchall()
    if len(rows)>c.MAX_EVENTS:c.fail('JOURNAL_LIMIT')
    for sequence,pin,parent,raw in rows:
        if type(sequence) is not int or sequence!=state['sequence']+1 or parent!=state['head'] or type(raw) is not str or len(raw.encode())>r.MAX_INPUT:c.fail('JOURNAL_CHAIN_INVALID')
        payload=r.decode(raw.encode());c.fields(payload,('sequence','parent_sha256','event'));c.integer(payload['sequence'],1,c.MAX_EVENTS)
        if payload['sequence']!=sequence or payload['parent_sha256']!=parent or r.digest(r.encode(payload))!=pin:c.fail('JOURNAL_HASH_MISMATCH')
        state=apply(state,payload['event']);state.update(sequence=sequence,head=pin);events.append(dict(sequence=sequence,sha256=pin,parent_sha256=parent,event=payload['event']))
    return state,events
def read():
    with r.connect() as con:return load(con)
def append(event,expected_head):
    c.pin(expected_head)
    with r.connect() as con:
        con.execute('BEGIN IMMEDIATE');state,_=load(con)
        if state['head']!=expected_head:c.fail('JOURNAL_HEAD_CONFLICT')
        if state['sequence']>=c.MAX_EVENTS:c.fail('JOURNAL_LIMIT')
        result=apply(state,event);sequence=state['sequence']+1;payload=dict(sequence=sequence,parent_sha256=state['head'],event=event);raw=r.encode(payload);pin=r.digest(raw);con.execute('INSERT INTO events VALUES(?,?,?,?)',(sequence,pin,state['head'],raw.decode()));result.update(sequence=sequence,head=pin)
    return result
