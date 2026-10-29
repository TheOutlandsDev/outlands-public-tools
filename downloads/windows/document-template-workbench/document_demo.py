"""New-only fictional document exercise, using the unchanged application's CLI."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

ROOT=Path(__file__).resolve().parent
APP=ROOT/'application'
CHECKS=dict(quality=True,privacy=True,rights=True,context=True)
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def require(ok,code):
    if not ok:raise ValueError(code)

class Exercise:
    def __init__(self,name,workspace):
        self.source=APP;self.workspace=workspace;self.calls=0;self.requests=0
        self.call('init')
    def call(self,*args,error=None):
        self.calls+=1
        result=subprocess.run([sys.executable,'-B',str(self.source/'workbench.py'),'--workspace',str(self.workspace),*map(str,args)],cwd=self.source,capture_output=True,text=True,encoding='utf-8',timeout=90)
        require(result.returncode==(2 if error else 0),'EXERCISE_COMMAND_FAILED')
        value=json.loads(result.stdout)
        if error:require(value==dict(error=error),'EXPECTED_REFUSAL_MISSING')
        return value
    def mutate(self,command,request,error=None):
        self.requests+=1;head=self.call('overview')['head'];name='inbox/toolkit-request-'+str(self.requests)+'.json'
        body=dict(expected_head=head,actor='sample_operator',reason='Fictional Windows document exercise',request=request)
        with (self.workspace/name).open('x',encoding='utf-8') as f:json.dump(body,f)
        value=self.call(command,'--file',name,error=error)
        return value if error else value['job']['result']


def inspect_doc(path,notes,heading):
    with zipfile.ZipFile(path) as z:
        require(len(z.namelist())==8 and len(set(z.namelist()))==8,'DOCX_PART_COUNT_FAILED')
        require(not any(n.startswith('word/media/') or 'vba' in n.lower() for n in z.namelist()),'DOCX_UNEXPECTED_ASSET')
        for n in z.namelist():
            raw=z.read(n);require(b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw,'DOCX_ENTITY_REFUSED');E.fromstring(raw)
            if n.endswith('.rels'):require(not any(x.attrib.get('TargetMode')=='External' for x in E.fromstring(raw)),'DOCX_EXTERNAL_RELATIONSHIP')
        doc=E.fromstring(z.read('word/document.xml'));texts=[n.text or '' for n in doc.iter(W+'t')];all_text=' '.join(texts)
        for literal in ('Service handoff for Sample instrument','Sample bracket','Example cable','Total quantity 7',heading):require(literal in all_text,'DOCX_TEXT_ORACLE_FAILED')
        require(('Review notes' in texts)==notes,'DOCX_SECTION_SELECTION_FAILED')
        tables=doc.findall('.//'+W+'tbl');require(len(tables)==1,'DOCX_TABLE_COUNT_FAILED')
        rows=[[''.join(t.itertext()) for t in row.findall(W+'tc')] for row in tables[0].findall(W+'tr')]
        require(any('Sample bracket' in c and '3' in row[-1] for row in rows for c in row),'DOCX_FIRST_ROW_FAILED')
        require(any('Example cable' in c and '4' in row[-1] for row in rows for c in row),'DOCX_SECOND_ROW_FAILED')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def documents(workspace):
    e=Exercise('document-template-workbench',workspace);before={n:(workspace/'inbox'/n).read_bytes() for n in ('template.json','values.json')}
    template=json.loads(before['template.json']);values=json.loads(before['values.json'])
    first=e.mutate('save-template',dict(parent_id=None,template=template))
    preview=e.mutate('preview',dict(template_id=first['template_id'],template_sha256=first['template_sha256'],values=values,sections=['summary','items']))
    request=dict(preview_id=preview['preview_id'],preview_sha256=preview['preview_sha256'],checks=dict(CHECKS,quality=False))
    e.mutate('build',request,error='REVIEW_REQUIRED');require(not list((workspace/'builds').iterdir()),'UNREVIEWED_DOCUMENT_CREATED')
    built=e.mutate('build',dict(request,checks=CHECKS));original=workspace/built['target']/'document.docx';first_hash=inspect_doc(original,False,'Requested items')
    template['label']='Fictional Windows revision two';template['sections'][1]['title']='Requested quantities'
    second=e.mutate('save-template',dict(parent_id=first['template_id'],template=template))
    second_preview=e.mutate('preview',dict(template_id=second['template_id'],template_sha256=second['template_sha256'],values=values,sections=['summary','items','notes']))
    second_build=e.mutate('build',dict(preview_id=second_preview['preview_id'],preview_sha256=second_preview['preview_sha256'],checks=CHECKS))
    second_hash=inspect_doc(workspace/second_build['target']/'document.docx',True,'Requested quantities')
    require(hashlib.sha256(original.read_bytes()).hexdigest()==first_hash,'HISTORICAL_DOCUMENT_CHANGED')
    e.call('inspect-build','--id',built['build_id']);e.call('inspect-build','--id',second_build['build_id'])
    state=e.call('overview');require([len(state[k]) for k in ('templates','previews','builds')]==[2,2,2] and state['unfinished_jobs']==0,'DOCUMENT_REOPEN_FAILED')
    require(all((workspace/'inbox'/n).read_bytes()==b for n,b in before.items()),'INPUT_CHANGED')
    return dict(status='PASS',templates=2,previews=2,documents=2,item_rows=2,total_quantity=7,docx_parts=8,
                unreviewed_build_refused=True,optional_notes_omitted_then_included=True,
                original_document_unchanged=True,input_bytes_unchanged=True,xml_independently_inspected=True,
                external_relationships=0,macros=0,original_docx_sha256=first_hash,revised_docx_sha256=second_hash,
                microsoft_word_visual_validation=False,command_checks=e.calls)


def exercise(workspace):
    if not workspace.is_absolute() or '..' in workspace.parts or workspace.exists() or not workspace.parent.is_dir():
        raise ValueError('EXERCISE_REQUIRES_NEW_ABSOLUTE_INSTANCE')
    if workspace.resolve().is_relative_to(ROOT):raise ValueError('EXTERNAL_INSTANCE_REQUIRED')
    result=documents(workspace)
    return dict(mode='FICTIONAL_DOCUMENT_EXERCISE',**result)
