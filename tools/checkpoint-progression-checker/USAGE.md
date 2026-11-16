# Fictional checkpoint proposal walkthrough

This self-contained exercise authors complete expected reports without using
`checkpoints.check`, `control_core.prepare`, `rows`, `reconcile` or `report` as an
expected-results oracle. It checks ordinal coverage, matching precedence,
resolution/list counters, issue positions, global withholding and empty no-change
windows. It never writes a checkpoint, loads source records or authenticates a
declared commit or prior ordinal.

Copy only `checkpoints.py`, `control_core.py`, `toolkit.py` and `native_windows.py`
into a trusted source directory. Use the selected Python without `-O`/`-OO`:
assertions are required and no pip packages are needed. Create a separate empty
private parent outside the source directory. Save the Python block as
`fictional_checkpoint_walkthrough.py`, outside both directories, and pass source
directory and private parent as its two arguments. Example paths are fictional.

```text
python -I -B fictional_checkpoint_walkthrough.py "D:\Fictional-Source" "D:\Private-Review"
python -I -B fictional_checkpoint_walkthrough.py "/home/example/fictional-source" "/home/example/private-review"
```

The first command is a Windows example and the second is a POSIX example. Each
run creates a new child directory and retains 74 authored inputs, 47 full reports,
a five-byte controlled partial-output artifact, an observation ledger and a
manifest: 124 files. The 81 outcomes comprise fifteen exit 0 results, 34 review
results and 32 controlled refusals. Eighty actual script-entrypoint children check
C XMLParser/TreeBuilder affinity before and in finally after execution; one separate
backend fault is excluded from that CLI count. Product inputs are JSON only,
without an arithmetic/Decimal-product context envelope.

```python
"""Fictional checkpoint proposals with independently authored reports."""
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
work=Path(tempfile.mkdtemp(prefix='fictional-checkpoint-',dir=parent)).resolve();assert work.parent==parent
runtimes=('checkpoints.py','control_core.py','toolkit.py','native_windows.py')
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
def expected(raw,previous,proposed,ec,rc,issues,resolved,missing,unexpected,suggested,eligible):
    assert (suggested is None)==bool(issues) and type(eligible) is bool
    assert issues==sorted(issues,key=lambda r:(r['side'],r['row'],r['code'])) and len({(r['side'],r['row'],r['code']) for r in issues})==len(issues)
    return dict(format='outlands-checkpoint-progression-review-v1',status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=sha(raw),
      counts=dict(expected=ec,receipts=rc,resolved_committed_batches=resolved,missing_receipts=missing,unexpected_receipts=unexpected),issues=issues,
      row_counts_recomputed=False,receipt_authority_verified=False,exactly_once_verified=False,target_changes_performed=False,
      previous=previous,proposed=proposed,suggested_checkpoint=suggested,advancement_eligible_for_explicit_review=eligible,
      previous_checkpoint_authority_verified=False,checkpoint_written=False,plan_only=True)
a=batch();b=batch('batch-b',2);h=batch('history',10);ra=receipt(a);rb=receipt(b);rh=receipt(h)
fixtures=[]
def fixture(name,previous,proposed,candidates,receipts,ec,rc,resolved,missing,unexpected,suggested,eligible,issues=(),*,raw=None,stream='sample-stream'):
    value=dict(format='outlands-checkpoint-progression-v1',stream=stream,previous=previous,proposed=proposed,expected=candidates,receipts=receipts)
    raw=encoded(value) if raw is None else raw
    fixtures.append((name,raw,expected(raw,previous,proposed,ec,rc,list(issues),resolved,missing,unexpected,suggested,eligible)))
fixture('full-contiguous-window',0,2,[a,b],[ra,rb],observed(2,2),observed(2,2),2,0,0,2,True)
fixture('input-order-does-not-change-suggestion',0,2,[b,a],[rb,ra],observed(2,2),observed(2,2),2,0,0,2,True)
fixture('identical-snapshots-count-once',0,2,[a,a,b],[ra,rb,ra],observed(3,2,duplicate=1),observed(3,2,duplicate=1),2,0,0,2,True)
fixture('previous-ordinal-is-not-reverified',1,2,[b],[rb],observed(1,1),observed(1,1),1,0,0,2,True)
for label,value in (('zero',0),('middle',2),('upper',10**9)):
    fixture('equal-empty-window-'+label,value,value,[],[],observed(0,0),observed(0,0),0,0,0,value,False)
edge=batch('a'+'x'*47,10**9)
fixture('upper-ordinal-and-identifier-boundaries',10**9-1,10**9,[edge],[receipt(edge,key='edge-receipt')],observed(1,1),observed(1,1),1,0,0,10**9,True)
wide=[batch('b'+str(i).zfill(4),i) for i in range(1,1001)]
fixture('one-thousand-contiguous-ordinals',0,1000,wide,[receipt(row) for row in wide],observed(1000,1000),observed(1000,1000),1000,0,0,1000,True)
declared=batch('declared',1,source_counts(1000,1,999))
fixture('one-batch-is-not-one-thousand-source-records',0,1,[declared],[receipt(declared)],observed(1,1),observed(1,1),1,0,0,1,True)
zero_pins=dict(a,source_sha256='0'*64,mapping_sha256='0'*64,preview_sha256='0'*64)
fixture('syntactic-pins-and-receipt-evidence-not-authentication',0,1,[zero_pins],[receipt(zero_pins,evidence='0'*64)],observed(1,1),observed(1,1),1,0,0,1,True)
pretty=dict(format='outlands-checkpoint-progression-v1',stream='sample-stream',previous=0,proposed=2,expected=[a,b],receipts=[ra,rb])
fixture('pretty-json-only-changes-raw-pin',0,2,[a,b],[ra,rb],observed(2,2),observed(2,2),2,0,0,2,True,raw=(json.dumps(pretty,indent=2)+'\n').encode('utf-8'))
fixture('utf8-bom-only-changes-raw-pin',0,2,[a,b],[ra,rb],observed(2,2),observed(2,2),2,0,0,2,True,raw=b'\xef\xbb\xbf'+encoded(pretty))
fixture('gap-is-not-a-missing-receipt',0,2,[b],[rb],observed(1,1),observed(1,1),1,0,0,None,False,[issue('expected',0,'CHECKPOINT_GAP')])
fixture('multiple-gaps-deduplicate-diagnostic',0,4,[b],[rb],observed(1,1),observed(1,1),1,0,0,None,False,[issue('expected',0,'CHECKPOINT_GAP')])
fixture('positive-empty-window-has-gap-only',0,2,[],[],observed(0,0),observed(0,0),0,0,0,None,False,[issue('expected',0,'CHECKPOINT_GAP')])
fixture('coverage-with-missing-receipt-still-withholds',0,2,[a,b],[ra],observed(2,2),observed(1,1),1,1,0,None,False,[issue('expected',2,'RECEIPT_MISSING')])
fixture('all-receipts-missing-is-not-a-coverage-gap',0,2,[a,b],[],observed(2,2),observed(0,0),0,2,0,None,False,[issue('expected',row,'RECEIPT_MISSING') for row in (1,2)])
for status in ('committed','failed','uncertain'):
    fixture('orphan-'+status+'-is-unexpected-only',0,2,[a,b],[ra,rb,dict(rh,status=status)],observed(2,2),observed(3,3),2,0,1,None,False,[issue('receipts',3,'UNEXPECTED_RECEIPT')])
for status in ('failed','uncertain'):
    fixture('matched-'+status+'-withholds',0,2,[a,b],[dict(ra,status=status),rb],observed(2,2),observed(2,2),1,0,0,None,False,[issue('receipts',1,'OUTCOME_'+status.upper())])
fixture('wrong-stream-can-resolve-but-never-suggest',0,2,[a,b],[dict(ra,stream='other-stream'),rb],observed(2,2),observed(2,2),2,0,0,None,False,[issue('receipts',1,'STREAM_MISMATCH')])
fixture('accepted-position-before-window-blocks',1,2,[a,b],[ra,rb],observed(2,2),observed(2,2),2,0,0,None,False,[issue('expected',1,'BATCH_OUTSIDE_CHECKPOINT_WINDOW')])
fixture('accepted-position-after-window-blocks',0,1,[a,b],[ra,rb],observed(2,2),observed(2,2),2,0,0,None,False,[issue('expected',2,'BATCH_OUTSIDE_CHECKPOINT_WINDOW')])
fixture('equal-nonempty-window-is-not-a-noop-pass',2,2,[a],[ra],observed(1,1),observed(1,1),1,0,0,None,False,[issue('expected',1,'BATCH_OUTSIDE_CHECKPOINT_WINDOW')])
fixture('equal-window-with-orphan-is-review',2,2,[],[ra],observed(0,0),observed(1,1),0,0,1,None,False,[issue('receipts',1,'UNEXPECTED_RECEIPT')])
for key,value in (('sequence',99),('source_sha256','0'*64),('mapping_sha256','0'*64),('preview_sha256','0'*64),('counts',source_counts(3,3,0))):
    fixture('same-id-'+key+'-mismatch',0,2,[a,b],[receipt(dict(a,**{key:value})),rb],observed(2,2),observed(2,2),1,0,0,None,False,[issue('receipts',1,'BATCH_METADATA_MISMATCH')])
fixture('metadata-mismatch-precedes-status-check',0,1,[a],[receipt(dict(a,source_sha256='0'*64),status='uncertain')],observed(1,1),observed(1,1),0,0,0,None,False,[issue('receipts',1,'BATCH_METADATA_MISMATCH')])
dirty=dict(a,counts=source_counts(3,2,0,rejected=1))
fixture('declared-source-counts-withhold',0,1,[dirty],[receipt(dirty)],observed(1,1),observed(1,1),0,0,0,None,False,[issue('expected',1,'BATCH_COUNTS_REQUIRE_REVIEW'),issue('receipts',1,'RECEIPT_COUNTS_REQUIRE_REVIEW')])
fixture('status-check-precedes-receipt-clean-check',0,1,[dirty],[receipt(dirty,status='failed')],observed(1,1),observed(1,1),0,0,0,None,False,[issue('expected',1,'BATCH_COUNTS_REQUIRE_REVIEW'),issue('receipts',1,'OUTCOME_FAILED')])
alias_b=dict(b,sequence=1)
fixture('sequence-alias-plus-deduplicated-gap',0,2,[a,alias_b],[ra,receipt(alias_b)],observed(2,2),observed(2,2),2,0,0,None,False,[issue('expected',0,'CHECKPOINT_GAP'),issue('expected',1,'SEQUENCE_ALIAS'),issue('expected',2,'SEQUENCE_ALIAS'),issue('receipts',1,'SEQUENCE_ALIAS'),issue('receipts',2,'SEQUENCE_ALIAS')])
fixture('alias-diagnostics-use-first-accepted-position',0,2,[a,a,alias_b],[ra,receipt(alias_b)],observed(3,2,duplicate=1),observed(2,2),2,0,0,None,False,[issue('expected',0,'CHECKPOINT_GAP'),issue('expected',1,'SEQUENCE_ALIAS'),issue('expected',3,'SEQUENCE_ALIAS'),issue('receipts',1,'SEQUENCE_ALIAS'),issue('receipts',2,'SEQUENCE_ALIAS')])
content_b=dict(b,source_sha256=a['source_sha256'],mapping_sha256=a['mapping_sha256'],preview_sha256=a['preview_sha256'])
fixture('content-alias-can-have-two-resolved-pairs',0,2,[a,content_b],[ra,receipt(content_b)],observed(2,2),observed(2,2),2,0,0,None,False,[issue('expected',1,'CONTENT_ID_ALIAS'),issue('expected',2,'CONTENT_ID_ALIAS'),issue('receipts',1,'CONTENT_ID_ALIAS'),issue('receipts',2,'CONTENT_ID_ALIAS')])
fixture('receipt-id-alias-withholds',0,2,[a,b],[ra,dict(rb,receipt_id=ra['receipt_id'])],observed(2,2),observed(2,2),2,0,0,None,False,[issue('receipts',row,'RECEIPT_ID_ALIAS') for row in (1,2)])
fixture('candidate-conflicts-become-gap-and-orphan',0,2,[a,dict(a,sequence=99),a,b],[ra,rb],observed(4,1,conflict=3),observed(2,2),1,0,1,None,False,[issue('expected',0,'CHECKPOINT_GAP'),*[issue('expected',row,'IDENTITY_CONFLICT') for row in (1,2,3)],issue('receipts',1,'UNEXPECTED_RECEIPT')])
fixture('conflicting-receipts-become-missing-not-outcome',0,2,[a,b],[ra,dict(ra,status='uncertain'),ra,rb],observed(2,2),observed(4,1,conflict=3),1,1,0,None,False,[issue('expected',1,'RECEIPT_MISSING'),*[issue('receipts',row,'IDENTITY_CONFLICT') for row in (1,2,3)]])
fixture('malformed-candidate-withholds-resolved-pairs',0,2,[a,b,None],[ra,rb],observed(3,2,rejected=1),observed(2,2),2,0,0,None,False,[issue('expected',3,'FIELDS_INVALID')])
fixture('malformed-receipt-withholds-resolved-pairs',0,2,[a,b],[ra,rb,None],observed(2,2),observed(3,2,rejected=1),2,0,0,None,False,[issue('receipts',3,'FIELDS_INVALID')])
fixture('all-malformed-candidates-gap-without-empty-cohort-code',0,2,[None],[],observed(1,0,rejected=1),observed(0,0),0,0,0,None,False,[issue('expected',0,'CHECKPOINT_GAP'),issue('expected',1,'FIELDS_INVALID')])
fixture('unsupported-receipt-status-is-rejected',0,1,[a],[dict(ra,status='pending')],observed(1,1),observed(1,0,rejected=1),0,1,0,None,False,[issue('expected',1,'RECEIPT_MISSING'),issue('receipts',1,'RECEIPT_STATUS_INVALID')])
fixture('metadata-and-cross-list-sequence-alias-order',0,2,[a,b],[receipt(dict(a,sequence=2)),rb],observed(2,2),observed(2,2),1,0,0,None,False,[issue('expected',2,'SEQUENCE_ALIAS'),issue('receipts',1,'BATCH_METADATA_MISMATCH'),issue('receipts',1,'SEQUENCE_ALIAS'),issue('receipts',2,'SEQUENCE_ALIAS')])
bad_inputs=[('invalid-json',b'{','JSON_INVALID'),('duplicate-json-key',b'{"format":1,"format":2}','JSON_DUPLICATE_KEY'),('floating-json-number',b'{"x":1.0}','JSON_INTEGER_OR_STRING_REQUIRED'),('nonfinite-json-number',b'NaN','JSON_INTEGER_OR_STRING_REQUIRED'),('invalid-utf8',b'\xff','JSON_INVALID'),('unpaired-surrogate',b'"\\ud800"','JSON_INVALID'),('json-depth-bound',b'['*34+b'0'+b']'*34,'JSON_STRUCTURE_LIMIT'),('json-text-bound',encoded(dict(value='X'*4097)),'JSON_TEXT_LIMIT'),('json-integer-bound',b'{"x":1000000000000000001}','JSON_INTEGER_LIMIT'),('outer-list',b'[]','FIELDS_INVALID')]
def bad(name,value,code):bad_inputs.append((name,encoded(value),code))
bad('outer-extra-field',dict(pretty,extra='PRIVATE_OUTER_SENTINEL'),'FIELDS_INVALID');bad('outer-format',dict(pretty,format='unsupported'),'FORMAT_INVALID');bad('top-stream-case',dict(pretty,stream='UPPER'),'IDENTIFIER_INVALID')
for name,updates,code in (
 ('previous-boolean',dict(previous=True),'INTEGER_INVALID'),('proposed-boolean',dict(proposed=True),'INTEGER_INVALID'),('previous-negative',dict(previous=-1),'INTEGER_INVALID'),('proposed-above-ordinal-bound',dict(proposed=10**9+1),'INTEGER_INVALID'),('previous-string',dict(previous='0'),'INTEGER_INVALID'),('backward-window',dict(previous=3),'CHECKPOINT_WINDOW_INVALID'),('window-one-over-width',dict(proposed=1001),'CHECKPOINT_WINDOW_INVALID'),('expected-not-list',dict(expected={}), 'ROW_LIMIT'),('receipts-not-list',dict(receipts={}), 'ROW_LIMIT'),('expected-list-limit',dict(expected=[{}]*1001), 'ROW_LIMIT'),('receipts-list-limit',dict(receipts=[{}]*1001), 'ROW_LIMIT')):bad(name,dict(pretty,**updates),code)
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
def run_case(case,args,code,expected,*,script='checkpoints.py',readonly=True,helper=None):
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
base_args=['--input',inputs/'full-contiguous-window.json'];run_case('default-stdout-report-is-exact',base_args,0,fixtures[0][-1])
for name,raw,code in bad_inputs:
    output=reports/(name+'.json');run_case(name,['--input',inputs/(name+'.json'),'--out',output],2,dict(status='ERROR',code=code));assert not output.exists()
for name,args,code in (
 ('input-byte-bound',['--input',inputs/'over-input.bin'],'INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'),('native-hardlink-input',['--input',inputs/'hard-input-alias.json'],'CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'),('existing-report',[*base_args,'--out',reports/'full-contiguous-window.json'],'INPUT_OR_OUTPUT_REFUSED'),('output-alias-input',[*base_args,'--out',inputs/'full-contiguous-window.json'],'INPUT_OR_OUTPUT_REFUSED'),('output-inside-source',[*base_args,'--out',module/'FICTIONAL-REFUSED.json'],'OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'),('parent-traversal',['--input',inputs/'..'/'not-selected.json'],'PATH_INVALID'),('missing-required-input',[],'ARGUMENTS_INVALID')):run_case(name,args,2,dict(status='ERROR',code=code))
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
    assert value['plan_only'] is True and all(value[key] is False for key in ('checkpoint_written','previous_checkpoint_authority_verified','target_changes_performed','row_counts_recomputed','receipt_authority_verified','exactly_once_verified'))
    assert (value['suggested_checkpoint'] is None)==bool(value['issues'])
    if value['issues']:assert value['advancement_eligible_for_explicit_review'] is False
    for side in ('expected','receipts'):
        counts=value['counts'][side];assert counts['input_rows']==sum(counts[key] for key in ('accepted_records','duplicate_rows','rejected_rows','conflict_rows'))
    assert all(key not in value for key in ('stream','id','plan','source_sha256','mapping_sha256','preview_sha256','receipt_sha256'))
for name in ('pretty-json-only-changes-raw-pin','utf8-bom-only-changes-raw-pin'):
    assert values[name]['suggested_checkpoint']==2 and values[name]['input_sha256']!=values['full-contiguous-window']['input_sha256']
assert values['wrong-stream-can-resolve-but-never-suggest']['counts']['resolved_committed_batches']==2
assert values['multiple-gaps-deduplicate-diagnostic']['issues']==[issue('expected',0,'CHECKPOINT_GAP')]
for name in ('zero','middle','upper'):
    value=values['equal-empty-window-'+name];assert value['suggested_checkpoint']==value['previous'] and value['advancement_eligible_for_explicit_review'] is False
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix');(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode('utf-8'))
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode('utf-8'));assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,1,2)},reports_verified=len(report_rows),report_status_counts={status:sum(value['status']==status for value in values.values()) for status in ('PASS','REVIEW_REQUIRED')},input_hash_observations=input_hash_observations,fixture_files_preserved=len(fixtures)+len(bad_inputs)+3,partial_output_bytes_retained=5,artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,child_xml_bindings_verified=xml_cli_checks==len(outcomes)-1,xml_bindings_checked_cli_cases=xml_cli_checks,unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fictional_checkpoint_progression_flow_checked=True,native_file_guards_checked=True,real_records_used=False,real_workbooks_used=False,imported=False,checkpoint_written=False,previous_checkpoint_authority_verified=False,target_changes_performed=False,row_counts_recomputed=False,receipt_authority_verified=False,exactly_once_verified=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered outcomes:

```json
[
  {
    "case": "full-contiguous-window",
    "exit_code": 0
  },
  {
    "case": "input-order-does-not-change-suggestion",
    "exit_code": 0
  },
  {
    "case": "identical-snapshots-count-once",
    "exit_code": 0
  },
  {
    "case": "previous-ordinal-is-not-reverified",
    "exit_code": 0
  },
  {
    "case": "equal-empty-window-zero",
    "exit_code": 0
  },
  {
    "case": "equal-empty-window-middle",
    "exit_code": 0
  },
  {
    "case": "equal-empty-window-upper",
    "exit_code": 0
  },
  {
    "case": "upper-ordinal-and-identifier-boundaries",
    "exit_code": 0
  },
  {
    "case": "one-thousand-contiguous-ordinals",
    "exit_code": 0
  },
  {
    "case": "one-batch-is-not-one-thousand-source-records",
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
    "case": "gap-is-not-a-missing-receipt",
    "exit_code": 1
  },
  {
    "case": "multiple-gaps-deduplicate-diagnostic",
    "exit_code": 1
  },
  {
    "case": "positive-empty-window-has-gap-only",
    "exit_code": 1
  },
  {
    "case": "coverage-with-missing-receipt-still-withholds",
    "exit_code": 1
  },
  {
    "case": "all-receipts-missing-is-not-a-coverage-gap",
    "exit_code": 1
  },
  {
    "case": "orphan-committed-is-unexpected-only",
    "exit_code": 1
  },
  {
    "case": "orphan-failed-is-unexpected-only",
    "exit_code": 1
  },
  {
    "case": "orphan-uncertain-is-unexpected-only",
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
    "case": "wrong-stream-can-resolve-but-never-suggest",
    "exit_code": 1
  },
  {
    "case": "accepted-position-before-window-blocks",
    "exit_code": 1
  },
  {
    "case": "accepted-position-after-window-blocks",
    "exit_code": 1
  },
  {
    "case": "equal-nonempty-window-is-not-a-noop-pass",
    "exit_code": 1
  },
  {
    "case": "equal-window-with-orphan-is-review",
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
    "case": "declared-source-counts-withhold",
    "exit_code": 1
  },
  {
    "case": "status-check-precedes-receipt-clean-check",
    "exit_code": 1
  },
  {
    "case": "sequence-alias-plus-deduplicated-gap",
    "exit_code": 1
  },
  {
    "case": "alias-diagnostics-use-first-accepted-position",
    "exit_code": 1
  },
  {
    "case": "content-alias-can-have-two-resolved-pairs",
    "exit_code": 1
  },
  {
    "case": "receipt-id-alias-withholds",
    "exit_code": 1
  },
  {
    "case": "candidate-conflicts-become-gap-and-orphan",
    "exit_code": 1
  },
  {
    "case": "conflicting-receipts-become-missing-not-outcome",
    "exit_code": 1
  },
  {
    "case": "malformed-candidate-withholds-resolved-pairs",
    "exit_code": 1
  },
  {
    "case": "malformed-receipt-withholds-resolved-pairs",
    "exit_code": 1
  },
  {
    "case": "all-malformed-candidates-gap-without-empty-cohort-code",
    "exit_code": 1
  },
  {
    "case": "unsupported-receipt-status-is-rejected",
    "exit_code": 1
  },
  {
    "case": "metadata-and-cross-list-sequence-alias-order",
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
    "case": "previous-boolean",
    "exit_code": 2
  },
  {
    "case": "proposed-boolean",
    "exit_code": 2
  },
  {
    "case": "previous-negative",
    "exit_code": 2
  },
  {
    "case": "proposed-above-ordinal-bound",
    "exit_code": 2
  },
  {
    "case": "previous-string",
    "exit_code": 2
  },
  {
    "case": "backward-window",
    "exit_code": 2
  },
  {
    "case": "window-one-over-width",
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

The 47 reports contain thirteen PASS results and 34 global holds. All 5,994
input-hash observations, 123 artifact hashes and manifest readback must match.
Every prior file stays byte-identical after every case. Full report bytes,
ordinals, issue lists, resolution counters, suggested values and eligibility are
explicit expected data. No generator or source-record matching oracle is used.

Compare `gap-is-not-a-missing-receipt` with
`coverage-with-missing-receipt-still-withholds`: coverage gaps and missing receipt
groups are different. `wrong-stream-can-resolve-but-never-suggest` has two internally
resolved pairs and still no suggestion. Multiple gaps share one fixed diagnostic.
Equal empty windows return the same ordinal with eligibility false, while the
full 1,000-ordinal boundary uses invented declarations only. A prior ordinal is
not independently reverified and a PASS never authorizes an actual advancement.

The otherwise valid orphan fixtures yield `UNEXPECTED_RECEIPT`; failed/uncertain
status adds no outcome/history diagnostic. Other inputs can also have independent
stream/alias issues. Metadata mismatch can prevent a later status diagnostic, and conflicted groups
are withheld before matching. Do not infer extra issue codes, a partial prefix,
verified commits or source completeness from any counter. Observed batch-list
accounting remains distinct from the record counts declared inside each batch.

`GUIDE-MANIFEST.json` lists every other retained file by relative name, length and
SHA-256. Keep all fixtures, reports and fingerprints private. The five-byte prefix
is intentionally unconfirmed, not a completed report, and cannot be reused as an
output. Audit hooks, process timeouts and native checks assume owned directories
and trusted quiescent inputs; they are not OS isolation, atomic snapshots,
safe-advancement proofs or hardware-durability guarantees.
