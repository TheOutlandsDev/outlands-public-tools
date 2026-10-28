"""Private scenario revisions, atomic event identities, comparison and review."""
import csv
from datetime import datetime,timezone
from email.message import EmailMessage
from email.policy import SMTP
import io
import sqlite3
import uuid
from . import contracts as c,runtime
from .engines import capacity,process,inventory,dispatch,events


def calculate(value):
    return dict(mode='LOCAL_ADVISORY_ANALYTICS',project_id=value['project_id'],title=value['title'],snapshot_utc=value['snapshot_utc'],capacity=[capacity.calculate(r) for r in value['capacity']],process=[process.calculate(r) for r in value['process']],inventory=[inventory.calculate(r,value['snapshot_utc']) for r in value['inventory']],dispatch=dispatch.calculate(value['dispatch']),snapshot=events.calculate(value),planning_reference=value.get('planning_reference'),external_system_writes=False,production_execution_authorized=False,purchase_authorized=False)


def _hash(project_id,sequence,parent,value):return runtime.digest(runtime.encode(dict(project_id=project_id,sequence=sequence,parent=parent,scenario=value)))


def _selected(con,project_id,sequence=None):
    c.token(project_id)
    if sequence is not None:c.integer(sequence,1,200)
    query='SELECT sequence,revision_sha256,parent_sha256,substr(scenario_json,1,?),length(CAST(scenario_json AS BLOB)) FROM revisions WHERE project_id=?'
    params=[runtime.MAX_INPUT+1,project_id]
    if sequence is not None:query+=' AND sequence=?';params.append(sequence)
    row=con.execute(query+' ORDER BY sequence DESC LIMIT 1',params).fetchone()
    if row is None:raise runtime.WorkbenchError('SCENARIO_NOT_FOUND')
    seq,sha,parent,text,length=row
    if length>runtime.MAX_INPUT:raise runtime.WorkbenchError('STORE_RECORD_LIMIT')
    value=c.scenario(text.encode())
    if value['project_id']!=project_id or _hash(project_id,seq,parent,value)!=sha:raise runtime.WorkbenchError('REVISION_HASH_MISMATCH')
    return dict(sequence=seq,revision_sha256=sha,parent_sha256=parent,scenario=value)


def show(project_id,sequence=None):
    with runtime.connect() as con:return _selected(con,project_id,sequence)


def projects():
    with runtime.connect() as con:
        rows=con.execute('SELECT project_id,MAX(sequence) FROM revisions GROUP BY project_id ORDER BY project_id LIMIT 101').fetchall()
        if len(rows)>100:raise runtime.WorkbenchError('PROJECT_LIMIT')
        return dict(projects=[dict(project_id=r[0],revisions=r[1]) for r in rows])


def save(raw,expected=None):
    value=c.scenario(raw);calculate(value);encoded=runtime.encode(value)
    if len(encoded)>runtime.MAX_INPUT:raise runtime.WorkbenchError('SCENARIO_LIMIT')
    project_id=value['project_id']
    with runtime.connect() as con:
        present=con.execute('SELECT 1 FROM revisions WHERE project_id=?',(project_id,)).fetchone()
        if present:
            old=_selected(con,project_id)
            if expected!=old['revision_sha256']:raise runtime.WorkbenchError('REVISION_CONFLICT')
            if old['scenario']==value:return dict(project_id=project_id,sequence=old['sequence'],revision_sha256=expected,created=False,inserted_events=0)
            sequence=old['sequence']+1;parent=expected
        else:
            if expected is not None:raise runtime.WorkbenchError('REVISION_CONFLICT')
            if con.execute('SELECT COUNT(DISTINCT project_id) FROM revisions').fetchone()[0]>=100:raise runtime.WorkbenchError('PROJECT_LIMIT')
            sequence=1;parent=None
        if sequence>200:raise runtime.WorkbenchError('REVISION_LIMIT')
        inserted=0
        for event in value['completions']:
            raw_event=runtime.encode(event);sha=runtime.digest(raw_event)
            existing=con.execute('SELECT payload_sha256 FROM completion_events WHERE project_id=? AND source=? AND event_id=?',(project_id,event['source'],event['event_id'])).fetchone()
            if existing:
                if existing[0]!=sha:raise runtime.WorkbenchError('EVENT_IDENTITY_CONFLICT')
            else:
                con.execute('INSERT INTO completion_events VALUES(?,?,?,?,?)',(project_id,event['source'],event['event_id'],sha,raw_event.decode()));inserted+=1
        if con.execute('SELECT COUNT(*) FROM completion_events').fetchone()[0]>10000:raise runtime.WorkbenchError('EVENT_STORE_LIMIT')
        revision=_hash(project_id,sequence,parent,value)
        con.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?)',(project_id,sequence,revision,parent,encoded.decode(),datetime.now(timezone.utc).isoformat()))
    return dict(project_id=project_id,sequence=sequence,revision_sha256=revision,created=True,inserted_events=inserted)


def import_file(path,expected=None):return save(runtime.read_bytes(runtime.local_path(path)),expected)


def ingest(project_id,path,expected):
    snapshot=show(project_id)
    if snapshot['revision_sha256']!=expected:raise runtime.WorkbenchError('REVISION_CONFLICT')
    batch=runtime.decode(runtime.read_bytes(runtime.local_path(path)));c.rows(batch,2000)
    selected={(r['source'],r['event_id']):r for r in snapshot['scenario']['completions']}
    for raw in batch:
        row=events.event(raw);key=(row['source'],row['event_id'])
        if key in selected and selected[key]!=row:raise runtime.WorkbenchError('EVENT_IDENTITY_CONFLICT')
        selected[key]=row
    snapshot['scenario']['completions']=list(selected.values())
    return save(runtime.encode(snapshot['scenario']),expected)


def history(project_id):
    c.token(project_id)
    with runtime.connect() as con:rows=con.execute('SELECT sequence,revision_sha256,parent_sha256,created_utc FROM revisions WHERE project_id=? ORDER BY sequence LIMIT 201',(project_id,)).fetchall()
    return dict(project_id=project_id,revisions=[dict(sequence=r[0],revision_sha256=r[1],parent_sha256=r[2],created_utc=r[3]) for r in rows])


def plan(project_id,sequence=None):
    snapshot=show(project_id,sequence);result=calculate(snapshot['scenario'])
    with runtime.connect() as con:
        rows=con.execute('SELECT payload_json FROM (SELECT payload_json,ROW_NUMBER() OVER(PARTITION BY domain,case_id ORDER BY row_version DESC) AS rank FROM reviews WHERE revision_sha256=?) WHERE rank=1 LIMIT 2001',(snapshot['revision_sha256'],)).fetchall()
    if len(rows)>2000:raise runtime.WorkbenchError('REVIEW_LIMIT')
    return dict(**result,sequence=snapshot['sequence'],revision_sha256=snapshot['revision_sha256'],reviews=[runtime.decode(r[0].encode()) for r in rows])


def compare(project_id,left,right):
    a=plan(project_id,c.integer(left,1,200));b=plan(project_id,c.integer(right,1,200));changes=[];added=[];removed=[]
    for domain in ('capacity','process','inventory'):
        before={r['id']:r for r in a[domain]};after={r['id']:r for r in b[domain]}
        added.extend(dict(domain=domain,id=key) for key in sorted(set(after)-set(before)))
        removed.extend(dict(domain=domain,id=key) for key in sorted(set(before)-set(after)))
        for key in sorted(set(before)&set(after)):
            for metric in sorted(set(before[key])&set(after[key])):
                x,y=before[key][metric],after[key][metric]
                if type(x) in (int,float) and type(y) in (int,float):changes.append(dict(domain=domain,id=key,metric=metric,before=x,after=y,delta=y-x))
                elif x is None or y is None:changes.append(dict(domain=domain,id=key,metric=metric,before=x,after=y,delta=None))
    before={r['id']:r for r in a['dispatch']['ranked']+a['dispatch']['blocked']};after={r['id']:r for r in b['dispatch']['ranked']+b['dispatch']['blocked']}
    added.extend(dict(domain='dispatch',id=key) for key in sorted(set(after)-set(before)));removed.extend(dict(domain='dispatch',id=key) for key in sorted(set(before)-set(after)))
    eligibility=[dict(id=key,before=before[key]['eligible'],after=after[key]['eligible']) for key in sorted(set(before)&set(after)) if before[key]['eligible']!=after[key]['eligible']]
    for key in sorted(set(before)&set(after)):
        if before[key]['eligible'] and after[key]['eligible']:changes.append(dict(domain='dispatch',id=key,metric='priority_score',before=before[key]['priority_score'],after=after[key]['priority_score'],delta=after[key]['priority_score']-before[key]['priority_score']))
    return dict(project_id=project_id,left_revision=a['revision_sha256'],right_revision=b['revision_sha256'],changes=changes,added_cases=added,removed_cases=removed,eligibility_changes=eligibility,dispatch_policy_before=a['dispatch']['policy_id'],dispatch_policy_after=b['dispatch']['policy_id'],completion_units_before=a['snapshot']['completed_units'],completion_units_after=b['snapshot']['completed_units'],window_before={k:v for k,v in a['snapshot'].items() if k.startswith('window_')},window_after={k:v for k,v in b['snapshot'].items() if k.startswith('window_')},assumptions_not_optimized=True)


def review(raw):
    value=runtime.decode(raw);c.fields(value,('project_id','revision_sha256','domain','case_id','expected_version','status','actor','note'))
    c.token(value['case_id']);c.integer(value['expected_version'],0,1000);c.text(value['actor'],80);c.text(value['note'],1000)
    if value['status'] not in ('noted','needs_review','reviewed'):raise runtime.WorkbenchError('REVIEW_INVALID')
    latest=plan(value['project_id'])
    if latest['revision_sha256']!=value['revision_sha256']:raise runtime.WorkbenchError('REVISION_CONFLICT')
    if value['domain'] in ('capacity','process','inventory'):selected=latest[value['domain']]
    elif value['domain']=='dispatch':selected=latest['dispatch']['ranked']+latest['dispatch']['blocked']
    else:raise runtime.WorkbenchError('REVIEW_DOMAIN_INVALID')
    if value['case_id'] not in {r['id'] for r in selected}:raise runtime.WorkbenchError('REVIEW_CASE_NOT_FOUND')
    with runtime.connect() as con:
        if _selected(con,value['project_id'])['revision_sha256']!=value['revision_sha256']:raise runtime.WorkbenchError('REVISION_CONFLICT')
        row=con.execute('SELECT MAX(row_version) FROM reviews WHERE revision_sha256=? AND domain=? AND case_id=?',(value['revision_sha256'],value['domain'],value['case_id'])).fetchone()
        if (row[0] or 0)!=value['expected_version']:raise runtime.WorkbenchError('REVIEW_VERSION_CONFLICT')
        if con.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]>=5000:raise runtime.WorkbenchError('REVIEW_LIMIT')
        result={k:v for k,v in value.items() if k!='expected_version'};result['row_version']=value['expected_version']+1
        con.execute('INSERT INTO reviews VALUES(?,?,?,?,?)',(value['revision_sha256'],value['domain'],value['case_id'],result['row_version'],runtime.encode(result).decode()))
    return dict(review=result,local_assertion_only=True)


def attach_planning(project_id,directory,expected):
    from .planning_report import read
    snapshot=show(project_id)
    if snapshot['revision_sha256']!=expected:raise runtime.WorkbenchError('REVISION_CONFLICT')
    snapshot['scenario']['planning_reference']=read(directory)
    return save(runtime.encode(snapshot['scenario']),expected)


def _csv(rows):
    columns=sorted({k for row in rows for k,v in row.items() if type(v) not in (dict,list,tuple)})
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n');writer.writeheader()
    for row in rows:
        cleaned={key:row.get(key) for key in columns}
        for key,value in cleaned.items():
            if type(value) is str and value.lstrip(' \t\r\n').startswith(('=','+','-','@')):cleaned[key]="'"+value
        writer.writerow(cleaned)
    return stream.getvalue().encode('utf-8')


def export(project_id):
    result=plan(project_id);directory=runtime.local_path('reports/'+uuid.uuid4().hex,False)
    data={'analytics.json':runtime.encode(result),'capacity.csv':_csv(result['capacity']),'process.csv':_csv(result['process']),'inventory.csv':_csv(result['inventory']),'dispatch.csv':_csv(result['dispatch']['ranked']+result['dispatch']['blocked']),'snapshot.csv':_csv([dict(completed_units=result['snapshot']['completed_units'],completion_events=result['snapshot']['completion_events'],active_units=result['snapshot']['active_units'])])}
    draft=EmailMessage(policy=SMTP);draft['From']='sample-outbox@example.invalid';draft['To']='sample-reader@example.invalid';draft['Subject']='Fictional-address analytics draft';draft['Date']='Tue, 01 Jan 2030 00:00:00 +0000';draft.set_content('PRIVATE LOCAL REPORT DRAFT\nRevision: '+result['revision_sha256']+'\nCompleted units: '+str(result['snapshot']['completed_units'])+'\nNo mail was sent.\n');data['summary.eml']=draft.as_bytes()
    if any(len(raw)>runtime.MAX_INPUT for raw in data.values()):raise runtime.WorkbenchError('OUTPUT_LIMIT')
    manifest=dict(format='outlands-analytics-report-v1',project_id=project_id,revision_sha256=result['revision_sha256'],files={name:dict(bytes=len(raw),sha256=runtime.digest(raw)) for name,raw in data.items()},mail_sent=False)
    runtime.mkdir(directory)
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
    first=import_file('inbox/sample-scenario.json');a=plan('sample-operations')
    review(runtime.encode(dict(project_id='sample-operations',revision_sha256=first['revision_sha256'],domain='capacity',case_id='base',expected_version=0,status='reviewed',actor='sample_reviewer',note='Fictional assumption review')))
    exported=export('sample-operations');second=ingest('sample-operations','inbox/sample-events.json',first['revision_sha256']);b=plan('sample-operations')
    again=ingest('sample-operations','inbox/sample-events.json',second['revision_sha256']);backup_result=backup()
    return dict(mode='FICTIONAL_OPERATIONS_ANALYTICS_DEMO',capacity=a['capacity'][0]['whole_unit_capacity'],minimum_people=a['capacity'][0]['minimum_people_under_assumptions'],oee=a['process'][0]['oee_fraction'],p90=a['process'][0]['p90_minutes_linear_interpolation'],reorder_units=a['inventory'][0]['proposed_order_units'],eligible_dispatch=len(a['dispatch']['ranked']),blocked_dispatch=len(a['dispatch']['blocked']),initial_completions=a['snapshot']['completed_units'],final_completions=b['snapshot']['completed_units'],revision=second['sequence'],replay_created_revision=again['created'],private_report_files=len(exported['manifest']['files']),backup_validated=backup_result['bytes']>0,external_system_writes=False,mail_sent=False)
