# Fictional typed document-intake walkthrough

Keep all six runtime/generator files together and use a selected Python interpreter. Typical commands from the tool directory are:

```text
python -E -s -B fictional_docx.py --variant before --out NEW_EXTERNAL_INPUT.docx
python -E -s -B document_intake.py --input NEW_EXTERNAL_INPUT.docx --table table-1 --mapping examples/mapping.json
python -E -s -B document_intake.py --input NEW_EXTERNAL_INPUT.docx --table table-1 --mapping examples/mapping.json --out NEW_EXTERNAL_REPORT.json
```

The default preview exports accepted typed values, mapping fields, identity provenance and hashes. It is not anonymized. Rejected and ignored payload values are omitted; accepted values remain private. A report can contain accepted records and still require review for the whole batch. Enforce `ready_for_explicit_review` as a whole-batch condition; true does not mean approval or import. No source is transformed and no record is imported.

Save the Python block below verbatim as `fictional_intake_walkthrough.py` outside the source tree. Give it the copied tool directory and an existing trusted private parent, using absolute paths. This invocation works in PowerShell 5.1 or a POSIX shell with the appropriate path syntax:

```text
python -I -B fictional_intake_walkthrough.py COPIED_TOOL_DIRECTORY EXISTING_PRIVATE_PARENT
```

For example, `D:\Private-Review` is a fictional parent placeholder to replace with your own existing private directory. The program creates a unique child and never reuses earlier output names. It invokes actual generator and intake script entrypoints under the same interpreter, with coherent C XML bindings. Every expected typed record, group, issue and accounting value is authored independently; neither the intake converter nor its grouping logic is imported as an oracle.

Cases cover four generator variants, exact duplicates and conflicting groups, accepted subsets held by whole-batch review, null versus zero, canonical integer/decimal/date/boolean grammar, literal case/whitespace, composite identities, explicit column policies, header/mapping refusals and exact source-row provenance. Raw DOCX, mapping, normalized CSV and stored-content SHA-256 values are independently calculated. Metadata/property omission and fingerprints do not establish confidentiality, authenticity or business correctness.

All main-body content is checked, even an unselected table. The program uses only invented ZIP/XML/mapping bytes, never starts Office, renders or executes documents, follows external resources or imports records. Input members are decompressed in memory, without filesystem unpacking. Packaging qualification separately extracts its verified source ZIP. Audit hooks and parser bounds are selected application controls, not an OS sandbox or hard deadline.

Every pre-existing workspace artifact must remain unchanged during later writes. Mandatory hardlink checks cover both document and mapping inputs; fresh report names, input aliases, source-output paths and traversal spellings are checked. One child-only write fault deliberately retains five unconfirmed bytes; subsequent reuse is refused. Keep this retained output privately and choose a fresh name. The program does not automatically delete any fixture or promise rollback, atomic snapshots or full metadata preservation.

The program writes 23 exact reports, an observation ledger and a SHA-256 manifest. It verifies every input/mapping/report byte, all four generated DOCX files and six unchanged copied runtime files. It prints fixed case outcomes and counts rather than host paths. The temporary child and its 80 files remain private; no real document or operational mapping is required.

```python
"""Fictional DOCX typed-intake previews and whole-batch gates; never run Office."""
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import warnings
import zipfile

if not __debug__:raise RuntimeError('ASSERTIONS_REQUIRED')
module=Path(sys.argv[1]).resolve(strict=True);parent=Path(sys.argv[2]).resolve(strict=True)
assert parent.is_dir() and not parent.is_relative_to(module) and not module.is_relative_to(parent)
assert not parent.is_symlink() and not getattr(parent,'is_junction',lambda:False)()
work=Path(tempfile.mkdtemp(prefix='fictional-document-intake-',dir=parent)).resolve();assert work.parent==parent
runtimes=('document_intake.py','intake.py','fictional_docx.py','docx_core.py','toolkit.py','native_windows.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
runtime_hashes={name:sha((module/name).read_bytes()) for name in runtimes}
inputs=work/'inputs';generated=work/'generated';reports=work/'reports'
inputs.mkdir();generated.mkdir();reports.mkdir()
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'
MAIN='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
def escape(value):return value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def para(value):return dict(kind='paragraph',text=value)
def table(rows):return dict(kind='table',rows=rows)
before=[para('Fictional intake example.'),table([['Record','Units','Due','Active'],
    ['sample-a','12','2030-01-10','true'],['sample-b','7','2030-01-11','false'],['sample-a','12','2030-01-10','true']])]
after=[para('Fictional revised intake example.'),table([['Record','Units','Due','Active'],['sample-a','14','2030-01-10','true'],['sample-c','5','2030-01-12','true']])]
needs_review=[para('Fictional revised intake example.'),table([['Record','Units','Due','Active'],['sample-a','12','2030-01-10','true'],['sample-a','13','2030-01-10','true'],['sample-c','invalid','2030-01-12','true']])]
variants={'before':before,'after':after,'needs-review':needs_review,'formatting':before}
def parts(spec,*,author='Fictional Author',bold=False):
    def p(value):return '<w:p><w:r>'+('<w:rPr><w:b/></w:rPr>' if bold else '')+'<w:t xml:space="preserve">'+escape(value)+'</w:t></w:r></w:p>'
    body=[]
    for block in spec:
        if block['kind']=='paragraph':body.append(p(block['text']))
        else:body.append('<w:tbl>'+''.join('<w:tr>'+''.join('<w:tc>'+p(value)+'</w:tc>' for value in row)+'</w:tr>' for row in block['rows'])+'</w:tbl>')
    return {
      '[Content_Types].xml':('<Types xmlns="'+C+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="'+MAIN+'"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>').encode(),
      '_rels/.rels':('<Relationships xmlns="'+P+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="word/document.xml"/><Relationship Id="core" Type="'+P+'/metadata/core-properties" Target="docProps/core.xml"/></Relationships>').encode(),
      'word/document.xml':('<w:document xmlns:w="'+W+'"><w:body>'+''.join(body)+'</w:body></w:document>').encode(),
      'docProps/core.xml':('<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>'+escape(author)+'</dc:creator></cp:coreProperties>').encode()}
def pack(values,*,stored=False,duplicate=None):
    output=io.BytesIO()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always',UserWarning)
        with zipfile.ZipFile(output,'w') as archive:
            rows=sorted(values.items())+([(duplicate,values[duplicate])] if duplicate else [])
            for name,raw in rows:
                info=zipfile.ZipInfo(name,date_time=(2030,1,1,0,0,0));info.compress_type=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
                archive.writestr(info,raw)
        assert len(notices)==(1 if duplicate else 0)
    return output.getvalue()
def model(spec):
    blocks=[];pcount=tcount=0
    for position,block in enumerate(spec,1):
        if block['kind']=='paragraph':
            pcount+=1;blocks.append(dict(id='paragraph-'+str(pcount),position=position,kind='paragraph',text=block['text']))
        else:
            tcount+=1;blocks.append(dict(id='table-'+str(tcount),position=position,kind='table',rows=copy.deepcopy(block['rows'])))
    return blocks
def changed(values,name,old,new):
    output=dict(values);assert old in output[name];output[name]=output[name].replace(old,new,1);return output

def field(source,target,kind='text',required=True):return dict(source=source,target=target,type=kind,required=required)
mapping=dict(format='outlands-table-map-v1',identity=['record_id'],unknown_columns='reject',fields=[
    field('Record','record_id'),field('Units','units','integer'),field('Due','due','date'),field('Active','active','boolean')])
maps={'base':mapping,'ignore-extra':dict(mapping,unknown_columns='ignore'),
      'optional-units':dict(mapping,fields=[mapping['fields'][0],field('Units','units','integer',False),*mapping['fields'][2:]]),
      'composite':dict(mapping,identity=['record_id','due']),
      'extended':dict(mapping,fields=[*mapping['fields'],field('Price','price','decimal'),field('Note','note','text',False)])}
map_raw={name:encoded(value) for name,value in maps.items()}
def rec(key,units=12,due='2030-01-10',active=True,**extra):return dict(record_id=key,units=units,due=due,active=active,**extra)
def accepted_record(record,rows):return dict(record=record,source_rows=rows)
def problem(row,code):return dict(row=row,code=code)
def expected(raw,blocks,rows,contract,accepted,issues,*,duplicates=0,conflicts=0,ignored=0,table_id='table-1',position=2):
    csv_text=io.StringIO(newline='');csv.writer(csv_text,lineterminator='\n').writerows(rows)
    counts=dict(input_rows=len(rows)-1,accepted_records=len(accepted),duplicate_rows=duplicates,rejected_rows=sum(r['code']!='IDENTITY_CONFLICT' for r in issues),conflict_rows=conflicts)
    assert counts['input_rows']==sum(counts[k] for k in ('accepted_records','duplicate_rows','rejected_rows','conflict_rows'))
    status='PASS' if accepted and not issues else 'REVIEW_REQUIRED'
    return dict(format='outlands-document-intake-v1',status=status,source_sha256=sha(raw),mapping_sha256=sha(map_raw[contract]),
      source_format='docx-table',mapping=maps[contract]['fields'],ignored_columns=ignored,counts=counts,accepted=accepted,issues=issues,
      ready_for_explicit_review=status=='PASS',imported=False,normalized_table_sha256=sha(csv_text.getvalue().encode('utf-8')),
      content_sha256=sha(encoded(blocks)),selected_table=table_id,table_position=position,source_row_basis='ONE_BASED_SELECTED_TABLE_ROW',
      document_properties_exported=False,source_transformed=False)
header=['Record','Units','Due','Active']
base_accepted=[accepted_record(rec('sample-a'),[2,4]),accepted_record(rec('sample-b',7,'2030-01-11',False),[3])]
after_accepted=[accepted_record(rec('sample-a',14),[2]),accepted_record(rec('sample-c',5,'2030-01-12'),[3])]
variant_raw={name:pack(parts(spec,bold=name=='formatting')) for name,spec in variants.items()}
variant_expectations={}
for name,spec in variants.items():
    values=base_accepted if name in ('before','formatting') else after_accepted if name=='after' else []
    issues=[problem(2,'IDENTITY_CONFLICT'),problem(3,'IDENTITY_CONFLICT'),problem(4,'VALUE_INTEGER_INVALID')] if name=='needs-review' else []
    variant_expectations[name]=expected(variant_raw[name],model(spec),spec[1]['rows'],'base',values,issues,
        duplicates=1 if name in ('before','formatting') else 0,conflicts=2 if name=='needs-review' else 0)
fixtures=[]
def fixture(name,rows,accepted,issues=(),*,contract='base',duplicates=0,conflicts=0,ignored=0,body=None,table_id='table-1',position=2,author='Fictional Author',bold=False,stored=False):
    blocks=body if body is not None else [para('Fictional selected intake table.'),table(rows)]
    raw=pack(parts(blocks,author=author,bold=bold),stored=stored)
    report=expected(raw,model(blocks),rows,contract,accepted,list(issues),duplicates=duplicates,conflicts=conflicts,ignored=ignored,table_id=table_id,position=position)
    fixtures.append((name,raw,contract,table_id,report))
fixture('whole-batch-invalid-holds-ready',[header,['safe-a','2','2030-01-10','true'],['rejected-a','PRIVATE_INVALID_TOKEN','2030-01-10','true']],
    [accepted_record(rec('safe-a',2),[2])],[problem(3,'VALUE_INTEGER_INVALID')])
fixture('whole-batch-conflict-holds-ready',[header,['group-a','1','2030-01-10','true'],['group-a','2','2030-01-10','true'],['unique-a','3','2030-01-10','true']],
    [accepted_record(rec('unique-a',3),[4])],[problem(2,'IDENTITY_CONFLICT'),problem(3,'IDENTITY_CONFLICT')],conflicts=2)
fixture('empty-accepted-set-holds-ready',[header],[])
fixture('optional-empty-is-null-not-zero',[header,['empty-a','','2030-01-10','false'],['zero-a','0','2030-01-10','false']],
    [accepted_record(rec('empty-a',None,active=False),[2]),accepted_record(rec('zero-a',0,active=False),[3])],contract='optional-units')
fixture('typed-decimal-text-null-and-literals',[header+['Price','Note'],['typed-a','0','2032-02-29','false','1.230000',''],['typed-b','-2','2030-01-10','true','-2.500000','  literal # $ \\ lambda λ  ']],
    [accepted_record(rec('typed-a',0,'2032-02-29',False,price='1.23',note=None),[2]),accepted_record(rec('typed-b',-2,price='-2.5',note='  literal # $ \\ lambda λ  '),[3])],contract='extended')
fixture('normalized-decimal-identical-duplicate',[header+['Price','Note'],['same-a','0','2030-01-10','true','1.230000',''],['same-a','0','2030-01-10','true','1.23','']],
    [accepted_record(rec('same-a',0,price='1.23',note=None),[2,3])],contract='extended',duplicates=1)
fixture('composite-identity-and-canonical-order',[header,['same-a','2','2030-01-11','true'],['same-a','1','2030-01-10','true']],
    [accepted_record(rec('same-a',1),[3]),accepted_record(rec('same-a',2,'2030-01-11'),[2])],contract='composite')
fixture('case-and-whitespace-are-literal',[header,['sample-a','2','2030-01-10','true'],['Sample-a','1','2030-01-10','true'],[' sample-a ','3','2030-01-10','true']],
    [accepted_record(rec(' sample-a ',3),[4]),accepted_record(rec('Sample-a',1),[3]),accepted_record(rec('sample-a',2),[2])])
fixture('unknown-column-explicit-ignore',[header+['Private extra'],['sample-a','2','2030-01-10','true','PRIVATE_IGNORED_TOKEN']],
    [accepted_record(rec('sample-a',2),[2])],contract='ignore-extra',ignored=1)
fixture('canonical-integer-refusals',[header,*[[f'bad-{i}',value,'2030-01-10','true'] for i,value in enumerate(('01','1.0','-0','+1','1000000000001'))]],[],
    [problem(row,'VALUE_INTEGER_INVALID') for row in range(2,7)])
fixture('canonical-boolean-refusals',[header,*[[f'bad-{i}','1','2030-01-10',value] for i,value in enumerate(('TRUE','1',' false '))]],[],
    [problem(row,'VALUE_BOOLEAN_INVALID') for row in range(2,5)])
fixture('calendar-date-refusals',[header,['date-a','1','2031-02-29','true'],['date-b','1','2030-1-10','true']],[],[problem(2,'VALUE_DATE_INVALID'),problem(3,'VALUE_DATE_INVALID')])
fixture('decimal-grammar-and-bound-refusals',[header+['Price','Note'],*[[f'bad-{i}','1','2030-01-10','true',value,''] for i,value in enumerate(('1e2','1.0000001','1000000000000.000001'))]],[],
    [problem(row,'VALUE_DECIMAL_INVALID') for row in range(2,5)],contract='extended')
fixture('required-empty-refusal',[header,['required-a','','2030-01-10','true']],[],[problem(2,'REQUIRED_VALUE_MISSING')])
fixture('mapped-text-bound-refusal',[header,['X'*257,'1','2030-01-10','true']],[],[problem(2,'VALUE_TEXT_INVALID')])
fixture('multiline-cell-controls-refused',[header,['line\nbreak','1','2030-01-10','true']],[],[problem(2,'VALUE_TEXT_INVALID')])
fixture('properties-change-raw-not-content',before[1]['rows'],base_accepted,duplicates=1,body=before,author='PRIVATE_PROPERTY_SENTINEL')
fixture('zip-transport-change-raw-not-content',before[1]['rows'],base_accepted,duplicates=1,body=before,stored=True)
second=[['Record','Units','Due','Active'],['selected-b','4','2030-01-12','true']]
fixture('explicit-second-table-no-header-search',second,[accepted_record(rec('selected-b',4,'2030-01-12'),[2])],
    body=[table([['Other'],['Ignored first table']]),para('Fictional separator.'),table(second)],table_id='table-2',position=3)
bad_docs=[]
def bad_doc(name,rows,error):bad_docs.append((name,pack(parts([table(rows)]),stored=True),error))
bad_doc('refuse-duplicate-header',[['Record','Record','Due','Active'],['a','1','2030-01-10','true']],'HEADER_INVALID')
bad_doc('refuse-empty-header',[['Record','','Due','Active'],['a','1','2030-01-10','true']],'HEADER_INVALID')
bad_doc('refuse-header-alias-inference',[['record','Units','Due','Active'],['a','1','2030-01-10','true']],'MAPPED_HEADER_MISSING')
bad_doc('refuse-unmapped-column',[header+['Extra'],['a','1','2030-01-10','true','extra']],'UNMAPPED_HEADER')
base_parts=parts(before)
bad_docs.extend([
 ('refuse-nonzip-document',b'Fictional refused document','DOCX_ARCHIVE_INVALID'),
 ('refuse-external-relationship',pack(changed(base_parts,'_rels/.rels',b'Target=',b'TargetMode="External" Target='),stored=True),'DOCX_RELATIONSHIP_INVALID'),
 ('refuse-dtd-document',pack(dict(base_parts,**{'word/document.xml':b'<!DOCTYPE w:document [<!ENTITY fictional "none">]>'+base_parts['word/document.xml']}),stored=True),'XML_DECLARATION_FORBIDDEN'),
 ('refuse-unselected-hidden-content',pack(changed(parts([table(before[1]['rows']),table([['hidden']])]),'word/document.xml',b'hidden',b'hidden</w:t><w:rPr><w:vanish/></w:rPr><w:t>'),stored=True),'DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT')])
bad_maps=[]
def bad_map(name,value,error):bad_maps.append((name,encoded(value),error))
bad_maps.extend([('refuse-invalid-mapping-json',b'{','JSON_INVALID'),('refuse-duplicate-mapping-json-key',b'{"format":"a","format":"b"}','JSON_DUPLICATE_KEY'),('refuse-float-mapping-json',b'{"value":1.0}','JSON_INTEGER_OR_STRING_REQUIRED')])
bad_map('refuse-map-empty-fields',dict(mapping,fields=[]),'MAP_INVALID')
bad_map('refuse-map-required-not-boolean',dict(mapping,fields=[dict(mapping['fields'][0],required='true'),*mapping['fields'][1:]]),'MAP_INVALID')
bad_map('refuse-map-duplicate-source',dict(mapping,fields=[mapping['fields'][0],dict(mapping['fields'][1],source='Record'),*mapping['fields'][2:]]),'MAP_DUPLICATE_FIELD')
bad_map('refuse-map-duplicate-target',dict(mapping,fields=[mapping['fields'][0],dict(mapping['fields'][1],target='record_id'),*mapping['fields'][2:]]),'MAP_DUPLICATE_FIELD')
bad_map('refuse-map-optional-identity',dict(mapping,fields=[dict(mapping['fields'][0],required=False),*mapping['fields'][1:]]),'MAP_IDENTITY_INVALID')
bad_map('refuse-map-unknown-identity',dict(mapping,identity=['unknown']),'MAP_IDENTITY_INVALID')
bad_map('refuse-map-target-case',dict(mapping,fields=[dict(mapping['fields'][0],target='Record'),*mapping['fields'][1:]]),'IDENTIFIER_INVALID')
bad_map('refuse-map-unknown-columns-policy',dict(mapping,unknown_columns='guess'),'MAP_INVALID')
bad_map('refuse-map-extra-field',dict(mapping,extra='private'),'FIELDS_INVALID')
for name,raw,contract,table_id,report in fixtures:(inputs/(name+'.docx')).write_bytes(raw)
for name,raw,error in bad_docs:(inputs/(name+'.docx')).write_bytes(raw)
for name,raw in map_raw.items():(inputs/('map-'+name+'.json')).write_bytes(raw)
for name,raw,error in bad_maps:(inputs/(name+'.json')).write_bytes(raw)
(inputs/'over-input-bound.docx').write_bytes(b'X'*(4*1024*1024+1))
(inputs/'over-mapping-bound.json').write_bytes(b'X'*(4*1024*1024+1))
(inputs/'hard-document.docx').write_bytes(variant_raw['before']);os.link(inputs/'hard-document.docx',inputs/'hard-document-alias.docx')
(inputs/'hard-mapping.json').write_bytes(map_raw['base']);os.link(inputs/'hard-mapping.json',inputs/'hard-mapping-alias.json')

def snapshot(root):
    value={}
    for path in root.rglob('*'):
        assert not path.is_symlink() and not getattr(path,'is_junction',lambda:False)()
        info=path.lstat();name=path.relative_to(root).as_posix()
        if stat.S_ISDIR(info.st_mode):value[name]=dict(kind='directory')
        else:
            assert stat.S_ISREG(info.st_mode);raw=path.read_bytes();value[name]=dict(kind='file',bytes=len(raw),sha256=sha(raw),links=info.st_nlink)
    return value
audit="""import runpy,sys,zipfile,xml.etree.ElementTree as ET,_elementtree,pyexpat
assert ET.XMLParser is _elementtree.XMLParser and ET.TreeBuilder is _elementtree.TreeBuilder
def deny_extract(*args,**kwargs):raise RuntimeError('FICTIONAL_GUIDE_FORBIDS_ARCHIVE_EXTRACTION')
zipfile.ZipFile.extract=deny_extract;zipfile.ZipFile.extractall=deny_extract
def guard(event,args):
    if event.startswith(('socket.','subprocess.','os.startfile')) or event in ('urllib.Request','webbrowser.open','os.system'):
        raise RuntimeError('FICTIONAL_GUIDE_FORBIDS_REMOTE_OR_PROCESS_ACTION')
sys.addaudithook(guard);script=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(script,run_name='__main__')
"""

outcomes=[];observations=[];report_rows=[];input_hash_observations=0
def run_case(case,args,code,expected,*,script='document_intake.py',readonly=True,helper=None):
    global input_hash_observations
    before=snapshot(work);source_before=snapshot(inputs)
    command=[sys.executable,'-E','-s','-B','-c',helper if helper else audit]
    command+=list(map(str,args)) if helper else [str(module/script),*map(str,args)]
    result=subprocess.run(command,cwd=module,capture_output=True,timeout=30)
    assert result.returncode==code and not result.stderr,(case,result.returncode,result.stdout,result.stderr)
    value=json.loads(result.stdout);assert value==expected,(case,value,expected)
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    after=snapshot(work)
    assert all(after.get(name)==entry for name,entry in before.items()),case
    if readonly:assert after==before,case
    assert snapshot(inputs)==source_before;input_hash_observations+=sum(row['kind']=='file' for row in source_before.values())
    outcomes.append(dict(case=case,exit_code=code));observations.append(dict(case=case,exit_code=code,result=value))
def inspect_case(name,path,contract,table_id,report):
    output=reports/(name+'.json');code=0 if report['status']=='PASS' else 1
    run_case(name,['--input',path,'--mapping',inputs/('map-'+contract+'.json'),'--table',table_id,'--out',output],code,dict(status=report['status'],report_written=True),readonly=False)
    assert output.read_bytes()==encoded(report)
    if os.name!='nt':assert output.stat().st_mode & 0o777==0o600
    report_rows.append(dict(case=name,path=output.relative_to(work).as_posix(),bytes=output.stat().st_size,sha256=sha(output.read_bytes()),source_sha256=report['source_sha256'],mapping_sha256=report['mapping_sha256'],normalized_table_sha256=report['normalized_table_sha256'],content_sha256=report['content_sha256']))
for name,spec in variants.items():
    raw=variant_raw[name];path=generated/(name+'.docx')
    run_case('generate-'+name,['--variant',name,'--out',path],0,dict(status='PASS',fictional=True,bytes=len(raw),sha256=sha(raw)),script='fictional_docx.py',readonly=False)
    assert path.read_bytes()==raw;inspect_case(name+'-intake',path,'base','table-1',variant_expectations[name])
before_path=generated/'before.docx';base_args=['--input',before_path,'--mapping',inputs/'map-base.json','--table','table-1']
run_case('default-report-already-exports-accepted-values',base_args,0,variant_expectations['before'])
for name,raw,contract,table_id,report in fixtures:inspect_case(name,inputs/(name+'.docx'),contract,table_id,report)
for name,raw,error in bad_docs:
    output=reports/(name+'.json');run_case(name,['--input',inputs/(name+'.docx'),'--mapping',inputs/'map-base.json','--table','table-1','--out',output],2,dict(status='ERROR',code=error));assert not output.exists()
for name,raw,error in bad_maps:
    output=reports/(name+'.json');run_case(name,['--input',before_path,'--mapping',inputs/(name+'.json'),'--table','table-1','--out',output],2,dict(status='ERROR',code=error));assert not output.exists()
for name,args,error in (
    ('refuse-unknown-table',['--input',before_path,'--mapping',inputs/'map-base.json','--table','table-9'],'TABLE_SELECTION_NOT_FOUND'),
    ('refuse-missing-explicit-table',['--input',before_path,'--mapping',inputs/'map-base.json'],'ARGUMENTS_INVALID'),
    ('refuse-document-input-bound',['--input',inputs/'over-input-bound.docx','--mapping',inputs/'map-base.json','--table','table-1'],'INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'),
    ('refuse-mapping-input-bound',['--input',before_path,'--mapping',inputs/'over-mapping-bound.json','--table','table-1'],'INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'),
    ('native-hardlink-document-refused',['--input',inputs/'hard-document-alias.docx','--mapping',inputs/'map-base.json','--table','table-1'],'CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'),
    ('native-hardlink-mapping-refused',['--input',before_path,'--mapping',inputs/'hard-mapping-alias.json','--table','table-1'],'CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'),
    ('refuse-overwriting-report',[*base_args,'--out',reports/'before-intake.json'],'INPUT_OR_OUTPUT_REFUSED'),
    ('refuse-document-output-alias',[*base_args,'--out',before_path],'INPUT_OR_OUTPUT_REFUSED'),
    ('refuse-mapping-output-alias',[*base_args,'--out',inputs/'map-base.json'],'INPUT_OR_OUTPUT_REFUSED'),
    ('refuse-source-output',[*base_args,'--out',module/'FICTIONAL-REFUSED.json'],'OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'),
    ('refuse-parent-traversal',['--input',inputs/'..'/'before.docx','--mapping',inputs/'map-base.json','--table','table-1'],'PATH_INVALID')):
    run_case(name,args,2,dict(status='ERROR',code=error))
assert not (module/'FICTIONAL-REFUSED.json').exists()
run_case('refuse-generator-overwrite',['--out',before_path],2,dict(status='ERROR',code='OUTPUT_REFUSED'),script='fictional_docx.py')
failure="""import json,os,sys,toolkit as t,xml.etree.ElementTree as ET,_elementtree,pyexpat
assert ET.XMLParser is _elementtree.XMLParser and ET.TreeBuilder is _elementtree.TreeBuilder
real=os.write;calls=0
def controlled(fd,data):
    global calls
    calls+=1
    if calls==1:return real(fd,data[:5])
    raise OSError('Fictional write interruption')
os.write=controlled
try:t.write_new(sys.argv[1],b'Fictional partial output.\\n')
except OSError:print(json.dumps({'controlled_write_failure':True,'partial_output_retained':True}))
else:raise AssertionError('EXPECTED_WRITE_INTERRUPTION')
finally:os.write=real
"""
run_case('controlled-write-retains-unconfirmed-prefix',[work/'partial-output.bin'],0,dict(controlled_write_failure=True,partial_output_retained=True),readonly=False,helper=failure)
assert (work/'partial-output.bin').read_bytes()==b'Ficti'
run_case('refuse-reusing-partial-output',[*base_args,'--out',work/'partial-output.bin'],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
values={row['case']:json.loads((work/row['path']).read_text(encoding='utf-8')) for row in report_rows}
assert values['whole-batch-invalid-holds-ready']['accepted'] and values['whole-batch-invalid-holds-ready']['ready_for_explicit_review'] is False
assert values['whole-batch-conflict-holds-ready']['accepted'] and values['whole-batch-conflict-holds-ready']['ready_for_explicit_review'] is False
assert values['before-intake']['ready_for_explicit_review'] is True and values['before-intake']['accepted'][0]['source_rows']==[2,4]
for case in values:
    value=values[case];assert value['imported'] is value['source_transformed'] is value['document_properties_exported'] is False
    assert all(marker not in encoded(value) for marker in (b'PRIVATE_INVALID_TOKEN',b'PRIVATE_IGNORED_TOKEN',b'PRIVATE_PROPERTY_SENTINEL',b'Fictional Author'))
assert values['before-intake']['content_sha256']==values['formatting-intake']['content_sha256']
assert values['before-intake']['source_sha256']!=values['formatting-intake']['source_sha256']
for case in ('properties-change-raw-not-content','zip-transport-change-raw-not-content'):
    assert values[case]['content_sha256']==values['before-intake']['content_sha256']
    assert values[case]['source_sha256']!=values['before-intake']['source_sha256']
for name in variants:assert (generated/(name+'.docx')).read_bytes()==variant_raw[name]
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix')
(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode('utf-8'))
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode('utf-8'))
assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,1,2)},
    generator_variants=4,reports_verified=len(report_rows),input_hash_observations=input_hash_observations,
    fixture_files_preserved=len(fixtures)+len(bad_docs)+len(map_raw)+len(bad_maps)+10,partial_output_bytes_retained=5,raw_content_fingerprint_contrasts=3,
    artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,
    unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fictional_document_intake_flow_checked=True,native_file_guards_checked=True,
    real_documents_used=False,document_properties_exported=False,external_resources_followed=False,document_executed=False,
    office_processes_started=False,archives_extracted=False,visible_layout_verified=False,general_word_compatibility_verified=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered outcomes:

```json
[
  {
    "case": "generate-before",
    "exit_code": 0
  },
  {
    "case": "before-intake",
    "exit_code": 0
  },
  {
    "case": "generate-after",
    "exit_code": 0
  },
  {
    "case": "after-intake",
    "exit_code": 0
  },
  {
    "case": "generate-needs-review",
    "exit_code": 0
  },
  {
    "case": "needs-review-intake",
    "exit_code": 1
  },
  {
    "case": "generate-formatting",
    "exit_code": 0
  },
  {
    "case": "formatting-intake",
    "exit_code": 0
  },
  {
    "case": "default-report-already-exports-accepted-values",
    "exit_code": 0
  },
  {
    "case": "whole-batch-invalid-holds-ready",
    "exit_code": 1
  },
  {
    "case": "whole-batch-conflict-holds-ready",
    "exit_code": 1
  },
  {
    "case": "empty-accepted-set-holds-ready",
    "exit_code": 1
  },
  {
    "case": "optional-empty-is-null-not-zero",
    "exit_code": 0
  },
  {
    "case": "typed-decimal-text-null-and-literals",
    "exit_code": 0
  },
  {
    "case": "normalized-decimal-identical-duplicate",
    "exit_code": 0
  },
  {
    "case": "composite-identity-and-canonical-order",
    "exit_code": 0
  },
  {
    "case": "case-and-whitespace-are-literal",
    "exit_code": 0
  },
  {
    "case": "unknown-column-explicit-ignore",
    "exit_code": 0
  },
  {
    "case": "canonical-integer-refusals",
    "exit_code": 1
  },
  {
    "case": "canonical-boolean-refusals",
    "exit_code": 1
  },
  {
    "case": "calendar-date-refusals",
    "exit_code": 1
  },
  {
    "case": "decimal-grammar-and-bound-refusals",
    "exit_code": 1
  },
  {
    "case": "required-empty-refusal",
    "exit_code": 1
  },
  {
    "case": "mapped-text-bound-refusal",
    "exit_code": 1
  },
  {
    "case": "multiline-cell-controls-refused",
    "exit_code": 1
  },
  {
    "case": "properties-change-raw-not-content",
    "exit_code": 0
  },
  {
    "case": "zip-transport-change-raw-not-content",
    "exit_code": 0
  },
  {
    "case": "explicit-second-table-no-header-search",
    "exit_code": 0
  },
  {
    "case": "refuse-duplicate-header",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-header",
    "exit_code": 2
  },
  {
    "case": "refuse-header-alias-inference",
    "exit_code": 2
  },
  {
    "case": "refuse-unmapped-column",
    "exit_code": 2
  },
  {
    "case": "refuse-nonzip-document",
    "exit_code": 2
  },
  {
    "case": "refuse-external-relationship",
    "exit_code": 2
  },
  {
    "case": "refuse-dtd-document",
    "exit_code": 2
  },
  {
    "case": "refuse-unselected-hidden-content",
    "exit_code": 2
  },
  {
    "case": "refuse-invalid-mapping-json",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-mapping-json-key",
    "exit_code": 2
  },
  {
    "case": "refuse-float-mapping-json",
    "exit_code": 2
  },
  {
    "case": "refuse-map-empty-fields",
    "exit_code": 2
  },
  {
    "case": "refuse-map-required-not-boolean",
    "exit_code": 2
  },
  {
    "case": "refuse-map-duplicate-source",
    "exit_code": 2
  },
  {
    "case": "refuse-map-duplicate-target",
    "exit_code": 2
  },
  {
    "case": "refuse-map-optional-identity",
    "exit_code": 2
  },
  {
    "case": "refuse-map-unknown-identity",
    "exit_code": 2
  },
  {
    "case": "refuse-map-target-case",
    "exit_code": 2
  },
  {
    "case": "refuse-map-unknown-columns-policy",
    "exit_code": 2
  },
  {
    "case": "refuse-map-extra-field",
    "exit_code": 2
  },
  {
    "case": "refuse-unknown-table",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-explicit-table",
    "exit_code": 2
  },
  {
    "case": "refuse-document-input-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-mapping-input-bound",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-document-refused",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-mapping-refused",
    "exit_code": 2
  },
  {
    "case": "refuse-overwriting-report",
    "exit_code": 2
  },
  {
    "case": "refuse-document-output-alias",
    "exit_code": 2
  },
  {
    "case": "refuse-mapping-output-alias",
    "exit_code": 2
  },
  {
    "case": "refuse-source-output",
    "exit_code": 2
  },
  {
    "case": "refuse-parent-traversal",
    "exit_code": 2
  },
  {
    "case": "refuse-generator-overwrite",
    "exit_code": 2
  },
  {
    "case": "controlled-write-retains-unconfirmed-prefix",
    "exit_code": 0
  },
  {
    "case": "refuse-reusing-partial-output",
    "exit_code": 2
  }
]
```

The summary verifies 62 cases (18 exit 0 accepted/control, 11 exit 1 review-required reports, 33 exit 2 intended refusals), 23 complete reports, 54 unchanged fixture files, 3,100 per-case input hash observations, three raw/content contrasts, five retained partial bytes, and 79 payload hashes plus one manifest readback: 80 exact workspace files. No unexpected application output or bytecode is accepted. Exit 1 is a meaningful review result, not an approved accepted subset. See [qualification](docs/QUALIFICATION.md), [methodology](docs/METHODOLOGY.md) and the retained [I/O history](IO-SAFETY.md).
