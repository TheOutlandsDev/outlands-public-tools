"""Independent copied reconciliation consumers on authored JSON; no real records, SQL or sources. MIT."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=("reconcile.py","toolkit.py","native_windows.py")
WINDOWS_ID="test_copied_cli.CopiedCLI.test_native_windows_path_grammar_and_named_stream_routes"
WINDOWS_REASON="Native Windows path-grammar fixtures"
POSIX_ID="test_copied_cli.CopiedCLI.test_native_posix_special_inputs_and_private_report_mode"
POSIX_REASON="Native POSIX special-file and mode fixtures"
LINK_ID="test_copied_cli.CopiedCLI.test_native_leaf_symlink_and_dangling_output_refusal"
LINK_REASON="Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS={(POSIX_ID,POSIX_REASON)}
REQUIRED_POSIX_SKIPS={(WINDOWS_ID,WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS={(LINK_ID,LINK_REASON)}
FALSE_FLAGS=("real_records_used","external_systems_accessed","external_system_writes","sql_queries_executed","input_sources_modified",
             "source_completeness_verified","business_meaning_verified","unit_conversion_performed","production_workflows_verified")
FLOW_IDS={"test_copied_cli.CopiedCLI.test_equal_totals_do_not_hide_three_authored_record_differences",
          "test_copied_cli.CopiedCLI.test_default_identity_disclosure_and_explicit_values_are_distinct",
          "test_copied_cli.CopiedCLI.test_any_conflict_globally_holds_changes_unchanged_and_totals"}
COMMON_NATIVE_IDS={"test_copied_cli.CopiedCLI.test_no_overwrite_three_input_aliases_and_source_output_protection",
                   "test_copied_cli.CopiedCLI.test_retained_partial_output_is_unconfirmed_and_never_reused",
                   "test_copied_cli.CopiedCLI.test_each_input_role_requires_single_link_without_masking",
                   "test_copied_cli.CopiedCLI.test_linked_parents_of_all_three_inputs_and_output_refuse"}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return (json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(",",":"))+"\n").encode()


def field(name,kind="text",nullable=False):return dict(name=name,type=kind,nullable=nullable)


def contract(fields=None,identity=None,totals=None):
    if fields is None:fields=[field("record_id"),field("units","integer"),field("due","date"),field("active","boolean")]
    return dict(format="outlands-reconciliation-contract-v1",identity=[fields[0]["name"]] if identity is None else identity,
                fields=fields,totals=["units"] if totals is None else totals)


def record(key,units=12,due="2030-01-10",active=True):return dict(record_id=key,units=units,due=due,active=active)


def sample_before():return [record("sample-a"),record("sample-b",7,"2030-01-11",False)]


def sample_after():return [record("sample-a",14),record("sample-c",5,"2030-01-12")]


def record_set(records):return dict(format="outlands-record-set-v1",records=records)


def counts(rows,accepted,duplicates=0,rejected=0,conflicts=0):
    assert rows==accepted+duplicates+rejected+conflicts
    return dict(input_rows=rows,accepted_records=accepted,duplicate_rows=duplicates,rejected_rows=rejected,conflict_rows=conflicts)


def change(identity,old,new,classification,fields,show=False):
    row=dict(identity=identity,classification=classification,changed_fields=fields,
             before_sha256=sha(canonical(old)) if old is not None else None,after_sha256=sha(canonical(new)) if new is not None else None)
    if show:row.update(before=old,after=new)
    return row


def expected(before,after,selected,status,before_count,after_count,changes,unchanged,totals,issues=(),show=False):
    return dict(format="outlands-reconciliation-v1",status=status,before_sha256=sha(before),after_sha256=sha(after),contract_sha256=sha(selected),
                before_counts=before_count,after_counts=after_count,changes=changes,unchanged_records=unchanged,totals=totals,issues=list(issues),
                values_included=show,external_system_writes=False)


CHILD=r'''
import _decimal,decimal,hashlib,importlib.metadata,json,os,runpy,sys
from pathlib import Path
from types import SimpleNamespace
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
assert decimal.Decimal is _decimal.Decimal and decimal.Context is _decimal.Context
def arithmetic_context():
 c=decimal.getcontext()
 return (c.prec,c.rounding,c.Emin,c.Emax,c.capitals,c.clamp,tuple(sorted((k.__name__,v) for k,v in c.traps.items())),tuple(sorted((k.__name__,v) for k,v in c.flags.items())))
arithmetic_before=arithmetic_context()
assert arithmetic_before[:6]==(28,'ROUND_HALF_EVEN',-999999,999999,1,0) and not any(decimal.getcontext().flags.values())
assert {key.__name__ for key,value in decimal.getcontext().traps.items() if value}=={'InvalidOperation','DivisionByZero','Overflow'}
base=Path(sys.argv[1]).resolve();mode=sys.argv[2];args=sys.argv[3:];sys.path.insert(0,str(base))
def audit(event,values):
 if event.startswith(('socket.','subprocess.','os.startfile','sqlite3.')) or event in ('os.system','webbrowser.open'):
  raise AssertionError('UNEXPECTED_NETWORK_SQL_OR_PROCESS')
sys.addaudithook(audit)
import reconcile as a
import toolkit as t
import native_windows as n
for module,name in ((a,'reconcile.py'),(t,'toolkit.py'),(n,'native_windows.py')):assert Path(module.__file__).resolve()==base/name
assert a.t is t and a.Decimal is decimal.Decimal and a.compare.__globals__ is a.__dict__
assert t.read.__globals__ is t.__dict__ and t.write_new.__globals__ is t.__dict__
def no_xml(*a,**kw):raise AssertionError('JSON_RECONCILIATION_CALLED_XML_READER')
t.xml=no_xml
if mode=='affinity':
 assert arithmetic_context()==arithmetic_before,'ARITHMETIC_CONTEXT_CHANGED'
 sys.stdout.write(t.encode(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=3)).decode());raise SystemExit(0)
if mode=='api':
 paths=[Path(value) for value in args[:3]];assert all(path.is_absolute() for path in paths)
 try:
  try:value=a.compare(*(path.read_bytes() for path in paths),json.loads(args[3]))
  except t.Rejected as error:sys.stdout.write(t.encode(dict(status='ERROR',code=str(error))).decode());raise SystemExit(2)
  sys.stdout.write(t.encode(value).decode());raise SystemExit(0 if value['status']=='MATCH' else 1)
 finally:assert arithmetic_context()==arithmetic_before,'ARITHMETIC_CONTEXT_CHANGED'
if mode.startswith(('short-','changed-')):
 role=mode.split('-',1)[1];assert role in ('before','after','contract')
 original_read=os.read;original_stat=os.fstat;changed=set();inode=os.stat(args[args.index('--'+role)+1]).st_ino
 def selected(fd):return original_stat(fd).st_ino==inode
 def read(fd,*values):
  if selected(fd) and mode.startswith('short-'):return b''
  raw=original_read(fd,*values)
  if raw and selected(fd):changed.add(fd)
  return raw
 def info(fd):
  value=original_stat(fd)
  if fd not in changed:return value
  fields={name:getattr(value,name) for name in dir(value) if name.startswith('st_')};fields['st_mtime_ns']+=1
  return SimpleNamespace(**fields)
 os.read=read
 if mode.startswith('changed-'):os.fstat=info
elif mode=='write-failure':
 original_write=os.write;written=False
 def write(fd,data):
  global written
  if written:raise OSError('FICTIONAL_PRIVATE_WRITE_FAILURE')
  written=True;return original_write(fd,data[:5])
 os.write=write
elif mode=='output-budget':t.MAX_OUTPUT=1
elif mode!='normal':raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
sys.argv=[str(base/'reconcile.py'),*args]
try:runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('RECONCILIATION_ENTRYPOINT_DID_NOT_EXIT')
finally:assert arithmetic_context()==arithmetic_before,'ARITHMETIC_CONTEXT_CHANGED'
'''


class CopiedCLI(unittest.TestCase):
    strict_links=None
    native_events=[]
    @classmethod
    def setUpClass(cls):
        cls.python_binary=Path(sys._base_executable).resolve();cls.python_pin=sha(cls.python_binary.read_bytes());cls.python_bytes=cls.python_binary.stat().st_size
        cls.python_version=".".join(map(str,sys.version_info[:3]))
        if cls.python_pin!=os.environ["OUTLANDS_TEST_PYTHON_SHA256"] or cls.python_version!=os.environ["OUTLANDS_TEST_PYTHON_VERSION"]:raise AssertionError("EXPECTED_PYTHON_BINARY_OR_VERSION_DIFFERS")
    @classmethod
    def tearDownClass(cls):
        if sha(cls.python_binary.read_bytes())!=cls.python_pin or cls.python_binary.stat().st_size!=cls.python_bytes:raise AssertionError("PYTHON_BINARY_CHANGED")
    def setUp(self):
        self.assertNotEqual(sys.prefix,sys.base_prefix);self.assertEqual(list(importlib.metadata.distributions()),[])
        parent=Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or tempfile.gettempdir());self.assertTrue(parent.is_absolute() and parent.is_dir());parent=parent.resolve(strict=True)
        self.temp=tempfile.TemporaryDirectory(prefix="reconciliation-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.assertEqual(self.work.parent,parent);self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();(self.copy/name).write_bytes(raw);self.pins[name]=sha(raw)
        self.paths={role:self.work/(role+".json") for role in ("before","after","contract")};self.output=self.work/"report.json"
        self.paths["before"].write_bytes(canonical(record_set(sample_before())));self.paths["after"].write_bytes(canonical(record_set(sample_after())));self.paths["contract"].write_bytes(canonical(contract()))
        self.env={key:value for key,value in os.environ.items() if not key.upper().startswith(("PYTHON","PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHON_COLORS="0",NO_COLOR="1");self.addCleanup(self.runtime_preserved)
    def runtime_preserved(self):
        self.assertEqual({p.name for p in self.copy.iterdir()},set(RUNTIME));self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME},self.pins);self.assertEqual(list(self.work.rglob("*.pyc")),[])
    def owned(self,path):
        path=Path(path);self.assertTrue(path.is_absolute() and path.resolve().is_relative_to(self.work));return path
    def fixture(self,before,after,selected=None):
        self.paths["before"].write_bytes(canonical(record_set(before)));self.paths["after"].write_bytes(canonical(record_set(after)))
        if selected is not None:self.paths["contract"].write_bytes(canonical(selected))
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
        before=self.snapshot();done=subprocess.run([sys.executable,"-I","-B","-W","error","-c",CHILD,str(self.copy if base is None else base),mode,*map(str,args)],cwd=self.work,env=self.env,stdin=subprocess.DEVNULL,capture_output=True,timeout=60)
        self.assertEqual(done.returncode,code,done.stderr.decode(errors="replace")[:3000]);self.assertEqual(done.stderr,b"")
        for private in (str(self.work).encode(),b"FICTIONAL_PRIVATE",b"Traceback"):self.assertNotIn(private,done.stdout)
        after=self.snapshot();self.assertEqual(before,{key:after.get(key) for key in before});allowed={self.owned(path).relative_to(self.work).as_posix() for path in allow}
        self.assertEqual(sorted(after.keys()-before.keys()-allowed),[],"Unexpected relative file creation");self.runtime_preserved()
        if text:return done.stdout.decode("ascii")
        value=json.loads(done.stdout)
        if code==2:
            self.assertEqual(set(value),{"status","code"});self.assertEqual(value["status"],"ERROR");self.assertRegex(value["code"],r"^[A-Z][A-Z0-9_]{0,100}$")
            if error is not None:self.assertEqual(value["code"],error)
        elif value.get("format")=="outlands-reconciliation-v1":
            self.assertIs(value["external_system_writes"],False);self.assertEqual(code,0 if value["status"]=="MATCH" else 1)
            for role in ("before","after","contract"):self.assertEqual(value[role+"_sha256"],sha(self.paths[role].read_bytes()))
            for side in ("before","after"):
                c=value[side+"_counts"];self.assertEqual(c["input_rows"],sum(c[k] for k in ("accepted_records","duplicate_rows","rejected_rows","conflict_rows")))
            if value["status"]=="REVIEW_REQUIRED":
                for key in ("changes","unchanged_records","totals"):self.assertIsNone(value[key])
        return value
    def cli(self,*,show=False,out=False,replacements=None,**options):
        selected=dict(self.paths);selected.update(replacements or {});args=[]
        for role in ("before","after","contract"):args.extend(["--"+role,selected[role]])
        if show:args.append("--show-values")
        if out:args.extend(["--out",self.output])
        return self.invoke(args,**options)
    def api(self,*,show=False,**options):return self.invoke([*(self.paths[role] for role in ("before","after","contract")),json.dumps(show)],mode="api",**options)
    def expect(self,status,before_count,after_count,changes,unchanged,totals,issues=(),*,show=False):
        want=expected(*(self.paths[role].read_bytes() for role in ("before","after","contract")),status,before_count,after_count,changes,unchanged,totals,issues,show)
        code=0 if status=="MATCH" else 1;self.assertEqual(self.cli(show=show,code=code),want);self.assertEqual(self.api(show=show,code=code),want);return want
    def refused(self,role,raw,code=None):
        self.paths[role].write_bytes(raw);self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            strict=self.strict_links if self.strict_links is not None else os.name!="nt" or os.environ.get("OUTLANDS_RECONCILIATION_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
            actual=os.name=="nt" and getattr(error,"winerror",None)==1314
            if actual and not strict:
                self.assertEqual(self.id(),LINK_ID);self.assertFalse(directory);self.native_events.append(dict(test=self.id(),reason=LINK_REASON,policy="actual_windows_1314",actual_windows_1314=True,winerror=1314,strict=False,provenance="test_copied_cli.CopiedCLI.symlink/caught-OSError"));self.skipTest(LINK_REASON)
            raise

    def test_actual_entrypoint_help_affinity_and_three_explicit_inputs(self):
        self.assertEqual(self.invoke(mode="affinity"),dict(status="COPIED_RUNTIME_AFFINITY",runtime_files=3));self.assertIn("--show-values",self.invoke(["--help"],text=True))
        for args in ([],["--before",self.paths["before"]],["--before",self.paths["before"],"--after",self.paths["after"]],["--unknown","FICTIONAL_PRIVATE_SENTINEL"]):self.invoke(args,code=2,error="ARGUMENTS_INVALID")

    def test_equal_totals_do_not_hide_three_authored_record_differences(self):
        old=sample_before();new=sample_after();names=["record_id","units","due","active"]
        changes=[change(dict(record_id="sample-a"),old[0],new[0],"CHANGED",["units"]),change(dict(record_id="sample-b"),old[1],None,"ONLY_IN_BEFORE",names),change(dict(record_id="sample-c"),None,new[1],"ONLY_IN_AFTER",names)]
        report=self.expect("DIFFERENCES",counts(2,2),counts(2,2),changes,0,dict(units=dict(before="19",after="19",delta="0")))
        self.assertEqual(self.cli(out=True,code=1,allow=[self.output]),dict(status="DIFFERENCES",report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))

    def test_identical_reordered_and_duplicate_records_match_unique_totals(self):
        rows=sample_before();self.fixture(rows,list(reversed(rows))+[rows[0]])
        report=self.expect("MATCH",counts(2,2),counts(3,2,1),[],2,dict(units=dict(before="19",after="19",delta="0")))
        self.assertNotEqual(report["before_sha256"],report["after_sha256"]);self.assertEqual(self.cli(out=True,allow=[self.output]),dict(status="MATCH",report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))

    def test_exact_fractional_totals_and_decimal_normalization(self):
        selected=contract([field("id"),field("amount","decimal")],totals=["amount"]);old=[dict(id="a",amount="0.100000"),dict(id="b",amount="0.2"),dict(id="zero",amount="-0.000000")];new=[dict(id="a",amount="0.3"),dict(id="b",amount="0.400"),dict(id="zero",amount="0")]
        self.fixture(old,new,selected);changes=[change(dict(id="a"),dict(id="a",amount="0.1"),dict(id="a",amount="0.3"),"CHANGED",["amount"]),change(dict(id="b"),dict(id="b",amount="0.2"),dict(id="b",amount="0.4"),"CHANGED",["amount"])]
        self.expect("DIFFERENCES",counts(3,3),counts(3,3),changes,1,dict(amount=dict(before="0.3",after="0.7",delta="0.4")))

    def test_maximum_scale_and_thousand_record_cancellation_are_exact(self):
        selected=contract([field("id"),field("amount","decimal"),field("qty","integer")],totals=["amount","qty"])
        old=[dict(id="row-"+str(i).zfill(4),amount="-999999999999.999999",qty=-1000000000000) for i in range(1000)]
        new=[dict(id="row-"+str(i).zfill(4),amount="999999999999.999998" if i==999 else "999999999999.999999",qty=1000000000000) for i in range(1000)]
        self.fixture(old,new,selected);changes=[change(dict(id=a["id"]),a,b,"CHANGED",["amount","qty"]) for a,b in zip(old,new)]
        self.expect("DIFFERENCES",counts(1000,1000),counts(1000,1000),changes,0,dict(amount=dict(before="-999999999999999.999",after="999999999999999.998999",delta="1999999999999999.997999"),qty=dict(before="-1000000000000000",after="1000000000000000",delta="2000000000000000")))

    def test_typed_scalars_do_not_coerce_booleans_strings_or_bad_dates(self):
        for key,supplied,error in (("units",True,"INTEGER_VALUE_INVALID"),("units","12","INTEGER_VALUE_INVALID"),("units",1000000000001,"INTEGER_VALUE_INVALID"),("active","true","BOOLEAN_VALUE_INVALID"),("due","2031-02-29","DATE_VALUE_INVALID"),("record_id","","TEXT_VALUE_INVALID"),("record_id","x"*257,"TEXT_VALUE_INVALID"),("record_id","line\nbreak","TEXT_VALUE_INVALID")):
            rows=sample_before();rows[0][key]=supplied;self.fixture(rows,sample_before());self.expect("REVIEW_REQUIRED",counts(2,1,rejected=1),counts(2,2),None,None,None,[dict(side="before",row=1,code=error)])
        selected=contract([field("id"),field("amount","decimal")],totals=["amount"])
        for value in ("01.2","1e2","1.0000001","1000000000000.000001"):
            self.fixture([dict(id="a",amount=value)],[],selected);self.expect("REVIEW_REQUIRED",counts(1,0,rejected=1),counts(0,0),None,None,None,[dict(side="before",row=1,code="DECIMAL_VALUE_INVALID")])
        selected=contract([field("id"),field("text")],totals=[]);row=dict(id="bounded",text="x"*256);self.fixture([row],[row],selected);self.expect("MATCH",counts(1,1),counts(1,1),[],1,{})

    def test_nullable_fields_are_explicit_and_missing_or_extra_fields_are_held(self):
        selected=contract([field("id"),field("note",nullable=True)],totals=[]);self.fixture([dict(id="a",note=None)],[dict(id="a",note=None)],selected)
        self.expect("MATCH",counts(1,1),counts(1,1),[],1,{})
        for row,error in ((dict(id="a"),"FIELDS_INVALID"),(dict(id="a",note=None,extra="FICTIONAL_PRIVATE_EXTRA"),"FIELDS_INVALID"),(dict(id=None,note=None),"NULL_NOT_ALLOWED")):
            self.fixture([row],[],selected);self.expect("REVIEW_REQUIRED",counts(1,0,rejected=1),counts(0,0),None,None,None,[dict(side="before",row=1,code=error)])

    def test_default_identity_disclosure_and_explicit_values_are_distinct(self):
        selected=contract([field("id"),field("value")],totals=[]);old=dict(id="fictional-visible-λ",value="Before private-looking value");new=dict(id="fictional-visible-λ",value="After private-looking value");self.fixture([old],[new],selected)
        for show in (False,True):
            c=change(dict(id=old["id"]),old,new,"CHANGED",["value"],show);report=self.expect("DIFFERENCES",counts(1,1),counts(1,1),[c],0,{},show=show)
            self.assertEqual(report["changes"][0]["identity"],dict(id=old["id"]));self.assertEqual("before" in report["changes"][0],show);self.assertEqual("after" in report["changes"][0],show)
        self.api(show=1,code=2,error="OPTION_INVALID")

    def test_composite_literal_identities_and_integer_keys_follow_encoded_order(self):
        selected=contract([field("id","integer"),field("value")],totals=[]);old=[dict(id=2,value="two"),dict(id=10,value="ten")];new=[dict(id=2,value="TWO"),dict(id=10,value="TEN")];self.fixture(old,new,selected)
        changes=[change(dict(id=10),old[1],new[1],"CHANGED",["value"]),change(dict(id=2),old[0],new[0],"CHANGED",["value"])];self.expect("DIFFERENCES",counts(2,2),counts(2,2),changes,0,{})
        selected=contract([field("id"),field("part","integer"),field("value")],identity=["id","part"],totals=[])
        rows=[dict(id=" a ",part=1,value="literal"),dict(id="A",part=1,value="upper"),dict(id="a",part=2,value="lower")];self.fixture(rows,list(reversed(rows)),selected);self.expect("MATCH",counts(3,3),counts(3,3),[],3,{})

    def test_any_conflict_globally_holds_changes_unchanged_and_totals(self):
        for side in ("before","after"):
            before=sample_before();after=sample_before();rows=before if side=="before" else after;rows.append(record("sample-a",99));self.fixture(before,after)
            for show in (False,True):self.expect("REVIEW_REQUIRED",counts(3,1,conflicts=2) if side=="before" else counts(2,2),counts(3,1,conflicts=2) if side=="after" else counts(2,2),None,None,None,[dict(side=side,row=1,code="IDENTITY_CONFLICT"),dict(side=side,row=3,code="IDENTITY_CONFLICT")],show=show)

    def test_rejected_values_are_omitted_with_before_then_after_row_issues(self):
        before=sample_before();before[0]["units"]="FICTIONAL_PRIVATE_BEFORE";after=sample_after();after[1]["active"]="FICTIONAL_PRIVATE_AFTER";self.fixture(before,after)
        issues=[dict(side="before",row=1,code="INTEGER_VALUE_INVALID"),dict(side="after",row=2,code="BOOLEAN_VALUE_INVALID")]
        report=self.expect("REVIEW_REQUIRED",counts(2,1,rejected=1),counts(2,1,rejected=1),None,None,None,issues,show=True);self.assertNotIn("FICTIONAL_PRIVATE",json.dumps(report))

    def test_normalized_duplicate_groups_count_once_and_conflicts_have_no_winner(self):
        selected=contract([field("id"),field("amount","decimal")],totals=["amount"]);before=[dict(id="a",amount="1.230000"),dict(id="a",amount="1.23")];after=[dict(id="a",amount="1.230")];self.fixture(before,after,selected)
        self.expect("MATCH",counts(2,1,1),counts(1,1),[],1,dict(amount=dict(before="1.23",after="1.23",delta="0")))
        after.extend([dict(id="a",amount="2"),dict(id="a",amount="1.23")]);self.fixture(before,after,selected)
        self.expect("REVIEW_REQUIRED",counts(2,1,1),counts(3,0,conflicts=3),None,None,None,[dict(side="after",row=i,code="IDENTITY_CONFLICT") for i in (1,2,3)])

    def test_empty_sets_and_one_sided_records_have_qualified_zero_totals(self):
        self.fixture([],[]);self.expect("MATCH",counts(0,0),counts(0,0),[],0,dict(units=dict(before="0",after="0",delta="0")))
        names=["record_id","units","due","active"];row=record("one",7)
        for before,after,classification,total in (([],[row],"ONLY_IN_AFTER",dict(before="0",after="7",delta="7")),([row],[],"ONLY_IN_BEFORE",dict(before="7",after="0",delta="-7"))):
            self.fixture(before,after);self.expect("DIFFERENCES",counts(len(before),len(before)),counts(len(after),len(after)),[change(dict(record_id="one"),before[0] if before else None,after[0] if after else None,classification,names,True)],0,dict(units=total),show=True)

    def test_contract_fields_identity_and_totals_have_exact_suitable_types(self):
        original=self.paths["contract"].read_bytes()
        for transform,error in ((lambda v:v.update(extra="invented"),"FIELDS_INVALID"),(lambda v:v.update(format="other"),"CONTRACT_FORMAT_INVALID"),(lambda v:v.update(fields=[]),"FIELD_LIMIT"),(lambda v:v["fields"].append(dict(v["fields"][0])),"DUPLICATE_FIELD"),(lambda v:v["fields"][0].update(nullable=1),"FIELD_INVALID"),(lambda v:v["fields"][0].update(name="Invalid Name"),"IDENTIFIER_INVALID"),(lambda v:v.update(identity=[]),"IDENTITY_REQUIRED"),(lambda v:v.update(identity=["active"]),"IDENTITY_TYPE_INVALID"),(lambda v:v.update(identity=["record_id","record_id"]),"FIELD_SELECTION_INVALID"),(lambda v:v.update(totals=["due"]),"TOTAL_TYPE_INVALID"),(lambda v:v["fields"][1].update(nullable=True),"TOTAL_TYPE_INVALID"),(lambda v:v["fields"][0].update(nullable=True),"IDENTITY_TYPE_INVALID")):
            value=json.loads(original);transform(value);self.refused("contract",canonical(value),error)

    def test_record_set_shape_field_and_record_limits_are_not_silently_trimmed(self):
        original=self.paths["before"].read_bytes()
        for value,error in ((dict(format="other",records=[]),"RECORD_SET_INVALID"),(dict(format="outlands-record-set-v1",records=[],extra=1),"FIELDS_INVALID"),(record_set([{}]*1001),"RECORD_SET_INVALID")):
            self.refused("before",canonical(value),error)
        self.paths["before"].write_bytes(original);fields=[field("id")]+[field("f"+str(i),nullable=True) for i in range(31)];selected=contract(fields,totals=[]);row=dict(id="a",**{"f"+str(i):None for i in range(31)});self.fixture([row],[row],selected);self.expect("MATCH",counts(1,1),counts(1,1),[],1,{})
        selected["fields"].append(field("overflow"));self.refused("contract",canonical(selected),"FIELD_LIMIT")

    def test_json_duplicate_float_nonfinite_and_utf8_errors_cover_each_role(self):
        originals={role:path.read_bytes() for role,path in self.paths.items()}
        for role in self.paths:
            for raw,error in ((b'{"x":1,"x":2}',"JSON_DUPLICATE_KEY"),(b'{"x":1.5}',"JSON_INTEGER_OR_STRING_REQUIRED"),(b'{"x":NaN}',"JSON_INTEGER_OR_STRING_REQUIRED"),(b'\xff',"JSON_INVALID"),(b'{',"JSON_INVALID")):
                self.refused(role,raw,error);self.paths[role].write_bytes(originals[role])

    def test_json_depth_nodes_text_and_integer_guards_precede_schema(self):
        deep=0
        for unused in range(34):deep=[deep]
        for value,error in ((dict(extra=deep),"JSON_STRUCTURE_LIMIT"),(dict(extra=[0]*100001),"JSON_STRUCTURE_LIMIT"),(dict(extra="x"*4097),"JSON_TEXT_LIMIT"),(dict(extra=1000000000000000001),"JSON_INTEGER_LIMIT")):
            self.refused("before",canonical(value),error)

    def test_raw_input_fingerprints_change_without_changing_supplied_set_meaning(self):
        self.fixture(sample_before(),sample_before());first=self.expect("MATCH",counts(2,2),counts(2,2),[],2,dict(units=dict(before="19",after="19",delta="0")))
        for role in self.paths:self.paths[role].write_bytes(json.dumps(json.loads(self.paths[role].read_bytes()),indent=2).encode())
        second=self.expect("MATCH",counts(2,2),counts(2,2),[],2,dict(units=dict(before="19",after="19",delta="0")))
        for role in self.paths:self.assertNotEqual(first[role+"_sha256"],second[role+"_sha256"])

    def test_actual_four_mebibyte_limits_apply_to_each_input_separately(self):
        self.fixture(sample_before(),sample_before());originals={role:path.read_bytes() for role,path in self.paths.items()}
        for role,path in self.paths.items():path.write_bytes(originals[role]+b" "*(4194304-len(originals[role])))
        self.expect("MATCH",counts(2,2),counts(2,2),[],2,dict(units=dict(before="19",after="19",delta="0")))
        for role,path in self.paths.items():
            at_limit=path.read_bytes();path.write_bytes(at_limit+b" ");self.api(code=2,error="INPUT_LIMIT");self.cli(code=2,error="INPUT_SIZE_LIMIT" if os.name=="nt" else "INPUT_LIMIT");path.write_bytes(at_limit)
        for role,path in self.paths.items():path.write_bytes(originals[role])
        self.cli(mode="output-budget",code=2,error="OUTPUT_LIMIT");self.assertFalse(self.output.exists())

    def test_contract_parse_precedes_record_validation_and_no_type_is_guessed(self):
        self.paths["before"].write_bytes(canonical(record_set([])|{"format":"not-a-record-set"}));self.paths["contract"].write_bytes(canonical(contract()|{"format":"not-a-contract"}));self.api(code=2,error="CONTRACT_FORMAT_INVALID");self.cli(code=2,error="CONTRACT_FORMAT_INVALID")
        self.paths["contract"].write_bytes(canonical(contract()));self.api(code=2,error="RECORD_SET_INVALID");self.cli(code=2,error="RECORD_SET_INVALID")

    def test_changed_field_order_is_declared_and_same_identity_is_not_renamed(self):
        selected=contract([field("record_id"),field("active","boolean"),field("due","date"),field("units","integer")]);old=record("a",1,"2030-01-10",False);new=record("a",2,"2030-01-11",True);self.fixture([old],[new],selected)
        changes=[change(dict(record_id="a"),old,new,"CHANGED",["active","due","units"])];self.expect("DIFFERENCES",counts(1,1),counts(1,1),changes,0,dict(units=dict(before="1",after="2",delta="1")))

    def test_short_and_changed_reads_are_injected_separately_for_three_roles(self):
        for role in self.paths:
            for prefix in ("short-","changed-"):self.cli(mode=prefix+role,code=2,error="INPUT_CHANGED")
            self.cli(replacements={role:self.work/("FICTIONAL_PRIVATE_"+role)},code=2)

    def test_no_overwrite_three_input_aliases_and_source_output_protection(self):
        self.output.write_bytes(b"Invented retained report");self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),b"Invented retained report")
        for target in self.paths.values():
            args=[]
            for role,path in self.paths.items():args.extend(["--"+role,path])
            self.invoke([*args,"--out",target],code=2)
        for target in (self.copy/"new.json",self.copy/"toolkit.py"):
            args=[]
            for role,path in self.paths.items():args.extend(["--"+role,path])
            self.invoke([*args,"--out",target],code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE")
        collection=self.owned(self.work/"collection");selected=collection/"tools/tabular-reconciliation-checker";selected.mkdir(parents=True);(collection/"systems").mkdir();(collection/"catalog").mkdir();(collection/"catalog/registry.json").write_bytes(b"{}\n")
        for name in RUNTIME:(selected/name).write_bytes((self.copy/name).read_bytes())
        self.invoke([*args,"--out",collection/"refused.json"],base=selected,code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE")

    def test_retained_partial_output_is_unconfirmed_and_never_reused(self):
        self.cli(out=True,mode="write-failure",code=2,error="INPUT_OR_OUTPUT_REFUSED",allow=[self.output]);self.assertEqual(self.output.read_bytes(),b'{"aft')
        self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),b'{"aft')

    def test_each_input_role_requires_single_link_without_masking(self):
        for role,target in self.paths.items():
            alias=self.owned(self.work/(role+"-hardlink"));os.link(target,alias);self.assertTrue(alias.samefile(target));self.cli(replacements={role:alias},code=2,error="CONTROL_NOT_SINGLE_LINK" if os.name=="nt" else "INPUT_UNSAFE")
            self.cli(code=2,error="CONTROL_NOT_SINGLE_LINK" if os.name=="nt" else "INPUT_UNSAFE");self.owned(alias).unlink();self.assertEqual(target.stat().st_nlink,1)

    def test_linked_parents_of_all_three_inputs_and_output_refuse(self):
        target=self.owned(self.work/"target");target.mkdir()
        for role,path in self.paths.items():(target/(role+".json")).write_bytes(path.read_bytes())
        route=self.owned(self.work/"route")
        if os.name=="nt":
            done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(route),str(target)],capture_output=True,timeout=15);self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:route.rmdir() if route.exists() else None)
        else:route.symlink_to(target,target_is_directory=True)
        for role in self.paths:self.cli(replacements={role:route/(role+".json")},code=2)
        args=[]
        for role,path in self.paths.items():args.extend(["--"+role,path])
        self.invoke([*args,"--out",route/"new.json"],code=2);self.assertFalse((target/"new.json").exists())

    def test_native_leaf_symlink_and_dangling_output_refusal(self):
        for role,target in self.paths.items():
            link=self.owned(self.work/(role+"-leaf-link"));self.symlink(link,target);self.cli(replacements={role:link},code=2)
        args=[]
        for role,path in self.paths.items():args.extend(["--"+role,path])
        for name,target in (("dangling",self.work/"never-created.json"),("source-pointing",self.copy/"never-created.json")):
            target=self.owned(target);self.assertFalse(os.path.lexists(target));route=self.owned(self.work/(name+".json"));self.symlink(route,target)
            self.invoke([*args,"--out",route],code=2);self.assertFalse(os.path.lexists(target));self.assertTrue(route.is_symlink())
        for name,target in [*self.paths.items(),("runtime",self.copy/"toolkit.py")]:
            raw=target.read_bytes();route=self.owned(self.work/(name+"-pointing.json"));self.symlink(route,target);self.invoke([*args,"--out",route],code=2);self.assertEqual(target.read_bytes(),raw)

    @unittest.skipUnless(os.name=="nt",WINDOWS_REASON)
    def test_native_windows_path_grammar_and_named_stream_routes(self):
        for role,target in self.paths.items():
            for path in (str(target)+":stream",str(self.work/"CON"),str(target)+".",str(target)+" ","x:relative","//example.invalid/share"):self.cli(replacements={role:path},code=2)
        args=[]
        for role,path in self.paths.items():args.extend(["--"+role,path])
        self.invoke([*args,"--out",str(self.output)+":stream"],code=2)

    @unittest.skipUnless(os.name!="nt",POSIX_REASON)
    def test_native_posix_special_inputs_and_private_report_mode(self):
        fifo=self.owned(self.work/"fictional.fifo");os.mkfifo(fifo);sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.owned(self.work/"s")));self.addCleanup(sock.close)
        for role in self.paths:
            for path in (fifo,self.work/"s",self.work):self.cli(replacements={role:path},code=2)
        self.cli(out=True,code=1,allow=[self.output]);self.assertEqual(stat.S_IMODE(self.output.stat().st_mode),0o600)

    def test_units_and_business_meaning_are_not_implicitly_converted(self):
        selected=contract([field("id"),field("amount","decimal"),field("unit")],totals=["amount"]);old=dict(id="a",amount="1",unit="m");new=dict(id="a",amount="100",unit="cm");self.fixture([old],[new],selected)
        self.expect("DIFFERENCES",counts(1,1),counts(1,1),[change(dict(id="a"),old,new,"CHANGED",["amount","unit"])],0,dict(amount=dict(before="1",after="100",delta="99")))


class TrackedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.started_ids=set();self.successful_ids=set()
    def startTest(self,test):self.started_ids.add(test.id());super().startTest(test)
    def addSuccess(self,test):self.successful_ids.add(test.id());super().addSuccess(test)


def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item


def load_copied_suite(strict=None):
    if strict is None:strict=os.name!="nt" or os.environ.get("OUTLANDS_RECONCILIATION_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
    assert type(strict) is bool
    CopiedCLI.strict_links=os.name!="nt" or strict;CopiedCLI.native_events=[];suite=unittest.defaultTestLoader.loadTestsFromTestCase(CopiedCLI);ids=[test.id() for test in flatten(suite)]
    assert len(ids)==len(set(ids))==30 and all(name.startswith("test_copied_cli.CopiedCLI.test_") for name in ids)
    assert all(name in set(ids) for name,reason in REQUIRED_WINDOWS_SKIPS|REQUIRED_POSIX_SKIPS|OPTIONAL_WINDOWS_LINK_SKIPS) and FLOW_IDS|COMMON_NATIVE_IDS<=set(ids)
    return suite


def run_copied_tests(strict=None,log_stream=None):
    suite=load_copied_suite(strict);strict=CopiedCLI.strict_links;ids=[test.id() for test in flatten(suite)]
    result=unittest.TextTestRunner(stream=log_stream if log_stream is not None else sys.stderr,verbosity=2,resultclass=TrackedResult).run(suite)
    skips=[dict(test=test.id(),reason=reason) for test,reason in result.skipped];required=REQUIRED_WINDOWS_SKIPS if os.name=="nt" else REQUIRED_POSIX_SKIPS;optional=OPTIONAL_WINDOWS_LINK_SKIPS if os.name=="nt" and not strict else set()
    observed={(row["test"],row["reason"]) for row in skips};unexpected=[row for row in skips if (row["test"],row["reason"]) not in required|optional];failed=sorted({getattr(test,"test_case",test).id() for test,trace in result.failures+result.errors})
    all_started=set(ids)<=result.started_ids;valid_successes=result.successful_ids<=result.started_ids&set(ids)
    good=result.wasSuccessful() and result.testsRun==30 and all_started and valid_successes and len(skips)==len(observed) and required<=observed<=required|optional
    native=COMMON_NATIVE_IDS|{WINDOWS_ID if os.name=="nt" else POSIX_ID};flow_checked=good and FLOW_IDS<=result.successful_ids;native_checked=good and native<=result.successful_ids
    return dict(schema=1,status="PASS" if good and flow_checked and native_checked else "FAIL",tests=result.testsRun,selected_tests=30,passed=len(result.successful_ids),skipped=len(skips),failures=len(result.failures),errors=len(result.errors),
        skips=skips,unexpected_skips=unexpected,missing_required_skips=[dict(test=name,reason=reason) for name,reason in sorted(required-observed)],failed_tests=failed,test_ids=ids,started_test_ids=sorted(result.started_ids),successful_test_ids=sorted(result.successful_ids),
        all_selected_tests_started=all_started,successful_ids_exclude_setup_failures=valid_successes,module_counts={"test_copied_cli":30},native_links_required=strict,native_fixture_events=CopiedCLI.native_events,
        fictional_reconciliation_flow_checked=flow_checked,native_file_guards_checked=native_checked,positive_asserted_test_ids=dict(fictional_reconciliation_flow_checked=sorted(FLOW_IDS),native_file_guards_checked=sorted(native)),
        child_arithmetic_context_verified=good and flow_checked and native_checked,
        copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,**{name:False for name in FALSE_FLAGS})


if __name__=="__main__":raise SystemExit(0 if run_copied_tests()["status"]=="PASS" else 1)
