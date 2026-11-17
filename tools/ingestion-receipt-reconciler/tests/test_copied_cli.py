"""Independent copied receipt recomputation on invented CSV/XLSX and authored previews. MIT."""
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
RUNTIME=("receipts.py","intake.py","run_core.py","toolkit.py","native_windows.py","fictional_workbook.py")
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
FALSE_FLAGS=("real_records_used","real_workbooks_used","imported","source_authority_verified","actual_store_contents_verified",
             "ingestion_run_executed","target_changes_performed","receipt_authority_verified","exactly_once_verified","production_workflows_verified")
FLOW_IDS={"test_copied_cli.CopiedCLI.test_complete_csv_receipt_recomputed_report_and_fresh_output",
          "test_copied_cli.CopiedCLI.test_csv_inline_shared_sources_have_independently_authored_typed_previews",
          "test_copied_cli.CopiedCLI.test_conflicts_rejections_and_empty_source_withhold_readiness"}
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



def counts(n=3,accepted=2,duplicate=1,rejected=0,conflict=0):
    assert n==accepted+duplicate+rejected+conflict
    return dict(input_rows=n,accepted_records=accepted,duplicate_rows=duplicate,rejected_rows=rejected,conflict_rows=conflict)


def authored_preview(raw,mapraw,kind,sheet,accounting,records,issues=(),ignored=0,status='PASS'):
    return dict(format='outlands-intake-preview-v1',status=status,source_sha256=sha(raw),mapping_sha256=sha(mapraw),source_format=kind,sheet=sheet,
        mapping=json.loads(mapraw)['fields'],ignored_columns=ignored,counts=accounting,accepted=[dict(record=record,source_rows=rows) for record,rows in records],
        issues=list(issues),ready_for_explicit_review=status=='PASS',imported=False)


def receipt_value(source,mapraw,preview,kind='csv',sheet=None,accounting=None,key='fictional-receipt'):
    return dict(format='outlands-ingestion-receipt-v1',receipt_id=key,source_sha256=sha(source),mapping_sha256=sha(mapraw),preview_sha256=sha(preview),
        source_format=kind,sheet=sheet,counts=copy.deepcopy(counts() if accounting is None else accounting))


def expected_report(receipt,source,mapraw,preview,observed,issues=()):
    return dict(format='outlands-ingestion-reconciliation-v1',status='REVIEW_REQUIRED' if issues else 'PASS',receipt_id=json.loads(receipt)['receipt_id'],
        receipt_sha256=sha(receipt),source_sha256=sha(source),mapping_sha256=sha(mapraw),supplied_preview_sha256=sha(preview),
        recomputed_preview_sha256=sha(canonical(observed)),observed_counts=observed['counts'],intake_status=observed['status'],issues=sorted(issues),
        row_counts_recomputed=True,ready_for_explicit_review=not issues,source_authority_verified=False,imported=False,target_changes_performed=False)



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
import receipts as r
import intake as a
import run_core as c
import fictional_workbook as g
import toolkit as t
import native_windows as n
for module,name in ((r,'receipts.py'),(a,'intake.py'),(c,'run_core.py'),(g,'fictional_workbook.py'),(t,'toolkit.py'),(n,'native_windows.py')):assert Path(module.__file__).resolve()==base/name
assert r.intake is a and r.t is c.t is a.t is g.t is t and a.zipfile is g.zipfile is zipfile and a.Decimal is decimal.Decimal
assert r.reconcile.__globals__ is r.__dict__ and a.preview.__globals__ is a.__dict__ and t.read.__globals__ is t.__dict__ and t.write_new.__globals__ is t.__dict__
def unused(*args,**kwargs):raise AssertionError('UNUSED_RUN_CORE_PIPELINE_CALLED')
for name in ('ids','items','manifest','buffers','observe','public_name','selected_names'):setattr(c,name,unused)
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
 if mode=='affinity':sys.stdout.write(t.encode(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=6,receipt_recomputation_only=True)).decode());raise SystemExit(0)
 if mode=='generator':
  sys.argv=[str(base/'fictional_workbook.py'),*args];runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('GENERATOR_ENTRYPOINT_DID_NOT_EXIT')
 if mode=='api':
  paths=[Path(value) for value in args];assert len(paths)==4 and all(path.is_absolute() for path in paths)
  try:value=r.reconcile(*(path.read_bytes() for path in paths))
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
 elif mode.startswith('parser-'):
  import struct,zlib
  error={'parser-zlib':zlib.error,'parser-struct':struct.error,'parser-eof':EOFError}[mode]
  def rejected(*args,**kwargs):raise error('FICTIONAL_PRIVATE_PARSER_ERROR')
  a.preview=rejected
 elif mode=='output-budget':t.MAX_OUTPUT=1
 elif mode!='normal':raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
 sys.argv=[str(base/'receipts.py'),*args];runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('RECEIPT_ENTRYPOINT_DID_NOT_EXIT')
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
        self.temp=tempfile.TemporaryDirectory(prefix="receipt-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.assertEqual(self.work.parent,parent);self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();(self.copy/name).write_bytes(raw);self.pins[name]=sha(raw)
        self.source=self.work/'source.dat';self.mapping=self.work/'mapping.json';self.preview=self.work/'preview.json';self.receipt=self.work/'receipt.json';self.output=self.work/'report.json'
        self.fixture()
        self.env={key:value for key,value in os.environ.items() if not key.upper().startswith(("PYTHON","PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHON_COLORS="0",NO_COLOR="1");self.addCleanup(self.runtime_preserved)
    def runtime_preserved(self):
        self.assertEqual({p.name for p in self.copy.iterdir()},set(RUNTIME));self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME},self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")),[])
    def owned(self,path):
        path=Path(path);self.assertTrue(path.is_absolute() and path.resolve().is_relative_to(self.work));return path
    def fixture(self,rows=None,records=None,accounting=None,issues=(),config=None,kind='csv',shared=False,raw=None,ignored=0,status='PASS'):
        rows=sample_rows() if rows is None else rows;records=sample_records() if records is None else records;accounting=counts() if accounting is None else accounting
        self.kind=kind;self.sheet='Records' if kind=='xlsx' else None
        self.source.write_bytes(raw if raw is not None else csv_bytes(rows) if kind=='csv' else workbook(rows,shared))
        self.mapping.write_bytes(canonical(mapping() if config is None else config))
        self.observed=authored_preview(self.source.read_bytes(),self.mapping.read_bytes(),kind,self.sheet,accounting,records,issues,ignored,status)
        self.preview.write_bytes(canonical(self.observed));self.claim=receipt_value(self.source.read_bytes(),self.mapping.read_bytes(),self.preview.read_bytes(),kind,self.sheet,accounting)
        self.assertIsNot(self.claim['counts'],self.observed['counts']);self.save_receipt()
    def save_receipt(self):self.receipt.write_bytes(canonical(self.claim))
    def repin_preview(self):self.claim['preview_sha256']=sha(self.preview.read_bytes());self.save_receipt()
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
        elif value.get('format')=='outlands-ingestion-reconciliation-v1':
            self.assertIs(value['row_counts_recomputed'],True)
            for key in ('source_authority_verified','imported','target_changes_performed'):self.assertIs(value[key],False)
            if value['issues']:self.assertIs(value['ready_for_explicit_review'],False)
            self.assertEqual(set(value),set(expected_report(self.receipt.read_bytes(),self.source.read_bytes(),self.mapping.read_bytes(),self.preview.read_bytes(),self.observed)))
        return value
    def roles(self):return dict(receipt=self.receipt,source=self.source,mapping=self.mapping,preview=self.preview)
    def arguments(self,**overrides):
        values=self.roles();values.update(overrides);return [item for role,path in values.items() for item in ('--'+role,path)]
    def cli(self,*,out=False,overrides=None,**kwargs):return self.invoke([*self.arguments(**({} if overrides is None else overrides)),*(['--out',self.output] if out else [])],**kwargs)
    def api(self,**kwargs):return self.invoke(list(self.roles().values()),mode='api',**kwargs)
    def want(self,issues=()):return expected_report(self.receipt.read_bytes(),self.source.read_bytes(),self.mapping.read_bytes(),self.preview.read_bytes(),self.observed,issues)
    def expect(self,issues=(),api=True):
        want=self.want(issues);code=1 if issues else 0;self.assertEqual(self.cli(code=code),want)
        if api:self.assertEqual(self.api(code=code),want)
        return want
    def refused_source(self,raw,code,kind='xlsx'):
        self.fixture(raw=raw,kind=kind);self.cli(out=True,code=2,error=code);self.api(code=2,error=code);self.assertFalse(self.output.exists())
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            strict=self.strict_links if self.strict_links is not None else os.name!="nt" or os.environ.get("OUTLANDS_INGESTION_RECEIPT_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
            actual=os.name=="nt" and getattr(error,"winerror",None)==1314
            if actual and not strict:
                self.assertEqual(self.id(),LINK_ID);self.assertFalse(directory);self.native_events.append(dict(test=self.id(),reason=LINK_REASON,policy="actual_windows_1314",actual_windows_1314=True,winerror=1314,strict=False,provenance="test_copied_cli.CopiedCLI.symlink/caught-OSError"));self.skipTest(LINK_REASON)
            raise



    def test_copied_affinity_and_actual_four_argument_entrypoint_help_are_inert(self):
        self.assertEqual(self.invoke(mode='affinity'),dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=6,receipt_recomputation_only=True))
        text=self.invoke(['--help'],text=True)
        for role in self.roles():self.assertIn('--'+role,text)
        self.invoke(code=2,error='ARGUMENTS_INVALID');self.invoke(['--unknown','FICTIONAL_PRIVATE_SENTINEL'],code=2,error='ARGUMENTS_INVALID')

    def test_complete_csv_receipt_recomputed_report_and_fresh_output(self):
        report=self.expect();self.assertEqual(report['observed_counts'],counts())
        self.assertEqual(self.cli(out=True,allow=[self.output]),dict(status='PASS',report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))
        self.assertIs(report['row_counts_recomputed'],True);self.assertIs(report['source_authority_verified'],False)

    def test_fictional_generator_actual_entrypoint_and_generated_xlsx_recompute(self):
        target=self.owned(self.work/'generated.xlsx');value=self.invoke(['--out',target],mode='generator',allow=[target]);raw=target.read_bytes()
        self.assertEqual(value,dict(status='PASS',fictional=True,bytes=len(raw),sha256=sha(raw)))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:self.assertEqual({name:archive.read(name) for name in archive.namelist()},components())
        self.fixture(raw=raw,kind='xlsx');self.expect()
        self.invoke(['--out',target],mode='generator',code=2)

    def test_csv_inline_shared_sources_have_independently_authored_typed_previews(self):
        hashes=[]
        for kind,shared in (('csv',False),('xlsx',False),('xlsx',True)):
            self.fixture(kind=kind,shared=shared);report=self.expect();hashes.append(report['source_sha256'])
            self.assertEqual(report['observed_counts'],counts());self.assertNotIn('accepted',report)
        self.assertEqual(len(set(hashes)),3)

    def test_all_five_types_optional_null_decimal_scale_and_signed_zero_recompute(self):
        config=mapping([field('Record','record_id'),field('Units','units','integer'),field('Price','price','decimal'),field('Active','active','boolean'),field('Due','due','date'),field('Note','note','text',False)])
        rows=[['Record','Units','Price','Active','Due','Note'],['fictional-a','1','1.230000','true','2032-02-29',''],['fictional-b','-1000000000000','-0.000000','false','2030-01-01','literal $HOME']]
        records=[(dict(record_id='fictional-a',units=1,price='1.23',active=True,due='2032-02-29',note=None),[2]),(dict(record_id='fictional-b',units=-1000000000000,price='-0',active=False,due='2030-01-01',note='literal $HOME'),[3])]
        for kind in ('csv','xlsx'):
            self.fixture(rows,records,counts(2,2,0),config=config,kind=kind);self.expect()

    def test_each_raw_pin_mismatch_is_independent_and_all_are_reported(self):
        for key in ('source_sha256','mapping_sha256','preview_sha256'):
            self.fixture();self.claim[key]='0'*64;self.save_receipt();self.expect([key.upper()+'_MISMATCH'])
        self.fixture()
        for key in ('source_sha256','mapping_sha256','preview_sha256'):self.claim[key]='0'*64
        self.save_receipt();self.expect(['SOURCE_SHA256_MISMATCH','MAPPING_SHA256_MISMATCH','PREVIEW_SHA256_MISMATCH'])

    def test_preview_whitespace_bom_and_receipt_reserialization_keep_typed_meaning(self):
        baseline=self.expect();value=json.loads(self.preview.read_bytes());self.preview.write_bytes(b'\xef\xbb\xbf'+json.dumps(value,indent=2).encode()+b'\n')
        self.expect(['PREVIEW_SHA256_MISMATCH']);self.repin_preview();changed=self.expect()
        self.assertNotEqual(changed['supplied_preview_sha256'],changed['recomputed_preview_sha256']);self.assertEqual(changed['recomputed_preview_sha256'],baseline['recomputed_preview_sha256'])
        before=changed['receipt_sha256'];self.receipt.write_bytes(json.dumps(self.claim,indent=2).encode()+b'\n');after=self.expect();self.assertNotEqual(before,after['receipt_sha256'])

    def test_mapping_and_csv_raw_reserialization_require_fresh_actual_preview_pins(self):
        raw=csv_bytes(sample_rows()).replace(b'\n',b'\r\n');self.fixture(raw=raw)
        mapraw=json.dumps(mapping(),indent=2).encode()+b'\n';self.mapping.write_bytes(mapraw)
        self.observed=authored_preview(raw,mapraw,'csv',None,counts(),sample_records());self.preview.write_bytes(canonical(self.observed));self.claim=receipt_value(raw,mapraw,self.preview.read_bytes());self.save_receipt();self.expect()
        self.assertEqual(self.observed['accepted'],[dict(record=record,source_rows=rows) for record,rows in sample_records()])

    def test_forged_receipt_counts_and_declared_accounting_disagreement_hold(self):
        self.claim['counts']=counts(3,1,2);self.save_receipt();self.expect(['RECEIPT_COUNT_MISMATCH'])
        self.fixture();baseline=canonical(self.observed);self.claim['counts']['input_rows']=4;self.save_receipt();self.assertEqual(canonical(self.observed),baseline);self.expect(['DECLARED_ACCOUNTING_MISMATCH','RECEIPT_COUNT_MISMATCH'])
        self.fixture();self.claim['counts']['accepted_records']=True;self.save_receipt();self.cli(code=2,error='INTEGER_INVALID');self.api(code=2,error='INTEGER_INVALID')

    def test_forged_preview_values_provenance_flags_and_unknown_fields_cannot_match(self):
        for change in ('value','provenance','flag','unknown','missing'):
            self.fixture();value=copy.deepcopy(self.observed)
            if change=='value':value['accepted'][0]['record']['units']=999
            elif change=='provenance':value['accepted'][0]['source_rows']=[999]
            elif change=='flag':value['ready_for_explicit_review']=False
            elif change=='unknown':value['extra']='FICTIONAL_PRIVATE_EXTRA'
            else:value['accepted'].pop()
            self.preview.write_bytes(canonical(value));self.repin_preview();self.expect(['PREVIEW_CONTENT_MISMATCH'])

    def test_canonical_typed_json_distinguishes_boolean_integer_even_when_python_equal(self):
        rows=[['Record','Units','Due','Active'],['sample-a','1','2030-01-10','true']];records=[(dict(record_id='sample-a',units=1,due='2030-01-10',active=True),[2])]
        for key in ('imported','active','units'):
            self.fixture(rows,records,counts(1,1,0));value=copy.deepcopy(self.observed)
            if key=='imported':value['imported']=0
            elif key=='active':value['accepted'][0]['record']['active']=1
            else:value['accepted'][0]['record']['units']=True
            self.assertEqual(value,self.observed);self.assertNotEqual(canonical(value),canonical(self.observed))
            self.preview.write_bytes(canonical(value));self.repin_preview();self.expect(['PREVIEW_CONTENT_MISMATCH'])

    def test_conflicts_rejections_and_empty_source_withhold_readiness(self):
        rows=sample_rows()+[['sample-a','8','2030-01-10','true'],['sample-c','bad','2030-01-12','true']]
        records=[(dict(record_id='sample-b',units=7,due='2030-01-11',active=False),[3])]
        issues=[dict(row=2,code='IDENTITY_CONFLICT'),dict(row=4,code='IDENTITY_CONFLICT'),dict(row=5,code='IDENTITY_CONFLICT'),dict(row=6,code='VALUE_INTEGER_INVALID')]
        self.fixture(rows,records,counts(5,1,0,1,3),issues,status='REVIEW_REQUIRED');report=self.expect(['INTAKE_REQUIRES_REVIEW']);self.assertFalse(report['ready_for_explicit_review'])
        self.fixture([sample_rows()[0]],[],counts(0,0,0),status='REVIEW_REQUIRED');self.expect(['INTAKE_REQUIRES_REVIEW'])

    def test_receipt_schema_identifiers_format_sheet_counts_and_json_refuse(self):
        variants=[('format','wrong','RECEIPT_FORMAT_INVALID'),('receipt_id','r'*49,'IDENTIFIER_INVALID'),('source_sha256','A'*64,'HASH_INVALID'),('source_format','xml','SOURCE_FORMAT_INVALID'),('sheet','Records','SHEET_SELECTION_INVALID')]
        for key,value,code in variants:
            self.fixture();self.claim[key]=value;self.save_receipt();self.cli(code=2,error=code);self.api(code=2,error=code)
        self.fixture();self.claim['receipt_id']='r'*48;self.save_receipt();self.expect()
        for role in ('receipt','mapping','preview'):
            self.fixture();getattr(self,role).write_bytes(b'{"x":1,"x":2}');self.cli(code=2,error='JSON_DUPLICATE_KEY');self.api(code=2,error='JSON_DUPLICATE_KEY')
        for raw,code in ((b'NaN','JSON_INTEGER_OR_STRING_REQUIRED'),(b'"\\ud800"','JSON_INVALID'),(b'['*34+b'0'+b']'*34,'JSON_STRUCTURE_LIMIT')):
            self.fixture();self.receipt.write_bytes(raw);self.cli(code=2,error=code);self.api(code=2,error=code)

    def test_csv_header_utf8_and_explicit_mapping_failures_are_fixed(self):
        for raw,code in ((b'Record,Record\na,b\n','HEADER_INVALID'),(b'Other,Units\na,1\n','MAPPED_HEADER_MISSING'),(b'\xff','CSV_INVALID'),(b'Record\x00,Units\na,1\n','CSV_INVALID')):
            self.refused_source(raw,code,kind='csv')
        self.fixture();config=mapping();config['fields'][1]['source']='Record';self.mapping.write_bytes(canonical(config));self.cli(code=2,error='MAP_DUPLICATE_FIELD');self.api(code=2,error='MAP_DUPLICATE_FIELD')
        self.fixture();config=mapping();config['identity']=['missing'];self.mapping.write_bytes(canonical(config));self.cli(code=2,error='MAP_IDENTITY_INVALID')

    def test_xlsx_formulas_hidden_macro_and_external_relationships_refuse(self):
        raw=workbook()
        cases=[('xl/worksheets/sheet1.xml',lambda b:b.replace(b'<is><t>12</t></is>',b'<f>1+11</f><v>12</v>'),'XLSX_ACTIVE_OR_HIDDEN_CONTENT'),('xl/workbook.xml',lambda b:b.replace(b'name="Records"',b'name="Records" state="hidden"'),'XLSX_ACTIVE_OR_HIDDEN_CONTENT'),('xl/_rels/workbook.xml.rels',lambda b:b.replace(b'Target=',b'TargetMode="External" Target='),'XLSX_RELATIONSHIP_INVALID'),('[Content_Types].xml',lambda b:b.replace(b'application/xml',b'application/vnd.ms-excel.sheet.macroEnabled'),'XLSX_CONTENT_TYPES_INVALID')]
        for path,change,code in cases:self.refused_source(edit(raw,{path:change}),code)

    def test_xlsx_zip_crc_path_duplicates_and_xml_declarations_refuse(self):
        raw=workbook();self.refused_source(edit(raw,{'../escape.xml':b'<x/>'}),'XLSX_PART_UNSUPPORTED')
        parts=list(components().items())
        with self.assertWarns(UserWarning):duplicate=zip_bytes(parts+[parts[0]])
        self.refused_source(duplicate,'XLSX_ARCHIVE_INVALID')
        damaged=bytearray(raw)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info=archive.getinfo('xl/worksheets/sheet1.xml');offset=info.header_offset+30+len(info.filename.encode())+len(info.extra)
        damaged[offset]^=1;self.refused_source(bytes(damaged),'XLSX_INVALID')
        for prefix,code in ((b'<!DOCTYPE worksheet [<!ENTITY x "x">]>','XML_DECLARATION_FORBIDDEN'),(b'<!--fictional-->','XML_COMMENT_FORBIDDEN')):self.refused_source(edit(raw,{'xl/worksheets/sheet1.xml':lambda b:prefix+b}),code)
        self.refused_source(edit(raw,{'xl/styles.xml':b' '*2097153}),'XLSX_EXPANSION_LIMIT')

    def test_exact_thousand_logical_rows_and_one_over_are_not_truncated(self):
        rows=[sample_rows()[0]]+[sample_rows()[1]]*1000;records=[(sample_records()[0][0],list(range(2,1002)))]
        self.fixture(rows,records,counts(1000,1,999));self.expect(api=False)
        self.fixture(raw=csv_bytes(rows+[sample_rows()[1]]));self.cli(code=2,error='TABLE_LIMIT');self.api(code=2,error='TABLE_LIMIT')

    def test_all_four_input_byte_limits_and_exact_json_caps_are_independent(self):
        for role in ('receipt','mapping','preview'):
            self.fixture();path=getattr(self,role);raw=path.read_bytes();path.write_bytes(raw+b' '*(4194304-len(raw)))
            if role=='mapping':
                self.observed=authored_preview(self.source.read_bytes(),self.mapping.read_bytes(),'csv',None,counts(),sample_records());self.preview.write_bytes(canonical(self.observed));self.claim=receipt_value(self.source.read_bytes(),self.mapping.read_bytes(),self.preview.read_bytes());self.save_receipt()
            elif role=='preview':self.repin_preview()
            self.expect(api=False);path.write_bytes(path.read_bytes()+b' ')
            self.cli(code=2,error='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT');self.api(code=2,error='INPUT_LIMIT')
        header=sample_rows()[0]+['Ignored0','Ignored1'];rows=[header]+[sample_rows()[1]+['',''] for _ in range(1000)];remaining=4194304-len(csv_bytes(rows))
        for row in rows[1:]:
            for index in (4,5):amount=min(4096,remaining);row[index]='x'*amount;remaining-=amount
        raw=csv_bytes(rows);self.assertEqual(remaining,0);self.assertEqual(len(raw),4194304)
        self.fixture(rows,[(sample_records()[0][0],list(range(2,1002)))],counts(1000,1,999),config=mapping(unknown='ignore'),raw=raw,ignored=2);self.expect(api=False)
        self.source.write_bytes(raw+b' ');self.cli(code=2,error='INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT');self.api(code=2,error='INPUT_LIMIT')

    def test_fixed_private_errors_and_each_selected_role_read_mutation(self):
        for role in self.roles():
            self.cli(overrides={role:self.work/'FICTIONAL_PRIVATE_MISSING'},code=2)
            for prefix in ('short-read-','changed-stat-'):self.cli(mode=prefix+role,code=2,error='INPUT_CHANGED')
        self.cli(mode='output-budget',code=2,error='OUTPUT_LIMIT')

    def test_controlled_intake_parser_errors_are_fixed_without_bypassing_normal_flow(self):
        for mode in ('parser-zlib','parser-struct','parser-eof'):self.cli(mode=mode,code=2,error='INTAKE_REFUSED')
        self.expect()

    def test_reconciliation_summary_omits_typed_values_and_provenance_but_is_private(self):
        literal='FICTIONAL_PRIVATE_TEXT_\u03bb_\U0001f9ea_$HOME_<script>'
        rows=[['Record','Units','Due','Active'],[literal,'12','2030-01-10','true']];records=[(dict(record_id=literal,units=12,due='2030-01-10',active=True),[2])]
        self.fixture(rows,records,counts(1,1,0));report=self.expect();encoded=canonical(report)
        self.assertNotIn(literal.encode(),encoded)
        for key in ('accepted','record','source_rows','mapping','issues_by_row'):self.assertNotIn(key,report)
        self.assertEqual(report['receipt_id'],'fictional-receipt');self.assertEqual(report['source_sha256'],sha(self.source.read_bytes()))

    def test_source_format_and_sheet_selection_are_explicit_not_extension_guesses(self):
        self.fixture();self.assertEqual(self.source.suffix,'.dat');self.expect()
        self.fixture(kind='xlsx');self.expect();self.claim['sheet']='records';self.save_receipt();self.cli(code=2,error='XLSX_SHEET_NOT_FOUND');self.api(code=2,error='XLSX_SHEET_NOT_FOUND')
        self.fixture(kind='xlsx');self.claim['sheet']=None;self.save_receipt();self.cli(code=2,error='SHEET_SELECTION_INVALID')
        self.fixture();self.claim['source_format']='xlsx';self.claim['sheet']='Records';self.save_receipt();self.cli(code=2,error='XLSX_INVALID')

    def test_object_order_is_insignificant_but_accepted_array_order_is_exact(self):
        value=dict(reversed(list(self.observed.items())));self.preview.write_bytes(json.dumps(value,indent=1).encode());self.repin_preview();self.expect()
        value=copy.deepcopy(self.observed);value['accepted'].reverse();self.preview.write_bytes(canonical(value));self.repin_preview();self.expect(['PREVIEW_CONTENT_MISMATCH'])

    def test_retained_partial_report_is_not_confirmed_or_replaced(self):
        want=self.want();self.cli(out=True,mode='write-failure',code=2,error='INPUT_OR_OUTPUT_REFUSED',allow=[self.output])
        self.assertEqual(self.output.read_bytes(),canonical(want)[:5]);self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),canonical(want)[:5])

    def test_no_overwrite_and_standalone_collection_source_output_guards(self):
        self.output.write_bytes(b'Invented preserved report');self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),b'Invented preserved report')
        for source in self.roles().values():self.invoke([*self.arguments(),'--out',source],code=2)
        for target in (self.copy/'new.json',self.copy/'toolkit.py'):self.invoke([*self.arguments(),'--out',target],code=2,error='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE')
        collection=self.owned(self.work/'collection');chosen=collection/'tools/ingestion-receipt-reconciler';chosen.mkdir(parents=True);(collection/'systems').mkdir();(collection/'catalog').mkdir();(collection/'catalog/registry.json').write_bytes(b'{}\n')
        for name in RUNTIME:(chosen/name).write_bytes((self.copy/name).read_bytes())
        target=collection/'refused.json';self.invoke([*self.arguments(),'--out',target],base=chosen,code=2,error='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE');self.assertFalse(target.exists())

    def test_mandatory_hardlink_inputs_and_existing_outputs_are_refused(self):
        for role,source in self.roles().items():
            alias=self.owned(self.work/(role+'-hardlink.json'));os.link(source,alias);self.assertTrue(alias.samefile(source))
            for path in (source,alias):self.cli(overrides={role:path},code=2,error='CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE')
            alias.unlink();self.assertEqual(source.stat().st_nlink,1)
        original=self.owned(self.work/'old-report.json');original.write_bytes(b'Invented existing bytes');alias=self.owned(self.work/'report-hardlink.json');os.link(original,alias)
        self.assertTrue(alias.samefile(original));self.invoke([*self.arguments(),'--out',alias],code=2);self.assertEqual(original.read_bytes(),b'Invented existing bytes')

    def test_linked_parent_read_and_report_routes_are_refused(self):
        target=self.owned(self.work/'target');target.mkdir();route=self.owned(self.work/'route')
        for role,source in self.roles().items():(target/(role+'.dat')).write_bytes(source.read_bytes())
        if os.name=='nt':
            done=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(route),str(target)],capture_output=True,timeout=15);self.assertEqual(done.returncode,0,done.stderr.decode(errors='replace'));self.addCleanup(lambda:route.rmdir() if route.exists() else None)
        else:route.symlink_to(target,target_is_directory=True)
        for role in self.roles():self.cli(overrides={role:route/(role+'.dat')},code=2)
        self.invoke([*self.arguments(),'--out',route/'new.json'],code=2);self.assertFalse((target/'new.json').exists())

    def test_native_leaf_symlink_and_dangling_output_refusal(self):
        for role,source in self.roles().items():
            link=self.owned(self.work/(role+'-linked.dat'));self.symlink(link,source);self.cli(overrides={role:link},code=2)
        for name,target in (('dangling',self.work/'never-created.json'),('source-pointing',self.copy/'never-created.json')):
            target=self.owned(target);self.assertFalse(os.path.lexists(target));route=self.owned(self.work/(name+'.json'));self.symlink(route,target);self.invoke([*self.arguments(),'--out',route],code=2)
            self.assertFalse(os.path.lexists(target),'Refused output must not create a symlink target');self.assertTrue(route.is_symlink())
        for name,target in (('receipt-pointing',self.receipt),('source-file-pointing',self.source),('mapping-pointing',self.mapping),('preview-pointing',self.preview),('runtime-pointing',self.copy/'toolkit.py')):
            raw=target.read_bytes();route=self.owned(self.work/(name+'.json'));self.symlink(route,target);self.invoke([*self.arguments(),'--out',route],code=2);self.assertEqual(target.read_bytes(),raw)

    @unittest.skipUnless(os.name=='nt',WINDOWS_REASON)
    def test_native_windows_path_grammar_and_named_stream_routes(self):
        for role,source in self.roles().items():
            for path in (str(source)+':stream',str(self.work/'CON'),str(source)+'.',str(source)+' ','x:relative','//example.invalid/share'):self.cli(overrides={role:path},code=2)
        self.invoke([*self.arguments(),'--out',str(self.output)+':stream'],code=2)

    @unittest.skipUnless(os.name!='nt',POSIX_REASON)
    def test_native_posix_special_inputs_and_private_report_mode(self):
        fifo=self.owned(self.work/'fictional.fifo');os.mkfifo(fifo);sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.owned(self.work/'s')));self.addCleanup(sock.close)
        for role in self.roles():
            for source in (fifo,self.work/'s',self.work):self.cli(overrides={role:source},code=2)
        self.cli(out=True,allow=[self.output]);self.assertEqual(stat.S_IMODE(self.output.stat().st_mode),0o600)

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
    if strict is None:strict=os.name!="nt" or os.environ.get("OUTLANDS_INGESTION_RECEIPT_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
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
        fictional_ingestion_receipt_flow_checked=flow_checked,native_file_guards_checked=native_checked,fictional_ingestion_receipt_flow_test_ids=sorted(FLOW_IDS),native_file_guard_test_ids=sorted(native),
        positive_asserted_test_ids=dict(fictional_ingestion_receipt_flow_checked=sorted(FLOW_IDS),native_file_guards_checked=sorted(native),row_counts_recomputed=sorted(FLOW_IDS)),child_xml_bindings_verified=good and flow_checked and native_checked and CopiedCLI.checked_children>0,xml_binding_checked_children=CopiedCLI.checked_children,
        child_arithmetic_context_verified=good and flow_checked and native_checked and CopiedCLI.checked_children>0,arithmetic_context_checked_children=CopiedCLI.checked_children,
        copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,
        row_counts_recomputed=flow_checked,copied_receipt_recomputation_only=True,**{name:False for name in FALSE_FLAGS})


if __name__=="__main__":raise SystemExit(0 if run_copied_tests()["status"]=="PASS" else 1)
