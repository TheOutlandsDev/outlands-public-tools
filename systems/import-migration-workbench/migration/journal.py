"""Hash-linked typed job replay; no filesystem actions during replay."""
import copy
import re
from . import contracts as c,runtime as r

def empty():return dict(sequence=0,head=c.ZERO,jobs={},plans={},imports={})
def summary(value):
    c.fields(value,('input_rows','accepted_rows','duplicate_rows','rejected_rows','conflict_rows','conflicting_keys'))
    for n in value:c.integer(value[n],0,c.MAX_ROWS)
    if value['input_rows']!=sum(value[k] for k in ('accepted_rows','duplicate_rows','rejected_rows','conflict_rows')) or value['conflicting_keys']>value['conflict_rows']//2:c.fail('JOURNAL_SUMMARY_INVALID')
def apply(state,event):
    c.fields(event,('operation','actor','reason','data'));c.text(event['actor'],160);c.text(event['reason']);op=c.choice(event['operation'],('job_started','job_completed','job_failed','job_interrupted'));data=event['data'];result=copy.deepcopy(state)
    if op=='job_started':
        c.fields(data,('job_id','kind','request'));identifier=c.identifier(data['job_id']);kind=c.choice(data['kind'],('plan','import'));c.request(kind,data['request'])
        if identifier in state['jobs']:c.fail('JOURNAL_JOB_ID_REUSED')
        if any(row['status']=='started' for row in state['jobs'].values()):c.fail('UNFINISHED_JOB_REVIEW_REQUIRED')
        if len(state['jobs'])>=c.MAX_JOBS or state['sequence']>=c.MAX_EVENTS-1:c.fail('JOURNAL_LIMIT')
        if kind=='import':
            plan=state['plans'].get(data['request']['plan_id'])
            if plan is None or plan['plan_sha256']!=data['request']['plan_sha256']:c.fail('PLAN_NOT_REGISTERED_OR_PIN_MISMATCH')
            if plan['summary']['conflict_rows']:c.fail('CONFLICTING_KEYS_REQUIRE_NEW_PLAN')
            if not plan['summary']['accepted_rows']:c.fail('NO_ACCEPTED_RECORDS')
            if plan['summary']['rejected_rows'] and not data['request']['accept_rejections']:c.fail('REJECTED_ROWS_REVIEW_REQUIRED')
            if any(row['fingerprint']==plan['fingerprint'] for row in state['imports'].values()):c.fail('EXACT_PLAN_ALREADY_IMPORTED')
        result['jobs'][identifier]=dict(job_id=identifier,kind=kind,request=copy.deepcopy(data['request']),actor=event['actor'],reason=event['reason'],status='started',started_sequence=state['sequence']+1,result=None,error=None)
    else:
        c.fields(data,('job_id','result') if op=='job_completed' else ('job_id','code'));identifier=c.identifier(data['job_id']);job=result['jobs'].get(identifier)
        if job is None or job['status']!='started':c.fail('JOURNAL_JOB_NOT_PENDING')
        if op!='job_interrupted' and event['actor']!=job['actor']:c.fail('JOURNAL_ACTOR_MISMATCH')
        if op=='job_completed':
            value=data['result']
            if job['kind']=='plan':
                c.fields(value,('plan_id','target','plan_sha256','fingerprint','summary'));c.identifier(value['plan_id']);c.pin(value['plan_sha256']);c.pin(value['fingerprint']);summary(value['summary'])
                if value['plan_id']!=identifier or value['target']!='plans/'+identifier:c.fail('JOURNAL_RESULT_INVALID')
                result['plans'][identifier]=copy.deepcopy(value)
            else:
                c.fields(value,('import_id','target','plan_id','plan_sha256','fingerprint','database_sha256','database_bytes','record_count','provenance_count','rejected_count'))
                c.identifier(value['import_id']);c.integer(value['database_bytes'],0,c.MAX_OUTPUT_STORE);c.integer(value['record_count'],1,c.MAX_ROWS);c.integer(value['provenance_count'],1,c.MAX_ROWS);c.integer(value['rejected_count'],0,c.MAX_ROWS);c.pin(value['database_sha256']);plan=state['plans'][job['request']['plan_id']]
                if value['import_id']!=identifier or value['target']!='stores/'+identifier or any(value[k]!=plan[k] for k in ('plan_id','plan_sha256','fingerprint')) or value['record_count']!=plan['summary']['accepted_rows'] or value['provenance_count']!=plan['summary']['accepted_rows']+plan['summary']['duplicate_rows'] or value['rejected_count']!=plan['summary']['rejected_rows']:c.fail('JOURNAL_RESULT_INVALID')
                result['imports'][identifier]=copy.deepcopy(value)
            job.update(status='completed',result=copy.deepcopy(value))
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
