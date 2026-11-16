"""Independent copied mapping-declaration consumers; no records, workbooks or migration actions. MIT."""
import copy
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import random
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from xml.sax.saxutils import escape

WINDOWS_ID="test_copied_cli.CopiedCLI.test_native_windows_path_grammar_and_named_stream_routes"
WINDOWS_REASON="Native Windows path-grammar fixtures"
POSIX_ID="test_copied_cli.CopiedCLI.test_native_posix_special_inputs_and_private_report_mode"
POSIX_REASON="Native POSIX special-file and mode fixtures"
LINK_ID="test_copied_cli.CopiedCLI.test_native_leaf_symlink_and_dangling_output_refusal"
LINK_REASON="Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS={(POSIX_ID,POSIX_REASON)}
REQUIRED_POSIX_SKIPS={(WINDOWS_ID,WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS={(LINK_ID,LINK_REASON)}

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=("mapping_diff.py","control_core.py","intake.py","toolkit.py","native_windows.py")
FALSE_FLAGS=("real_records_used","real_workbooks_used","imported","source_transformed","compatibility_verified","rename_inferred",
             "rows_validated","external_resources_followed","source_completeness_verified","production_workflows_verified")
FLOW_IDS={"test_copied_cli.CopiedCLI.test_complete_identical_report_and_fresh_output_are_exact",
          "test_copied_cli.CopiedCLI.test_fictional_changed_declarations_keep_descriptive_review_changes",
          "test_copied_cli.CopiedCLI.test_target_replacement_is_added_removed_without_rename_inference"}
COMMON_NATIVE_IDS={"test_copied_cli.CopiedCLI.test_no_overwrite_and_standalone_collection_source_output_guards",
                   "test_copied_cli.CopiedCLI.test_retained_partial_report_is_not_confirmed_or_replaced",
                   "test_copied_cli.CopiedCLI.test_mandatory_hardlink_inputs_and_existing_outputs_are_refused",
                   "test_copied_cli.CopiedCLI.test_linked_parent_read_and_report_routes_are_refused"}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return (json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(",",":"))+"\n").encode()


def field(source,target,kind="text",required=True):return dict(source=source,target=target,type=kind,required=required)


def mapping(fields=None,identity=None,unknown="reject"):
    if fields is None:fields=[field("Record","record_id"),field("Units","units","integer")]
    return dict(format="outlands-table-map-v1",identity=[fields[0]["target"]] if identity is None else identity,unknown_columns=unknown,fields=fields)


def selected(before=None,after=None):
    before=mapping() if before is None else before
    return dict(format="outlands-intake-mapping-diff-v1",before=copy.deepcopy(before),after=copy.deepcopy(before if after is None else after))


def change(target,code):return dict(target=target,code=code)


def expected(raw,value,changes=()):
    # The caller authors every target/code observation; no matching or classification oracle.
    return dict(format="outlands-intake-mapping-diff-review-v1",status="REVIEW_REQUIRED" if changes else "PASS",input_sha256=sha(raw),
        counts=dict(before_fields=len(value["before"]["fields"]),after_fields=len(value["after"]["fields"])),issues=[],
        row_counts_recomputed=False,receipt_authority_verified=False,exactly_once_verified=False,target_changes_performed=False,
        changes=list(changes),before_mapping_sha256=sha(canonical(value["before"])),after_mapping_sha256=sha(canonical(value["after"])),
        compatibility_verified=False,rename_inferred=False,rows_validated=False)


CHILD=r'''
import _elementtree,hashlib,importlib.metadata,json,os,pyexpat,runpy,sys
from pathlib import Path
from types import SimpleNamespace
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();mode=sys.argv[2];args=sys.argv[3:];sys.path.insert(0,str(base))
def audit(event,values):
 if event.startswith(('socket.','subprocess.','os.startfile','sqlite3.')) or event in ('os.system','webbrowser.open'):
  raise AssertionError('UNEXPECTED_NETWORK_RECORD_STORE_OR_PROCESS')
sys.addaudithook(audit)
import mapping_diff as a
import control_core as c
import intake as i
import toolkit as t
import native_windows as n
for module,name in ((a,'mapping_diff.py'),(c,'control_core.py'),(i,'intake.py'),(t,'toolkit.py'),(n,'native_windows.py')):assert Path(module.__file__).resolve()==base/name
assert a.t is c.t is i.t is t and a.c is c and a.intake is i
assert a.compare.__globals__ is a.__dict__ and i.mapping.__globals__ is i.__dict__ and c.report.__globals__ is c.__dict__
assert t.read.__globals__ is t.__dict__ and t.write_new.__globals__ is t.__dict__
def unused(*a,**kw):raise AssertionError('MAPPING_DECLARATIONS_CALLED_UNUSED_RECORD_OR_XML_PIPELINE')
for name in ('preview','_convert','csv_rows','xlsx_rows'):setattr(i,name,unused)
for name in ('rows','accounting','batch','receipt','prepare','reconcile'):setattr(c,name,unused)
t.xml=unused
def bindings():
 assert t.ET.XMLParser is _elementtree.XMLParser and t.ET.TreeBuilder is _elementtree.TreeBuilder and t.XMLBuilder.__mro__[1] is _elementtree.TreeBuilder
 return (t.ET.XMLParser,t.ET.TreeBuilder,t.XMLBuilder.__mro__[1],pyexpat.EXPAT_VERSION)
initial=bindings()
try:
 if mode=='affinity':sys.stdout.write(t.encode(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=5,unused_record_readers_forbidden=True)).decode());raise SystemExit(0)
 if mode=='api':
  path=Path(args[0]);assert path.is_absolute()
  try:value=a.compare(path.read_bytes())
  except t.Rejected as error:sys.stdout.write(t.encode(dict(status='ERROR',code=str(error))).decode());raise SystemExit(2)
  sys.stdout.write(t.encode(value).decode());raise SystemExit(0 if value['status']=='PASS' else 1)
 if mode in ('short-read','changed-stat'):
  real_read=os.read;real_stat=os.fstat;changed=False
  def read(*values):
   global changed
   if mode=='short-read':return b''
   raw=real_read(*values)
   if raw:changed=True
   return raw
  def info(fd):
   value=real_stat(fd)
   if not changed:return value
   fields={name:getattr(value,name) for name in dir(value) if name.startswith('st_')};fields['st_mtime_ns']+=1;return SimpleNamespace(**fields)
  os.read=read;os.fstat=info
 elif mode=='write-failure':
  real_write=os.write;written=False
  def write(fd,data):
   global written
   if written:raise OSError('FICTIONAL_PRIVATE_WRITE_FAILURE')
   written=True;return real_write(fd,data[:5])
  os.write=write
 elif mode=='output-budget':t.MAX_OUTPUT=1
 elif mode!='normal':raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
 sys.argv=[str(base/'mapping_diff.py'),*args];runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('MAPPING_ENTRYPOINT_DID_NOT_EXIT')
finally:assert bindings()==initial,'SELECTED_XML_BINDINGS_CHANGED'
'''


class CopiedCLI(unittest.TestCase):
    strict_links=None
    native_events=[]
    checked_children=0
    @classmethod
    def setUpClass(cls):
        cls.python_binary=Path(sys._base_executable).resolve();cls.python_pin=sha(cls.python_binary.read_bytes());cls.python_bytes=cls.python_binary.stat().st_size
        cls.python_version=".".join(map(str,sys.version_info[:3]))
        if cls.python_pin!=os.environ["OUTLANDS_TEST_PYTHON_SHA256"] or cls.python_version!=os.environ["OUTLANDS_TEST_PYTHON_VERSION"]:
            raise AssertionError("EXPECTED_PYTHON_BINARY_OR_VERSION_DIFFERS")
    @classmethod
    def tearDownClass(cls):
        if sha(cls.python_binary.read_bytes())!=cls.python_pin or cls.python_binary.stat().st_size!=cls.python_bytes:raise AssertionError("PYTHON_BINARY_CHANGED")
    def setUp(self):
        self.assertNotEqual(sys.prefix,sys.base_prefix);self.assertEqual(list(importlib.metadata.distributions()),[])
        parent=Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or tempfile.gettempdir());self.assertTrue(parent.is_absolute() and parent.is_dir());parent=parent.resolve(strict=True)
        self.temp=tempfile.TemporaryDirectory(prefix="intake-map-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.assertEqual(self.work.parent,parent);self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();(self.copy/name).write_bytes(raw);self.pins[name]=sha(raw)
        self.input=self.work/"mappings.json";self.input.write_bytes(canonical(selected()));self.output=self.work/"report.json"
        self.env={key:value for key,value in os.environ.items() if not key.upper().startswith(("PYTHON","PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHON_COLORS="0",NO_COLOR="1");self.addCleanup(self.runtime_preserved)
    def runtime_preserved(self):
        self.assertEqual({p.name for p in self.copy.iterdir()},set(RUNTIME));self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME},self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")),[])
    def owned(self,path):
        path=Path(path);self.assertTrue(path.is_absolute() and path.resolve().is_relative_to(self.work));return path
    def write(self,raw):self.input.write_bytes(raw)
    def snapshot(self):
        rows={}
        def visit(folder):
            for path in folder.iterdir():
                info=path.lstat();key=path.relative_to(self.work).as_posix()
                if path.is_symlink() or getattr(path,"is_junction",lambda:False)():rows[key]=("LINK",os.readlink(path))
                elif stat.S_ISDIR(info.st_mode):rows[key]=("DIRECTORY",);visit(path)
                elif stat.S_ISREG(info.st_mode):rows[key]=(sha(path.read_bytes()),info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_ino,info.st_nlink)
                else:rows[key]=("SPECIAL",info.st_mode)
        visit(self.work);return rows
    def invoke(self,args=(),*,mode="normal",code=0,error=None,allow=(),base=None,text=False):
        before=self.snapshot()
        done=subprocess.run([sys.executable,"-I","-B","-W","error","-c",CHILD,str(self.copy if base is None else base),mode,*map(str,args)],
            cwd=self.work,env=self.env,stdin=subprocess.DEVNULL,capture_output=True,timeout=60)
        self.assertEqual(done.returncode,code,done.stderr.decode(errors="replace")[:3000]);self.assertEqual(done.stderr,b"");type(self).checked_children+=1
        for private in (str(self.work).encode(),b"FICTIONAL_PRIVATE",b"Traceback"):self.assertNotIn(private,done.stdout)
        after=self.snapshot();self.assertEqual(before,{key:after.get(key) for key in before})
        allowed={self.owned(path).relative_to(self.work).as_posix() for path in allow};self.assertEqual(sorted(after.keys()-before.keys()-allowed),[],"Unexpected relative file creation")
        self.runtime_preserved()
        if text:return done.stdout.decode("ascii")
        value=json.loads(done.stdout)
        if code==2:
            self.assertEqual(set(value),{"status","code"});self.assertEqual(value["status"],"ERROR");self.assertRegex(value["code"],r"^[A-Z][A-Z0-9_]{0,100}$")
            if error is not None:self.assertEqual(value["code"],error)
        elif value.get("format")=="outlands-intake-mapping-diff-review-v1":
            self.assertEqual(value["input_sha256"],sha(self.input.read_bytes()));self.assertEqual(value["issues"],[])
            for key in ("row_counts_recomputed","receipt_authority_verified","exactly_once_verified","target_changes_performed","compatibility_verified","rename_inferred","rows_validated"):self.assertIs(value[key],False)
        return value
    def cli(self,*,out=False,**kwargs):return self.invoke(["--input",self.input,*(["--out",self.output] if out else [])],**kwargs)
    def api(self,**kwargs):return self.invoke([self.input],mode="api",**kwargs)
    def check(self,value,changes=(),raw=None,api=True):
        raw=canonical(value) if raw is None else raw;self.write(raw);want=expected(raw,value,changes);code=0 if not changes else 1
        self.assertEqual(self.cli(code=code),want)
        if api:self.assertEqual(self.api(code=code),want)
        return want
    def refused(self,raw,code=None):
        self.write(raw);self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
    def invalid_map(self,config,code):
        for role in ("before","after"):
            value=selected();value[role]=copy.deepcopy(config);self.refused(canonical(value),code)
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            strict=self.strict_links if self.strict_links is not None else os.name!="nt" or os.environ.get("OUTLANDS_INTAKE_MAPPING_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
            actual=os.name=="nt" and getattr(error,"winerror",None)==1314
            if actual and not strict:
                self.assertEqual(self.id(),LINK_ID);self.assertFalse(directory);self.native_events.append(dict(test=self.id(),reason=LINK_REASON,policy="actual_windows_1314",actual_windows_1314=True,winerror=1314,strict=False,provenance="test_copied_cli.CopiedCLI.symlink/caught-OSError"));self.skipTest(LINK_REASON)
            raise

    def test_copied_affinity_and_actual_entrypoint_help_are_inert(self):
        self.assertEqual(self.invoke(mode='affinity'),dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=5,unused_record_readers_forbidden=True))
        self.assertIn('--input',self.invoke(['--help'],text=True));self.assertIn('--out',self.invoke(['--help'],text=True))
        self.invoke(code=2,error='ARGUMENTS_INVALID');self.invoke(['--unknown','FICTIONAL_PRIVATE_SENTINEL'],code=2,error='ARGUMENTS_INVALID')

    def test_complete_identical_report_and_fresh_output_are_exact(self):
        value=selected();report=self.check(value);self.assertEqual(report['before_mapping_sha256'],report['after_mapping_sha256'])
        self.assertEqual(self.cli(out=True,allow=[self.output]),dict(status='PASS',report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))
        self.assertEqual(set(report['counts']),{'before_fields','after_fields'});self.assertEqual(report['changes'],[])

    def test_fictional_changed_declarations_keep_descriptive_review_changes(self):
        value=selected();value['after']['fields'][1].update(source='Quantity',type='decimal',required=False)
        changes=[change('units',code) for code in ('SOURCE_HEADER_CHANGED','TYPE_CHANGED','REQUIRED_CHANGED')];report=self.check(value,changes)
        self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertEqual(report['issues'],[]);self.assertEqual(report['changes'],changes)
        self.assertEqual(self.cli(out=True,code=1,allow=[self.output]),dict(status='REVIEW_REQUIRED',report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))

    def test_source_header_case_whitespace_literals_and_unicode_are_not_exported(self):
        before=mapping();before['fields'][1]['source']='  Fictional $HOME # "header" \\ '+chr(0x03bb)+' '+chr(0x1f9ea)+'  '
        after=copy.deepcopy(before);after['fields'][1]['source']=before['fields'][1]['source'].replace('header','HEADER')
        report=self.check(selected(before,after),[change('units','SOURCE_HEADER_CHANGED')])
        for marker in (before['fields'][1]['source'],after['fields'][1]['source'],'Fictional','$HOME',chr(0x03bb),chr(0x1f9ea)):self.assertNotIn(marker,json.dumps(report))
        self.assertEqual(report['changes'][0]['target'],'units');self.assertNotEqual(report['before_mapping_sha256'],report['after_mapping_sha256'])

    def test_all_five_declared_types_are_compared_without_conversion(self):
        for kind in ('text','decimal','boolean','date'):
            value=selected();value['after']['fields'][1]['type']=kind
            self.check(value,[change('units','TYPE_CHANGED')])
        value=selected();value['before']['fields'][1]['type']='decimal';value['after']['fields'][1]['type']='text'
        self.check(value,[change('units','TYPE_CHANGED')])

    def test_required_flag_changes_are_descriptive_and_strictly_boolean(self):
        value=selected();value['after']['fields'][1]['required']=False;self.check(value,[change('units','REQUIRED_CHANGED')])
        value=selected(value['after'],value['before']);self.check(value,[change('units','REQUIRED_CHANGED')])
        for bad in (0,1,'false',None):
            config=mapping();config['fields'][1]['required']=bad;self.invalid_map(config,'MAP_INVALID')

    def test_added_removed_targets_sort_by_identifier_and_record_membership(self):
        before=mapping();after=copy.deepcopy(before);after['fields']=[field('Zulu','zulu'),*after['fields'],field('Alpha','alpha')]
        changes=[change('alpha','FIELD_ADDED'),change('zulu','FIELD_ADDED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')]
        self.check(selected(before,after),changes)
        self.check(selected(after,before),[change('alpha','FIELD_REMOVED'),change('zulu','FIELD_REMOVED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])

    def test_target_replacement_is_added_removed_without_rename_inference(self):
        value=selected();value['after']['fields'][1].update(target='quantity',source='Different source',type='text',required=False)
        report=self.check(value,[change('quantity','FIELD_ADDED'),change('units','FIELD_REMOVED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])
        self.assertIs(report['rename_inferred'],False);self.assertNotIn('SOURCE_HEADER_CHANGED',json.dumps(report));self.assertNotIn('TYPE_CHANGED',json.dumps(report))

    def test_identity_order_and_membership_are_significant_without_field_changes(self):
        before=mapping(identity=['record_id','units']);after=copy.deepcopy(before);after['identity'].reverse()
        self.check(selected(before,after),[change(None,'IDENTITY_ORDER_OR_MEMBERS_CHANGED')])
        after['identity']=['record_id'];self.check(selected(before,after),[change(None,'IDENTITY_ORDER_OR_MEMBERS_CHANGED')])
        after['identity']=['units'];self.check(selected(mapping(),after),[change(None,'IDENTITY_ORDER_OR_MEMBERS_CHANGED')])

    def test_field_list_order_changes_canonical_pin_without_paired_field_codes(self):
        value=selected();value['after']['fields'].reverse();report=self.check(value,[change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])
        self.assertNotEqual(report['before_mapping_sha256'],report['after_mapping_sha256']);self.assertEqual(report['counts'],dict(before_fields=2,after_fields=2))

    def test_unknown_column_policy_and_global_change_order_are_exact(self):
        value=selected();value['after']['unknown_columns']='ignore';self.check(value,[change(None,'UNKNOWN_COLUMN_POLICY_CHANGED')])
        value['before']['identity']=['record_id','units'];value['after']['identity']=['units','record_id'];value['after']['fields'].reverse()
        self.check(value,[change(None,code) for code in ('IDENTITY_ORDER_OR_MEMBERS_CHANGED','UNKNOWN_COLUMN_POLICY_CHANGED','FIELD_ORDER_OR_MEMBERS_CHANGED')])

    def test_each_target_has_source_type_required_code_order_before_globals(self):
        before=mapping([field('Zulu','zulu'),field('Alpha','alpha')],['zulu']);after=mapping([field('Different Alpha','alpha','boolean'),field('Different Zulu','zulu','integer',False)],['alpha'],'ignore')
        changes=[change('alpha','SOURCE_HEADER_CHANGED'),change('alpha','TYPE_CHANGED'),change('zulu','SOURCE_HEADER_CHANGED'),change('zulu','TYPE_CHANGED'),change('zulu','REQUIRED_CHANGED'),change(None,'IDENTITY_ORDER_OR_MEMBERS_CHANGED'),change(None,'UNKNOWN_COLUMN_POLICY_CHANGED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')]
        self.check(selected(before,after),changes)

    def test_reversing_valid_inputs_reverses_added_removed_and_mapping_pins(self):
        before=mapping();after=copy.deepcopy(before);after['fields'].append(field('Extra','extra'))
        a=self.check(selected(before,after),[change('extra','FIELD_ADDED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])
        b=self.check(selected(after,before),[change('extra','FIELD_REMOVED'),change(None,'FIELD_ORDER_OR_MEMBERS_CHANGED')])
        self.assertEqual(a['before_mapping_sha256'],b['after_mapping_sha256']);self.assertEqual(a['after_mapping_sha256'],b['before_mapping_sha256'])

    def test_outer_bom_whitespace_and_object_key_order_affect_only_raw_pin(self):
        value=selected();baseline=self.check(value)
        reordered=dict(reversed(list(value.items())))
        for side in ('before','after'):
            reordered[side]=dict(reversed(list(reordered[side].items())));reordered[side]['fields']=[dict(reversed(list(row.items()))) for row in reordered[side]['fields']]
        raw=b'\xef\xbb\xbf'+json.dumps(reordered,ensure_ascii=True,indent=3).encode()+b'\n  '
        report=self.check(reordered,raw=raw);self.assertNotEqual(baseline['input_sha256'],report['input_sha256'])
        self.assertEqual({key:value for key,value in baseline.items() if key!='input_sha256'},{key:value for key,value in report.items() if key!='input_sha256'})

    def test_outer_shapes_unknown_fields_and_wrong_formats_refuse_entirely(self):
        for value,code in ((None,'FIELDS_INVALID'),([], 'FIELDS_INVALID'),({},'FIELDS_INVALID'),(dict(selected(),extra='FICTIONAL_PRIVATE_OUTER'),'FIELDS_INVALID'),(dict(selected(),format='wrong'),'FORMAT_INVALID')):
            self.refused(canonical(value),code)
        for role in ('before','after'):
            value=selected();value.pop(role);self.refused(canonical(value),'FIELDS_INVALID')
            value=selected();value[role]=None;self.refused(canonical(value),'FIELDS_INVALID')

    def test_invalid_maps_in_either_role_never_return_partial_comparisons(self):
        variants=[]
        for key,bad,code in (('format','wrong','MAP_INVALID'),('fields',[],'MAP_INVALID'),('unknown_columns',False,'MAP_INVALID')):
            config=mapping();config[key]=bad;variants.append((config,code))
        config=mapping();config['extra']='FICTIONAL_PRIVATE_MAP';variants.append((config,'FIELDS_INVALID'))
        config=mapping();config['fields'][1]['type']='script';variants.append((config,'MAP_INVALID'))
        config=mapping();config['fields'][1]['target']='Upper';variants.append((config,'IDENTIFIER_INVALID'))
        config=mapping();config['fields'][1]['target']='record_id';variants.append((config,'MAP_DUPLICATE_FIELD'))
        config=mapping();config['fields'][1]['source']='Record';variants.append((config,'MAP_DUPLICATE_FIELD'))
        for config,code in variants:self.invalid_map(config,code)

    def test_source_header_character_limits_are_distinct_from_json_limits(self):
        config=mapping();config['fields'][1]['source']='x'*256;self.check(selected(config))
        for source in ('','x'*257,'line\nbreak','tab\tvalue','null\x00value','delete\x7fvalue'):
            config=mapping();config['fields'][1]['source']=source;self.invalid_map(config,'MAP_INVALID')
        config=mapping();config['fields'][1]['source']='x'*4097
        for role in ('before','after'):
            value=selected();value[role]=config;self.refused(canonical(value),'JSON_TEXT_LIMIT')
        config=mapping();config['fields'][1]['source']='literal'+chr(0x85)+'value';self.check(selected(config))

    def test_identity_bounds_members_uniqueness_and_required_constraints_refuse(self):
        for identity in ([],['record_id','record_id'],['missing'],[True],None,['a','b','c','d','e']):
            config=mapping();config['identity']=identity;self.invalid_map(config,'MAP_IDENTITY_INVALID')
        config=mapping();config['fields'][0]['required']=False;self.invalid_map(config,'MAP_IDENTITY_INVALID')
        fields=[field('Header'+str(i),'f'+str(i)) for i in range(4)];config=mapping(fields,[row['target'] for row in fields]);self.check(selected(config))

    def test_exact_32_fields_report_all_99_authored_changes_and_33_refuses(self):
        before_fields=[field('Before'+str(i),'f'+str(i).zfill(2),'text',i==0) for i in range(32)]
        after_fields=[field('After'+str(i),'f'+str(i).zfill(2),'integer',i!=0) for i in range(32)]
        before=mapping(before_fields,['f00']);after=mapping(list(reversed(after_fields)),['f01'],'ignore')
        changes=[change('f'+str(i).zfill(2),code) for i in range(32) for code in ('SOURCE_HEADER_CHANGED','TYPE_CHANGED','REQUIRED_CHANGED')]+[change(None,code) for code in ('IDENTITY_ORDER_OR_MEMBERS_CHANGED','UNKNOWN_COLUMN_POLICY_CHANGED','FIELD_ORDER_OR_MEMBERS_CHANGED')]
        report=self.check(selected(before,after),changes);self.assertEqual(len(report['changes']),99)
        bad=copy.deepcopy(before);bad['fields'].append(field('Additional','additional'));self.invalid_map(bad,'MAP_INVALID')
        one=mapping([field('One','one')]);self.check(selected(one))

    def test_json_duplicate_keys_float_integer_unicode_depth_and_node_caps_refuse(self):
        for raw,code in ((b'{"format":1,"format":2}','JSON_DUPLICATE_KEY'),(b'1.0','JSON_INTEGER_OR_STRING_REQUIRED'),(b'NaN','JSON_INTEGER_OR_STRING_REQUIRED'),(b'Infinity','JSON_INTEGER_OR_STRING_REQUIRED'),(b'1000000000000000001','JSON_INTEGER_LIMIT'),(b'"\\ud800"','JSON_INVALID'),(b'\xff','JSON_INVALID'),(b'['*34+b'0'+b']'*34,'JSON_STRUCTURE_LIMIT'),(b'['+b'0,'*100000+b'0]','JSON_STRUCTURE_LIMIT')):
            self.refused(raw,code)
        raw=canonical(selected()).replace(b'"type":"integer"',b'"type":"integer","type":"text"',1);self.refused(raw,'JSON_DUPLICATE_KEY')

    def test_exact_four_mebibyte_whitespace_input_and_one_over_refusal(self):
        value=selected();raw=canonical(value);raw+=b' '*(4194304-len(raw));self.assertEqual(len(raw),4194304);self.check(value,raw=raw)
        self.write(raw+b' ');self.api(code=2,error='INPUT_LIMIT');self.cli(out=True,code=2,error='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT');self.assertFalse(self.output.exists())

    def test_fixed_private_errors_read_mutations_and_output_budget_are_refused(self):
        self.invoke(['--input',self.work/'FICTIONAL_PRIVATE_MISSING.json'],code=2)
        self.cli(mode='short-read',code=2,error='INPUT_CHANGED');self.cli(mode='changed-stat',code=2,error='INPUT_CHANGED')
        self.cli(mode='output-budget',code=2,error='OUTPUT_LIMIT');self.assertFalse(self.output.exists())

    def test_retained_partial_report_is_not_confirmed_or_replaced(self):
        raw=self.input.read_bytes();want=expected(raw,selected())
        self.cli(out=True,mode='write-failure',code=2,error='INPUT_OR_OUTPUT_REFUSED',allow=[self.output]);self.assertEqual(self.output.read_bytes(),canonical(want)[:5])
        self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),canonical(want)[:5])

    def test_no_overwrite_and_standalone_collection_source_output_guards(self):
        self.output.write_bytes(b'Invented preserved report');self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),b'Invented preserved report')
        self.invoke(['--input',self.input,'--out',self.input],code=2)
        for target in (self.copy/'new.json',self.copy/'toolkit.py'):self.invoke(['--input',self.input,'--out',target],code=2,error='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE')
        collection=self.owned(self.work/'collection');chosen=collection/'tools/intake-mapping-diff';chosen.mkdir(parents=True);(collection/'systems').mkdir();(collection/'catalog').mkdir();(collection/'catalog/registry.json').write_bytes(b'{}\n')
        for name in RUNTIME:(chosen/name).write_bytes((self.copy/name).read_bytes())
        target=collection/'refused.json';self.invoke(['--input',self.input,'--out',target],base=chosen,code=2,error='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE');self.assertFalse(target.exists())

    def test_mandatory_hardlink_inputs_and_existing_outputs_are_refused(self):
        alias=self.owned(self.work/'input-hardlink.json');os.link(self.input,alias);self.assertTrue(alias.samefile(self.input))
        for source in (self.input,alias):self.invoke(['--input',source],code=2,error='CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE')
        alias.unlink();self.assertEqual(self.input.stat().st_nlink,1)
        original=self.owned(self.work/'old-report.json');original.write_bytes(b'Invented existing bytes');alias=self.owned(self.work/'report-hardlink.json');os.link(original,alias)
        self.assertTrue(alias.samefile(original));self.invoke(['--input',self.input,'--out',alias],code=2);self.assertEqual(original.read_bytes(),b'Invented existing bytes');self.assertEqual(alias.read_bytes(),original.read_bytes())

    def test_linked_parent_read_and_report_routes_are_refused(self):
        target=self.owned(self.work/'target');target.mkdir();(target/'input.json').write_bytes(canonical(selected()));route=self.owned(self.work/'route')
        if os.name=='nt':
            done=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(route),str(target)],capture_output=True,timeout=15);self.assertEqual(done.returncode,0,done.stderr.decode(errors='replace'));self.addCleanup(lambda:route.rmdir() if route.exists() else None)
        else:route.symlink_to(target,target_is_directory=True)
        self.invoke(['--input',route/'input.json'],code=2);self.invoke(['--input',self.input,'--out',route/'new.json'],code=2);self.assertFalse((target/'new.json').exists())

    def test_native_leaf_symlink_and_dangling_output_refusal(self):
        link=self.owned(self.work/'linked.json');self.symlink(link,self.input);self.invoke(['--input',link],code=2)
        for name,target in (('dangling',self.work/'never-created.json'),('source-pointing',self.copy/'never-created.json')):
            target=self.owned(target);self.assertFalse(os.path.lexists(target));route=self.owned(self.work/(name+'.json'));self.symlink(route,target);self.invoke(['--input',self.input,'--out',route],code=2)
            self.assertFalse(os.path.lexists(target),'Refused output must not create a symlink target');self.assertTrue(route.is_symlink())
        for name,target in (('input-pointing',self.input),('runtime-pointing',self.copy/'toolkit.py')):
            raw=target.read_bytes();route=self.owned(self.work/(name+'.json'));self.symlink(route,target);self.invoke(['--input',self.input,'--out',route],code=2);self.assertEqual(target.read_bytes(),raw)

    @unittest.skipUnless(os.name=='nt',WINDOWS_REASON)
    def test_native_windows_path_grammar_and_named_stream_routes(self):
        for path in (str(self.input)+':stream',str(self.work/'CON'),str(self.input)+'.',str(self.input)+' ','x:relative','//example.invalid/share'):self.invoke(['--input',path],code=2)
        self.invoke(['--input',self.input,'--out',str(self.output)+':stream'],code=2)

    @unittest.skipUnless(os.name!='nt',POSIX_REASON)
    def test_native_posix_special_inputs_and_private_report_mode(self):
        fifo=self.owned(self.work/'fictional.fifo');os.mkfifo(fifo);sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.owned(self.work/'s')));self.addCleanup(sock.close)
        for source in (fifo,self.work/'s',self.work):self.invoke(['--input',source],code=2)
        self.cli(out=True,allow=[self.output]);self.assertEqual(stat.S_IMODE(self.output.stat().st_mode),0o600)

    def test_path_like_headers_and_decimal_type_remain_unused_declarations(self):
        before=mapping([field('https://asset.example.invalid/not-opened','record_id'),field('//example.invalid/share/not-opened','units','decimal')]);after=copy.deepcopy(before);after['fields'][1]['type']='date'
        report=self.check(selected(before,after),[change('units','TYPE_CHANGED')])
        self.assertNotIn('example.invalid',json.dumps(report));self.assertIs(report['rows_validated'],False);self.assertIs(report['compatibility_verified'],False)
        self.assertEqual(self.invoke(mode='affinity')['unused_record_readers_forbidden'],True)


class TrackedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.started_ids=set();self.successful_ids=set()
    def startTest(self,test):self.started_ids.add(test.id());super().startTest(test)
    def addSuccess(self,test):self.successful_ids.add(test.id());super().addSuccess(test)


def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item


def load_copied_suite(strict=None):
    if strict is None:strict=os.name!="nt" or os.environ.get("OUTLANDS_INTAKE_MAPPING_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
    assert type(strict) is bool
    CopiedCLI.strict_links=os.name!="nt" or strict;CopiedCLI.native_events=[];CopiedCLI.checked_children=0
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CopiedCLI);ids=[test.id() for test in flatten(suite)]
    assert len(ids)==len(set(ids))==30 and all(name.startswith("test_copied_cli.CopiedCLI.test_") for name in ids)
    assert all(name in set(ids) for name,reason in REQUIRED_WINDOWS_SKIPS|REQUIRED_POSIX_SKIPS|OPTIONAL_WINDOWS_LINK_SKIPS)
    assert FLOW_IDS|COMMON_NATIVE_IDS<=set(ids)
    return suite


def run_copied_tests(strict=None,log_stream=None):
    suite=load_copied_suite(strict);strict=CopiedCLI.strict_links;ids=[test.id() for test in flatten(suite)]
    result=unittest.TextTestRunner(stream=log_stream if log_stream is not None else sys.stderr,verbosity=2,resultclass=TrackedResult).run(suite)
    skips=[dict(test=test.id(),reason=reason) for test,reason in result.skipped]
    required=REQUIRED_WINDOWS_SKIPS if os.name=="nt" else REQUIRED_POSIX_SKIPS;optional=OPTIONAL_WINDOWS_LINK_SKIPS if os.name=="nt" and not strict else set()
    observed={(row["test"],row["reason"]) for row in skips};unexpected=[row for row in skips if (row["test"],row["reason"]) not in required|optional]
    failed=sorted({getattr(test,"test_case",test).id() for test,trace in result.failures+result.errors});all_started=set(ids)<=result.started_ids;valid_successes=result.successful_ids<=result.started_ids&set(ids)
    good=result.wasSuccessful() and result.testsRun==30 and all_started and valid_successes and len(skips)==len(observed) and required<=observed<=required|optional
    native=COMMON_NATIVE_IDS|{WINDOWS_ID if os.name=="nt" else POSIX_ID};flow_checked=good and FLOW_IDS<=result.successful_ids;native_checked=good and native<=result.successful_ids
    return dict(schema=1,status="PASS" if good and flow_checked and native_checked else "FAIL",tests=result.testsRun,selected_tests=30,
        passed=len(result.successful_ids),skipped=len(skips),failures=len(result.failures),errors=len(result.errors),skips=skips,unexpected_skips=unexpected,
        missing_required_skips=[dict(test=name,reason=reason) for name,reason in sorted(required-observed)],failed_tests=failed,test_ids=ids,started_test_ids=sorted(result.started_ids),successful_test_ids=sorted(result.successful_ids),
        all_selected_tests_started=all_started,successful_ids_exclude_setup_failures=valid_successes,module_counts={"test_copied_cli":30},native_links_required=strict,native_fixture_events=CopiedCLI.native_events,
        fictional_intake_mapping_flow_checked=flow_checked,native_file_guards_checked=native_checked,fictional_intake_mapping_flow_test_ids=sorted(FLOW_IDS),native_file_guard_test_ids=sorted(native),
        positive_asserted_test_ids=dict(fictional_intake_mapping_flow_checked=sorted(FLOW_IDS),native_file_guards_checked=sorted(native)),child_xml_bindings_verified=good and flow_checked and native_checked and CopiedCLI.checked_children>0,xml_binding_checked_children=CopiedCLI.checked_children,
        copied_declaration_reader_only=True,copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,
        **{name:False for name in FALSE_FLAGS})


if __name__=="__main__":raise SystemExit(0 if run_copied_tests()["status"]=="PASS" else 1)
