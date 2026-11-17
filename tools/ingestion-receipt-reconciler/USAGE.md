# Fictional four-input reconciliation walkthrough

This exercise independently authors complete typed previews and complete receipt
reports. It never uses `intake.preview`, `intake.mapping`, `receipts.reconcile` or
the shared artifact functions to create expected results. The actual receipt CLI
does rerun intake: counts are recomputed from invented selected bytes, while source,
receipt and store authority remain unverified. No records are imported.

Copy only `receipts.py`, `run_core.py`, `intake.py`, `toolkit.py`,
`native_windows.py` and `fictional_workbook.py` into a trusted source directory.
Use the selected Python without `-O`/`-OO`; assertions are required, no pip packages
are needed. Create a separate empty private parent outside source. Save the Python
block as `fictional_receipt_walkthrough.py` outside both directories, then pass the
source directory and private parent as its two arguments. Paths below are fictional.

```text
python -I -B fictional_receipt_walkthrough.py "D:\Fictional-Source" "D:\Private-Review"
python -I -B fictional_receipt_walkthrough.py "/home/example/fictional-source" "/home/example/private-review"
```

Choose the Windows or POSIX command. Each run retains 262 authored role-input files,
33 complete reconciliation reports, one generated invented workbook, a five-byte
partial-output artifact, ledger and manifest: 299 files. The 86 outcomes comprise
fifteen exit 0 results, 21 review holds and 50 controlled refusals. Eighty-five actual
script-entrypoint children check C XMLParser/TreeBuilder and Decimal/Context identity
plus every qualified default Decimal-context setting before and in finally after
execution. The separate direct backend fault is excluded from that CLI count.

```python
"""Fictional four-input receipt reconciliation with independently authored complete reports."""
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
work=Path(tempfile.mkdtemp(prefix='fictional-receipt-reconciliation-',dir=parent)).resolve();assert work.parent==parent
runtimes=('receipts.py','run_core.py','intake.py','toolkit.py','native_windows.py','fictional_workbook.py')
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
base_map=dict(format='outlands-table-map-v1',identity=['record_id'],unknown_columns='reject',fields=[field('Record','record_id'),field('Units','units','integer')])
extended_map=dict(base_map,fields=[*base_map['fields'],field('Due','due','date'),field('Active','active','boolean'),field('Price','price','decimal')])
def record(key,units,**extra):return dict(record_id=key,units=units,**extra)
def accepted(value,rows):return dict(record=value,source_rows=rows)
def counts(n,accepted,duplicate=0,rejected=0,conflict=0):
    assert n==accepted+duplicate+rejected+conflict
    return dict(input_rows=n,accepted_records=accepted,duplicate_rows=duplicate,rejected_rows=rejected,conflict_rows=conflict)
def preview(source,mapping,records,n,*,issues=(),duplicates=0,conflicts=0,kind='csv',sheet=None,ignored=0):
    observed=counts(n,len(records),duplicates,sum(i['code']!='IDENTITY_CONFLICT' for i in issues),conflicts)
    status='PASS' if records and not issues else 'REVIEW_REQUIRED'
    return dict(format='outlands-intake-preview-v1',status=status,source_sha256=sha(source),mapping_sha256=sha(mapping),source_format=kind,sheet=sheet,
      mapping=json.loads(mapping)['fields'],ignored_columns=ignored,counts=observed,accepted=records,issues=list(issues),ready_for_explicit_review=status=='PASS',imported=False)
def receipt(source,mapping,supplied,observed,*,kind='csv',sheet=None):
    return dict(format='outlands-ingestion-receipt-v1',receipt_id='fictional-receipt',source_sha256=sha(source),mapping_sha256=sha(mapping),preview_sha256=sha(supplied),source_format=kind,sheet=sheet,counts=observed['counts'])
def expected(declaration,source,mapping,supplied,observed,issues):
    return dict(status='REVIEW_REQUIRED' if issues else 'PASS',format='outlands-ingestion-reconciliation-v1',receipt_id=json.loads(declaration)['receipt_id'],receipt_sha256=sha(declaration),
      source_sha256=sha(source),mapping_sha256=sha(mapping),supplied_preview_sha256=sha(supplied),recomputed_preview_sha256=sha(encoded(observed)),observed_counts=observed['counts'],
      intake_status=observed['status'],issues=sorted(issues),row_counts_recomputed=True,ready_for_explicit_review=not issues,source_authority_verified=False,imported=False,target_changes_performed=False)
base_rows=[['Record','Units'],['sample-alpha','7'],['sample-beta','9'],['sample-alpha','7']]
base_source=csv_bytes(base_rows);base_mapping=encoded(base_map)
base_accepted=[accepted(record('sample-alpha',7),[2,4]),accepted(record('sample-beta',9),[3])]
base_observed=preview(base_source,base_mapping,base_accepted,3,duplicates=1);base_preview=encoded(base_observed)
base_receipt=receipt(base_source,base_mapping,base_preview,base_observed)
files={};fixtures=[];bad_cases=[]
def save(name,role,raw):
    path=name+'-'+role+('.bin' if role=='source' else '.json');assert path not in files;files[path]=raw;return path
def fixture(name,source=base_source,mapping=base_mapping,observed=base_observed,*,supplied=None,claim=None,issues=(),kind='csv',sheet=None):
    supplied=encoded(observed) if supplied is None else supplied
    claim=receipt(source,mapping,supplied,observed,kind=kind,sheet=sheet) if claim is None else claim
    declaration=encoded(claim) if type(claim) is dict else claim
    roles={role:save(name,role,raw) for role,raw in [('receipt',declaration),('source',source),('mapping',mapping),('preview',supplied)]}
    fixtures.append((name,roles,expected(declaration,source,mapping,supplied,observed,list(issues))))
fixture('exact-csv-recomputed-counts')
fixture('receipt-id-is-visible',claim=dict(base_receipt,receipt_id='invented-id'))
fixture('pretty-receipt-raw-pin-changes',claim=(json.dumps(base_receipt,indent=2)+'\n').encode('ascii'))
fixture('pretty-preview-semantic-match',supplied=(json.dumps(base_observed,indent=2)+'\n').encode('ascii'))
pretty_preview=(json.dumps(base_observed,indent=2)+'\n').encode('ascii')
fixture('pretty-preview-stale-raw-pin',supplied=pretty_preview,claim=base_receipt,issues=['PREVIEW_SHA256_MISMATCH'])
for role in ('source','mapping','preview'):
    fixture('incorrect-'+role+'-raw-pin',claim=dict(base_receipt,**{role+'_sha256':'0'*64}),issues=[role.upper()+'_SHA256_MISMATCH'])
fixture('all-three-raw-pin-mismatches',claim=dict(base_receipt,source_sha256='0'*64,mapping_sha256='0'*64,preview_sha256='0'*64),issues=['SOURCE_SHA256_MISMATCH','MAPPING_SHA256_MISMATCH','PREVIEW_SHA256_MISMATCH'])
fixture('same-total-forged-accounting',claim=dict(base_receipt,counts=counts(3,1,2)),issues=['RECEIPT_COUNT_MISMATCH'])
badaccount=dict(base_receipt,counts=dict(base_receipt['counts'],input_rows=4))
fixture('inconsistent-declared-accounting',claim=badaccount,issues=['DECLARED_ACCOUNTING_MISMATCH','RECEIPT_COUNT_MISMATCH'])
for name,update in [('accepted-value',lambda v:v['accepted'][0]['record'].update(units=999)),('source-row-provenance',lambda v:v['accepted'][0].update(source_rows=[999])),('false-not-integer-zero',lambda v:v.update(imported=0)),('extra-preview-field',lambda v:v.update(extra='PRIVATE_PREVIEW_SENTINEL')),('accepted-array-order',lambda v:v['accepted'].reverse()),('preview-mapping-order',lambda v:v['mapping'].reverse()),('missing-accepted-row',lambda v:v['accepted'].pop()),('changed-preview-status',lambda v:v.update(status='REVIEW_REQUIRED'))]:
    forged=copy.deepcopy(base_observed);update(forged)
    fixture('typed-preview-'+name,supplied=encoded(forged),issues=['PREVIEW_CONTENT_MISMATCH'])
one_source=csv_bytes([['Record','Units'],['sample-alpha','1']]);one_records=[accepted(record('sample-alpha',1),[2])]
one_observed=preview(one_source,base_mapping,one_records,1);forged=copy.deepcopy(one_observed);forged['accepted'][0]['record']['units']=True
fixture('typed-true-is-not-integer-one',one_source,observed=one_observed,supplied=encoded(forged),issues=['PREVIEW_CONTENT_MISMATCH'])
for label,source in [('crlf',base_source.replace(b'\n',b'\r\n')),('utf8-bom',b'\xef\xbb\xbf'+base_source)]:
    observed=preview(source,base_mapping,base_accepted,3,duplicates=1);fixture(label+'-source-fresh-pins',source,observed=observed)
pretty_mapping=(json.dumps(base_map,indent=2)+'\n').encode('ascii')
pretty_observed=preview(base_source,pretty_mapping,base_accepted,3,duplicates=1)
fixture('pretty-mapping-fresh-preview',mapping=pretty_mapping,observed=pretty_observed)
fixture('pretty-mapping-stale-preview-content',mapping=pretty_mapping,observed=pretty_observed,supplied=base_preview,issues=['PREVIEW_CONTENT_MISMATCH'])
for label,shared in [('inline',False),('shared',True)]:
    source=pack(parts(base_rows,shared=shared));observed=preview(source,base_mapping,base_accepted,3,duplicates=1,kind='xlsx',sheet='Records')
    fixture(label+'-xlsx-four-input-parity',source,observed=observed,kind='xlsx',sheet='Records')
extended_rows=[['Record','Units','Due','Active','Price'],['typed-a','0','2032-02-29','false','1.230000'],['typed-a','0','2032-02-29','false','1.23'],['typed-b','-2','2030-01-10','true','999999999999.999999']]
extended_source=csv_bytes(extended_rows);extended_mapping=encoded(extended_map)
extended_records=[accepted(record('typed-a',0,due='2032-02-29',active=False,price='1.23'),[2,3]),accepted(record('typed-b',-2,due='2030-01-10',active=True,price='999999999999.999999'),[4])]
fixture('actual-bounded-conversions-default-context',extended_source,extended_mapping,preview(extended_source,extended_mapping,extended_records,3,duplicates=1))
review_source=csv_bytes([['Record','Units'],['safe-a','2'],['bad-a','INVALID_VALUE_TOKEN']])
review_observed=preview(review_source,base_mapping,[accepted(record('safe-a',2),[2])],2,issues=[dict(row=3,code='VALUE_INTEGER_INVALID')])
fixture('invalid-row-retains-observed-counts-not-ready',review_source,observed=review_observed,issues=['INTAKE_REQUIRES_REVIEW'])
conflict_source=csv_bytes([['Record','Units'],['group-a','1'],['group-a','2'],['group-a','1'],['safe-a','3']])
conflict_observed=preview(conflict_source,base_mapping,[accepted(record('safe-a',3),[5])],4,issues=[dict(row=row,code='IDENTITY_CONFLICT') for row in (2,3,4)],conflicts=3)
fixture('conflict-group-withheld-valid-subset-observed',conflict_source,observed=conflict_observed,issues=['INTAKE_REQUIRES_REVIEW'])
empty_source=b'Record,Units\n';empty_observed=preview(empty_source,base_mapping,[],0)
fixture('header-only-requires-review',empty_source,observed=empty_observed,issues=['INTAKE_REQUIRES_REVIEW'])
signed_source=csv_bytes([['Record','Units','Due','Active','Price'],['signed-a','0','2030-01-10','true','-0.000000'],['signed-a','0','2030-01-10','true','0']])
signed_observed=preview(signed_source,extended_mapping,[],2,issues=[dict(row=row,code='IDENTITY_CONFLICT') for row in (2,3)],conflicts=2)
fixture('signed-decimal-zero-is-not-canonical-merge',signed_source,extended_mapping,signed_observed,issues=['INTAKE_REQUIRES_REVIEW'])
max_receipt=dict(base_receipt,receipt_id='r'+'x'*47);fixture('receipt-id-48-boundary',claim=max_receipt)
def bad(name,role,raw,code,*,source=base_source,mapping=base_mapping,supplied=base_preview,claim=base_receipt):
    values=dict(receipt=encoded(claim) if type(claim) is dict else claim,source=source,mapping=mapping,preview=supplied);values[role]=raw
    roles={key:save(name,key,value) for key,value in values.items()};bad_cases.append((name,roles,code))
for role in ('receipt','mapping','preview'):
    bad(role+'-duplicate-json-key',role,b'{"x":1,"x":2}','JSON_DUPLICATE_KEY')
    bad(role+'-invalid-json',role,b'{','JSON_INVALID')
    bad(role+'-floating-json',role,b'{"x":1.0}','JSON_INTEGER_OR_STRING_REQUIRED')
bad('receipt-unknown-field','receipt',encoded(dict(base_receipt,path='PRIVATE_RECEIPT_SENTINEL')),'FIELDS_INVALID')
for label,updates,code in [('format',dict(format='unsupported'),'RECEIPT_FORMAT_INVALID'),('identifier-49',dict(receipt_id='r'*49),'IDENTIFIER_INVALID'),('hash-uppercase',dict(source_sha256='A'*64),'HASH_INVALID'),('format-not-supported',dict(source_format='xml'),'SOURCE_FORMAT_INVALID'),('csv-sheet',dict(sheet='Records'),'SHEET_SELECTION_INVALID'),('xlsx-sheet-missing',dict(source_format='xlsx',sheet=None),'SHEET_SELECTION_INVALID'),('boolean-count',dict(counts=dict(base_receipt['counts'],input_rows=True)),'INTEGER_INVALID'),('count-over-bound',dict(counts=dict(base_receipt['counts'],input_rows=1001)),'INTEGER_INVALID')]:bad('receipt-'+label,'receipt',encoded(dict(base_receipt,**updates)),code)
bad('mapping-missing-identity','mapping',encoded(dict(base_map,identity=[])),'MAP_IDENTITY_INVALID')
bad('mapping-duplicate-field','mapping',encoded(dict(base_map,fields=[base_map['fields'][0]]*2)),'MAP_DUPLICATE_FIELD')
bad('source-duplicate-header','source',b'Record,Record\nx,y\n','HEADER_INVALID')
bad('source-missing-mapped-header','source',b'Record\nx\n','MAPPED_HEADER_MISSING')
bad('source-unknown-header','source',b'Record,Units,Extra\nx,1,z\n','UNMAPPED_HEADER')
bad('source-invalid-utf8','source',b'\xff','CSV_INVALID')
bad('source-csv-nul','source',b'Record,Units\nx,1\x00\n','CSV_INVALID')
xparts=parts(base_rows);xsource=pack(xparts);xobserved=preview(xsource,base_mapping,base_accepted,3,duplicates=1,kind='xlsx',sheet='Records');xpreview=encoded(xobserved);xclaim=receipt(xsource,base_mapping,xpreview,xobserved,kind='xlsx',sheet='Records')
for label,values,code in [('formula',changed(xparts,'xl/worksheets/sheet1.xml',b'<is><t>7</t></is>',b'<f>1+6</f>'),'XLSX_ACTIVE_OR_HIDDEN_CONTENT'),('external-relationship',changed(xparts,'xl/_rels/workbook.xml.rels',b'Target=',b'TargetMode="External" Target='),'XLSX_RELATIONSHIP_INVALID'),('macro-part',dict(xparts,**{'xl/vbaProject.bin':b'Fictional refused bytes'}),'XLSX_PART_UNSUPPORTED'),('unselected-formula',changed(parts(base_rows,second=base_rows),'xl/worksheets/sheet2.xml',b'<is><t>7</t></is>',b'<f>1+6</f>'),'XLSX_ACTIVE_OR_HIDDEN_CONTENT')]:
    bad('xlsx-'+label,'source',pack(values,stored=True),code,source=xsource,supplied=xpreview,claim=xclaim)
bad('xlsx-sheet-case-exact','receipt',encoded(dict(xclaim,sheet='records')),'XLSX_SHEET_NOT_FOUND',source=xsource,supplied=xpreview,claim=xclaim)
bad('preview-json-depth','preview',b'['*34+b'0'+b']'*34,'JSON_STRUCTURE_LIMIT')
bad('preview-json-text-limit','preview',encoded(dict(value='X'*4097)),'JSON_TEXT_LIMIT')
generator_rows=[['Record','Units','Due','Active'],['sample-a','12','2030-01-10','true'],['sample-b','7','2030-01-11','false'],['sample-a','12','2030-01-10','true']]
generated_raw=pack(parts(generator_rows));generator_map=dict(base_map,fields=[*base_map['fields'],field('Due','due','date'),field('Active','active','boolean')]);generator_mapping=encoded(generator_map)
generator_records=[accepted(record('sample-a',12,due='2030-01-10',active=True),[2,4]),accepted(record('sample-b',7,due='2030-01-11',active=False),[3])]
generator_observed=preview(generated_raw,generator_mapping,generator_records,3,duplicates=1,kind='xlsx',sheet='Records');generator_preview=encoded(generator_observed);generator_claim=encoded(receipt(generated_raw,generator_mapping,generator_preview,generator_observed,kind='xlsx',sheet='Records'))
for role,raw in [('receipt',generator_claim),('mapping',generator_mapping),('preview',generator_preview)]:files['generator-'+role+'.json']=raw
for name,raw in files.items():(inputs/name).write_bytes(raw)
(inputs/'over-role.bin').write_bytes(b'X'*(4*1024*1024+1))
(inputs/'hard-input.bin').write_bytes(base_source);os.link(inputs/'hard-input.bin',inputs/'hard-alias.bin')

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
def run_case(case,args,code,expected,*,script='receipts.py',readonly=True,helper=None):
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
def arguments(roles):return [value for role in ('receipt','source','mapping','preview') for value in ('--'+role,inputs/roles[role])]
def inspect_case(name,roles,value):
    output=reports/(name+'.json');code=0 if value['status']=='PASS' else 1
    run_case(name,[*arguments(roles),'--out',output],code,dict(status=value['status'],report_written=True),readonly=False)
    assert output.read_bytes()==encoded(value)
    if os.name!='nt':assert output.stat().st_mode & 0o777==0o600
    report_rows.append(dict(case=name,path=output.relative_to(work).as_posix(),bytes=output.stat().st_size,sha256=sha(output.read_bytes())))
for name,roles,value in fixtures:inspect_case(name,roles,value)
base_roles=fixtures[0][1];base_args=arguments(base_roles)
run_case('default-summary-omits-accepted-values',base_args,0,fixtures[0][-1])
for name,roles,code in bad_cases:
    output=reports/(name+'.json');run_case(name,[*arguments(roles),'--out',output],2,dict(status='ERROR',code=code));assert not output.exists()
for role in ('receipt','source','mapping','preview'):
    selected=dict(base_roles,**{role:'over-role.bin'});run_case(role+'-byte-bound',arguments(selected),2,dict(status='ERROR',code='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'))
    selected=dict(base_roles,**{role:'hard-alias.bin'});run_case(role+'-hardlink-refusal',arguments(selected),2,dict(status='ERROR',code='CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'))
    run_case('output-alias-'+role,[*base_args,'--out',inputs/base_roles[role]],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
for name,args,code in [('existing-report',[*base_args,'--out',reports/'exact-csv-recomputed-counts.json'],'INPUT_OR_OUTPUT_REFUSED'),('output-inside-source',[*base_args,'--out',module/'FICTIONAL-REFUSED.json'],'OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'),('parent-traversal',['--receipt',inputs/'..'/'not-selected.json',*base_args[2:]],'PATH_INVALID'),('missing-required-preview',base_args[:-2],'ARGUMENTS_INVALID')]:run_case(name,args,2,dict(status='ERROR',code=code))
assert not (module/'FICTIONAL-REFUSED.json').exists()
run_case('generate-fictional-workbook',['--out',generated/'records.xlsx'],0,dict(status='PASS',fictional=True,bytes=len(generated_raw),sha256=sha(generated_raw)),script='fictional_workbook.py',readonly=False)
assert (generated/'records.xlsx').read_bytes()==generated_raw
generator_roles=dict(receipt='generator-receipt.json',mapping='generator-mapping.json',preview='generator-preview.json')
generator_output=reports/'generated-workbook-reconciliation.json'
generator_args=['--receipt',inputs/generator_roles['receipt'],'--source',generated/'records.xlsx','--mapping',inputs/generator_roles['mapping'],'--preview',inputs/generator_roles['preview']]
generated_report=expected(generator_claim,generated_raw,generator_mapping,generator_preview,generator_observed,[])
run_case('generated-workbook-reconciliation',[*generator_args,'--out',generator_output],0,dict(status='PASS',report_written=True),readonly=False)
assert generator_output.read_bytes()==encoded(generated_report);report_rows.append(dict(case='generated-workbook-reconciliation',path=generator_output.relative_to(work).as_posix(),bytes=generator_output.stat().st_size,sha256=sha(generator_output.read_bytes())))
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
    assert value['row_counts_recomputed'] is True
    assert value['source_authority_verified'] is value['imported'] is value['target_changes_performed'] is False
    assert value['ready_for_explicit_review']==(not value['issues'])
    assert all(key not in value for key in ('accepted','source_rows','mapping','source_format','sheet'))
    assert b'sample-alpha' not in encoded(value) and b'INVALID_VALUE_TOKEN' not in encoded(value)
    v=value['observed_counts'];assert v['input_rows']==sum(v[k] for k in ('accepted_records','duplicate_rows','rejected_rows','conflict_rows'))
assert values['pretty-preview-semantic-match']['supplied_preview_sha256']!=values['pretty-preview-semantic-match']['recomputed_preview_sha256']
assert values['invalid-row-retains-observed-counts-not-ready']['observed_counts']==counts(2,1,rejected=1)
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix');(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode('utf-8'))
artifacts=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=artifacts),sort_keys=True,indent=2)+'\n').encode('utf-8'));assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in artifacts)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,1,2)},reports_verified=len(report_rows),report_status_counts={status:sum(v['status']==status for v in values.values()) for status in ('PASS','REVIEW_REQUIRED')},input_hash_observations=input_hash_observations,fixture_files_preserved=len(files)+3,partial_output_bytes_retained=5,artifact_payload_hashes_checked=len(artifacts),artifact_manifest_readbacks=1,expected_workspace_files=len(artifacts)+1,child_xml_bindings_verified=binding_cli_checks==len(outcomes)-1,child_arithmetic_context_verified=binding_cli_checks==len(outcomes)-1,bindings_checked_cli_cases=binding_cli_checks,unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fictional_ingestion_receipt_flow_checked=True,native_file_guards_checked=True,row_counts_recomputed=True,real_records_used=False,real_workbooks_used=False,imported=False,source_authority_verified=False,actual_store_contents_verified=False,ingestion_run_executed=False,target_changes_performed=False,receipt_authority_verified=False,exactly_once_verified=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered outcomes:

```json
[
  {
    "case": "exact-csv-recomputed-counts",
    "exit_code": 0
  },
  {
    "case": "receipt-id-is-visible",
    "exit_code": 0
  },
  {
    "case": "pretty-receipt-raw-pin-changes",
    "exit_code": 0
  },
  {
    "case": "pretty-preview-semantic-match",
    "exit_code": 0
  },
  {
    "case": "pretty-preview-stale-raw-pin",
    "exit_code": 1
  },
  {
    "case": "incorrect-source-raw-pin",
    "exit_code": 1
  },
  {
    "case": "incorrect-mapping-raw-pin",
    "exit_code": 1
  },
  {
    "case": "incorrect-preview-raw-pin",
    "exit_code": 1
  },
  {
    "case": "all-three-raw-pin-mismatches",
    "exit_code": 1
  },
  {
    "case": "same-total-forged-accounting",
    "exit_code": 1
  },
  {
    "case": "inconsistent-declared-accounting",
    "exit_code": 1
  },
  {
    "case": "typed-preview-accepted-value",
    "exit_code": 1
  },
  {
    "case": "typed-preview-source-row-provenance",
    "exit_code": 1
  },
  {
    "case": "typed-preview-false-not-integer-zero",
    "exit_code": 1
  },
  {
    "case": "typed-preview-extra-preview-field",
    "exit_code": 1
  },
  {
    "case": "typed-preview-accepted-array-order",
    "exit_code": 1
  },
  {
    "case": "typed-preview-preview-mapping-order",
    "exit_code": 1
  },
  {
    "case": "typed-preview-missing-accepted-row",
    "exit_code": 1
  },
  {
    "case": "typed-preview-changed-preview-status",
    "exit_code": 1
  },
  {
    "case": "typed-true-is-not-integer-one",
    "exit_code": 1
  },
  {
    "case": "crlf-source-fresh-pins",
    "exit_code": 0
  },
  {
    "case": "utf8-bom-source-fresh-pins",
    "exit_code": 0
  },
  {
    "case": "pretty-mapping-fresh-preview",
    "exit_code": 0
  },
  {
    "case": "pretty-mapping-stale-preview-content",
    "exit_code": 1
  },
  {
    "case": "inline-xlsx-four-input-parity",
    "exit_code": 0
  },
  {
    "case": "shared-xlsx-four-input-parity",
    "exit_code": 0
  },
  {
    "case": "actual-bounded-conversions-default-context",
    "exit_code": 0
  },
  {
    "case": "invalid-row-retains-observed-counts-not-ready",
    "exit_code": 1
  },
  {
    "case": "conflict-group-withheld-valid-subset-observed",
    "exit_code": 1
  },
  {
    "case": "header-only-requires-review",
    "exit_code": 1
  },
  {
    "case": "signed-decimal-zero-is-not-canonical-merge",
    "exit_code": 1
  },
  {
    "case": "receipt-id-48-boundary",
    "exit_code": 0
  },
  {
    "case": "default-summary-omits-accepted-values",
    "exit_code": 0
  },
  {
    "case": "receipt-duplicate-json-key",
    "exit_code": 2
  },
  {
    "case": "receipt-invalid-json",
    "exit_code": 2
  },
  {
    "case": "receipt-floating-json",
    "exit_code": 2
  },
  {
    "case": "mapping-duplicate-json-key",
    "exit_code": 2
  },
  {
    "case": "mapping-invalid-json",
    "exit_code": 2
  },
  {
    "case": "mapping-floating-json",
    "exit_code": 2
  },
  {
    "case": "preview-duplicate-json-key",
    "exit_code": 2
  },
  {
    "case": "preview-invalid-json",
    "exit_code": 2
  },
  {
    "case": "preview-floating-json",
    "exit_code": 2
  },
  {
    "case": "receipt-unknown-field",
    "exit_code": 2
  },
  {
    "case": "receipt-format",
    "exit_code": 2
  },
  {
    "case": "receipt-identifier-49",
    "exit_code": 2
  },
  {
    "case": "receipt-hash-uppercase",
    "exit_code": 2
  },
  {
    "case": "receipt-format-not-supported",
    "exit_code": 2
  },
  {
    "case": "receipt-csv-sheet",
    "exit_code": 2
  },
  {
    "case": "receipt-xlsx-sheet-missing",
    "exit_code": 2
  },
  {
    "case": "receipt-boolean-count",
    "exit_code": 2
  },
  {
    "case": "receipt-count-over-bound",
    "exit_code": 2
  },
  {
    "case": "mapping-missing-identity",
    "exit_code": 2
  },
  {
    "case": "mapping-duplicate-field",
    "exit_code": 2
  },
  {
    "case": "source-duplicate-header",
    "exit_code": 2
  },
  {
    "case": "source-missing-mapped-header",
    "exit_code": 2
  },
  {
    "case": "source-unknown-header",
    "exit_code": 2
  },
  {
    "case": "source-invalid-utf8",
    "exit_code": 2
  },
  {
    "case": "source-csv-nul",
    "exit_code": 2
  },
  {
    "case": "xlsx-formula",
    "exit_code": 2
  },
  {
    "case": "xlsx-external-relationship",
    "exit_code": 2
  },
  {
    "case": "xlsx-macro-part",
    "exit_code": 2
  },
  {
    "case": "xlsx-unselected-formula",
    "exit_code": 2
  },
  {
    "case": "xlsx-sheet-case-exact",
    "exit_code": 2
  },
  {
    "case": "preview-json-depth",
    "exit_code": 2
  },
  {
    "case": "preview-json-text-limit",
    "exit_code": 2
  },
  {
    "case": "receipt-byte-bound",
    "exit_code": 2
  },
  {
    "case": "receipt-hardlink-refusal",
    "exit_code": 2
  },
  {
    "case": "output-alias-receipt",
    "exit_code": 2
  },
  {
    "case": "source-byte-bound",
    "exit_code": 2
  },
  {
    "case": "source-hardlink-refusal",
    "exit_code": 2
  },
  {
    "case": "output-alias-source",
    "exit_code": 2
  },
  {
    "case": "mapping-byte-bound",
    "exit_code": 2
  },
  {
    "case": "mapping-hardlink-refusal",
    "exit_code": 2
  },
  {
    "case": "output-alias-mapping",
    "exit_code": 2
  },
  {
    "case": "preview-byte-bound",
    "exit_code": 2
  },
  {
    "case": "preview-hardlink-refusal",
    "exit_code": 2
  },
  {
    "case": "output-alias-preview",
    "exit_code": 2
  },
  {
    "case": "existing-report",
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
    "case": "missing-required-preview",
    "exit_code": 2
  },
  {
    "case": "generate-fictional-workbook",
    "exit_code": 0
  },
  {
    "case": "generated-workbook-reconciliation",
    "exit_code": 0
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

All 33 full reports (twelve PASS, 21 review holds), 22,532 input-hash observations,
298 payload hashes and manifest readback must match. Every earlier workspace file
remains byte-identical after every case. Known preview bytes include typed records,
array order, mapping fields and exact source-row positions; outer report expectations
include all pins, counts, status, flags and sorted issues.

Raw fingerprints and canonical content are different checks. Pretty preview JSON
with an updated receipt pin passes while supplied/recomputed hashes differ; a stale
raw pin holds readiness. Re-pinned forged values, provenance, Boolean/integer types,
arrays or unknown preview fields still fail content comparison. Pretty map bytes
change the map fingerprint inside the recomputed preview too. CSV BOM/line endings
are tracked in exact source hashes, not silently erased from receipt evidence.

Invalid/conflicting rows and header-only sources retain actual observed counts
while readiness is false. The decimal cases exercise bounded conversions under the
qualified default context, including normalized duplicates and signed zero; there
is no context-independence claim. Inline/shared/generated workbooks are invented
fixtures, not independent Excel writers or Office interoperability evidence.

Every role has separate unmasked byte/hardlink and output-alias checks. Refused
formula/cache, external, macro and unselected-sheet fixtures are not executed.
`GUIDE-MANIFEST.json` lists every other file's relative path, bytes and SHA-256.
Keep all role inputs/previews/reports private. The five-byte prefix is unconfirmed,
not a report, and cannot be reused. Audit hooks, native guards and timeouts assume
owned trusted directories; they are not OS isolation, atomic snapshots or durability.
