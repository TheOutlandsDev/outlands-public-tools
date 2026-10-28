"""Typed, replay-checked append-only job journal; no file operations on replay."""
import copy
import re
from . import contracts as c,runtime as r

def empty():return dict(sequence=0,head=c.ZERO,jobs={},snapshots={})

def _result(kind,job_id,request,result,state):
    common=('snapshot_id','manifest_sha256','file_count','directory_count','total_bytes')
    c.fields(result,(*common,'target','excluded_count') if kind=='snapshot' else (*common,'target','receipt_sha256') if kind in ('restore','restore_imported') else common)
    c.identifier(result['snapshot_id']);c.pin(result['manifest_sha256']);c.integer(result['file_count'],0,c.MAX_FILES);c.integer(result['directory_count'],0,c.MAX_DIRS);c.integer(result['total_bytes'],0,c.MAX_TOTAL)
    if kind=='snapshot':
        if result['snapshot_id']!=job_id or result['target']!='snapshots/'+job_id:c.fail('JOURNAL_RESULT_INVALID')
        c.integer(result['excluded_count'],0,c.MAX_ENTRIES)
    elif kind=='restore_imported':
        if result['manifest_sha256']!=request['manifest_sha256'] or result['target']!='restores/'+job_id:c.fail('JOURNAL_RESULT_PIN_MISMATCH')
        c.pin(result['receipt_sha256'])
    else:
        expected=state['snapshots'][request['snapshot_id']]['result']
        if any(result[name]!=expected[name] for name in common):c.fail('JOURNAL_RESULT_PIN_MISMATCH')
        if kind=='restore':
            c.pin(result['receipt_sha256'])
            if result['target']!='restores/'+job_id:c.fail('JOURNAL_RESULT_INVALID')

def apply(state,event):
    c.fields(event,('operation','actor','reason','data'));c.text(event['actor'],160);c.text(event['reason']);op=c.choice(event['operation'],('job_started','job_completed','job_failed','job_interrupted','hold_changed'));data=event['data'];result=copy.deepcopy(state)
    if op=='job_started':
        c.fields(data,('job_id','kind','request'));identifier=c.identifier(data['job_id']);kind=c.choice(data['kind'],('snapshot','restore','verify','restore_imported'));c.request(kind,data['request'])
        if identifier in state['jobs']:c.fail('JOURNAL_JOB_ID_REUSED')
        if any(row['status']=='started' for row in state['jobs'].values()):c.fail('UNFINISHED_JOB_REVIEW_REQUIRED')
        if len(state['jobs'])>=c.MAX_JOBS or state['sequence']>=c.MAX_EVENTS-1:c.fail('JOURNAL_LIMIT')
        if kind in ('restore','verify') and data['request']['snapshot_id'] not in state['snapshots']:c.fail('SNAPSHOT_NOT_REGISTERED')
        result['jobs'][identifier]=dict(job_id=identifier,kind=kind,request=copy.deepcopy(data['request']),actor=event['actor'],reason=event['reason'],status='started',started_sequence=state['sequence']+1,result=None,error=None)
    elif op=='hold_changed':
        c.fields(data,('snapshot_id','hold'));identifier=c.identifier(data['snapshot_id'])
        if identifier not in state['snapshots']:c.fail('SNAPSHOT_NOT_REGISTERED')
        if type(data['hold']) is not bool:c.fail('HOLD_INVALID')
        if any(row['status']=='started' for row in state['jobs'].values()):c.fail('UNFINISHED_JOB_REVIEW_REQUIRED')
        result['snapshots'][identifier]['hold']=data['hold']
    else:
        c.fields(data,('job_id','result') if op=='job_completed' else ('job_id','code'));identifier=c.identifier(data['job_id']);job=result['jobs'].get(identifier)
        if job is None or job['status']!='started':c.fail('JOURNAL_JOB_NOT_PENDING')
        if op!='job_interrupted' and event['actor']!=job['actor']:c.fail('JOURNAL_ACTOR_MISMATCH')
        if op=='job_completed':
            _result(job['kind'],identifier,job['request'],data['result'],state);job.update(status='completed',result=copy.deepcopy(data['result']))
            if job['kind']=='snapshot':result['snapshots'][identifier]=dict(snapshot_id=identifier,completed_sequence=state['sequence']+1,hold=False,result=copy.deepcopy(data['result']))
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
        state,_=load(con)
        if state['head']!=expected_head:c.fail('JOURNAL_HEAD_CONFLICT')
        if state['sequence']>=c.MAX_EVENTS:c.fail('JOURNAL_LIMIT')
        result=apply(state,event);sequence=state['sequence']+1;payload=dict(sequence=sequence,parent_sha256=state['head'],event=event);raw=r.encode(payload);pin=r.digest(raw);con.execute('INSERT INTO events VALUES(?,?,?,?)',(sequence,pin,state['head'],raw.decode()));result.update(sequence=sequence,head=pin)
    return result
