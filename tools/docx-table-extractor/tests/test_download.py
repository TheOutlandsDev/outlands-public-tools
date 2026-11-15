"""Independent copied DOCX consumers on invented packages; no Office, real documents or extraction. MIT."""
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
RUNTIME=("docx_tables.py","docx_core.py","toolkit.py","native_windows.py","fictional_docx.py")
W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P="http://schemas.openxmlformats.org/package/2006/relationships"
C="http://schemas.openxmlformats.org/package/2006/content-types"
MAIN="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
WINDOWS_ID="test_download.Download.test_native_windows_path_grammar_and_named_stream_routes"
WINDOWS_REASON="Native Windows path-grammar fixtures"
POSIX_ID="test_download.Download.test_native_posix_special_inputs_and_private_report_mode"
POSIX_REASON="Native POSIX special-file and mode fixtures"
LINK_ID="test_download.Download.test_native_leaf_symlink_and_dangling_output_refusal"
LINK_REASON="Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS={(POSIX_ID,POSIX_REASON)}
REQUIRED_POSIX_SKIPS={(WINDOWS_ID,WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS={(LINK_ID,LINK_REASON)}
FALSE_FLAGS=("real_documents_used","document_properties_exported","external_resources_followed","document_executed",
             "office_processes_started","archives_extracted","visible_layout_verified","general_word_compatibility_verified","production_workflows_verified")
FLOW_IDS={"test_download.Download.test_fictional_generator_variants_and_exact_report_readback",
          "test_download.Download.test_default_index_hashes_omit_all_body_and_property_values",
          "test_download.Download.test_explicit_ordered_tables_and_top_level_paragraphs"}
COMMON_NATIVE_IDS={"test_download.Download.test_no_overwrite_and_standalone_collection_source_output_guards",
                   "test_download.Download.test_retained_partial_report_is_not_confirmed_or_replaced",
                   "test_download.Download.test_mandatory_hardlink_inputs_and_existing_outputs_are_refused",
                   "test_download.Download.test_linked_parent_read_and_report_routes_are_refused"}


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


def expected(raw,blocks,tables=(),paragraphs=False):
    rows=[];pcount=tcount=rcount=ccount=0
    for source in blocks:
        if source["kind"]=="paragraph":
            pcount+=1;rows.append(dict(id="paragraph-"+str(pcount),position=len(rows)+1,kind="paragraph",text=source["text"]))
        else:
            tcount+=1;rcount+=len(source["rows"]);ccount+=sum(map(len,source["rows"]))
            rows.append(dict(id="table-"+str(tcount),position=len(rows)+1,kind="table",rows=source["rows"]))
    indexed={row["id"]:row for row in rows if row["kind"]=="table"}
    return dict(format="outlands-docx-table-extract-v1",status="PASS",source_sha256=sha(raw),content_sha256=sha(canonical(rows)),
        counts=dict(paragraphs=pcount,tables=tcount,rows=rcount,cells=ccount),
        table_index=[dict(id=row["id"],position=row["position"],rows=len(row["rows"]),columns=len(row["rows"][0])) for row in indexed.values()],
        selected_tables=[indexed[key] for key in tables],selected_paragraphs=[row for row in rows if row["kind"]=="paragraph"] if paragraphs else [],
        document_properties_exported=False,external_resources_followed=False,document_executed=False)


CHILD=r'''
import _elementtree,hashlib,importlib.metadata,json,os,pyexpat,runpy,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();mode=sys.argv[2];args=sys.argv[3:];sys.path.insert(0,str(base))
def audit(event,values):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open'):
  raise AssertionError('UNEXPECTED_NETWORK_OFFICE_OR_PROCESS')
sys.addaudithook(audit)
def no_extract(*a,**kw):raise AssertionError('INPUT_ARCHIVE_EXTRACTION_FORBIDDEN')
zipfile.ZipFile.extract=zipfile.ZipFile.extractall=no_extract
import docx_tables as a
import docx_core as d
import fictional_docx as g
import toolkit as t
import native_windows as n
for module,name in ((a,'docx_tables.py'),(d,'docx_core.py'),(g,'fictional_docx.py'),(t,'toolkit.py'),(n,'native_windows.py')):
 assert Path(module.__file__).resolve()==base/name
assert a.docx_core is d and a.t is d.t is g.t is t
assert t.ET.XMLParser is _elementtree.XMLParser and t.ET.TreeBuilder is _elementtree.TreeBuilder
assert t.XMLBuilder.__mro__[1] is _elementtree.TreeBuilder and len(pyexpat.version_info)==3
assert a.inspect.__globals__ is a.__dict__ and d.extract.__globals__ is d.__dict__
assert t.read.__globals__ is t.__dict__ and t.write_new.__globals__ is t.__dict__
if mode=='affinity':
 sys.stdout.write(t.encode(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=5)).decode());raise SystemExit(0)
if mode=='generator':
 sys.argv=[str(base/'fictional_docx.py'),*args]
 runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('GENERATOR_ENTRYPOINT_DID_NOT_EXIT')
if mode=='api':
 path=Path(args[0]);assert path.is_absolute()
 try:value=a.inspect(path.read_bytes(),json.loads(args[1]),json.loads(args[2]))
 except t.Rejected as error:sys.stdout.write(t.encode(dict(status='ERROR',code=str(error))).decode());raise SystemExit(2)
 sys.stdout.write(t.encode(value).decode());raise SystemExit(0)
if mode=='short-read':os.read=lambda *unused:b''
elif mode=='changed-stat':
 original_read=os.read;original_stat=os.fstat;changed=False
 def read(*values):
  global changed
  raw=original_read(*values)
  if raw:changed=True
  return raw
 def info(fd):
  value=original_stat(fd)
  if not changed:return value
  fields={name:getattr(value,name) for name in dir(value) if name.startswith('st_')};fields['st_mtime_ns']+=1
  return SimpleNamespace(**fields)
 os.read=read;os.fstat=info
elif mode=='write-failure':
 original_write=os.write;written=False
 def write(fd,data):
  global written
  if written:raise OSError('FICTIONAL_PRIVATE_WRITE_FAILURE')
  written=True;return original_write(fd,data[:5])
 os.write=write
elif mode=='output-budget':t.MAX_OUTPUT=1
elif mode!='normal':raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
sys.argv=[str(base/'docx_tables.py'),*args]
runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('EXTRACTOR_ENTRYPOINT_DID_NOT_EXIT')
'''


class Download(unittest.TestCase):
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
        self.temp=tempfile.TemporaryDirectory(prefix="docx-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.assertEqual(self.work.parent,parent);self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();(self.copy/name).write_bytes(raw);self.pins[name]=sha(raw)
        self.input=self.work/"fictional.docx";self.input.write_bytes(document());self.output=self.work/"summary.json"
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
        elif value.get("format")=="outlands-docx-table-extract-v1":
            for key in ("document_properties_exported","external_resources_followed","document_executed"):self.assertIs(value[key],False)
            self.assertEqual(value["source_sha256"],sha(self.input.read_bytes()))
        return value
    def cli(self,*,tables=(),paragraphs=False,out=False,**options):
        args=["--input",self.input]
        for table in tables:args.extend(["--table",table])
        if paragraphs:args.append("--include-paragraphs")
        if out:args.extend(["--out",self.output])
        return self.invoke(args,**options)
    def api(self,*,tables=(),paragraphs=False,**options):return self.invoke([self.input,json.dumps(tables),json.dumps(paragraphs)],mode="api",**options)
    def refused(self,raw,code=None):
        self.write(raw);self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            strict=self.strict_links if self.strict_links is not None else os.name!="nt" or os.environ.get("OUTLANDS_DOCX_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
            actual=os.name=="nt" and getattr(error,"winerror",None)==1314
            if actual and not strict:
                self.assertEqual(self.id(),LINK_ID);self.assertFalse(directory);self.native_events.append(dict(test=self.id(),reason=LINK_REASON,policy="actual_windows_1314",actual_windows_1314=True,winerror=1314,strict=False,provenance="test_download.Download.symlink/caught-OSError"));self.skipTest(LINK_REASON)
            raise

    def test_copied_affinity_and_both_entrypoint_help_are_inert(self):
        self.assertEqual(self.invoke(mode="affinity"),dict(status="COPIED_RUNTIME_AFFINITY",runtime_files=5))
        self.assertIn("--input",self.invoke(["--help"],text=True));self.assertIn("--variant",self.invoke(["--help"],mode="generator",text=True))
        for mode in ("normal","generator"):
            self.invoke(mode=mode,code=2,error="ARGUMENTS_INVALID");self.invoke(["--unknown","FICTIONAL_PRIVATE_SENTINEL"],mode=mode,code=2,error="ARGUMENTS_INVALID")

    def test_fictional_generator_variants_and_exact_report_readback(self):
        for variant in ("before","after","needs-review","formatting"):
            target=self.owned(self.work/(variant+".docx"));value=self.invoke(["--out",target,"--variant",variant],mode="generator",allow=[target])
            raw=target.read_bytes();self.assertEqual(value,dict(status="PASS",fictional=True,bytes=len(raw),sha256=sha(raw)))
            blocks=sample_blocks()
            if variant in ("after","needs-review"):
                rows=[["Record","Units","Due","Active"]]+([["sample-a","14","2030-01-10","true"],["sample-c","5","2030-01-12","true"]] if variant=="after" else [["sample-a","12","2030-01-10","true"],["sample-a","13","2030-01-10","true"],["sample-c","invalid","2030-01-12","true"]])
                blocks=[dict(kind="paragraph",text="Fictional revised intake example."),dict(kind="table",rows=rows)]
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                self.assertEqual({name:archive.read(name) for name in archive.namelist()},components(blocks,bold=variant=="formatting"))
                self.assertTrue(all(info.date_time==(2030,1,1,0,0,0) and info.compress_type==zipfile.ZIP_DEFLATED for info in archive.infolist()))
            self.input=target;report=self.cli(tables=["table-1"],paragraphs=True);self.assertEqual(report,expected(raw,blocks,["table-1"],True));self.invoke(["--out",target],mode="generator",code=2)
        self.assertEqual(self.cli(tables=["table-1"],paragraphs=True,out=True,allow=[self.output]),dict(status="PASS",report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))

    def test_default_index_hashes_omit_all_body_and_property_values(self):
        blocks=[dict(kind="paragraph",text="Private-looking fictional paragraph"),dict(kind="table",rows=[["Hidden-by-default fictional cell"]])]
        raw=document(blocks,author="Invented property creator");self.write(raw);value=self.cli();self.assertEqual(value,expected(raw,blocks))
        for needle in ("Private-looking","Hidden-by-default","Invented property"):self.assertNotIn(needle,json.dumps(value))
        self.assertEqual(self.api(),value);self.assertEqual(value["table_index"],[dict(id="table-1",position=2,rows=1,columns=1)])

    def test_explicit_ordered_tables_and_top_level_paragraphs(self):
        blocks=[dict(kind="table",rows=[["A","B"]]),dict(kind="paragraph",text="Between"),dict(kind="table",rows=[["C"],["D"]]),dict(kind="paragraph",text="Last")]
        raw=document(blocks);self.write(raw);want=expected(raw,blocks,["table-2","table-1"],True)
        self.assertEqual(self.cli(tables=["table-2","table-1"],paragraphs=True),want);self.assertEqual(self.api(tables=["table-2","table-1"],paragraphs=True),want)
        self.assertEqual(self.cli(paragraphs=True),expected(raw,blocks,paragraphs=True))

    def test_unicode_whitespace_tabs_line_breaks_and_literal_markup(self):
        blocks=[dict(kind="paragraph",text="  café λ 🧪 & <script>literal</script>  "),dict(kind="table",rows=[["A","B"]])]
        raw=document(blocks);raw=edit(raw,{"word/document.xml":lambda b:b.replace(b'</w:t>',b'</w:t><w:tab/><w:t>Next</w:t><w:br/><w:t>Last</w:t>',1)})
        blocks[0]["text"]+="\tNext\nLast";self.write(raw);self.assertEqual(self.cli(tables=["table-1"],paragraphs=True),expected(raw,blocks,["table-1"],True))
        self.cli(paragraphs=True,out=True,allow=[self.output]);report=self.output.read_bytes();self.assertTrue(report.isascii());self.assertIn(b"\\ud83e\\uddea",report);self.assertIn(b"<script>literal</script>",report)

    def test_formatting_and_properties_change_raw_but_preserve_content_hash(self):
        first=document();self.write(first);a=self.cli(tables=["table-1"],paragraphs=True)
        second=document(author="Another fictional creator",bold=True);self.write(second);b=self.cli(tables=["table-1"],paragraphs=True)
        self.assertNotEqual(a["source_sha256"],b["source_sha256"]);self.assertEqual(a["content_sha256"],b["content_sha256"])
        self.assertEqual({k:v for k,v in a.items() if k!="source_sha256"},{k:v for k,v in b.items() if k!="source_sha256"});self.assertNotIn("creator",json.dumps(b))

    def test_invalid_duplicate_unknown_and_typed_selections_refuse(self):
        for tables,paragraphs,code in ((["table-1","table-1"],False,"SELECTION_INVALID"),(["table-2"],False,"TABLE_SELECTION_NOT_FOUND"),([True],False,"SELECTION_INVALID"),("table-1",False,"SELECTION_INVALID"),([],1,"SELECTION_INVALID"),(["table-1"]*33,False,"SELECTION_INVALID")):
            self.api(tables=tables,paragraphs=paragraphs,code=2,error=code)
        self.cli(tables=["table-1","table-1"],out=True,code=2,error="SELECTION_INVALID");self.cli(tables=["TABLE-1"],code=2,error="TABLE_SELECTION_NOT_FOUND");self.assertFalse(self.output.exists())

    def test_empty_text_and_multiple_cell_paragraphs_preserve_block_positions(self):
        blocks=[dict(kind="paragraph",text=""),dict(kind="table",rows=[["First"]]),dict(kind="paragraph",text="After")]
        raw=edit(document(blocks),{"word/document.xml":lambda b:b.replace(b'</w:tc>',b'<w:p><w:r><w:t>Second</w:t></w:r></w:p></w:tc>',1)})
        blocks[1]["rows"][0][0]="First\nSecond";self.write(raw);self.assertEqual(self.cli(tables=["table-1"],paragraphs=True),expected(raw,blocks,["table-1"],True))
        self.refused(document([]),"DOCX_EMPTY_DOCUMENT");self.refused(document([dict(kind="table",rows=[])]),"DOCX_EMPTY_TABLE")

    def test_unselected_tables_and_body_features_are_still_validated(self):
        raw=document([dict(kind="table",rows=[["Selected"]]),dict(kind="table",rows=[["Unchecked must refuse"]])])
        raw=edit(raw,{"word/document.xml":lambda b:b.replace(b'Unchecked must refuse',b'Bad</w:t><w:hyperlink/><w:t>',1)})
        self.write(raw);self.cli(tables=["table-1"],code=2,error="DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT");self.api(tables=["table-1"],code=2,error="DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT")
        self.refused(edit(document(),{"word/document.xml":lambda b:b.replace(b'<w:body>',b'<w:body><w:unknown/>')}),"DOCX_BODY_FEATURE_UNSUPPORTED")

    def test_invalid_truncated_and_corrupt_crc_archives_have_fixed_errors(self):
        for raw in (b"Invented not ZIP",document()[:50]):self.refused(raw,"DOCX_ARCHIVE_INVALID")
        raw=bytearray(document());needle=b"Fictional intake example.";offset=raw.index(needle);raw[offset]^=1
        self.refused(bytes(raw),"DOCX_ARCHIVE_INVALID")

    def test_duplicate_traversal_active_and_unknown_parts_are_not_extracted(self):
        parts=components()
        with self.assertWarns(UserWarning):raw=zip_bytes([*parts.items(),("word/document.xml",parts["word/document.xml"])])
        self.refused(raw,"DOCX_ARCHIVE_INVALID")
        for name in ("../fictional.xml","word/vbaProject.bin","word/media/image1.png","customXml/item1.xml","word/document.xml/"):
            self.refused(zip_bytes(dict(parts,**{name:b"Invented refused bytes"})),"DOCX_PART_UNSUPPORTED")

    def test_zip_encryption_compression_entry_count_and_special_modes_refuse(self):
        raw=bytearray(document())
        for signature,offset in ((b"PK\x03\x04",6),(b"PK\x01\x02",8)):
            position=raw.index(signature);struct.pack_into("<H",raw,position+offset,struct.unpack_from("<H",raw,position+offset)[0]|1)
        self.refused(bytes(raw),"DOCX_PART_UNSUPPORTED")
        raw=bytearray(document())
        for signature,offset in ((b"PK\x03\x04",8),(b"PK\x01\x02",10)):struct.pack_into("<H",raw,raw.index(signature)+offset,99)
        self.refused(bytes(raw),"DOCX_PART_UNSUPPORTED")
        raw=bytearray(document());position=raw.index(b"PK\x01\x02");struct.pack_into("<I",raw,position+38,(stat.S_IFLNK|0o777)<<16);self.refused(bytes(raw),"DOCX_PART_UNSUPPORTED")
        with self.assertWarns(UserWarning):raw=zip_bytes([("word/document.xml",b"x")]*65)
        self.refused(raw,"DOCX_ARCHIVE_INVALID")

    def test_expanded_part_ratio_and_total_budgets_refuse(self):
        parts=components();parts["docProps/core.xml"]=b"x"*(2097152+1);self.refused(zip_bytes(parts),"DOCX_EXPANSION_LIMIT")
        parts=components();parts["docProps/core.xml"]=b"x"*100000;self.refused(zip_bytes(parts,zipfile.ZIP_DEFLATED),"DOCX_EXPANSION_LIMIT")
        block=random.Random(734).randbytes(16384);payload=block*128;parts=components()
        for name in ("docProps/core.xml","docProps/app.xml","word/styles.xml","word/settings.xml","word/fontTable.xml"):parts[name]=payload
        self.refused(zip_bytes(parts,zipfile.ZIP_DEFLATED),"DOCX_EXPANSION_LIMIT")

    def test_required_parts_content_types_and_main_identity_are_explicit(self):
        for name in ("[Content_Types].xml","_rels/.rels","word/document.xml"):
            parts=components();parts.pop(name);self.refused(zip_bytes(parts),"DOCX_REQUIRED_PART_MISSING")
        for old,new,code in ((MAIN.encode(),b"application/vnd.ms-word.document.macroEnabled.main+xml","DOCX_ACTIVE_CONTENT"),(MAIN.encode(),b"application/xml","DOCX_MAIN_TYPE_INVALID")):
            self.refused(edit(document(),{"[Content_Types].xml":lambda b:b.replace(old,new)}),code)
        self.refused(edit(document(),{"[Content_Types].xml":lambda b:b.replace(b'</Types>',b'<Default Extension="xml" ContentType="application/xml"/></Types>')}),"DOCX_CONTENT_TYPES_INVALID")

    def test_relationships_never_follow_external_or_ambiguous_targets(self):
        for target in (b"../word/document.xml",b"word/../word/document.xml",b"https://asset.example.invalid/document.xml",b"word/document.xml?x",b"word%2Fdocument.xml",b"word\\document.xml"):
            self.refused(edit(document(),{"_rels/.rels":lambda b:b.replace(b'word/document.xml',target,1)}),"DOCX_RELATIONSHIP_INVALID")
        self.refused(edit(document(),{"_rels/.rels":lambda b:b.replace(b'Target=',b'TargetMode="External" Target=',1)}),"DOCX_RELATIONSHIP_INVALID")
        self.refused(edit(document(),{"_rels/.rels":lambda b:b.replace(b'Id="core"',b'Id="main"')}),"DOCX_RELATIONSHIP_INVALID")
        self.refused(edit(document(),{"word/styles.xml":b"Opaque unbound style"}),"DOCX_UNBOUND_PART")

    def test_dtd_processing_instructions_comments_and_utf16_refuse(self):
        for prefix,code in (("<!DOCTYPE w:document [<!ENTITY fixture 'invented'>]>","XML_DECLARATION_FORBIDDEN"),("<?fixture invented?>","XML_PROCESSING_INSTRUCTION_FORBIDDEN"),("<!-- invented comment -->","XML_COMMENT_FORBIDDEN")):
            for encoding in ("utf-8","utf-16"):
                self.refused(edit(document(),{"word/document.xml":lambda b:(prefix+b.decode()).encode(encoding)}),code)

    def test_xml_depth_nodes_attributes_and_expanded_attribute_text_are_bounded(self):
        for xml in (("<r>"*33+"</r>"*33).encode(),b'<r '+b' '.join(('a'+str(i)+'="x"').encode() for i in range(33))+b'/>',b'<r>'+b'<a/>'*50000+b'</r>'):
            self.refused(edit(document(),{"word/document.xml":xml}),"XML_STRUCTURE_LIMIT")
        namespace="urn:fictional:"+"q"*230
        xml=('<w:document xmlns:w="'+W+'" xmlns:k="'+namespace+'"><w:body>'+('<w:p k:a="x"/>'*9000)+'</w:body></w:document>').encode()
        self.refused(edit(document(),{"word/document.xml":xml}),"XML_TEXT_LIMIT")

    def test_opaque_property_and_style_bytes_are_omitted_not_evaluated(self):
        parts=components();parts["docProps/core.xml"]=b"Opaque invented metadata <not even XML"
        parts["word/styles.xml"]=b"Opaque invented style containing https://asset.example.invalid/never"
        parts["word/_rels/document.xml.rels"]=('<Relationships xmlns="'+P+'"><Relationship Id="style" Type="'+R+'/styles" Target="styles.xml"/></Relationships>').encode()
        raw=zip_bytes(parts);self.write(raw);self.assertEqual(self.cli(tables=["table-1"],paragraphs=True),expected(raw,sample_blocks(),["table-1"],True))
        self.assertNotIn("Opaque",json.dumps(self.api()));self.assertNotIn("asset.example",json.dumps(self.cli()))

    def test_text_cell_column_and_row_boundaries_refuse_without_truncation(self):
        blocks=[dict(kind="table",rows=[["x"*4096]])];raw=document(blocks);self.write(raw);self.assertEqual(self.cli(tables=["table-1"]),expected(raw,blocks,["table-1"]))
        for blocks,code in (([dict(kind="paragraph",text="x"*4097)],"DOCX_TEXT_LIMIT"),([dict(kind="table",rows=[["x"]*33])],"DOCX_ROW_FEATURE_UNSUPPORTED"),([dict(kind="table",rows=[["x"]]*1002)],"DOCX_TABLE_FEATURE_UNSUPPORTED")):
            self.refused(document(blocks),code)
        for blocks in ([dict(kind="table",rows=[["x"]*32])],[dict(kind="table",rows=[["x"]]*1001)]):
            raw=document(blocks);self.write(raw);self.assertEqual(self.cli(),expected(raw,blocks))

    def test_global_paragraph_table_cell_and_text_counts_are_bounded(self):
        for blocks in ([dict(kind="paragraph",text="x")]*2001,[dict(kind="table",rows=[["x"]])]*33,[dict(kind="paragraph",text="x"*4096)]*257):
            self.refused(document(blocks),"DOCX_CONTENT_LIMIT")
        # This many cells reaches the earlier XML-node guard before extraction.
        self.refused(document([dict(kind="table",rows=[["x"]*20]*1001)]),"XML_STRUCTURE_LIMIT")
        blocks=[dict(kind="paragraph",text="x")]*2000;raw=document(blocks);self.write(raw);self.assertEqual(self.cli(),expected(raw,blocks))

    def test_actual_four_mebibyte_input_and_api_overflow_boundaries(self):
        parts=components();parts["docProps/core.xml"]=b"x"*2097152
        parts["word/styles.xml"]=b"";parts["word/_rels/document.xml.rels"]=('<Relationships xmlns="'+P+'"><Relationship Id="style" Type="'+R+'/styles" Target="styles.xml"/></Relationships>').encode()
        extra=4194304-len(zip_bytes(parts));self.assertTrue(0<extra<=2097152);parts["word/styles.xml"]=b"y"*extra
        raw=zip_bytes(parts);self.assertEqual(len(raw),4194304);self.write(raw);self.assertEqual(self.cli(),expected(raw,sample_blocks()));self.assertEqual(self.api(),expected(raw,sample_blocks()))
        self.write(raw+b"x");self.api(code=2,error="INPUT_LIMIT");self.cli(code=2,error="INPUT_SIZE_LIMIT" if os.name=="nt" else "INPUT_LIMIT")

    def test_active_merged_nested_nonrectangular_and_property_payloads_refuse(self):
        for markup in (b'<w:fldSimple/>',b'<w:ins/>',b'<w:hyperlink/>',b'<w:rPr><w:vanish/></w:rPr>'):
            self.refused(edit(document(),{"word/document.xml":lambda b:b.replace(b'<w:r>',b'<w:r>'+markup,1)}),"DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT")
        for markup in (b'<w:tbl/>',b'<w:tcPr><w:gridSpan w:val="2"/></w:tcPr>'):
            self.refused(edit(document(),{"word/document.xml":lambda b:b.replace(b'<w:tc>',b'<w:tc>'+markup,1)}))
        self.refused(document([dict(kind="table",rows=[["A","B"],["C"]])]),"DOCX_TABLE_NOT_RECTANGULAR")
        self.refused(edit(document(),{"word/document.xml":lambda b:b.replace(b'<w:p>',b'<w:p><w:pPr><w:t>Invented hidden payload</w:t></w:pPr>',1)}),"DOCX_PROPERTY_PAYLOAD_UNSUPPORTED")

    def test_fixed_errors_short_and_changed_reads_never_echo_private_paths(self):
        self.invoke(["--input",self.work/"FICTIONAL_PRIVATE_MISSING.docx"],code=2)
        self.cli(mode="short-read",code=2,error="INPUT_CHANGED");self.cli(mode="changed-stat",code=2,error="INPUT_CHANGED")
        self.cli(mode="output-budget",code=2,error="OUTPUT_LIMIT");self.assertFalse(self.output.exists())

    def test_retained_partial_report_is_not_confirmed_or_replaced(self):
        report=expected(self.input.read_bytes(),sample_blocks());self.cli(out=True,mode="write-failure",code=2,error="INPUT_OR_OUTPUT_REFUSED",allow=[self.output])
        self.assertEqual(self.output.read_bytes(),canonical(report)[:5]);self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),canonical(report)[:5])

    def test_no_overwrite_and_standalone_collection_source_output_guards(self):
        self.output.write_bytes(b"Invented preserved report");self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),b"Invented preserved report")
        self.invoke(["--input",self.input,"--out",self.input],code=2)
        for target in (self.copy/"new.json",self.copy/"toolkit.py"):
            self.invoke(["--input",self.input,"--out",target],code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE")
        collection=self.owned(self.work/"collection");selected=collection/"tools/docx-table-extractor";selected.mkdir(parents=True);(collection/"systems").mkdir();(collection/"catalog").mkdir();(collection/"catalog/registry.json").write_bytes(b"{}\n")
        for name in RUNTIME:(selected/name).write_bytes((self.copy/name).read_bytes())
        target=collection/"refused.json";self.invoke(["--input",self.input,"--out",target],base=selected,code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE");self.assertFalse(target.exists())

    def test_mandatory_hardlink_inputs_and_existing_outputs_are_refused(self):
        alias=self.owned(self.work/"hardlinked.docx");os.link(self.input,alias);self.assertTrue(alias.samefile(self.input))
        for path in (self.input,alias):self.invoke(["--input",path],code=2,error="CONTROL_NOT_SINGLE_LINK" if os.name=="nt" else "INPUT_UNSAFE")
        self.invoke(["--out",alias],mode="generator",code=2)

    def test_linked_parent_read_and_report_routes_are_refused(self):
        target=self.owned(self.work/"target");target.mkdir();(target/"input.docx").write_bytes(document());route=self.owned(self.work/"route")
        if os.name=="nt":
            done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(route),str(target)],capture_output=True,timeout=15);self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:route.rmdir() if route.exists() else None)
        else:route.symlink_to(target,target_is_directory=True)
        self.invoke(["--input",route/"input.docx"],code=2);self.invoke(["--input",self.input,"--out",route/"new.json"],code=2);self.assertFalse((target/"new.json").exists())

    def test_native_leaf_symlink_and_dangling_output_refusal(self):
        link=self.owned(self.work/"linked.docx");self.symlink(link,self.input);self.invoke(["--input",link],code=2);original=self.input.read_bytes()
        for name,target in (("dangling",self.work/"never-created.json"),("source-pointing",self.copy/"never-created.json")):
            target=self.owned(target);self.assertFalse(os.path.lexists(target));route=self.owned(self.work/(name+".json"));self.symlink(route,target)
            self.invoke(["--input",self.input,"--out",route],code=2);self.assertFalse(os.path.lexists(target),"Refused output must not create a symlink target");self.assertTrue(route.is_symlink())
        for name,target in (("input-pointing",self.input),("runtime-pointing",self.copy/"toolkit.py")):
            target=self.owned(target);raw=target.read_bytes();route=self.owned(self.work/(name+".json"));self.symlink(route,target);self.invoke(["--input",self.input,"--out",route],code=2);self.assertEqual(target.read_bytes(),raw)
        self.assertEqual(self.input.read_bytes(),original)

    @unittest.skipUnless(os.name=="nt",WINDOWS_REASON)
    def test_native_windows_path_grammar_and_named_stream_routes(self):
        for path in (str(self.input)+":stream",str(self.work/"CON"),str(self.input)+".",str(self.input)+" ","x:relative","//example.invalid/share"):
            self.invoke(["--input",path],code=2)
        self.invoke(["--input",self.input,"--out",str(self.output)+":stream"],code=2)

    @unittest.skipUnless(os.name!="nt",POSIX_REASON)
    def test_native_posix_special_inputs_and_private_report_mode(self):
        fifo=self.owned(self.work/"fictional.fifo");os.mkfifo(fifo);sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.owned(self.work/"s")));self.addCleanup(sock.close)
        for path in (fifo,self.work/"s",self.work):self.invoke(["--input",path],code=2)
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
    if strict is None:strict=os.name!="nt" or os.environ.get("OUTLANDS_DOCX_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
    assert type(strict) is bool
    Download.strict_links=os.name!="nt" or strict;Download.native_events=[]
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Download);ids=[test.id() for test in flatten(suite)]
    assert len(ids)==len(set(ids))==30 and all(name.startswith("test_download.Download.test_") for name in ids)
    assert all(name in set(ids) for name,reason in REQUIRED_WINDOWS_SKIPS|REQUIRED_POSIX_SKIPS|OPTIONAL_WINDOWS_LINK_SKIPS)
    assert FLOW_IDS|COMMON_NATIVE_IDS<=set(ids)
    return suite


def run_copied_tests(strict=None,log_stream=None):
    suite=load_copied_suite(strict);strict=Download.strict_links;ids=[test.id() for test in flatten(suite)]
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
        all_selected_tests_started=all_started,successful_ids_exclude_setup_failures=valid_successes,module_counts={"test_download":30},native_links_required=strict,native_fixture_events=Download.native_events,
        fictional_docx_flow_checked=flow_checked,native_file_guards_checked=native_checked,fictional_docx_flow_test_ids=sorted(FLOW_IDS),native_file_guard_test_ids=sorted(native),
        positive_asserted_test_ids=dict(fictional_docx_flow_checked=sorted(FLOW_IDS),native_file_guards_checked=sorted(native)),copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,
        **{name:False for name in FALSE_FLAGS})


if __name__=="__main__":raise SystemExit(0 if run_copied_tests()["status"]=="PASS" else 1)
