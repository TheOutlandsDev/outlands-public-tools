"""Immutable project editing, check history, review, comparisons and private exports."""
import difflib
import io
import re
import sqlite3
import time
import uuid
import zipfile
from . import contracts as c,jobs,runtime as r


def _revision(con,identifier,version=None):
    c.token(identifier);params=[identifier];statement='SELECT version,project_sha256,parent_sha256,definition_json FROM projects WHERE project_id=?'
    if version is not None:c.integer(version,1,100);statement+=' AND version=?';params.append(version)
    row=con.execute(statement+' ORDER BY version DESC LIMIT 1',params).fetchone()
    if row is None:raise r.WorkbenchError('PROJECT_NOT_FOUND')
    definition=c.project(row[3].encode());payload=dict(version=row[0],parent_sha256=row[2],definition=definition)
    if definition['project_id']!=identifier or r.digest(r.encode(payload))!=row[1]:raise r.WorkbenchError('PROJECT_HASH_MISMATCH')
    return dict(**payload,sha256=row[1])


def _save(con,definition,old=None):
    if old and old['definition']==definition:return dict(project_id=definition['project_id'],version=old['version'],project_sha256=old['sha256'],created=False)
    version=old['version']+1 if old else 1
    if version>100:raise r.WorkbenchError('REVISION_LIMIT')
    payload=dict(version=version,parent_sha256=old['sha256'] if old else None,definition=definition);sha=r.digest(r.encode(payload));raw=r.encode(definition)
    if len(raw)>r.MAX_INPUT:raise r.WorkbenchError('PROJECT_SIZE_LIMIT')
    con.execute('INSERT INTO projects VALUES(?,?,?,?,?)',(definition['project_id'],version,sha,payload['parent_sha256'],raw.decode()))
    return dict(project_id=definition['project_id'],version=version,project_sha256=sha,created=True)


def import_project(raw):
    value=c.project(raw)
    with r.connect() as con:
        exists=con.execute('SELECT 1 FROM projects WHERE project_id=?',(value['project_id'],)).fetchone()
        if exists:
            old=_revision(con,value['project_id'])
            if old['definition']!=value:raise r.WorkbenchError('PROJECT_ID_EXISTS')
            return _save(con,value,old)
        if con.execute('SELECT COUNT(DISTINCT project_id) FROM projects').fetchone()[0]>=40:raise r.WorkbenchError('PROJECT_LIMIT')
        return _save(con,value)


def projects():
    with r.connect() as con:rows=con.execute('SELECT project_id,MAX(version) FROM projects GROUP BY project_id ORDER BY project_id LIMIT 41').fetchall()
    if len(rows)>40:raise r.WorkbenchError('PROJECT_LIMIT')
    return dict(projects=[dict(project_id=row[0],version=row[1]) for row in rows])


def project(identifier,version=None):
    with r.connect() as con:return _revision(con,identifier,version)


def history(identifier):
    c.token(identifier)
    with r.connect() as con:rows=con.execute('SELECT version,project_sha256,parent_sha256 FROM projects WHERE project_id=? ORDER BY version LIMIT 101',(identifier,)).fetchall()
    return dict(project_id=identifier,versions=[dict(version=row[0],sha256=row[1],parent_sha256=row[2]) for row in rows])


def edit(raw):
    value=r.decode(raw);c.fields(value,('project_id','expected_sha256','path','content','operation'));c.token(value['project_id']);c.hash_value(value['expected_sha256']);c.path(value['path'])
    if value['operation'] not in ('save','delete'):raise r.WorkbenchError('EDIT_OPERATION_INVALID')
    if value['operation']=='delete' and value['content'] is not None:raise r.WorkbenchError('DELETE_CONTENT_INVALID')
    with r.connect() as con:
        old=_revision(con,value['project_id'])
        if old['sha256']!=value['expected_sha256']:raise r.WorkbenchError('PROJECT_REVISION_CONFLICT')
        files={f['path']:f['content'] for f in old['definition']['files']}
        if value['operation']=='delete':
            if value['path'] not in files:raise r.WorkbenchError('FILE_NOT_FOUND')
            del files[value['path']]
        else:files[value['path']]=value['content']
        definition=c.project(r.encode({**old['definition'],'files':[dict(path=path,content=content) for path,content in files.items()]}))
        return _save(con,definition,old)


def _finish(revision,result):
    identifier=uuid.uuid4().hex;payload=dict(format='outlands-developer-validation-v1',artifact_id=identifier,project_id=revision['definition']['project_id'],project_sha256=revision['sha256'],project_version=revision['version'],result=result);sha=r.digest(r.encode(payload))
    with r.connect() as con:
        if con.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0]>=400:raise r.WorkbenchError('ARTIFACT_LIMIT')
        con.execute('INSERT INTO artifacts VALUES(?,?,?)',(identifier,sha,r.encode(payload).decode()))
    return dict(artifact_id=identifier,artifact_sha256=sha,status=result['status'],saved=True)


def validate(raw):
    value=r.decode(raw);c.fields(value,('project_id','expected_sha256'));c.hash_value(value['expected_sha256'])
    with r.connect() as con:
        revision=_revision(con,value['project_id'])
        if revision['sha256']!=value['expected_sha256']:raise r.WorkbenchError('PROJECT_REVISION_CONFLICT')
    return jobs.start('validation',lambda control:control.execute(revision['definition']),lambda result:_finish(revision,result))


def _artifact(con,identifier):
    if type(identifier) is not str or not re.fullmatch('[0-9a-f]{32}',identifier):raise r.WorkbenchError('ARTIFACT_ID_INVALID')
    row=con.execute('SELECT artifact_sha256,payload_json FROM artifacts WHERE artifact_id=?',(identifier,)).fetchone()
    if row is None:raise r.WorkbenchError('ARTIFACT_NOT_FOUND')
    payload=r.decode(row[1].encode())
    if payload['artifact_id']!=identifier or r.digest(r.encode(payload))!=row[0]:raise r.WorkbenchError('ARTIFACT_HASH_MISMATCH')
    return dict(artifact_id=identifier,artifact_sha256=row[0],payload=payload)


def artifacts():
    with r.connect() as con:rows=con.execute('SELECT artifact_id FROM artifacts ORDER BY rowid DESC LIMIT 401').fetchall();values=[_artifact(con,row[0]) for row in rows]
    return dict(artifacts=[dict(artifact_id=v['artifact_id'],project_id=v['payload']['project_id'],version=v['payload']['project_version'],status=v['payload']['result']['status']) for v in values])


def artifact(identifier):
    with r.connect() as con:
        value=_artifact(con,identifier);row=con.execute('SELECT payload_json FROM reviews WHERE artifact_sha256=? ORDER BY row_version DESC LIMIT 1',(value['artifact_sha256'],)).fetchone();value['review']=r.decode(row[0].encode()) if row else dict(status='pending',row_version=0)
    return value


def review(raw):
    value=r.decode(raw);c.fields(value,('artifact_id','artifact_sha256','expected_version','status','actor','note','checks'));c.hash_value(value['artifact_sha256']);c.integer(value['expected_version'],0,1000);c.text(value['actor'],80);c.text(value['note'],1000,empty=True);c.fields(value['checks'],('quality','privacy','rights','context'))
    if value['status'] not in ('pending','approved','rejected') or any(type(v) is not bool for v in value['checks'].values()):raise r.WorkbenchError('REVIEW_INVALID')
    if value['status']=='approved' and not all(value['checks'].values()):raise r.WorkbenchError('REVIEW_CHECKS_REQUIRED')
    with r.connect() as con:
        record=_artifact(con,value['artifact_id'])
        if record['artifact_sha256']!=value['artifact_sha256']:raise r.WorkbenchError('ARTIFACT_CONFLICT')
        if value['status']=='approved' and (record['payload']['result']['status']!='completed' or not record['payload']['result']['passed']):raise r.WorkbenchError('REVIEW_REQUIRES_PASSING_CHECKS')
        row=con.execute('SELECT MAX(row_version) FROM reviews WHERE artifact_sha256=?',(record['artifact_sha256'],)).fetchone();version=row[0] or 0
        if version!=value['expected_version']:raise r.WorkbenchError('REVIEW_VERSION_CONFLICT')
        if con.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]>=5000:raise r.WorkbenchError('REVIEW_LIMIT')
        payload={key:item for key,item in value.items() if key!='expected_version'};payload['row_version']=version+1;con.execute('INSERT INTO reviews VALUES(?,?,?)',(record['artifact_sha256'],version+1,r.encode(payload).decode()))
    return dict(review=payload,operator_assertions_unverified=True)


def compare(identifier,left,right):
    with r.connect() as con:a=_revision(con,identifier,left);b=_revision(con,identifier,right)
    af={f['path']:f['content'] for f in a['definition']['files']};bf={f['path']:f['content'] for f in b['definition']['files']};changes=[];previews=0
    for path in sorted(set(af)|set(bf)):
        before=af.get(path);after=bf.get(path)
        if before==after:continue
        status='added' if before is None else 'deleted' if after is None else 'modified';row=dict(path=path,status=status,before_sha256=r.digest(before.encode()) if before is not None else None,after_sha256=r.digest(after.encode()) if after is not None else None)
        a_lines=(before or '').splitlines(True);b_lines=(after or '').splitlines(True)
        if previews<10:
            left_text=''.join(a_lines[:200])[:8000];right_text=''.join(b_lines[:200])[:8000];lines=list(difflib.unified_diff(left_text.splitlines(True),right_text.splitlines(True),fromfile='before/'+path,tofile='after/'+path));diff=''.join(lines)
            row.update(preview=diff[:16000],preview_complete=len(a_lines)<=200 and len(b_lines)<=200 and len(before or '')<=8000 and len(after or '')<=8000 and len(diff)<=16000);previews+=1
        else:row.update(preview='',preview_complete=False)
        changes.append(row)
    return dict(project_id=identifier,left_version=left,right_version=right,left_sha256=a['sha256'],right_sha256=b['sha256'],changes=changes,source_hash_comparison_complete=True,diff_previews_complete=all(v['preview_complete'] for v in changes))


def export(identifier):
    with r.DATABASE_LOCK:
        record=artifact(identifier)
        if record['review']['status']!='approved':raise r.WorkbenchError('APPROVAL_REQUIRED')
        payload=record['payload'];revision=project(payload['project_id'],payload['project_version'])
        if revision['sha256']!=payload['project_sha256']:raise r.WorkbenchError('PROJECT_REVISION_CONFLICT')
        data={'project.json':r.encode(revision['definition']),'validation.json':r.encode(record),'review.json':r.encode(record['review'])}
        data.update({'source/'+f['path']:f['content'].encode('utf-8') for f in revision['definition']['files']})
        manifest=dict(format='outlands-developer-export-v1',project_id=payload['project_id'],project_version=payload['project_version'],project_sha256=payload['project_sha256'],artifact_sha256=record['artifact_sha256'],review_version=record['review']['row_version'],all_files_checked=payload['result']['all_files_checked'],code_executed=False,public_release_authorized=False,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())})
        data['manifest.json']=r.encode(manifest);buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for name,raw in sorted(data.items()):
                info=zipfile.ZipInfo(name,(2020,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;archive.writestr(info,raw,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        raw=buffer.getvalue();directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory);r.write_new(directory/'project-source.zip',raw);receipt=dict(format='outlands-developer-export-receipt-v1',bytes=len(raw),sha256=r.digest(raw),manifest=manifest);r.write_new(directory/'receipt.json',r.encode(receipt))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),**receipt)


def backup():
    target=r.local_path('backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
    with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
        con=sqlite3.connect(target.as_uri()+'?mode=rw',uri=True)
        try:source.backup(con);r.validate_schema(con)
        finally:con.close()
    raw=r.read_bytes(target,r.MAX_STORE);return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),scope='Database state only; inbox and exported files are not included')


def demo():
    imported=import_project(r.read_bytes(r.SOURCE/'examples/sample-project.json'));identifier=imported['project_id'];first=project(identifier);run=jobs.wait(validate(r.encode(dict(project_id=identifier,expected_sha256=first['sha256'])))['job_id']);record=artifact(run['artifact_id']);edit(r.encode(dict(project_id=identifier,expected_sha256=first['sha256'],path='src/sample.py',content='def total(values):\n    return sum(values) + 1\n',operation='save')));second=project(identifier);changes=compare(identifier,1,2);next_run=jobs.wait(validate(r.encode(dict(project_id=identifier,expected_sha256=second['sha256'])))['job_id']);review(r.encode(dict(artifact_id=record['artifact_id'],artifact_sha256=record['artifact_sha256'],expected_version=0,status='approved',actor='sample_reviewer',note='Fictional static review; runtime behavior unverified',checks=dict(quality=True,privacy=True,rights=True,context=True))));exported=export(record['artifact_id']);saved=backup()
    return dict(mode='FICTIONAL_DEVELOPER_WORKSPACE_DEMO',projects=len(projects()['projects']),files=len(first['definition']['files']),versions=2,checked=record['payload']['result']['counts']['pass'],unchecked=record['payload']['result']['counts']['unchecked'],changed_files=len(changes['changes']),validation_artifacts=len(artifacts()['artifacts']),new_review_pending=artifact(next_run['artifact_id'])['review']['status']=='pending',private_export_members=len(exported['manifest']['files'])+1,export_version=exported['manifest']['project_version'],backup_validated=saved['bytes']>0,project_code_executed=False,external_services_used=False)
