"""Immutable case registry, explicit execution trust and independently reviewed evidence."""
import base64
import html
import re
import sqlite3
import uuid
from . import contracts as c,jobs,runtime as r


def _revision(con,identifier,version=None):
    c.token(identifier);params=[identifier];sql='SELECT version,case_sha256,parent_sha256,definition_json FROM cases WHERE case_id=?'
    if version is not None:c.integer(version,1,100);sql+=' AND version=?';params.append(version)
    row=con.execute(sql+' ORDER BY version DESC LIMIT 1',params).fetchone()
    if row is None:raise r.WorkbenchError('CASE_NOT_FOUND')
    definition=c.definition(r.decode(row[3].encode()));payload=dict(version=row[0],parent_sha256=row[2],definition=definition)
    if definition['case_id']!=identifier or r.digest(r.encode(payload))!=row[1]:raise r.WorkbenchError('CASE_HASH_MISMATCH')
    return dict(**payload,sha256=row[1])


def _save(con,definition,expected):
    identifier=definition['case_id'];exists=con.execute('SELECT 1 FROM cases WHERE case_id=?',(identifier,)).fetchone();old=_revision(con,identifier) if exists else None
    if expected!=(old['sha256'] if old else None):raise r.WorkbenchError('CASE_REVISION_CONFLICT')
    if old and old['definition']==definition:return dict(case_id=identifier,version=old['version'],case_sha256=old['sha256'],created=False)
    if old is None and con.execute('SELECT COUNT(DISTINCT case_id) FROM cases').fetchone()[0]>=100:raise r.WorkbenchError('CASE_LIMIT')
    version=old['version']+1 if old else 1
    if version>100:raise r.WorkbenchError('REVISION_LIMIT')
    payload=dict(version=version,parent_sha256=expected,definition=definition);sha=r.digest(r.encode(payload));con.execute('INSERT INTO cases VALUES(?,?,?,?,?)',(identifier,version,sha,expected,r.encode(definition).decode()))
    return dict(case_id=identifier,version=version,case_sha256=sha,created=True)


def save_case(raw):
    value=r.decode(raw);c.fields(value,('definition','expected_sha256'))
    if value['expected_sha256'] is not None:c.hash_value(value['expected_sha256'])
    definition=c.definition(value['definition'])
    with r.connect() as con:return _save(con,definition,value['expected_sha256'])


def import_bundle(raw):
    definitions=c.bundle(raw);results=[]
    with r.connect() as con:
        for definition in definitions:
            exists=con.execute('SELECT 1 FROM cases WHERE case_id=?',(definition['case_id'],)).fetchone();old=_revision(con,definition['case_id']) if exists else None
            if old and old['definition']!=definition:raise r.WorkbenchError('CASE_ID_EXISTS')
            results.append(_save(con,definition,old['sha256'] if old else None))
    return dict(cases=results,executed=False)


def _trust(con,sha):
    row=con.execute('SELECT payload_json FROM trusts WHERE case_sha256=? ORDER BY row_version DESC LIMIT 1',(sha,)).fetchone()
    return r.decode(row[0].encode()) if row else dict(status='pending',row_version=0)


def cases():
    with r.connect() as con:
        ids=con.execute('SELECT case_id FROM cases GROUP BY case_id ORDER BY case_id LIMIT 101').fetchall();values=[_revision(con,row[0]) for row in ids]
        if len(values)>100:raise r.WorkbenchError('CASE_LIMIT')
        return dict(cases=[dict(case_id=v['definition']['case_id'],title=v['definition']['title'],version=v['version'],sha256=v['sha256'],trust=_trust(con,v['sha256'])) for v in values])


def case(identifier,version=None):
    with r.connect() as con:value=_revision(con,identifier,version);value['trust']=_trust(con,value['sha256'])
    return value


def history(identifier):
    c.token(identifier)
    with r.connect() as con:rows=con.execute('SELECT version,case_sha256,parent_sha256 FROM cases WHERE case_id=? ORDER BY version LIMIT 101',(identifier,)).fetchall()
    return dict(case_id=identifier,versions=[dict(version=row[0],sha256=row[1],parent_sha256=row[2]) for row in rows])


def trust(raw):
    value=r.decode(raw);c.fields(value,('case_id','case_sha256','expected_version','status','actor','note','checks'));c.hash_value(value['case_sha256']);c.integer(value['expected_version'],0,1000);c.text(value['actor'],80);c.text(value['note'],1000,empty=True);c.fields(value['checks'],('code_reviewed','authority','input_reviewed','effects_reviewed'))
    if value['status'] not in ('approved','revoked') or any(type(v) is not bool for v in value['checks'].values()):raise r.WorkbenchError('TRUST_INVALID')
    if value['status']=='approved' and not all(value['checks'].values()):raise r.WorkbenchError('TRUST_CHECKS_REQUIRED')
    with r.connect() as con:
        revision=_revision(con,value['case_id'])
        if revision['sha256']!=value['case_sha256']:raise r.WorkbenchError('CASE_REVISION_CONFLICT')
        old=_trust(con,revision['sha256'])
        if old['row_version']!=value['expected_version']:raise r.WorkbenchError('TRUST_VERSION_CONFLICT')
        if con.execute('SELECT COUNT(*) FROM trusts').fetchone()[0]>=5000:raise r.WorkbenchError('TRUST_LIMIT')
        payload={key:item for key,item in value.items() if key!='expected_version'};payload['row_version']=old['row_version']+1;con.execute('INSERT INTO trusts VALUES(?,?,?)',(revision['sha256'],payload['row_version'],r.encode(payload).decode()))
    return dict(trust=payload,executed=False,operator_assertions_unverified=True)


def _finish(snapshots,result):
    identifier=uuid.uuid4().hex;payload=dict(format='outlands-test-evidence-v1',artifact_id=identifier,suite=snapshots,result=result);raw=r.encode(payload)
    if len(raw)>3*1024*1024:raise r.WorkbenchError('ARTIFACT_SIZE_LIMIT')
    sha=r.digest(raw)
    with r.connect() as con:
        if con.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0]>=200:raise r.WorkbenchError('ARTIFACT_LIMIT')
        con.execute('INSERT INTO artifacts VALUES(?,?,?)',(identifier,sha,raw.decode()))
    return dict(artifact_id=identifier,artifact_sha256=sha,status=result['status'],saved=True)


def start_run(raw):
    request=c.suite(raw);snapshots=[]
    # Validate the entire suite before any script is materialized or started.
    with r.connect() as con:
        if con.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0]>=200:raise r.WorkbenchError('ARTIFACT_LIMIT')
        for item in request['cases']:
            revision=_revision(con,item['case_id'])
            if revision['sha256']!=item['expected_sha256']:raise r.WorkbenchError('CASE_REVISION_CONFLICT')
            approval=_trust(con,revision['sha256'])
            if approval['status']!='approved':raise r.WorkbenchError('EXECUTION_TRUST_REQUIRED')
            if approval['row_version']!=item['trust_version']:raise r.WorkbenchError('TRUST_VERSION_CONFLICT')
            snapshots.append(dict(case_id=item['case_id'],version=revision['version'],case_sha256=revision['sha256'],definition=revision['definition'],trust_at_start=approval))
    def task(control):
        results=[]
        for snapshot in snapshots:
            before=len(control.children)
            try:observed=control.execute(snapshot['definition'])
            except Exception:observed=dict(status='refused',reason='RUNNER_REFUSED',owned_child_started=len(control.children)>before,passed=False)
            results.append(dict(case_id=snapshot['case_id'],case_sha256=snapshot['case_sha256'],observed=observed))
        attempted=sum(v['observed']['owned_child_started'] for v in results);matched=sum(v['observed'].get('passed',False) for v in results);complete=not control.cancelled.is_set() and all(v['observed']['status']!='not_run' for v in results)
        return dict(status='completed' if complete else 'cancelled',complete=complete,planned=len(snapshots),attempted=attempted,matched=matched,unmatched=attempted-matched,not_started=len(snapshots)-attempted,cases=results,scope='Owned trusted Python children only; no descendant containment or sandbox')
    return jobs.start(task,lambda result:_finish(snapshots,result))


def _artifact(con,identifier):
    if type(identifier) is not str or not re.fullmatch('[0-9a-f]{32}',identifier):raise r.WorkbenchError('ARTIFACT_ID_INVALID')
    row=con.execute('SELECT artifact_sha256,payload_json FROM artifacts WHERE artifact_id=?',(identifier,)).fetchone()
    if row is None:raise r.WorkbenchError('ARTIFACT_NOT_FOUND')
    payload=r.decode(row[1].encode())
    if payload['artifact_id']!=identifier or r.digest(r.encode(payload))!=row[0]:raise r.WorkbenchError('ARTIFACT_HASH_MISMATCH')
    return dict(artifact_id=identifier,artifact_sha256=row[0],payload=payload)


def artifacts():
    with r.connect() as con:ids=con.execute('SELECT artifact_id FROM artifacts ORDER BY rowid DESC LIMIT 201').fetchall();values=[_artifact(con,row[0]) for row in ids]
    return dict(artifacts=[dict(artifact_id=v['artifact_id'],status=v['payload']['result']['status'],planned=v['payload']['result']['planned'],matched=v['payload']['result']['matched']) for v in values])


def artifact(identifier):
    with r.connect() as con:value=_artifact(con,identifier);row=con.execute('SELECT payload_json FROM reviews WHERE artifact_sha256=? ORDER BY row_version DESC LIMIT 1',(value['artifact_sha256'],)).fetchone();value['review']=r.decode(row[0].encode()) if row else dict(status='pending',row_version=0)
    return value


def review(raw):
    value=r.decode(raw);c.fields(value,('artifact_id','artifact_sha256','expected_version','status','actor','note','checks'));c.hash_value(value['artifact_sha256']);c.integer(value['expected_version'],0,1000);c.text(value['actor'],80);c.text(value['note'],1000,empty=True);c.fields(value['checks'],('quality','privacy','rights','context'))
    if value['status'] not in ('pending','approved','rejected') or any(type(v) is not bool for v in value['checks'].values()):raise r.WorkbenchError('REVIEW_INVALID')
    if value['status']=='approved' and not all(value['checks'].values()):raise r.WorkbenchError('REVIEW_CHECKS_REQUIRED')
    with r.connect() as con:
        record=_artifact(con,value['artifact_id'])
        if record['artifact_sha256']!=value['artifact_sha256']:raise r.WorkbenchError('ARTIFACT_CONFLICT')
        if value['status']=='approved' and not record['payload']['result']['complete']:raise r.WorkbenchError('REVIEW_REQUIRES_COMPLETE_EVIDENCE')
        row=con.execute('SELECT MAX(row_version) FROM reviews WHERE artifact_sha256=?',(record['artifact_sha256'],)).fetchone();version=row[0] or 0
        if version!=value['expected_version']:raise r.WorkbenchError('REVIEW_VERSION_CONFLICT')
        if con.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]>=5000:raise r.WorkbenchError('REVIEW_LIMIT')
        payload={key:item for key,item in value.items() if key!='expected_version'};payload['row_version']=version+1;con.execute('INSERT INTO reviews VALUES(?,?,?)',(record['artifact_sha256'],version+1,r.encode(payload).decode()))
    return dict(review=payload,verdicts_unchanged=True,operator_assertions_unverified=True)


def compare(left,right):
    with r.DATABASE_LOCK:a=artifact(left);b=artifact(right)
    af={v['case_id']:v for v in a['payload']['result']['cases']};bf={v['case_id']:v for v in b['payload']['result']['cases']};rows=[]
    for identifier in sorted(set(af)|set(bf)):
        av=af.get(identifier);bv=bf.get(identifier);ar=av['observed'] if av else {};br=bv['observed'] if bv else {}
        rows.append(dict(case_id=identifier,present_left=av is not None,present_right=bv is not None,same_case_revision=bool(av and bv and av['case_sha256']==bv['case_sha256']),left_status=ar.get('status'),right_status=br.get('status'),left_matched=ar.get('passed'),right_matched=br.get('passed'),same_captured_stream_hashes=bool(ar.get('streams') and br.get('streams') and all(ar['streams'][name]['sha256']==br['streams'][name]['sha256'] for name in ('stdout','stderr')))))
    return dict(left=left,right=right,same_case_set=set(af)==set(bf),both_complete=a['payload']['result']['complete'] and b['payload']['result']['complete'],cases=rows,scope='Exact case/output comparison, not causal interpretation or proof of correctness')


def export(identifier):
    with r.DATABASE_LOCK:
        record=artifact(identifier)
        if record['review']['status']!='approved':raise r.WorkbenchError('APPROVAL_REQUIRED')
        payload=record['payload'];data={'run.json':r.encode(record),'cases.json':r.encode(payload['suite']),'review.json':r.encode(record['review'])}
        for row in payload['result']['cases']:
            for name,stream in row['observed'].get('streams',{}).items():
                raw=base64.b64decode(stream['base64'],validate=True)
                if len(raw)!=stream['bytes'] or r.digest(raw)!=stream['sha256']:raise r.WorkbenchError('CAPTURE_HASH_MISMATCH')
                data['captures/'+row['case_id']+'/'+name+'.bin']=raw
        summary={key:value for key,value in payload['result'].items() if key!='cases'};summary['cases']=[dict(case_id=row['case_id'],case_sha256=row['case_sha256'],status=row['observed']['status'],matched=row['observed'].get('passed',False),exit_code=row['observed'].get('exit_code'),matches=row['observed'].get('matches')) for row in payload['result']['cases']]
        page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Private test evidence</title><style>body{max-width:1000px;margin:30px auto;font:16px system-ui;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Private expected/observed evidence</h1><p>Operator review does not turn unmatched checks into matches or authorize publication. Raw captures and scripts remain private.</p><pre>'+html.escape(r.encode(summary).decode())+'</pre></html>';data['summary.html']=page.encode()
        manifest=dict(format='outlands-test-evidence-export-v1',artifact_id=identifier,artifact_sha256=record['artifact_sha256'],review_version=record['review']['row_version'],complete=payload['result']['complete'],planned=payload['result']['planned'],attempted=payload['result']['attempted'],matched=payload['result']['matched'],unmatched=payload['result']['unmatched'],not_started=payload['result']['not_started'],public_release_authorized=False,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())})
        directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        for name,raw in sorted(data.items()):
            path=directory/name
            for parent in reversed(path.parents):
                if parent.is_relative_to(directory) and not parent.exists():r.mkdir(parent)
            r.write_new(path,raw)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)


def backup():
    target=r.local_path('backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
    with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
        con=sqlite3.connect(target.as_uri()+'?mode=rw',uri=True)
        try:source.backup(con);r.validate_schema(con)
        finally:con.close()
    raw=r.read_bytes(target,r.MAX_STORE);return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),scope='Database only; run directories, inbox and exported files are omitted')


def demo():
    imported=import_bundle(r.read_bytes(r.SOURCE/'examples/sample-cases.json'));pins=[]
    for item in imported['cases']:
        revision=case(item['case_id']);trust(r.encode(dict(case_id=item['case_id'],case_sha256=revision['sha256'],expected_version=0,status='approved',actor='sample_operator',note='Explicit fictional demo script trust',checks=dict(code_reviewed=True,authority=True,input_reviewed=True,effects_reviewed=True))));pins.append(dict(case_id=item['case_id'],expected_sha256=revision['sha256'],trust_version=1))
    first=jobs.wait(start_run(r.encode(dict(cases=pins)))['job_id']);second=jobs.wait(start_run(r.encode(dict(cases=pins[:2])))['job_id']);record=artifact(first['artifact_id']);review(r.encode(dict(artifact_id=record['artifact_id'],artifact_sha256=record['artifact_sha256'],expected_version=0,status='approved',actor='sample_reviewer',note='Fictional failures remain unmatched; review evidence only',checks=dict(quality=True,privacy=True,rights=True,context=True))));exported=export(first['artifact_id']);saved=backup();result=record['payload']['result']
    return dict(mode='FICTIONAL_TEST_EVIDENCE_DEMO',cases=len(cases()['cases']),attempted=result['attempted'],matched=result['matched'],unmatched=result['unmatched'],timeouts=sum(v['observed']['status']=='timeout' for v in result['cases']),expected_nonzero_matched=next(v['observed']['passed'] for v in result['cases'] if v['case_id']=='sample-nonzero'),artifacts=len(artifacts()['artifacts']),fresh_review_pending=artifact(second['artifact_id'])['review']['status']=='pending',private_export_files=len(exported['manifest']['files'])+1,backup_validated=saved['bytes']>0,original_operational_checks_executed=False,external_services_used=False)
