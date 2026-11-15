# Fictional positional document-diff walkthrough

Keep all five runtime/generator files together. From the copied tool directory, generate invented files at new absolute external paths and compare:

```text
python -E -s -B fictional_docx.py --variant before --out NEW_EXTERNAL_BEFORE.docx
python -E -s -B fictional_docx.py --variant after --out NEW_EXTERNAL_AFTER.docx
python -E -s -B document_diff.py --before NEW_EXTERNAL_BEFORE.docx --after NEW_EXTERNAL_AFTER.docx
python -E -s -B document_diff.py --before NEW_EXTERNAL_BEFORE.docx --after NEW_EXTERNAL_AFTER.docx --show-values --out NEW_EXTERNAL_REPORT.json
```

Default reports retain identifying hashes, block IDs, dimensions and coordinates while omitting full changed values. Opt-in values are plain stored content and do not anonymize it. Pairing is positional, including derived IDs/positions; shifts, reorders and renumbering are not semantic moves. Missing cells are null, whereas present empty strings have string hashes. Raw-byte changes can accompany a stored-content match.

Save the Python block verbatim as `fictional_document_diff_walkthrough.py` outside the source directory. Supply the copied runtime directory and an existing trusted private parent, with suitable absolute path syntax in PowerShell 5.1 or a POSIX shell:

```text
python -I -B fictional_document_diff_walkthrough.py COPIED_TOOL_DIRECTORY EXISTING_PRIVATE_PARENT
```

For example, `D:\Private-Review` is a fictional parent placeholder to replace with your own existing private directory. Each run creates and retains a unique child. The program invokes actual generator/diff script entrypoints, checks C XMLParser/TreeBuilder affinity before and after them, and compares complete independently authored expected reports without calling compare(), _summary() or extract() as oracles.

Cases cover all four generator variants, positional classifications, literal values and whitespace, cell LF joining, missing/empty row and column changes, derived-ID renumbering, and raw-versus-content matches from formatting/property/ZIP transport changes. The needs-review generator variant is accepted literal text, not a business decision. No Office, external writer, rendering, document execution, external resource or real document is used.

Exact 512 changed blocks and 4,096 changed cells per paired table are accepted; one-over cases refuse the entire comparison with no output report. Two paired tables may each have 4,096 cell changes. Stored ZIP fixtures keep those cases below other input/parser/expansion limits. Each before/after role separately exercises unsupported input, byte bounds and mandatory hardlink refusal. Every existing workspace artifact and input byte must remain unchanged during later operations.

Inputs are decompressed only in memory without filesystem unpacking. Source-download qualification separately extracts its verified source ZIP. Limits, audit hooks and sampled native checks are not an OS sandbox, hard deadline, hostile-filesystem guarantee or atomic snapshot. A child-only backend fault retains five unconfirmed bytes; the same output name cannot be reused. No automatic deletion, rollback or full metadata preservation is promised.

The program writes 29 exact reports, an observation ledger and a SHA-256 manifest, checking all fixture/report bytes, all four generated DOCX files and five unchanged copied runtime files. It prints fixed case names and counts rather than private host paths. All 106 workspace files remain private. Full values appear only for reported changes; a matching report does not dump unchanged body content.

```python
"""Fictional positional DOCX block/cell comparisons; never run Office."""
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
work=Path(tempfile.mkdtemp(prefix='fictional-document-diff-',dir=parent)).resolve();assert work.parent==parent
runtimes=('document_diff.py','docx_core.py','toolkit.py','native_windows.py','fictional_docx.py')
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

def p_summary(number,position,text,show=False):
    block=dict(kind='paragraph',id='paragraph-'+str(number),position=position,text=text)
    value=dict(kind='paragraph',id=block['id'],sha256=sha(encoded(block)))
    if show:value['value']=text
    return value
def t_summary(number,position,rows,show=False):
    block=dict(kind='table',id='table-'+str(number),position=position,rows=rows)
    value=dict(kind='table',id=block['id'],sha256=sha(encoded(block)),rows=len(rows),columns=len(rows[0]))
    if show:value['value']=rows
    return value
def cell(row,column,left,right,show=False):
    value=dict(row=row,column=column,before_sha256=sha(encoded(left)) if left is not None else None,after_sha256=sha(encoded(right)) if right is not None else None)
    if show:value.update(before=left,after=right)
    return value
def change(position,classification,left,right,cells=None):
    value=dict(position=position,classification=classification,before=left,after=right)
    if cells is not None:value['cell_changes']=cells
    return value
def counts(spec):
    tables=[b['rows'] for b in spec if b['kind']=='table']
    return dict(paragraphs=sum(b['kind']=='paragraph' for b in spec),tables=len(tables),rows=sum(len(rows) for rows in tables),cells=sum(len(row) for rows in tables for row in rows))
def report(left,right,before_spec,after_spec,status,changes,show=False):
    assert status in ('MATCH','DIFFERENCES') and (status=='DIFFERENCES')==bool(changes)
    return dict(format='outlands-document-diff-v1',status=status,comparison='SUPPORTED_STORED_CONTENT_BY_POSITION',
      before_source_sha256=sha(left),after_source_sha256=sha(right),raw_bytes_changed=left!=right,
      before_content_sha256=sha(encoded(model(before_spec))),after_content_sha256=sha(encoded(model(after_spec))),
      before_counts=counts(before_spec),after_counts=counts(after_spec),changes=changes,values_included=show,
      document_properties_compared=False,formatting_compared=False,document_executed=False)
variant_raw={name:pack(parts(spec,bold=name=='formatting')) for name,spec in variants.items()}
def variant_changes(name,show=False):
    if name in ('before','formatting'):return []
    old_rows=before[1]['rows'];new_rows=variants[name][1]['rows']
    rows=([cell(2,2,'12','14',show),cell(3,1,'sample-b','sample-c',show),cell(3,2,'7','5',show),cell(3,3,'2030-01-11','2030-01-12',show),cell(3,4,'false','true',show),
           cell(4,1,'sample-a',None,show),cell(4,2,'12',None,show),cell(4,3,'2030-01-10',None,show),cell(4,4,'true',None,show)] if name=='after' else
          [cell(3,1,'sample-b','sample-a',show),cell(3,2,'7','13',show),cell(3,3,'2030-01-11','2030-01-10',show),cell(3,4,'false','true',show),cell(4,1,'sample-a','sample-c',show),cell(4,2,'12','invalid',show),cell(4,3,'2030-01-10','2030-01-12',show)])
    return [change(1,'CHANGED',p_summary(1,1,before[0]['text'],show),p_summary(1,1,variants[name][0]['text'],show)),
        change(2,'CHANGED',t_summary(1,2,old_rows,show),t_summary(1,2,new_rows,show),rows)]
variant_reports={name:report(variant_raw['before'],variant_raw[name],before,spec,'MATCH' if name in ('before','formatting') else 'DIFFERENCES',variant_changes(name)) for name,spec in variants.items()}
fixtures=[]
def fixture(name,before_spec,after_spec,status,changes,*,show=False,left_parts=None,right_parts=None,stored=False):
    left=pack(parts(before_spec) if left_parts is None else left_parts,stored=stored);right=pack(parts(after_spec) if right_parts is None else right_parts,stored=stored)
    fixtures.append((name,left,right,report(left,right,before_spec,after_spec,status,changes,show),show))
fixture('explicit-values-for-generated-after',before,after,'DIFFERENCES',variant_changes('after',True),show=True)
literal_before=[para('Fictional before')];literal_after=[para('<script>Fictional literal & data</script>')]
fixture('paragraph-default-omits-stored-payload',literal_before,literal_after,'DIFFERENCES',[change(1,'CHANGED',p_summary(1,1,literal_before[0]['text']),p_summary(1,1,literal_after[0]['text']))])
fixture('paragraph-opt-in-is-literal-text',literal_before,literal_after,'DIFFERENCES',[change(1,'CHANGED',p_summary(1,1,literal_before[0]['text'],True),p_summary(1,1,literal_after[0]['text'],True))],show=True)
fixture('added-paragraph-at-tail',[para('A')],[para('A'),para('B')],'DIFFERENCES',[change(2,'ADDED',None,p_summary(2,2,'B'))])
fixture('removed-paragraph-at-tail',[para('A'),para('B')],[para('A')],'DIFFERENCES',[change(2,'REMOVED',p_summary(2,2,'B'),None)])
fixture('paragraph-to-table-kind-change',[para('A')],[table([['A']])],'DIFFERENCES',[change(1,'KIND_CHANGED',p_summary(1,1,'A',True),t_summary(1,1,[['A']],True))],show=True)
fixture('table-to-paragraph-kind-change',[table([['A']])],[para('A')],'DIFFERENCES',[change(1,'KIND_CHANGED',t_summary(1,1,[['A']]),p_summary(1,1,'A'))])
fixture('reordered-paragraphs-are-positional',[para('A'),para('B')],[para('B'),para('A')],'DIFFERENCES',[change(1,'CHANGED',p_summary(1,1,'A'),p_summary(1,1,'B')),change(2,'CHANGED',p_summary(2,2,'B'),p_summary(2,2,'A'))])
fixture('leading-insertion-shifts-later-blocks',[para('A'),para('B')],[para('X'),para('A'),para('B')],'DIFFERENCES',[change(1,'CHANGED',p_summary(1,1,'A'),p_summary(1,1,'X')),change(2,'CHANGED',p_summary(2,2,'B'),p_summary(2,2,'A')),change(3,'ADDED',None,p_summary(3,3,'B'))])
fixture('paragraph-id-renumbering-is-structural',[para('A'),para('B')],[table([['X']]),para('B')],'DIFFERENCES',[change(1,'KIND_CHANGED',p_summary(1,1,'A',True),t_summary(1,1,[['X']],True)),change(2,'CHANGED',p_summary(2,2,'B',True),p_summary(1,2,'B',True))],show=True)
fixture('table-id-renumbering-can-have-zero-cell-changes',[table([['X']]),table([['A']])],[para('X'),table([['A']])],'DIFFERENCES',[change(1,'KIND_CHANGED',t_summary(1,1,[['X']]),p_summary(1,1,'X')),change(2,'CHANGED',t_summary(2,2,[['A']]),t_summary(1,2,[['A']]),[])])
small_old=[['A','B'],['x','1']];small_new=[['A','B'],['x','2']]
fixture('one-cell-coordinate-change',[table(small_old)],[table(small_new)],'DIFFERENCES',[change(1,'CHANGED',t_summary(1,1,small_old),t_summary(1,1,small_new),[cell(2,2,'1','2')])])
fixture('added-empty-cell-is-not-missing',[table([['A']])],[table([['A'],['']])],'DIFFERENCES',[change(1,'CHANGED',t_summary(1,1,[['A']],True),t_summary(1,1,[['A'],['']],True),[cell(2,1,None,'',True)])],show=True)
fixture('removed-empty-cell-becomes-missing',[table([['A'],['']])],[table([['A']])],'DIFFERENCES',[change(1,'CHANGED',t_summary(1,1,[['A'],['']],True),t_summary(1,1,[['A']],True),[cell(2,1,'',None,True)])],show=True)
cols_old=[['A'],['']];cols_new=[['A',''],['','B']]
fixture('added-column-retains-empty-versus-missing',[table(cols_old)],[table(cols_new)],'DIFFERENCES',[change(1,'CHANGED',t_summary(1,1,cols_old,True),t_summary(1,1,cols_new,True),[cell(1,2,None,'',True),cell(2,2,None,'B',True)])],show=True)
fixture('removed-column-retains-empty-versus-missing',[table(cols_new)],[table(cols_old)],'DIFFERENCES',[change(1,'CHANGED',t_summary(1,1,cols_new,True),t_summary(1,1,cols_old,True),[cell(1,2,'',None,True),cell(2,2,'B',None,True)])],show=True)
fixture('added-empty-paragraph-is-a-real-block',[para('A')],[para('A'),para('')],'DIFFERENCES',[change(2,'ADDED',None,p_summary(2,2,'',True))],show=True)
space_before=[para('  Fictional space\tline\nend  ')];space_after=[para(' Fictional space\tline\nend ')]
fixture('stored-space-tab-and-lf-are-literal',space_before,space_after,'DIFFERENCES',[change(1,'CHANGED',p_summary(1,1,space_before[0]['text'],True),p_summary(1,1,space_after[0]['text'],True))],show=True)
cell_spec=copy.deepcopy(before);cell_spec[1]['rows'][0][0]='Record\nSecond'
cell_parts=changed(parts(before),'word/document.xml',b'</w:tc>',b'<w:p><w:r><w:t>Second</w:t></w:r></w:p></w:tc>')
fixture('multiple-cell-paragraphs-join-with-lf',before,cell_spec,'DIFFERENCES',[change(2,'CHANGED',t_summary(1,2,before[1]['rows'],True),t_summary(1,2,cell_spec[1]['rows'],True),[cell(1,1,'Record','Record\nSecond',True)])],show=True,right_parts=cell_parts)
fixture('property-only-match-with-raw-change',before,before,'MATCH',[],show=True,right_parts=parts(before,author='FICTIONAL_PROPERTY_DO_NOT_EXPORT'))
opaque_left=parts(before);opaque_left['word/styles.xml']=b'Fictional opaque style marker A; no style evaluation.'
opaque_left['word/_rels/document.xml.rels']=('<Relationships xmlns="'+P+'"><Relationship Id="styles" Type="'+R+'/styles" Target="styles.xml"/></Relationships>').encode('utf-8')
opaque_right=dict(opaque_left,**{'word/styles.xml':b'Fictional opaque style marker B; still not interpreted.'})
fixture('opaque-style-byte-change-does-not-compare-formatting',before,before,'MATCH',[],left_parts=opaque_left,right_parts=opaque_right)
# Different ZIP transport is represented explicitly, without changing stored blocks.
left=pack(parts(before));right=pack(parts(before),stored=True)
fixtures.append(('zip-transport-only-content-match',left,right,report(left,right,before,before,'MATCH',[]),False))
blocks_old=[para('A')]*512;blocks_new=[para('B')]*512
fixture('exactly-512-changed-blocks',blocks_old,blocks_new,'DIFFERENCES',[change(n,'CHANGED',p_summary(n,n,'A'),p_summary(n,n,'B')) for n in range(1,513)],stored=True)
rows_old=[['A']*32 for n in range(128)];rows_new=[['B']*32 for n in range(128)]
all_cells=[cell(row,col,'A','B') for row in range(1,129) for col in range(1,33)]
fixture('exactly-4096-changed-cells', [table(rows_old)],[table(rows_new)],'DIFFERENCES',[change(1,'CHANGED',t_summary(1,1,rows_old),t_summary(1,1,rows_new),all_cells)],stored=True)
fixture('two-paired-tables-each-have-4096-cell-changes',[table(rows_old),table(rows_old)],[table(rows_new),table(rows_new)],'DIFFERENCES',[change(n,'CHANGED',t_summary(n,n,rows_old),t_summary(n,n,rows_new),all_cells) for n in (1,2)],stored=True)
bad_inputs=[]
base_parts=parts(before)
bad_inputs.extend([
 ('refuse-nonzip',b'Fictional refused DOCX','DOCX_ARCHIVE_INVALID'),
 ('refuse-duplicate-zip-member',pack(base_parts,duplicate='word/document.xml'),'DOCX_ARCHIVE_INVALID'),
 ('refuse-external-relationship',pack(changed(base_parts,'_rels/.rels',b'Target=',b'TargetMode="External" Target='),stored=True),'DOCX_RELATIONSHIP_INVALID'),
 ('refuse-dtd',pack(dict(base_parts,**{'word/document.xml':b'<!DOCTYPE w:document [<!ENTITY fictional "none">]>'+base_parts['word/document.xml']}),stored=True),'XML_DECLARATION_FORBIDDEN'),
 ('refuse-hidden-run',pack(changed(base_parts,'word/document.xml',b'<w:r>',b'<w:r><w:rPr><w:vanish/></w:rPr>'),stored=True),'DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT'),
 ('refuse-nested-table',pack(changed(base_parts,'word/document.xml',b'<w:tc>',b'<w:tc><w:tbl/>'),stored=True),'DOCX_NESTED_OR_UNSUPPORTED_CELL'),
 ('refuse-nonrectangular-table',pack(parts([table([['A','B'],['one']])]),stored=True),'DOCX_TABLE_NOT_RECTANGULAR'),
 ('refuse-empty-document',pack(parts([]),stored=True),'DOCX_EMPTY_DOCUMENT'),
 ('refuse-expanded-part-bound',pack(dict(base_parts,**{'word/document.xml':b'X'*(2*1024*1024+1)}),stored=True),'DOCX_EXPANSION_LIMIT'),
 ('refuse-xml-depth-bound',pack(dict(base_parts,**{'word/document.xml':('<w:document xmlns:w="'+W+'"><w:body>'+'<w:p>'*33+'</w:p>'*33+'</w:body></w:document>').encode('utf-8')}),stored=True),'XML_STRUCTURE_LIMIT')])
overflow_rows_old=[['A']*32 for n in range(129)];overflow_rows_new=[['B']*32 for n in range(128)]+[['B']+['A']*31]
bad_comparisons=[('refuse-513-changed-blocks',pack(parts([para('A')]*513),stored=True),pack(parts([para('B')]*513),stored=True),'BLOCK_CHANGE_LIMIT'),
 ('refuse-4097-changed-cells',pack(parts([table(overflow_rows_old)]),stored=True),pack(parts([table(overflow_rows_new)]),stored=True),'CELL_CHANGE_LIMIT')]
for name,left,right,value,show in fixtures:(inputs/(name+'-before.docx')).write_bytes(left);(inputs/(name+'-after.docx')).write_bytes(right)
for name,raw,error in bad_inputs:(inputs/(name+'.docx')).write_bytes(raw)
for name,left,right,error in bad_comparisons:(inputs/(name+'-before.docx')).write_bytes(left);(inputs/(name+'-after.docx')).write_bytes(right)
for role in ('before','after'):
    (inputs/('over-'+role+'.docx')).write_bytes(b'X'*(4*1024*1024+1));path=inputs/('hard-'+role+'.docx');path.write_bytes(variant_raw['before']);os.link(path,inputs/('hard-'+role+'-alias.docx'))

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
sys.addaudithook(guard);script=sys.argv[1];sys.argv=sys.argv[1:]
try:runpy.run_path(script,run_name='__main__')
finally:assert ET.XMLParser is _elementtree.XMLParser and ET.TreeBuilder is _elementtree.TreeBuilder
"""

outcomes=[];observations=[];report_rows=[];input_hash_observations=0;xml_cli_checks=0
def run_case(case,args,code,expected,*,script='document_diff.py',readonly=True,helper=None):
    global input_hash_observations,xml_cli_checks
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
    if helper is None:xml_cli_checks+=1
def inspect_case(name,left,right,value,show=False):
    args=['--before',left,'--after',right];output=reports/(name+'.json')
    if show:args+=['--show-values']
    code=0 if value['status']=='MATCH' else 1
    run_case(name,[*args,'--out',output],code,dict(status=value['status'],report_written=True),readonly=False)
    assert output.read_bytes()==encoded(value)
    if os.name!='nt':assert output.stat().st_mode & 0o777==0o600
    report_rows.append(dict(case=name,path=output.relative_to(work).as_posix(),bytes=output.stat().st_size,sha256=sha(output.read_bytes()),before_source_sha256=value['before_source_sha256'],after_source_sha256=value['after_source_sha256'],before_content_sha256=value['before_content_sha256'],after_content_sha256=value['after_content_sha256']))
for name,spec in variants.items():
    raw=variant_raw[name];path=generated/(name+'.docx')
    run_case('generate-'+name,['--variant',name,'--out',path],0,dict(status='PASS',fictional=True,bytes=len(raw),sha256=sha(raw)),script='fictional_docx.py',readonly=False)
    assert path.read_bytes()==raw
for name in variants:inspect_case('before-versus-'+name,generated/'before.docx',generated/(name+'.docx'),variant_reports[name])
for name,left,right,value,show in fixtures:inspect_case(name,inputs/(name+'-before.docx'),inputs/(name+'-after.docx'),value,show)
base_args=['--before',generated/'before.docx','--after',generated/'after.docx']
run_case('default-stdout-diff-is-exact',base_args,1,variant_reports['after'])
for name,raw,error in bad_inputs:
    for role in ('before','after'):
        choices=dict(before=generated/'before.docx',after=generated/'after.docx');choices[role]=inputs/(name+'.docx');output=reports/(name+'-'+role+'.json')
        run_case(name+'-'+role,[item for key,path in choices.items() for item in ('--'+key,path)]+['--out',output],2,dict(status='ERROR',code=error));assert not output.exists()
for name,left,right,error in bad_comparisons:
    output=reports/(name+'.json');run_case(name,['--before',inputs/(name+'-before.docx'),'--after',inputs/(name+'-after.docx'),'--out',output],2,dict(status='ERROR',code=error));assert not output.exists()
for role in ('before','after'):
    choices=dict(before=generated/'before.docx',after=generated/'after.docx');choices[role]=inputs/('over-'+role+'.docx')
    run_case('refuse-'+role+'-input-byte-bound',[item for key,path in choices.items() for item in ('--'+key,path)],2,dict(status='ERROR',code='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'))
    choices[role]=inputs/('hard-'+role+'-alias.docx')
    run_case('native-hardlink-'+role+'-refused',[item for key,path in choices.items() for item in ('--'+key,path)],2,dict(status='ERROR',code='CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'))
run_case('refuse-existing-report',[*base_args,'--out',reports/'before-versus-after.json'],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
for role in ('before','after'):run_case('refuse-output-alias-'+role,[*base_args,'--out',generated/(role+'.docx')],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
run_case('refuse-output-in-copied-source',[*base_args,'--out',module/'FICTIONAL-REFUSED.json'],2,dict(status='ERROR',code='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'))
assert not (module/'FICTIONAL-REFUSED.json').exists()
run_case('refuse-parent-traversal',['--before',inputs/'..'/'unselected.docx','--after',generated/'after.docx'],2,dict(status='ERROR',code='PATH_INVALID'))
run_case('refuse-missing-after',['--before',generated/'before.docx'],2,dict(status='ERROR',code='ARGUMENTS_INVALID'))
run_case('refuse-generator-overwrite',['--out',generated/'before.docx'],2,dict(status='ERROR',code='OUTPUT_REFUSED'),script='fictional_docx.py')
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
assert len(values['exactly-512-changed-blocks']['changes'])==512
assert len(values['exactly-4096-changed-cells']['changes'][0]['cell_changes'])==4096
assert [len(row['cell_changes']) for row in values['two-paired-tables-each-have-4096-cell-changes']['changes']]==[4096,4096]
assert values['table-id-renumbering-can-have-zero-cell-changes']['changes'][1]['cell_changes']==[]
assert values['added-empty-cell-is-not-missing']['changes'][0]['cell_changes'][0]['before'] is None
assert values['added-empty-cell-is-not-missing']['changes'][0]['cell_changes'][0]['after']==''
assert b'<script>' not in encoded(values['paragraph-default-omits-stored-payload'])
assert values['paragraph-opt-in-is-literal-text']['changes'][0]['after']['value']==literal_after[0]['text']
for case in ('before-versus-formatting','property-only-match-with-raw-change','opaque-style-byte-change-does-not-compare-formatting','zip-transport-only-content-match'):
    value=values[case];assert value['status']=='MATCH' and value['changes']==[] and value['raw_bytes_changed'] is True and value['before_content_sha256']==value['after_content_sha256']
for value in values.values():
    assert value['document_properties_compared'] is value['formatting_compared'] is value['document_executed'] is False
    assert b'FICTIONAL_PROPERTY_DO_NOT_EXPORT' not in encoded(value)
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
    generator_variants=4,reports_verified=len(report_rows),report_status_counts={status:sum(value['status']==status for value in values.values()) for status in ('MATCH','DIFFERENCES')},
    input_hash_observations=input_hash_observations,fixture_files_preserved=2*len(fixtures)+len(bad_inputs)+2*len(bad_comparisons)+10,
    partial_output_bytes_retained=5,artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,
    child_xml_bindings_verified=xml_cli_checks==len(outcomes)-1,xml_bindings_checked_cli_cases=xml_cli_checks,
    unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fictional_document_diff_flow_checked=True,native_file_guards_checked=True,
    real_documents_used=False,document_properties_compared=False,formatting_compared=False,document_executed=False,external_resources_followed=False,
    office_processes_started=False,archives_extracted=False,visible_layout_verified=False,semantic_move_detection_verified=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered outcomes:

```json
[
  {
    "case": "generate-before",
    "exit_code": 0
  },
  {
    "case": "generate-after",
    "exit_code": 0
  },
  {
    "case": "generate-needs-review",
    "exit_code": 0
  },
  {
    "case": "generate-formatting",
    "exit_code": 0
  },
  {
    "case": "before-versus-before",
    "exit_code": 0
  },
  {
    "case": "before-versus-after",
    "exit_code": 1
  },
  {
    "case": "before-versus-needs-review",
    "exit_code": 1
  },
  {
    "case": "before-versus-formatting",
    "exit_code": 0
  },
  {
    "case": "explicit-values-for-generated-after",
    "exit_code": 1
  },
  {
    "case": "paragraph-default-omits-stored-payload",
    "exit_code": 1
  },
  {
    "case": "paragraph-opt-in-is-literal-text",
    "exit_code": 1
  },
  {
    "case": "added-paragraph-at-tail",
    "exit_code": 1
  },
  {
    "case": "removed-paragraph-at-tail",
    "exit_code": 1
  },
  {
    "case": "paragraph-to-table-kind-change",
    "exit_code": 1
  },
  {
    "case": "table-to-paragraph-kind-change",
    "exit_code": 1
  },
  {
    "case": "reordered-paragraphs-are-positional",
    "exit_code": 1
  },
  {
    "case": "leading-insertion-shifts-later-blocks",
    "exit_code": 1
  },
  {
    "case": "paragraph-id-renumbering-is-structural",
    "exit_code": 1
  },
  {
    "case": "table-id-renumbering-can-have-zero-cell-changes",
    "exit_code": 1
  },
  {
    "case": "one-cell-coordinate-change",
    "exit_code": 1
  },
  {
    "case": "added-empty-cell-is-not-missing",
    "exit_code": 1
  },
  {
    "case": "removed-empty-cell-becomes-missing",
    "exit_code": 1
  },
  {
    "case": "added-column-retains-empty-versus-missing",
    "exit_code": 1
  },
  {
    "case": "removed-column-retains-empty-versus-missing",
    "exit_code": 1
  },
  {
    "case": "added-empty-paragraph-is-a-real-block",
    "exit_code": 1
  },
  {
    "case": "stored-space-tab-and-lf-are-literal",
    "exit_code": 1
  },
  {
    "case": "multiple-cell-paragraphs-join-with-lf",
    "exit_code": 1
  },
  {
    "case": "property-only-match-with-raw-change",
    "exit_code": 0
  },
  {
    "case": "opaque-style-byte-change-does-not-compare-formatting",
    "exit_code": 0
  },
  {
    "case": "zip-transport-only-content-match",
    "exit_code": 0
  },
  {
    "case": "exactly-512-changed-blocks",
    "exit_code": 1
  },
  {
    "case": "exactly-4096-changed-cells",
    "exit_code": 1
  },
  {
    "case": "two-paired-tables-each-have-4096-cell-changes",
    "exit_code": 1
  },
  {
    "case": "default-stdout-diff-is-exact",
    "exit_code": 1
  },
  {
    "case": "refuse-nonzip-before",
    "exit_code": 2
  },
  {
    "case": "refuse-nonzip-after",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-zip-member-before",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-zip-member-after",
    "exit_code": 2
  },
  {
    "case": "refuse-external-relationship-before",
    "exit_code": 2
  },
  {
    "case": "refuse-external-relationship-after",
    "exit_code": 2
  },
  {
    "case": "refuse-dtd-before",
    "exit_code": 2
  },
  {
    "case": "refuse-dtd-after",
    "exit_code": 2
  },
  {
    "case": "refuse-hidden-run-before",
    "exit_code": 2
  },
  {
    "case": "refuse-hidden-run-after",
    "exit_code": 2
  },
  {
    "case": "refuse-nested-table-before",
    "exit_code": 2
  },
  {
    "case": "refuse-nested-table-after",
    "exit_code": 2
  },
  {
    "case": "refuse-nonrectangular-table-before",
    "exit_code": 2
  },
  {
    "case": "refuse-nonrectangular-table-after",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-document-before",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-document-after",
    "exit_code": 2
  },
  {
    "case": "refuse-expanded-part-bound-before",
    "exit_code": 2
  },
  {
    "case": "refuse-expanded-part-bound-after",
    "exit_code": 2
  },
  {
    "case": "refuse-xml-depth-bound-before",
    "exit_code": 2
  },
  {
    "case": "refuse-xml-depth-bound-after",
    "exit_code": 2
  },
  {
    "case": "refuse-513-changed-blocks",
    "exit_code": 2
  },
  {
    "case": "refuse-4097-changed-cells",
    "exit_code": 2
  },
  {
    "case": "refuse-before-input-byte-bound",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-before-refused",
    "exit_code": 2
  },
  {
    "case": "refuse-after-input-byte-bound",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-after-refused",
    "exit_code": 2
  },
  {
    "case": "refuse-existing-report",
    "exit_code": 2
  },
  {
    "case": "refuse-output-alias-before",
    "exit_code": 2
  },
  {
    "case": "refuse-output-alias-after",
    "exit_code": 2
  },
  {
    "case": "refuse-output-in-copied-source",
    "exit_code": 2
  },
  {
    "case": "refuse-parent-traversal",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-after",
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

The summary verifies 69 observations: ten exit 0 accepted/control, 25 exit 1 differences and 34 exit 2 intended refusals. Its 29 reports comprise five matches and 24 differences. It checks 74 unchanged fixture files, 4,830 per-case input hash observations, 68 actual main CLI XML-binding completions (one backend-fault helper excluded), five retained partial bytes, and 105 payload hashes plus one manifest readback: 106 exact files. No unexpected application output or bytecode is accepted. See [qualification](docs/QUALIFICATION.md), [methodology](docs/METHODOLOGY.md) and retained [I/O history](IO-SAFETY.md).
