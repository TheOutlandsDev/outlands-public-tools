"""Complete private template revision, composition, build and reviewed handoff workflow."""
from contextlib import closing
import copy
import re
import sqlite3
import uuid
from . import contracts as c,runtime as r,journal as j,artifacts as a

def seed_fictional(root):
    for name in ('template.json','values.json','template-request.json'):r.write_new(root/'inbox'/name,r.read_bytes(r.SOURCE/'examples'/name))
def _head(state,pin):
    c.pin(pin)
    if state['head']!=pin:c.fail('JOURNAL_HEAD_CONFLICT')
def _code(error):return str(error) if isinstance(error,r.WorkbenchError) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',str(error)) else 'OPERATION_REFUSED'
def overview():
    state,_=j.read();return dict(sequence=state['sequence'],head=state['head'],jobs=list(state['jobs'].values()),templates=list(state['templates'].values()),previews=list(state['previews'].values()),builds=list(state['builds'].values()),unfinished_jobs=sum(row['status']=='started' for row in state['jobs'].values()))
def example():return dict(template=r.decode(r.read_bytes(r.SOURCE/'examples/template.json')),values=r.decode(r.read_bytes(r.SOURCE/'examples/values.json')))
def history():
    state,events=j.read();return dict(head=state['head'],events=events)
def job(identifier):
    c.identifier(identifier);state,_=j.read()
    if identifier not in state['jobs']:c.fail('JOB_NOT_FOUND')
    return state['jobs'][identifier]
def inspect_template(identifier):
    state,_=j.read();value=a.read_template(state,identifier);return dict(result=state['templates'][identifier],template=value)
def inspect_preview(identifier):
    state,_=j.read();value=a.read_preview(state,identifier);return dict(result=state['previews'][identifier],preview=value,docx_pixel_render=False)
def inspect_build(identifier):
    state,_=j.read();raw,model,inspection=a.read_build(state,identifier);return dict(result=state['builds'][identifier],preview=model,inspection=inspection,docx_pixel_render=False)
def document_bytes(identifier):
    state,_=j.read();raw,_,_=a.read_build(state,identifier);return raw
def compare(first,second):
    state,_=j.read();before=a.read_template(state,first);after=a.read_template(state,second)
    def changes(key):
        identity='name' if key=='fields' else 'id';left={v[identity]:v for v in before[key]};right={v[identity]:v for v in after[key]};return dict(added=sorted(set(right)-set(left)),removed=sorted(set(left)-set(right)),changed=sorted(n for n in left.keys()&right.keys() if left[n]!=right[n]),order_changed=[v[identity] for v in before[key]]!=[v[identity] for v in after[key]])
    return dict(first=state['templates'][first],second=state['templates'][second],same_template_bytes=r.encode(before)==r.encode(after),label_changed=before['label']!=after['label'],title_changed=before['title']!=after['title'],fields=changes('fields'),sections=changes('sections'))
def _run(kind,raw):
    value=r.decode(raw);c.envelope(value,('request',));c.request(kind,value['request'])
    with r.DATABASE_LOCK:
        state,_=j.read();_head(state,value['expected_head']);identifier=uuid.uuid4().hex;state=j.append(dict(operation='job_started',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,kind=kind,request=value['request'])),state['head'])
        try:
            if kind=='template':result=a.write_template(identifier,value['request'])
            elif kind=='preview':result=a.write_preview(identifier,value['request'],state)
            else:result=a.write_build(identifier,value['request'],state)
            state=j.append(dict(operation='job_completed',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,result=result)),state['head'])
        except Exception as error:
            code=_code(error);current,_=j.read()
            if current['jobs'][identifier]['status']=='started':j.append(dict(operation='job_failed',actor=value['actor'],reason=value['reason'],data=dict(job_id=identifier,code=code)),current['head'])
            raise r.WorkbenchError(code) from None
    return dict(head=state['head'],job=state['jobs'][identifier])
def save_template(raw):return _run('template',raw)
def preview(raw):return _run('preview',raw)
def build(raw):return _run('build',raw)
def recover(raw):
    value=r.decode(raw);c.fields(value,('actor','reason'));c.text(value['actor'],160);c.text(value['reason']);recovered=[]
    with r.DATABASE_LOCK:
        state,_=j.read()
        for row in list(state['jobs'].values()):
            if row['status']=='started':state=j.append(dict(operation='job_interrupted',actor=value['actor'],reason=value['reason'],data=dict(job_id=row['job_id'],code='INTERRUPTED_NO_AUTOREPLAY')),state['head']);recovered.append(row['job_id'])
    return dict(head=state['head'],interrupted_jobs=recovered,partial_outputs_retained=True,automatically_replayed=False,existing_documents_overwritten=False)
def export(raw):
    value=r.decode(raw);c.envelope(value,('preview_id','build_id','checks'));c.identifier(value['preview_id']);c.checks(value['checks'])
    if value['build_id'] is not None:c.identifier(value['build_id'])
    with r.DATABASE_LOCK:
        state,_=j.read();_head(state,value['expected_head']);model=a.read_preview(state,value['preview_id']);selected=state['previews'][value['preview_id']];template=a.read_template(state,selected['template_id']);built=None;inspection=None;document=None
        if value['build_id'] is not None:
            built=state['builds'].get(value['build_id'])
            if built is None or built['preview_id']!=value['preview_id']:c.fail('BUILD_PREVIEW_MISMATCH')
            document,_,inspection=a.read_build(state,value['build_id'])
        data={'template.json':r.encode(template),'preview.json':r.encode(model),'journal.json':r.encode(history()),'review.json':r.encode(value),'receipt.json':r.encode(dict(preview=selected,build=built)),'inspection.json':r.encode(inspection)}
        if document is not None:data.update({'document.docx':document,'document.docx.sha256':(r.digest(document)+'  document.docx\n').encode()})
        manifest=dict(format='outlands-private-document-handoff-v1',journal_head=state['head'],contains_input_values=True,contains_document=document is not None,public_release_authorized=False,files={name:dict(bytes=len(raw),sha256=r.digest(raw)) for name,raw in sorted(data.items())});directory=r.local_path('reports/'+uuid.uuid4().hex,False);r.mkdir(directory)
        for name,content in sorted(data.items()):r.write_new(directory/name,content)
        r.write_new(directory/'manifest.json',r.encode(manifest))
    return dict(directory=directory.relative_to(r.ROOT).as_posix(),manifest=manifest)
def backup_index():
    with r.DATABASE_LOCK:
        target=r.local_path('index-backups/'+uuid.uuid4().hex+'.sqlite3',False);r.write_new(target,b'')
        with r.connect() as source,r.io_errors(),r.guarded._store_scope(target,initial=True):
            with closing(sqlite3.connect(target)) as destination:source.backup(destination);r.validate_schema(destination);j.load(destination)
        raw=r.read_bytes(target,r.MAX_STORE)
    return dict(file=target.relative_to(r.ROOT).as_posix(),bytes=len(raw),sha256=r.digest(raw),contains_input_values=True,includes_document_files=False,private_index_backup=True)
def demo():
    fixtures=example();checks=dict(quality=True,privacy=True,rights=True,context=True)
    def run(fn,request):return fn(r.encode(dict(expected_head=overview()['head'],actor='sample_operator',reason='Fictional document workflow',request=request)))['job']['result']
    first=run(save_template,dict(parent_id=None,template=fixtures['template']));second_template=copy.deepcopy(fixtures['template']);second_template['label']='Fictional handoff revision two';second_template['sections'][1]['title']='Requested quantities';second=run(save_template,dict(parent_id=first['template_id'],template=second_template));comparison=compare(first['template_id'],second['template_id'])
    first_preview=run(preview,dict(template_id=first['template_id'],template_sha256=first['template_sha256'],values=fixtures['values'],sections=['summary','items']));second_preview=run(preview,dict(template_id=second['template_id'],template_sha256=second['template_sha256'],values=fixtures['values'],sections=['summary','items','notes']));first_build=run(build,dict(preview_id=first_preview['preview_id'],preview_sha256=first_preview['preview_sha256'],checks=checks));run(build,dict(preview_id=second_preview['preview_id'],preview_sha256=second_preview['preview_sha256'],checks=checks));inspected=inspect_build(first_build['build_id']);report=export(r.encode(dict(expected_head=overview()['head'],actor='sample_operator',reason='Fictional reviewed handoff',preview_id=first_preview['preview_id'],build_id=first_build['build_id'],checks=checks)));backup=backup_index();state=overview();total=inspected['preview']['sections'][1]['blocks'][0]['totals'][0]['quantity']
    return dict(mode='FICTIONAL_DOCUMENT_TEMPLATE_DEMO',templates=len(state['templates']),previews=len(state['previews']),builds=len(state['builds']),journal_events=state['sequence'],first_preview_sections=first_preview['summary']['sections'],first_preview_tables=first_preview['summary']['tables'],first_preview_table_rows=first_preview['summary']['table_rows'],total_quantity=total,changed_sections=comparison['sections']['changed'],document_parts=inspected['inspection']['parts'],external_relationships=inspected['inspection']['external_relationships'],private_report_files=len(report['manifest']['files'])+1,index_backup_verified=backup['bytes']>0,index_contains_input_values=True,index_includes_document_files=False,existing_documents_overwritten=False,external_services_used=False)
