"""Independent copied batch-declaration planning consumers; no retries, imports or execution. MIT."""
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
RUNTIME=("replay.py","control_core.py","toolkit.py","native_windows.py")
FALSE_FLAGS=("real_records_used","real_workbooks_used","imported","retry_performed","execution_authorized","target_changes_performed",
             "row_counts_recomputed","receipt_authority_verified","exactly_once_verified","production_workflows_verified")
FLOW_IDS={"test_copied_cli.CopiedCLI.test_complete_skip_and_manual_advice_report_and_fresh_output",
          "test_copied_cli.CopiedCLI.test_missing_receipts_are_manual_advice_without_execution_authority",
          "test_copied_cli.CopiedCLI.test_unrelated_failed_or_uncertain_supplied_history_holds_entire_plan"}
COMMON_NATIVE_IDS={"test_copied_cli.CopiedCLI.test_no_overwrite_and_standalone_collection_source_output_guards",
                   "test_copied_cli.CopiedCLI.test_retained_partial_report_is_not_confirmed_or_replaced",
                   "test_copied_cli.CopiedCLI.test_mandatory_hardlink_inputs_and_existing_outputs_are_refused",
                   "test_copied_cli.CopiedCLI.test_linked_parent_read_and_report_routes_are_refused"}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return (json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(",",":"))+"\n").encode()


def count(n,a,d=0,r=0,c=0):
    assert n==a+d+r+c
    return dict(input_rows=n,accepted_records=a,duplicate_rows=d,rejected_rows=r,conflict_rows=c)


def batch(key='batch-a',sequence=1,counts=None):
    return dict(id=key,sequence=sequence,source_sha256=sha(('source:'+key).encode()),mapping_sha256=sha(b'fictional-map'),preview_sha256=sha(('preview:'+key).encode()),counts=count(3,2,1) if counts is None else counts)


def receipt(value=None,status='committed',stream='fictional-stream',rid=None):
    value=batch() if value is None else copy.deepcopy(value)
    return dict(receipt_id='receipt-'+value['id'] if rid is None else rid,stream=stream,batch=value,status=status,receipt_sha256=sha(('receipt:'+value['id']).encode()))


def selected(expected=None,receipts=None,stream='fictional-stream'):
    return dict(format='outlands-batch-replay-v1',stream=stream,expected=[batch(),batch('batch-b',2)] if expected is None else copy.deepcopy(expected),receipts=[receipt()] if receipts is None else copy.deepcopy(receipts))


def issue(side,row,code):return dict(side=side,row=row,code=code)


def decision(key,sequence,advice):return dict(id=key,sequence=sequence,decision=advice,execution_authorized=False)


def sample_plan():return [decision('batch-a',1,'SKIP_ALREADY_COMMITTED'),decision('batch-b',2,'MANUAL_REVIEW_NEW_BATCH')]


def expected(raw,ecount,rcount,issues,plan):
    # Counts, issue positions/codes and every advice row are authored by each case.
    assert bool(issues)==(plan is None)
    return dict(format='outlands-batch-replay-plan-v1',status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=sha(raw),
        counts=dict(expected=ecount,receipts=rcount),issues=sorted(issues,key=lambda row:(row['side'],row['row'],row['code'])),
        row_counts_recomputed=False,receipt_authority_verified=False,exactly_once_verified=False,target_changes_performed=False,
        plan=plan,plan_only=True,retry_performed=False,execution_authorized=False)


CHILD=r'''
import _elementtree,hashlib,importlib.metadata,json,os,pyexpat,runpy,sys
from pathlib import Path
from types import SimpleNamespace
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();mode=sys.argv[2];args=sys.argv[3:];sys.path.insert(0,str(base))
def audit(event,values):
 if event.startswith(('socket.','subprocess.','os.startfile','sqlite3.')) or event in ('os.system','webbrowser.open'):
  raise AssertionError('UNEXPECTED_NETWORK_RETRY_IMPORT_OR_PROCESS')
sys.addaudithook(audit)
import replay as a
import control_core as c
import toolkit as t
import native_windows as n
for module,name in ((a,'replay.py'),(c,'control_core.py'),(t,'toolkit.py'),(n,'native_windows.py')):assert Path(module.__file__).resolve()==base/name
assert a.t is c.t is t and a.c is c
assert a.plan.__globals__ is a.__dict__ and c.prepare.__globals__ is c.rows.__globals__ is c.report.__globals__ is c.__dict__
assert t.read.__globals__ is t.__dict__ and t.write_new.__globals__ is t.__dict__
def unused(*a,**kw):raise AssertionError('PLANNER_CALLED_UNUSED_XML_OR_RECONCILER')
t.xml=unused;c.reconcile=unused
def bindings():
 assert t.ET.XMLParser is _elementtree.XMLParser and t.ET.TreeBuilder is _elementtree.TreeBuilder and t.XMLBuilder.__mro__[1] is _elementtree.TreeBuilder
 return (t.ET.XMLParser,t.ET.TreeBuilder,t.XMLBuilder.__mro__[1],pyexpat.EXPAT_VERSION)
initial=bindings()
try:
 if mode=='affinity':sys.stdout.write(t.encode(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=4,planning_only=True)).decode());raise SystemExit(0)
 if mode=='api':
  path=Path(args[0]);assert path.is_absolute()
  try:value=a.plan(path.read_bytes())
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
 sys.argv=[str(base/'replay.py'),*args];runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('PLANNER_ENTRYPOINT_DID_NOT_EXIT')
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
        self.temp=tempfile.TemporaryDirectory(prefix="batch-replay-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.assertEqual(self.work.parent,parent);self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();(self.copy/name).write_bytes(raw);self.pins[name]=sha(raw)
        self.input=self.work/"batches.json";self.input.write_bytes(canonical(selected()));self.output=self.work/"report.json"
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
        elif value.get("format")=="outlands-batch-replay-plan-v1":
            self.assertEqual(value["input_sha256"],sha(self.input.read_bytes()));self.assertIs(value["plan_only"],True)
            for key in ("retry_performed","execution_authorized","target_changes_performed","row_counts_recomputed","receipt_authority_verified","exactly_once_verified"):self.assertIs(value[key],False)
            for side in ("expected","receipts"):
                counts=value["counts"][side];self.assertEqual(counts["input_rows"],sum(counts[key] for key in ("accepted_records","duplicate_rows","rejected_rows","conflict_rows")))
            if value["plan"] is not None:self.assertTrue(all(row["execution_authorized"] is False for row in value["plan"]))
        return value
    def cli(self,*,out=False,**kwargs):return self.invoke(["--input",self.input,*(["--out",self.output] if out else [])],**kwargs)
    def api(self,**kwargs):return self.invoke([self.input],mode="api",**kwargs)
    def check(self,value,ecount,rcount,issues=(),plan=None,raw=None,api=True):
        raw=canonical(value) if raw is None else raw;self.write(raw);want=expected(raw,ecount,rcount,issues,plan);code=1 if issues else 0
        self.assertEqual(self.cli(code=code),want)
        if api:self.assertEqual(self.api(code=code),want)
        return want
    def refused(self,raw,code=None):
        self.write(raw);self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            strict=self.strict_links if self.strict_links is not None else os.name!="nt" or os.environ.get("OUTLANDS_BATCH_REPLAY_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
            actual=os.name=="nt" and getattr(error,"winerror",None)==1314
            if actual and not strict:
                self.assertEqual(self.id(),LINK_ID);self.assertFalse(directory);self.native_events.append(dict(test=self.id(),reason=LINK_REASON,policy="actual_windows_1314",actual_windows_1314=True,winerror=1314,strict=False,provenance="test_copied_cli.CopiedCLI.symlink/caught-OSError"));self.skipTest(LINK_REASON)
            raise

    def test_copied_affinity_and_actual_entrypoint_help_are_inert(self):
        self.assertEqual(self.invoke(mode='affinity'),dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=4,planning_only=True))
        self.assertIn('--input',self.invoke(['--help'],text=True));self.assertIn('--out',self.invoke(['--help'],text=True))
        self.invoke(code=2,error='ARGUMENTS_INVALID');self.invoke(['--unknown','FICTIONAL_PRIVATE_SENTINEL'],code=2,error='ARGUMENTS_INVALID')

    def test_complete_skip_and_manual_advice_report_and_fresh_output(self):
        report=self.check(selected(),count(2,2),count(1,1),plan=sample_plan())
        self.assertEqual(self.cli(out=True,allow=[self.output]),dict(status='PASS',report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))
        self.assertIs(report['plan_only'],True);self.assertIs(report['execution_authorized'],False)

    def test_missing_receipts_are_manual_advice_without_execution_authority(self):
        advice=[decision('batch-a',1,'MANUAL_REVIEW_NEW_BATCH'),decision('batch-b',2,'MANUAL_REVIEW_NEW_BATCH')]
        report=self.check(selected(receipts=[]),count(2,2),count(0,0),plan=advice)
        self.assertEqual(report['status'],'PASS');self.assertTrue(all(row['execution_authorized'] is False for row in report['plan']))
        self.assertIs(report['retry_performed'],False)

    def test_healthy_unrelated_committed_history_is_allowed_without_extra_advice(self):
        value=selected(receipts=[receipt(),receipt(batch('history',10))]);self.check(value,count(2,2),count(2,2),plan=sample_plan())
        value=selected([batch()],[receipt(batch('history',10))]);self.check(value,count(1,1),count(1,1),plan=[decision('batch-a',1,'MANUAL_REVIEW_NEW_BATCH')])

    def test_unrelated_failed_or_uncertain_supplied_history_holds_entire_plan(self):
        for status in ('failed','uncertain'):
            value=selected(receipts=[receipt(),receipt(batch('history',10),status)])
            self.check(value,count(2,2),count(2,2),[issue('receipts',2,'HISTORY_'+status.upper())])
            self.check(selected(receipts=[receipt(status=status)]),count(2,2),count(1,1),[issue('receipts',1,'HISTORY_'+status.upper())])

    def test_unclean_declared_source_counts_block_candidates_and_supplied_history(self):
        for embedded in (count(3,1,1,1),count(3,1,1,0,1),count(3,0,3),count(0,0)):
            bad=batch(counts=embedded)
            self.check(selected([bad,batch('batch-b',2)],[receipt(bad)]),count(2,2),count(1,1),[issue('expected',1,'BATCH_COUNTS_REQUIRE_REVIEW'),issue('receipts',1,'RECEIPT_COUNTS_REQUIRE_REVIEW')])
            history=batch('history',10,embedded)
            self.check(selected(receipts=[receipt(),receipt(history)]),count(2,2),count(2,2),[issue('receipts',2,'RECEIPT_COUNTS_REQUIRE_REVIEW')])

    def test_identical_duplicate_snapshots_collapse_once_with_complete_list_accounting(self):
        a=batch();b=batch('batch-b',2);ra=receipt(a)
        report=self.check(selected([a,a,b],[ra,ra]),count(3,2,1),count(2,1,1),plan=sample_plan())
        self.assertEqual(len(report['plan']),2);self.assertEqual(report['issues'],[])

    def test_conflicting_candidate_group_withholds_every_member_including_repeats(self):
        a=batch();altered=dict(a,sequence=99);b=batch('batch-b',2)
        self.check(selected([a,a,altered,b],[]),count(4,1,c=3),count(0,0),[issue('expected',i,'IDENTITY_CONFLICT') for i in (1,2,3)])

    def test_conflicting_receipt_snapshots_withhold_all_without_latest_status_choice(self):
        original=receipt();changed=copy.deepcopy(original);changed['status']='uncertain'
        self.check(selected(receipts=[original,original,changed]),count(2,2),count(3,0,c=3),[issue('receipts',i,'IDENTITY_CONFLICT') for i in (1,2,3)])
        for attribute,value in (('receipt_id','other-receipt'),('receipt_sha256','0'*64)):
            changed=copy.deepcopy(original);changed[attribute]=value
            self.check(selected(receipts=[original,changed]),count(2,2),count(2,0,c=2),[issue('receipts',i,'IDENTITY_CONFLICT') for i in (1,2)])

    def test_malformed_rows_in_either_list_hold_otherwise_supported_decisions(self):
        self.check(selected([None,batch()],[receipt()]),count(2,1,r=1),count(1,1),[issue('expected',1,'FIELDS_INVALID')])
        self.check(selected([batch()],[None,receipt()]),count(1,1),count(2,1,r=1),[issue('receipts',1,'FIELDS_INVALID')])
        extra=dict(batch('batch-b',2),private='FICTIONAL_PRIVATE_REJECTED_ROW')
        result=self.check(selected([batch(),extra],[receipt()]),count(2,1,r=1),count(1,1),[issue('expected',2,'FIELDS_INVALID')])
        self.assertNotIn('FICTIONAL_PRIVATE_REJECTED_ROW',json.dumps(result))

    def test_wrong_stream_on_selected_or_unrelated_receipts_holds_whole_plan(self):
        self.check(selected(receipts=[receipt(stream='other-stream')]),count(2,2),count(1,1),[issue('receipts',1,'STREAM_MISMATCH')])
        self.check(selected(receipts=[receipt(),receipt(batch('history',10),stream='other-stream')]),count(2,2),count(2,2),[issue('receipts',2,'STREAM_MISMATCH')])

    def test_matching_id_requires_exact_sequence_fingerprints_and_declared_counts(self):
        for key,new in (('sequence',99),('source_sha256','0'*64),('mapping_sha256','0'*64),('preview_sha256','0'*64),('counts',count(3,1,2))):
            changed=batch();changed[key]=new
            self.check(selected([batch()],[receipt(changed)]),count(1,1),count(1,1),[issue('receipts',1,'BATCH_METADATA_MISMATCH')])

    def test_sequence_aliases_span_candidate_and_receipt_declarations(self):
        a=batch();b=batch('batch-b',1)
        self.check(selected([a,b],[]),count(2,2),count(0,0),[issue('expected',1,'SEQUENCE_ALIAS'),issue('expected',2,'SEQUENCE_ALIAS')])
        self.check(selected([a],[receipt(batch('history',1))]),count(1,1),count(1,1),[issue('expected',1,'SEQUENCE_ALIAS'),issue('receipts',1,'SEQUENCE_ALIAS')])
        self.check(selected([a],[receipt(a)]),count(1,1),count(1,1),plan=[decision('batch-a',1,'SKIP_ALREADY_COMMITTED')])

    def test_complete_content_fingerprint_aliases_span_different_ids_in_both_lists(self):
        a=batch();b=batch('batch-b',2)
        for key in ('source_sha256','mapping_sha256','preview_sha256'):b[key]=a[key]
        self.check(selected([a,b],[]),count(2,2),count(0,0),[issue('expected',1,'CONTENT_ID_ALIAS'),issue('expected',2,'CONTENT_ID_ALIAS')])
        renamed=dict(b,id='history',sequence=3)
        self.check(selected([a],[receipt(renamed)]),count(1,1),count(1,1),[issue('expected',1,'CONTENT_ID_ALIAS'),issue('receipts',1,'CONTENT_ID_ALIAS')])

    def test_receipt_identifier_aliases_between_batch_ids_are_not_merged(self):
        a=batch();b=batch('batch-b',2)
        self.check(selected([a,b],[receipt(a,rid='shared-receipt'),receipt(b,rid='shared-receipt')]),count(2,2),count(2,2),[issue('receipts',1,'RECEIPT_ID_ALIAS'),issue('receipts',2,'RECEIPT_ID_ALIAS')])

    def test_empty_or_fully_withheld_candidate_cohorts_never_produce_a_plan(self):
        self.check(selected([],[]),count(0,0),count(0,0),[issue('expected',0,'EMPTY_BATCH_COHORT')])
        self.check(selected([],[receipt()]),count(0,0),count(1,1),[issue('expected',0,'EMPTY_BATCH_COHORT')])
        self.check(selected([None],[]),count(1,0,r=1),count(0,0),[issue('expected',0,'EMPTY_BATCH_COHORT'),issue('expected',1,'FIELDS_INVALID')])
        a=batch();self.check(selected([a,dict(a,sequence=99)],[]),count(2,0,c=2),count(0,0),[issue('expected',0,'EMPTY_BATCH_COHORT'),issue('expected',1,'IDENTITY_CONFLICT'),issue('expected',2,'IDENTITY_CONFLICT')])

    def test_changed_mapping_under_new_batch_id_is_manual_advice_not_retry_permission(self):
        candidate=dict(batch(),id='changed',sequence=3,mapping_sha256='0'*64)
        result=self.check(selected([candidate],[receipt()]),count(1,1),count(1,1),plan=[decision('changed',3,'MANUAL_REVIEW_NEW_BATCH')])
        self.assertIs(result['retry_performed'],False);self.assertIs(result['execution_authorized'],False);self.assertIs(result['exactly_once_verified'],False)

    def test_typed_row_bounds_and_declared_accounting_rejections_are_exact(self):
        variants=[]
        for key,value,code in (('id','Bad ID','IDENTIFIER_INVALID'),('sequence',True,'INTEGER_INVALID'),('sequence',0,'INTEGER_INVALID'),('sequence',1000000001,'INTEGER_INVALID'),('source_sha256','A'*64,'HASH_INVALID'),('mapping_sha256','short','HASH_INVALID')):
            bad=batch('batch-b',2);bad[key]=value;variants.append((bad,code))
        bad=batch('batch-b',2);bad['counts']['input_rows']=True;variants.append((bad,'INTEGER_INVALID'))
        bad=batch('batch-b',2);bad['counts']['input_rows']=4;variants.append((bad,'DECLARED_ACCOUNTING_MISMATCH'))
        bad=batch('batch-b',2);bad['counts']['accepted_records']=-1;variants.append((bad,'INTEGER_INVALID'))
        bad=batch('batch-b',2);bad['counts']['extra']=0;variants.append((bad,'FIELDS_INVALID'))
        for bad,code in variants:self.check(selected([batch(),bad],[receipt()]),count(2,1,r=1),count(1,1),[issue('expected',2,code)])
        for key,value,code in (('status','pending','RECEIPT_STATUS_INVALID'),('receipt_id','Bad ID','IDENTIFIER_INVALID'),('stream','Bad Stream','IDENTIFIER_INVALID'),('receipt_sha256','x'*64,'HASH_INVALID'),('batch',{},'FIELDS_INVALID')):
            bad=receipt(batch('history',10));bad[key]=value
            self.check(selected([batch()],[receipt(),bad]),count(1,1),count(2,1,r=1),[issue('receipts',2,code)])
        key='a'*48;value=batch(key,1000000000,count(1000,1000));self.check(selected([value],[]),count(1,1),count(0,0),plan=[decision(key,1000000000,'MANUAL_REVIEW_NEW_BATCH')])

    def test_exact_thousand_unique_candidates_and_receipts_and_one_over_limits(self):
        batches=[batch('batch-'+str(i).zfill(4),i) for i in range(1,1001)];receipts=[receipt(value) for value in batches]
        plan=[decision(value['id'],value['sequence'],'SKIP_ALREADY_COMMITTED') for value in batches]
        self.check(selected(batches,receipts),count(1000,1000),count(1000,1000),plan=plan,api=False)
        self.check(selected(batches,[]),count(1000,1000),count(0,0),plan=[decision(value['id'],value['sequence'],'MANUAL_REVIEW_NEW_BATCH') for value in batches],api=False)
        self.refused(canonical(selected(batches+[batch('extra',1001)],[])),'ROW_LIMIT')
        self.refused(canonical(selected(batches,receipts+[receipt(batch('extra',1001))])),'ROW_LIMIT')

    def test_outer_schema_json_caps_and_explicit_stream_contract_refuse(self):
        for value,code in ((None,'FIELDS_INVALID'),([], 'FIELDS_INVALID'),({},'FIELDS_INVALID'),(dict(selected(),extra='FICTIONAL_PRIVATE_OUTER'),'FIELDS_INVALID'),(dict(selected(),format='wrong'),'FORMAT_INVALID'),(selected(stream='Bad Stream'),'IDENTIFIER_INVALID'),(selected(expected={}), 'ROW_LIMIT'),(selected(receipts={}), 'ROW_LIMIT')):self.refused(canonical(value),code)
        for raw,code in ((b'{"format":1,"format":2}','JSON_DUPLICATE_KEY'),(b'1.0','JSON_INTEGER_OR_STRING_REQUIRED'),(b'NaN','JSON_INTEGER_OR_STRING_REQUIRED'),(b'1000000000000000001','JSON_INTEGER_LIMIT'),(b'"\\ud800"','JSON_INVALID'),(b'\xff','JSON_INVALID'),(b'['*34+b'0'+b']'*34,'JSON_STRUCTURE_LIMIT'),(b'['+b'0,'*100000+b'0]','JSON_STRUCTURE_LIMIT'),(canonical(dict(value='x'*4097)),'JSON_TEXT_LIMIT')):self.refused(raw,code)

    def test_raw_pin_order_invariance_bom_and_four_mebibyte_input_boundary(self):
        value=selected();baseline=self.check(value,count(2,2),count(1,1),plan=sample_plan())
        value['expected'].reverse();value=dict(reversed(list(value.items())));raw=b'\xef\xbb\xbf'+json.dumps(value,indent=2).encode()+b'\n'
        changed=self.check(value,count(2,2),count(1,1),plan=sample_plan(),raw=raw)
        self.assertNotEqual(changed['input_sha256'],baseline['input_sha256']);self.assertEqual({k:v for k,v in changed.items() if k!='input_sha256'},{k:v for k,v in baseline.items() if k!='input_sha256'})
        value=selected();raw=canonical(value);raw+=b' '*(4194304-len(raw));self.assertEqual(len(raw),4194304);self.check(value,count(2,2),count(1,1),plan=sample_plan(),raw=raw)
        self.write(raw+b' ');self.api(code=2,error='INPUT_LIMIT');self.cli(out=True,code=2,error='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT');self.assertFalse(self.output.exists())

    def test_fixed_private_errors_read_mutations_and_output_budget_are_refused(self):
        self.invoke(['--input',self.work/'FICTIONAL_PRIVATE_MISSING.json'],code=2)
        self.cli(mode='short-read',code=2,error='INPUT_CHANGED');self.cli(mode='changed-stat',code=2,error='INPUT_CHANGED');self.cli(mode='output-budget',code=2,error='OUTPUT_LIMIT');self.assertFalse(self.output.exists())

    def test_retained_partial_report_is_not_confirmed_or_replaced(self):
        raw=self.input.read_bytes();want=expected(raw,count(2,2),count(1,1),[],sample_plan())
        self.cli(out=True,mode='write-failure',code=2,error='INPUT_OR_OUTPUT_REFUSED',allow=[self.output]);self.assertEqual(self.output.read_bytes(),canonical(want)[:5])
        self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),canonical(want)[:5])

    def test_no_overwrite_and_standalone_collection_source_output_guards(self):
        self.output.write_bytes(b'Invented preserved report');self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),b'Invented preserved report')
        self.invoke(['--input',self.input,'--out',self.input],code=2)
        for target in (self.copy/'new.json',self.copy/'toolkit.py'):self.invoke(['--input',self.input,'--out',target],code=2,error='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE')
        collection=self.owned(self.work/'collection');chosen=collection/'tools/batch-replay-planner';chosen.mkdir(parents=True);(collection/'systems').mkdir();(collection/'catalog').mkdir();(collection/'catalog/registry.json').write_bytes(b'{}\n')
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



    def test_declared_source_counts_and_pins_are_not_loaded_or_authenticated(self):
        advice=[decision('batch-a',1,'MANUAL_REVIEW_NEW_BATCH')]
        a=self.check(selected([batch(counts=count(1,1))],[]),count(1,1),count(0,0),plan=advice)
        b=self.check(selected([batch(counts=count(1000,1000))],[]),count(1,1),count(0,0),plan=advice)
        self.assertEqual({k:v for k,v in a.items() if k!='input_sha256'},{k:v for k,v in b.items() if k!='input_sha256'})
        value=batch();value.update(source_sha256='0'*64,mapping_sha256='1'*64,preview_sha256='2'*64)
        result=self.check(selected([value],[]),count(1,1),count(0,0),plan=advice)
        for key in ('source_sha256','mapping_sha256','preview_sha256'):self.assertNotIn(value[key],json.dumps(result))
        self.assertIs(result['row_counts_recomputed'],False);self.assertIs(result['receipt_authority_verified'],False);self.assertIs(result['exactly_once_verified'],False)


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
    if strict is None:strict=os.name!="nt" or os.environ.get("OUTLANDS_BATCH_REPLAY_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
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
        fictional_batch_replay_flow_checked=flow_checked,native_file_guards_checked=native_checked,fictional_batch_replay_flow_test_ids=sorted(FLOW_IDS),native_file_guard_test_ids=sorted(native),
        positive_asserted_test_ids=dict(fictional_batch_replay_flow_checked=sorted(FLOW_IDS),native_file_guards_checked=sorted(native)),child_xml_bindings_verified=good and flow_checked and native_checked and CopiedCLI.checked_children>0,xml_binding_checked_children=CopiedCLI.checked_children,
        copied_planning_only=True,copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,
        **{name:False for name in FALSE_FLAGS})


if __name__=="__main__":raise SystemExit(0 if run_copied_tests()["status"]=="PASS" else 1)
