"""Immutable neutral datasets/queries/reports, bounded jobs, review and private exports."""
import csv
import html
import io
import re
import sqlite3
import uuid
from . import contracts as c,jobs,report_xml,snapshots,runtime as r


def _dataset(con,identifier):
    c.token(identifier);row=con.execute('SELECT dataset_sha256,snapshot_file,snapshot_sha256,dataset_json FROM datasets WHERE dataset_id=?',(identifier,)).fetchone()
    if row is None:raise r.WorkbenchError('DATASET_NOT_FOUND')
    value=c.dataset(row[3].encode())
    if value['dataset_id']!=identifier or r.digest(r.encode(value))!=row[0]:raise r.WorkbenchError('DATASET_HASH_MISMATCH')
    if not re.fullmatch(r'snapshots/[0-9a-f]{32}\.sqlite3',row[1]):raise r.WorkbenchError('SNAPSHOT_PATH_INVALID')
    c.hash_value(row[2])
    return dict(definition=value,dataset_sha256=row[0],snapshot_file=row[1],snapshot_sha256=row[2])


def import_dataset(raw):
    value=c.dataset(raw);encoded=r.encode(value);sha=r.digest(encoded)
    if len(encoded)>r.MAX_INPUT:raise r.WorkbenchError('DATASET_SIZE_LIMIT')
    with r.connect() as con:
        old=con.execute('SELECT dataset_sha256 FROM datasets WHERE dataset_id=?',(value['dataset_id'],)).fetchone()
        if old:
            if old[0]!=sha:raise r.WorkbenchError('DATASET_IMMUTABLE')
            return dict(dataset_id=value['dataset_id'],dataset_sha256=sha,created=False)
        if con.execute('SELECT COUNT(*) FROM datasets').fetchone()[0]>=50:raise r.WorkbenchError('DATASET_LIMIT')
        file,file_sha=snapshots.create(value,sha);con.execute('INSERT INTO datasets VALUES(?,?,?,?,?)',(value['dataset_id'],sha,file,file_sha,encoded.decode()))
    return dict(dataset_id=value['dataset_id'],dataset_sha256=sha,created=True)


def datasets():
    with r.connect() as con:rows=con.execute('SELECT dataset_id,dataset_sha256 FROM datasets ORDER BY dataset_id LIMIT 51').fetchall()
    if len(rows)>50:raise r.WorkbenchError('DATASET_LIMIT')
    return dict(datasets=[dict(dataset_id=row[0],dataset_sha256=row[1]) for row in rows])


def dataset(identifier):
    with r.connect() as con:value=_dataset(con,identifier)
    return {key:value[key] for key in ('definition','dataset_sha256','snapshot_sha256')}


def _revision(con,kind,identifier,version=None):
    c.token(identifier);table='queries' if kind=='query' else 'reports';column=kind+'_id';hash_column=kind+'_sha256';params=[identifier];query='SELECT version,'+hash_column+',parent_sha256,definition_json FROM '+table+' WHERE '+column+'=?'
    if version is not None:c.integer(version,1,200);query+=' AND version=?';params.append(version)
    row=con.execute(query+' ORDER BY version DESC LIMIT 1',params).fetchone()
    if row is None:raise r.WorkbenchError('REVISION_NOT_FOUND')
    definition=r.decode(row[3].encode());payload=dict(kind=kind,version=row[0],parent_sha256=row[2],definition=definition)
    if r.digest(r.encode(payload))!=row[1]:raise r.WorkbenchError('REVISION_HASH_MISMATCH')
    return dict(**payload,sha256=row[1])


def _save(kind,identifier,definition,expected):
    c.token(identifier)
    if expected is not None:c.hash_value(expected)
    table='queries' if kind=='query' else 'reports';column=kind+'_id'
    with r.connect() as con:
        existing=con.execute('SELECT 1 FROM '+table+' WHERE '+column+'=?',(identifier,)).fetchone();old=_revision(con,kind,identifier) if existing else None
        if expected!=(old['sha256'] if old else None):raise r.WorkbenchError('REVISION_CONFLICT')
        if old and old['definition']==definition:return dict(kind=kind,identifier=identifier,sha256=old['sha256'],version=old['version'],created=False)
        if old is None and con.execute('SELECT COUNT(DISTINCT '+column+') FROM '+table).fetchone()[0]>=100:raise r.WorkbenchError('DOCUMENT_LIMIT')
        version=old['version']+1 if old else 1
        if version>200:raise r.WorkbenchError('REVISION_LIMIT')
        payload=dict(kind=kind,version=version,parent_sha256=expected,definition=definition);sha=r.digest(r.encode(payload));con.execute('INSERT INTO '+table+' VALUES(?,?,?,?,?)',(identifier,version,sha,expected,r.encode(definition).decode()))
    return dict(kind=kind,identifier=identifier,sha256=sha,version=version,created=True)


def save_query(raw):
    value=r.decode(raw);c.fields(value,('definition','expected_sha256'));definition=c.query(r.encode(value['definition']));return _save('query',definition['query_id'],definition,value['expected_sha256'])


def save_report(raw):
    value=r.decode(raw);c.fields(value,('report_id','title','xml','expected_sha256'));c.token(value['report_id']);c.text(value['title'],120);c.text(value['xml'],512*1024,multiline=True)
    definition=dict(report_id=value['report_id'],title=value['title'],report=report_xml.inspect(value['xml'].encode()));return _save('report',value['report_id'],definition,value['expected_sha256'])


def documents(kind):
    if kind not in ('query','report'):raise r.WorkbenchError('KIND_INVALID')
    table='queries' if kind=='query' else 'reports';column=kind+'_id'
    with r.connect() as con:rows=con.execute('SELECT '+column+',MAX(version) FROM '+table+' GROUP BY '+column+' ORDER BY '+column+' LIMIT 101').fetchall()
    if len(rows)>100:raise r.WorkbenchError('DOCUMENT_LIMIT')
    return dict(kind=kind,documents=[dict(identifier=row[0],version=row[1]) for row in rows])


def document(kind,identifier,version=None):
    if kind not in ('query','report'):raise r.WorkbenchError('KIND_INVALID')
    with r.connect() as con:return _revision(con,kind,identifier,version)


def history(kind,identifier):
    if kind not in ('query','report'):raise r.WorkbenchError('KIND_INVALID')
    table='queries' if kind=='query' else 'reports';column=kind+'_id';c.token(identifier)
    with r.connect() as con:rows=con.execute('SELECT version,'+kind+'_sha256,parent_sha256 FROM '+table+' WHERE '+column+'=? ORDER BY version LIMIT 201',(identifier,)).fetchall()
    return dict(kind=kind,identifier=identifier,versions=[dict(version=row[0],sha256=row[1],parent_sha256=row[2]) for row in rows])


def _finish(kind,context,result):
    identifier=uuid.uuid4().hex;payload=dict(format='outlands-sql-artifact-v1',artifact_id=identifier,kind=kind,context=context,result=result);raw=r.encode(payload);sha=r.digest(raw)
    if len(raw)>2*1024*1024:raise r.WorkbenchError('ARTIFACT_SIZE_LIMIT')
    with r.connect() as con:
        if con.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0]>=200:raise r.WorkbenchError('ARTIFACT_LIMIT')
        con.execute('INSERT INTO artifacts VALUES(?,?,?,?)',(identifier,kind,sha,raw.decode()))
    return dict(artifact_id=identifier,artifact_sha256=sha,status=result['status'],saved=True)


def start_query(raw):
    value=r.decode(raw);c.fields(value,('query_id','expected_query_sha256','dataset_id','expected_dataset_sha256','bindings'))
    with r.connect() as con:
        query=_revision(con,'query',value['query_id']);data=_dataset(con,value['dataset_id'])
        if value['expected_query_sha256']!=query['sha256'] or value['expected_dataset_sha256']!=data['dataset_sha256']:raise r.WorkbenchError('RUN_INPUT_CONFLICT')
        bound=c.bindings(value['bindings'],query['definition']['parameters']);request=snapshots.request(data['definition'],data['snapshot_file'],data['snapshot_sha256'])
    request.update(sql=query['definition']['sql'],parameters=query['definition']['parameters'],bindings=bound,mode='query');context=dict(query=query,dataset_id=value['dataset_id'],dataset_sha256=data['dataset_sha256'],snapshot_sha256=data['snapshot_sha256'],bindings=bound)
    return jobs.start('query',lambda control:control.execute(request),lambda result:_finish('query',context,result))


def start_validation(raw):
    value=r.decode(raw);c.fields(value,('report_id','expected_report_sha256','dataset_id','expected_dataset_sha256','bindings'))
    with r.connect() as con:
        report=_revision(con,'report',value['report_id']);data=_dataset(con,value['dataset_id'])
        if value['expected_report_sha256']!=report['sha256'] or value['expected_dataset_sha256']!=data['dataset_sha256']:raise r.WorkbenchError('RUN_INPUT_CONFLICT')
        bound=c.bindings(value['bindings'],report['definition']['report']['parameters']);snapshot=snapshots.request(data['definition'],data['snapshot_file'],data['snapshot_sha256'])
    def validate(control):
        results=[]
        for definition in report['definition']['report']['datasets']:
            if control.cancelled.is_set():return dict(status='cancelled',worker_executed=bool(control.children))
            request=dict(**snapshot,sql=definition['sql'],parameters=definition['parameters'],bindings={key:bound[target] for key,target in definition['parameter_links'].items()},mode='inspect');result=control.execute(request);expected=[field['column'] for field in definition['fields']];passed=result.get('status')=='completed' and result.get('columns')==expected and not result.get('truncated',True)
            results.append(dict(dataset=definition['name'],expected_columns=expected,passed=passed,inspection=result))
        return dict(status='completed',valid=all(item['passed'] for item in results),datasets=results,rendered=False,external_connections_used=False,worker_executed=bool(control.children))
    context=dict(report=report,dataset_id=value['dataset_id'],dataset_sha256=data['dataset_sha256'],snapshot_sha256=data['snapshot_sha256'],bindings=bound)
    return jobs.start('validation',validate,lambda result:_finish('validation',context,result))


def report_query(report_id,name):
    report=document('report',report_id);selected=next((item for item in report['definition']['report']['datasets'] if item['name']==name),None)
    if selected is None:raise r.WorkbenchError('REPORT_DATASET_NOT_FOUND')
    definition=dict(format='outlands-sql-query-v1',query_id='report-'+report['sha256'][:8]+'-'+name[:32],title='Offline report '+name,sql=selected['sql'],parameters=selected['parameters']);return dict(definition=definition,bindings={key:None for key in selected['parameters']},source_report_sha256=report['sha256'],saved=False)


def _artifact(con,identifier):
    if type(identifier) is not str or not re.fullmatch('[0-9a-f]{32}',identifier):raise r.WorkbenchError('ARTIFACT_ID_INVALID')
    row=con.execute('SELECT kind,artifact_sha256,payload_json FROM artifacts WHERE artifact_id=?',(identifier,)).fetchone()
    if row is None:raise r.WorkbenchError('ARTIFACT_NOT_FOUND')
    payload=r.decode(row[2].encode())
    if r.digest(r.encode(payload))!=row[1] or payload['kind']!=row[0] or payload['artifact_id']!=identifier:raise r.WorkbenchError('ARTIFACT_HASH_MISMATCH')
    return dict(artifact_id=identifier,kind=row[0],artifact_sha256=row[1],payload=payload)


def artifacts():
    with r.connect() as con:rows=con.execute('SELECT artifact_id,kind,artifact_sha256 FROM artifacts ORDER BY rowid DESC LIMIT 201').fetchall()
    if len(rows)>200:raise r.WorkbenchError('ARTIFACT_LIMIT')
    return dict(artifacts=[dict(artifact_id=row[0],kind=row[1],artifact_sha256=row[2]) for row in rows])


def artifact(identifier):
    with r.connect() as con:
        result=_artifact(con,identifier);row=con.execute('SELECT payload_json FROM reviews WHERE artifact_sha256=? ORDER BY row_version DESC LIMIT 1',(result['artifact_sha256'],)).fetchone();result['review']=r.decode(row[0].encode()) if row else dict(status='pending',row_version=0)
    return result


def review(raw):
    value=r.decode(raw);c.fields(value,('artifact_id','artifact_sha256','expected_version','status','actor','note','checks'));c.hash_value(value['artifact_sha256']);c.integer(value['expected_version'],0,1000);c.text(value['actor'],80);c.text(value['note'],1000,empty=True);c.fields(value['checks'],('quality','privacy','rights','context'))
    if value['status'] not in ('pending','approved','rejected') or any(type(flag) is not bool for flag in value['checks'].values()):raise r.WorkbenchError('REVIEW_INVALID')
    if value['status']=='approved' and not all(value['checks'].values()):raise r.WorkbenchError('REVIEW_CHECKS_REQUIRED')
    with r.connect() as con:
        result=_artifact(con,value['artifact_id'])
        if result['artifact_sha256']!=value['artifact_sha256']:raise r.WorkbenchError('ARTIFACT_CONFLICT')
        if value['status']=='approved' and result['payload']['result']['status']!='completed':raise r.WorkbenchError('REVIEW_INCOMPLETE_ARTIFACT')
        row=con.execute('SELECT MAX(row_version) FROM reviews WHERE artifact_sha256=?',(result['artifact_sha256'],)).fetchone();version=row[0] or 0
        if version!=value['expected_version']:raise r.WorkbenchError('REVIEW_VERSION_CONFLICT')
        if con.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]>=5000:raise r.WorkbenchError('REVIEW_LIMIT')
        payload={key:item for key,item in value.items() if key!='expected_version'};payload['row_version']=version+1;con.execute('INSERT INTO reviews VALUES(?,?,?)',(result['artifact_sha256'],version+1,r.encode(payload).decode()))
    return dict(review=payload,operator_assertions_unverified=True)


def compare(left,right):
    with r.DATABASE_LOCK:a=artifact(left);b=artifact(right)
    ar=a['payload']['result'];br=b['payload']['result']
    if a['kind']!='query' or b['kind']!='query' or ar['status']!='completed' or br['status']!='completed':raise r.WorkbenchError('COMPARISON_REQUIRES_COMPLETED_QUERIES')
    return dict(left=left,right=right,same_query=a['payload']['context']['query']['sha256']==b['payload']['context']['query']['sha256'],same_dataset=a['payload']['context']['dataset_sha256']==b['payload']['context']['dataset_sha256'],same_bindings=a['payload']['context']['bindings']==b['payload']['context']['bindings'],columns_equal=ar['columns']==br['columns'],rows_equal_in_returned_order=ar['rows']==br['rows'],left_rows=len(ar['rows']),right_rows=len(br['rows']),comparison_complete=not ar['truncated'] and not br['truncated'],scope='Exact returned-order comparison; no causal interpretation or unordered row matching')


def _csv_cell(value):
    if isinstance(value,str) and (value[:1] in ('\t','\r','\n') or value.lstrip()[:1] in ('=','+','-','@')):return "'"+value
    return '' if value is None else value


def export(identifier):
    with r.DATABASE_LOCK:
        record=artifact(identifier)
        if record['review']['status']!='approved':raise r.WorkbenchError('APPROVAL_REQUIRED')
        payload=record['payload'];result=payload['result'];data={'artifact.json':r.encode(record),'result.json':r.encode(result),'context.json':r.encode(payload['context']),'review.json':r.encode(record['review'])}
        if record['kind']=='query':
            stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerow([_csv_cell(value) for value in result['columns']]);writer.writerows([_csv_cell(value) for value in row] for row in result['rows']);data['preview.csv']=stream.getvalue().encode('utf-8')
        summary=dict(kind=record['kind'],artifact_sha256=record['artifact_sha256'],status=result['status'],dataset_id=payload['context']['dataset_id'],dataset_sha256=payload['context']['dataset_sha256'],result_truncated=result.get('truncated',False),validation_passed=result.get('valid'))
        if record['kind']=='query':summary.update(columns=result['columns'],returned_rows=len(result['rows']),html_preview_scope='First twenty returned rows; text clipped to 200 characters; JSON and CSV retain the returned preview',rows=[[cell[:200] if isinstance(cell,str) else cell for cell in row] for row in result['rows'][:20]])
        else:summary['datasets']=[dict(dataset=item['dataset'],passed=item['passed'],expected_columns=item['expected_columns'],inspection_status=item['inspection']['status'],actual_columns=item['inspection'].get('columns')) for item in result.get('datasets',[])]
        page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Offline SQL report</title><style>body{max-width:1000px;margin:30px auto;font:16px system-ui;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Private offline SQL artifact</h1><p>Review before sharing. Results may be truncated; this is not report rendering or publication clearance.</p><pre>'+html.escape(r.encode(summary).decode())+'</pre></html>';data['report.html']=page.encode()
        manifest=dict(format='outlands-sql-export-v1',artifact_id=identifier,artifact_sha256=record['artifact_sha256'],review_version=record['review']['row_version'],kind=record['kind'],result_truncated=result.get('truncated',False),validation_passed=result.get('valid'),csv_formula_prefixing='apostrophe_for_leading_formula_markers',public_release_authorized=False,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())})
        directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        for name,raw in sorted(data.items()):r.write_new(directory/name,raw)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)


def backup():
    target=r.local_path('backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
    with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
        con=sqlite3.connect(target.as_uri()+'?mode=rw',uri=True)
        try:source.backup(con);r.validate_schema(con)
        finally:con.close()
    raw=r.read_bytes(target,r.MAX_STORE);return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),snapshots_included=False)


def demo():
    imported=import_dataset(r.read_bytes(r.SOURCE/'examples/sample-dataset.json'));definition=r.decode(r.read_bytes(r.SOURCE/'examples/sample-query.json'));first=save_query(r.encode(dict(definition=definition,expected_sha256=None)))
    def run(minimum,query):return jobs.wait(start_query(r.encode(dict(query_id=definition['query_id'],expected_query_sha256=query['sha256'],dataset_id=imported['dataset_id'],expected_dataset_sha256=imported['dataset_sha256'],bindings=dict(minimum=minimum))))['job_id'])
    a=run(0,first);b=run(4,first);report=save_report(r.encode(dict(report_id='sample-report',title='Fictional report',xml=r.read_bytes(r.SOURCE/'examples/sample-report.xml').decode(),expected_sha256=None)));validation=jobs.wait(start_validation(r.encode(dict(report_id='sample-report',expected_report_sha256=report['sha256'],dataset_id=imported['dataset_id'],expected_dataset_sha256=imported['dataset_sha256'],bindings=dict(minimum=0))))['job_id'])
    definition['sql']=definition['sql'].replace('SUM(i.quantity)','SUM(i.quantity) + 1');second=save_query(r.encode(dict(definition=definition,expected_sha256=first['sha256'])));c_run=run(0,second)
    record=artifact(a['artifact_id']);review(r.encode(dict(artifact_id=a['artifact_id'],artifact_sha256=record['artifact_sha256'],expected_version=0,status='approved',actor='sample_reviewer',note='Fictional query review',checks=dict(quality=True,privacy=True,rights=True,context=True))));exported=export(a['artifact_id']);saved=backup();rows=record['payload']['result']['rows'];validated=artifact(validation['artifact_id'])['payload']['result'];comparison=compare(a['artifact_id'],b['artifact_id'])
    return dict(mode='FICTIONAL_SQL_REPORT_DEMO',groups=rows,filtered_groups=artifact(b['artifact_id'])['payload']['result']['rows'],query_versions=2,revision_groups=artifact(c_run['artifact_id'])['payload']['result']['rows'],report_valid=validated['valid'],report_datasets=len(validated['datasets']),artifacts=len(artifacts()['artifacts']),comparison_rows_equal=comparison['rows_equal_in_returned_order'],private_export_files=len(exported['manifest']['files'])+1,backup_validated=saved['bytes']>0,external_connections_used=False,report_rendered=False)
