"""Independent copied document-intake consumers on invented tables/maps; no Office, import or extraction. MIT."""
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
RUNTIME=("document_intake.py","docx_core.py","intake.py","toolkit.py","native_windows.py","fictional_docx.py")
W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P="http://schemas.openxmlformats.org/package/2006/relationships"
C="http://schemas.openxmlformats.org/package/2006/content-types"
MAIN="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
WINDOWS_ID="test_copied_cli.CopiedCLI.test_native_windows_path_grammar_and_named_stream_routes"
WINDOWS_REASON="Native Windows path-grammar fixtures"
POSIX_ID="test_copied_cli.CopiedCLI.test_native_posix_special_inputs_and_private_report_mode"
POSIX_REASON="Native POSIX special-file and mode fixtures"
LINK_ID="test_copied_cli.CopiedCLI.test_native_leaf_symlink_and_dangling_output_refusal"
LINK_REASON="Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS={(POSIX_ID,POSIX_REASON)}
REQUIRED_POSIX_SKIPS={(WINDOWS_ID,WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS={(LINK_ID,LINK_REASON)}
FALSE_FLAGS=("real_documents_used","document_properties_exported","external_resources_followed","document_executed",
             "office_processes_started","archives_extracted","visible_layout_verified","general_word_compatibility_verified","production_workflows_verified",
             "imported","source_transformed")
FLOW_IDS={"test_copied_cli.CopiedCLI.test_generator_variants_pass_and_review_hold_are_exact",
          "test_copied_cli.CopiedCLI.test_five_explicit_types_and_four_distinct_provenance_hashes",
          "test_copied_cli.CopiedCLI.test_conflicts_hold_all_members_without_hiding_independent_records"}
COMMON_NATIVE_IDS={"test_copied_cli.CopiedCLI.test_no_overwrite_aliases_and_standalone_collection_source_protection",
                   "test_copied_cli.CopiedCLI.test_retained_partial_report_does_not_approve_or_replace_outputs",
                   "test_copied_cli.CopiedCLI.test_both_input_roles_require_single_link_regular_files",
                   "test_copied_cli.CopiedCLI.test_linked_parents_of_both_inputs_and_output_are_refused"}



def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(",",":"))+"\n").encode()


def zip_bytes(parts,compression=zipfile.ZIP_STORED):
    output=io.BytesIO()
    with zipfile.ZipFile(output,"w") as archive:
        rows=parts.items() if isinstance(parts,dict) else parts
        for name,raw in rows:
            info=zipfile.ZipInfo(name,date_time=(2030,1,1,0,0,0));info.compress_type=compression
            archive.writestr(info,raw)
    return output.getvalue()


def components(blocks=None,*,author="Fictional Author",bold=False):
    if blocks is None:blocks=sample_blocks()
    def paragraph(value):
        return '<w:p><w:r>'+('<w:rPr><w:b/></w:rPr>' if bold else '')+'<w:t xml:space="preserve">'+escape(value)+'</w:t></w:r></w:p>'
    body=[]
    for block in blocks:
        if block["kind"]=="paragraph":body.append(paragraph(block["text"]))
        else:body.append('<w:tbl>'+''.join('<w:tr>'+''.join('<w:tc>'+paragraph(value)+'</w:tc>' for value in row)+'</w:tr>' for row in block["rows"] )+'</w:tbl>')
    return {
        "[Content_Types].xml":('<Types xmlns="'+C+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="'+MAIN+'"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>').encode(),
        "_rels/.rels":('<Relationships xmlns="'+P+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="word/document.xml"/><Relationship Id="core" Type="'+P+'/metadata/core-properties" Target="docProps/core.xml"/></Relationships>').encode(),
        "word/document.xml":('<w:document xmlns:w="'+W+'"><w:body>'+''.join(body)+'</w:body></w:document>').encode(),
        "docProps/core.xml":('<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>'+escape(author)+'</dc:creator></cp:coreProperties>').encode()}


def sample_blocks():
    return [dict(kind="paragraph",text="Fictional intake example."),dict(kind="table",rows=[
        ["Record","Units","Due","Active"],["sample-a","12","2030-01-10","true"],
        ["sample-b","7","2030-01-11","false"],["sample-a","12","2030-01-10","true"]])]


def document(blocks=None,**options):return zip_bytes(components(blocks,**options))


def edit(raw,changes):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:parts={name:archive.read(name) for name in archive.namelist()}
    for name,change in changes.items():
        if change is None:parts.pop(name,None)
        else:parts[name]=change(parts.get(name,b"")) if callable(change) else change
    return zip_bytes(parts)



def field(source,target,kind="text",required=True):return dict(source=source,target=target,type=kind,required=required)


def mapping(fields=None,identity=None,unknown="reject"):
    if fields is None:fields=[field("Record","record_id"),field("Units","units","integer"),field("Due","due","date"),field("Active","active","boolean")]
    return dict(format="outlands-table-map-v1",identity=[fields[0]["target"]] if identity is None else identity,unknown_columns=unknown,fields=fields)


def sample_records(variant="before"):
    if variant=="after":return [(dict(record_id="sample-a",units=14,due="2030-01-10",active=True),[2]),(dict(record_id="sample-c",units=5,due="2030-01-12",active=True),[3])]
    return [(dict(record_id="sample-a",units=12,due="2030-01-10",active=True),[2,4]),(dict(record_id="sample-b",units=7,due="2030-01-11",active=False),[3])]


def normalized(rows):
    stream=io.StringIO(newline="");csv.writer(stream,lineterminator="\n").writerows(rows);return stream.getvalue().encode()


def blocks_model(blocks):
    rows=[];pcount=tcount=0
    for block in blocks:
        if block["kind"]=="paragraph":
            pcount+=1;rows.append(dict(id="paragraph-"+str(pcount),position=len(rows)+1,kind="paragraph",text=block["text"]))
        else:
            tcount+=1;rows.append(dict(id="table-"+str(tcount),position=len(rows)+1,kind="table",rows=block["rows"]))
    return rows


def expected(raw,mapping_raw,blocks,records,issues=(),*,selected="table-1",ignored=0):
    model=blocks_model(blocks);table=next(row for row in model if row["id"]==selected)
    conflicts=sum(issue["code"]=="IDENTITY_CONFLICT" for issue in issues)
    counts=dict(input_rows=len(table["rows"])-1,accepted_records=len(records),duplicate_rows=sum(len(rows)-1 for record,rows in records),rejected_rows=len(issues)-conflicts,conflict_rows=conflicts)
    assert counts["input_rows"]==counts["accepted_records"]+counts["duplicate_rows"]+counts["rejected_rows"]+counts["conflict_rows"]
    status="PASS" if records and not issues else "REVIEW_REQUIRED"
    return dict(format="outlands-document-intake-v1",status=status,source_sha256=sha(raw),mapping_sha256=sha(mapping_raw),source_format="docx-table",
        mapping=json.loads(mapping_raw)["fields"],ignored_columns=ignored,counts=counts,accepted=[dict(record=record,source_rows=rows) for record,rows in records],
        issues=list(issues),ready_for_explicit_review=status=="PASS",imported=False,normalized_table_sha256=sha(normalized(table["rows"])),content_sha256=sha(canonical(model)),
        selected_table=selected,table_position=table["position"],source_row_basis="ONE_BASED_SELECTED_TABLE_ROW",document_properties_exported=False,source_transformed=False)


CHILD=r'''
import _elementtree,hashlib,importlib.metadata,json,os,pyexpat,runpy,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();mode=sys.argv[2];args=sys.argv[3:];sys.path.insert(0,str(base))
def audit(event,values):
 if event.startswith(('socket.','subprocess.','os.startfile')) or event in ('os.system','webbrowser.open'):
  raise AssertionError('UNEXPECTED_NETWORK_OFFICE_OR_PROCESS')
sys.addaudithook(audit)
def no_extract(*a,**kw):raise AssertionError('INPUT_ARCHIVE_EXTRACTION_FORBIDDEN')
zipfile.ZipFile.extract=zipfile.ZipFile.extractall=no_extract
import document_intake as a
import docx_core as d
import intake as i
import fictional_docx as g
import toolkit as t
import native_windows as n
for module,name in ((a,'document_intake.py'),(d,'docx_core.py'),(i,'intake.py'),(g,'fictional_docx.py'),(t,'toolkit.py'),(n,'native_windows.py')):
 assert Path(module.__file__).resolve()==base/name
assert a.docx_core is d and a.intake is i and a.t is d.t is i.t is g.t is t
assert t.ET.XMLParser is _elementtree.XMLParser and t.ET.TreeBuilder is _elementtree.TreeBuilder
assert t.XMLBuilder.__mro__[1] is _elementtree.TreeBuilder and len(pyexpat.version_info)==3
assert a.preview.__globals__ is a.__dict__ and i.preview.__globals__ is i.__dict__ and d.extract.__globals__ is d.__dict__
def no_xlsx(*a,**kw):raise AssertionError('DOCX_ADAPTER_MUST_USE_ONLY_SELECTED_IN_MEMORY_CSV')
i.xlsx_rows=no_xlsx
if mode=='affinity':
 sys.stdout.write(t.encode(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=6)).decode());raise SystemExit(0)
if mode=='generator':
 sys.argv=[str(base/'fictional_docx.py'),*args]
 runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('GENERATOR_ENTRYPOINT_DID_NOT_EXIT')
if mode=='api':
 document=Path(args[0]);mapping=Path(args[1]);assert document.is_absolute() and mapping.is_absolute()
 try:value=a.preview(document.read_bytes(),mapping.read_bytes(),json.loads(args[2]))
 except t.Rejected as error:sys.stdout.write(t.encode(dict(status='ERROR',code=str(error))).decode());raise SystemExit(2)
 sys.stdout.write(t.encode(value).decode());raise SystemExit(0 if value['status']=='PASS' else 1)
if mode in ('short-read','short-mapping-read','changed-stat','changed-mapping-stat'):
 original_read=os.read;original_stat=os.fstat;changed=set()
 inode=os.stat(args[args.index('--mapping')+1]).st_ino if 'mapping' in mode else None
 def selected(fd):return inode is None or original_stat(fd).st_ino==inode
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
sys.argv=[str(base/'document_intake.py'),*args]
runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('INTAKE_ENTRYPOINT_DID_NOT_EXIT')
'''


class CopiedCLI(unittest.TestCase):
    strict_links=None
    native_events=[]
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
        self.temp=tempfile.TemporaryDirectory(prefix="document-intake-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.assertEqual(self.work.parent,parent);self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();(self.copy/name).write_bytes(raw);self.pins[name]=sha(raw)
        self.input=self.work/"fictional.docx";self.input.write_bytes(document());self.mapping=self.work/"mapping.json";self.mapping.write_bytes(canonical(mapping()));self.output=self.work/"summary.json"
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
        self.assertEqual(done.returncode,code,done.stderr.decode(errors="replace")[:3000]);self.assertEqual(done.stderr,b"")
        for private in (str(self.work).encode(),b"FICTIONAL_PRIVATE",b"Traceback"):self.assertNotIn(private,done.stdout)
        after=self.snapshot();self.assertEqual(before,{key:after.get(key) for key in before})
        allowed={self.owned(path).relative_to(self.work).as_posix() for path in allow};self.assertEqual(sorted(after.keys()-before.keys()-allowed),[],"Unexpected relative file creation")
        self.runtime_preserved()
        if text:return done.stdout.decode("ascii")
        value=json.loads(done.stdout)
        if code==2:
            self.assertEqual(set(value),{"status","code"});self.assertEqual(value["status"],"ERROR");self.assertRegex(value["code"],r"^[A-Z][A-Z0-9_]{0,100}$")
            if error is not None:self.assertEqual(value["code"],error)
        elif value.get("format")=="outlands-document-intake-v1":
            for key in ("document_properties_exported","imported","source_transformed"):self.assertIs(value[key],False)
            self.assertEqual(value["source_sha256"],sha(self.input.read_bytes()));self.assertEqual(value["mapping_sha256"],sha(self.mapping.read_bytes()))
            self.assertEqual(value["ready_for_explicit_review"],value["status"]=="PASS");self.assertEqual(code,0 if value["status"]=="PASS" else 1)
            count=value["counts"];self.assertEqual(count["input_rows"],sum(count[k] for k in ("accepted_records","duplicate_rows","rejected_rows","conflict_rows")))
            self.assertNotIn("sheet",value)
        return value
    def cli(self,*,table="table-1",out=False,input_path=None,mapping_path=None,**options):
        return self.invoke(["--input",self.input if input_path is None else input_path,"--mapping",self.mapping if mapping_path is None else mapping_path,"--table",table,*(["--out",self.output] if out else [])],**options)
    def api(self,*,table="table-1",**options):return self.invoke([self.input,self.mapping,json.dumps(table)],mode="api",**options)
    def fixture(self,rows,contract=None):
        blocks=[dict(kind="table",rows=rows)];raw=document(blocks);self.write(raw)
        if contract is not None:self.mapping.write_bytes(canonical(contract))
        return raw,blocks
    def expect(self,blocks,records,issues=(),*,table="table-1",ignored=0,code=0):
        value=expected(self.input.read_bytes(),self.mapping.read_bytes(),blocks,records,issues,selected=table,ignored=ignored)
        self.assertEqual(self.cli(table=table,code=code),value);self.assertEqual(self.api(table=table,code=code),value);return value
    def refused(self,raw,code=None):
        self.write(raw);self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
    def invalid_mapping(self,raw,code=None):
        self.mapping.write_bytes(raw);self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            strict=self.strict_links if self.strict_links is not None else os.name!="nt" or os.environ.get("OUTLANDS_DOCUMENT_INTAKE_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
            actual=os.name=="nt" and getattr(error,"winerror",None)==1314
            if actual and not strict:
                self.assertEqual(self.id(),LINK_ID);self.assertFalse(directory);self.native_events.append(dict(test=self.id(),reason=LINK_REASON,policy="actual_windows_1314",actual_windows_1314=True,winerror=1314,strict=False,provenance="test_copied_cli.CopiedCLI.symlink/caught-OSError"));self.skipTest(LINK_REASON)
            raise


    def test_actual_entrypoints_help_affinity_and_both_inputs_are_required(self):
        self.assertEqual(self.invoke(mode="affinity"),dict(status="COPIED_RUNTIME_AFFINITY",runtime_files=6))
        self.assertIn("--mapping",self.invoke(["--help"],text=True));self.assertIn("--variant",self.invoke(["--help"],mode="generator",text=True))
        for args in ([],["--input",self.input],["--input",self.input,"--mapping",self.mapping],["--unknown","FICTIONAL_PRIVATE_SENTINEL"]):self.invoke(args,code=2,error="ARGUMENTS_INVALID")
        self.invoke(["--out",self.work/"unused.docx","--variant","FICTIONAL_PRIVATE_VARIANT"],mode="generator",code=2,error="ARGUMENTS_INVALID")

    def test_generator_variants_pass_and_review_hold_are_exact(self):
        for variant in ("before","after","needs-review","formatting"):
            target=self.owned(self.work/(variant+".docx"));value=self.invoke(["--out",target,"--variant",variant],mode="generator",allow=[target]);raw=target.read_bytes()
            self.assertEqual(value,dict(status="PASS",fictional=True,bytes=len(raw),sha256=sha(raw)));blocks=sample_blocks();records=sample_records();issues=[];code=0
            if variant in ("after","needs-review"):
                rows=[["Record","Units","Due","Active"]]+([["sample-a","14","2030-01-10","true"],["sample-c","5","2030-01-12","true"]] if variant=="after" else [["sample-a","12","2030-01-10","true"],["sample-a","13","2030-01-10","true"],["sample-c","invalid","2030-01-12","true"]])
                blocks=[dict(kind="paragraph",text="Fictional revised intake example."),dict(kind="table",rows=rows)]
                if variant=="after":records=sample_records("after")
                else:records=[];issues=[dict(row=2,code="IDENTITY_CONFLICT"),dict(row=3,code="IDENTITY_CONFLICT"),dict(row=4,code="VALUE_INTEGER_INVALID")];code=1
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:self.assertEqual({name:archive.read(name) for name in archive.namelist()},components(blocks,bold=variant=="formatting"))
            self.input=target;report=self.expect(blocks,records,issues,code=code);output=self.work/(variant+".json")
            self.assertEqual(self.invoke(["--input",self.input,"--mapping",self.mapping,"--table","table-1","--out",output],code=code,allow=[output]),dict(status=report["status"],report_written=True));self.assertEqual(output.read_bytes(),canonical(report))

    def test_five_explicit_types_and_four_distinct_provenance_hashes(self):
        contract=mapping([field("Key","key"),field("Count","count","integer"),field("Price","price","decimal"),field("Enabled","enabled","boolean"),field("Day","day","date")])
        raw,blocks=self.fixture([["Key","Count","Price","Enabled","Day"],["fixture-a","-12","0012.50","true","2032-02-29"]],contract)
        self.expect(blocks,[],[dict(row=2,code="VALUE_DECIMAL_INVALID")],code=1)
        raw,blocks=self.fixture([["Key","Count","Price","Enabled","Day"],["fixture-a","-12","12.500000","true","2032-02-29"]])
        result=self.expect(blocks,[(dict(key="fixture-a",count=-12,price="12.5",enabled=True,day="2032-02-29"),[2])])
        self.assertEqual(len({result[k] for k in ("source_sha256","normalized_table_sha256","mapping_sha256","content_sha256")}),4)
        self.assertEqual(result["source_row_basis"],"ONE_BASED_SELECTED_TABLE_ROW");self.assertEqual(result["table_position"],1)

    def test_integer_decimal_bounds_and_no_implicit_numeric_or_boolean_coercion(self):
        contract=mapping([field("Key","key"),field("Value","value","integer")]);rows=[["Key","Value"],["a","1000000000000"],["b","-1000000000000"]]
        raw,blocks=self.fixture(rows,contract);self.expect(blocks,[(dict(key="a",value=1000000000000),[2]),(dict(key="b",value=-1000000000000),[3])])
        for kind,values,code in (("integer",["-0","01","+1","1.0","1000000000001"],"VALUE_INTEGER_INVALID"),("decimal",["01.2","1e2","1.0000001","1000000000000.1"],"VALUE_DECIMAL_INVALID"),("boolean",["TRUE","1"," false"],"VALUE_BOOLEAN_INVALID"),("date",["2031-02-29","2030-1-01","2030-01-01Z"],"VALUE_DATE_INVALID")):
            contract=mapping([field("Key","key"),field("Value","value",kind)]);raw,blocks=self.fixture([["Key","Value"]]+[["fixture-"+str(i),v] for i,v in enumerate(values)],contract)
            self.expect(blocks,[],[dict(row=i+2,code=code) for i in range(len(values))],code=1)
        contract=mapping([field("Key","key"),field("Value","value","decimal")]);raw,blocks=self.fixture([["Key","Value"],["a","-0.000000"],["b","1000000000000"]],contract)
        self.expect(blocks,[(dict(key="a",value="-0"),[2]),(dict(key="b",value="1000000000000"),[3])])

    def test_optional_blank_null_required_missing_and_literal_text_are_distinct(self):
        contract=mapping([field("Key","key"),field("Optional","optional","integer",False),field("Text","text","text",False)])
        raw,blocks=self.fixture([["Key","Optional","Text"],[" a ","","  literal  "],["","1","held"]],contract)
        self.expect(blocks,[(dict(key=" a ",optional=None,text="  literal  "),[2])],[dict(row=3,code="REQUIRED_VALUE_MISSING")],code=1)
        raw,blocks=self.fixture([["Key","Optional","Text"],["A","",""],["a","0"," "]]);self.expect(blocks,[(dict(key="A",optional=None,text=None),[2]),(dict(key="a",optional=0,text=" "),[3])])

    def test_headers_are_exact_and_unknown_columns_need_explicit_policy(self):
        for header,code in ((["Record","Units","Due","Due"],"HEADER_INVALID"),(["","Units","Due","Active"],"HEADER_INVALID"),(["record","Units","Due","Active"],"MAPPED_HEADER_MISSING"),([" Record","Units","Due","Active"],"MAPPED_HEADER_MISSING")):
            raw,blocks=self.fixture([header,["a","1","2030-01-01","true"]]);self.api(code=2,error=code);self.cli(out=True,code=2,error=code)
        contract=mapping([field("Record","record_id"),field("Units","units","integer")]);raw,blocks=self.fixture([["Record","Units","Extra"],["a","1","ignored only explicitly"]],contract)
        self.api(code=2,error="UNMAPPED_HEADER");self.cli(code=2,error="UNMAPPED_HEADER");contract["unknown_columns"]="ignore";self.mapping.write_bytes(canonical(contract));self.expect(blocks,[(dict(record_id="a",units=1),[2])],ignored=1)

    def test_identical_duplicates_preserve_all_rows_without_first_or_last_winner(self):
        raw,blocks=self.fixture([["Key","Value"],["z","1"],["a","2"],["z","1"],["a","2"],["z","1"]],mapping([field("Key","key"),field("Value","value","integer")]))
        value=self.expect(blocks,[(dict(key="a",value=2),[3,5]),(dict(key="z",value=1),[2,4,6])]);self.assertEqual(value["counts"],dict(input_rows=5,accepted_records=2,duplicate_rows=3,rejected_rows=0,conflict_rows=0))
        self.assertTrue(value["ready_for_explicit_review"]);self.assertFalse(value["imported"])

    def test_conflicts_hold_all_members_without_hiding_independent_records(self):
        raw,blocks=self.fixture([["Key","Value"],["conflict","1"],["ok","9"],["conflict","2"],["conflict","1"]],mapping([field("Key","key"),field("Value","value","integer")]))
        issues=[dict(row=n,code="IDENTITY_CONFLICT") for n in (2,4,5)];value=self.expect(blocks,[(dict(key="ok",value=9),[3])],issues,code=1)
        self.assertEqual(value["counts"],dict(input_rows=4,accepted_records=1,duplicate_rows=0,rejected_rows=0,conflict_rows=3));self.assertFalse(value["ready_for_explicit_review"]);self.assertNotIn("conflict",json.dumps(value["accepted"]))

    def test_rejected_payloads_are_omitted_and_issue_rows_are_sorted(self):
        raw,blocks=self.fixture([["Key","Value"],["FICTIONAL_PRIVATE_BAD","not-an-integer"],["ok","7"],["","4"],["long","x"*257]],mapping([field("Key","key"),field("Value","value","integer")]))
        issues=[dict(row=2,code="VALUE_INTEGER_INVALID"),dict(row=4,code="REQUIRED_VALUE_MISSING"),dict(row=5,code="VALUE_TEXT_INVALID")]
        value=self.expect(blocks,[(dict(key="ok",value=7),[3])],issues,code=1);encoded=canonical(value)
        self.assertNotIn(b"not-an-integer",encoded);self.assertNotIn(b"FICTIONAL_PRIVATE_BAD",encoded);self.assertNotIn(b"x"*257,encoded)

    def test_mapping_schema_field_uniqueness_and_identity_are_not_inferred(self):
        variants=[]
        for change,code in ((lambda v:v.update(extra="private"),"FIELDS_INVALID"),(lambda v:v.update(format="other"),"MAP_INVALID"),(lambda v:v.update(unknown_columns="guess"),"MAP_INVALID"),(lambda v:v.update(identity=[]),"MAP_IDENTITY_INVALID"),(lambda v:v.update(identity=["unknown"]),"MAP_IDENTITY_INVALID"),(lambda v:v.update(identity=["record_id","record_id"]),"MAP_IDENTITY_INVALID"),(lambda v:v["fields"][0].update(required=False),"MAP_IDENTITY_INVALID"),(lambda v:v["fields"][0].update(type="guess"),"MAP_INVALID"),(lambda v:v["fields"][0].update(target="Invalid Target"),"IDENTIFIER_INVALID"),(lambda v:v["fields"].append(dict(v["fields"][0])),"MAP_DUPLICATE_FIELD"),(lambda v:v["fields"][0].update(required=1),"MAP_INVALID")):
            value=mapping();change(value);variants.append((value,code))
        for value,code in variants:self.invalid_mapping(canonical(value),code)

    def test_mapping_json_diagnostics_reject_duplicate_float_nonfinite_and_bad_utf8(self):
        for raw,code in ((b"{","JSON_INVALID"),(b"\xff","JSON_INVALID"),(b'[]',"FIELDS_INVALID"),(b'{"format":1,"format":2}',"JSON_DUPLICATE_KEY"),(b'{"value":1.5}',"JSON_INTEGER_OR_STRING_REQUIRED"),(b'{"value":NaN}',"JSON_INTEGER_OR_STRING_REQUIRED")):
            self.invalid_mapping(raw,code)
        value=mapping();value["fields"][0]["source"]="x"*257;self.invalid_mapping(canonical(value),"MAP_INVALID")

    def test_raw_content_table_and_mapping_fingerprints_have_separate_meanings(self):
        first=self.expect(sample_blocks(),sample_records());self.write(document(author="Fictional changed property",bold=True));second=self.expect(sample_blocks(),sample_records())
        self.assertNotEqual(first["source_sha256"],second["source_sha256"])
        for key in ("content_sha256","normalized_table_sha256","mapping_sha256"):self.assertEqual(first[key],second[key])
        self.mapping.write_bytes(json.dumps(mapping(),indent=2).encode());third=self.expect(sample_blocks(),sample_records());self.assertNotEqual(second["mapping_sha256"],third["mapping_sha256"]);self.assertEqual(second["accepted"],third["accepted"])

    def test_explicit_table_selection_and_all_body_validation_precede_mapping(self):
        contract=mapping([field("Key","key")]);blocks=[dict(kind="table",rows=[["Key"],["a"]]),dict(kind="paragraph",text="Between"),dict(kind="table",rows=[["Key"],["b"]])]
        self.write(document(blocks));self.mapping.write_bytes(canonical(contract));self.expect(blocks,[(dict(key="b"),[2])],table="table-2");self.assertEqual(self.cli(table="table-2")["table_position"],3)
        for selected,code in ((None,"TABLE_SELECTION_INVALID"),("TABLE-2","TABLE_SELECTION_NOT_FOUND"),("table-9","TABLE_SELECTION_NOT_FOUND")):self.api(table=selected,code=2,error=code)
        raw=edit(document(blocks),{"word/document.xml":lambda b:b.replace(b'<w:t xml:space="preserve">a',b'<w:hyperlink/><w:t xml:space="preserve">a',1)})
        self.write(raw);self.cli(table="table-2",code=2,error="DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT")
        self.mapping.write_bytes(b"{");self.cli(table="table-2",code=2,error="DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT")

    def test_literal_unicode_markup_formulas_and_spaces_remain_plain_text(self):
        contract=mapping([field("Key","key"),field("Text","text")]);rows=[["Key","Text"],[" a ","  café λ 🧪 <script>literal</script>  "],["formula","=SUM(1,2)"]]
        raw,blocks=self.fixture(rows,contract);value=self.expect(blocks,[(dict(key=" a ",text=rows[1][1]),[2]),(dict(key="formula",text="=SUM(1,2)"),[3])])
        self.cli(out=True,allow=[self.output]);self.assertEqual(self.output.read_bytes(),canonical(value));self.assertTrue(self.output.read_bytes().isascii());self.assertIn(b"\\ud83e\\uddea",self.output.read_bytes())

    def test_csv_quoting_is_in_memory_and_multiline_cells_are_held(self):
        contract=mapping([field("Key","key"),field("Text","text")]);rows=[["Key","Text"],["a","comma, and \"quote\""]];raw,blocks=self.fixture(rows,contract)
        value=self.expect(blocks,[(dict(key="a",text='comma, and "quote"'),[2])]);self.assertEqual(value["normalized_table_sha256"],sha(b'Key,Text\na,"comma, and ""quote"""\n'))
        raw=edit(document([dict(kind="table",rows=[["Key","Text"],["a","Line1"]])]),{"word/document.xml":lambda b:b.replace(b'Line1</w:t>',b'Line1</w:t><w:br/><w:t>Line2</w:t>')})
        self.write(raw);blocks=[dict(kind="table",rows=[["Key","Text"],["a","Line1\nLine2"]])];value=self.expect(blocks,[],[dict(row=2,code="VALUE_TEXT_INVALID")],code=1)
        self.assertEqual(value["normalized_table_sha256"],sha(b'Key,Text\na,"Line1\nLine2"\n'));self.assertEqual(list(self.work.rglob("*.csv")),[])

    def test_header_only_and_all_rejected_batches_never_become_ready(self):
        contract=mapping([field("Key","key")]);raw,blocks=self.fixture([["Key"]],contract);self.expect(blocks,[],code=1)
        raw,blocks=self.fixture([["Key"],[""]]);self.expect(blocks,[],[dict(row=2,code="REQUIRED_VALUE_MISSING")],code=1)
        self.refused(document([]),"DOCX_EMPTY_DOCUMENT");self.refused(document([dict(kind="table",rows=[])]),"DOCX_EMPTY_TABLE")

    def test_zip_crc_duplicates_and_unselected_parts_never_extract_to_disk(self):
        raw=bytearray(document());raw[raw.index(b"Fictional intake example.")]^=1;self.refused(bytes(raw),"DOCX_ARCHIVE_INVALID")
        parts=components()
        with self.assertWarns(UserWarning):raw=zip_bytes([*parts.items(),("word/document.xml",parts["word/document.xml"])])
        self.refused(raw,"DOCX_ARCHIVE_INVALID")
        for name in ("../fictional.xml","word/vbaProject.bin","word/media/image.png"):self.refused(zip_bytes(dict(parts,**{name:b"Invented refused bytes"})),"DOCX_PART_UNSUPPORTED")
        self.refused(document()[:50],"DOCX_ARCHIVE_INVALID")

    def test_xml_dtd_comments_processing_instructions_and_structure_bounds_refuse(self):
        for prefix,code in (("<!DOCTYPE w:document [<!ENTITY fixture 'invented'>]>","XML_DECLARATION_FORBIDDEN"),("<?fixture invented?>","XML_PROCESSING_INSTRUCTION_FORBIDDEN"),("<!-- invented -->","XML_COMMENT_FORBIDDEN")):
            for encoding in ("utf-8","utf-16"):self.refused(edit(document(),{"word/document.xml":lambda b:(prefix+b.decode()).encode(encoding)}),code)
        for xml in (("<r>"*33+"</r>"*33).encode(),b'<r>'+b'<a/>'*50000+b'</r>'):self.refused(edit(document(),{"word/document.xml":xml}),"XML_STRUCTURE_LIMIT")

    def test_external_relationships_active_and_nonrectangular_tables_refuse(self):
        self.refused(edit(document(),{"_rels/.rels":lambda b:b.replace(b'Target=',b'TargetMode="External" Target=',1)}),"DOCX_RELATIONSHIP_INVALID")
        for markup in (b'<w:fldSimple/>',b'<w:rPr><w:vanish/></w:rPr>',b'<w:ins/>'):self.refused(edit(document(),{"word/document.xml":lambda b:b.replace(b'<w:r>',b'<w:r>'+markup,1)}),"DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT")
        self.refused(document([dict(kind="table",rows=[["A","B"],["C"]])]),"DOCX_TABLE_NOT_RECTANGULAR")

    def test_each_input_has_its_actual_four_mebibyte_bound_and_output_budget(self):
        parts=components();parts["docProps/core.xml"]=b"x"*2097152;parts["word/styles.xml"]=b"";parts["word/_rels/document.xml.rels"]=('<Relationships xmlns="'+P+'"><Relationship Id="style" Type="'+R+'/styles" Target="styles.xml"/></Relationships>').encode()
        parts["word/styles.xml"]=b"y"*(4194304-len(zip_bytes(parts)));raw=zip_bytes(parts);self.assertEqual(len(raw),4194304);self.write(raw)
        map_raw=canonical(mapping());self.mapping.write_bytes(map_raw+b" "*(4194304-len(map_raw)));self.expect(sample_blocks(),sample_records())
        self.mapping.write_bytes(self.mapping.read_bytes()+b" ");self.api(code=2,error="INPUT_LIMIT");self.cli(code=2,error="INPUT_SIZE_LIMIT" if os.name=="nt" else "INPUT_LIMIT")
        self.mapping.write_bytes(map_raw);self.write(raw+b"x");self.api(code=2,error="INPUT_LIMIT");self.cli(code=2,error="INPUT_SIZE_LIMIT" if os.name=="nt" else "INPUT_LIMIT")
        self.write(document());self.cli(mode="output-budget",code=2,error="OUTPUT_LIMIT");self.assertFalse(self.output.exists())

    def test_mapping_field_and_selected_table_row_limits_preserve_full_results(self):
        fields=[field("C"+str(i),"c"+str(i)) for i in range(32)];contract=mapping(fields);rows=[[f["source"] for f in fields],[str(i) for i in range(32)]];raw,blocks=self.fixture(rows,contract)
        self.expect(blocks,[(dict(("c"+str(i),str(i)) for i in range(32)),[2])]);contract["fields"].append(field("Other","other"));self.invalid_mapping(canonical(contract),"MAP_INVALID")
        contract=mapping([field("Key","key")]);rows=[["Key"]]+[["fixture-"+str(i).zfill(4)] for i in range(1000)];raw,blocks=self.fixture(rows,contract)
        self.expect(blocks,[(dict(key=row[0]),[i+2]) for i,row in enumerate(rows[1:])]);self.refused(document([dict(kind="table",rows=rows+[["overflow"]])]),"DOCX_TABLE_FEATURE_UNSUPPORTED")

    def test_short_and_changed_reads_of_each_input_role_have_fixed_diagnostics(self):
        for mode in ("short-read","short-mapping-read","changed-stat","changed-mapping-stat"):self.cli(mode=mode,code=2,error="INPUT_CHANGED")
        self.cli(input_path=self.work/"FICTIONAL_PRIVATE_DOCUMENT.docx",code=2);self.cli(mapping_path=self.work/"FICTIONAL_PRIVATE_MAPPING.json",code=2)

    def test_retained_partial_report_does_not_approve_or_replace_outputs(self):
        report=expected(self.input.read_bytes(),self.mapping.read_bytes(),sample_blocks(),sample_records())
        self.cli(out=True,mode="write-failure",code=2,error="INPUT_OR_OUTPUT_REFUSED",allow=[self.output]);self.assertEqual(self.output.read_bytes(),canonical(report)[:5])
        self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),canonical(report)[:5])

    def test_no_overwrite_aliases_and_standalone_collection_source_protection(self):
        self.output.write_bytes(b"Invented preserved report");self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),b"Invented preserved report")
        for target in (self.input,self.mapping):self.invoke(["--input",self.input,"--mapping",self.mapping,"--table","table-1","--out",target],code=2)
        for target in (self.copy/"new.json",self.copy/"toolkit.py"):self.invoke(["--input",self.input,"--mapping",self.mapping,"--table","table-1","--out",target],code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE")
        collection=self.owned(self.work/"collection");selected=collection/"tools/document-intake-checker";selected.mkdir(parents=True);(collection/"systems").mkdir();(collection/"catalog").mkdir();(collection/"catalog/registry.json").write_bytes(b"{}\n")
        for name in RUNTIME:(selected/name).write_bytes((self.copy/name).read_bytes())
        self.invoke(["--input",self.input,"--mapping",self.mapping,"--table","table-1","--out",collection/"refused.json"],base=selected,code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE")

    def test_both_input_roles_require_single_link_regular_files(self):
        for target,suffix in ((self.input,"document"),(self.mapping,"mapping")):
            alias=self.owned(self.work/(suffix+"-hardlink"));os.link(target,alias);self.assertTrue(alias.samefile(target))
            self.cli(input_path=alias if target==self.input else None,mapping_path=alias if target==self.mapping else None,code=2,error="CONTROL_NOT_SINGLE_LINK" if os.name=="nt" else "INPUT_UNSAFE")
            self.cli(code=2,error="CONTROL_NOT_SINGLE_LINK" if os.name=="nt" else "INPUT_UNSAFE")
            self.owned(alias).unlink();self.assertEqual(target.stat().st_nlink,1)

    def test_linked_parents_of_both_inputs_and_output_are_refused(self):
        target=self.owned(self.work/"target");target.mkdir();(target/"input.docx").write_bytes(document());(target/"mapping.json").write_bytes(canonical(mapping()));route=self.owned(self.work/"route")
        if os.name=="nt":
            done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(route),str(target)],capture_output=True,timeout=15);self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:route.rmdir() if route.exists() else None)
        else:route.symlink_to(target,target_is_directory=True)
        self.cli(input_path=route/"input.docx",code=2);self.cli(mapping_path=route/"mapping.json",code=2)
        self.invoke(["--input",self.input,"--mapping",self.mapping,"--table","table-1","--out",route/"new.json"],code=2);self.assertFalse((target/"new.json").exists())

    def test_native_leaf_symlink_and_dangling_output_refusal(self):
        for target,name in ((self.input,"document-link"),(self.mapping,"mapping-link")):
            link=self.owned(self.work/name);self.symlink(link,target);self.cli(input_path=link if target==self.input else None,mapping_path=link if target==self.mapping else None,code=2)
        for name,target in (("dangling",self.work/"never-created.json"),("source-pointing",self.copy/"never-created.json")):
            target=self.owned(target);self.assertFalse(os.path.lexists(target));route=self.owned(self.work/(name+".json"));self.symlink(route,target)
            self.invoke(["--input",self.input,"--mapping",self.mapping,"--table","table-1","--out",route],code=2);self.assertFalse(os.path.lexists(target));self.assertTrue(route.is_symlink())
        for name,target in (("document-pointing",self.input),("mapping-pointing",self.mapping),("runtime-pointing",self.copy/"toolkit.py")):
            raw=target.read_bytes();route=self.owned(self.work/(name+".json"));self.symlink(route,target);self.invoke(["--input",self.input,"--mapping",self.mapping,"--table","table-1","--out",route],code=2);self.assertEqual(target.read_bytes(),raw)

    @unittest.skipUnless(os.name=="nt",WINDOWS_REASON)
    def test_native_windows_path_grammar_and_named_stream_routes(self):
        for path in (str(self.input)+":stream",str(self.work/"CON"),str(self.input)+".",str(self.input)+" ","x:relative","//example.invalid/share"):
            self.cli(input_path=path,code=2);self.cli(mapping_path=path,code=2)
        self.invoke(["--input",self.input,"--mapping",self.mapping,"--table","table-1","--out",str(self.output)+":stream"],code=2)

    @unittest.skipUnless(os.name!="nt",POSIX_REASON)
    def test_native_posix_special_inputs_and_private_report_mode(self):
        fifo=self.owned(self.work/"fictional.fifo");os.mkfifo(fifo);sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.owned(self.work/"s")));self.addCleanup(sock.close)
        for path in (fifo,self.work/"s",self.work):self.cli(input_path=path,code=2);self.cli(mapping_path=path,code=2)
        self.cli(out=True,allow=[self.output]);self.assertEqual(stat.S_IMODE(self.output.stat().st_mode),0o600)

    def test_mapping_order_composite_identity_and_reordered_columns_are_explicit(self):
        contract=mapping([field("Amount","amount","integer"),field("Key","key"),field("Day","day","date")],identity=["key","day"])
        rows=[["Day","Key","Amount"],["2030-01-02","a","5"],["2030-01-01","a","7"],["2030-01-01","a","7"]];raw,blocks=self.fixture(rows,contract)
        records=[(dict(amount=7,key="a",day="2030-01-01"),[3,4]),(dict(amount=5,key="a",day="2030-01-02"),[2])];value=self.expect(blocks,records)
        self.assertEqual(value["mapping"],contract["fields"]);self.assertEqual(value["counts"]["duplicate_rows"],1)


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
    if strict is None:strict=os.name!="nt" or os.environ.get("OUTLANDS_DOCUMENT_INTAKE_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
    assert type(strict) is bool
    CopiedCLI.strict_links=os.name!="nt" or strict;CopiedCLI.native_events=[]
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
        fictional_document_intake_flow_checked=flow_checked,native_file_guards_checked=native_checked,fictional_document_intake_flow_test_ids=sorted(FLOW_IDS),native_file_guard_test_ids=sorted(native),
        positive_asserted_test_ids=dict(fictional_document_intake_flow_checked=sorted(FLOW_IDS),native_file_guards_checked=sorted(native)),copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,
        **{name:False for name in FALSE_FLAGS})


if __name__=="__main__":raise SystemExit(0 if run_copied_tests()["status"]=="PASS" else 1)
