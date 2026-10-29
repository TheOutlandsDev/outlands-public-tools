"""Two complete-package exercises on invented inputs and new private directories."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CHECKS=dict(quality=True,privacy=True,rights=True,context=True)
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def require(ok,code):
    if not ok:raise ValueError(code)


def hashes(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


class Exercise:
    def __init__(self,name,workspace):
        self.source=ROOT/'systems'/name;self.workspace=workspace;self.calls=0;self.requests=0
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
        body=dict(expected_head=head,actor='sample_operator',reason='Fictional Toolkit 0.5 exercise',request=request)
        with (self.workspace/name).open('x',encoding='utf-8') as f:json.dump(body,f)
        value=self.call(command,'--file',name,error=error)
        return value if error else value['job']['result']


def imports(workspace):
    e=Exercise('import-migration-workbench',workspace)
    selected=['orders.csv','supplement.jsonl','conflicts.jsonl','contract.json']
    before={n:(workspace/'inbox'/n).read_bytes() for n in selected}
    contract=json.loads(before['contract.json']);sources=[dict(path='inbox/orders.csv',format='csv'),dict(path='inbox/supplement.jsonl',format='jsonl')]
    plan=e.mutate('plan',dict(sources=sources,contract=contract));s=plan['summary']
    require([s[k] for k in ('input_rows','accepted_rows','duplicate_rows','rejected_rows','conflict_rows')]==[7,3,2,2,0],'IMPORT_PREVIEW_ORACLE_FAILED')
    request=dict(plan_id=plan['plan_id'],plan_sha256=plan['plan_sha256'],accept_rejections=False,checks=CHECKS)
    e.mutate('import',request,error='REJECTED_ROWS_REVIEW_REQUIRED')
    require(not list((workspace/'stores').iterdir()),'REFUSED_IMPORT_CREATED_STORE')
    imported=e.mutate('import',dict(request,accept_rejections=True));store=workspace/imported['target'];db=store/'data.sqlite3'
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as con:
        con.execute('PRAGMA query_only=ON')
        records=[json.loads(row[0]) for row in con.execute('SELECT data_json FROM records ORDER BY record_id')]
        counts=[con.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('records','provenance','rejected')]
    require(counts==[3,5,2],'SQLITE_READBACK_COUNTS_FAILED')
    expected=[('sample-a',3,'12.50',True,'alpha'),('sample-b',7,'2.00',False,'=SUM(1)'),('sample-c',0,'0',True,None)]
    for row,(key,quantity,amount,active,note) in zip(records,expected):
        require(row['id']==key and row['quantity']==quantity and Decimal(row['amount'])==Decimal(amount) and row['active'] is active and row['note']==note,'SQLITE_VALUE_ORACLE_FAILED')
    e.call('inspect-import','--id',imported['import_id']);saved=hashes(store)
    e.mutate('import',dict(request,accept_rejections=True),error='EXACT_PLAN_ALREADY_IMPORTED')
    conflict=e.mutate('plan',dict(sources=[sources[0],dict(path='inbox/conflicts.jsonl',format='jsonl')],contract=contract))
    require(conflict['summary']['conflict_rows']==3,'CONFLICT_ORACLE_FAILED')
    e.mutate('import',dict(request,plan_id=conflict['plan_id'],plan_sha256=conflict['plan_sha256'],accept_rejections=True),error='CONFLICTING_KEYS_REQUIRE_NEW_PLAN')
    require(hashes(store)==saved and len(list((workspace/'stores').iterdir()))==1,'EXISTING_STORE_CHANGED')
    state=e.call('overview');require(len(state['imports'])==1 and state['unfinished_jobs']==0,'IMPORT_REOPEN_FAILED')
    require(all((workspace/'inbox'/n).read_bytes()==b for n,b in before.items()),'INPUT_CHANGED')
    return dict(status='PASS',input_rows=7,accepted_records=3,duplicate_rows=2,rejected_rows=2,provenance_rows=5,
                quantities=[3,7,0],rejection_without_review='REJECTED_ROWS_REVIEW_REQUIRED',repeat_refused=True,
                conflicting_rows=3,conflict_refused=True,sqlite_independently_read=True,input_bytes_unchanged=True,
                existing_store_unchanged=True,registered_stores=1,command_checks=e.calls)


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
    template['label']='Fictional Toolkit revision two';template['sections'][1]['title']='Requested quantities'
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


def run(workspace,exercise='all'):
    selected=('imports','documents') if exercise=='all' else (exercise,)
    require(all((ROOT/'systems'/('import-migration-workbench' if n=='imports' else 'document-template-workbench')/'workbench.py').is_file() for n in selected),'COMPLETE_PACKAGE_REQUIRED')
    workspace=Path(workspace)
    require(workspace.is_absolute() and '..' not in workspace.parts and not workspace.exists() and workspace.parent.is_dir(),'NEW_ABSOLUTE_WORKSPACE_REQUIRED')
    require(not workspace.resolve().is_relative_to(ROOT),'EXTERNAL_WORKSPACE_REQUIRED');workspace.mkdir(mode=0o700)
    outcomes={name:globals()[name](workspace/name) for name in selected}
    receipt=dict(schema=1,status='PASS',synthetic_only=True,exercises=outcomes,exercises_passed=len(outcomes),command_checks=sum(r['command_checks'] for r in outcomes.values()),runtime_bundled=False)
    with (workspace/'exercise-results.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',required=True,type=Path);p.add_argument('--exercise',choices=('all','imports','documents'),default='all');args=p.parse_args()
    try:print(json.dumps(run(args.workspace,args.exercise),sort_keys=True))
    except Exception:print(json.dumps(dict(status='FAILED',error='EXERCISE_REFUSED_OR_ORACLE_FAILED')));sys.exit(1)
