# Fictional batch replay advice walkthrough

This self-contained exercise authors full expected reports without using
`replay.plan`, `control_core.prepare`, `rows` or `report` as an expected-results
oracle. It checks advice, declared-history blockers, observed list accounting,
issue positions/order, whole-plan withholding and retained artifacts. It never
loads the record/map/preview/receipt bytes referenced by declared pins or performs
a retry, import, target action or authorization.

Copy only `replay.py`, `control_core.py`, `toolkit.py` and `native_windows.py` into
a trusted source directory. Use the selected Python without `-O`/`-OO`; assertions
are required and no pip packages are needed. Create a separate empty private
parent outside the source directory. Save the Python block as
`fictional_batch_replay_walkthrough.py`, outside both directories, and pass source
directory and private parent as its two arguments. Example paths are fictional.

```text
python -I -B fictional_batch_replay_walkthrough.py "D:\Fictional-Source" "D:\Private-Review"
python -I -B fictional_batch_replay_walkthrough.py "/home/example/fictional-source" "/home/example/private-review"
```

The first command is a Windows example and the second is a POSIX example. Each
run creates one new child directory and retains 64 authored inputs, 44 complete
reports, a five-byte controlled partial-output artifact, an observation ledger
and a manifest: 111 files. The 71 outcomes are seventeen exit 0 results, 29 review
results and 25 controlled refusals. Seventy actual script-entrypoint children
check C XMLParser/TreeBuilder affinity before and in `finally` after execution;
one separate backend fault is excluded from that CLI count. Product inputs are
JSON only, with no arithmetic-product/context envelope.

```python
"""Fictional batch replay advice with independently authored reports."""
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
work=Path(tempfile.mkdtemp(prefix='fictional-batch-replay-',dir=parent)).resolve();assert work.parent==parent
runtimes=('replay.py','control_core.py','toolkit.py','native_windows.py')
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
def advice(key,sequence,decision):return dict(id=key,sequence=sequence,decision=decision,execution_authorized=False)
def expected(raw,ec,rc,issues,plan):
    assert (plan is None)==bool(issues)
    assert issues==sorted(issues,key=lambda r:(r['side'],r['row'],r['code'])) and len({(r['side'],r['row'],r['code']) for r in issues})==len(issues)
    return dict(format='outlands-batch-replay-plan-v1',status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=sha(raw),counts=dict(expected=ec,receipts=rc),issues=issues,
      row_counts_recomputed=False,receipt_authority_verified=False,exactly_once_verified=False,target_changes_performed=False,plan=plan,plan_only=True,retry_performed=False,execution_authorized=False)
a=batch();b=batch('batch-b',2);h=batch('history',10);ra=receipt(a);rb=receipt(b);rh=receipt(h)
baseline=[advice('batch-a',1,'SKIP_ALREADY_COMMITTED'),advice('batch-b',2,'MANUAL_REVIEW_NEW_BATCH')]
fixtures=[]
def fixture(name,candidates,receipts,ec,rc,plan,issues=(),*,stream='sample-stream',raw=None):
    value=dict(format='outlands-batch-replay-v1',stream=stream,expected=candidates,receipts=receipts)
    raw=encoded(value) if raw is None else raw
    fixtures.append((name,raw,expected(raw,ec,rc,list(issues),plan)))
fixture('exact-commit-and-relative-absence',[a,b],[ra],observed(2,2),observed(1,1),baseline)
fixture('no-receipts-means-manual-review-only',[a,b],[],observed(2,2),observed(0,0),[advice('batch-a',1,'MANUAL_REVIEW_NEW_BATCH'),advice('batch-b',2,'MANUAL_REVIEW_NEW_BATCH')])
fixture('all-exact-committed-advice-is-skip',[a,b],[ra,rb],observed(2,2),observed(2,2),[advice('batch-a',1,'SKIP_ALREADY_COMMITTED'),advice('batch-b',2,'SKIP_ALREADY_COMMITTED')])
fixture('input-order-does-not-reorder-advice',[b,a],[rb,ra],observed(2,2),observed(2,2),[advice('batch-a',1,'SKIP_ALREADY_COMMITTED'),advice('batch-b',2,'SKIP_ALREADY_COMMITTED')])
fixture('identical-snapshots-count-once',[a,a,b],[ra,ra],observed(3,2,duplicate=1),observed(2,1,duplicate=1),baseline)
fixture('healthy-unselected-history-is-allowed',[a,b],[ra,rh],observed(2,2),observed(2,2),baseline)
fixture('only-candidate-b-with-healthy-other-history',[b],[ra],observed(1,1),observed(1,1),[advice('batch-b',2,'MANUAL_REVIEW_NEW_BATCH')])
changed=dict(a,id='changed',sequence=3,mapping_sha256='0'*64)
fixture('changed-mapping-new-id-is-manual-only',[changed],[ra],observed(1,1),observed(1,1),[advice('changed',3,'MANUAL_REVIEW_NEW_BATCH')])
fixture('receipt-evidence-pin-not-loaded',[a,b],[dict(ra,receipt_sha256='0'*64)],observed(2,2),observed(1,1),baseline)
declared=dict(a,source_sha256='0'*64,mapping_sha256='0'*64,preview_sha256='0'*64)
fixture('syntactic-zero-pins-not-authentication',[declared],[receipt(declared)],observed(1,1),observed(1,1),[advice('batch-a',1,'SKIP_ALREADY_COMMITTED')])
large=batch('declared',7,source_counts(1000,1,999))
fixture('source-record-counts-are-declarations',[large],[],observed(1,1),observed(0,0),[advice('declared',7,'MANUAL_REVIEW_NEW_BATCH')])
fixture('one-thousand-duplicate-snapshots',[a]*1000,[ra]*1000,observed(1000,1,duplicate=999),observed(1000,1,duplicate=999),[advice('batch-a',1,'SKIP_ALREADY_COMMITTED')])
edge=batch('a'+'x'*47,10**9)
fixture('identifier-and-sequence-boundaries',[edge,a],[],observed(2,2),observed(0,0),[advice('batch-a',1,'MANUAL_REVIEW_NEW_BATCH'),advice(edge['id'],10**9,'MANUAL_REVIEW_NEW_BATCH')])
pretty=dict(format='outlands-batch-replay-v1',stream='sample-stream',expected=[a,b],receipts=[ra])
fixture('pretty-json-only-changes-raw-pin',[a,b],[ra],observed(2,2),observed(1,1),baseline,raw=(json.dumps(pretty,indent=2)+'\n').encode('utf-8'))
fixture('utf8-bom-only-changes-raw-pin',[a,b],[ra],observed(2,2),observed(1,1),baseline,raw=b'\xef\xbb\xbf'+encoded(pretty))
for status in ('failed','uncertain'):
    fixture('selected-'+status+'-blocks-whole-plan',[a,b],[dict(ra,status=status)],observed(2,2),observed(1,1),None,[issue('receipts',1,'HISTORY_'+status.upper())])
    fixture('unselected-'+status+'-blocks-whole-plan',[a,b],[ra,dict(rh,status=status)],observed(2,2),observed(2,2),None,[issue('receipts',2,'HISTORY_'+status.upper())])
fixture('unselected-wrong-stream-blocks',[a,b],[ra,dict(rh,stream='other-stream')],observed(2,2),observed(2,2),None,[issue('receipts',2,'STREAM_MISMATCH')])
dirty_h=dict(h,counts=source_counts(3,2,0,rejected=1))
fixture('unselected-unclean-counts-blocks',[a,b],[ra,receipt(dirty_h)],observed(2,2),observed(2,2),None,[issue('receipts',2,'RECEIPT_COUNTS_REQUIRE_REVIEW')])
fixture('malformed-unselected-history-blocks',[a,b],[ra,None],observed(2,2),observed(2,1,rejected=1),None,[issue('receipts',2,'FIELDS_INVALID')])
fixture('malformed-candidate-blocks',[a,b,None],[ra],observed(3,2,rejected=1),observed(1,1),None,[issue('expected',3,'FIELDS_INVALID')])
fixture('conflict-includes-identical-candidate-repeats',[a,dict(a,sequence=99),a,b],[ra],observed(4,1,conflict=3),observed(1,1),None,[issue('expected',row,'IDENTITY_CONFLICT') for row in (1,2,3)])
fixture('conflicting-history-is-not-latest-status-selection',[a,b],[ra,dict(ra,status='uncertain'),ra],observed(2,2),observed(3,0,conflict=3),None,[issue('receipts',row,'IDENTITY_CONFLICT') for row in (1,2,3)])
fixture('different-receipt-ids-under-one-batch-conflict',[a,b],[ra,dict(ra,receipt_id='different')],observed(2,2),observed(2,0,conflict=2),None,[issue('receipts',row,'IDENTITY_CONFLICT') for row in (1,2)])
fixture('sequence-alias-not-a-tie-winner',[a,dict(b,sequence=1)],[],observed(2,2),observed(0,0),None,[issue('expected',row,'SEQUENCE_ALIAS') for row in (1,2)])
fixture('alias-diagnostics-use-first-accepted-position',[a,a,dict(b,sequence=1)],[],observed(3,2,duplicate=1),observed(0,0),None,[issue('expected',row,'SEQUENCE_ALIAS') for row in (1,3)])
fixture('sequence-alias-spans-candidate-and-history',[b],[receipt(dict(a,sequence=2))],observed(1,1),observed(1,1),None,[issue('expected',1,'SEQUENCE_ALIAS'),issue('receipts',1,'SEQUENCE_ALIAS')])
renamed=dict(a,id='renamed',sequence=3)
fixture('content-under-new-id-is-an-alias',[renamed],[ra],observed(1,1),observed(1,1),None,[issue('expected',1,'CONTENT_ID_ALIAS'),issue('receipts',1,'CONTENT_ID_ALIAS')])
same_content=dict(b,source_sha256=a['source_sha256'],mapping_sha256=a['mapping_sha256'],preview_sha256=a['preview_sha256'])
fixture('content-alias-covers-all-accepted-representatives',[a,same_content],[ra],observed(2,2),observed(1,1),None,[issue('expected',1,'CONTENT_ID_ALIAS'),issue('expected',2,'CONTENT_ID_ALIAS'),issue('receipts',1,'CONTENT_ID_ALIAS')])
fixture('receipt-id-alias-across-batches',[a,b],[ra,dict(rh,receipt_id=ra['receipt_id'])],observed(2,2),observed(2,2),None,[issue('receipts',row,'RECEIPT_ID_ALIAS') for row in (1,2)])
for key,value in (('sequence',99),('source_sha256','0'*64),('mapping_sha256','0'*64),('preview_sha256','0'*64),('counts',source_counts(3,3,0))):
    fixture('same-id-'+key+'-mismatch',[a,b],[receipt(dict(a,**{key:value}))],observed(2,2),observed(1,1),None,[issue('receipts',1,'BATCH_METADATA_MISMATCH')])
dirty_a=dict(a,counts=source_counts(3,2,0,conflict=1))
fixture('declared-source-conflicts-withhold-both-sides',[dirty_a],[receipt(dirty_a)],observed(1,1),observed(1,1),None,[issue('expected',1,'BATCH_COUNTS_REQUIRE_REVIEW'),issue('receipts',1,'RECEIPT_COUNTS_REQUIRE_REVIEW')])
zero=dict(a,counts=source_counts(0,0,0))
fixture('structurally-accepted-zero-source-is-not-empty-cohort',[zero],[],observed(1,1),observed(0,0),None,[issue('expected',1,'BATCH_COUNTS_REQUIRE_REVIEW')])
fixture('empty-candidate-cohort-blocks',[],[rh],observed(0,0),observed(1,1),None,[issue('expected',0,'EMPTY_BATCH_COHORT')])
fixture('all-malformed-candidates-have-cohort-and-row-issues',[None],[],observed(1,0,rejected=1),observed(0,0),None,[issue('expected',0,'EMPTY_BATCH_COHORT'),issue('expected',1,'FIELDS_INVALID')])
invalid=[None,dict(a,id='UPPER'),dict(a,sequence=True),dict(a,source_sha256='A'*64),dict(a,extra='PRIVATE_REJECTED_SENTINEL'),dict(a,counts=dict(a['counts'],input_rows=4)),dict(a,counts=dict(a['counts'],accepted_records='2'))]
codes=['FIELDS_INVALID','IDENTIFIER_INVALID','INTEGER_INVALID','HASH_INVALID','FIELDS_INVALID','DECLARED_ACCOUNTING_MISMATCH','INTEGER_INVALID']
fixture('malformed-declarations-are-accounted-and-withheld',[a,b,*invalid],[ra],observed(9,2,rejected=7),observed(1,1),None,[issue('expected',row,code) for row,code in enumerate(codes,3)])
fixture('unsupported-receipt-status-is-rejected',[a,b],[ra,dict(rh,status='pending')],observed(2,2),observed(2,1,rejected=1),None,[issue('receipts',2,'RECEIPT_STATUS_INVALID')])
fixture('metadata-and-alias-issues-are-sorted',[a,b],[receipt(dict(a,sequence=2))],observed(2,2),observed(1,1),None,[issue('expected',2,'SEQUENCE_ALIAS'),issue('receipts',1,'BATCH_METADATA_MISMATCH'),issue('receipts',1,'SEQUENCE_ALIAS')])
bad_inputs=[('invalid-json',b'{','JSON_INVALID'),('duplicate-json-key',b'{"format":1,"format":2}','JSON_DUPLICATE_KEY'),('floating-json-number',b'{"x":1.0}','JSON_INTEGER_OR_STRING_REQUIRED'),('nonfinite-json-number',b'NaN','JSON_INTEGER_OR_STRING_REQUIRED'),('invalid-utf8',b'\xff','JSON_INVALID'),('unpaired-surrogate',b'"\\ud800"','JSON_INVALID'),('json-depth-bound',b'['*34+b'0'+b']'*34,'JSON_STRUCTURE_LIMIT'),('json-text-bound',encoded(dict(value='X'*4097)),'JSON_TEXT_LIMIT'),('json-integer-bound',b'{"x":1000000000000000001}','JSON_INTEGER_LIMIT'),('outer-list',b'[]','FIELDS_INVALID')]
def bad(name,value,code):bad_inputs.append((name,encoded(value),code))
bad('outer-extra-field',dict(pretty,extra='PRIVATE_OUTER_SENTINEL'),'FIELDS_INVALID')
bad('outer-format',dict(pretty,format='unsupported'),'FORMAT_INVALID')
bad('invalid-top-stream',dict(pretty,stream='UPPER'),'IDENTIFIER_INVALID')
bad('expected-not-list',dict(pretty,expected={}), 'ROW_LIMIT')
bad('receipts-not-list',dict(pretty,receipts={}), 'ROW_LIMIT')
bad('expected-list-limit',dict(pretty,expected=[{}]*1001), 'ROW_LIMIT')
bad('receipts-list-limit',dict(pretty,receipts=[{}]*1001), 'ROW_LIMIT')
for name,raw,report in fixtures:(inputs/(name+'.json')).write_bytes(raw)
for name,raw,code in bad_inputs:(inputs/(name+'.json')).write_bytes(raw)
(inputs/'over-input.bin').write_bytes(b'X'*(4*1024*1024+1))
(inputs/'hard-input.json').write_bytes(fixtures[0][1]);os.link(inputs/'hard-input.json',inputs/'hard-input-alias.json')

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
def run_case(case,args,code,expected,*,script='replay.py',readonly=True,helper=None):
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
base_args=['--input',inputs/'exact-commit-and-relative-absence.json']
run_case('default-stdout-report-is-exact',base_args,0,fixtures[0][-1])
for name,raw,code in bad_inputs:
    output=reports/(name+'.json');run_case(name,['--input',inputs/(name+'.json'),'--out',output],2,dict(status='ERROR',code=code));assert not output.exists()
for name,args,code in (
 ('input-byte-bound',['--input',inputs/'over-input.bin'],'INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'),('native-hardlink-input',['--input',inputs/'hard-input-alias.json'],'CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'),
 ('existing-report',[*base_args,'--out',reports/'exact-commit-and-relative-absence.json'],'INPUT_OR_OUTPUT_REFUSED'),('output-alias-input',[*base_args,'--out',inputs/'exact-commit-and-relative-absence.json'],'INPUT_OR_OUTPUT_REFUSED'),
 ('output-inside-source',[*base_args,'--out',module/'FICTIONAL-REFUSED.json'],'OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'),('parent-traversal',['--input',inputs/'..'/'not-selected.json'],'PATH_INVALID'),('missing-required-input',[],'ARGUMENTS_INVALID')):
    run_case(name,args,2,dict(status='ERROR',code=code))
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
assert (work/'partial-output.bin').read_bytes()==b'Ficti'
run_case('partial-output-cannot-be-reused',[*base_args,'--out',work/'partial-output.bin'],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
values={row['case']:json.loads((work/row['path']).read_text(encoding='utf-8')) for row in report_rows}
for value in values.values():
    assert value['plan_only'] is True and all(value[key] is False for key in ('retry_performed','execution_authorized','target_changes_performed','row_counts_recomputed','receipt_authority_verified','exactly_once_verified'))
    assert (value['plan'] is None)==bool(value['issues'])
    for side in ('expected','receipts'):
        counts=value['counts'][side];assert counts['input_rows']==sum(counts[key] for key in ('accepted_records','duplicate_rows','rejected_rows','conflict_rows'))
    if value['plan'] is not None:assert value['plan'] and all(row['execution_authorized'] is False for row in value['plan'])
    assert all(marker not in encoded(value) for marker in (b'PRIVATE_REJECTED_SENTINEL',b'PRIVATE_OUTER_SENTINEL'))
for name in ('pretty-json-only-changes-raw-pin','utf8-bom-only-changes-raw-pin'):
    assert values[name]['plan']==values['exact-commit-and-relative-absence']['plan'] and values[name]['input_sha256']!=values['exact-commit-and-relative-absence']['input_sha256']
assert values['conflicting-history-is-not-latest-status-selection']['issues']==[issue('receipts',row,'IDENTITY_CONFLICT') for row in (1,2,3)]
assert values['structurally-accepted-zero-source-is-not-empty-cohort']['counts']['expected']['accepted_records']==1
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix')
(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode('utf-8'))
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode('utf-8'))
assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,1,2)},reports_verified=len(report_rows),report_status_counts={status:sum(value['status']==status for value in values.values()) for status in ('PASS','REVIEW_REQUIRED')},
 input_hash_observations=input_hash_observations,fixture_files_preserved=len(fixtures)+len(bad_inputs)+3,partial_output_bytes_retained=5,artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,
 child_xml_bindings_verified=xml_cli_checks==len(outcomes)-1,xml_bindings_checked_cli_cases=xml_cli_checks,unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fictional_batch_replay_flow_checked=True,native_file_guards_checked=True,
 real_records_used=False,real_workbooks_used=False,imported=False,retry_performed=False,execution_authorized=False,target_changes_performed=False,row_counts_recomputed=False,receipt_authority_verified=False,exactly_once_verified=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered outcomes:

```json
[
  {
    "case": "exact-commit-and-relative-absence",
    "exit_code": 0
  },
  {
    "case": "no-receipts-means-manual-review-only",
    "exit_code": 0
  },
  {
    "case": "all-exact-committed-advice-is-skip",
    "exit_code": 0
  },
  {
    "case": "input-order-does-not-reorder-advice",
    "exit_code": 0
  },
  {
    "case": "identical-snapshots-count-once",
    "exit_code": 0
  },
  {
    "case": "healthy-unselected-history-is-allowed",
    "exit_code": 0
  },
  {
    "case": "only-candidate-b-with-healthy-other-history",
    "exit_code": 0
  },
  {
    "case": "changed-mapping-new-id-is-manual-only",
    "exit_code": 0
  },
  {
    "case": "receipt-evidence-pin-not-loaded",
    "exit_code": 0
  },
  {
    "case": "syntactic-zero-pins-not-authentication",
    "exit_code": 0
  },
  {
    "case": "source-record-counts-are-declarations",
    "exit_code": 0
  },
  {
    "case": "one-thousand-duplicate-snapshots",
    "exit_code": 0
  },
  {
    "case": "identifier-and-sequence-boundaries",
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
    "case": "selected-failed-blocks-whole-plan",
    "exit_code": 1
  },
  {
    "case": "unselected-failed-blocks-whole-plan",
    "exit_code": 1
  },
  {
    "case": "selected-uncertain-blocks-whole-plan",
    "exit_code": 1
  },
  {
    "case": "unselected-uncertain-blocks-whole-plan",
    "exit_code": 1
  },
  {
    "case": "unselected-wrong-stream-blocks",
    "exit_code": 1
  },
  {
    "case": "unselected-unclean-counts-blocks",
    "exit_code": 1
  },
  {
    "case": "malformed-unselected-history-blocks",
    "exit_code": 1
  },
  {
    "case": "malformed-candidate-blocks",
    "exit_code": 1
  },
  {
    "case": "conflict-includes-identical-candidate-repeats",
    "exit_code": 1
  },
  {
    "case": "conflicting-history-is-not-latest-status-selection",
    "exit_code": 1
  },
  {
    "case": "different-receipt-ids-under-one-batch-conflict",
    "exit_code": 1
  },
  {
    "case": "sequence-alias-not-a-tie-winner",
    "exit_code": 1
  },
  {
    "case": "alias-diagnostics-use-first-accepted-position",
    "exit_code": 1
  },
  {
    "case": "sequence-alias-spans-candidate-and-history",
    "exit_code": 1
  },
  {
    "case": "content-under-new-id-is-an-alias",
    "exit_code": 1
  },
  {
    "case": "content-alias-covers-all-accepted-representatives",
    "exit_code": 1
  },
  {
    "case": "receipt-id-alias-across-batches",
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
    "case": "declared-source-conflicts-withhold-both-sides",
    "exit_code": 1
  },
  {
    "case": "structurally-accepted-zero-source-is-not-empty-cohort",
    "exit_code": 1
  },
  {
    "case": "empty-candidate-cohort-blocks",
    "exit_code": 1
  },
  {
    "case": "all-malformed-candidates-have-cohort-and-row-issues",
    "exit_code": 1
  },
  {
    "case": "malformed-declarations-are-accounted-and-withheld",
    "exit_code": 1
  },
  {
    "case": "unsupported-receipt-status-is-rejected",
    "exit_code": 1
  },
  {
    "case": "metadata-and-alias-issues-are-sorted",
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
    "case": "invalid-top-stream",
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

The 44 reports comprise fifteen PASS plans and 29 global review holds. The guide
checks 4,544 input-hash observations, 110 artifact hashes and a manifest readback.
Every prior file must remain byte-identical after every case. Full advice lists,
counts, diagnostics and report bytes are manual expectations; a matching manifest
alone is not the oracle. No generator or independent source-record reconciliation
is used.

Look at `unselected-failed-blocks-whole-plan`,
`unselected-uncertain-blocks-whole-plan` and
`conflicting-history-is-not-latest-status-selection`: each withholds the entire
plan. The conflicting group reports only its explicit conflict positions, without
inventing an extra HISTORY diagnostic for rows already withheld. Missing receipts
give manual-review advice only relative to the supplied snapshots. Healthy
unselected committed history is permitted, while alias or metadata issues still
block. Even a PASS plan never has execution authorization.

`source-record-counts-are-declarations` reports one accepted batch-list row whose
declared source accounting is 1,000 input records. No such record file is loaded.
`structurally-accepted-zero-source-is-not-empty-cohort` has an accepted batch-list
row but unsuitable source counts and a withheld plan. These demonstrate two
different accounting scopes, not verified source facts. Zero-filled syntactically
valid pins and arbitrary receipt evidence pins are declarations, not trust proofs.

`GUIDE-MANIFEST.json` lists every other retained file by relative name, bytes and
SHA-256. Keep all fixtures, reports, fingerprints and ledgers private. The five-byte
prefix is intentionally unconfirmed, is not a completed report and cannot be
reused as an output. Audit hooks, process timeouts and native checks assume owned
directories and trusted quiescent inputs; they are not an OS sandbox, atomic
snapshot, replay-safety proof or hardware-durability guarantee.
