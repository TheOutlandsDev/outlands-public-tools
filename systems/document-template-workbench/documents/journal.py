"""Typed append-only revision/build replay; no filesystem actions during replay."""
import copy
import re
from . import contracts as c,model,runtime as r

def empty():return dict(sequence=0,head=c.ZERO,jobs={},templates={},previews={},builds={})
def template_value(state,identifier):return state['jobs'][identifier]['request']['template']
def compose_preview(state,request):
    chosen=state['templates'].get(request['template_id'])
    if chosen is None or chosen['template_sha256']!=request['template_sha256']:c.fail('TEMPLATE_NOT_REGISTERED_OR_PIN_MISMATCH')
    return model.compose(template_value(state,request['template_id']),request['values'],request['sections'])
def apply(state,event):
    c.fields(event,('operation','actor','reason','data'));c.text(event['actor'],160);c.text(event['reason']);op=c.choice(event['operation'],('job_started','job_completed','job_failed','job_interrupted'));data=event['data'];result=copy.deepcopy(state)
    if op=='job_started':
        c.fields(data,('job_id','kind','request'));identifier=c.identifier(data['job_id']);kind=c.choice(data['kind'],('template','preview','build'));request=c.request(kind,data['request'])
        if identifier in state['jobs']:c.fail('JOURNAL_JOB_ID_REUSED')
        if any(row['status']=='started' for row in state['jobs'].values()):c.fail('UNFINISHED_JOB_REVIEW_REQUIRED')
        if len(state['jobs'])>=c.MAX_JOBS or state['sequence']>=c.MAX_EVENTS-1:c.fail('JOURNAL_LIMIT')
        if kind=='template':
            if request['parent_id'] is not None and request['parent_id'] not in state['templates']:c.fail('PARENT_NOT_REGISTERED')
        elif kind=='preview':compose_preview(state,request)
        else:
            selected=state['previews'].get(request['preview_id'])
            if selected is None or selected['preview_sha256']!=request['preview_sha256']:c.fail('PREVIEW_NOT_REGISTERED_OR_PIN_MISMATCH')
        result['jobs'][identifier]=dict(job_id=identifier,kind=kind,request=copy.deepcopy(request),actor=event['actor'],reason=event['reason'],status='started',started_sequence=state['sequence']+1,result=None,error=None)
    else:
        c.fields(data,('job_id','result') if op=='job_completed' else ('job_id','code'));identifier=c.identifier(data['job_id']);job=result['jobs'].get(identifier)
        if job is None or job['status']!='started':c.fail('JOURNAL_JOB_NOT_PENDING')
        if op!='job_interrupted' and event['actor']!=job['actor']:c.fail('JOURNAL_ACTOR_MISMATCH')
        if op=='job_completed':
            value=data['result'];request=job['request']
            if job['kind']=='template':
                expected=dict(template_id=identifier,target='templates/'+identifier,template_sha256=r.digest(r.encode(request['template'])),parent_id=request['parent_id'],label=request['template']['label'])
                if value!=expected:c.fail('JOURNAL_RESULT_INVALID')
                result['templates'][identifier]=copy.deepcopy(value)
            elif job['kind']=='preview':
                preview=compose_preview(state,request);expected=dict(preview_id=identifier,target='previews/'+identifier,preview_sha256=r.digest(r.encode(preview)),template_id=request['template_id'],template_sha256=request['template_sha256'],values_sha256=preview['values_sha256'],summary=preview['summary'])
                if value!=expected or any(type(v) is not int for v in value['summary'].values()):c.fail('JOURNAL_RESULT_INVALID')
                result['previews'][identifier]=copy.deepcopy(value)
            else:
                c.fields(value,('build_id','target','preview_id','preview_sha256','document_sha256','document_bytes','parts'))
                selected=state['previews'][request['preview_id']];c.pin(value['document_sha256']);c.integer(value['document_bytes'],1,c.MAX_DOCX);c.integer(value['parts'],8,8)
                if value['build_id']!=identifier or value['target']!='builds/'+identifier or any(value[k]!=selected[k] for k in ('preview_id','preview_sha256')):c.fail('JOURNAL_RESULT_INVALID')
                result['builds'][identifier]=copy.deepcopy(value)
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
