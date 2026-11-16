# Fictional intake-mapping revision walkthrough

This self-contained exercise authors complete expected reports independently of
`compare`, `intake.mapping` and `control_core.report`. It checks exact target-ID
change lists, canonical mapping hashes, input-byte fingerprints and privacy,
then retains evidence of controlled refusals. It never supplies real records,
validates a row, opens a workbook or evaluates a migration.

Copy only `mapping_diff.py`, `control_core.py`, `intake.py`, `toolkit.py` and
`native_windows.py` into a trusted source directory. Use the selected Python build
without `-O`/`-OO`; assertions are required. No pip packages are needed. Create a
separate empty private parent outside the source directory. Save the Python block
as `fictional_intake_mapping_walkthrough.py`, outside both directories, and pass
the source directory and private parent as its two arguments. Example paths are
fictional; choose your own.

```text
python -I -B fictional_intake_mapping_walkthrough.py "D:\Fictional-Source" "D:\Private-Review"
python -I -B fictional_intake_mapping_walkthrough.py "/home/example/fictional-source" "/home/example/private-review"
```

The first command is a Windows example and the second is a POSIX example. Each
run creates one fresh child directory. It retains 79 authored inputs, 23 full
reports, a five-byte controlled partial-write artifact, an observation ledger and
a manifest: 105 files. It checks every existing file before/after each case,
including failed writes. The 86 outcomes are nine exit 0, sixteen review results
and 61 controlled refusals. Eighty-five actual script-entrypoint children check
C XMLParser/TreeBuilder affinity before and in `finally` after execution. One
separate backend-fault helper is excluded from that CLI count. No Decimal context
or arithmetic-product check is implied.

```python
"""Fictional intake-mapping declarations with independently authored reports."""
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
work=Path(tempfile.mkdtemp(prefix='fictional-intake-mapping-',dir=parent)).resolve();assert work.parent==parent
runtimes=('mapping_diff.py','control_core.py','intake.py','toolkit.py','native_windows.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
runtime_hashes={name:sha((module/name).read_bytes()) for name in runtimes}
inputs=work/'inputs';reports=work/'reports'
inputs.mkdir();reports.mkdir()

def field(source,target,kind='text',required=True):return dict(source=source,target=target,type=kind,required=required)
base=dict(format='outlands-table-map-v1',identity=['record_id'],unknown_columns='reject',fields=[field('Record','record_id'),field('Units','units','integer')])
def outer(before,after):return dict(format='outlands-intake-mapping-diff-v1',before=before,after=after)
def change(target,code):return dict(target=target,code=code)
def expected(raw,before,after,changes):
    return dict(format='outlands-intake-mapping-diff-review-v1',status='REVIEW_REQUIRED' if changes else 'PASS',input_sha256=sha(raw),
      counts=dict(before_fields=len(before['fields']),after_fields=len(after['fields'])),issues=[],row_counts_recomputed=False,
      receipt_authority_verified=False,exactly_once_verified=False,target_changes_performed=False,changes=changes,
      before_mapping_sha256=sha(encoded(before)),after_mapping_sha256=sha(encoded(after)),compatibility_verified=False,rename_inferred=False,rows_validated=False)
fixtures=[]
def fixture(name,before,after,changes=(),*,raw=None):
    raw=encoded(outer(before,after)) if raw is None else raw
    fixtures.append((name,raw,expected(raw,before,after,list(changes))))
fixture('identical-maps-pass',base,base)
fixture('pretty-input-same-canonical-map-pins',base,base,raw=(json.dumps(outer(base,base),indent=2)+'\n').encode('utf-8'))
reordered={key:base[key] for key in reversed(base)};reordered['fields']=[{key:f[key] for key in reversed(f)} for f in base['fields']]
fixture('object-key-order-does-not-change-map',base,reordered,raw=(json.dumps(outer(base,reordered),separators=(',',':'))+'\n').encode('ascii'))
fixture('utf8-bom-changes-raw-input-only',base,base,raw=b'\xef\xbb\xbf'+encoded(outer(base,base)))
for name,updates,changes in (
 ('source-header-only',dict(source='PRIVATE_HEADER_SENTINEL'),[change('units','SOURCE_HEADER_CHANGED')]),
 ('type-only',dict(type='decimal'),[change('units','TYPE_CHANGED')]),
 ('required-only',dict(required=False),[change('units','REQUIRED_CHANGED')]),
 ('three-field-attributes-in-fixed-order',dict(source='Quantity',type='decimal',required=False),[change('units','SOURCE_HEADER_CHANGED'),change('units','TYPE_CHANGED'),change('units','REQUIRED_CHANGED')])):
    after=copy.deepcopy(base);after['fields'][1].update(updates);fixture(name,base,after,changes)
renamed=copy.deepcopy(base);renamed['fields'][1]['target']='quantity'
fixture('target-change-is-add-and-remove',base,renamed,[change('quantity','FIELD_ADDED'),change('units','FIELD_REMOVED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])
added=dict(base,fields=[*base['fields'],field('Optional Note','note',required=False)])
fixture('added-field-and-list-membership',base,added,[change('note','FIELD_ADDED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])
removed=dict(base,fields=[base['fields'][0]])
fixture('removed-field-and-list-membership',base,removed,[change('units','FIELD_REMOVED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])
fixture('field-order-is-significant',base,dict(base,fields=list(reversed(base['fields']))),[change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])
composite=dict(base,identity=['record_id','units'])
fixture('identity-order-is-significant',composite,dict(composite,identity=['units','record_id']),[change(None,'IDENTITY_ORDER_OR_MEMBERS_CHANGED')])
fixture('identity-membership-change',base,dict(base,identity=['units']),[change(None,'IDENTITY_ORDER_OR_MEMBERS_CHANGED')])
fixture('unknown-column-policy-change',base,dict(base,unknown_columns='ignore'),[change(None,'UNKNOWN_COLUMN_POLICY_CHANGED')])
many_before=dict(base,identity=['record_id','units']);many_after=copy.deepcopy(many_before)
many_after.update(identity=['units','record_id'],unknown_columns='ignore',fields=list(reversed(many_after['fields'])))
many_after['fields'][0].update(source='PRIVATE_CHANGED_UNITS',type='date')
many_after['fields'][1].update(source='PRIVATE_CHANGED_RECORD',type='boolean')
fixture('target-order-then-global-order',many_before,many_after,[change('record_id','SOURCE_HEADER_CHANGED'),change('record_id','TYPE_CHANGED'),change('units','SOURCE_HEADER_CHANGED'),change('units','TYPE_CHANGED'),change(None,'IDENTITY_ORDER_OR_MEMBERS_CHANGED'),change(None,'UNKNOWN_COLUMN_POLICY_CHANGED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])
literal=copy.deepcopy(base);literal['fields'][1]['source']='  literal # $ \\ \u03bb \U0001f9ea  '
fixture('literal-unicode-header-is-omitted',base,literal,[change('units','SOURCE_HEADER_CHANGED')])
case=copy.deepcopy(base);case['fields'][1]['source']='units'
fixture('source-header-case-is-literal',base,case,[change('units','SOURCE_HEADER_CHANGED')])
edge=copy.deepcopy(base);edge['fields'][1]['source']='H'*256
fixture('source-header-at-character-bound',base,edge,[change('units','SOURCE_HEADER_CHANGED')])
longtarget='a'+'x'*47;edge_target=dict(base,fields=[base['fields'][0],field('Long target',longtarget)])
fixture('target-at-identifier-bound',edge_target,edge_target)
maximum=dict(format='outlands-table-map-v1',identity=['f00','f01','f02','f03'],unknown_columns='reject',fields=[field('F'+str(i).zfill(2),'f'+str(i).zfill(2)) for i in range(32)])
fixture('thirty-two-fields-four-identities',maximum,maximum)
bool_identity=dict(base,identity=['units'],fields=[base['fields'][0],field('Units','units','boolean')])
fixture('required-boolean-identity-is-only-a-declaration',bool_identity,bool_identity)
changed_types=copy.deepcopy(base);changed_types['fields'][0]['type']='date';changed_types['fields'][1]['type']='boolean'
fixture('types-change-without-validating-records',base,changed_types,[change('record_id','TYPE_CHANGED'),change('units','TYPE_CHANGED')])
bad_maps=[]
def bad_map(name,value,code):bad_maps.append((name,value,code))
bad_map('map-format',dict(base,format='unsupported'),'MAP_INVALID')
bad_map('map-fields-empty',dict(base,fields=[]),'MAP_INVALID')
bad_map('map-thirty-three-fields',dict(maximum,fields=maximum['fields']+[field('F32','f32')]),'MAP_INVALID')
bad_map('map-identity-empty',dict(base,identity=[]),'MAP_IDENTITY_INVALID')
bad_map('map-identity-duplicate',dict(base,identity=['record_id','record_id']),'MAP_IDENTITY_INVALID')
bad_map('map-identity-unknown',dict(base,identity=['missing']),'MAP_IDENTITY_INVALID')
bad_map('map-five-identities',dict(maximum,identity=['f00','f01','f02','f03','f04']),'MAP_IDENTITY_INVALID')
bad_map('map-policy-invalid',dict(base,unknown_columns='guess'),'MAP_INVALID')
bad_map('map-top-extra',dict(base,extra='PRIVATE_EXTRA_SENTINEL'),'FIELDS_INVALID')
for name,updates,code in (
 ('map-source-empty',dict(source=''),'MAP_INVALID'),('map-source-too-long',dict(source='X'*257),'MAP_INVALID'),
 ('map-source-ascii-control',dict(source='line\nbreak'),'MAP_INVALID'),('map-source-del',dict(source='delete\x7fmarker'),'MAP_INVALID'),
 ('map-target-case',dict(target='Upper'),'IDENTIFIER_INVALID'),('map-required-integer',dict(required=1),'MAP_INVALID'),
 ('map-type-unsupported',dict(type='script'),'MAP_INVALID'),('map-field-extra',dict(extra='PRIVATE_EXTRA_SENTINEL'),'FIELDS_INVALID'),
 ('map-duplicate-source',dict(source='Record'),'MAP_DUPLICATE_FIELD'),('map-duplicate-target',dict(target='record_id'),'MAP_DUPLICATE_FIELD')):
    value=copy.deepcopy(base);value['fields'][1].update(updates);bad_map(name,value,code)
optional=copy.deepcopy(base);optional['fields'][0]['required']=False;bad_map('map-optional-identity',optional,'MAP_IDENTITY_INVALID')
bad_inputs=[('invalid-json',b'{','JSON_INVALID'),('duplicate-json-key',b'{"format":1,"format":2}','JSON_DUPLICATE_KEY'),
 ('floating-json-number',b'{"x":1.0}','JSON_INTEGER_OR_STRING_REQUIRED'),('nonfinite-json-number',b'NaN','JSON_INTEGER_OR_STRING_REQUIRED'),
 ('invalid-utf8',b'\xff','JSON_INVALID'),('unpaired-surrogate',b'"\\ud800"','JSON_INVALID'),
 ('json-depth-bound',b'['*34+b'0'+b']'*34,'JSON_STRUCTURE_LIMIT'),('json-text-bound',encoded(dict(value='X'*4097)),'JSON_TEXT_LIMIT'),
 ('json-integer-bound',b'{"value":1000000000000000001}','JSON_INTEGER_LIMIT'),('outer-list',b'[]','FIELDS_INVALID'),
 ('outer-extra-field',encoded(dict(outer(base,base),extra='PRIVATE_OUTER_SENTINEL')),'FIELDS_INVALID'),
 ('outer-format',encoded(dict(outer(base,base),format='unsupported')),'FORMAT_INVALID'),
 ('outer-missing-after',encoded(dict(format='outlands-intake-mapping-diff-v1',before=base)),'FIELDS_INVALID')]
for name,raw,report in fixtures:(inputs/(name+'.json')).write_bytes(raw)
for name,value,code in bad_maps:
    for side in ('before','after'):(inputs/(name+'-'+side+'.json')).write_bytes(encoded(outer(value,base) if side=='before' else outer(base,value)))
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
def run_case(case,args,code,expected,*,script='mapping_diff.py',readonly=True,helper=None):
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
    report_rows.append(dict(case=name,path=output.relative_to(work).as_posix(),bytes=output.stat().st_size,sha256=sha(output.read_bytes()),input_sha256=report['input_sha256'],before_mapping_sha256=report['before_mapping_sha256'],after_mapping_sha256=report['after_mapping_sha256']))
base_args=['--input',inputs/'identical-maps-pass.json']
run_case('default-stdout-report-is-exact',base_args,0,fixtures[0][-1])
for name,value,code in bad_maps:
    for side in ('before','after'):
        output=reports/(name+'-'+side+'.json');run_case(name+'-'+side,['--input',inputs/(name+'-'+side+'.json'),'--out',output],2,dict(status='ERROR',code=code));assert not output.exists()
for name,raw,code in bad_inputs:
    output=reports/(name+'.json');run_case(name,['--input',inputs/(name+'.json'),'--out',output],2,dict(status='ERROR',code=code));assert not output.exists()
for name,args,code in (
 ('input-byte-bound',['--input',inputs/'over-input.bin'],'INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'),
 ('native-hardlink-input',['--input',inputs/'hard-input-alias.json'],'CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE'),
 ('existing-report',[*base_args,'--out',reports/'identical-maps-pass.json'],'INPUT_OR_OUTPUT_REFUSED'),
 ('output-alias-input',[*base_args,'--out',inputs/'identical-maps-pass.json'],'INPUT_OR_OUTPUT_REFUSED'),
 ('output-inside-source',[*base_args,'--out',module/'FICTIONAL-REFUSED.json'],'OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'),
 ('parent-traversal',['--input',inputs/'..'/'not-selected.json'],'PATH_INVALID'),('missing-required-input',[],'ARGUMENTS_INVALID')):
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
    assert value['issues']==[] and all(value[key] is False for key in ('compatibility_verified','rename_inferred','rows_validated','target_changes_performed','row_counts_recomputed','receipt_authority_verified','exactly_once_verified'))
    assert all(marker not in encoded(value) for marker in (b'PRIVATE_HEADER_SENTINEL',b'PRIVATE_CHANGED_UNITS',b'PRIVATE_CHANGED_RECORD',b'PRIVATE_EXTRA_SENTINEL',b'PRIVATE_OUTER_SENTINEL'))
for name in ('pretty-input-same-canonical-map-pins','object-key-order-does-not-change-map','utf8-bom-changes-raw-input-only'):
    assert values[name]['before_mapping_sha256']==values[name]['after_mapping_sha256']==values['identical-maps-pass']['before_mapping_sha256']
    assert values[name]['input_sha256']!=values['identical-maps-pass']['input_sha256']
assert values['field-order-is-significant']['before_mapping_sha256']!=values['field-order-is-significant']['after_mapping_sha256']
assert values['source-header-case-is-literal']['changes']==[change('units','SOURCE_HEADER_CHANGED')]
assert b'"target":"units"' in encoded(values['source-header-case-is-literal'])
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix')
(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode('utf-8'))
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode('utf-8'))
assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,1,2)},
 reports_verified=len(report_rows),report_status_counts={status:sum(value['status']==status for value in values.values()) for status in ('PASS','REVIEW_REQUIRED')},
 input_hash_observations=input_hash_observations,fixture_files_preserved=len(fixtures)+2*len(bad_maps)+len(bad_inputs)+3,
 partial_output_bytes_retained=5,artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,
 child_xml_bindings_verified=xml_cli_checks==len(outcomes)-1,xml_bindings_checked_cli_cases=xml_cli_checks,unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,
 fictional_intake_mapping_flow_checked=True,native_file_guards_checked=True,real_records_used=False,real_workbooks_used=False,imported=False,source_transformed=False,
 compatibility_verified=False,rename_inferred=False,rows_validated=False,external_resources_followed=False,source_completeness_verified=False,production_workflows_verified=False),sort_keys=True))
```

Expected ordered outcomes:

```json
[
  {
    "case": "identical-maps-pass",
    "exit_code": 0
  },
  {
    "case": "pretty-input-same-canonical-map-pins",
    "exit_code": 0
  },
  {
    "case": "object-key-order-does-not-change-map",
    "exit_code": 0
  },
  {
    "case": "utf8-bom-changes-raw-input-only",
    "exit_code": 0
  },
  {
    "case": "source-header-only",
    "exit_code": 1
  },
  {
    "case": "type-only",
    "exit_code": 1
  },
  {
    "case": "required-only",
    "exit_code": 1
  },
  {
    "case": "three-field-attributes-in-fixed-order",
    "exit_code": 1
  },
  {
    "case": "target-change-is-add-and-remove",
    "exit_code": 1
  },
  {
    "case": "added-field-and-list-membership",
    "exit_code": 1
  },
  {
    "case": "removed-field-and-list-membership",
    "exit_code": 1
  },
  {
    "case": "field-order-is-significant",
    "exit_code": 1
  },
  {
    "case": "identity-order-is-significant",
    "exit_code": 1
  },
  {
    "case": "identity-membership-change",
    "exit_code": 1
  },
  {
    "case": "unknown-column-policy-change",
    "exit_code": 1
  },
  {
    "case": "target-order-then-global-order",
    "exit_code": 1
  },
  {
    "case": "literal-unicode-header-is-omitted",
    "exit_code": 1
  },
  {
    "case": "source-header-case-is-literal",
    "exit_code": 1
  },
  {
    "case": "source-header-at-character-bound",
    "exit_code": 1
  },
  {
    "case": "target-at-identifier-bound",
    "exit_code": 0
  },
  {
    "case": "thirty-two-fields-four-identities",
    "exit_code": 0
  },
  {
    "case": "required-boolean-identity-is-only-a-declaration",
    "exit_code": 0
  },
  {
    "case": "types-change-without-validating-records",
    "exit_code": 1
  },
  {
    "case": "default-stdout-report-is-exact",
    "exit_code": 0
  },
  {
    "case": "map-format-before",
    "exit_code": 2
  },
  {
    "case": "map-format-after",
    "exit_code": 2
  },
  {
    "case": "map-fields-empty-before",
    "exit_code": 2
  },
  {
    "case": "map-fields-empty-after",
    "exit_code": 2
  },
  {
    "case": "map-thirty-three-fields-before",
    "exit_code": 2
  },
  {
    "case": "map-thirty-three-fields-after",
    "exit_code": 2
  },
  {
    "case": "map-identity-empty-before",
    "exit_code": 2
  },
  {
    "case": "map-identity-empty-after",
    "exit_code": 2
  },
  {
    "case": "map-identity-duplicate-before",
    "exit_code": 2
  },
  {
    "case": "map-identity-duplicate-after",
    "exit_code": 2
  },
  {
    "case": "map-identity-unknown-before",
    "exit_code": 2
  },
  {
    "case": "map-identity-unknown-after",
    "exit_code": 2
  },
  {
    "case": "map-five-identities-before",
    "exit_code": 2
  },
  {
    "case": "map-five-identities-after",
    "exit_code": 2
  },
  {
    "case": "map-policy-invalid-before",
    "exit_code": 2
  },
  {
    "case": "map-policy-invalid-after",
    "exit_code": 2
  },
  {
    "case": "map-top-extra-before",
    "exit_code": 2
  },
  {
    "case": "map-top-extra-after",
    "exit_code": 2
  },
  {
    "case": "map-source-empty-before",
    "exit_code": 2
  },
  {
    "case": "map-source-empty-after",
    "exit_code": 2
  },
  {
    "case": "map-source-too-long-before",
    "exit_code": 2
  },
  {
    "case": "map-source-too-long-after",
    "exit_code": 2
  },
  {
    "case": "map-source-ascii-control-before",
    "exit_code": 2
  },
  {
    "case": "map-source-ascii-control-after",
    "exit_code": 2
  },
  {
    "case": "map-source-del-before",
    "exit_code": 2
  },
  {
    "case": "map-source-del-after",
    "exit_code": 2
  },
  {
    "case": "map-target-case-before",
    "exit_code": 2
  },
  {
    "case": "map-target-case-after",
    "exit_code": 2
  },
  {
    "case": "map-required-integer-before",
    "exit_code": 2
  },
  {
    "case": "map-required-integer-after",
    "exit_code": 2
  },
  {
    "case": "map-type-unsupported-before",
    "exit_code": 2
  },
  {
    "case": "map-type-unsupported-after",
    "exit_code": 2
  },
  {
    "case": "map-field-extra-before",
    "exit_code": 2
  },
  {
    "case": "map-field-extra-after",
    "exit_code": 2
  },
  {
    "case": "map-duplicate-source-before",
    "exit_code": 2
  },
  {
    "case": "map-duplicate-source-after",
    "exit_code": 2
  },
  {
    "case": "map-duplicate-target-before",
    "exit_code": 2
  },
  {
    "case": "map-duplicate-target-after",
    "exit_code": 2
  },
  {
    "case": "map-optional-identity-before",
    "exit_code": 2
  },
  {
    "case": "map-optional-identity-after",
    "exit_code": 2
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
    "case": "outer-missing-after",
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

The 23 reports include seven PASS and sixteen REVIEW_REQUIRED comparisons.
All 6,794 input-hash observations, 104 artifact hashes and the manifest readback
must match. Full report bytes, field counts, code order, symbolic targets and
canonical before/after mapping pins are explicit expectations, not a manifest-only
or application-generated oracle. No generator is used.

The pretty, reordered-object and BOM cases change the exact input hash while
retaining equal canonical mapping hashes. Field/identity list order still matters.
Source-header attributes are absent from output; equal strings can still appear
in retained target IDs or keys. The header-case example deliberately retains
target `units` when the changed source header is also `units`. Target identifiers,
counts, code lists and hashes remain private and can correlate a known input. A valid difference
has an empty `issues` list, a retained change list and `REVIEW_REQUIRED`; a malformed
map refuses the operation. No compatibility or rename verdict follows from PASS.

`GUIDE-MANIFEST.json` lists every other retained file by relative name, byte length
and SHA-256. Keep all fixtures, reports and hashes private. The partial prefix
is deliberately unconfirmed, is not a report and cannot be reused as an output.
The guard and audit checks assume owned directories and trusted, quiescent inputs;
they do not establish an OS sandbox, atomic snapshot or hardware durability.
