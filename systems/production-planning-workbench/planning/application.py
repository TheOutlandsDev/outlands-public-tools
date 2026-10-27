"""Append-only private revisions, operator review, reports and SQLite backups."""
import csv
from datetime import datetime,timezone
import io
import sqlite3
import uuid
from pydantic import BaseModel,ConfigDict,Field
from . import project,runtime
from .engines.operator import OperatorWorkflowCommand,resolve_operator_transition


def now():return datetime.now(timezone.utc).isoformat()


def _hash(project_id,sequence,parent,raw):
    return runtime.digest(runtime.encode(dict(project_id=project_id,sequence=sequence,parent=parent,project=runtime.decode(raw))))


def _selected(con,project_id):
    row=con.execute('SELECT sequence,revision_sha256,parent_sha256,substr(snapshot_json,1,?),length(CAST(snapshot_json AS BLOB)) FROM revisions WHERE project_id=? ORDER BY sequence DESC LIMIT 1',(runtime.MAX_INPUT+1,project_id)).fetchone()
    if row is None:raise runtime.WorkbenchError('PROJECT_NOT_FOUND')
    sequence,revision,parent,text,length=row
    if length>runtime.MAX_INPUT:raise runtime.WorkbenchError('STORE_RECORD_LIMIT')
    raw=text.encode('utf-8')
    if _hash(project_id,sequence,parent,raw)!=revision:raise runtime.WorkbenchError('REVISION_HASH_MISMATCH')
    parsed=project.parse(raw)
    if parsed.project_id!=project_id:raise runtime.WorkbenchError('PROJECT_ID_MISMATCH')
    return dict(sequence=sequence,revision_sha256=revision,parent_sha256=parent,project=parsed.model_dump(mode='json'))


def show(project_id):
    with runtime.connect() as con:return _selected(con,project_id)


def projects():
    with runtime.connect() as con:
        rows=con.execute('SELECT project_id,MAX(sequence) FROM revisions GROUP BY project_id ORDER BY project_id LIMIT 101').fetchall()
        if len(rows)>100:raise runtime.WorkbenchError('PROJECT_LIMIT')
        return dict(projects=[dict(project_id=r[0],revisions=r[1]) for r in rows])


def save(raw,expected=None):
    selected=project.parse(raw);project.calculate(selected)
    canonical=runtime.encode(selected.model_dump(mode='json'))
    if len(canonical)>runtime.MAX_INPUT:raise runtime.WorkbenchError('PROJECT_LIMIT')
    with runtime.connect() as con:
        present=con.execute('SELECT 1 FROM revisions WHERE project_id=?',(selected.project_id,)).fetchone()
        if present:
            before=_selected(con,selected.project_id)
            if expected!=before['revision_sha256']:raise runtime.WorkbenchError('REVISION_CONFLICT')
            old=before['project']['order_history'];new=selected.model_dump(mode='json')['order_history']
            if len(new)<len(old) or new[:len(old)]!=old:raise runtime.WorkbenchError('ORDER_HISTORY_APPEND_ONLY')
            if before['project']==selected.model_dump(mode='json'):return dict(project_id=selected.project_id,revision_sha256=expected,sequence=before['sequence'],created=False)
            sequence=before['sequence']+1;parent=expected
        else:
            if expected is not None:raise runtime.WorkbenchError('REVISION_CONFLICT')
            if con.execute('SELECT COUNT(DISTINCT project_id) FROM revisions').fetchone()[0]>=100:raise runtime.WorkbenchError('PROJECT_LIMIT')
            sequence=1;parent=None
        if sequence>200:raise runtime.WorkbenchError('REVISION_LIMIT')
        revision=_hash(selected.project_id,sequence,parent,canonical)
        con.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?)',(selected.project_id,sequence,revision,parent,canonical.decode(),now()))
    return dict(project_id=selected.project_id,revision_sha256=revision,sequence=sequence,created=True)


def import_file(path,expected=None):return save(runtime.read_bytes(runtime.local_path(path)),expected)


def history(project_id):
    with runtime.connect() as con:
        rows=con.execute('SELECT sequence,revision_sha256,parent_sha256,created_utc FROM revisions WHERE project_id=? ORDER BY sequence LIMIT 201',(project_id,)).fetchall()
    return dict(project_id=project_id,revisions=[dict(sequence=r[0],revision_sha256=r[1],parent_sha256=r[2],created_utc=r[3]) for r in rows])


def _states(con,project_id,revision):
    rows=con.execute('SELECT state_json FROM (SELECT state_json,ROW_NUMBER() OVER(PARTITION BY action_id ORDER BY row_version DESC) AS rank FROM actions WHERE project_id=? AND revision_sha256=?) WHERE rank=1 LIMIT 2001',(project_id,revision)).fetchall()
    if len(rows)>2000:raise runtime.WorkbenchError('ACTION_LIMIT')
    return {v['action_id']:v for v in (runtime.decode(r[0].encode()) for r in rows)}


def plan(project_id):
    snapshot=show(project_id);selected=project.parse(runtime.encode(snapshot['project']))
    result=project.calculate(selected);revision=snapshot['revision_sha256']
    with runtime.connect() as con:states=_states(con,project_id,revision)
    for action in result['actions']:
        action['action_id']=runtime.digest(runtime.encode(dict(revision=revision,identity=action)))
        action['workflow']=states.get(action['action_id'],dict(status='OPEN',row_version=0,latest_note=None,exception_code=None))
    return dict(**result,revision_sha256=revision,sequence=snapshot['sequence'],title=selected.title)


class ActionRequest(BaseModel):
    project_id:str=Field(pattern=r'^[a-z][a-z0-9-]{1,39}$')
    revision_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    action_id:str=Field(pattern=r'^[0-9a-f]{64}$')
    actor:str=Field(min_length=1,max_length=80)
    change:OperatorWorkflowCommand
    model_config=ConfigDict(extra='forbid')


def apply_action(raw):
    runtime.decode(raw)
    try:request=ActionRequest.model_validate_json(raw,strict=True)
    except ValueError:raise runtime.WorkbenchError('ACTION_INVALID') from None
    if not request.actor.strip():raise runtime.WorkbenchError('ACTION_INVALID')
    projected=plan(request.project_id)
    if projected['revision_sha256']!=request.revision_sha256:raise runtime.WorkbenchError('REVISION_CONFLICT')
    selected=next((r for r in projected['actions'] if r['action_id']==request.action_id),None)
    if selected is None:raise runtime.WorkbenchError('ACTION_NOT_FOUND')
    with runtime.connect() as con:
        if _selected(con,request.project_id)['revision_sha256']!=request.revision_sha256:raise runtime.WorkbenchError('REVISION_CONFLICT')
        if con.execute('SELECT COUNT(*) FROM actions').fetchone()[0]>=5000:raise runtime.WorkbenchError('ACTION_LIMIT')
        state=_states(con,request.project_id,request.revision_sha256).get(request.action_id,dict(status='OPEN',row_version=0))
        if state['row_version']!=request.change.expected_version:raise runtime.WorkbenchError('ACTION_VERSION_CONFLICT')
        status=resolve_operator_transition(state['status'],request.change)
        new=dict(action_id=request.action_id,status=status,row_version=state['row_version']+1,latest_note=request.change.note,exception_code=request.change.exception_code if status=='EXCEPTION' else None,updated_by=request.actor.strip(),updated_utc=now())
        if status=='EXCEPTION' and request.change.command=='ADD_NOTE':new['exception_code']=state['exception_code']
        event=dict(command=request.change.command,from_status=state['status'],to_status=status,actor=request.actor.strip(),note=request.change.note,exception_code=request.change.exception_code)
        con.execute('INSERT INTO actions VALUES(?,?,?,?,?,?)',(request.action_id,new['row_version'],request.project_id,request.revision_sha256,runtime.encode(new).decode(),runtime.encode(event).decode()))
    return dict(state=new,local_record_only=True,production_execution_authorized=False)


def revise_order(project_id,path,expected):
    current=show(project_id)
    if current['revision_sha256']!=expected:raise runtime.WorkbenchError('REVISION_CONFLICT')
    raw=runtime.read_bytes(runtime.local_path(path));runtime.decode(raw)
    try:order=project.OSOrderState.model_validate_json(raw,strict=True)
    except ValueError:raise runtime.WorkbenchError('ORDER_INVALID') from None
    current['project']['order_history'].append(order.model_dump(mode='json'))
    return save(runtime.encode(current['project']),expected)


def _csv(rows,columns):
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n');writer.writeheader()
    for row in rows:
        values={key:row.get(key,'') for key in columns}
        for key,value in values.items():
            if type(value) is str and value.lstrip(' \t\r\n').startswith(('=','+','-','@')):values[key]="'"+value
        writer.writerow(values)
    return stream.getvalue().encode('utf-8')


def export(project_id):
    result=plan(project_id);directory=runtime.local_path('reports/'+uuid.uuid4().hex,False)
    rows=[dict(part_number=p['part_number'],**r) for p in result['products'] for r in p['allocation']['orders']]
    data={'plan.json':runtime.encode(result),'orders.csv':_csv(rows,('part_number','order_id','due_date','demand_quantity','covered_quantity','uncovered_quantity','recommended_start_quantity','priority_label','risk_category')),'allocations.csv':_csv(result['actions'],('part_number','order_id','lot_id','kanban','operation','quantity','priority_sort','action_id')),'readiness.csv':_csv(result['shipment_readiness'],('order_id','readiness_state','unshipped_quantity','ready_quantity','production_remaining','independently_verified','shipment_authorized'))}
    if any(len(raw)>runtime.MAX_INPUT for raw in data.values()):raise runtime.WorkbenchError('OUTPUT_LIMIT')
    runtime.mkdir(directory);manifest=dict(format='outlands-planning-report-v1',project_id=project_id,revision_sha256=result['revision_sha256'],external_system_writes=False,files={name:dict(bytes=len(raw),sha256=runtime.digest(raw)) for name,raw in data.items()})
    for name,raw in data.items():runtime.write_new(directory/name,raw)
    runtime.write_new(directory/'manifest.json',runtime.encode(manifest))
    return dict(directory=directory.relative_to(runtime.ROOT).as_posix(),manifest=manifest)


def backup():
    destination=runtime.local_path('backups/'+uuid.uuid4().hex+'.sqlite3',False);runtime.write_new(destination,b'')
    with runtime.connect() as source,runtime.io_errors(),runtime.guarded._store_scope(destination,initial=True):
        target=sqlite3.connect(destination.as_uri()+'?mode=rw',uri=True)
        try:source.backup(target);runtime.validate_schema(target)
        finally:target.close()
    raw=runtime.read_bytes(destination,64*1024*1024)
    return dict(file=destination.relative_to(runtime.ROOT).as_posix(),bytes=len(raw),sha256=runtime.digest(raw))


def demo():
    imported=import_file('inbox/sample-project.json');first=plan('sample-workshop')
    action=first['actions'][0]
    changed=apply_action(runtime.encode(dict(project_id=first['project_id'],revision_sha256=first['revision_sha256'],action_id=action['action_id'],actor='sample_reviewer',change=dict(command='ACKNOWLEDGE',expected_version=0))))
    exported=export('sample-workshop')
    revised=revise_order('sample-workshop','inbox/sample-order-revision.json',first['revision_sha256'])
    final=plan('sample-workshop');backed=backup()
    return dict(mode='FICTIONAL_PLANNING_WORKBENCH_DEMO',products=len(first['products']),initial_remaining_demand=sum(p['remaining_demand'] for p in first['products']),initial_dock_allocated=sum(p['dock_allocated_quantity'] for p in first['products']),initial_covered=sum(p['allocation']['conservation']['covered'] for p in first['products']),initial_uncovered=sum(p['allocation']['conservation']['uncovered'] for p in first['products']),initial_proposed_lots=sum(p['lot_proposal']['recommended_lot_count'] for p in first['products']),action_status=changed['state']['status'],private_report_files=len(exported['manifest']['files']),revisions=revised['sequence'],final_uncovered=sum(p['allocation']['conservation']['uncovered'] for p in final['products']),backup_validated=backed['bytes']>0,external_system_writes=False,lot_ids_reserved=False,shipment_execution_authorized=False)
