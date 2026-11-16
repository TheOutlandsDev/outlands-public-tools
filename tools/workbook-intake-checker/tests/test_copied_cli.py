"""Independent mapped CSV/XLSX consumers on fictional records; no Office or external writer. MIT."""
import copy
import csv
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

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=("intake.py","toolkit.py","native_windows.py","fictional_workbook.py")
WINDOWS_ID="test_copied_cli.CopiedCLI.test_native_windows_path_grammar_and_named_stream_routes"
WINDOWS_REASON="Native Windows path-grammar fixtures"
POSIX_ID="test_copied_cli.CopiedCLI.test_native_posix_special_inputs_and_private_report_mode"
POSIX_REASON="Native POSIX special-file and mode fixtures"
LINK_ID="test_copied_cli.CopiedCLI.test_native_leaf_symlink_and_dangling_output_refusal"
LINK_REASON="Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS={(POSIX_ID,POSIX_REASON)}
REQUIRED_POSIX_SKIPS={(WINDOWS_ID,WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS={(LINK_ID,LINK_REASON)}

S="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P="http://schemas.openxmlformats.org/package/2006/relationships"
C="http://schemas.openxmlformats.org/package/2006/content-types"
FALSE_FLAGS=("real_records_used","real_workbooks_used","imported","source_transformed","formulas_evaluated","macros_executed",
             "office_processes_started","external_resources_followed","visible_layout_verified","production_workflows_verified")
FLOW_IDS={"test_copied_cli.CopiedCLI.test_generator_and_fresh_report_readback_are_exact",
          "test_copied_cli.CopiedCLI.test_csv_inline_shared_string_reports_have_authored_parity",
          "test_copied_cli.CopiedCLI.test_conflict_groups_withhold_all_members_but_preserve_independent_rows"}
COMMON_NATIVE_IDS={"test_copied_cli.CopiedCLI.test_no_overwrite_and_standalone_collection_source_output_guards",
                   "test_copied_cli.CopiedCLI.test_retained_partial_report_is_not_confirmed_or_replaced",
                   "test_copied_cli.CopiedCLI.test_mandatory_hardlink_inputs_and_existing_outputs_are_refused",
                   "test_copied_cli.CopiedCLI.test_linked_parent_read_and_report_routes_are_refused"}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return (json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(",",":"))+"\n").encode()


def field(source,target,kind="text",required=True):return dict(source=source,target=target,type=kind,required=required)


def mapping(fields=None,identity=None,unknown="reject"):
    if fields is None:fields=[field("Record","record_id"),field("Units","units","integer"),field("Due","due","date"),field("Active","active","boolean")]
    return dict(format="outlands-table-map-v1",identity=[fields[0]["target"]] if identity is None else identity,unknown_columns=unknown,fields=fields)


def sample_rows():return [["Record","Units","Due","Active"],["sample-a","12","2030-01-10","true"],["sample-b","7","2030-01-11","false"],["sample-a","12","2030-01-10","true"]]


def sample_records():return [(dict(record_id="sample-a",units=12,due="2030-01-10",active=True),[2,4]),(dict(record_id="sample-b",units=7,due="2030-01-11",active=False),[3])]


def csv_bytes(rows):
    output=io.StringIO(newline="");csv.writer(output,lineterminator="\n").writerows(rows);return output.getvalue().encode()


def zip_bytes(parts,compression=zipfile.ZIP_STORED):
    output=io.BytesIO()
    with zipfile.ZipFile(output,"w") as archive:
        for name,raw in (parts.items() if isinstance(parts,dict) else parts):
            info=zipfile.ZipInfo(name,date_time=(2030,1,1,0,0,0));info.compress_type=compression;archive.writestr(info,raw)
    return output.getvalue()


def column(number):
    value=""
    while number:number,remainder=divmod(number-1,26);value=chr(65+remainder)+value
    return value


def components(rows=None,shared=False):
    if rows is None:rows=sample_rows()
    strings=list(dict.fromkeys(value for row in rows for value in row));body=[]
    for r,row in enumerate(rows,1):
        cells=[]
        for c,value in enumerate(row,1):
            ref=column(c)+str(r)
            cells.append('<c r="'+ref+'" t="s"><v>'+str(strings.index(value))+'</v></c>' if shared else '<c r="'+ref+'" t="inlineStr"><is><t>'+escape(value)+'</t></is></c>')
        body.append('<row r="'+str(r)+'">'+''.join(cells)+'</row>')
    parts={
        "[Content_Types].xml":('<Types xmlns="'+C+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'+('<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>' if shared else '')+'</Types>').encode(),
        "_rels/.rels":('<Relationships xmlns="'+P+'"><Relationship Id="rId1" Type="'+R+'/officeDocument" Target="xl/workbook.xml"/></Relationships>').encode(),
        "xl/workbook.xml":('<workbook xmlns="'+S+'" xmlns:r="'+R+'"><sheets><sheet name="Records" sheetId="1" r:id="rId1"/></sheets></workbook>').encode(),
        "xl/_rels/workbook.xml.rels":('<Relationships xmlns="'+P+'"><Relationship Id="rId1" Type="'+R+'/worksheet" Target="worksheets/sheet1.xml"/>'+('<Relationship Id="rId2" Type="'+R+'/sharedStrings" Target="sharedStrings.xml"/>' if shared else '')+'</Relationships>').encode(),
        "xl/worksheets/sheet1.xml":('<worksheet xmlns="'+S+'"><sheetData>'+''.join(body)+'</sheetData></worksheet>').encode()}
    if shared:parts["xl/sharedStrings.xml"]=('<sst xmlns="'+S+'">'+''.join('<si><t>'+escape(value)+'</t></si>' for value in strings)+'</sst>').encode()
    return parts


def workbook(rows=None,shared=False):return zip_bytes(components(rows,shared))


def edit(raw,changes):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:parts={name:archive.read(name) for name in archive.namelist()}
    for name,value in changes.items():
        if value is None:parts.pop(name,None)
        else:parts[name]=value(parts.get(name,b"")) if callable(value) else value
    return zip_bytes(parts)


def expected(raw,mapping_raw,kind,sheet,input_rows,records,issues=(),ignored=0):
    # Typed records, source-row lists and issues are authored at each call site.
    conflicts=sum(row["code"]=="IDENTITY_CONFLICT" for row in issues)
    counts=dict(input_rows=input_rows,accepted_records=len(records),duplicate_rows=sum(len(rows)-1 for record,rows in records),rejected_rows=len(issues)-conflicts,conflict_rows=conflicts)
    assert input_rows==sum(counts[key] for key in ("accepted_records","duplicate_rows","rejected_rows","conflict_rows"))
    status="PASS" if records and not issues else "REVIEW_REQUIRED"
    return dict(format="outlands-intake-preview-v1",status=status,source_sha256=sha(raw),mapping_sha256=sha(mapping_raw),source_format=kind,sheet=sheet,
        mapping=json.loads(mapping_raw)["fields"],ignored_columns=ignored,counts=counts,accepted=[dict(record=record,source_rows=rows) for record,rows in records],issues=list(issues),ready_for_explicit_review=status=="PASS",imported=False)


CHILD=r'''
import _decimal,_elementtree,decimal,hashlib,importlib.metadata,json,os,pyexpat,runpy,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();mode=sys.argv[2];args=sys.argv[3:];sys.path.insert(0,str(base))
def audit(event,values):
 if event.startswith(('socket.','subprocess.','os.startfile','sqlite3.')) or event in ('os.system','webbrowser.open'):
  raise AssertionError('UNEXPECTED_NETWORK_OFFICE_STORE_OR_PROCESS')
sys.addaudithook(audit)
def no_extract(*a,**kw):raise AssertionError('INPUT_ARCHIVE_EXTRACTION_FORBIDDEN')
zipfile.ZipFile.extract=zipfile.ZipFile.extractall=no_extract
import intake as a
import fictional_workbook as g
import toolkit as t
import native_windows as n
for module,name in ((a,'intake.py'),(g,'fictional_workbook.py'),(t,'toolkit.py'),(n,'native_windows.py')):assert Path(module.__file__).resolve()==base/name
assert a.t is g.t is t and a.zipfile is g.zipfile is zipfile and a.Decimal is decimal.Decimal
assert a.preview.__globals__ is a.__dict__ and t.read.__globals__ is t.__dict__ and t.write_new.__globals__ is t.__dict__
def state():
 assert t.ET.XMLParser is _elementtree.XMLParser and t.ET.TreeBuilder is _elementtree.TreeBuilder and t.XMLBuilder.__mro__[1] is _elementtree.TreeBuilder
 assert decimal.Decimal is _decimal.Decimal and decimal.Context is _decimal.Context and a.Decimal is _decimal.Decimal
 context=decimal.getcontext()
 return (t.ET.XMLParser,t.ET.TreeBuilder,t.XMLBuilder.__mro__[1],pyexpat.EXPAT_VERSION,
  context.prec,context.rounding,context.Emin,context.Emax,context.capitals,context.clamp,
  tuple(sorted((key.__name__,value) for key,value in context.traps.items())),tuple(sorted((key.__name__,value) for key,value in context.flags.items())))
before=state();assert before[4:10]==(28,'ROUND_HALF_EVEN',-999999,999999,1,0)
assert not any(decimal.getcontext().flags.values()) and {key.__name__ for key,value in decimal.getcontext().traps.items() if value}=={'InvalidOperation','DivisionByZero','Overflow'}
try:
 if mode=='affinity':sys.stdout.write(t.encode(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=4)).decode());raise SystemExit(0)
 if mode=='generator':
  sys.argv=[str(base/'fictional_workbook.py'),*args];runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('GENERATOR_ENTRYPOINT_DID_NOT_EXIT')
 if mode=='api':
  source=Path(args[0]);mapping=Path(args[1]);assert source.is_absolute() and mapping.is_absolute()
  try:value=a.preview(source.read_bytes(),mapping.read_bytes(),json.loads(args[2]),json.loads(args[3]))
  except t.Rejected as error:sys.stdout.write(t.encode(dict(status='ERROR',code=str(error))).decode());raise SystemExit(2)
  sys.stdout.write(t.encode(value).decode());raise SystemExit(0 if value['status']=='PASS' else 1)
 if mode.startswith(('short-read-','changed-stat-')):
  role=mode.rsplit('-',1)[1];path=Path(args[args.index('--'+role)+1]);info=path.stat();identity=(info.st_dev,info.st_ino)
  real_read=os.read;real_stat=os.fstat;changed=False
  def selected(fd):
   info=real_stat(fd);return (info.st_dev,info.st_ino)==identity
  def read(fd,*values):
   global changed
   if mode.startswith('short-read-') and selected(fd):return b''
   raw=real_read(fd,*values)
   if raw and selected(fd):changed=True
   return raw
  def info(fd):
   value=real_stat(fd)
   if not changed or (value.st_dev,value.st_ino)!=identity:return value
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
 sys.argv=[str(base/'intake.py'),*args];runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('INTAKE_ENTRYPOINT_DID_NOT_EXIT')
finally:assert state()==before,'SELECTED_XML_OR_DEFAULT_ARITHMETIC_CONTEXT_CHANGED'
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
        self.temp=tempfile.TemporaryDirectory(prefix="workbook-intake-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.assertEqual(self.work.parent,parent);self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();(self.copy/name).write_bytes(raw);self.pins[name]=sha(raw)
        self.input=self.work/"records.csv";self.mapping=self.work/"mapping.json";self.output=self.work/"report.json"
        self.kind="csv";self.sheet=None;self.rows=sample_rows();self.input.write_bytes(csv_bytes(self.rows));self.mapping.write_bytes(canonical(mapping()))
        self.env={key:value for key,value in os.environ.items() if not key.upper().startswith(("PYTHON","PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHON_COLORS="0",NO_COLOR="1");self.addCleanup(self.runtime_preserved)
    def runtime_preserved(self):
        self.assertEqual({p.name for p in self.copy.iterdir()},set(RUNTIME));self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME},self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")),[])
    def owned(self,path):
        path=Path(path);self.assertTrue(path.is_absolute() and path.resolve().is_relative_to(self.work));return path
    def fixture(self,rows,config=None,kind="csv",shared=False,raw=None):
        self.rows=rows;self.kind=kind;self.sheet="Records" if kind=="xlsx" else None
        self.input.write_bytes(raw if raw is not None else csv_bytes(rows) if kind=="csv" else workbook(rows,shared))
        self.mapping.write_bytes(canonical(mapping() if config is None else config))
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
        elif value.get("format")=="outlands-intake-preview-v1":
            self.assertIs(value["imported"],False);self.assertEqual(value["source_sha256"],sha(self.input.read_bytes()));self.assertEqual(value["mapping_sha256"],sha(self.mapping.read_bytes()))
            counts=value["counts"];self.assertEqual(counts["input_rows"],sum(counts[key] for key in ("accepted_records","duplicate_rows","rejected_rows","conflict_rows")))
            self.assertEqual(code,0 if value["status"]=="PASS" else 1)
        return value
    def arguments(self,input=None,mapping=None):
        args=["--input",self.input if input is None else input,"--mapping",self.mapping if mapping is None else mapping,"--format",self.kind]
        if self.sheet is not None:args.extend(["--sheet",self.sheet])
        return args
    def cli(self,*,out=False,**options):return self.invoke([*self.arguments(),*(["--out",self.output] if out else [])],**options)
    def api(self,*,options=None,**kwargs):
        kind,sheet=(self.kind,self.sheet) if options is None else options
        return self.invoke([self.input,self.mapping,json.dumps(kind),json.dumps(sheet)],mode="api",**kwargs)
    def expect(self,records,issues=(),ignored=0,api=True):
        want=expected(self.input.read_bytes(),self.mapping.read_bytes(),self.kind,self.sheet,len(self.rows)-1,records,issues,ignored);code=0 if want["status"]=="PASS" else 1
        self.assertEqual(self.cli(code=code),want)
        if api:self.assertEqual(self.api(code=code),want)
        return want
    def check(self,rows,records,issues=(),config=None,kind="csv",shared=False,raw=None,ignored=0,api=True):
        self.fixture(rows,config,kind,shared,raw);return self.expect(records,issues,ignored,api)
    def refused_workbook(self,raw,code=None):
        self.fixture(sample_rows(),kind="xlsx",raw=raw);self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            strict=self.strict_links if self.strict_links is not None else os.name!="nt" or os.environ.get("OUTLANDS_WORKBOOK_INTAKE_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
            actual=os.name=="nt" and getattr(error,"winerror",None)==1314
            if actual and not strict:
                self.assertEqual(self.id(),LINK_ID);self.assertFalse(directory);self.native_events.append(dict(test=self.id(),reason=LINK_REASON,policy="actual_windows_1314",actual_windows_1314=True,winerror=1314,strict=False,provenance="test_copied_cli.CopiedCLI.symlink/caught-OSError"));self.skipTest(LINK_REASON)
            raise


    def test_copied_affinity_and_actual_entrypoint_help_are_inert(self):
        self.assertEqual(self.invoke(mode="affinity"),dict(status="COPIED_RUNTIME_AFFINITY",runtime_files=4))
        self.assertIn("--mapping",self.invoke(["--help"],text=True));self.assertIn("--sheet",self.invoke(["--help"],text=True));self.assertIn("--out",self.invoke(["--help"],mode="generator",text=True))
        for mode in ("normal","generator"):
            self.invoke(mode=mode,code=2,error="ARGUMENTS_INVALID");self.invoke(["--unknown","FICTIONAL_PRIVATE_SENTINEL"],mode=mode,code=2,error="ARGUMENTS_INVALID")
        self.invoke(["--input",self.input,"--mapping",self.mapping],code=2,error="ARGUMENTS_INVALID")

    def test_generator_and_fresh_report_readback_are_exact(self):
        target=self.owned(self.work/"generated.xlsx");value=self.invoke(["--out",target],mode="generator",allow=[target]);raw=target.read_bytes()
        self.assertEqual(value,dict(status="PASS",fictional=True,bytes=len(raw),sha256=sha(raw)))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual({name:archive.read(name) for name in archive.namelist()},components())
            self.assertTrue(all(info.date_time==(2030,1,1,0,0,0) and info.compress_type==zipfile.ZIP_DEFLATED for info in archive.infolist()))
        self.input=target;self.kind="xlsx";self.sheet="Records";report=self.expect(sample_records())
        self.assertEqual(self.cli(out=True,allow=[self.output]),dict(status="PASS",report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))
        self.invoke(["--out",target],mode="generator",code=2,error="OUTPUT_REFUSED")

    def test_csv_inline_shared_string_reports_have_authored_parity(self):
        results=[]
        for kind,shared in (("csv",False),("xlsx",False),("xlsx",True)):
            results.append(self.check(sample_rows(),sample_records(),kind=kind,shared=shared))
        for key in ("status","mapping","counts","accepted","issues","ready_for_explicit_review","imported"):
            self.assertEqual(results[0][key],results[1][key]);self.assertEqual(results[1][key],results[2][key])
        self.assertEqual(len({row["source_sha256"] for row in results}),3);self.assertEqual(len({row["mapping_sha256"] for row in results}),1)

    def test_five_exact_types_optional_null_and_required_blank_accounting(self):
        config=mapping([field("ID","id"),field("Integer","integer","integer"),field("Decimal","decimal","decimal"),field("Boolean","boolean","boolean"),field("Date","date","date",False)])
        rows=[["ID","Integer","Decimal","Boolean","Date"],["a","-1000000000000","1.500000","false",""],["b","0","-0.125000","true","2032-02-29"],["c","","1","true","2030-01-01"]]
        records=[(dict(id="a",integer=-1000000000000,decimal="1.5",boolean=False,date=None),[2]),(dict(id="b",integer=0,decimal="-0.125",boolean=True,date="2032-02-29"),[3])]
        issues=[dict(row=4,code="REQUIRED_VALUE_MISSING")]
        for kind in ("csv","xlsx"):self.check(rows,records,issues,config,kind)

    def test_normalized_duplicates_preserve_all_rows_and_literal_identity_spelling(self):
        config=mapping([field("ID","id"),field("Amount","amount","decimal")]);rows=[["ID","Amount"],["a","1.500000"],["a","1.5"],["A","1.5"],[" a","1.5"]]
        records=[(dict(id=" a",amount="1.5"),[5]),(dict(id="A",amount="1.5"),[4]),(dict(id="a",amount="1.5"),[2,3])]
        value=self.check(rows,records,config=config);self.assertEqual(value["counts"]["duplicate_rows"],1)
        self.check(rows,records,config=config,kind="xlsx",shared=True)

    def test_conflict_groups_withhold_all_members_but_preserve_independent_rows(self):
        rows=sample_rows()+[["sample-a","13","2030-01-10","true"],["sample-c","Fictional rejected sentinel","2030-01-10","true"]]
        records=[(dict(record_id="sample-b",units=7,due="2030-01-11",active=False),[3])]
        issues=[dict(row=2,code="IDENTITY_CONFLICT"),dict(row=4,code="IDENTITY_CONFLICT"),dict(row=5,code="IDENTITY_CONFLICT"),dict(row=6,code="VALUE_INTEGER_INVALID")]
        for kind in ("csv","xlsx"):
            value=self.check(rows,records,issues,kind=kind);self.assertFalse(value["ready_for_explicit_review"]);self.assertNotIn("Fictional rejected sentinel",json.dumps(value))
            self.assertEqual(value["counts"],dict(input_rows=5,accepted_records=1,duplicate_rows=0,rejected_rows=1,conflict_rows=3))

    def test_composite_identity_field_order_and_typed_duplicate_groups(self):
        config=mapping([field("Name","name"),field("Number","number","integer"),field("Flag","flag","boolean")],["number","name"])
        rows=[["Name","Number","Flag"],["b","2","true"],["a","10","false"],["b","2","true"]]
        records=[(dict(name="a",number=10,flag=False),[3]),(dict(name="b",number=2,flag=True),[2,4])]
        self.check(rows,records,config=config);self.check(rows,records,config=config,kind="xlsx")

    def test_unknown_columns_headers_and_empty_tables_require_explicit_policy(self):
        rows=[sample_rows()[0]+["Unknown"],sample_rows()[1]+["Fictional ignored cell"]];self.fixture(rows)
        self.cli(out=True,code=2,error="UNMAPPED_HEADER");self.assertFalse(self.output.exists())
        self.check(rows,[(sample_records()[0][0],[2])],config=mapping(unknown="ignore"),ignored=1)
        for rows,code in (([],"HEADER_INVALID"),([["A","A"]],"HEADER_INVALID"),([["", "B"]],"HEADER_INVALID"),([["record","Units","Due","Active"]],"MAPPED_HEADER_MISSING")):
            for kind in ("csv","xlsx"):
                self.fixture(rows,kind=kind);self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
        for kind in ("csv","xlsx"):self.check([sample_rows()[0]],[],kind=kind)

    def test_mapping_schema_duplicates_types_and_bounded_json_are_refused(self):
        variants=[]
        config=mapping();config["fields"][1]["target"]="record_id";variants.append((config,"MAP_DUPLICATE_FIELD"))
        config=mapping();config["fields"][1]["source"]="Record";variants.append((config,"MAP_DUPLICATE_FIELD"))
        config=mapping();config["fields"][0]["required"]=False;variants.append((config,"MAP_IDENTITY_INVALID"))
        config=mapping();config["fields"][0]["required"]=1;variants.append((config,"MAP_INVALID"))
        config=mapping();config["fields"][0]["target"]="Bad Name";variants.append((config,"IDENTIFIER_INVALID"))
        config=mapping();config["fields"][0]["source"]="bad\x7f";variants.append((config,"MAP_INVALID"))
        config=mapping();config["identity"]=["record_id"]*2;variants.append((config,"MAP_IDENTITY_INVALID"))
        config=mapping();config["fields"]*=9;variants.append((config,"MAP_INVALID"))
        config=mapping();config["extra"]=True;variants.append((config,"FIELDS_INVALID"))
        for config,code in variants:
            self.mapping.write_bytes(canonical(config));self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
        for raw,code in ((b'{"format":1,"format":2}',"JSON_DUPLICATE_KEY"),(b'{"x":1.2}',"JSON_INTEGER_OR_STRING_REQUIRED"),(b'{"x":NaN}',"JSON_INTEGER_OR_STRING_REQUIRED"),(b'\xff',"JSON_INVALID"),(b'[]',"FIELDS_INVALID"),(b'['*34+b'0'+b']'*34,"JSON_STRUCTURE_LIMIT")):
            self.mapping.write_bytes(raw);self.api(code=2,error=code);self.cli(out=True,code=2,error=code)

    def test_csv_utf8_bom_quotes_logical_positions_and_blank_rows_are_exact(self):
        config=mapping([field("ID","id"),field("Value","value")]);rows=[["ID","Value"],["a,b",'quoted "value"'],["line\nbreak","rejected"],[],["extra","one","two"]]
        issues=[dict(row=3,code="VALUE_TEXT_INVALID"),dict(row=4,code="ROW_WIDTH_INVALID"),dict(row=5,code="ROW_WIDTH_INVALID")]
        self.check(rows,[(dict(id="a,b",value='quoted "value"'),[2])],issues,config,raw=b'\xef\xbb\xbf'+csv_bytes(rows).replace(b'\n',b'\r\n'))
        for raw in (b'\xff',b'"unclosed',b'ID\x00,Value\na,b\n'):
            self.fixture(sample_rows(),raw=raw);self.api(code=2,error="CSV_INVALID");self.cli(out=True,code=2,error="CSV_INVALID");self.assertFalse(self.output.exists())

    def test_xlsx_literal_cell_types_do_not_infer_display_or_business_meaning(self):
        rows=[["ID","Number","Flag","Date"],["a","12","true","2032-02-29"]];config=mapping([field("ID","id"),field("Number","number","integer"),field("Flag","flag","boolean"),field("Date","date","date")])
        raw=workbook(rows);raw=edit(raw,{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'<c r="B2" t="inlineStr"><is><t>12</t></is></c>',b'<c r="B2" s="999"><v>12</v></c>').replace(b'<c r="C2" t="inlineStr"><is><t>true</t></is></c>',b'<c r="C2" t="b"><v>1</v></c>').replace(b'<c r="D2" t="inlineStr"><is><t>2032-02-29</t></is></c>',b'<c r="D2" t="d"><v>2032-02-29</v></c>')})
        self.check(rows,[(dict(id="a",number=12,flag=True,date="2032-02-29"),[2])],config=config,kind="xlsx",raw=raw)
        textmap=mapping([field("ID","id"),field("Value","value")]);rows=[["ID","Value"],["a","1e3"]]
        raw=edit(workbook(rows),{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'<c r="B2" t="inlineStr"><is><t>1e3</t></is></c>',b'<c r="B2" s="14"><v>1e3</v></c>')})
        self.check(rows,[(dict(id="a",value="1e3"),[2])],config=textmap,kind="xlsx",raw=raw)
        decimalmap=mapping([field("ID","id"),field("Value","value","decimal")]);self.check(rows,[],[dict(row=2,code="VALUE_DECIMAL_INVALID")],decimalmap,"xlsx",raw=raw)
        rows=[["ID","Value"],["a","45000"]];raw=edit(workbook(rows),{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'<c r="B2" t="inlineStr"><is><t>45000</t></is></c>',b'<c r="B2" s="14"><v>45000</v></c>')})
        self.check(rows,[(dict(id="a",value="45000"),[2])],config=textmap,kind="xlsx",raw=raw)

    def test_sparse_xlsx_cells_pad_blanks_but_csv_width_stays_explicit(self):
        config=mapping([field("ID","id"),field("Optional","optional","text",False),field("Value","value","text",False)])
        rows=[["ID","Optional","Value"],["a","","tail"],["b"]];raw=edit(workbook(rows),{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'<c r="B2" t="inlineStr"><is><t></t></is></c>',b'')})
        self.check(rows,[(dict(id="a",optional=None,value="tail"),[2]),(dict(id="b",optional=None,value=None),[3])],config=config,kind="xlsx",raw=raw)
        self.check(rows,[(dict(id="a",optional=None,value="tail"),[2])],[dict(row=3,code="ROW_WIDTH_INVALID")],config)

    def test_shared_strings_rich_text_indexes_and_cell_coordinates_are_bounded(self):
        raw=workbook(shared=True)
        for changed,code in ((edit(raw,{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'<v>0</v>',b'<v>99999</v>',1)}),"XLSX_SHARED_STRING_INVALID"),(edit(raw,{"xl/sharedStrings.xml":lambda b:b.replace(b'<si><t>Record</t></si>',b'<si><r><t>Record</t></r></si>')}),"XLSX_RICH_STRING_UNSUPPORTED"),(edit(raw,{"xl/sharedStrings.xml":None}),"XLSX_RELATIONSHIP_INVALID")):
            self.refused_workbook(changed,code)
        for coordinate,code in ((b'A2',"XLSX_CELL_ORDER_INVALID"),(b'A1',"XLSX_CELL_INVALID"),(b'B3',"XLSX_CELL_INVALID"),(b'AG2',"XLSX_CELL_ORDER_INVALID"),(b'AAA2',"XLSX_CELL_INVALID")):
            self.refused_workbook(edit(workbook(),{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'B2',coordinate,1)}),code)
        self.refused_workbook(edit(workbook(),{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'<t>Record</t>',b'<r><t>Record</t></r>',1)}),"XLSX_RICH_STRING_UNSUPPORTED")

    def test_every_sheet_is_checked_and_selection_is_exact_visible_and_explicit(self):
        parts=components();parts["xl/workbook.xml"]=parts["xl/workbook.xml"].replace(b'</sheets>',b'<sheet name="Other" sheetId="2" r:id="rId2"/></sheets>')
        parts["xl/_rels/workbook.xml.rels"]=parts["xl/_rels/workbook.xml.rels"].replace(b'</Relationships>',('<Relationship Id="rId2" Type="'+R+'/worksheet" Target="worksheets/sheet2.xml"/></Relationships>').encode())
        parts["xl/worksheets/sheet2.xml"]=components()["xl/worksheets/sheet1.xml"]
        self.check(sample_rows(),sample_records(),kind="xlsx",raw=zip_bytes(parts))
        parts["xl/worksheets/sheet2.xml"]=parts["xl/worksheets/sheet2.xml"].replace(b'<is>',b'<f>1+1</f><is>',1);self.refused_workbook(zip_bytes(parts),"XLSX_ACTIVE_OR_HIDDEN_CONTENT")
        self.refused_workbook(edit(workbook(),{"xl/workbook.xml":lambda b:b.replace(b'name="Records"',b'name="Records" state="hidden"')}),"XLSX_ACTIVE_OR_HIDDEN_CONTENT")
        self.fixture(sample_rows(),kind="xlsx")
        for sheet in ("records","Missing"):self.sheet=sheet;self.api(code=2,error="XLSX_SHEET_NOT_FOUND");self.cli(code=2,error="XLSX_SHEET_NOT_FOUND")
        for sheet in (None,"",32,True):self.api(options=("xlsx",sheet),code=2,error="XLSX_SELECTION_INVALID")

    def test_formula_cache_macro_external_defined_and_hidden_features_refuse(self):
        for markup in (b'<f>1+1</f><v>2</v>',b'<formula>invented</formula>'):
            self.refused_workbook(edit(workbook(),{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'<is>',markup+b'<is>',1)}),"XLSX_ACTIVE_OR_HIDDEN_CONTENT")
        self.refused_workbook(edit(workbook(),{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'<row r="2"',b'<row hidden="1" r="2"')}),"XLSX_ACTIVE_OR_HIDDEN_CONTENT")
        self.refused_workbook(edit(workbook(),{"xl/worksheets/sheet1.xml":lambda b:b.replace(b'</worksheet>',b'<mergeCells/></worksheet>')}),"XLSX_SHEET_FEATURE_UNSUPPORTED")
        for markup in (b'<definedNames><definedName name="invented">1+1</definedName></definedNames>',b'<externalReferences/>'):
            self.refused_workbook(edit(workbook(),{"xl/workbook.xml":lambda b:b.replace(b'</workbook>',markup+b'</workbook>')}),"XLSX_WORKBOOK_FEATURE_UNSUPPORTED")
        for name in ('../fictional.xml','xl/vbaProject.bin','xl/externalLinks/link1.xml','customXml/item1.xml'):
            self.refused_workbook(edit(workbook(),{name:b'Invented blocked bytes'}),"XLSX_PART_UNSUPPORTED")
        self.refused_workbook(edit(workbook(),{"xl/_rels/workbook.xml.rels":lambda b:b.replace(b'Target=',b'TargetMode="External" Target=',1)}),"XLSX_RELATIONSHIP_INVALID")
        self.refused_workbook(edit(workbook(),{"[Content_Types].xml":lambda b:b.replace(b'spreadsheetml.sheet.main+xml',b'macroEnabled.main+xml')}),"XLSX_CONTENT_TYPES_INVALID")

    def test_zip_crc_duplicates_encryption_compression_and_invalid_parts_refuse(self):
        for raw in (b'Invented not ZIP',workbook()[:40]):self.refused_workbook(raw,"XLSX_INVALID")
        parts=components()
        with self.assertWarns(UserWarning):raw=zip_bytes([*parts.items(),('xl/workbook.xml',parts['xl/workbook.xml'])])
        self.refused_workbook(raw,"XLSX_ARCHIVE_INVALID")
        raw=bytearray(workbook());raw[raw.index(b'Fictional') if b'Fictional' in raw else raw.index(b'Record') ]^=1;self.refused_workbook(bytes(raw),"XLSX_INVALID")
        for kind in ("encrypted","compression","symlink"):
            raw=bytearray(workbook())
            if kind=="encrypted":
                for signature,offset in ((b'PK\x03\x04',6),(b'PK\x01\x02',8)):
                    position=raw.index(signature);struct.pack_into('<H',raw,position+offset,struct.unpack_from('<H',raw,position+offset)[0]|1)
            elif kind=="compression":
                for signature,offset in ((b'PK\x03\x04',8),(b'PK\x01\x02',10)):struct.pack_into('<H',raw,raw.index(signature)+offset,99)
            else:struct.pack_into('<I',raw,raw.index(b'PK\x01\x02')+38,(stat.S_IFLNK|0o777)<<16)
            self.refused_workbook(bytes(raw),"XLSX_ARCHIVE_INVALID")
        for name in ('_rels/.rels','xl/workbook.xml','xl/_rels/workbook.xml.rels'):
            self.refused_workbook(edit(workbook(),{name:None}),"XLSX_PART_MISSING")

    def test_xml_declarations_comments_and_structural_character_budgets_refuse(self):
        for prefix,code in (("<!DOCTYPE worksheet [<!ENTITY fictional 'none'>]>","XML_DECLARATION_FORBIDDEN"),("<?fictional none?>","XML_PROCESSING_INSTRUCTION_FORBIDDEN"),("<!-- invented comment -->","XML_COMMENT_FORBIDDEN")):
            for encoding in ('utf-8','utf-16'):
                self.refused_workbook(edit(workbook(),{'xl/worksheets/sheet1.xml':lambda b:(prefix+b.decode()).encode(encoding)}),code)
        for xml in (("<r>"*33+"</r>"*33).encode(),b'<r '+b' '.join(('a'+str(i)+'="x"').encode() for i in range(33))+b'/>',b'<r>'+b'<a/>'*50000+b'</r>'):
            self.refused_workbook(edit(workbook(),{'xl/worksheets/sheet1.xml':xml}),"XML_STRUCTURE_LIMIT")
        namespace='urn:fictional:'+'q'*230;xml=('<r xmlns:k="'+namespace+'">'+('<a k:x="y"/>'*9000)+'</r>').encode()
        self.refused_workbook(edit(workbook(),{'xl/worksheets/sheet1.xml':xml}),"XML_TEXT_LIMIT")

    def test_part_expansion_ratio_total_and_entry_budgets_fail_closed(self):
        self.refused_workbook(edit(workbook(),{'docProps/core.xml':b'x'*2097153}),"XLSX_EXPANSION_LIMIT")
        parts=components();parts['docProps/core.xml']=b'x'*100000;self.refused_workbook(zip_bytes(parts,zipfile.ZIP_DEFLATED),"XLSX_EXPANSION_LIMIT")
        parts=components();payload=random.Random(734).randbytes(16384)*128
        for name in ('docProps/core.xml','docProps/app.xml','xl/styles.xml','xl/sharedStrings.xml','xl/worksheets/sheet2.xml'):parts[name]=payload
        self.refused_workbook(zip_bytes(parts,zipfile.ZIP_DEFLATED),"XLSX_EXPANSION_LIMIT")
        with self.assertWarns(UserWarning):raw=zip_bytes([('xl/workbook.xml',b'x')]*65)
        self.refused_workbook(raw,"XLSX_ARCHIVE_INVALID")

    def test_exact_rows_columns_and_raw_cell_limits_are_not_truncated(self):
        rows=[sample_rows()[0]]+[sample_rows()[1]]*1000;records=[(sample_records()[0][0],list(range(2,1002)))]
        for kind in ('csv','xlsx'):
            self.check(rows,records,kind=kind,api=False);self.fixture(rows+[sample_rows()[1]],kind=kind);self.api(code=2,error='TABLE_LIMIT');self.cli(out=True,code=2,error='TABLE_LIMIT');self.assertFalse(self.output.exists())
        config=mapping([field('ID','id')],unknown='ignore');rows=[['ID']+['ignored-'+str(i) for i in range(31)],['a']+['x']*31]
        for kind in ('csv','xlsx'):self.check(rows,[(dict(id='a'),[2])],config=config,kind=kind,ignored=31)
        for kind,code in (('csv','TABLE_LIMIT'),('xlsx','XLSX_CELL_ORDER_INVALID')):
            self.fixture([rows[0]+['extra'],rows[1]+['x']],config,kind);self.cli(code=2,error=code)
        for kind in ('csv','xlsx'):
            self.check([['ID','Extra'],['a','x'*4096]],[(dict(id='a'),[2])],config=config,kind=kind,ignored=1)
            self.fixture([['ID','Extra'],['a','x'*4097]],config,kind);self.api(code=2,error='TABLE_LIMIT');self.cli(code=2,error='TABLE_LIMIT')

    def test_both_file_byte_limits_and_format_sheet_api_options_are_explicit(self):
        parts=components();parts['docProps/core.xml']=b'x'*2097152;parts['xl/styles.xml']=b'';extra=4194304-len(zip_bytes(parts));self.assertTrue(0<extra<=2097152);parts['xl/styles.xml']=b'y'*extra;raw=zip_bytes(parts);self.assertEqual(len(raw),4194304)
        self.check(sample_rows(),sample_records(),kind='xlsx',raw=raw)
        self.input.write_bytes(raw+b'x');self.api(code=2,error='XLSX_SELECTION_INVALID');self.cli(code=2,error='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT')
        self.fixture(sample_rows());raw=canonical(mapping());padded=raw+b' '*(4194304-len(raw));self.mapping.write_bytes(padded);self.expect(sample_records());self.mapping.write_bytes(padded+b' ')
        self.api(code=2,error='INPUT_LIMIT');self.cli(code=2,error='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT')
        self.fixture(sample_rows())
        for options,code in ((('csv','Records'),'FORMAT_INVALID'),(('CSV',None),'FORMAT_INVALID'),((None,None),'FORMAT_INVALID'),(('xlsx',None),'XLSX_SELECTION_INVALID')):self.api(options=options,code=2,error=code)
        self.invoke([*self.arguments(),'--format','other'],code=2,error='ARGUMENTS_INVALID')

    def test_default_accepted_payload_provenance_and_hashes_are_private_not_anonymized(self):
        config=mapping([field('ID','id'),field('Value','value')]);rows=[['ID','Value'],['Fictional \u03bb \U0001f9ea','<script>literal & data</script>']]
        report=self.check(rows,[(dict(id='Fictional \u03bb \U0001f9ea',value='<script>literal & data</script>'),[2])],config=config)
        self.assertIn('<script>literal & data</script>',json.dumps(report));self.assertEqual(report['accepted'][0]['source_rows'],[2]);self.assertEqual(report['mapping'],config['fields'])
        self.cli(out=True,allow=[self.output]);self.assertEqual(self.output.read_bytes(),canonical(report));self.assertTrue(self.output.read_bytes().isascii());self.assertIn(b'\\ud83e\\uddea',self.output.read_bytes())

    def test_fixed_private_errors_and_selected_role_read_mutations(self):
        for role in ('input','mapping'):
            self.invoke(self.arguments(**{role:self.work/'FICTIONAL_PRIVATE_MISSING'}),code=2)
            for mode in ('short-read-','changed-stat-'):self.cli(out=True,mode=mode+role,code=2,error='INPUT_CHANGED');self.assertFalse(self.output.exists())
        self.cli(mode='output-budget',code=2,error='OUTPUT_LIMIT');self.assertFalse(self.output.exists())

    def test_retained_partial_report_is_not_confirmed_or_replaced(self):
        want=expected(self.input.read_bytes(),self.mapping.read_bytes(),'csv',None,3,sample_records())
        self.cli(out=True,mode='write-failure',code=2,error='INPUT_OR_OUTPUT_REFUSED',allow=[self.output]);self.assertEqual(self.output.read_bytes(),canonical(want)[:5])
        self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),canonical(want)[:5])

    def test_no_overwrite_and_standalone_collection_source_output_guards(self):
        self.output.write_bytes(b'Invented preserved output');self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),b'Invented preserved output')
        for target in (self.input,self.mapping):self.invoke([*self.arguments(),'--out',target],code=2)
        for target in (self.copy/'new.json',self.copy/'toolkit.py'):self.invoke([*self.arguments(),'--out',target],code=2,error='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE')
        collection=self.owned(self.work/'collection');selected=collection/'tools/workbook-intake-checker';selected.mkdir(parents=True);(collection/'systems').mkdir();(collection/'catalog').mkdir();(collection/'catalog/registry.json').write_bytes(b'{}\n')
        for name in RUNTIME:(selected/name).write_bytes((self.copy/name).read_bytes())
        target=collection/'refused.json';self.invoke([*self.arguments(),'--out',target],base=selected,code=2,error='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE');self.assertFalse(target.exists())

    def test_mandatory_hardlink_inputs_and_existing_outputs_are_refused(self):
        for kind in ('csv','xlsx'):
            self.fixture(sample_rows(),kind=kind)
            for role in ('input','mapping'):
                source=getattr(self,role);alias=self.owned(self.work/(kind+'-'+role+'-hardlinked'));os.link(source,alias);self.assertTrue(alias.samefile(source))
                for path in (source,alias):self.invoke(self.arguments(**{role:path}),code=2,error='CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE')
                self.invoke(['--out',alias],mode='generator',code=2);alias.unlink();self.assertEqual(source.stat().st_nlink,1)

    def test_linked_parent_read_and_report_routes_are_refused(self):
        for kind in ('csv','xlsx'):
            self.fixture(sample_rows(),kind=kind);target=self.owned(self.work/(kind+'-target'));target.mkdir();(target/'input').write_bytes(self.input.read_bytes());(target/'mapping').write_bytes(self.mapping.read_bytes());route=self.owned(self.work/(kind+'-route'))
            if os.name=='nt':
                done=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(route),str(target)],capture_output=True,timeout=15);self.assertEqual(done.returncode,0,done.stderr.decode(errors='replace'));self.addCleanup(lambda route=route:route.rmdir() if route.exists() else None)
            else:route.symlink_to(target,target_is_directory=True)
            for role in ('input','mapping'):self.invoke(self.arguments(**{role:route/role}),code=2)
            self.invoke([*self.arguments(),'--out',route/'new.json'],code=2);self.assertFalse((target/'new.json').exists())

    def test_native_leaf_symlink_and_dangling_output_refusal(self):
        for role in ('input','mapping'):
            link=self.owned(self.work/(role+'-linked'));self.symlink(link,getattr(self,role));self.invoke(self.arguments(**{role:link}),code=2)
        for name,target in (('dangling',self.work/'never-created.json'),('source-pointing',self.copy/'never-created.json')):
            target=self.owned(target);self.assertFalse(os.path.lexists(target));route=self.owned(self.work/(name+'.json'));self.symlink(route,target);self.invoke([*self.arguments(),'--out',route],code=2)
            self.assertFalse(os.path.lexists(target),'Refused output must not create a symlink target');self.assertTrue(route.is_symlink())
        for name,target in (('input-pointing',self.input),('mapping-pointing',self.mapping),('runtime-pointing',self.copy/'toolkit.py')):
            raw=target.read_bytes();route=self.owned(self.work/(name+'.json'));self.symlink(route,target);self.invoke([*self.arguments(),'--out',route],code=2);self.assertEqual(target.read_bytes(),raw)

    @unittest.skipUnless(os.name=='nt',WINDOWS_REASON)
    def test_native_windows_path_grammar_and_named_stream_routes(self):
        for role in ('input','mapping'):
            source=getattr(self,role)
            for path in (str(source)+':stream',str(self.work/'CON'),str(source)+'.',str(source)+' ','x:relative','//example.invalid/share'):self.invoke(self.arguments(**{role:path}),code=2)
        self.invoke([*self.arguments(),'--out',str(self.output)+':stream'],code=2)

    @unittest.skipUnless(os.name!='nt',POSIX_REASON)
    def test_native_posix_special_inputs_and_private_report_mode(self):
        fifo=self.owned(self.work/'fictional.fifo');os.mkfifo(fifo);sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.owned(self.work/'s')));self.addCleanup(sock.close)
        for role in ('input','mapping'):
            for path in (fifo,self.work/'s',self.work):self.invoke(self.arguments(**{role:path}),code=2)
        self.cli(out=True,allow=[self.output]);self.assertEqual(stat.S_IMODE(self.output.stat().st_mode),0o600)

    def test_decimal_maximum_scale_signed_zero_and_exact_rejection_under_default_context(self):
        config=mapping([field('ID','id'),field('Amount','amount','decimal')]);rows=[['ID','Amount'],['a','999999999999.999999'],['b','-999999999999.999999'],['c','1000000000000.000000'],['d','-0.000000'],['e','0.000001'],['f','1000000000000.000001'],['g','1.0000001'],['h','1e3'],['i','01.0']]
        records=[(dict(id='a',amount='999999999999.999999'),[2]),(dict(id='b',amount='-999999999999.999999'),[3]),(dict(id='c',amount='1000000000000'),[4]),(dict(id='d',amount='-0'),[5]),(dict(id='e',amount='0.000001'),[6])]
        issues=[dict(row=row,code='VALUE_DECIMAL_INVALID') for row in range(7,11)]
        for kind in ('csv','xlsx'):self.check(rows,records,issues,config,kind)
        config=mapping([field('Amount','amount','decimal')]);rows=[['Amount'],['-0.000'],['0.000'],['0']]
        self.check(rows,[(dict(amount='-0'),[2]),(dict(amount='0'),[3,4])],config=config)


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
    if strict is None:strict=os.name!="nt" or os.environ.get("OUTLANDS_WORKBOOK_INTAKE_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
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
        fictional_workbook_intake_flow_checked=flow_checked,native_file_guards_checked=native_checked,fictional_workbook_intake_flow_test_ids=sorted(FLOW_IDS),native_file_guard_test_ids=sorted(native),
        positive_asserted_test_ids=dict(fictional_workbook_intake_flow_checked=sorted(FLOW_IDS),native_file_guards_checked=sorted(native)),child_xml_bindings_verified=good and flow_checked and native_checked and CopiedCLI.checked_children>0,xml_binding_checked_children=CopiedCLI.checked_children,
        child_arithmetic_context_verified=good and flow_checked and native_checked and CopiedCLI.checked_children>0,arithmetic_context_checked_children=CopiedCLI.checked_children,
        copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,
        **{name:False for name in FALSE_FLAGS})


if __name__=="__main__":raise SystemExit(0 if run_copied_tests()["status"]=="PASS" else 1)
