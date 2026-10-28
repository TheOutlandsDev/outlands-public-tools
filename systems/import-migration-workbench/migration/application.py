"""Private explicit review, durable attempts and fresh local import destinations."""
from contextlib import closing
import csv
import io
import re
import sqlite3
import uuid
from . import contracts as c,runtime as r,engine,journal as j,destination as d

def _head(state,pin):
    c.pin(pin)
    if state['head']!=pin:c.fail('JOURNAL_HEAD_CONFLICT')
def _code(error):return str(error) if isinstance(error,r.WorkbenchError) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',str(error)) else 'OPERATION_REFUSED'
def overview():
    state,_=j.read();return dict(sequence=state['sequence'],head=state['head'],jobs=list(state['jobs'].values()),plans=list(state['plans'].values()),imports=list(state['imports'].values()),unfinished_jobs=sum(row['status']=='started' for row in state['jobs'].values()))
def history():
    state,events=j.read();return dict(head=state['head'],events=events)
def example():return r.decode(r.read_bytes(r.SOURCE/'examples/contract.json'))
def job(identifier):
    c.identifier(identifier);state,_=j.read()
    if identifier not in state['jobs']:c.fail('JOB_NOT_FOUND')
    return state['jobs'][identifier]
def inspect_plan(identifier):
    c.identifier(identifier);state,_=j.read();result=state['plans'].get(identifier)
    if result is None:c.fail('PLAN_NOT_REGISTERED')
    return dict(result=result,plan=engine.read_plan(result),current_source_bytes_reverified=False)
def inspect_import(identifier):
    c.identifier(identifier);state,_=j.read();result=state['imports'].get(identifier)
    if result is None:c.fail('IMPORT_NOT_REGISTERED')
    plan=d.verify(result,state['plans'][result['plan_id']]);return dict(result=result,records=[row['data'] for row in plan['records']],source_inputs_read=False,destination_verified=True)

def _run(kind,raw):
    value=r.decode(raw);c.envelope(value,('request',));c.request(kind,value['request'])
    with r.DATABASE_LOCK:
        state,_=j.read();_head(state,value['expected_head']);identifier=uuid.uuid4().hex;event=dict(operation='job_started',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,kind=kind,request=value['request']));state=j.append(event,state['head'])
        try:
            if kind=='plan':result=engine.write_plan(identifier,value['request'])
            else:result=d.create(identifier,state['plans'][value['request']['plan_id']])
            state=j.append(dict(operation='job_completed',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,result=result)),state['head'])
        except Exception as error:
            code=_code(error);current,_=j.read()
            if current['jobs'][identifier]['status']=='started':j.append(dict(operation='job_failed',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,code=code)),current['head'])
            raise r.WorkbenchError(code) from None
    return dict(head=state['head'],job=state['jobs'][identifier])
def plan(raw):return _run('plan',raw)
def import_plan(raw):return _run('import',raw)
def recover(raw):
    value=r.decode(raw);c.fields(value,('actor','reason'));c.text(value['actor'],160);c.text(value['reason']);recovered=[]
    with r.DATABASE_LOCK:
        state,_=j.read()
        for row in list(state['jobs'].values()):
            if row['status']=='started':
                state=j.append(dict(operation='job_interrupted',actor=value['actor'],reason=value['reason'],data=dict(job_id=row['job_id'],code='INTERRUPTED_NO_AUTOREPLAY')),state['head']);recovered.append(row['job_id'])
    return dict(head=state['head'],interrupted_jobs=recovered,partial_outputs_retained=True,automatically_replayed=False,existing_stores_modified=False)
def _csv(plan):
    output=io.StringIO(newline='');writer=csv.writer(output,lineterminator='\n');names=[row['target'] for row in plan['contract']['fields']];writer.writerow(names)
    def cell(value):
        text='' if value is None else ('true' if value is True else 'false' if value is False else str(value))
        if text and (text[0] in '\t\r\n' or text.lstrip()[:1] in ('=','+','-','@')):text="'"+text
        return text
    for row in plan['records']:writer.writerow([cell(row['data'][name]) for name in names])
    return output.getvalue().encode('utf-8')
def export(raw):
    value=r.decode(raw);c.envelope(value,('plan_id','import_id','checks'));c.identifier(value['plan_id']);c.checks(value['checks'])
    if value['import_id'] is not None:c.identifier(value['import_id'])
    with r.DATABASE_LOCK:
        state,_=j.read();_head(state,value['expected_head']);selected=state['plans'].get(value['plan_id'])
        if selected is None:c.fail('PLAN_NOT_REGISTERED')
        plan=engine.read_plan(selected);imported=None
        if value['import_id'] is not None:
            imported=state['imports'].get(value['import_id'])
            if imported is None or imported['plan_id']!=value['plan_id']:c.fail('IMPORT_PLAN_MISMATCH')
            d.verify(imported,selected)
        data={'plan.json':r.encode(plan),'accepted.jsonl':b''.join(r.encode(row['data'])+b'\n' for row in plan['records']),'accepted-display.csv':_csv(plan),'rejected.json':r.encode(plan['rejected']),'journal.json':r.encode(history()),'review.json':r.encode(value),'receipt.json':r.encode(dict(plan=selected,imported=imported,destination_verified=imported is not None))}
        manifest=dict(format='outlands-private-migration-export-v1',journal_head=state['head'],contains_normalized_values=True,contains_raw_source_bytes=False,public_release_authorized=False,csv_is_display_only=True,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())});directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        for name,content in sorted(data.items()):r.write_new(directory/name,content)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)
def backup_index():
    with r.DATABASE_LOCK:
        target=r.local_path('index-backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
        with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
            with closing(sqlite3.connect(target)) as destination:source.backup(destination);r.validate_schema(destination);j.load(destination)
        raw=r.read_bytes(target,r.MAX_STORE)
    return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),includes_plan_or_store_bytes=False,private_index_backup=True)
def demo():
    before={name:r.read_bytes(r.ROOT/'inbox'/name) for name in ('orders.csv','supplement.jsonl','conflicts.jsonl','contract.json')};rule=example();sources=[dict(path='inbox/orders.csv',format='csv'),dict(path='inbox/supplement.jsonl',format='jsonl')];checks=dict(quality=True,privacy=True,rights=True,context=True)
    def run(fn,request):return fn(r.encode(dict(expected_head=overview()['head'],actor='sample_operator',reason='Fictional staged migration',request=request)))
    first=run(plan,dict(sources=sources,contract=rule))['job']['result'];request=dict(plan_id=first['plan_id'],plan_sha256=first['plan_sha256'],accept_rejections=True,checks=checks);imported=run(import_plan,request)['job']['result'];inspect_import(imported['import_id'])
    repeat=run(plan,dict(sources=sources,contract=rule))['job']['result'];repeat_refused=False
    try:run(import_plan,dict(request,plan_id=repeat['plan_id'],plan_sha256=repeat['plan_sha256']))
    except r.WorkbenchError as error:
        if str(error)!='EXACT_PLAN_ALREADY_IMPORTED':raise
        repeat_refused=True
    conflict=run(plan,dict(sources=[sources[0],dict(path='inbox/conflicts.jsonl',format='jsonl')],contract=rule))['job']['result'];conflict_refused=False
    try:run(import_plan,dict(request,plan_id=conflict['plan_id'],plan_sha256=conflict['plan_sha256']))
    except r.WorkbenchError as error:
        if str(error)!='CONFLICTING_KEYS_REQUIRE_NEW_PLAN':raise
        conflict_refused=True
    report=export(r.encode(dict(expected_head=overview()['head'],actor='sample_operator',reason='Fictional private handoff',plan_id=first['plan_id'],import_id=imported['import_id'],checks=checks)));backup=backup_index();state=overview()
    return dict(mode='FICTIONAL_IMPORT_MIGRATION_DEMO',plans=len(state['plans']),imports=len(state['imports']),journal_events=state['sequence'],input_rows=first['summary']['input_rows'],accepted_rows=first['summary']['accepted_rows'],duplicate_rows=first['summary']['duplicate_rows'],rejected_rows=first['summary']['rejected_rows'],provenance_rows=imported['provenance_count'],conflict_rows=conflict['summary']['conflict_rows'],repeat_import_refused=repeat_refused,conflict_import_refused=conflict_refused,private_report_files=len(report['manifest']['files'])+1,index_backup_verified=backup['bytes']>0,index_includes_plan_or_store_bytes=False,source_files_changed=any(r.read_bytes(r.ROOT/'inbox'/name)!=raw for name,raw in before.items()),external_services_used=False,existing_stores_overwritten=False)
