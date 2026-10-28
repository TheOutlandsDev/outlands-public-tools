"""Append-only, hash-linked manual assessment history and private handoffs."""
import base64
from contextlib import closing
import sqlite3
import uuid
from . import contracts as c,runtime as r
from .vendor import record_contract as legacy

def _history(con,identifier):
    c.token(identifier);rows=con.execute('SELECT version,sha256,parent_sha256,payload_json FROM revisions WHERE assessment_id=? ORDER BY version LIMIT 66',(identifier,)).fetchall()
    if not rows:raise r.WorkbenchError('ASSESSMENT_NOT_FOUND')
    if len(rows)>c.MAX_REVISIONS:raise r.WorkbenchError('HISTORY_LIMIT')
    previous=None;document=None;result=[]
    for version,pin,parent,raw in rows:
        if version!=len(result)+1 or parent!=previous or len(raw.encode())>r.MAX_INPUT:raise r.WorkbenchError('HISTORY_CHAIN_INVALID')
        payload=r.decode(raw.encode());c.fields(payload,('assessment_id','version','parent_sha256','event','document'))
        if payload['assessment_id']!=identifier or payload['version']!=version or payload['parent_sha256']!=parent or r.digest(r.encode(payload))!=pin:raise r.WorkbenchError('HISTORY_HASH_MISMATCH')
        event=payload['event'];c.fields(event,('operation','actor','reason','data'))
        if version==1:
            if event['operation']!='create':raise r.WorkbenchError('HISTORY_CREATE_REQUIRED')
            c.text(event['actor'],160);c.text(event['reason']);document=c.create(event['data'])
        else:document=c.apply(document,event)
        if document!=payload['document'] or document['assessment_id']!=identifier:raise r.WorkbenchError('HISTORY_REPLAY_MISMATCH')
        result.append(dict(version=version,sha256=pin,parent_sha256=parent,event=event,document=document));previous=pin
    return result

def _append(con,document,event,previous=None):
    version=1 if previous is None else previous['version']+1
    if version>c.MAX_REVISIONS or con.execute('SELECT COUNT(*) FROM revisions').fetchone()[0]>=128:raise r.WorkbenchError('HISTORY_LIMIT')
    parent=previous['sha256'] if previous else None;payload=dict(assessment_id=document['assessment_id'],version=version,parent_sha256=parent,event=event,document=document);raw=r.encode(payload);pin=r.digest(raw)
    con.execute('INSERT INTO revisions VALUES(?,?,?,?,?)',(document['assessment_id'],version,pin,parent,raw.decode()))
    return dict(assessment_id=document['assessment_id'],version=version,sha256=pin)

def create(raw):
    value=r.decode(raw);c.fields(value,('actor','reason','assessment'));c.text(value['actor'],160);c.text(value['reason']);document=c.create(value['assessment'])
    with r.connect() as con:
        if con.execute('SELECT 1 FROM revisions WHERE assessment_id=?',(document['assessment_id'],)).fetchone():raise r.WorkbenchError('ASSESSMENT_EXISTS')
        if con.execute('SELECT COUNT(DISTINCT assessment_id) FROM revisions').fetchone()[0]>=8:raise r.WorkbenchError('ASSESSMENT_LIMIT')
        return _append(con,document,dict(operation='create',actor=value['actor'],reason=value['reason'],data=value['assessment']))

def act(raw):
    value=r.decode(raw);c.fields(value,('assessment_id','expected_sha256','command'));c.hash_value(value['expected_sha256'])
    with r.connect() as con:
        previous=_history(con,value['assessment_id'])[-1]
        if previous['sha256']!=value['expected_sha256']:raise r.WorkbenchError('ASSESSMENT_REVISION_CONFLICT')
        return _append(con,c.apply(previous['document'],value['command']),value['command'],previous)

def assessment(identifier,version=None):
    with r.connect() as con:history=_history(con,identifier)
    if version is not None:c.integer(version,1,len(history))
    selected=history[-1] if version is None else history[version-1];doc=selected['document'];records=doc['legacy_records'];legacy_report=legacy.check_records(records) if records is not None else None
    return dict(assessment_id=identifier,**selected,legacy_report=legacy_report,operator_assertions_unverified=True,execution_performed=False)

def assessments():
    with r.connect() as con:
        ids=[row[0] for row in con.execute('SELECT DISTINCT assessment_id FROM revisions ORDER BY assessment_id LIMIT 9')]
        if len(ids)>8:raise r.WorkbenchError('ASSESSMENT_LIMIT')
        rows=[_history(con,identifier)[-1] for identifier in ids]
    return dict(assessments=[dict(assessment_id=v['document']['assessment_id'],title=v['document']['title'],version=v['version'],sha256=v['sha256'],findings=len(v['document']['findings']),resolved=sum(f['state']=='Resolved' for f in v['document']['findings'])) for v in rows])

def history(identifier):
    with r.connect() as con:rows=_history(con,identifier)
    return dict(assessment_id=identifier,versions=[dict(version=row['version'],sha256=row['sha256'],parent_sha256=row['parent_sha256'],operation=row['event']['operation'],actor=row['event']['actor'],reason=row['event']['reason'],command_sha256=r.digest(r.encode(row['event']))) for row in rows])

def compare(identifier,left,right):
    a=assessment(identifier,left);b=assessment(identifier,right);changes=[]
    for kind in ('submissions','findings','retests'):
        before={v['id']:v for v in a['document'][kind]};after={v['id']:v for v in b['document'][kind]}
        for key in sorted(set(before)|set(after)):
            old=before.get(key);new=after.get(key)
            if old!=new:changes.append(dict(kind=kind,id=key,status='added' if old is None else 'removed' if new is None else 'changed',before_sha256=r.digest(r.encode(old)) if old is not None else None,after_sha256=r.digest(r.encode(new)) if new is not None else None))
    if a['document']['legacy_records']!=b['document']['legacy_records']:changes.append(dict(kind='legacy',status='changed'))
    return dict(left_sha256=a['sha256'],right_sha256=b['sha256'],changes=changes,execution_performed=False)

def export(raw):
    value=r.decode(raw);c.fields(value,('assessment_id','expected_sha256','actor','reason','checks'));c.fields(value['checks'],('quality','privacy','rights','context'));c.text(value['actor'],160);c.text(value['reason']);c.hash_value(value['expected_sha256'])
    if any(type(v) is not bool or not v for v in value['checks'].values()):raise r.WorkbenchError('EXPORT_REVIEW_REQUIRED')
    with r.DATABASE_LOCK:
        selected=assessment(value['assessment_id'])
        if selected['sha256']!=value['expected_sha256']:raise r.WorkbenchError('ASSESSMENT_REVISION_CONFLICT')
        doc=selected['document'];data={'assessment.json':r.encode(selected),'history.json':r.encode(history(value['assessment_id'])),'review.json':r.encode(value)}
        if doc['legacy_records'] is not None:data['legacy-records.json']=r.encode(doc['legacy_records']);data['legacy-report.json']=r.encode(selected['legacy_report'])
        for row in doc['submissions']:data['receipts/'+row['id']+'.bin']=base64.b64decode(row['receipt']['content_base64'],validate=True)
        manifest=dict(format='outlands-private-assessment-export-v1',assessment_id=value['assessment_id'],assessment_sha256=selected['sha256'],version=selected['version'],operator_assertions_unverified=True,execution_performed=False,public_release_authorized=False,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())})
        directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        for name,content in sorted(data.items()):
            target=directory/name
            if not target.parent.exists():r.mkdir(target.parent)
            r.write_new(target,content)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)

def backup():
    target=r.local_path('backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
    with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
        with closing(sqlite3.connect(target)) as destination:
            source.backup(destination);r.validate_schema(destination)
            for row in destination.execute('SELECT DISTINCT assessment_id FROM revisions'):_history(destination,row[0])
    raw=r.read_bytes(target,r.MAX_STORE)
    return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),private_backup=True)

def demo():
    fixture=r.decode(r.read_bytes(r.SOURCE/'examples/sample-assessment.json'));created=create(r.encode(fixture['create']))
    for command in fixture['commands']:created=act(r.encode(dict(assessment_id=created['assessment_id'],expected_sha256=created['sha256'],command=command)))
    selected=assessment(created['assessment_id']);exported=export(r.encode(dict(assessment_id=created['assessment_id'],expected_sha256=created['sha256'],actor='sample_reviewer',reason='Fictional private handoff',checks=dict(quality=True,privacy=True,rights=True,context=True))));saved=backup()
    return dict(mode='FICTIONAL_ASSESSMENT_MANAGEMENT_DEMO',versions=created['version'],submissions=len(selected['document']['submissions']),finding_state=selected['document']['findings'][0]['state'],legacy_closure_claim_unverified=selected['legacy_report']['outcomes_verified'] is False,private_export_files=len(exported['manifest']['files'])+1,backup_validated=saved['bytes']>0,execution_performed=False,external_services_used=False)
