# Fictional CSV and workbook intake walkthrough

This exercise constructs invented tables and expected full reports independently
of the intake parser. It uses only copied runtime files and never opens real
workbooks, Excel, network resources or a data store. It checks CSV/inline/shared
string parity, explicit mapping and typed accounting, sparse cells, exact sheet
selection and refusals, including a formula on an unselected sheet.

Use Python from the pinned qualification build, without `-O` or `-OO`: assertions
are part of this exercise. Copy `intake.py`, `toolkit.py`, `native_windows.py` and
`fictional_workbook.py` into a trusted source directory. No pip packages are needed.
Create a separate, empty private parent directory outside that source directory.
Save the following Python block as `fictional_workbook_intake_walkthrough.py`
outside both directories. Run it with the source directory and private parent as
its two arguments. Example directory names are fictional; choose your own paths.

```text
python -I -B fictional_workbook_intake_walkthrough.py "D:\Fictional-Source" "D:\Private-Review"
python -I -B fictional_workbook_intake_walkthrough.py "/home/example/fictional-source" "/home/example/private-review"
```

The first command is a Windows example; the second is a POSIX example. Each run
creates one new child directory and retains all authored fixtures, the generated
workbook, 28 exact reports, an observation ledger, a five-byte controlled-failure
artifact and a manifest. Earlier files must remain byte-identical after every
case. The exercise checks the C XML bindings and C Decimal/default context before
and after each actual script entry point. The separate fault helper tests partial
retention; it is not a second CLI or a completed report.

The 78 expected outcomes below include 19 exit-0 results, 12 review results and
47 controlled refusals. There are 77 actual script entry-point checks and one
controlled backend write-failure case. No real-input safety verdict follows.

```python
"""Fictional CSV/XLSX intake with independently authored complete reports."""
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
work=Path(tempfile.mkdtemp(prefix='fictional-workbook-intake-',dir=parent)).resolve();assert work.parent==parent
runtimes=('intake.py','toolkit.py','native_windows.py','fictional_workbook.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
runtime_hashes={name:sha((module/name).read_bytes()) for name in runtimes}
inputs=work/'inputs';reports=work/'reports'
generated=work/'generated'
inputs.mkdir();reports.mkdir();generated.mkdir()


S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'

def escape(value):return value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def column(number):return (chr(64+(number-1)//26) if number>26 else '')+chr(65+(number-1)%26)
def worksheet(rows,*,shared=None):
    output=[]
    for r,row in enumerate(rows,1):
        cells=[]
        for c,value in enumerate(row,1):
            ref=column(c)+str(r)
            if value is None:continue
            if isinstance(value,dict):
                kind=value['kind'];text=value['value'];attrs=value.get('attrs','')
                cell='<c r="'+ref+'" t="'+kind+'"'+attrs+'><v>'+escape(text)+'</v></c>'
            elif shared is not None:cell='<c r="'+ref+'" t="s"><v>'+str(shared.index(value))+'</v></c>'
            else:cell='<c r="'+ref+'" t="inlineStr"><is><t>'+escape(value)+'</t></is></c>'
            cells.append(cell)
        output.append('<row r="'+str(r)+'">'+''.join(cells)+'</row>')
    return ('<worksheet xmlns="'+S+'"><sheetData>'+''.join(output)+'</sheetData></worksheet>').encode('utf-8')

def parts(rows,*,shared=False,second=None):
    values=list(dict.fromkeys(value for row in rows for value in row)) if shared else None
    sheets=[('Records',rows)]+([('Second',second)] if second is not None else [])
    overrides=''.join('<Override PartName="/xl/worksheets/sheet'+str(i)+'.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1))
    values_xml='<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>' if shared else ''
    output={
      '[Content_Types].xml':('<Types xmlns="'+C+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'+overrides+values_xml+'</Types>').encode(),
      '_rels/.rels':('<Relationships xmlns="'+P+'"><Relationship Id="rId1" Type="'+R+'/officeDocument" Target="xl/workbook.xml"/></Relationships>').encode(),
      'xl/workbook.xml':('<workbook xmlns="'+S+'" xmlns:r="'+R+'"><sheets>'+''.join('<sheet name="'+name+'" sheetId="'+str(i)+'" r:id="rId'+str(i)+'"/>' for i,(name,_) in enumerate(sheets,1))+'</sheets></workbook>').encode(),
      'xl/_rels/workbook.xml.rels':('<Relationships xmlns="'+P+'">'+''.join('<Relationship Id="rId'+str(i)+'" Type="'+R+'/worksheet" Target="worksheets/sheet'+str(i)+'.xml"/>' for i in range(1,len(sheets)+1))+('<Relationship Id="rId'+str(len(sheets)+1)+'" Type="'+R+'/sharedStrings" Target="sharedStrings.xml"/>' if shared else '')+'</Relationships>').encode()}
    for i,(_,data) in enumerate(sheets,1):output['xl/worksheets/sheet'+str(i)+'.xml']=worksheet(data,shared=values)
    if shared:output['xl/sharedStrings.xml']=('<sst xmlns="'+S+'">'+''.join('<si><t>'+escape(v)+'</t></si>' for v in values)+'</sst>').encode('utf-8')
    return output

def pack(values,*,stored=False,duplicate=None):
    output=io.BytesIO()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always',UserWarning)
        with zipfile.ZipFile(output,'w') as archive:
            for name,raw in sorted(values.items())+([(duplicate,values[duplicate])] if duplicate else []):
                info=zipfile.ZipInfo(name,date_time=(2030,1,1,0,0,0));info.compress_type=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
                archive.writestr(info,raw)
        assert len(notices)==(1 if duplicate else 0)
    return output.getvalue()

def changed(values,name,old,new):
    output=dict(values);assert old in output[name];output[name]=output[name].replace(old,new,1);return output
def csv_bytes(rows):
    output=io.StringIO(newline='');csv.writer(output,lineterminator='\n').writerows(rows);return output.getvalue().encode('utf-8')
def field(source,target,kind='text',required=True):return dict(source=source,target=target,type=kind,required=required)
mapping=dict(format='outlands-table-map-v1',identity=['record_id'],unknown_columns='reject',fields=[field('Record','record_id'),field('Units','units','integer'),field('Due','due','date'),field('Active','active','boolean')])
maps={'base':mapping,'ignore-extra':dict(mapping,unknown_columns='ignore'),
 'optional-units':dict(mapping,fields=[mapping['fields'][0],field('Units','units','integer',False),*mapping['fields'][2:]]),
 'composite':dict(mapping,identity=['record_id','due']),
 'extended':dict(mapping,fields=[*mapping['fields'],field('Price','price','decimal'),field('Note','note','text',False)]),
 'date-as-text':dict(mapping,fields=[*mapping['fields'][:2],field('Due','due'),mapping['fields'][3]])}
map_raw={name:encoded(value) for name,value in maps.items()}
def rec(key,units=12,due='2030-01-10',active=True,**extra):return dict(record_id=key,units=units,due=due,active=active,**extra)
def accepted_record(record,rows):return dict(record=record,source_rows=rows)
def problem(row,code):return dict(row=row,code=code)
def expected(raw,kind,sheet,contract,n,accepted,issues,*,duplicates=0,conflicts=0,ignored=0):
    counts=dict(input_rows=n,accepted_records=len(accepted),duplicate_rows=duplicates,rejected_rows=sum(row['code']!='IDENTITY_CONFLICT' for row in issues),conflict_rows=conflicts)
    assert n==sum(counts[key] for key in ('accepted_records','duplicate_rows','rejected_rows','conflict_rows'))
    status='PASS' if accepted and not issues else 'REVIEW_REQUIRED'
    return dict(format='outlands-intake-preview-v1',status=status,source_sha256=sha(raw),mapping_sha256=sha(map_raw[contract]),source_format=kind,sheet=sheet,mapping=maps[contract]['fields'],ignored_columns=ignored,counts=counts,accepted=accepted,issues=list(issues),ready_for_explicit_review=status=='PASS',imported=False)
header=['Record','Units','Due','Active']
base_rows=[header,['sample-a','12','2030-01-10','true'],['sample-b','7','2030-01-11','false'],['sample-a','12','2030-01-10','true']]
base_accepted=[accepted_record(rec('sample-a'),[2,4]),accepted_record(rec('sample-b',7,'2030-01-11',False),[3])]
generated_raw=pack(parts(base_rows))
generated_expected=expected(generated_raw,'xlsx','Records','base',3,base_accepted,[],duplicates=1)
fixtures=[]
def fixture(name,rows,accepted,issues=(),*,contract='base',duplicates=0,conflicts=0,ignored=0,kind='csv',shared=False,values=None,sheet='Records',n=None):
    raw=csv_bytes(rows) if kind=='csv' else pack(parts(rows,shared=shared) if values is None else values,stored=values is not None)
    report=expected(raw,kind,None if kind=='csv' else sheet,contract,len(rows)-1 if n is None else n,accepted,issues,duplicates=duplicates,conflicts=conflicts,ignored=ignored)
    fixtures.append((name,raw,kind,None if kind=='csv' else sheet,contract,report))
for name,kind,shared in [('csv-parity','csv',False),('inline-parity','xlsx',False),('shared-parity','xlsx',True)]:fixture(name,base_rows,base_accepted,duplicates=1,kind=kind,shared=shared)
fixture('invalid-row-holds-batch-ready',[header,['safe-a','2','2030-01-10','true'],['bad-a','PRIVATE_INVALID_TOKEN','2030-01-10','true']],[accepted_record(rec('safe-a',2),[2])],[problem(3,'VALUE_INTEGER_INVALID')])
fixture('conflict-withholds-every-group-member',[header,['group-a','1','2030-01-10','true'],['group-a','2','2030-01-10','true'],['group-a','1','2030-01-10','true'],['safe-a','3','2030-01-10','true']],[accepted_record(rec('safe-a',3),[5])],[problem(row,'IDENTITY_CONFLICT') for row in (2,3,4)],conflicts=3)
for kind in ('csv','xlsx'):fixture(kind+'-header-only-is-review',[header],[],kind=kind)
fixture('optional-empty-is-null-not-zero',[header,['empty-a','','2030-01-10','false'],['zero-a','0','2030-01-10','false']],[accepted_record(rec('empty-a',None,active=False),[2]),accepted_record(rec('zero-a',0,active=False),[3])],contract='optional-units')
fixture('decimal-text-and-literal-text',[header+['Price','Note'],['typed-a','0','2032-02-29','false','1.230000',''],['typed-b','-2','2030-01-10','true','-2.500000','  literal # $ \\ lambda λ  ']],[accepted_record(rec('typed-a',0,'2032-02-29',False,price='1.23',note=None),[2]),accepted_record(rec('typed-b',-2,price='-2.5',note='  literal # $ \\ lambda λ  '),[3])],contract='extended')
fixture('decimal-normalized-identical-duplicate',[header+['Price','Note'],['same-a','0','2030-01-10','true','1.230000',''],['same-a','0','2030-01-10','true','1.23','']],[accepted_record(rec('same-a',0,price='1.23',note=None),[2,3])],contract='extended',duplicates=1)
fixture('negative-zero-remains-signed',[header+['Price','Note'],['signed-a','0','2030-01-10','true','-0.000000',''],['signed-a','0','2030-01-10','true','0','']],[],[problem(2,'IDENTITY_CONFLICT'),problem(3,'IDENTITY_CONFLICT')],contract='extended',conflicts=2)
fixture('decimal-boundaries-are-exact-at-default-context',[header+['Price','Note'],['bound-a','1000000000000','2030-01-10','true','999999999999.999999',''],['bound-b','-1000000000000','2030-01-10','false','-1000000000000.000000','']],[accepted_record(rec('bound-a',10**12,price='999999999999.999999',note=None),[2]),accepted_record(rec('bound-b',-10**12,active=False,price='-1000000000000',note=None),[3])],contract='extended')
fixture('composite-identity-and-order',[header,['same-a','2','2030-01-11','true'],['same-a','1','2030-01-10','true']],[accepted_record(rec('same-a',1),[3]),accepted_record(rec('same-a',2,'2030-01-11'),[2])],contract='composite')
fixture('case-and-space-are-literal',[header,['sample-a','2','2030-01-10','true'],['Sample-a','1','2030-01-10','true'],[' sample-a ','3','2030-01-10','true']],[accepted_record(rec(' sample-a ',3),[4]),accepted_record(rec('Sample-a',1),[3]),accepted_record(rec('sample-a',2),[2])])
fixture('explicit-ignore-counts-column',[header+['Private extra'],['sample-a','2','2030-01-10','true','PRIVATE_IGNORED_TOKEN']],[accepted_record(rec('sample-a',2),[2])],contract='ignore-extra',ignored=1)
fixture('canonical-integer-rejections',[header,*[[f'bad-{i}',value,'2030-01-10','true'] for i,value in enumerate(('01','1.0','-0','+1','1000000000001'))]],[],[problem(row,'VALUE_INTEGER_INVALID') for row in range(2,7)])
fixture('boolean-and-calendar-rejections',[header,['bad-a','1','2030-01-10','TRUE'],['bad-b','1','2031-02-29','true']],[],[problem(2,'VALUE_BOOLEAN_INVALID'),problem(3,'VALUE_DATE_INVALID')])
fixture('decimal-grammar-refusals',[header+['Price','Note'],*[[f'bad-{i}','1','2030-01-10','true',value,''] for i,value in enumerate(('1e2','1.0000001','1000000000000.000001'))]],[],[problem(row,'VALUE_DECIMAL_INVALID') for row in range(2,5)],contract='extended')
fixture('required-text-length-and-ascii-controls',[header,['required-a','','2030-01-10','true'],['X'*257,'1','2030-01-10','true'],['line\nbreak','1','2030-01-10','true'],['delete\x7fmarker','1','2030-01-10','true']],[],[problem(2,'REQUIRED_VALUE_MISSING'),*[problem(row,'VALUE_TEXT_INVALID') for row in (3,4,5)]])
fixture('csv-blank-record-is-accounted',[header,['safe-a','2','2030-01-10','true'],[]],[accepted_record(rec('safe-a',2),[2])],[problem(3,'ROW_WIDTH_INVALID')])
fixture('csv-short-row-is-rejected',[header,['short-a','1']],[],[problem(2,'ROW_WIDTH_INVALID')])
sparse=[header,['sparse-a',None,'2030-01-10','false']]
fixture('xlsx-sparse-cell-becomes-optional-null',sparse,[accepted_record(rec('sparse-a',None,active=False),[2])],kind='xlsx',contract='optional-units')
typed=[header,['typed-a',dict(kind='n',value='12'),dict(kind='d',value='2030-01-10'),dict(kind='b',value='1')]]
fixture('xlsx-numeric-boolean-date-literals',typed,[accepted_record(rec('typed-a'),[2])],kind='xlsx')
exponent=[header,['number-a',dict(kind='n',value='1e2'),'2030-01-10','true']]
fixture('xlsx-exponent-literal-fails-integer-map',exponent,[],[problem(2,'VALUE_INTEGER_INVALID')],kind='xlsx')
date_literal=[header,['date-a','1',dict(kind='d',value='not-a-calendar-date'),'true']]
fixture('xlsx-date-cell-is-not-calendar-validation',date_literal,[accepted_record(rec('date-a',1,'not-a-calendar-date'),[2])],kind='xlsx',contract='date-as-text')
second=[header,['second-a','4','2030-01-12','true']]
fixture('explicit-second-sheet-selected',second,[accepted_record(rec('second-a',4,'2030-01-12'),[2])],kind='xlsx',values=parts(base_rows,second=second),sheet='Second')
opaque=parts(base_rows);opaque['xl/styles.xml']=b'FICTIONAL_OPAQUE_STYLE_NOT_INTERPRETED';opaque['docProps/core.xml']=b'FICTIONAL_PRIVATE_PROPERTY_NOT_EXPORTED'
fixture('bounded-opaque-styles-and-properties',base_rows,base_accepted,duplicates=1,kind='xlsx',values=opaque)
bad_inputs=[]
def bad(name,raw,kind,code,sheet=None):bad_inputs.append((name,raw,kind,'Records' if kind=='xlsx' and sheet is None else sheet,code))
bad('empty-csv',b'','csv','HEADER_INVALID')
bad('duplicate-header',b'Record,Record,Due,Active\na,1,2030-01-10,true\n','csv','HEADER_INVALID')
bad('missing-header',b'record,Units,Due,Active\na,1,2030-01-10,true\n','csv','MAPPED_HEADER_MISSING')
bad('unmapped-header',b'Record,Units,Due,Active,Extra\na,1,2030-01-10,true,x\n','csv','UNMAPPED_HEADER')
bad('invalid-utf8',b'\xff','csv','CSV_INVALID')
bad('invalid-csv-quotes',b'"unclosed','csv','CSV_INVALID')
bad('csv-raw-cell-limit',csv_bytes([header,['X'*4097,'1','2030-01-10','true']]),'csv','TABLE_LIMIT')
bad('csv-row-limit',csv_bytes([header]+[['a','1','2030-01-10','true']]*1001),'csv','TABLE_LIMIT')
base_parts=parts(base_rows)
bad('nonzip-workbook',b'Fictional refused workbook','xlsx','XLSX_INVALID')
bad('duplicate-zip-member',pack(base_parts,stored=True,duplicate='xl/workbook.xml'),'xlsx','XLSX_ARCHIVE_INVALID')
for name in ('../blocked.xml','xl/vbaProject.bin','xl/externalLinks/link1.xml'):
    bad('unsupported-'+('traversal' if name.startswith('..') else 'macro' if 'vba' in name else 'external-link'),pack(dict(base_parts,**{name:b'FICTIONAL_BLOCKED_PART'}),stored=True),'xlsx','XLSX_PART_UNSUPPORTED')
bad('external-relationship',pack(changed(base_parts,'xl/_rels/workbook.xml.rels',b'Target=',b'TargetMode="External" Target='),stored=True),'xlsx','XLSX_RELATIONSHIP_INVALID')
bad('formula-with-cache',pack(changed(base_parts,'xl/worksheets/sheet1.xml',b'<c r="B2" t="inlineStr"><is><t>12</t></is></c>',b'<c r="B2"><f>1+1</f><v>2</v></c>'),stored=True),'xlsx','XLSX_ACTIVE_OR_HIDDEN_CONTENT')
unselected=parts(base_rows,second=second);unselected=changed(unselected,'xl/worksheets/sheet2.xml',b'<sheetData>',b'<sheetData><f>1+1</f>')
bad('unselected-sheet-formula',pack(unselected,stored=True),'xlsx','XLSX_ACTIVE_OR_HIDDEN_CONTENT')
bad('hidden-sheet',pack(changed(base_parts,'xl/workbook.xml',b'name="Records"',b'name="Records" state="hidden"'),stored=True),'xlsx','XLSX_ACTIVE_OR_HIDDEN_CONTENT')
bad('merged-cells',pack(changed(base_parts,'xl/worksheets/sheet1.xml',b'</worksheet>',b'<mergeCells/></worksheet>'),stored=True),'xlsx','XLSX_SHEET_FEATURE_UNSUPPORTED')
shared_parts=parts(base_rows,shared=True)
bad('invalid-shared-index',pack(changed(shared_parts,'xl/worksheets/sheet1.xml',b'<v>0</v>',b'<v>999</v>'),stored=True),'xlsx','XLSX_SHARED_STRING_INVALID')
bad('rich-inline-string',pack(changed(base_parts,'xl/worksheets/sheet1.xml',b'<t>Record</t>',b'<r><t>Record</t></r>'),stored=True),'xlsx','XLSX_RICH_STRING_UNSUPPORTED')
bad('wrong-cell-order',pack(changed(base_parts,'xl/worksheets/sheet1.xml',b'r="B2"',b'r="A2"'),stored=True),'xlsx','XLSX_CELL_ORDER_INVALID')
bad('dtd-workbook',pack(dict(base_parts,**{'xl/workbook.xml':b'<!DOCTYPE workbook [<!ENTITY fictional "none">]>'+base_parts['xl/workbook.xml']}),stored=True),'xlsx','XML_DECLARATION_FORBIDDEN')
bad('xml-depth-limit',pack(dict(base_parts,**{'xl/workbook.xml':b'<x>'*33+b'</x>'*33}),stored=True),'xlsx','XML_STRUCTURE_LIMIT')
bad('expanded-part-limit',pack(dict(base_parts,**{'docProps/core.xml':b'X'*(2*1024*1024+1)}),stored=True),'xlsx','XLSX_EXPANSION_LIMIT')
bad('expansion-ratio-limit',pack(dict(base_parts,**{'docProps/core.xml':b'X'*100000})),'xlsx','XLSX_EXPANSION_LIMIT')
bad_maps=[]
def bad_map(name,value,code):bad_maps.append((name,encoded(value),code))
bad_maps.extend([('map-invalid-json',b'{','JSON_INVALID'),('map-duplicate-json-key',b'{"format":1,"format":2}','JSON_DUPLICATE_KEY'),('map-floating-json-number',b'{"x":1.0}','JSON_INTEGER_OR_STRING_REQUIRED')])
bad_map('map-empty-fields',dict(mapping,fields=[]),'MAP_INVALID')
bad_map('map-duplicate-target',dict(mapping,fields=[mapping['fields'][0],dict(mapping['fields'][1],target='record_id'),*mapping['fields'][2:]]),'MAP_DUPLICATE_FIELD')
bad_map('map-optional-identity',dict(mapping,fields=[dict(mapping['fields'][0],required=False),*mapping['fields'][1:]]),'MAP_IDENTITY_INVALID')
bad_map('map-extra-key',dict(mapping,private='FICTIONAL'),'FIELDS_INVALID')
for name,raw,kind,sheet,contract,report in fixtures:(inputs/(name+('.csv' if kind=='csv' else '.xlsx'))).write_bytes(raw)
for name,raw,kind,sheet,code in bad_inputs:(inputs/(name+('.csv' if kind=='csv' else '.xlsx'))).write_bytes(raw)
for name,raw in map_raw.items():(inputs/('map-'+name+'.json')).write_bytes(raw)
for name,raw,code in bad_maps:(inputs/(name+'.json')).write_bytes(raw)
for role in ('source','mapping'):(inputs/('over-'+role+'.bin')).write_bytes(b'X'*(4*1024*1024+1))
for role,raw in (('source',csv_bytes(base_rows)),('mapping',map_raw['base'])):
    path=inputs/('hard-'+role+'.bin');path.write_bytes(raw);os.link(path,inputs/('hard-'+role+'-alias.bin'))

def snapshot(root):
    value={}
    for path in root.rglob('*'):
        assert not path.is_symlink() and not getattr(path,'is_junction',lambda:False)()
        info=path.lstat();name=path.relative_to(root).as_posix()
        if stat.S_ISDIR(info.st_mode):value[name]=dict(kind='directory')
        else:
            assert stat.S_ISREG(info.st_mode);raw=path.read_bytes();value[name]=dict(kind='file',bytes=len(raw),sha256=sha(raw),links=info.st_nlink)
    return value
audit="""import runpy,sys,zipfile,decimal,_decimal,xml.etree.ElementTree as ET,_elementtree,pyexpat
assert decimal.Decimal is _decimal.Decimal and decimal.Context is _decimal.Context
def arithmetic_state():
    value=decimal.getcontext()
    return (value.prec,value.rounding,value.Emin,value.Emax,value.capitals,value.clamp,sorted(signal.__name__ for signal,active in value.traps.items() if active),sorted(signal.__name__ for signal,active in value.flags.items() if active))
expected_arithmetic=(28,decimal.ROUND_HALF_EVEN,-999999,999999,1,0,['DivisionByZero','InvalidOperation','Overflow'],[])
assert arithmetic_state()==expected_arithmetic
assert ET.XMLParser is _elementtree.XMLParser and ET.TreeBuilder is _elementtree.TreeBuilder
def deny_extract(*args,**kwargs):raise RuntimeError('FICTIONAL_GUIDE_FORBIDS_ARCHIVE_EXTRACTION')
zipfile.ZipFile.extract=deny_extract;zipfile.ZipFile.extractall=deny_extract
def guard(event,args):
    if event.startswith(('socket.','subprocess.','os.startfile')) or event in ('urllib.Request','webbrowser.open','os.system'):
        raise RuntimeError('FICTIONAL_GUIDE_FORBIDS_REMOTE_OR_PROCESS_ACTION')
sys.addaudithook(guard);script=sys.argv[1];sys.argv=sys.argv[1:]
try:runpy.run_path(script,run_name='__main__')
finally:
    assert arithmetic_state()==expected_arithmetic
    assert ET.XMLParser is _elementtree.XMLParser and ET.TreeBuilder is _elementtree.TreeBuilder
"""

outcomes=[];observations=[];report_rows=[];input_hash_observations=0;binding_cli_checks=0
def run_case(case,args,code,expected,*,script='intake.py',readonly=True,helper=None):
    global input_hash_observations,binding_cli_checks
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
    if helper is None:binding_cli_checks+=1
def inspect_case(name,path,kind,sheet,contract,value):
    args=['--input',path,'--mapping',inputs/('map-'+contract+'.json'),'--format',kind]
    if sheet is not None:args+=['--sheet',sheet]
    output=reports/(name+'.json');code=0 if value['status']=='PASS' else 1
    run_case(name,[*args,'--out',output],code,dict(status=value['status'],report_written=True),readonly=False)
    assert output.read_bytes()==encoded(value)
    if os.name!='nt':assert output.stat().st_mode & 0o777==0o600
    report_rows.append(dict(case=name,path=output.relative_to(work).as_posix(),bytes=output.stat().st_size,sha256=sha(output.read_bytes()),source_sha256=value['source_sha256'],mapping_sha256=value['mapping_sha256']))
run_case('generate-fictional-workbook',['--out',generated/'records.xlsx'],0,dict(status='PASS',fictional=True,bytes=len(generated_raw),sha256=sha(generated_raw)),script='fictional_workbook.py',readonly=False)
assert (generated/'records.xlsx').read_bytes()==generated_raw
inspect_case('generated-intake',generated/'records.xlsx','xlsx','Records','base',generated_expected)
for name,raw,kind,sheet,contract,value in fixtures:inspect_case(name,inputs/(name+('.csv' if kind=='csv' else '.xlsx')),kind,sheet,contract,value)
base_args=['--input',inputs/'csv-parity.csv','--mapping',inputs/'map-base.json','--format','csv']
run_case('default-stdout-contains-accepted-values',base_args,0,fixtures[0][-1])
for name,raw,kind,sheet,code in bad_inputs:
    output=reports/(name+'.json');args=['--input',inputs/(name+('.csv' if kind=='csv' else '.xlsx')),'--mapping',inputs/'map-base.json','--format',kind]
    if sheet is not None:args+=['--sheet',sheet]
    run_case(name,[*args,'--out',output],2,dict(status='ERROR',code=code));assert not output.exists()
for name,raw,code in bad_maps:
    output=reports/(name+'.json');run_case(name,['--input',inputs/'csv-parity.csv','--mapping',inputs/(name+'.json'),'--format','csv','--out',output],2,dict(status='ERROR',code=code));assert not output.exists()
for name,args,code in (
 ('missing-explicit-sheet',['--input',generated/'records.xlsx','--mapping',inputs/'map-base.json','--format','xlsx'],'XLSX_SELECTION_INVALID'),
 ('sheet-name-case-exact',['--input',generated/'records.xlsx','--mapping',inputs/'map-base.json','--format','xlsx','--sheet','records'],'XLSX_SHEET_NOT_FOUND'),
 ('csv-refuses-sheet',[*base_args,'--sheet','Records'],'FORMAT_INVALID'),
 ('missing-required-format',['--input',inputs/'csv-parity.csv','--mapping',inputs/'map-base.json'],'ARGUMENTS_INVALID'),
 ('source-byte-bound',['--input',inputs/'over-source.bin','--mapping',inputs/'map-base.json','--format','csv'],'INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'),
 ('mapping-byte-bound',['--input',inputs/'csv-parity.csv','--mapping',inputs/'over-mapping.bin','--format','csv'],'INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'),
 ('native-hardlink-source',['--input',inputs/'hard-source-alias.bin','--mapping',inputs/'map-base.json','--format','csv'],'CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'),
 ('native-hardlink-mapping',['--input',inputs/'csv-parity.csv','--mapping',inputs/'hard-mapping-alias.bin','--format','csv'],'CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'),
 ('existing-report',[*base_args,'--out',reports/'csv-parity.json'],'INPUT_OR_OUTPUT_REFUSED'),
 ('output-alias-source',[*base_args,'--out',inputs/'csv-parity.csv'],'INPUT_OR_OUTPUT_REFUSED'),
 ('output-alias-mapping',[*base_args,'--out',inputs/'map-base.json'],'INPUT_OR_OUTPUT_REFUSED'),
 ('output-inside-source',[*base_args,'--out',module/'FICTIONAL-REFUSED.json'],'OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'),
 ('parent-traversal',['--input',inputs/'..'/'not-selected.csv','--mapping',inputs/'map-base.json','--format','csv'],'PATH_INVALID')):
    run_case(name,args,2,dict(status='ERROR',code=code))
assert not (module/'FICTIONAL-REFUSED.json').exists()
run_case('generator-refuses-overwrite',['--out',generated/'records.xlsx'],2,dict(status='ERROR',code='OUTPUT_REFUSED'),script='fictional_workbook.py')
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
run_case('partial-output-cannot-be-reused',[*base_args,'--out',work/'partial-output.bin'],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
values={row['case']:json.loads((work/row['path']).read_text(encoding='utf-8')) for row in report_rows}
for value in values.values():
    counts=value['counts'];assert counts['input_rows']==sum(counts[key] for key in ('accepted_records','duplicate_rows','rejected_rows','conflict_rows'))
    assert value['imported'] is False
    assert all(marker not in encoded(value) for marker in (b'PRIVATE_INVALID_TOKEN',b'PRIVATE_IGNORED_TOKEN',b'FICTIONAL_PRIVATE_PROPERTY_NOT_EXPORTED',b'FICTIONAL_OPAQUE_STYLE_NOT_INTERPRETED'))
for name in ('invalid-row-holds-batch-ready','conflict-withholds-every-group-member'):assert values[name]['accepted'] and values[name]['ready_for_explicit_review'] is False
for name in ('inline-parity','shared-parity','generated-intake'):
    assert all(values[name][key]==values['csv-parity'][key] for key in ('status','counts','accepted','issues','mapping'))
assert len({values[name]['source_sha256'] for name in ('csv-parity','inline-parity','shared-parity')})==3
assert values['xlsx-date-cell-is-not-calendar-validation']['accepted'][0]['record']['due']=='not-a-calendar-date'
assert values['negative-zero-remains-signed']['counts']['conflict_rows']==2
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix')
(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode('utf-8'))
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode('utf-8'))
assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,1,2)},
 generator_variants=1,reports_verified=len(report_rows),report_status_counts={status:sum(value['status']==status for value in values.values()) for status in ('PASS','REVIEW_REQUIRED')},
 input_hash_observations=input_hash_observations,fixture_files_preserved=len(fixtures)+len(bad_inputs)+len(map_raw)+len(bad_maps)+6,
 partial_output_bytes_retained=5,artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,
 child_xml_bindings_verified=binding_cli_checks==len(outcomes)-1,child_arithmetic_context_verified=binding_cli_checks==len(outcomes)-1,bindings_checked_cli_cases=binding_cli_checks,
 unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fictional_workbook_intake_flow_checked=True,native_file_guards_checked=True,
 real_records_used=False,real_workbooks_used=False,imported=False,source_transformed=False,formulas_evaluated=False,macros_executed=False,
 office_processes_started=False,external_resources_followed=False,visible_layout_verified=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered case outcomes:

```json
[
  {
    "case": "generate-fictional-workbook",
    "exit_code": 0
  },
  {
    "case": "generated-intake",
    "exit_code": 0
  },
  {
    "case": "csv-parity",
    "exit_code": 0
  },
  {
    "case": "inline-parity",
    "exit_code": 0
  },
  {
    "case": "shared-parity",
    "exit_code": 0
  },
  {
    "case": "invalid-row-holds-batch-ready",
    "exit_code": 1
  },
  {
    "case": "conflict-withholds-every-group-member",
    "exit_code": 1
  },
  {
    "case": "csv-header-only-is-review",
    "exit_code": 1
  },
  {
    "case": "xlsx-header-only-is-review",
    "exit_code": 1
  },
  {
    "case": "optional-empty-is-null-not-zero",
    "exit_code": 0
  },
  {
    "case": "decimal-text-and-literal-text",
    "exit_code": 0
  },
  {
    "case": "decimal-normalized-identical-duplicate",
    "exit_code": 0
  },
  {
    "case": "negative-zero-remains-signed",
    "exit_code": 1
  },
  {
    "case": "decimal-boundaries-are-exact-at-default-context",
    "exit_code": 0
  },
  {
    "case": "composite-identity-and-order",
    "exit_code": 0
  },
  {
    "case": "case-and-space-are-literal",
    "exit_code": 0
  },
  {
    "case": "explicit-ignore-counts-column",
    "exit_code": 0
  },
  {
    "case": "canonical-integer-rejections",
    "exit_code": 1
  },
  {
    "case": "boolean-and-calendar-rejections",
    "exit_code": 1
  },
  {
    "case": "decimal-grammar-refusals",
    "exit_code": 1
  },
  {
    "case": "required-text-length-and-ascii-controls",
    "exit_code": 1
  },
  {
    "case": "csv-blank-record-is-accounted",
    "exit_code": 1
  },
  {
    "case": "csv-short-row-is-rejected",
    "exit_code": 1
  },
  {
    "case": "xlsx-sparse-cell-becomes-optional-null",
    "exit_code": 0
  },
  {
    "case": "xlsx-numeric-boolean-date-literals",
    "exit_code": 0
  },
  {
    "case": "xlsx-exponent-literal-fails-integer-map",
    "exit_code": 1
  },
  {
    "case": "xlsx-date-cell-is-not-calendar-validation",
    "exit_code": 0
  },
  {
    "case": "explicit-second-sheet-selected",
    "exit_code": 0
  },
  {
    "case": "bounded-opaque-styles-and-properties",
    "exit_code": 0
  },
  {
    "case": "default-stdout-contains-accepted-values",
    "exit_code": 0
  },
  {
    "case": "empty-csv",
    "exit_code": 2
  },
  {
    "case": "duplicate-header",
    "exit_code": 2
  },
  {
    "case": "missing-header",
    "exit_code": 2
  },
  {
    "case": "unmapped-header",
    "exit_code": 2
  },
  {
    "case": "invalid-utf8",
    "exit_code": 2
  },
  {
    "case": "invalid-csv-quotes",
    "exit_code": 2
  },
  {
    "case": "csv-raw-cell-limit",
    "exit_code": 2
  },
  {
    "case": "csv-row-limit",
    "exit_code": 2
  },
  {
    "case": "nonzip-workbook",
    "exit_code": 2
  },
  {
    "case": "duplicate-zip-member",
    "exit_code": 2
  },
  {
    "case": "unsupported-traversal",
    "exit_code": 2
  },
  {
    "case": "unsupported-macro",
    "exit_code": 2
  },
  {
    "case": "unsupported-external-link",
    "exit_code": 2
  },
  {
    "case": "external-relationship",
    "exit_code": 2
  },
  {
    "case": "formula-with-cache",
    "exit_code": 2
  },
  {
    "case": "unselected-sheet-formula",
    "exit_code": 2
  },
  {
    "case": "hidden-sheet",
    "exit_code": 2
  },
  {
    "case": "merged-cells",
    "exit_code": 2
  },
  {
    "case": "invalid-shared-index",
    "exit_code": 2
  },
  {
    "case": "rich-inline-string",
    "exit_code": 2
  },
  {
    "case": "wrong-cell-order",
    "exit_code": 2
  },
  {
    "case": "dtd-workbook",
    "exit_code": 2
  },
  {
    "case": "xml-depth-limit",
    "exit_code": 2
  },
  {
    "case": "expanded-part-limit",
    "exit_code": 2
  },
  {
    "case": "expansion-ratio-limit",
    "exit_code": 2
  },
  {
    "case": "map-invalid-json",
    "exit_code": 2
  },
  {
    "case": "map-duplicate-json-key",
    "exit_code": 2
  },
  {
    "case": "map-floating-json-number",
    "exit_code": 2
  },
  {
    "case": "map-empty-fields",
    "exit_code": 2
  },
  {
    "case": "map-duplicate-target",
    "exit_code": 2
  },
  {
    "case": "map-optional-identity",
    "exit_code": 2
  },
  {
    "case": "map-extra-key",
    "exit_code": 2
  },
  {
    "case": "missing-explicit-sheet",
    "exit_code": 2
  },
  {
    "case": "sheet-name-case-exact",
    "exit_code": 2
  },
  {
    "case": "csv-refuses-sheet",
    "exit_code": 2
  },
  {
    "case": "missing-required-format",
    "exit_code": 2
  },
  {
    "case": "source-byte-bound",
    "exit_code": 2
  },
  {
    "case": "mapping-byte-bound",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-source",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-mapping",
    "exit_code": 2
  },
  {
    "case": "existing-report",
    "exit_code": 2
  },
  {
    "case": "output-alias-source",
    "exit_code": 2
  },
  {
    "case": "output-alias-mapping",
    "exit_code": 2
  },
  {
    "case": "output-inside-source",
    "exit_code": 2
  },
  {
    "case": "parent-traversal",
    "exit_code": 2
  },
  {
    "case": "generator-refuses-overwrite",
    "exit_code": 2
  },
  {
    "case": "controlled-write-retains-unconfirmed-prefix",
    "exit_code": 0
  },
  {
    "case": "partial-output-cannot-be-reused",
    "exit_code": 2
  }
]
```

The final summary also checks 71 preserved fixtures, 5,538 fixture-hash
observations, 102 artifact hashes and the manifest readback (103 retained files).
CSV, inline-string and shared-string reports have the same explicit typed
records/counts/issues, while their raw source SHA-256 values differ. The generator
has one CLI variant; the guide separately authors its inline/shared-string inputs.
These cases do not establish interoperability with an independent workbook writer.

Open the JSON reports as private data. Default reports include accepted values,
field mappings and `source_rows`. `invalid-row-holds-batch-ready` and
`conflict-withholds-every-group-member` retain unrelated valid records but both
have `ready_for_explicit_review: false`. A `PASS` is only the declared syntax/type
and grouping result. Nothing approves a batch or imports a record.

`GUIDE-MANIFEST.json` lists every other retained file by relative path, byte length
and SHA-256. The exercise independently reconstructs the expected workbook bytes,
full report bytes and typed outcomes; a matching manifest alone is not the oracle.
Treat the complete directory, hashes and observation ledger as private. The raw
fingerprints do not anonymize an input or establish origin/authenticity.

Only input archive parts are decompressed in memory; no input archive is extracted.
The bounds and checked file operations assume trusted, quiescent inputs and owned
parent directories. They are not an OS resource sandbox or a hostile-directory
containment proof. The controlled partial output is deliberately retained and
cannot be reused as an output name. No transaction rollback, complete ACL/metadata
preservation or crash/power-loss durability is established.
