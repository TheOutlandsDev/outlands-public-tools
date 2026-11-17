# Fictional ingestion cohort walkthrough

This exercise authors complete expected reports without using `coverage.check`,
`control_core.prepare`, `rows`, `reconcile` or `report` as an expected-results
oracle. It verifies list accounting, unique declared totals, matching precedence,
global withholding and empty-cohort review holds. No records/store is accessed, run
executed, receipt authenticated or real ingestion history used.

Copy only `coverage.py`, `control_core.py`, `toolkit.py`, `native_windows.py` into
a trusted source directory. Use the selected Python without `-O`/`-OO`: assertions
are required and no pip packages are needed. Create a separate empty private
parent outside the source directory. Save the Python block as
`fictional_ingestion_coverage_walkthrough.py`, outside both directories, and pass
source directory and private parent as its two arguments. Paths below are fictional.

```text
python -I -B fictional_ingestion_coverage_walkthrough.py "D:\Fictional-Source" "D:\Private-Review"
python -I -B fictional_ingestion_coverage_walkthrough.py "/home/example/fictional-source" "/home/example/private-review"
```

Choose the Windows or POSIX example for your system. Each run retains 64 authored
inputs, 44 full reports, a five-byte controlled partial-output artifact, an
observation ledger and manifest: 111 files. Its 71 outcomes comprise thirteen
exit 0 results, 33 review results and 25 controlled refusals. Seventy actual
script-entrypoint children check C XMLParser/TreeBuilder affinity before and in
finally after execution; a separate backend fault is excluded from that CLI
count. Product inputs are JSON only, without arithmetic/Decimal-product scope.

```python
"""Fictional declared ingestion cohorts with independently authored reports."""
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
work=Path(tempfile.mkdtemp(prefix='fictional-ingestion-coverage-',dir=parent)).resolve();assert work.parent==parent
runtimes=('coverage.py','control_core.py','toolkit.py','native_windows.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
runtime_hashes={name:sha((module/name).read_bytes()) for name in runtimes}
inputs=work/'inputs';reports=work/'reports'
inputs.mkdir();reports.mkdir()




def pin(label):return sha(('Fictional declared '+label).encode('ascii'))
def source_counts(n=3,accepted=2,duplicate=1,rejected=0,conflict=0):
    assert n==accepted+duplicate+rejected+conflict
    return dict(input_rows=n,accepted_records=accepted,duplicate_rows=duplicate,rejected_rows=rejected,conflict_rows=conflict)
def batch(key='batch-a',sequence=1,counts=None):
    return dict(id=key,sequence=sequence,source_sha256=pin('source '+key),mapping_sha256=pin('mapping'),preview_sha256=pin('preview '+key),counts=source_counts() if counts is None else counts)
def receipt(value,status='committed',stream='sample-stream',key=None,evidence=None):
    return dict(receipt_id='receipt-'+value['id'] if key is None else key,stream=stream,batch=copy.deepcopy(value),status=status,receipt_sha256=pin('receipt '+value['id']) if evidence is None else evidence)
def observed(n,accepted,duplicate=0,rejected=0,conflict=0):
    assert n==accepted+duplicate+rejected+conflict
    return dict(input_rows=n,accepted_records=accepted,duplicate_rows=duplicate,rejected_rows=rejected,conflict_rows=conflict)
def issue(side,row,code):return dict(side=side,row=row,code=code)
def expected(raw,ec,rc,issues,resolved,missing,unexpected,totals):
    assert (totals is None)==bool(issues)
    assert issues==sorted(issues,key=lambda r:(r['side'],r['row'],r['code'])) and len({(r['side'],r['row'],r['code']) for r in issues})==len(issues)
    return dict(format='outlands-ingestion-run-coverage-review-v1',status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=sha(raw),
      counts=dict(expected=ec,receipts=rc,resolved_committed_batches=resolved,missing_receipts=missing,unexpected_receipts=unexpected),issues=issues,
      row_counts_recomputed=False,receipt_authority_verified=False,exactly_once_verified=False,target_changes_performed=False,
      declared_totals=totals,cohort_complete=not issues,actual_store_contents_verified=False)
a=batch();b=batch('batch-b',2);h=batch('history',10);ra=receipt(a);rb=receipt(b);rh=receipt(h)
two=source_counts(6,4,2);one=source_counts();fixtures=[]
def fixture(name,candidates,receipts,ec,rc,resolved,missing,unexpected,totals,issues=(),*,raw=None,stream='sample-stream'):
    value=dict(format='outlands-ingestion-run-coverage-v1',stream=stream,expected=candidates,receipts=receipts)
    raw=encoded(value) if raw is None else raw
    fixtures.append((name,raw,expected(raw,ec,rc,list(issues),resolved,missing,unexpected,totals)))
fixture('full-declared-cohort',[a,b],[ra,rb],observed(2,2),observed(2,2),2,0,0,two)
fixture('input-order-does-not-change-totals',[b,a],[rb,ra],observed(2,2),observed(2,2),2,0,0,two)
fixture('identical-snapshots-count-once',[a,a,b],[ra,rb,ra],observed(3,2,duplicate=1),observed(3,2,duplicate=1),2,0,0,two)
far=dict(b,sequence=10**9)
fixture('noncontiguous-sequences-are-allowed',[a,far],[ra,receipt(far)],observed(2,2),observed(2,2),2,0,0,two)
edge=batch('a'+'x'*47,10**9)
fixture('identifier-and-sequence-upper-boundaries',[edge],[receipt(edge,key='r'*48)],observed(1,1),observed(1,1),1,0,0,one)
wide=[batch('b'+str(i).zfill(4),i*1000) for i in range(1,1001)]
fixture('one-thousand-unique-declared-batches',wide,[receipt(row) for row in wide],observed(1000,1000),observed(1000,1000),1000,0,0,source_counts(3000,2000,1000))
declared=batch('declared',1,source_counts(1000,1,999))
fixture('source-duplicates-are-not-batch-duplicates',[declared,declared],[receipt(declared)]*2,observed(2,1,duplicate=1),observed(2,1,duplicate=1),1,0,0,source_counts(1000,1,999))
allclean=batch('all-clean',5,source_counts(1000,1000,0))
fixture('declared-total-fields-not-reconstructed-records',[a,allclean],[ra,receipt(allclean)],observed(2,2),observed(2,2),2,0,0,source_counts(1003,1002,1))
zero_pins=dict(a,source_sha256='0'*64,mapping_sha256='0'*64,preview_sha256='0'*64)
fixture('syntactic-pins-and-receipt-evidence-not-authentication',[zero_pins],[receipt(zero_pins,evidence='0'*64)],observed(1,1),observed(1,1),1,0,0,one)
pretty=dict(format='outlands-ingestion-run-coverage-v1',stream='sample-stream',expected=[a,b],receipts=[ra,rb])
fixture('pretty-json-only-changes-raw-pin',[a,b],[ra,rb],observed(2,2),observed(2,2),2,0,0,two,raw=(json.dumps(pretty,indent=2)+'\n').encode('utf-8'))
fixture('utf8-bom-only-changes-raw-pin',[a,b],[ra,rb],observed(2,2),observed(2,2),2,0,0,two,raw=b'\xef\xbb\xbf'+encoded(pretty))
fixture('empty-cohort-requires-review',[],[],observed(0,0),observed(0,0),0,0,0,None,[issue('expected',0,'EMPTY_BATCH_COHORT')])
fixture('missing-receipt-withholds-all-totals',[a,b],[ra],observed(2,2),observed(1,1),1,1,0,None,[issue('expected',2,'RECEIPT_MISSING')])
fixture('all-receipts-missing',[a,b],[],observed(2,2),observed(0,0),0,2,0,None,[issue('expected',row,'RECEIPT_MISSING') for row in (1,2)])
for status in ('committed','failed','uncertain'):
    fixture('otherwise-valid-orphan-'+status,[a,b],[ra,rb,dict(rh,status=status)],observed(2,2),observed(3,3),2,0,1,None,[issue('receipts',3,'UNEXPECTED_RECEIPT')])
fixture('orphan-status-does-not-hide-other-stream-issue',[a],[ra,receipt(h,status='failed',stream='other-stream')],observed(1,1),observed(2,2),1,0,1,None,[issue('receipts',2,'STREAM_MISMATCH'),issue('receipts',2,'UNEXPECTED_RECEIPT')])
for status in ('failed','uncertain'):
    fixture('matched-'+status+'-withholds',[a,b],[dict(ra,status=status),rb],observed(2,2),observed(2,2),1,0,0,None,[issue('receipts',1,'OUTCOME_'+status.upper())])
fixture('wrong-stream-can-resolve-but-never-complete',[a,b],[dict(ra,stream='other-stream'),rb],observed(2,2),observed(2,2),2,0,0,None,[issue('receipts',1,'STREAM_MISMATCH')])
for key,value in (('sequence',99),('source_sha256','0'*64),('mapping_sha256','0'*64),('preview_sha256','0'*64),('counts',source_counts(3,3,0))):
    fixture('same-id-'+key+'-mismatch',[a,b],[receipt(dict(a,**{key:value})),rb],observed(2,2),observed(2,2),1,0,0,None,[issue('receipts',1,'BATCH_METADATA_MISMATCH')])
fixture('metadata-mismatch-precedes-status-check',[a],[receipt(dict(a,source_sha256='0'*64),status='uncertain')],observed(1,1),observed(1,1),0,0,0,None,[issue('receipts',1,'BATCH_METADATA_MISMATCH')])
for field in ('rejected','conflict'):
    dirty=dict(a,counts=source_counts(3,2,0,**{field:1}))
    fixture('declared-source-'+field+'-withholds',[dirty],[receipt(dirty)],observed(1,1),observed(1,1),0,0,0,None,[issue('expected',1,'BATCH_COUNTS_REQUIRE_REVIEW'),issue('receipts',1,'RECEIPT_COUNTS_REQUIRE_REVIEW')])
dirty=dict(a,counts=source_counts(3,2,0,rejected=1))
fixture('status-precedes-receipt-clean-check',[dirty],[receipt(dirty,status='failed')],observed(1,1),observed(1,1),0,0,0,None,[issue('expected',1,'BATCH_COUNTS_REQUIRE_REVIEW'),issue('receipts',1,'OUTCOME_FAILED')])
zero=dict(a,counts=source_counts(0,0,0))
fixture('zero-declared-source-is-not-healthy',[zero],[receipt(zero)],observed(1,1),observed(1,1),0,0,0,None,[issue('expected',1,'BATCH_COUNTS_REQUIRE_REVIEW'),issue('receipts',1,'RECEIPT_COUNTS_REQUIRE_REVIEW')])
alias_b=dict(b,sequence=1)
fixture('sequence-alias-with-two-resolved-pairs',[a,alias_b],[ra,receipt(alias_b)],observed(2,2),observed(2,2),2,0,0,None,[issue(side,row,'SEQUENCE_ALIAS') for side in ('expected','receipts') for row in (1,2)])
fixture('aliases-use-first-accepted-position',[a,a,alias_b],[ra,receipt(alias_b)],observed(3,2,duplicate=1),observed(2,2),2,0,0,None,[issue('expected',1,'SEQUENCE_ALIAS'),issue('expected',3,'SEQUENCE_ALIAS'),issue('receipts',1,'SEQUENCE_ALIAS'),issue('receipts',2,'SEQUENCE_ALIAS')])
content_b=dict(b,source_sha256=a['source_sha256'],mapping_sha256=a['mapping_sha256'],preview_sha256=a['preview_sha256'])
fixture('content-alias-with-two-resolved-pairs',[a,content_b],[ra,receipt(content_b)],observed(2,2),observed(2,2),2,0,0,None,[issue(side,row,'CONTENT_ID_ALIAS') for side in ('expected','receipts') for row in (1,2)])
fixture('receipt-id-alias-is-not-batch-id-matching',[a,b],[ra,dict(rb,receipt_id=ra['receipt_id'])],observed(2,2),observed(2,2),2,0,0,None,[issue('receipts',row,'RECEIPT_ID_ALIAS') for row in (1,2)])
fixture('expected-conflicts-become-orphan',[a,dict(a,sequence=99),a,b],[ra,rb],observed(4,1,conflict=3),observed(2,2),1,0,1,None,[*[issue('expected',row,'IDENTITY_CONFLICT') for row in (1,2,3)],issue('receipts',1,'UNEXPECTED_RECEIPT')])
fixture('all-expected-conflicts-also-empty-cohort',[a,dict(a,sequence=99)],[],observed(2,0,conflict=2),observed(0,0),0,0,0,None,[issue('expected',0,'EMPTY_BATCH_COHORT'),issue('expected',1,'IDENTITY_CONFLICT'),issue('expected',2,'IDENTITY_CONFLICT')])
fixture('receipt-conflicts-become-missing-not-outcome',[a,b],[ra,dict(ra,status='uncertain'),ra,rb],observed(2,2),observed(4,1,conflict=3),1,1,0,None,[issue('expected',1,'RECEIPT_MISSING'),*[issue('receipts',row,'IDENTITY_CONFLICT') for row in (1,2,3)]])
fixture('malformed-expected-withholds-resolved-pairs',[a,b,None],[ra,rb],observed(3,2,rejected=1),observed(2,2),2,0,0,None,[issue('expected',3,'FIELDS_INVALID')])
fixture('malformed-receipt-withholds-resolved-pairs',[a,b],[ra,rb,None],observed(2,2),observed(3,2,rejected=1),2,0,0,None,[issue('receipts',3,'FIELDS_INVALID')])
fixture('all-malformed-expected-also-empty-cohort',[None],[],observed(1,0,rejected=1),observed(0,0),0,0,0,None,[issue('expected',0,'EMPTY_BATCH_COHORT'),issue('expected',1,'FIELDS_INVALID')])
fixture('unsupported-receipt-status-is-rejected',[a],[dict(ra,status='pending')],observed(1,1),observed(1,0,rejected=1),0,1,0,None,[issue('expected',1,'RECEIPT_MISSING'),issue('receipts',1,'RECEIPT_STATUS_INVALID')])
fixture('receipt-identifier-one-over-bound-rejected',[edge],[receipt(edge,key='r'*49)],observed(1,1),observed(1,0,rejected=1),0,1,0,None,[issue('expected',1,'RECEIPT_MISSING'),issue('receipts',1,'IDENTIFIER_INVALID')])
fixture('metadata-plus-cross-list-sequence-alias',[a,b],[receipt(dict(a,sequence=2)),rb],observed(2,2),observed(2,2),1,0,0,None,[issue('expected',2,'SEQUENCE_ALIAS'),issue('receipts',1,'BATCH_METADATA_MISMATCH'),issue('receipts',1,'SEQUENCE_ALIAS'),issue('receipts',2,'SEQUENCE_ALIAS')])
bad_inputs=[('invalid-json',b'{','JSON_INVALID'),('duplicate-json-key',b'{"format":1,"format":2}','JSON_DUPLICATE_KEY'),('floating-json-number',b'{"x":1.0}','JSON_INTEGER_OR_STRING_REQUIRED'),('nonfinite-json-number',b'NaN','JSON_INTEGER_OR_STRING_REQUIRED'),('invalid-utf8',b'\xff','JSON_INVALID'),('unpaired-surrogate',b'"\\ud800"','JSON_INVALID'),('json-depth-bound',b'['*34+b'0'+b']'*34,'JSON_STRUCTURE_LIMIT'),('json-text-bound',encoded(dict(value='X'*4097)),'JSON_TEXT_LIMIT'),('json-integer-bound',b'{"x":1000000000000000001}','JSON_INTEGER_LIMIT'),('outer-list',b'[]','FIELDS_INVALID')]
def bad(name,value,code):bad_inputs.append((name,encoded(value),code))
bad('outer-extra-field',dict(pretty,extra='PRIVATE_OUTER_SENTINEL'),'FIELDS_INVALID');bad('outer-format',dict(pretty,format='unsupported'),'FORMAT_INVALID');bad('top-stream-case',dict(pretty,stream='UPPER'),'IDENTIFIER_INVALID')
for name,updates in (('expected-not-list',dict(expected={})),('receipts-not-list',dict(receipts={})),('expected-list-limit',dict(expected=[{}]*1001)),('receipts-list-limit',dict(receipts=[{}]*1001))):bad(name,dict(pretty,**updates),'ROW_LIMIT')
for name,raw,report in fixtures:(inputs/(name+'.json')).write_bytes(raw)
for name,raw,code in bad_inputs:(inputs/(name+'.json')).write_bytes(raw)
(inputs/'over-input.bin').write_bytes(b'X'*(4*1024*1024+1));(inputs/'hard-input.json').write_bytes(fixtures[0][1]);os.link(inputs/'hard-input.json',inputs/'hard-input-alias.json')

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
def run_case(case,args,code,expected,*,script='coverage.py',readonly=True,helper=None):
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
for name,raw,report in fixtures:
    output=reports/(name+'.json');code=0 if report['status']=='PASS' else 1
    run_case(name,['--input',inputs/(name+'.json'),'--out',output],code,dict(status=report['status'],report_written=True),readonly=False)
    assert output.read_bytes()==encoded(report)
    if os.name!='nt':assert output.stat().st_mode & 0o777==0o600
    report_rows.append(dict(case=name,path=output.relative_to(work).as_posix(),bytes=output.stat().st_size,sha256=sha(output.read_bytes()),input_sha256=report['input_sha256']))
base_args=['--input',inputs/'full-declared-cohort.json'];run_case('default-stdout-report-is-exact',base_args,0,fixtures[0][-1])
for name,raw,code in bad_inputs:
    output=reports/(name+'.json');run_case(name,['--input',inputs/(name+'.json'),'--out',output],2,dict(status='ERROR',code=code));assert not output.exists()
for name,args,code in (
 ('input-byte-bound',['--input',inputs/'over-input.bin'],'INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'),('native-hardlink-input',['--input',inputs/'hard-input-alias.json'],'CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'),('existing-report',[*base_args,'--out',reports/'full-declared-cohort.json'],'INPUT_OR_OUTPUT_REFUSED'),('output-alias-input',[*base_args,'--out',inputs/'full-declared-cohort.json'],'INPUT_OR_OUTPUT_REFUSED'),('output-inside-source',[*base_args,'--out',module/'FICTIONAL-REFUSED.json'],'OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'),('parent-traversal',['--input',inputs/'..'/'not-selected.json'],'PATH_INVALID'),('missing-required-input',[],'ARGUMENTS_INVALID')):run_case(name,args,2,dict(status='ERROR',code=code))
assert not (module/'FICTIONAL-REFUSED.json').exists()
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
finally:
    os.write=real
    assert ET.XMLParser is _elementtree.XMLParser and ET.TreeBuilder is _elementtree.TreeBuilder
"""
run_case('controlled-write-retains-unconfirmed-prefix',[work/'partial-output.bin'],0,dict(controlled_write_failure=True,partial_output_retained=True),readonly=False,helper=failure)
assert (work/'partial-output.bin').read_bytes()==b'Ficti';run_case('partial-output-cannot-be-reused',[*base_args,'--out',work/'partial-output.bin'],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
values={row['case']:json.loads((work/row['path']).read_text(encoding='utf-8')) for row in report_rows}
for value in values.values():
    assert all(value[key] is False for key in ('actual_store_contents_verified','target_changes_performed','row_counts_recomputed','receipt_authority_verified','exactly_once_verified'))
    assert (value['declared_totals'] is None)==bool(value['issues']) and value['cohort_complete']==(not value['issues'])
    for side in ('expected','receipts'):
        counts=value['counts'][side];assert counts['input_rows']==sum(counts[key] for key in ('accepted_records','duplicate_rows','rejected_rows','conflict_rows'))
    assert all(key not in value for key in ('stream','id','plan','source_sha256','mapping_sha256','preview_sha256','receipt_sha256'))
for name in ('pretty-json-only-changes-raw-pin','utf8-bom-only-changes-raw-pin'):
    assert values[name]['declared_totals']==two and values[name]['input_sha256']!=values['full-declared-cohort']['input_sha256']
assert values['wrong-stream-can-resolve-but-never-complete']['counts']['resolved_committed_batches']==2
assert values['source-duplicates-are-not-batch-duplicates']['counts']['expected']['duplicate_rows']==1
assert values['source-duplicates-are-not-batch-duplicates']['declared_totals']['duplicate_rows']==999
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix');(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode('utf-8'))
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode('utf-8'));assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,1,2)},reports_verified=len(report_rows),report_status_counts={status:sum(value['status']==status for value in values.values()) for status in ('PASS','REVIEW_REQUIRED')},input_hash_observations=input_hash_observations,fixture_files_preserved=len(fixtures)+len(bad_inputs)+3,partial_output_bytes_retained=5,artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,child_xml_bindings_verified=xml_cli_checks==len(outcomes)-1,xml_bindings_checked_cli_cases=xml_cli_checks,unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fictional_ingestion_run_coverage_flow_checked=True,native_file_guards_checked=True,real_records_used=False,real_workbooks_used=False,imported=False,actual_store_contents_verified=False,ingestion_run_executed=False,target_changes_performed=False,row_counts_recomputed=False,receipt_authority_verified=False,exactly_once_verified=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered outcomes:

```json
[
  {
    "case": "full-declared-cohort",
    "exit_code": 0
  },
  {
    "case": "input-order-does-not-change-totals",
    "exit_code": 0
  },
  {
    "case": "identical-snapshots-count-once",
    "exit_code": 0
  },
  {
    "case": "noncontiguous-sequences-are-allowed",
    "exit_code": 0
  },
  {
    "case": "identifier-and-sequence-upper-boundaries",
    "exit_code": 0
  },
  {
    "case": "one-thousand-unique-declared-batches",
    "exit_code": 0
  },
  {
    "case": "source-duplicates-are-not-batch-duplicates",
    "exit_code": 0
  },
  {
    "case": "declared-total-fields-not-reconstructed-records",
    "exit_code": 0
  },
  {
    "case": "syntactic-pins-and-receipt-evidence-not-authentication",
    "exit_code": 0
  },
  {
    "case": "pretty-json-only-changes-raw-pin",
    "exit_code": 0
  },
  {
    "case": "utf8-bom-only-changes-raw-pin",
    "exit_code": 0
  },
  {
    "case": "empty-cohort-requires-review",
    "exit_code": 1
  },
  {
    "case": "missing-receipt-withholds-all-totals",
    "exit_code": 1
  },
  {
    "case": "all-receipts-missing",
    "exit_code": 1
  },
  {
    "case": "otherwise-valid-orphan-committed",
    "exit_code": 1
  },
  {
    "case": "otherwise-valid-orphan-failed",
    "exit_code": 1
  },
  {
    "case": "otherwise-valid-orphan-uncertain",
    "exit_code": 1
  },
  {
    "case": "orphan-status-does-not-hide-other-stream-issue",
    "exit_code": 1
  },
  {
    "case": "matched-failed-withholds",
    "exit_code": 1
  },
  {
    "case": "matched-uncertain-withholds",
    "exit_code": 1
  },
  {
    "case": "wrong-stream-can-resolve-but-never-complete",
    "exit_code": 1
  },
  {
    "case": "same-id-sequence-mismatch",
    "exit_code": 1
  },
  {
    "case": "same-id-source_sha256-mismatch",
    "exit_code": 1
  },
  {
    "case": "same-id-mapping_sha256-mismatch",
    "exit_code": 1
  },
  {
    "case": "same-id-preview_sha256-mismatch",
    "exit_code": 1
  },
  {
    "case": "same-id-counts-mismatch",
    "exit_code": 1
  },
  {
    "case": "metadata-mismatch-precedes-status-check",
    "exit_code": 1
  },
  {
    "case": "declared-source-rejected-withholds",
    "exit_code": 1
  },
  {
    "case": "declared-source-conflict-withholds",
    "exit_code": 1
  },
  {
    "case": "status-precedes-receipt-clean-check",
    "exit_code": 1
  },
  {
    "case": "zero-declared-source-is-not-healthy",
    "exit_code": 1
  },
  {
    "case": "sequence-alias-with-two-resolved-pairs",
    "exit_code": 1
  },
  {
    "case": "aliases-use-first-accepted-position",
    "exit_code": 1
  },
  {
    "case": "content-alias-with-two-resolved-pairs",
    "exit_code": 1
  },
  {
    "case": "receipt-id-alias-is-not-batch-id-matching",
    "exit_code": 1
  },
  {
    "case": "expected-conflicts-become-orphan",
    "exit_code": 1
  },
  {
    "case": "all-expected-conflicts-also-empty-cohort",
    "exit_code": 1
  },
  {
    "case": "receipt-conflicts-become-missing-not-outcome",
    "exit_code": 1
  },
  {
    "case": "malformed-expected-withholds-resolved-pairs",
    "exit_code": 1
  },
  {
    "case": "malformed-receipt-withholds-resolved-pairs",
    "exit_code": 1
  },
  {
    "case": "all-malformed-expected-also-empty-cohort",
    "exit_code": 1
  },
  {
    "case": "unsupported-receipt-status-is-rejected",
    "exit_code": 1
  },
  {
    "case": "receipt-identifier-one-over-bound-rejected",
    "exit_code": 1
  },
  {
    "case": "metadata-plus-cross-list-sequence-alias",
    "exit_code": 1
  },
  {
    "case": "default-stdout-report-is-exact",
    "exit_code": 0
  },
  {
    "case": "invalid-json",
    "exit_code": 2
  },
  {
    "case": "duplicate-json-key",
    "exit_code": 2
  },
  {
    "case": "floating-json-number",
    "exit_code": 2
  },
  {
    "case": "nonfinite-json-number",
    "exit_code": 2
  },
  {
    "case": "invalid-utf8",
    "exit_code": 2
  },
  {
    "case": "unpaired-surrogate",
    "exit_code": 2
  },
  {
    "case": "json-depth-bound",
    "exit_code": 2
  },
  {
    "case": "json-text-bound",
    "exit_code": 2
  },
  {
    "case": "json-integer-bound",
    "exit_code": 2
  },
  {
    "case": "outer-list",
    "exit_code": 2
  },
  {
    "case": "outer-extra-field",
    "exit_code": 2
  },
  {
    "case": "outer-format",
    "exit_code": 2
  },
  {
    "case": "top-stream-case",
    "exit_code": 2
  },
  {
    "case": "expected-not-list",
    "exit_code": 2
  },
  {
    "case": "receipts-not-list",
    "exit_code": 2
  },
  {
    "case": "expected-list-limit",
    "exit_code": 2
  },
  {
    "case": "receipts-list-limit",
    "exit_code": 2
  },
  {
    "case": "input-byte-bound",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-input",
    "exit_code": 2
  },
  {
    "case": "existing-report",
    "exit_code": 2
  },
  {
    "case": "output-alias-input",
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
    "case": "missing-required-input",
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

The 44 full reports contain eleven PASS and 33 global holds. All 4,544 input-hash
observations, 110 artifact hashes and manifest readback must match. Every prior
workspace file remains byte-identical after every case. Full report bytes, counts,
issue positions/order, null totals and cohort flags are explicitly expected data.

Compare the noncontiguous successful cohort with `empty-cohort-requires-review`:
sequence gaps are allowed, an absent accepted cohort is not. The duplicate case
counts one observed repeated batch while declared source duplicate totals remain
999. The 1,000-batch case totals 3,000 declared input rows; no source records are
loaded to establish those numbers. Zero pins demonstrate syntax acceptance rather
than authenticated evidence. Pretty JSON and a UTF-8 BOM change the raw pin while
leaving the declared totals unchanged.

`wrong-stream-can-resolve-but-never-complete` has two resolved pairs and still
withholds every total. Metadata mismatch precedes outcome checks; otherwise valid
orphan failed/uncertain status adds no outcome code, while an independent wrong
stream still adds its diagnostic. Conflicted groups are withheld before matching.
No counter certifies actual store contents, full-run coverage or exactly-once work.

`GUIDE-MANIFEST.json` lists every other retained file by relative name, length and
SHA-256. The retained five-byte prefix is unconfirmed, not a completed report, and
cannot be reused as an output. Keep all fixtures, reports and fingerprints private.
Audit hooks, timeouts and native guards assume owned directories and trusted
quiescent inputs; they are not OS isolation, atomic snapshots or durability proof.
