"""Independent positional DOCX diff consumers on invented packages; no Office or real documents. MIT."""
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
RUNTIME=("document_diff.py","docx_core.py","toolkit.py","native_windows.py","fictional_docx.py")
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
FALSE_FLAGS=("real_documents_used","document_properties_compared","formatting_compared","document_executed",
             "external_resources_followed","office_processes_started","archives_extracted","visible_layout_verified",
             "semantic_move_detection_verified","production_workflows_verified")
FLOW_IDS={"test_copied_cli.CopiedCLI.test_fictional_generator_variants_and_exact_report_readback",
          "test_copied_cli.CopiedCLI.test_default_changed_block_hashes_omit_all_body_and_property_values",
          "test_copied_cli.CopiedCLI.test_positional_added_removed_and_kind_changed_blocks"}
COMMON_NATIVE_IDS={"test_copied_cli.CopiedCLI.test_no_overwrite_and_standalone_collection_source_output_guards",
                   "test_copied_cli.CopiedCLI.test_retained_partial_report_is_not_confirmed_or_replaced",
                   "test_copied_cli.CopiedCLI.test_mandatory_hardlink_inputs_and_existing_outputs_are_refused",
                   "test_copied_cli.CopiedCLI.test_linked_parent_read_and_report_routes_are_refused"}


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



def model(blocks):
    result=[];paragraphs=tables=rows=cells=0
    for block in blocks:
        if block["kind"]=="paragraph":
            paragraphs+=1;result.append(dict(id="paragraph-"+str(paragraphs),position=len(result)+1,kind="paragraph",text=block["text"]))
        else:
            tables+=1;rows+=len(block["rows"]);cells+=sum(map(len,block["rows"]))
            result.append(dict(id="table-"+str(tables),position=len(result)+1,kind="table",rows=block["rows"]))
    return result,dict(paragraphs=paragraphs,tables=tables,rows=rows,cells=cells)


def expected(before_raw,before_blocks,after_raw,after_blocks,specs=(),values=False):
    # Positions, classifications and changed-cell coordinates are authored by each case.
    # This serializes the specified observations; it never matches or classifies blocks.
    before,bc=model(before_blocks);after,ac=model(after_blocks)
    def summary(block):
        if block is None:return None
        result=dict(kind=block["kind"],id=block["id"],sha256=sha(canonical(block)))
        if block["kind"]=="table":result.update(rows=len(block["rows"]),columns=len(block["rows"][0]))
        if values:result["value"]=block["text"] if block["kind"]=="paragraph" else block["rows"]
        return result
    changes=[]
    for position,classification,coordinates in specs:
        old=before[position-1] if position<=len(before) else None
        new=after[position-1] if position<=len(after) else None
        row=dict(position=position,classification=classification,before=summary(old),after=summary(new))
        if coordinates is not None:
            cells=[]
            for r,c in coordinates:
                left=old["rows"][r-1][c-1] if r<=len(old["rows"]) and c<=len(old["rows"][r-1]) else None
                right=new["rows"][r-1][c-1] if r<=len(new["rows"]) and c<=len(new["rows"][r-1]) else None
                cell=dict(row=r,column=c,before_sha256=sha(canonical(left)) if left is not None else None,
                          after_sha256=sha(canonical(right)) if right is not None else None)
                if values:cell.update(before=left,after=right)
                cells.append(cell)
            row["cell_changes"]=cells
        changes.append(row)
    return dict(format="outlands-document-diff-v1",status="DIFFERENCES" if specs else "MATCH",
        comparison="SUPPORTED_STORED_CONTENT_BY_POSITION",before_source_sha256=sha(before_raw),after_source_sha256=sha(after_raw),
        raw_bytes_changed=before_raw!=after_raw,before_content_sha256=sha(canonical(before)),after_content_sha256=sha(canonical(after)),
        before_counts=bc,after_counts=ac,changes=changes,values_included=values,
        document_properties_compared=False,formatting_compared=False,document_executed=False)


CHILD=r'''
import _elementtree,hashlib,importlib.metadata,json,os,pyexpat,runpy,sys,zipfile,zlib
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
import document_diff as a
import docx_core as d
import fictional_docx as g
import toolkit as t
import native_windows as n
for module,name in ((a,'document_diff.py'),(d,'docx_core.py'),(g,'fictional_docx.py'),(t,'toolkit.py'),(n,'native_windows.py')):
 assert Path(module.__file__).resolve()==base/name
assert a.docx_core is d and a.t is d.t is g.t is t and d.zipfile is g.zipfile is zipfile and d.zlib is zlib
assert a.compare.__globals__ is a.__dict__ and d.extract.__globals__ is d.__dict__
assert t.read.__globals__ is t.__dict__ and t.write_new.__globals__ is t.__dict__
def xml_bindings():
 assert t.ET.XMLParser is _elementtree.XMLParser and t.ET.TreeBuilder is _elementtree.TreeBuilder
 assert t.XMLBuilder.__mro__[1] is _elementtree.TreeBuilder and len(pyexpat.version_info)==3
 return (t.ET.XMLParser,t.ET.TreeBuilder,t.XMLBuilder.__mro__[1],pyexpat.EXPAT_VERSION)
initial_xml=xml_bindings()
try:
 if mode=='affinity':
  sys.stdout.write(t.encode(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=5)).decode());raise SystemExit(0)
 if mode=='generator':
  sys.argv=[str(base/'fictional_docx.py'),*args]
  runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('GENERATOR_ENTRYPOINT_DID_NOT_EXIT')
 if mode=='api':
  before=Path(args[0]);after=Path(args[1]);assert before.is_absolute() and after.is_absolute()
  try:value=a.compare(before.read_bytes(),after.read_bytes(),json.loads(args[2]))
  except t.Rejected as error:sys.stdout.write(t.encode(dict(status='ERROR',code=str(error))).decode());raise SystemExit(2)
  sys.stdout.write(t.encode(value).decode());raise SystemExit(1 if value['status']=='DIFFERENCES' else 0)
 if mode.startswith(('short-read-','changed-stat-')):
  role=mode.rsplit('-',1)[1];path=Path(args[args.index('--'+role)+1]);selected=path.stat();identity=(selected.st_dev,selected.st_ino)
  original_read=os.read;original_stat=os.fstat;changed=False
  def selected_fd(fd):
   info=original_stat(fd);return (info.st_dev,info.st_ino)==identity
  def read(fd,*rest):
   global changed
   if mode.startswith('short-read-') and selected_fd(fd):return b''
   raw=original_read(fd,*rest)
   if raw and selected_fd(fd):changed=True
   return raw
  def info(fd):
   value=original_stat(fd)
   if not changed or (value.st_dev,value.st_ino)!=identity:return value
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
 sys.argv=[str(base/'document_diff.py'),*args]
 runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('DIFF_ENTRYPOINT_DID_NOT_EXIT')
finally:assert xml_bindings()==initial_xml
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
        self.temp=tempfile.TemporaryDirectory(prefix="document-diff-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.assertEqual(self.work.parent,parent);self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();(self.copy/name).write_bytes(raw);self.pins[name]=sha(raw)
        self.before=self.work/"before.docx";self.after=self.work/"after.docx"
        self.before.write_bytes(document());self.after.write_bytes(document());self.output=self.work/"summary.json"
        self.env={key:value for key,value in os.environ.items() if not key.upper().startswith(("PYTHON","PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHON_COLORS="0",NO_COLOR="1");self.addCleanup(self.runtime_preserved)
    def runtime_preserved(self):
        self.assertEqual({p.name for p in self.copy.iterdir()},set(RUNTIME));self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME},self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")),[])
    def owned(self,path):
        path=Path(path);self.assertTrue(path.is_absolute() and path.resolve().is_relative_to(self.work));return path
    def write(self,before,after=None):self.before.write_bytes(before);self.after.write_bytes(before if after is None else after)
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
        elif value.get("format")=="outlands-document-diff-v1":
            for key in ("document_properties_compared","formatting_compared","document_executed"):self.assertIs(value[key],False)
            self.assertEqual(value["before_source_sha256"],sha(self.before.read_bytes()));self.assertEqual(value["after_source_sha256"],sha(self.after.read_bytes()))
        return value
    def arguments(self,before=None,after=None):return ["--before",self.before if before is None else before,"--after",self.after if after is None else after]
    def cli(self,*,values=False,out=False,**options):
        args=self.arguments()
        if values:args.append("--show-values")
        if out:args.extend(["--out",self.output])
        return self.invoke(args,**options)
    def api(self,*,values=False,**options):return self.invoke([self.before,self.after,json.dumps(values)],mode="api",**options)
    def check(self,before_blocks,after_blocks,specs=(),values=False,raws=None,api=False):
        before,after=raws if raws is not None else (document(before_blocks),document(after_blocks));self.write(before,after)
        want=expected(before,before_blocks,after,after_blocks,specs,values);code=1 if specs else 0
        self.assertEqual(self.cli(values=values,code=code),want)
        if api:self.assertEqual(self.api(values=values,code=code),want)
        return want
    def refused(self,raw,code=None):
        for role in ("before","after"):
            self.write(document());getattr(self,role).write_bytes(raw)
            self.api(code=2,error=code);self.cli(out=True,code=2,error=code);self.assertFalse(self.output.exists())
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            strict=self.strict_links if self.strict_links is not None else os.name!="nt" or os.environ.get("OUTLANDS_DOCUMENT_DIFF_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
            actual=os.name=="nt" and getattr(error,"winerror",None)==1314
            if actual and not strict:
                self.assertEqual(self.id(),LINK_ID);self.assertFalse(directory);self.native_events.append(dict(test=self.id(),reason=LINK_REASON,policy="actual_windows_1314",actual_windows_1314=True,winerror=1314,strict=False,provenance="test_copied_cli.CopiedCLI.symlink/caught-OSError"));self.skipTest(LINK_REASON)
            raise


    def test_copied_affinity_and_both_entrypoint_help_are_inert(self):
        self.assertEqual(self.invoke(mode="affinity"),dict(status="COPIED_RUNTIME_AFFINITY",runtime_files=5))
        self.assertIn("--before",self.invoke(["--help"],text=True));self.assertIn("--after",self.invoke(["--help"],text=True));self.assertIn("--variant",self.invoke(["--help"],mode="generator",text=True))
        for mode in ("normal","generator"):
            self.invoke(mode=mode,code=2,error="ARGUMENTS_INVALID");self.invoke(["--unknown","FICTIONAL_PRIVATE_SENTINEL"],mode=mode,code=2,error="ARGUMENTS_INVALID")
        self.invoke(["--before",self.before],code=2,error="ARGUMENTS_INVALID");self.invoke(["--after",self.after],code=2,error="ARGUMENTS_INVALID")

    def test_fictional_generator_variants_and_exact_report_readback(self):
        generated={}
        for variant in ("before","after","needs-review","formatting"):
            target=self.owned(self.work/(variant+"-generated.docx"));value=self.invoke(["--out",target,"--variant",variant],mode="generator",allow=[target]);raw=target.read_bytes()
            self.assertEqual(value,dict(status="PASS",fictional=True,bytes=len(raw),sha256=sha(raw)));blocks=sample_blocks()
            if variant in ("after","needs-review"):
                rows=[["Record","Units","Due","Active"]]+([["sample-a","14","2030-01-10","true"],["sample-c","5","2030-01-12","true"]] if variant=="after" else [["sample-a","12","2030-01-10","true"],["sample-a","13","2030-01-10","true"],["sample-c","invalid","2030-01-12","true"]])
                blocks=[dict(kind="paragraph",text="Fictional revised intake example."),dict(kind="table",rows=rows)]
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                self.assertEqual({name:archive.read(name) for name in archive.namelist()},components(blocks,bold=variant=="formatting"))
                self.assertTrue(all(info.date_time==(2030,1,1,0,0,0) and info.compress_type==zipfile.ZIP_DEFLATED for info in archive.infolist()))
            generated[variant]=(raw,blocks);self.invoke(["--out",target],mode="generator",code=2)
        raw,blocks=generated["before"]
        for variant,specs in (("before",[]),("formatting",[]),("after",[(1,"CHANGED",None),(2,"CHANGED",[(2,2),(3,1),(3,2),(3,3),(3,4),(4,1),(4,2),(4,3),(4,4)])]),("needs-review",[(1,"CHANGED",None),(2,"CHANGED",[(3,1),(3,2),(3,3),(3,4),(4,1),(4,2),(4,3)])])):
            other,other_blocks=generated[variant];report=self.check(blocks,other_blocks,specs,True,raws=(raw,other))
        self.assertEqual(self.cli(values=True,out=True,code=1,allow=[self.output]),dict(status="DIFFERENCES",report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))

    def test_default_changed_block_hashes_omit_all_body_and_property_values(self):
        before=[dict(kind="paragraph",text="Fictional undisclosed before"),dict(kind="table",rows=[["Fictional undisclosed cell"]])]
        after=[dict(kind="paragraph",text="Fictional undisclosed after"),dict(kind="table",rows=[["Fictional undisclosed replacement"]])]
        value=self.check(before,after,[(1,"CHANGED",None),(2,"CHANGED",[(1,1)])],api=True)
        self.assertNotIn("undisclosed",json.dumps(value));self.assertEqual(value["before_counts"],dict(paragraphs=1,tables=1,rows=1,cells=1))
        self.assertEqual(set(value["changes"][0]["before"]),{"kind","sha256","id"});self.assertEqual(set(value["changes"][1]["before"]),{"kind","sha256","id","rows","columns"})

    def test_unicode_whitespace_tabs_line_breaks_empty_text_and_cell_paragraphs(self):
        before=[dict(kind="paragraph",text=""),dict(kind="table",rows=[["First"]])]
        after=[dict(kind="paragraph",text="  café λ 🧪 & <script>literal</script>  "),dict(kind="table",rows=[["First"]])]
        raw=edit(document(after),{"word/document.xml":lambda b:b.replace(b'</w:t>',b'</w:t><w:tab/><w:t>Next</w:t><w:br/><w:t>Last</w:t>',1).replace(b'</w:tc>',b'<w:p><w:r><w:t>Second</w:t></w:r></w:p></w:tc>',1)})
        after[0]["text"]+="\tNext\nLast";after[1]["rows"][0][0]="First\nSecond"
        want=self.check(before,after,[(1,"CHANGED",None),(2,"CHANGED",[(1,1)])],True,raws=(document(before),raw),api=True)
        self.cli(values=True,out=True,code=1,allow=[self.output]);self.assertEqual(self.output.read_bytes(),canonical(want));self.assertTrue(self.output.read_bytes().isascii());self.assertIn(b"\\ud83e\\uddea",self.output.read_bytes())

    def test_formatting_property_and_container_changes_preserve_supported_content(self):
        blocks=sample_blocks();first=document(blocks);second=document(blocks,author="Invented changed author",bold=True)
        value=self.check(blocks,blocks,raws=(first,second),api=True);self.assertTrue(value["raw_bytes_changed"]);self.assertEqual(value["before_content_sha256"],value["after_content_sha256"])
        parts=components(blocks);parts["docProps/core.xml"]=b"Opaque private-looking fictional <not-XML"
        parts["word/styles.xml"]=b"Opaque style https://asset.example.invalid/never"
        parts["word/_rels/document.xml.rels"]=('<Relationships xmlns="'+P+'"><Relationship Id="style" Type="'+R+'/styles" Target="styles.xml"/></Relationships>').encode()
        self.check(blocks,blocks,raws=(first,zip_bytes(parts)),values=True)
        self.check(blocks,blocks,raws=(first,zip_bytes(list(reversed(list(components(blocks).items()))),zipfile.ZIP_DEFLATED)))

    def test_positional_added_removed_and_kind_changed_blocks(self):
        p=dict(kind="paragraph",text="A");q=dict(kind="paragraph",text="B");table=dict(kind="table",rows=[["A"]])
        self.check([p],[p,q],[(2,"ADDED",None)],True,api=True);self.check([p,q],[p],[(2,"REMOVED",None)],True)
        self.check([p],[table],[(1,"KIND_CHANGED",None)],True);self.check([table],[p],[(1,"KIND_CHANGED",None)])

    def test_insertions_reorders_and_renumbered_ids_remain_positional(self):
        a=dict(kind="paragraph",text="A");b=dict(kind="paragraph",text="B");t=dict(kind="table",rows=[["same"]])
        self.check([a,b],[b,a],[(1,"CHANGED",None),(2,"CHANGED",None)],True)
        self.check([a,b],[dict(kind="paragraph",text="Inserted"),a,b],[(1,"CHANGED",None),(2,"CHANGED",None),(3,"ADDED",None)],True)
        value=self.check([a,t],[t,t],[(1,"KIND_CHANGED",None),(2,"CHANGED",[])],True)
        self.assertEqual(value["changes"][1]["cell_changes"],[]);self.assertEqual(value["changes"][1]["before"]["value"],value["changes"][1]["after"]["value"])
        self.assertNotIn("MOVED",json.dumps(value));self.check([t,a],[a,a],[(1,"KIND_CHANGED",None),(2,"CHANGED",None)])

    def test_cell_coordinates_distinguish_missing_rows_columns_and_empty_strings(self):
        before=[dict(kind="table",rows=[["A",""],["x","1"]])];after=[dict(kind="table",rows=[["A",""],["x","2"],["",""]])]
        value=self.check(before,after,[(1,"CHANGED",[(2,2),(3,1),(3,2)])],True,api=True)
        cell=value["changes"][0]["cell_changes"][1];self.assertIsNone(cell["before"]);self.assertIsNone(cell["before_sha256"]);self.assertEqual(cell["after"],"");self.assertEqual(cell["after_sha256"],sha(canonical("")))
        self.check(after,before,[(1,"CHANGED",[(2,2),(3,1),(3,2)])],True)
        self.check([dict(kind="table",rows=[[""]])],[dict(kind="table",rows=[["",""]])],[(1,"CHANGED",[(1,2)])],True)

    def test_table_reshape_counts_and_unchanged_cells_use_exact_coordinates(self):
        before=[dict(kind="table",rows=[["A","B"],["C","D"]])];after=[dict(kind="table",rows=[["A","B","C","D"]])]
        self.check(before,after,[(1,"CHANGED",[(1,3),(1,4),(2,1),(2,2)])],True,api=True)
        self.check(before,[dict(kind="table",rows=[["A","B"],["C","changed"]])],[(1,"CHANGED",[(2,2)])])

    def test_exact_512_changed_blocks_succeed_and_513_globally_refuse(self):
        before=[dict(kind="paragraph",text="A")]*512;after=[dict(kind="paragraph",text="B")]*512
        self.check(before,after,[(i,"CHANGED",None) for i in range(1,513)])
        self.write(document(before+[before[0]]),document(after+[after[0]]))
        for values in (False,True):self.cli(values=values,out=True,code=2,error="BLOCK_CHANGE_LIMIT");self.assertFalse(self.output.exists())
        self.api(code=2,error="BLOCK_CHANGE_LIMIT")

    def test_exact_4096_changed_cells_succeed_and_4097_globally_refuse(self):
        before=[dict(kind="table",rows=[["A"]*32 for unused in range(128)])];after=[dict(kind="table",rows=[["B"]*32 for unused in range(128)])]
        coordinates=[(r,c) for r in range(1,129) for c in range(1,33)];self.check(before,after,[(1,"CHANGED",coordinates)])
        before[0]["rows"].append(["A"]*32);after[0]["rows"].append(["B"]+["A"]*31);self.write(document(before),document(after))
        for values in (False,True):self.cli(values=values,out=True,code=2,error="CELL_CHANGE_LIMIT");self.assertFalse(self.output.exists())
        self.api(code=2,error="CELL_CHANGE_LIMIT")

    def test_cell_cap_is_per_changed_table_and_unchanged_blocks_do_not_consume_changes(self):
        a=dict(kind="table",rows=[["A"]*32 for unused in range(128)]);b=dict(kind="table",rows=[["B"]*32 for unused in range(128)])
        coords=[(r,c) for r in range(1,129) for c in range(1,33)];value=self.check([a,a],[b,b],[(1,"CHANGED",coords),(2,"CHANGED",coords)])
        self.assertEqual(sum(len(row["cell_changes"]) for row in value["changes"]),8192)
        same=dict(kind="paragraph",text="same");self.check([same]*1000+[dict(kind="paragraph",text="A")],[same]*1000+[dict(kind="paragraph",text="B")],[(1001,"CHANGED",None)])

    def test_both_full_documents_are_validated_before_any_partial_comparison(self):
        valid=document([dict(kind="paragraph",text="A")]*513)
        invalid=edit(document([dict(kind="paragraph",text="B")]*513),{"word/document.xml":lambda raw:raw.replace(b'</w:body>',b'<w:unknown/></w:body>')})
        for role in ("before","after"):
            self.write(valid);getattr(self,role).write_bytes(invalid);self.cli(out=True,code=2,error="DOCX_BODY_FEATURE_UNSUPPORTED");self.api(code=2,error="DOCX_BODY_FEATURE_UNSUPPORTED");self.assertFalse(self.output.exists())
        self.refused(document([]),"DOCX_EMPTY_DOCUMENT")

    def test_invalid_truncated_and_corrupt_crc_archives_have_fixed_errors(self):
        for raw in (b"Invented not ZIP",document()[:50]):self.refused(raw,"DOCX_ARCHIVE_INVALID")
        raw=bytearray(document());raw[raw.index(b"Fictional intake example.")]^=1;self.refused(bytes(raw),"DOCX_ARCHIVE_INVALID")

    def test_duplicate_traversal_active_compression_and_special_zip_parts_refuse(self):
        parts=components()
        with self.assertWarns(UserWarning):raw=zip_bytes([*parts.items(),("word/document.xml",parts["word/document.xml"])])
        self.refused(raw,"DOCX_ARCHIVE_INVALID")
        for name in ("../fictional.xml","word/vbaProject.bin","word/media/image1.png","customXml/item1.xml"):
            self.refused(zip_bytes(dict(parts,**{name:b"Invented refused bytes"})),"DOCX_PART_UNSUPPORTED")
        for kind in ("encrypted","compression","symlink"):
            raw=bytearray(document())
            if kind=="encrypted":
                for signature,offset in ((b"PK\x03\x04",6),(b"PK\x01\x02",8)):
                    position=raw.index(signature);struct.pack_into("<H",raw,position+offset,struct.unpack_from("<H",raw,position+offset)[0]|1)
            elif kind=="compression":
                for signature,offset in ((b"PK\x03\x04",8),(b"PK\x01\x02",10)):struct.pack_into("<H",raw,raw.index(signature)+offset,99)
            else:struct.pack_into("<I",raw,raw.index(b"PK\x01\x02")+38,(stat.S_IFLNK|0o777)<<16)
            self.refused(bytes(raw),"DOCX_PART_UNSUPPORTED")
        with self.assertWarns(UserWarning):raw=zip_bytes([("word/document.xml",b"x")]*65)
        self.refused(raw,"DOCX_ARCHIVE_INVALID")

    def test_expanded_part_ratio_and_total_budgets_refuse_in_both_roles(self):
        parts=components();parts["docProps/core.xml"]=b"x"*2097153;self.refused(zip_bytes(parts),"DOCX_EXPANSION_LIMIT")
        parts=components();parts["docProps/core.xml"]=b"x"*100000;self.refused(zip_bytes(parts,zipfile.ZIP_DEFLATED),"DOCX_EXPANSION_LIMIT")
        payload=random.Random(734).randbytes(16384)*128;parts=components()
        for name in ("docProps/core.xml","docProps/app.xml","word/styles.xml","word/settings.xml","word/fontTable.xml"):parts[name]=payload
        self.refused(zip_bytes(parts,zipfile.ZIP_DEFLATED),"DOCX_EXPANSION_LIMIT")

    def test_required_parts_types_and_relationship_targets_are_explicit(self):
        for name in ("[Content_Types].xml","_rels/.rels","word/document.xml"):
            parts=components();parts.pop(name);self.refused(zip_bytes(parts),"DOCX_REQUIRED_PART_MISSING")
        self.refused(edit(document(),{"[Content_Types].xml":lambda raw:raw.replace(MAIN.encode(),b"application/vnd.ms-word.document.macroEnabled.main+xml")}),"DOCX_ACTIVE_CONTENT")
        self.refused(edit(document(),{"[Content_Types].xml":lambda raw:raw.replace(MAIN.encode(),b"application/xml")}),"DOCX_MAIN_TYPE_INVALID")
        for target in (b"../word/document.xml",b"https://asset.example.invalid/document.xml",b"word/document.xml?x",b"word%2Fdocument.xml",b"word\\document.xml"):
            self.refused(edit(document(),{"_rels/.rels":lambda raw:raw.replace(b'word/document.xml',target,1)}),"DOCX_RELATIONSHIP_INVALID")
        self.refused(edit(document(),{"_rels/.rels":lambda raw:raw.replace(b'Target=',b'TargetMode="External" Target=',1)}),"DOCX_RELATIONSHIP_INVALID")
        self.refused(edit(document(),{"word/styles.xml":b"Opaque unbound style"}),"DOCX_UNBOUND_PART")

    def test_xml_declarations_processing_instructions_comments_and_structure_are_bounded(self):
        for prefix,code in (("<!DOCTYPE w:document [<!ENTITY fixture 'invented'>]>","XML_DECLARATION_FORBIDDEN"),("<?fixture invented?>","XML_PROCESSING_INSTRUCTION_FORBIDDEN"),("<!-- invented comment -->","XML_COMMENT_FORBIDDEN")):
            for encoding in ("utf-8","utf-16"):self.refused(edit(document(),{"word/document.xml":lambda raw:(prefix+raw.decode()).encode(encoding)}),code)
        for xml in (("<r>"*33+"</r>"*33).encode(),b'<r '+b' '.join(('a'+str(i)+'="x"').encode() for i in range(33))+b'/>',b'<r>'+b'<a/>'*50000+b'</r>'):
            self.refused(edit(document(),{"word/document.xml":xml}),"XML_STRUCTURE_LIMIT")
        namespace="urn:fictional:"+"q"*230;xml=('<w:document xmlns:w="'+W+'" xmlns:k="'+namespace+'"><w:body>'+('<w:p k:a="x"/>'*9000)+'</w:body></w:document>').encode()
        self.refused(edit(document(),{"word/document.xml":xml}),"XML_TEXT_LIMIT")

    def test_active_merged_nested_namespace_and_property_payloads_refuse(self):
        for markup in (b'<w:fldSimple/>',b'<w:ins/>',b'<w:hyperlink/>',b'<w:rPr><w:vanish/></w:rPr>',b'<w:object/>'):
            self.refused(edit(document(),{"word/document.xml":lambda raw:raw.replace(b'<w:r>',b'<w:r>'+markup,1)}),"DOCX_ACTIVE_OR_UNSUPPORTED_CONTENT")
        for markup in (b'<w:tbl/>',b'<w:tcPr><w:gridSpan w:val="2"/></w:tcPr>'):
            self.refused(edit(document(),{"word/document.xml":lambda raw:raw.replace(b'<w:tc>',b'<w:tc>'+markup,1)}))
        self.refused(document([dict(kind="table",rows=[["A","B"],["C"]])]),"DOCX_TABLE_NOT_RECTANGULAR")
        self.refused(edit(document(),{"word/document.xml":lambda raw:raw.replace(b'<w:p>',b'<w:p><w:pPr><w:t>Invented hidden payload</w:t></w:pPr>',1)}),"DOCX_PROPERTY_PAYLOAD_UNSUPPORTED")
        self.refused(edit(document(),{"word/document.xml":lambda raw:raw.replace(W.encode(),b"urn:fictional:unsupported")}),"DOCX_DOCUMENT_INVALID")

    def test_core_text_row_column_and_global_budgets_refuse_without_truncation(self):
        for blocks,code in (([dict(kind="paragraph",text="x"*4097)],"DOCX_TEXT_LIMIT"),([dict(kind="table",rows=[["x"]*33])],"DOCX_ROW_FEATURE_UNSUPPORTED"),([dict(kind="table",rows=[["x"]]*1002)],"DOCX_TABLE_FEATURE_UNSUPPORTED"),([dict(kind="paragraph",text="x")]*2001,"DOCX_CONTENT_LIMIT"),([dict(kind="table",rows=[["x"]])]*33,"DOCX_CONTENT_LIMIT"),([dict(kind="paragraph",text="x"*4096)]*257,"DOCX_CONTENT_LIMIT")):
            self.refused(document(blocks),code)
        for blocks in ([dict(kind="paragraph",text="x"*4096)],[dict(kind="table",rows=[["x"]*32])],[dict(kind="table",rows=[["x"]]*1001)],[dict(kind="paragraph",text="x")]*2000):self.check(blocks,blocks)
        self.refused(document([dict(kind="table",rows=[["x"]*20]*1001)]),"XML_STRUCTURE_LIMIT")

    def test_actual_four_mebibyte_inputs_and_strict_boolean_api_options(self):
        parts=components();parts["docProps/core.xml"]=b"x"*2097152;parts["word/styles.xml"]=b""
        parts["word/_rels/document.xml.rels"]=('<Relationships xmlns="'+P+'"><Relationship Id="style" Type="'+R+'/styles" Target="styles.xml"/></Relationships>').encode()
        extra=4194304-len(zip_bytes(parts));self.assertTrue(0<extra<=2097152);parts["word/styles.xml"]=b"y"*extra;raw=zip_bytes(parts);self.assertEqual(len(raw),4194304)
        self.check(sample_blocks(),sample_blocks(),raws=(raw,raw),api=True)
        for role in ("before","after"):
            self.write(document());getattr(self,role).write_bytes(raw+b"x");self.api(code=2,error="INPUT_LIMIT");self.cli(out=True,code=2,error="INPUT_SIZE_LIMIT" if os.name=="nt" else "INPUT_LIMIT");self.assertFalse(self.output.exists())
        self.write(document())
        for value in (0,1,"true",None,[],{}):self.api(values=value,code=2,error="OPTION_INVALID")

    def test_fixed_private_errors_and_selected_role_read_mutations(self):
        for role in ("before","after"):
            paths={role:self.work/"FICTIONAL_PRIVATE_MISSING.docx"};self.invoke(self.arguments(**paths),code=2)
            for mode in ("short-read-","changed-stat-"):self.cli(out=True,mode=mode+role,code=2,error="INPUT_CHANGED");self.assertFalse(self.output.exists())
        self.cli(mode="output-budget",code=2,error="OUTPUT_LIMIT");self.assertFalse(self.output.exists())

    def test_retained_partial_report_is_not_confirmed_or_replaced(self):
        want=expected(self.before.read_bytes(),sample_blocks(),self.after.read_bytes(),sample_blocks());self.cli(out=True,mode="write-failure",code=2,error="INPUT_OR_OUTPUT_REFUSED",allow=[self.output])
        self.assertEqual(self.output.read_bytes(),canonical(want)[:5]);self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),canonical(want)[:5])

    def test_no_overwrite_and_standalone_collection_source_output_guards(self):
        self.output.write_bytes(b"Invented preserved report");self.cli(out=True,code=2);self.assertEqual(self.output.read_bytes(),b"Invented preserved report")
        for target in (self.before,self.after):self.invoke([*self.arguments(),"--out",target],code=2)
        for target in (self.copy/"new.json",self.copy/"toolkit.py"):
            self.invoke([*self.arguments(),"--out",target],code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE")
        collection=self.owned(self.work/"collection");selected=collection/"tools/document-content-diff";selected.mkdir(parents=True);(collection/"systems").mkdir();(collection/"catalog").mkdir();(collection/"catalog/registry.json").write_bytes(b"{}\n")
        for name in RUNTIME:(selected/name).write_bytes((self.copy/name).read_bytes())
        target=collection/"refused.json";self.invoke([*self.arguments(),"--out",target],base=selected,code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE");self.assertFalse(target.exists())

    def test_mandatory_hardlink_inputs_and_existing_outputs_are_refused(self):
        for role in ("before","after"):
            source=getattr(self,role);alias=self.owned(self.work/(role+"-hardlinked.docx"));os.link(source,alias);self.assertTrue(alias.samefile(source))
            for path in (source,alias):self.invoke(self.arguments(**{role:path}),code=2,error="CONTROL_NOT_SINGLE_LINK" if os.name=="nt" else "INPUT_UNSAFE")
            self.invoke(["--out",alias],mode="generator",code=2);alias.unlink();self.assertEqual(source.stat().st_nlink,1)

    def test_linked_parent_read_and_report_routes_are_refused(self):
        target=self.owned(self.work/"target");target.mkdir();(target/"input.docx").write_bytes(document());route=self.owned(self.work/"route")
        if os.name=="nt":
            done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(route),str(target)],capture_output=True,timeout=15);self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:route.rmdir() if route.exists() else None)
        else:route.symlink_to(target,target_is_directory=True)
        for role in ("before","after"):self.invoke(self.arguments(**{role:route/"input.docx"}),code=2)
        self.invoke([*self.arguments(),"--out",route/"new.json"],code=2);self.assertFalse((target/"new.json").exists())

    def test_native_leaf_symlink_and_dangling_output_refusal(self):
        for role in ("before","after"):
            link=self.owned(self.work/(role+"-linked.docx"));self.symlink(link,getattr(self,role));self.invoke(self.arguments(**{role:link}),code=2)
        for name,target in (("dangling",self.work/"never-created.json"),("source-pointing",self.copy/"never-created.json")):
            target=self.owned(target);self.assertFalse(os.path.lexists(target));route=self.owned(self.work/(name+".json"));self.symlink(route,target)
            self.invoke([*self.arguments(),"--out",route],code=2);self.assertFalse(os.path.lexists(target),"Refused output must not create a symlink target");self.assertTrue(route.is_symlink())
        for name,target in (("before-pointing",self.before),("after-pointing",self.after),("runtime-pointing",self.copy/"toolkit.py")):
            raw=target.read_bytes();route=self.owned(self.work/(name+".json"));self.symlink(route,target);self.invoke([*self.arguments(),"--out",route],code=2);self.assertEqual(target.read_bytes(),raw)

    @unittest.skipUnless(os.name=="nt",WINDOWS_REASON)
    def test_native_windows_path_grammar_and_named_stream_routes(self):
        for role in ("before","after"):
            source=getattr(self,role)
            for path in (str(source)+":stream",str(self.work/"CON"),str(source)+".",str(source)+" ","x:relative","//example.invalid/share"):
                self.invoke(self.arguments(**{role:path}),code=2)
        self.invoke([*self.arguments(),"--out",str(self.output)+":stream"],code=2)

    @unittest.skipUnless(os.name!="nt",POSIX_REASON)
    def test_native_posix_special_inputs_and_private_report_mode(self):
        fifo=self.owned(self.work/"fictional.fifo");os.mkfifo(fifo);sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.owned(self.work/"s")));self.addCleanup(sock.close)
        for role in ("before","after"):
            for path in (fifo,self.work/"s",self.work):self.invoke(self.arguments(**{role:path}),code=2)
        self.cli(out=True,allow=[self.output]);self.assertEqual(stat.S_IMODE(self.output.stat().st_mode),0o600)

    def test_show_values_exports_only_changed_blocks_with_identical_hashes(self):
        before=[dict(kind="paragraph",text="Unchanged fictional secret"),dict(kind="paragraph",text="Before <literal>"),dict(kind="table",rows=[["unchanged cell","before"]])]
        after=[dict(kind="paragraph",text="Unchanged fictional secret"),dict(kind="paragraph",text="After <literal>"),dict(kind="table",rows=[["unchanged cell","after"]])]
        specs=[(2,"CHANGED",None),(3,"CHANGED",[(1,2)])];default=self.check(before,after,specs);shown=self.check(before,after,specs,True,api=True)
        self.assertNotIn("Unchanged fictional secret",json.dumps(shown));self.assertNotIn("<literal>",json.dumps(default));self.assertIn("<literal>",json.dumps(shown))
        for left,right in zip(default["changes"],shown["changes"]):
            for side in ("before","after"):self.assertEqual(left[side]["sha256"],right[side]["sha256"])
        self.assertEqual(shown["changes"][1]["after"]["value"],[["unchanged cell","after"]])


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
    if strict is None:strict=os.name!="nt" or os.environ.get("OUTLANDS_DOCUMENT_DIFF_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
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
        fictional_document_diff_flow_checked=flow_checked,native_file_guards_checked=native_checked,fictional_document_diff_flow_test_ids=sorted(FLOW_IDS),native_file_guard_test_ids=sorted(native),
        positive_asserted_test_ids=dict(fictional_document_diff_flow_checked=sorted(FLOW_IDS),native_file_guards_checked=sorted(native)),child_xml_bindings_verified=good and flow_checked and native_checked and CopiedCLI.checked_children>0,xml_binding_checked_children=CopiedCLI.checked_children,
        copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,
        **{name:False for name in FALSE_FLAGS})


if __name__=="__main__":raise SystemExit(0 if run_copied_tests()["status"]=="PASS" else 1)
