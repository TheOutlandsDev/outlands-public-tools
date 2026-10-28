"""Replay-checked private recordings, acknowledgements and reviewed handoffs."""
from contextlib import closing
import copy
import csv
import io
import sqlite3
import uuid
from . import contracts as c,engine,runtime as r

def _apply(document,event):
    c.fields(event,('operation','actor','reason','data'));c.text(event['actor'],160);c.text(event['reason']);op=c.choice(event['operation'],('ingest','acknowledge'))
    if op=='ingest':
        c.fields(event['data'],('snapshots',));return c.append(document,event['data']['snapshots'])
    data=c.acknowledgement(event['data'])
    if data['actor']!=event['actor'] or data['reason']!=event['reason']:c.fail('ACKNOWLEDGEMENT_ACTOR_MISMATCH')
    if len(document['acknowledgements'])>=64:c.fail('ACKNOWLEDGEMENT_LIMIT')
    incident=next((row for row in engine.analyse(document)['incidents'] if row['incident_id']==data['incident_id']),None)
    if incident is None:c.fail('INCIDENT_NOT_FOUND')
    if incident['state']=='resolved':c.fail('INCIDENT_ALREADY_RESOLVED')
    if (incident['episode'],incident['escalations'])!=(data['expected_episode'],data['expected_escalations']):c.fail('INCIDENT_REVISION_CONFLICT')
    doc=copy.deepcopy(document);doc['acknowledgements'].append(dict(**data,snapshot_count=len(doc['snapshots'])));c.bounded(doc);return doc

def _initial(event):
    c.fields(event,('operation','actor','reason','data'));c.text(event['actor'],160);c.text(event['reason']);op=c.choice(event['operation'],('create','import'))
    c.fields(event['data'],('case',) if op=='create' else ('case','snapshots'))
    document=c.create(event['data']['case'])
    return c.append(document,event['data']['snapshots']) if op=='import' else document

def _history(con,identifier):
    c.token(identifier);rows=con.execute('SELECT version,sha256,parent_sha256,payload_json FROM revisions WHERE case_id=? ORDER BY version LIMIT 66',(identifier,)).fetchall()
    if not rows:c.fail('CASE_NOT_FOUND')
    if len(rows)>c.MAX_REVISIONS:c.fail('HISTORY_LIMIT')
    previous=None;document=None;result=[]
    for version,pin,parent,raw in rows:
        if type(version) is not int or version!=len(result)+1 or parent!=previous or type(raw) is not str or len(raw.encode())>r.MAX_INPUT:c.fail('HISTORY_CHAIN_INVALID')
        payload=r.decode(raw.encode());c.fields(payload,('case_id','version','parent_sha256','event','document'))
        if payload['case_id']!=identifier or type(payload['version']) is not int or payload['version']!=version or payload['parent_sha256']!=parent or r.digest(r.encode(payload))!=pin:c.fail('HISTORY_HASH_MISMATCH')
        document=_initial(payload['event']) if version==1 else _apply(document,payload['event'])
        if r.encode(document)!=r.encode(payload['document']) or document['case_id']!=identifier:c.fail('HISTORY_REPLAY_MISMATCH')
        result.append(dict(version=version,sha256=pin,parent_sha256=parent,event=payload['event'],document=document));previous=pin
    return result

def _append(con,document,event,previous=None):
    version=previous['version']+1 if previous else 1
    if version>c.MAX_REVISIONS or con.execute('SELECT COUNT(*) FROM revisions').fetchone()[0]>=128:c.fail('HISTORY_LIMIT')
    parent=previous['sha256'] if previous else None;payload=dict(case_id=document['case_id'],version=version,parent_sha256=parent,event=event,document=document);raw=r.encode(payload)
    if len(raw)>r.MAX_INPUT:c.fail('REVISION_SIZE_LIMIT')
    pin=r.digest(raw);con.execute('INSERT INTO revisions VALUES(?,?,?,?,?)',(document['case_id'],version,pin,parent,raw.decode()))
    return dict(case_id=document['case_id'],version=version,sha256=pin)

def create(raw,imported=False):
    value=r.decode(raw);c.fields(value,('actor','reason','case','snapshots') if imported else ('actor','reason','case'))
    event=dict(operation='import' if imported else 'create',actor=value['actor'],reason=value['reason'],data={k:v for k,v in value.items() if k not in ('actor','reason')});document=_initial(event)
    with r.connect() as con:
        if con.execute('SELECT 1 FROM revisions WHERE case_id=?',(document['case_id'],)).fetchone():c.fail('CASE_EXISTS')
        if con.execute('SELECT COUNT(DISTINCT case_id) FROM revisions').fetchone()[0]>=8:c.fail('CASE_LIMIT')
        return _append(con,document,event)

def act(raw):
    value=r.decode(raw);c.fields(value,('case_id','expected_sha256','command'));c.hash_value(value['expected_sha256'])
    with r.connect() as con:
        previous=_history(con,value['case_id'])[-1]
        if previous['sha256']!=value['expected_sha256']:c.fail('CASE_REVISION_CONFLICT')
        document=_apply(previous['document'],value['command']);return _append(con,document,value['command'],previous)

def case(identifier,version=None):
    with r.connect() as con:history=_history(con,identifier)
    if version is not None:c.integer(version,1,len(history))
    row=history[-1] if version is None else history[version-1]
    return dict(case_id=identifier,**row,report=engine.analyse(row['document']),operator_assertions_unverified=True)

def cases():
    with r.connect() as con:
        identifiers=[row[0] for row in con.execute('SELECT DISTINCT case_id FROM revisions ORDER BY case_id LIMIT 9')]
        if len(identifiers)>8:c.fail('CASE_LIMIT')
        rows=[_history(con,identifier)[-1] for identifier in identifiers]
    return dict(cases=[dict(case_id=row['document']['case_id'],title=row['document']['title'],version=row['version'],sha256=row['sha256'],snapshots=len(row['document']['snapshots'])) for row in rows])

def history(identifier):
    with r.connect() as con:rows=_history(con,identifier)
    return dict(case_id=identifier,versions=[dict(version=row['version'],sha256=row['sha256'],parent_sha256=row['parent_sha256'],operation=row['event']['operation'],actor=row['event']['actor'],reason=row['event']['reason'],command_sha256=r.digest(r.encode(row['event']))) for row in rows])

def compare(identifier,left,right):
    a=case(identifier,left);b=case(identifier,right);before={row['incident_id']:row for row in a['report']['incidents']};after={row['incident_id']:row for row in b['report']['incidents']};changes=[]
    for key in sorted(set(before)|set(after)):
        old=before.get(key);new=after.get(key)
        if old!=new:changes.append(dict(incident_id=key,status='added' if old is None else 'removed' if new is None else 'changed',before_state=old['state'] if old else None,after_state=new['state'] if new else None,before_sha256=r.digest(r.encode(old)) if old else None,after_sha256=r.digest(r.encode(new)) if new else None))
    return dict(left_sha256=a['sha256'],right_sha256=b['sha256'],left_snapshots=a['report']['snapshots'],right_snapshots=b['report']['snapshots'],changes=changes,left_availability=a['report']['availability'],right_availability=b['report']['availability'],windows_may_differ=True)

def _csv(headers,rows):
    buffer=io.StringIO(newline='');writer=csv.writer(buffer,lineterminator='\n');writer.writerow(headers)
    for row in rows:
        cells=[]
        for value in row:
            cell='' if value is None else str(value)
            if cell.lstrip().startswith(('=','+','-','@')) or cell.startswith(('\t','\r','\n')):cell="'"+cell
            cells.append(cell)
        writer.writerow(cells)
    return buffer.getvalue().encode('utf-8')

def export(raw):
    value=r.decode(raw);c.fields(value,('case_id','expected_sha256','actor','reason','checks'));c.fields(value['checks'],('quality','privacy','rights','context'));c.text(value['actor'],160);c.text(value['reason']);c.hash_value(value['expected_sha256'])
    if any(type(v) is not bool or not v for v in value['checks'].values()):c.fail('EXPORT_REVIEW_REQUIRED')
    with r.DATABASE_LOCK:
        selected=case(value['case_id'])
        if selected['sha256']!=value['expected_sha256']:c.fail('CASE_REVISION_CONFLICT')
        report=selected['report'];doc=selected['document'];recording=dict(actor=value['actor'],reason=value['reason'],case={k:doc[k] for k in ('case_id','title','policy','services','maintenance')},snapshots=doc['snapshots'])
        data={'case.json':r.encode(selected),'recording.json':r.encode(recording),'report.json':r.encode(report),'history.json':r.encode(history(value['case_id'])),'review.json':r.encode(value)}
        headers=('service_id','signal_id','kind','state','severity','episode','occurrences','clean_count','held','acknowledged');data['incidents.csv']=_csv(headers,([row[k] for k in headers] for row in report['incidents']))
        headers=('snapshot_id','at','service_id','status','maintenance_id','fresh_signals','required_signals');data['timeline.csv']=_csv(headers,([row[k] for k in headers] for row in report['timeline']))
        headers=('service_id',*engine.BUCKETS,'healthy_fraction_of_known_seconds','observation_coverage_fraction');data['availability.csv']=_csv(headers,([row['service_id'],*[row['seconds'][k] for k in engine.BUCKETS],row['healthy_fraction_of_known_seconds'],row['observation_coverage_fraction']] for row in report['availability']['services']))
        manifest=dict(format='outlands-private-reliability-export-v1',case_id=value['case_id'],case_sha256=selected['sha256'],version=selected['version'],public_release_authorized=False,observations_independently_verified=False,execution_performed=False,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())})
        directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        for name,content in sorted(data.items()):r.write_new(directory/name,content)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)

def backup():
    target=r.local_path('backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
    with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
        with closing(sqlite3.connect(target)) as destination:
            source.backup(destination);r.validate_schema(destination)
            for row in destination.execute('SELECT DISTINCT case_id FROM revisions'):_history(destination,row[0])
    raw=r.read_bytes(target,r.MAX_STORE);return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),private_backup=True)

def demo():
    recording=r.decode(r.read_bytes(r.SOURCE/'examples/sample-recording.json'));saved=create(r.encode(recording),imported=True);selected=case(saved['case_id']);incident=next(row for row in selected['report']['incidents'] if row['kind']=='health' and row['state']=='active');actor='sample_reviewer';reason='Fictional incident acknowledged; no live action'
    saved=act(r.encode(dict(case_id=saved['case_id'],expected_sha256=saved['sha256'],command=dict(operation='acknowledge',actor=actor,reason=reason,data=dict(incident_id=incident['incident_id'],expected_episode=incident['episode'],expected_escalations=incident['escalations'],actor=actor,reason=reason)))))
    exported=export(r.encode(dict(case_id=saved['case_id'],expected_sha256=saved['sha256'],actor=actor,reason='Fictional private handoff',checks=dict(quality=True,privacy=True,rights=True,context=True))));saved_backup=backup();report=case(saved['case_id'])['report'];availability=report['availability']['services'][0]
    return dict(mode='FICTIONAL_RELIABILITY_DEMO',snapshots=report['snapshots'],incident_counts=report['counts'],reopened_health_episode=next(row['episode'] for row in report['incidents'] if row['kind']=='health'),acknowledged_health_incidents=sum(row['acknowledged'] for row in report['incidents'] if row['kind']=='health'),seconds=availability['seconds'],tail_extrapolated=False,private_export_files=len(exported['manifest']['files'])+1,backup_validated=saved_backup['bytes']>0,execution_performed=False,network_probed=False)
