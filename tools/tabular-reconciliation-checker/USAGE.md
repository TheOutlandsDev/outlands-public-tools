# Fictional three-input reconciliation walkthrough

Keep the three runtime files together. From the source directory, compare the invented fixtures:

```text
python -E -s -B reconcile.py --before examples/before.json --after examples/after.json --contract examples/contract.json
python -E -s -B reconcile.py --before examples/before.json --after examples/after.json --contract examples/contract.json --show-values --out NEW_EXTERNAL_REPORT.json
```

Default qualified reports disclose identity values, changed field names, per-record hashes, selected totals and input fingerprints. Full changed records are included only with `--show-values`; neither mode anonymizes records. Any invalid/conflicting row globally sets changes, unchanged_records and totals to null, even when values_included is true. Meaning, units, completeness, authorization and business decisions remain caller assertions.

Save the Python block below verbatim as `fictional_reconciliation_walkthrough.py` outside the source directory. Supply the copied runtime directory and an existing trusted private parent, using appropriate absolute paths for PowerShell 5.1 or a POSIX shell:

```text
python -I -B fictional_reconciliation_walkthrough.py COPIED_TOOL_DIRECTORY EXISTING_PRIVATE_PARENT
```

For example, `D:\Private-Review` is a fictional parent placeholder to replace with your own existing private directory. Each run creates a new owned child and retains it. The program invokes actual script entrypoints with independently authored full expected records, changes, counts, issue positions and total strings. It never calls the comparator, scalar converter or grouping logic as its expected-results oracle.

The cases include equal totals of 19 with three row differences, default versus explicit values, matches/empty/one-sided sets, canonical duplicate accounting, global review holds, nullable fields, exact decimal normalization and arithmetic, literal/composite identities and all three input roles. Qualified arithmetic uses the selected default C Decimal binding/context (precision 28, `ROUND_HALF_EVEN`); arbitrary altered ambient library contexts are outside this proof.

The program uses invented JSON only. No generator, XML/DOCX document input, rendering, Office, SQL, provider connection, external write or unit conversion occurs. Its shared-toolkit XML binding checks are environment/buffer-boundary scope, not XML product ingestion. Audit hooks and cooperative parser/native bounds are not an OS sandbox, hard deadline or hostile-filesystem guarantee.

Every existing workspace entry and each input's bytes must remain unchanged. Separate hardlinks and 4 MiB byte bounds are checked for before, after and contract roles. Same-file before/after selection is explicitly allowed. New reports must not overwrite inputs or earlier outputs or reside in the source directory. A child-only native backend write fault retains five unconfirmed bytes; later reuse is refused. No automatic deletion, rollback, atomic snapshot or full metadata preservation is promised.

The program writes 29 exact reports, an observation ledger and a SHA-256 manifest, verifying every fixture/report byte and the three unchanged copied runtime files. It prints fixed case names/counts rather than private host paths. All 127 workspace files remain private; actual records or operational contracts are unnecessary.

```python
"""Fictional JSON reconciliation with explicit expected changes and exact totals."""
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
work=Path(tempfile.mkdtemp(prefix='fictional-reconciliation-',dir=parent)).resolve();assert work.parent==parent
runtimes=('reconcile.py','toolkit.py','native_windows.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
runtime_hashes={name:sha((module/name).read_bytes()) for name in runtimes}
inputs=work/'inputs';reports=work/'reports'
inputs.mkdir();reports.mkdir()

def field(name,kind='text',nullable=False):return dict(name=name,type=kind,nullable=nullable)
contracts={
 'base':dict(format='outlands-reconciliation-contract-v1',identity=['record_id'],fields=[field('record_id'),field('units','integer'),field('due','date'),field('active','boolean')],totals=['units']),
 'decimal':dict(format='outlands-reconciliation-contract-v1',identity=['id'],fields=[field('id'),field('amount','decimal')],totals=['amount']),
 'two-totals':dict(format='outlands-reconciliation-contract-v1',identity=['id'],fields=[field('id'),field('units','integer'),field('amount','decimal')],totals=['units','amount']),
 'composite':dict(format='outlands-reconciliation-contract-v1',identity=['id','sequence'],fields=[field('id'),field('sequence','integer'),field('units','integer')],totals=['units'])}
contracts['nullable']=dict(contracts['base'],fields=[*contracts['base']['fields'][:2],field('due','date',True),contracts['base']['fields'][3]])
contracts['no-totals']=dict(contracts['base'],totals=[])
contracts['field-order']=dict(contracts['base'],fields=[contracts['base']['fields'][0],contracts['base']['fields'][3],contracts['base']['fields'][2],contracts['base']['fields'][1]])
contract_raw={name:encoded(value) for name,value in contracts.items()}
def rec(key,units=12,due='2030-01-10',active=True):return dict(record_id=key,units=units,due=due,active=active)
def record_set(rows):return encoded(dict(format='outlands-record-set-v1',records=rows))
def count(n,accepted,duplicate=0,rejected=0,conflict=0):
    assert n==accepted+duplicate+rejected+conflict
    return dict(input_rows=n,accepted_records=accepted,duplicate_rows=duplicate,rejected_rows=rejected,conflict_rows=conflict)
def issue(side,row,code):return dict(side=side,row=row,code=code)
def change(identity,classification,fields,old,new,show=False):
    value=dict(identity=identity,classification=classification,changed_fields=fields,before_sha256=sha(encoded(old)) if old is not None else None,after_sha256=sha(encoded(new)) if new is not None else None)
    if show:value.update(before=old,after=new)
    return value
def total(before,after,delta):return dict(before=before,after=after,delta=delta)
def report(raw_before,raw_after,contract,status,before_counts,after_counts,changes,unchanged,totals,issues=(),show=False):
    assert status in ('MATCH','DIFFERENCES','REVIEW_REQUIRED')
    assert (status=='REVIEW_REQUIRED')==(bool(issues))
    if issues:assert changes is unchanged is totals is None
    else:assert type(changes) is list and type(unchanged) is int and type(totals) is dict and (status=='DIFFERENCES')==bool(changes)
    return dict(format='outlands-reconciliation-v1',status=status,before_sha256=sha(raw_before),after_sha256=sha(raw_after),contract_sha256=sha(contract_raw[contract]),
      before_counts=before_counts,after_counts=after_counts,changes=changes,unchanged_records=unchanged,totals=totals,issues=list(issues),values_included=show,external_system_writes=False)
a=rec('sample-a');b=rec('sample-b',7,'2030-01-11',False);aa=rec('sample-a',14);c=rec('sample-c',5,'2030-01-12')
base_before=[a,b];base_after=[aa,c];base_fields=['record_id','units','due','active']
def base_changes(show=False,fields=base_fields):return [change(dict(record_id='sample-a'),'CHANGED',['units'],a,aa,show),change(dict(record_id='sample-b'),'ONLY_IN_BEFORE',fields,b,None,show),change(dict(record_id='sample-c'),'ONLY_IN_AFTER',fields,None,c,show)]
fixtures=[]
def fixture(name,before,after,contract,status,bc,ac,changes,unchanged,totals,issues=(),show=False):
    old,new=record_set(before),record_set(after);value=report(old,new,contract,status,bc,ac,changes,unchanged,totals,issues,show)
    fixtures.append((name,old,new,contract,show,value))
fixture('equal-nineteen-still-has-three-differences',base_before,base_after,'base','DIFFERENCES',count(2,2),count(2,2),base_changes(),0,dict(units=total('19','19','0')))
fixture('explicit-values-reveal-complete-changed-records',base_before,base_after,'base','DIFFERENCES',count(2,2),count(2,2),base_changes(True),0,dict(units=total('19','19','0')),show=True)
fixture('identical-sets-match',base_before,base_before,'base','MATCH',count(2,2),count(2,2),[],2,dict(units=total('19','19','0')))
fixture('order-and-identical-duplicate-count-once',base_before,[b,a,a],'base','MATCH',count(2,2),count(3,2,duplicate=1),[],2,dict(units=total('19','19','0')))
fixture('empty-sets-qualified-zero-totals',[],[],'base','MATCH',count(0,0),count(0,0),[],0,dict(units=total('0','0','0')))
fixture('one-sided-after-records',[],base_before,'base','DIFFERENCES',count(0,0),count(2,2),[change(dict(record_id=r['record_id']),'ONLY_IN_AFTER',base_fields,None,r) for r in (a,b)],0,dict(units=total('0','19','19')))
fixture('one-sided-before-records',base_before,[],'base','DIFFERENCES',count(2,2),count(0,0),[change(dict(record_id=r['record_id']),'ONLY_IN_BEFORE',base_fields,r,None) for r in (a,b)],0,dict(units=total('19','0','-19')))
fixture('no-selected-total-fields',base_before,base_after,'no-totals','DIFFERENCES',count(2,2),count(2,2),base_changes(),0,{})
null_a=rec('sample-a',due=None)
fixture('explicit-null-is-valid-and-distinct', [null_a],[a],'nullable','DIFFERENCES',count(1,1),count(1,1),[change(dict(record_id='sample-a'),'CHANGED',['due'],null_a,a)],0,dict(units=total('12','12','0')))
fixture('nullable-explicit-null-can-match',[null_a],[null_a],'nullable','MATCH',count(1,1),count(1,1),[],1,dict(units=total('12','12','0')))
missing=dict(a);del missing['due']
fixture('nullable-does-not-allow-missing-field',[missing,b],base_after,'nullable','REVIEW_REQUIRED',count(2,1,rejected=1),count(2,2),None,None,None,[issue('before',1,'FIELDS_INVALID')])
conflict_after=[a,rec('sample-a',13),b]
conflicts=[issue('after',1,'IDENTITY_CONFLICT'),issue('after',2,'IDENTITY_CONFLICT')]
fixture('one-conflict-globally-withholds-comparison',base_before,conflict_after,'base','REVIEW_REQUIRED',count(2,2),count(3,1,conflict=2),None,None,None,conflicts)
fixture('show-values-cannot-bypass-review-hold',base_before,conflict_after,'base','REVIEW_REQUIRED',count(2,2),count(3,1,conflict=2),None,None,None,conflicts,show=True)
invalid_a=rec('sample-a','PRIVATE_REJECTED_TOKEN')
fixture('one-invalid-row-globally-withholds-comparison',[invalid_a,b],base_after,'base','REVIEW_REQUIRED',count(2,1,rejected=1),count(2,2),None,None,None,[issue('before',1,'INTEGER_VALUE_INVALID')])
fixture('both-sides-have-position-only-issues',[invalid_a,b],[aa,rec('sample-c',5,'2030-01-12','PRIVATE_BOOLEAN_TOKEN')],'base','REVIEW_REQUIRED',count(2,1,rejected=1),count(2,1,rejected=1),None,None,None,[issue('before',1,'INTEGER_VALUE_INVALID'),issue('after',2,'BOOLEAN_VALUE_INVALID')])
bool_a=rec('sample-a',True)
fixture('identical-invalid-inputs-are-not-a-match',[bool_a],[bool_a],'base','REVIEW_REQUIRED',count(1,0,rejected=1),count(1,0,rejected=1),None,None,None,[issue('before',1,'INTEGER_VALUE_INVALID'),issue('after',1,'INTEGER_VALUE_INVALID')])
old_dec=[dict(id='a',amount='0.1'),dict(id='b',amount='0.2')];new_dec=[dict(id='a',amount='0.3'),dict(id='b',amount='0.4')]
fixture('exact-decimal-totals-and-delta',old_dec,new_dec,'decimal','DIFFERENCES',count(2,2),count(2,2),[change(dict(id='a'),'CHANGED',['amount'],old_dec[0],new_dec[0]),change(dict(id='b'),'CHANGED',['amount'],old_dec[1],new_dec[1])],0,dict(amount=total('0.3','0.7','0.4')))
fixture('decimal-spelling-and-negative-zero-normalize',[dict(id='a',amount='1.500'),dict(id='b',amount='-0.000')],[dict(id='a',amount='1.5'),dict(id='b',amount='0')],'decimal','MATCH',count(2,2),count(2,2),[],2,dict(amount=total('1.5','1.5','0')))
fixture('normalized-decimal-duplicate-counts-once',[dict(id='a',amount='1.500'),dict(id='a',amount='1.5'),dict(id='b',amount='-0')],[dict(id='b',amount='0.000'),dict(id='a',amount='1.5')],'decimal','MATCH',count(3,2,duplicate=1),count(2,2),[],2,dict(amount=total('1.5','1.5','0')))
old_multi=[dict(id='a',units=-2,amount='-0.1'),dict(id='b',units=3,amount='0.2')];new_multi=[dict(id='a',units=1,amount='0.3'),dict(id='b',units=1,amount='-0.1')]
fixture('negative-values-and-two-selected-totals',old_multi,new_multi,'two-totals','DIFFERENCES',count(2,2),count(2,2),[change(dict(id='a'),'CHANGED',['units','amount'],old_multi[0],new_multi[0]),change(dict(id='b'),'CHANGED',['units','amount'],old_multi[1],new_multi[1])],0,dict(units=total('1','2','1'),amount=total('0.1','0.2','0.1')))
hi=rec('high',10**12);lo=rec('low',-10**12);hi2=rec('high',10**12-1);lo2=rec('low',-10**12+1)
fixture('integer-boundaries-and-zero-total-delta',[hi,lo],[hi2,lo2],'base','DIFFERENCES',count(2,2),count(2,2),[change(dict(record_id='high'),'CHANGED',['units'],hi,hi2),change(dict(record_id='low'),'CHANGED',['units'],lo,lo2)],0,dict(units=total('0','0','0')))
literal=[rec(' sample-a ',1),rec('Sample-a',2),rec('sample-a',3)]
fixture('identity-case-and-spaces-are-literal',literal,list(reversed(literal)),'base','MATCH',count(3,3),count(3,3),[],3,dict(units=total('6','6','0')))
old_comp=[dict(id='a',sequence=2,units=1),dict(id='a',sequence=10,units=2)];new_comp=[dict(id='a',sequence=2,units=3),dict(id='a',sequence=10,units=2)]
fixture('explicit-text-integer-composite-identity',old_comp,new_comp,'composite','DIFFERENCES',count(2,2),count(2,2),[change(dict(id='a',sequence=2),'CHANGED',['units'],old_comp[0],new_comp[0])],1,dict(units=total('3','5','2')))
fixture('contract-field-order-controls-change-field-order',base_before,base_after,'field-order','DIFFERENCES',count(2,2),count(2,2),base_changes(fields=['record_id','active','due','units']),0,dict(units=total('19','19','0')))
bad_text=[rec('',1),rec('X'*257,1),rec('line\nbreak',1),rec('delete\x7fmarker',1)]
fixture('mapped-text-length-and-ascii-controls',bad_text,[],'base','REVIEW_REQUIRED',count(4,0,rejected=4),count(0,0),None,None,None,[issue('before',n,'TEXT_VALUE_INVALID') for n in range(1,5)])
fixture('invalid-date-and-strict-boolean',[rec('date-a',1,'2031-02-29'),rec('bool-a',1,active=1)],[],'base','REVIEW_REQUIRED',count(2,0,rejected=2),count(0,0),None,None,None,[issue('before',1,'DATE_VALUE_INVALID'),issue('before',2,'BOOLEAN_VALUE_INVALID')])
bad_decimal=[dict(id='bad-a',amount='1e2'),dict(id='bad-b',amount='1.0000001'),dict(id='bad-c',amount='1000000000000.000001')]
fixture('decimal-grammar-and-quantity-bound',bad_decimal,[],'decimal','REVIEW_REQUIRED',count(3,0,rejected=3),count(0,0),None,None,None,[issue('before',n,'DECIMAL_VALUE_INVALID') for n in range(1,4)])
extra=dict(a,private_extra='PRIVATE_EXTRA_TOKEN')
fixture('row-schema-extra-field-is-rejected',[extra],[],'base','REVIEW_REQUIRED',count(1,0,rejected=1),count(0,0),None,None,None,[issue('before',1,'FIELDS_INVALID')])
bad_contracts=[]
def bad_contract(name,value,code):bad_contracts.append((name,encoded(value),code))
base=contracts['base']
bad_contract('contract-wrong-format',dict(base,format='fictional-invalid'),'CONTRACT_FORMAT_INVALID')
bad_contract('contract-empty-fields',dict(base,fields=[]),'FIELD_LIMIT')
bad_contract('contract-extra-field',dict(base,private_extra='fictional'),'FIELDS_INVALID')
bad_contract('contract-duplicate-field',dict(base,fields=base['fields']+[base['fields'][0]]),'DUPLICATE_FIELD')
bad_contract('contract-empty-identity',dict(base,identity=[]),'IDENTITY_REQUIRED')
bad_contract('contract-duplicate-identity',dict(base,identity=['record_id','record_id']),'FIELD_SELECTION_INVALID')
bad_contract('contract-unknown-identity',dict(base,identity=['unknown']),'FIELD_SELECTION_INVALID')
bad_contract('contract-identity-boolean',dict(base,identity=['active']),'IDENTITY_TYPE_INVALID')
bad_contract('contract-nullable-identity',dict(base,fields=[field('record_id',nullable=True),*base['fields'][1:]]),'IDENTITY_TYPE_INVALID')
bad_contract('contract-total-date',dict(base,totals=['due']),'TOTAL_TYPE_INVALID')
bad_contract('contract-nullable-total',dict(base,fields=[base['fields'][0],field('units','integer',True),*base['fields'][2:]]),'TOTAL_TYPE_INVALID')
bad_contract('contract-duplicate-total',dict(base,totals=['units','units']),'FIELD_SELECTION_INVALID')
bad_contract('contract-nullable-must-be-boolean',dict(base,fields=[dict(base['fields'][0],nullable='false'),*base['fields'][1:]]),'FIELD_INVALID')
bad_contract('contract-field-name-case',dict(base,fields=[dict(base['fields'][0],name='Record'),*base['fields'][1:]]),'IDENTIFIER_INVALID')
bad_json=[
 ('before-duplicate-json-key','before',b'{"format":1,"format":2}','JSON_DUPLICATE_KEY'),
 ('after-float-json-number','after',b'{"value":1.0}','JSON_INTEGER_OR_STRING_REQUIRED'),
 ('contract-nonfinite-json-number','contract',b'{"value":NaN}','JSON_INTEGER_OR_STRING_REQUIRED'),
 ('before-invalid-utf8','before',b'\xff','JSON_INVALID'),
 ('after-depth-bound','after',b'['*34+b'0'+b']'*34,'JSON_STRUCTURE_LIMIT'),
 ('before-json-integer-bound','before',b'{"value":1000000000000000001}','JSON_INTEGER_LIMIT'),
 ('before-record-set-format','before',encoded(dict(format='wrong',records=[])),'RECORD_SET_INVALID'),
 ('after-record-set-row-count','after',record_set([{}]*1001),'RECORD_SET_INVALID'),
 ('before-record-set-top-level-extra','before',encoded(dict(format='outlands-record-set-v1',records=[],extra=1)),'FIELDS_INVALID')]
for name,raw in contract_raw.items():(inputs/('contract-'+name+'.json')).write_bytes(raw)
for name,old,new,contract,show,value in fixtures:
    (inputs/(name+'-before.json')).write_bytes(old);(inputs/(name+'-after.json')).write_bytes(new)
for name,raw,code in bad_contracts:(inputs/(name+'.json')).write_bytes(raw)
for name,role,raw,code in bad_json:(inputs/(name+'.json')).write_bytes(raw)
for role in ('before','after','contract'):(inputs/('over-'+role+'.json')).write_bytes(b'X'*(4*1024*1024+1))
for role,raw in (('before',record_set(base_before)),('after',record_set(base_after)),('contract',contract_raw['base'])):
    original=inputs/('hard-'+role+'.json');original.write_bytes(raw);os.link(original,inputs/('hard-'+role+'-alias.json'))

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
finally:assert arithmetic_state()==expected_arithmetic
"""

outcomes=[];observations=[];report_rows=[];input_hash_observations=0;arithmetic_cli_checks=0
def run_case(case,args,code,expected,*,script='reconcile.py',readonly=True,helper=None):
    global input_hash_observations,arithmetic_cli_checks
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
    if helper is None:arithmetic_cli_checks+=1
def args_for(name,contract,show=False):
    args=['--before',inputs/(name+'-before.json'),'--after',inputs/(name+'-after.json'),'--contract',inputs/('contract-'+contract+'.json')]
    if show:args+=['--show-values']
    return args
def inspect_case(name,args,value):
    output=reports/(name+'.json');code=0 if value['status']=='MATCH' else 1
    run_case(name,[*args,'--out',output],code,dict(status=value['status'],report_written=True),readonly=False)
    assert output.read_bytes()==encoded(value)
    if os.name!='nt':assert output.stat().st_mode & 0o777==0o600
    report_rows.append(dict(case=name,path=output.relative_to(work).as_posix(),bytes=output.stat().st_size,sha256=sha(output.read_bytes()),before_sha256=value['before_sha256'],after_sha256=value['after_sha256'],contract_sha256=value['contract_sha256']))
for name,old,new,contract,show,value in fixtures:inspect_case(name,args_for(name,contract,show),value)
first=fixtures[0][0];base_args=args_for(first,'base')
run_case('default-stdout-report-is-exact',base_args,1,fixtures[0][-1])
same_path=inputs/(first+'-before.json');same_value=report(record_set(base_before),record_set(base_before),'base','MATCH',count(2,2),count(2,2),[],2,dict(units=total('19','19','0')))
inspect_case('same-single-link-file-can-fill-two-input-roles',['--before',same_path,'--after',same_path,'--contract',inputs/'contract-base.json'],same_value)
for name,raw,error in bad_contracts:
    run_case(name,['--before',inputs/(first+'-before.json'),'--after',inputs/(first+'-after.json'),'--contract',inputs/(name+'.json')],2,dict(status='ERROR',code=error))
for name,role,raw,error in bad_json:
    choices=dict(before=inputs/(first+'-before.json'),after=inputs/(first+'-after.json'),contract=inputs/'contract-base.json');choices[role]=inputs/(name+'.json')
    run_case(name,[item for key,path in choices.items() for item in ('--'+key,path)],2,dict(status='ERROR',code=error))
for role in ('before','after','contract'):
    choices=dict(before=inputs/(first+'-before.json'),after=inputs/(first+'-after.json'),contract=inputs/'contract-base.json');choices[role]=inputs/('over-'+role+'.json')
    run_case('refuse-'+role+'-input-byte-bound',[item for key,path in choices.items() for item in ('--'+key,path)],2,dict(status='ERROR',code='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'))
    choices[role]=inputs/('hard-'+role+'-alias.json')
    run_case('native-hardlink-'+role+'-refused',[item for key,path in choices.items() for item in ('--'+key,path)],2,dict(status='ERROR',code='CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'))
run_case('refuse-existing-report',[*base_args,'--out',reports/(first+'.json')],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
for role,path in (('before',inputs/(first+'-before.json')),('after',inputs/(first+'-after.json')),('contract',inputs/'contract-base.json')):
    run_case('refuse-output-alias-'+role,[*base_args,'--out',path],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
run_case('refuse-output-in-copied-source',[*base_args,'--out',module/'FICTIONAL-REFUSED.json'],2,dict(status='ERROR',code='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'))
assert not (module/'FICTIONAL-REFUSED.json').exists()
run_case('refuse-parent-traversal',['--before',inputs/'..'/'not-selected.json','--after',inputs/(first+'-after.json'),'--contract',inputs/'contract-base.json'],2,dict(status='ERROR',code='PATH_INVALID'))
run_case('refuse-missing-contract',['--before',inputs/(first+'-before.json'),'--after',inputs/(first+'-after.json')],2,dict(status='ERROR',code='ARGUMENTS_INVALID'))
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
for value in values.values():
    assert value['external_system_writes'] is False
    if value['status']=='REVIEW_REQUIRED':assert value['changes'] is value['unchanged_records'] is value['totals'] is None
    for side in ('before','after'):
        counts=value[side+'_counts'];assert counts['input_rows']==sum(counts[k] for k in ('accepted_records','duplicate_rows','rejected_rows','conflict_rows'))
    assert all(marker not in encoded(value) for marker in (b'PRIVATE_REJECTED_TOKEN',b'PRIVATE_BOOLEAN_TOKEN',b'PRIVATE_EXTRA_TOKEN'))
default=values['equal-nineteen-still-has-three-differences'];detail=values['explicit-values-reveal-complete-changed-records']
assert default['totals']['units']==dict(before='19',after='19',delta='0') and len(default['changes'])==3
assert all('before' not in row and 'after' not in row for row in default['changes'])
assert all('before' in row and 'after' in row for row in detail['changes'])
assert values['show-values-cannot-bypass-review-hold']['values_included'] is True
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix')
(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode('utf-8'))
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode('utf-8'))
assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,1,2)},
    reports_verified=len(report_rows),report_status_counts={status:sum(value['status']==status for value in values.values()) for status in ('MATCH','DIFFERENCES','REVIEW_REQUIRED')},input_hash_observations=input_hash_observations,fixture_files_preserved=2*len(fixtures)+len(contract_raw)+len(bad_contracts)+len(bad_json)+9,
    partial_output_bytes_retained=5,artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,
    unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,child_arithmetic_context_verified=arithmetic_cli_checks==len(outcomes)-1,arithmetic_context_checked_cli_cases=arithmetic_cli_checks,fictional_reconciliation_flow_checked=True,native_file_guards_checked=True,
    real_records_used=False,external_systems_accessed=False,external_system_writes=False,sql_queries_executed=False,input_sources_modified=False,
    source_completeness_verified=False,business_meaning_verified=False,unit_conversion_performed=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered outcomes:

```json
[
  {
    "case": "equal-nineteen-still-has-three-differences",
    "exit_code": 1
  },
  {
    "case": "explicit-values-reveal-complete-changed-records",
    "exit_code": 1
  },
  {
    "case": "identical-sets-match",
    "exit_code": 0
  },
  {
    "case": "order-and-identical-duplicate-count-once",
    "exit_code": 0
  },
  {
    "case": "empty-sets-qualified-zero-totals",
    "exit_code": 0
  },
  {
    "case": "one-sided-after-records",
    "exit_code": 1
  },
  {
    "case": "one-sided-before-records",
    "exit_code": 1
  },
  {
    "case": "no-selected-total-fields",
    "exit_code": 1
  },
  {
    "case": "explicit-null-is-valid-and-distinct",
    "exit_code": 1
  },
  {
    "case": "nullable-explicit-null-can-match",
    "exit_code": 0
  },
  {
    "case": "nullable-does-not-allow-missing-field",
    "exit_code": 1
  },
  {
    "case": "one-conflict-globally-withholds-comparison",
    "exit_code": 1
  },
  {
    "case": "show-values-cannot-bypass-review-hold",
    "exit_code": 1
  },
  {
    "case": "one-invalid-row-globally-withholds-comparison",
    "exit_code": 1
  },
  {
    "case": "both-sides-have-position-only-issues",
    "exit_code": 1
  },
  {
    "case": "identical-invalid-inputs-are-not-a-match",
    "exit_code": 1
  },
  {
    "case": "exact-decimal-totals-and-delta",
    "exit_code": 1
  },
  {
    "case": "decimal-spelling-and-negative-zero-normalize",
    "exit_code": 0
  },
  {
    "case": "normalized-decimal-duplicate-counts-once",
    "exit_code": 0
  },
  {
    "case": "negative-values-and-two-selected-totals",
    "exit_code": 1
  },
  {
    "case": "integer-boundaries-and-zero-total-delta",
    "exit_code": 1
  },
  {
    "case": "identity-case-and-spaces-are-literal",
    "exit_code": 0
  },
  {
    "case": "explicit-text-integer-composite-identity",
    "exit_code": 1
  },
  {
    "case": "contract-field-order-controls-change-field-order",
    "exit_code": 1
  },
  {
    "case": "mapped-text-length-and-ascii-controls",
    "exit_code": 1
  },
  {
    "case": "invalid-date-and-strict-boolean",
    "exit_code": 1
  },
  {
    "case": "decimal-grammar-and-quantity-bound",
    "exit_code": 1
  },
  {
    "case": "row-schema-extra-field-is-rejected",
    "exit_code": 1
  },
  {
    "case": "default-stdout-report-is-exact",
    "exit_code": 1
  },
  {
    "case": "same-single-link-file-can-fill-two-input-roles",
    "exit_code": 0
  },
  {
    "case": "contract-wrong-format",
    "exit_code": 2
  },
  {
    "case": "contract-empty-fields",
    "exit_code": 2
  },
  {
    "case": "contract-extra-field",
    "exit_code": 2
  },
  {
    "case": "contract-duplicate-field",
    "exit_code": 2
  },
  {
    "case": "contract-empty-identity",
    "exit_code": 2
  },
  {
    "case": "contract-duplicate-identity",
    "exit_code": 2
  },
  {
    "case": "contract-unknown-identity",
    "exit_code": 2
  },
  {
    "case": "contract-identity-boolean",
    "exit_code": 2
  },
  {
    "case": "contract-nullable-identity",
    "exit_code": 2
  },
  {
    "case": "contract-total-date",
    "exit_code": 2
  },
  {
    "case": "contract-nullable-total",
    "exit_code": 2
  },
  {
    "case": "contract-duplicate-total",
    "exit_code": 2
  },
  {
    "case": "contract-nullable-must-be-boolean",
    "exit_code": 2
  },
  {
    "case": "contract-field-name-case",
    "exit_code": 2
  },
  {
    "case": "before-duplicate-json-key",
    "exit_code": 2
  },
  {
    "case": "after-float-json-number",
    "exit_code": 2
  },
  {
    "case": "contract-nonfinite-json-number",
    "exit_code": 2
  },
  {
    "case": "before-invalid-utf8",
    "exit_code": 2
  },
  {
    "case": "after-depth-bound",
    "exit_code": 2
  },
  {
    "case": "before-json-integer-bound",
    "exit_code": 2
  },
  {
    "case": "before-record-set-format",
    "exit_code": 2
  },
  {
    "case": "after-record-set-row-count",
    "exit_code": 2
  },
  {
    "case": "before-record-set-top-level-extra",
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
    "case": "refuse-contract-input-byte-bound",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-contract-refused",
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
    "case": "refuse-output-alias-contract",
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
    "case": "refuse-missing-contract",
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

The summary verifies 68 observations (nine exit 0 accepted/control, 22 exit 1 difference/review results, 37 exit 2 intended refusals). Its 29 reports comprise eight matches, 11 differences and ten review-required global holds. It checks 95 unchanged input fixtures, 6,460 per-case input hash observations, five retained partial bytes and 126 payload hashes plus one manifest readback: 127 exact files. No unexpected application output or bytecode is accepted. See [qualification](docs/QUALIFICATION.md), [methodology](docs/METHODOLOGY.md) and retained [I/O history](IO-SAFETY.md).
