# Fictional DOCX walkthrough

Use a selected Python interpreter and keep the five runtime files together. From the copied source directory, ordinary commands are:

```text
python -E -s -B fictional_docx.py --variant before --out NEW_EXTERNAL_INPUT.docx
python -E -s -B docx_tables.py --input NEW_EXTERNAL_INPUT.docx
python -E -s -B docx_tables.py --input NEW_EXTERNAL_INPUT.docx --table table-1 --include-paragraphs --out NEW_EXTERNAL_REPORT.json
```

The four generator variants are `before`, `after`, `needs-review` and `formatting`. Values are literal stored strings; `needs-review` does not activate a business-rule validator. The default has no selected table/paragraph values. Opt-in selections expose their content, and hashes remain identifying even with default omission. This is not anonymization.

The complete program below creates only invented DOCX fixtures under a new owned child of an existing private parent. Save the Python block verbatim as `fictional_docx_walkthrough.py` **outside** the source directory. Then run it with the copied module directory and existing private parent as its two arguments. No administrator installation or Python package is required. The program invokes actual generator and CLI script entrypoints using the same interpreter, refuses archive filesystem extraction in those controlled children, verifies complete expected reports without importing the extractor as an oracle, and checks every pre-existing workspace entry remains unchanged during later writes.

For PowerShell 5.1 use an explicit selected executable and absolute paths:

```text
python -I -B fictional_docx_walkthrough.py COPIED_TOOL_DIRECTORY EXISTING_PRIVATE_PARENT
```

For example, `D:\Private-Review` is a fictional parent placeholder; replace it with your own trusted existing directory. The program resolves its arguments and creates one fresh child, so no rerun reuses prior outputs. The same invocation structure works in a POSIX shell with POSIX absolute paths. It prints fixed case names and exit codes rather than host paths. Review its private artifacts locally before sharing anything.

The checks cover all four generator variants, default/explicit selections, caller order, whitespace and cell paragraph LF joining, raw-versus-content fingerprint contrasts, bounded opaque formatting parts, malformed/unsupported ZIP/XML/relationships, unselected-body validation, input and content bounds, mandatory hardlink refusal, no-overwrite and source-output refusal, and one controlled five-byte retained write failure. A failed write does not imply rollback or safe reuse of that destination. Ordinary documents outside the subset may be refused.

Input DOCX members are decompressed only in memory; they are not extracted onto the filesystem. Source-download qualification separately extracts its verified source ZIP. Styles and document properties are not interpreted or exported. No document is executed or rendered, Office is not started, and no external resource is followed. Audit hooks provide selected controlled-case checks, not an operating-system sandbox. Use trusted quiescent inputs and parents; native metadata checks are sampled rather than atomic.

The program writes 18 exact JSON reports, an observation ledger and a SHA-256 manifest. It independently checks input archive bytes, stored-block content hashes, report bytes, all four generated archives, five unchanged copied runtime files and all prior workspace files. Formatting/property/ZIP transport can change the raw input hash without changing the stored-content hash. Neither hash proves visible layout, authenticity or Word compatibility. The guide's temporary files remain private and are never automatically deleted.

```python
"""Fictional DOCX archives and explicit stored-text selections; never run Office."""
import copy
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
work=Path(tempfile.mkdtemp(prefix='fictional-docx-tables-',dir=parent)).resolve();assert work.parent==parent
runtimes=('docx_tables.py','fictional_docx.py','docx_core.py','toolkit.py','native_windows.py')
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
def summary(raw,blocks,selection=(),paragraphs=False):
    tables={row['id']:row for row in blocks if row['kind']=='table'}
    return dict(format='outlands-docx-table-extract-v1',status='PASS',source_sha256=sha(raw),content_sha256=sha(encoded(blocks)),
      counts=dict(paragraphs=sum(row['kind']=='paragraph' for row in blocks),tables=len(tables),rows=sum(len(row['rows']) for row in tables.values()),cells=sum(len(cells) for row in tables.values() for cells in row['rows'])),
      table_index=[dict(id=row['id'],position=row['position'],rows=len(row['rows']),columns=len(row['rows'][0])) for row in tables.values()],
      selected_tables=[tables[key] for key in selection],selected_paragraphs=[row for row in blocks if row['kind']=='paragraph'] if paragraphs else [],
      document_properties_exported=False,external_resources_followed=False,document_executed=False)
def changed(values,name,old,new):
    output=dict(values);assert old in output[name];output[name]=output[name].replace(old,new,1);return output
base_parts=parts(before);variant_raw={name:pack(parts(spec,bold=name=='formatting')) for name,spec in variants.items()}
multi=[table([['Alpha','Value'],['fixture-a','0012']]),para('Fictional middle.'),table([['Beta'],['<script>literal & data</script>']]),para('Fictional tail.')]
space_spec=[para('  Fictional λ & example  ')]
space_parts=changed(parts(space_spec),'word/document.xml',b'</w:t>',b'</w:t><w:tab/><w:t>Next</w:t><w:br/><w:t>Last</w:t>')
space_model=model([para('  Fictional λ & example  \tNext\nLast')])
cell_spec=copy.deepcopy(before);cell_spec[1]['rows'][0][0]='Record\nSecond'
cell_parts=changed(base_parts,'word/document.xml',b'</w:tc>',b'<w:p><w:r><w:t>Second</w:t></w:r></w:p></w:tc>')
opaque=dict(base_parts);opaque['word/styles.xml']=b'Fictional opaque styles; deliberately not interpreted as XML.'
opaque['word/_rels/document.xml.rels']=('<Relationships xmlns="'+P+'"><Relationship Id="styles" Type="'+R+'/styles" Target="styles.xml"/></Relationships>').encode()
accepted=[
 ('multi-two-tables',pack(parts(multi)),model(multi)),
 ('whitespace-unicode-tab-break',pack(space_parts),space_model),
 ('multiple-cell-paragraphs',pack(cell_parts),model(cell_spec)),
 ('changed-properties-only',pack(parts(before,author='SYNTHETIC_PROPERTY_DO_NOT_EXPORT')),model(before)),
 ('same-parts-stored-zip',pack(base_parts,stored=True),model(before)),
 ('opaque-format-parts',pack(opaque),model(before)),
 ('empty-stored-paragraph',pack(parts([para('')])),model([para('')]))]
bad=[
 ('refuse-not-zip',b'Fictional non-archive input','DOCX_ARCHIVE_INVALID'),
 ('refuse-truncated-zip',variant_raw['before'][:50],'DOCX_ARCHIVE_INVALID'),
 ('refuse-duplicate-zip-member',pack(base_parts,duplicate='word/document.xml'),'DOCX_ARCHIVE_INVALID'),
 ('refuse-missing-main-part',pack({k:v for k,v in base_parts.items() if k!='word/document.xml'},stored=True),'DOCX_REQUIRED_PART_MISSING'),
 ('refuse-traversal-part',pack(dict(base_parts,**{'../fictional.xml':b'Fictional refused part'}),stored=True),'DOCX_PART_UNSUPPORTED'),
 ('refuse-macro-part',pack(dict(base_parts,**{'word/vbaProject.bin':b'Fictional refused macro marker'}),stored=True),'DOCX_PART_UNSUPPORTED'),
 ('refuse-macro-content-type',pack(changed(base_parts,'[Content_Types].xml',MAIN.encode(),b'application/vnd.ms-word.document.macroEnabled.main+xml'),stored=True),'DOCX_ACTIVE_CONTENT'),
 ('refuse-external-relationship',pack(changed(base_parts,'_rels/.rels',b'Target=',b'TargetMode="External" Target='),stored=True),'DOCX_RELATIONSHIP_INVALID'),
 ('refuse-traversal-relationship',pack(changed(base_parts,'_rels/.rels',b'Target="word/document.xml"',b'Target="../word/document.xml"'),stored=True),'DOCX_RELATIONSHIP_INVALID'),
 ('refuse-missing-main-relationship',pack(changed(base_parts,'_rels/.rels',('<Relationship Id="main" Type="'+R+'/officeDocument" Target="word/document.xml"/>').encode(),b''),stored=True),'DOCX_MAIN_RELATIONSHIP_MISSING'),
 ('refuse-unbound-format-part',pack(dict(base_parts,**{'word/styles.xml':b'Fictional unbound style'}),stored=True),'DOCX_UNBOUND_PART'),
 ('refuse-wrong-main-content-type',pack(changed(base_parts,'[Content_Types].xml',MAIN.encode(),b'application/xml'),stored=True),'DOCX_MAIN_TYPE_INVALID'),
 ('refuse-dtd',pack(dict(base_parts,**{'word/document.xml':b'<!DOCTYPE w:document [<!ENTITY sample "Fictional">]>'+base_parts['word/document.xml']}),stored=True),'XML_DECLARATION_FORBIDDEN'),
 ('refuse-processing-instruction',pack(dict(base_parts,**{'word/document.xml':b'<?fictional data?>'+base_parts['word/document.xml']}),stored=True),'XML_PROCESSING_INSTRUCTION_FORBIDDEN'),
 ('refuse-xml-comment',pack(changed(base_parts,'word/document.xml',b'<w:body>',b'<w:body><!-- fictional -->'),stored=True),'XML_COMMENT_FORBIDDEN'),
 ('refuse-direct-hidden-run',pack(changed(base_parts,'word/document.xml',b'<w:r>',b'<w:r><w:rPr><w:vanish/></w:rPr>'),stored=True),'DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT'),
 ('refuse-field',pack(changed(base_parts,'word/document.xml',b'<w:r>',b'<w:r><w:fldSimple/>'),stored=True),'DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT'),
 ('refuse-tracked-change',pack(changed(base_parts,'word/document.xml',b'<w:body>',b'<w:body><w:ins/>'),stored=True),'DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT'),
 ('refuse-hyperlink',pack(changed(base_parts,'word/document.xml',b'<w:r>',b'<w:r><w:hyperlink/>'),stored=True),'DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT'),
 ('refuse-merged-cell',pack(changed(base_parts,'word/document.xml',b'<w:tc>',b'<w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr>'),stored=True),'DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT'),
 ('refuse-nested-table',pack(changed(base_parts,'word/document.xml',b'<w:tc>',b'<w:tc><w:tbl/>'),stored=True),'DOCX_NESTED_OR_UNSUPPORTED_CELL'),
 ('refuse-nonrectangular-table',pack(parts([table([['A','B'],['Only one']])]),stored=True),'DOCX_TABLE_NOT_RECTANGULAR'),
 ('refuse-wrong-grid-width',pack(changed(base_parts,'word/document.xml',b'<w:tbl>',b'<w:tbl><w:tblGrid><w:gridCol/></w:tblGrid>'),stored=True),'DOCX_GRID_INVALID'),
 ('refuse-property-text-payload',pack(changed(base_parts,'word/document.xml',b'<w:p>',b'<w:p><w:pPr><w:t>Fictional hidden payload</w:t></w:pPr>'),stored=True),'DOCX_PROPERTY_PAYLOAD_UNSUPPORTED'),
 ('refuse-unknown-body-element',pack(changed(base_parts,'word/document.xml',b'<w:body>',b'<w:body><w:unknown/>'),stored=True),'DOCX_BODY_FEATURE_UNSUPPORTED'),
 ('refuse-empty-document',pack(parts([]),stored=True),'DOCX_EMPTY_DOCUMENT'),
 ('refuse-empty-table',pack(parts([table([])]),stored=True),'DOCX_EMPTY_TABLE'),
 ('refuse-paragraph-character-bound',pack(parts([para('X'*4097)]),stored=True),'DOCX_TEXT_LIMIT'),
 ('refuse-column-bound',pack(parts([table([['X']*33])]),stored=True),'DOCX_ROW_FEATURE_UNSUPPORTED'),
 ('refuse-paragraph-count-bound',pack(parts([para('X')]*2001),stored=True),'DOCX_CONTENT_LIMIT'),
 ('refuse-table-count-bound',pack(parts([table([['X']])]*33),stored=True),'DOCX_CONTENT_LIMIT'),
 ('refuse-expansion-ratio',pack({name:b'X'*100000 for name in ('[Content_Types].xml','_rels/.rels','word/document.xml')}),'DOCX_EXPANSION_LIMIT'),
 ('refuse-expanded-part-bound',pack(dict(base_parts,**{'word/document.xml':b'X'*(2*1024*1024+1)}),stored=True),'DOCX_EXPANSION_LIMIT')]
unselected_parts=parts([table([['Supported first']]),table([['Unsupported second']])])
unselected_parts=changed(unselected_parts,'word/document.xml',b'Unsupported second',b'Unsupported second</w:t><w:rPr><w:vanish/></w:rPr><w:t>')
unselected_raw=pack(unselected_parts,stored=True)
for name,raw,blocks in accepted:(inputs/(name+'.docx')).write_bytes(raw)
for name,raw,error in bad:(inputs/(name+'.docx')).write_bytes(raw)
(inputs/'unsupported-unselected-table.docx').write_bytes(unselected_raw)
(inputs/'over-input-bound.docx').write_bytes(b'X'*(4*1024*1024+1))
(inputs/'hard-original.docx').write_bytes(variant_raw['before']);os.link(inputs/'hard-original.docx',inputs/'hard-alias.docx')
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
def run_case(case,args,code,expected,*,script='docx_tables.py',readonly=True,helper=None):
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
def inspect_case(case,path,raw,blocks,selection=(),paragraphs=False):
    args=['--input',path];output=reports/(case+'.json')
    for key in selection:args+=['--table',key]
    if paragraphs:args+=['--include-paragraphs']
    args+=['--out',output]
    run_case(case,args,0,dict(status='PASS',report_written=True),readonly=False)
    expected=summary(raw,blocks,selection,paragraphs);assert output.read_bytes()==encoded(expected)
    if os.name!='nt':assert output.stat().st_mode & 0o777==0o600
    report_rows.append(dict(case=case,path=output.relative_to(work).as_posix(),bytes=output.stat().st_size,sha256=sha(output.read_bytes()),source_sha256=sha(raw),content_sha256=expected['content_sha256']))
for name,spec in variants.items():
    raw=variant_raw[name];path=generated/(name+'.docx')
    run_case('generate-'+name,['--variant',name,'--out',path],0,dict(status='PASS',fictional=True,bytes=len(raw),sha256=sha(raw)),script='fictional_docx.py',readonly=False)
    assert path.read_bytes()==raw
    inspect_case(name+'-default',path,raw,model(spec))
    inspect_case(name+'-selected',path,raw,model(spec),('table-1',),True)
before_path=generated/'before.docx';before_raw=variant_raw['before'];before_model=model(before)
run_case('default-stdout-is-exact',['--input',before_path],0,summary(before_raw,before_model))
inspect_case('table-only-no-paragraphs',before_path,before_raw,before_model,('table-1',),False)
inspect_case('paragraphs-only-no-tables',before_path,before_raw,before_model,(),True)
accepted_map={name:(raw,blocks) for name,raw,blocks in accepted}
for case,name,selection,paragraphs in (
    ('multi-default','multi-two-tables',(),False),
    ('caller-order-two-then-one','multi-two-tables',('table-2','table-1'),True),
    ('whitespace-and-unicode-preserved','whitespace-unicode-tab-break',(),True),
    ('cell-paragraphs-join-with-lf','multiple-cell-paragraphs',('table-1',),False),
    ('property-change-not-exported','changed-properties-only',('table-1',),True),
    ('zip-transport-change-keeps-content-hash','same-parts-stored-zip',('table-1',),True),
    ('opaque-styles-not-evaluated','opaque-format-parts',('table-1',),True),
    ('empty-paragraph-is-stored-content','empty-stored-paragraph',(),True)):
    raw,blocks=accepted_map[name];inspect_case(case,inputs/(name+'.docx'),raw,blocks,selection,paragraphs)
for name,raw,error in bad:
    output=reports/(name+'.json')
    run_case(name,['--input',inputs/(name+'.docx'),'--out',output],2,dict(status='ERROR',code=error));assert not output.exists()
for case,args,error in (
    ('refuse-unknown-table',['--table','table-9'],'TABLE_SELECTION_NOT_FOUND'),
    ('refuse-duplicate-table-selection',['--table','table-1','--table','table-1'],'SELECTION_INVALID'),
    ('refuse-case-changed-table-id',['--table','TABLE-1'],'TABLE_SELECTION_NOT_FOUND'),
    ('refuse-selection-count-bound',['--table','table-1']*33,'SELECTION_INVALID')):
    run_case(case,['--input',before_path,*args],2,dict(status='ERROR',code=error))
run_case('unselected-content-still-validated',['--input',inputs/'unsupported-unselected-table.docx','--table','table-1'],2,dict(status='ERROR',code='DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT'))
run_case('refuse-input-byte-bound',['--input',inputs/'over-input-bound.docx'],2,dict(status='ERROR',code='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'))
run_case('native-hardlink-input-refused',['--input',inputs/'hard-alias.docx'],2,dict(status='ERROR',code='CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'))
run_case('refuse-existing-report',['--input',before_path,'--out',reports/'before-default.json'],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
run_case('refuse-input-output-alias',['--input',before_path,'--out',before_path],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
run_case('refuse-source-output',['--input',before_path,'--out',module/'FICTIONAL-REFUSED.json'],2,dict(status='ERROR',code='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'))
assert not (module/'FICTIONAL-REFUSED.json').exists()
run_case('refuse-parent-traversal',['--input',inputs/'..'/'before.docx'],2,dict(status='ERROR',code='PATH_INVALID'))
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
run_case('refuse-reusing-partial-output',['--input',before_path,'--out',work/'partial-output.bin'],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
values={row['case']:json.loads((work/row['path']).read_bytes()) for row in report_rows}
for name in variants:
    value=values[name+'-default'];assert value['selected_tables']==value['selected_paragraphs']==[]
    assert all(marker not in encoded(value) for marker in (b'Fictional intake',b'sample-a',b'Fictional Author',b'SYNTHETIC_PROPERTY_DO_NOT_EXPORT'))
assert values['before-default']['content_sha256']==values['formatting-default']['content_sha256']
assert values['before-default']['source_sha256']!=values['formatting-default']['source_sha256']
for case in ('property-change-not-exported','zip-transport-change-keeps-content-hash','opaque-styles-not-evaluated'):
    assert values[case]['content_sha256']==values['before-default']['content_sha256']
    assert values[case]['source_sha256']!=values['before-default']['source_sha256']
    assert b'SYNTHETIC_PROPERTY_DO_NOT_EXPORT' not in encoded(values[case])
for name,spec in variants.items():assert (generated/(name+'.docx')).read_bytes()==variant_raw[name]
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix')
(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode())
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode())
assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,2)},
    generator_variants=4,reports_verified=len(report_rows),input_hash_observations=input_hash_observations,
    fixture_files_preserved=len(accepted)+len(bad)+8,partial_output_bytes_retained=5,raw_content_fingerprint_contrasts=4,
    artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,
    unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fictional_docx_flow_checked=True,native_file_guards_checked=True,
    real_documents_used=False,document_properties_exported=False,external_resources_followed=False,document_executed=False,
    office_processes_started=False,archives_extracted=False,visible_layout_verified=False,general_word_compatibility_verified=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered outcomes (exit 0 means accepted/control succeeded; exit 2 means the intended refusal):

```json
[
  {
    "case": "generate-before",
    "exit_code": 0
  },
  {
    "case": "before-default",
    "exit_code": 0
  },
  {
    "case": "before-selected",
    "exit_code": 0
  },
  {
    "case": "generate-after",
    "exit_code": 0
  },
  {
    "case": "after-default",
    "exit_code": 0
  },
  {
    "case": "after-selected",
    "exit_code": 0
  },
  {
    "case": "generate-needs-review",
    "exit_code": 0
  },
  {
    "case": "needs-review-default",
    "exit_code": 0
  },
  {
    "case": "needs-review-selected",
    "exit_code": 0
  },
  {
    "case": "generate-formatting",
    "exit_code": 0
  },
  {
    "case": "formatting-default",
    "exit_code": 0
  },
  {
    "case": "formatting-selected",
    "exit_code": 0
  },
  {
    "case": "default-stdout-is-exact",
    "exit_code": 0
  },
  {
    "case": "table-only-no-paragraphs",
    "exit_code": 0
  },
  {
    "case": "paragraphs-only-no-tables",
    "exit_code": 0
  },
  {
    "case": "multi-default",
    "exit_code": 0
  },
  {
    "case": "caller-order-two-then-one",
    "exit_code": 0
  },
  {
    "case": "whitespace-and-unicode-preserved",
    "exit_code": 0
  },
  {
    "case": "cell-paragraphs-join-with-lf",
    "exit_code": 0
  },
  {
    "case": "property-change-not-exported",
    "exit_code": 0
  },
  {
    "case": "zip-transport-change-keeps-content-hash",
    "exit_code": 0
  },
  {
    "case": "opaque-styles-not-evaluated",
    "exit_code": 0
  },
  {
    "case": "empty-paragraph-is-stored-content",
    "exit_code": 0
  },
  {
    "case": "refuse-not-zip",
    "exit_code": 2
  },
  {
    "case": "refuse-truncated-zip",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-zip-member",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-main-part",
    "exit_code": 2
  },
  {
    "case": "refuse-traversal-part",
    "exit_code": 2
  },
  {
    "case": "refuse-macro-part",
    "exit_code": 2
  },
  {
    "case": "refuse-macro-content-type",
    "exit_code": 2
  },
  {
    "case": "refuse-external-relationship",
    "exit_code": 2
  },
  {
    "case": "refuse-traversal-relationship",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-main-relationship",
    "exit_code": 2
  },
  {
    "case": "refuse-unbound-format-part",
    "exit_code": 2
  },
  {
    "case": "refuse-wrong-main-content-type",
    "exit_code": 2
  },
  {
    "case": "refuse-dtd",
    "exit_code": 2
  },
  {
    "case": "refuse-processing-instruction",
    "exit_code": 2
  },
  {
    "case": "refuse-xml-comment",
    "exit_code": 2
  },
  {
    "case": "refuse-direct-hidden-run",
    "exit_code": 2
  },
  {
    "case": "refuse-field",
    "exit_code": 2
  },
  {
    "case": "refuse-tracked-change",
    "exit_code": 2
  },
  {
    "case": "refuse-hyperlink",
    "exit_code": 2
  },
  {
    "case": "refuse-merged-cell",
    "exit_code": 2
  },
  {
    "case": "refuse-nested-table",
    "exit_code": 2
  },
  {
    "case": "refuse-nonrectangular-table",
    "exit_code": 2
  },
  {
    "case": "refuse-wrong-grid-width",
    "exit_code": 2
  },
  {
    "case": "refuse-property-text-payload",
    "exit_code": 2
  },
  {
    "case": "refuse-unknown-body-element",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-document",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-table",
    "exit_code": 2
  },
  {
    "case": "refuse-paragraph-character-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-column-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-paragraph-count-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-table-count-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-expansion-ratio",
    "exit_code": 2
  },
  {
    "case": "refuse-expanded-part-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-unknown-table",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-table-selection",
    "exit_code": 2
  },
  {
    "case": "refuse-case-changed-table-id",
    "exit_code": 2
  },
  {
    "case": "refuse-selection-count-bound",
    "exit_code": 2
  },
  {
    "case": "unselected-content-still-validated",
    "exit_code": 2
  },
  {
    "case": "refuse-input-byte-bound",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-input-refused",
    "exit_code": 2
  },
  {
    "case": "refuse-existing-report",
    "exit_code": 2
  },
  {
    "case": "refuse-input-output-alias",
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

The summary additionally checks 70 cases (24 exit 0, 46 exit 2), 48 unchanged fixture files, 3,080 per-case input hash observations, 18 reports, four raw/content fingerprint contrasts, five retained partial bytes, and 68 payload hashes plus one manifest readback: 69 workspace files. No bytecode or unexpected application file is accepted. These checks concern this fictional walkthrough, not real documents, Word compatibility or a production workflow. See [qualification](docs/QUALIFICATION.md), [current behavior](README.md) and the retained [I/O history](IO-SAFETY.md).
