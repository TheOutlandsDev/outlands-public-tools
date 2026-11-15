"""Independent copied MIME consumers on authored example.invalid messages; no mail, rendering or extraction. MIT."""
import base64
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=("inspect_eml.py","fictional_eml.py","message_core.py","toolkit.py","native_windows.py")
PREFIX=b"From: robot@example.invalid\r\nTo: reviewer@example.invalid\r\nSubject: Fictional\r\nMIME-Version: 1.0\r\n"
WINDOWS_ID="test_download.Download.test_native_windows_path_grammar_and_named_stream_routes"
WINDOWS_REASON="Native Windows path-grammar fixtures"
POSIX_ID="test_download.Download.test_native_posix_special_inputs_and_private_report_mode"
POSIX_REASON="Native POSIX special-file and mode fixtures"
LINK_ID="test_download.Download.test_native_leaf_symlink_and_dangling_output_refusal"
LINK_REASON="Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS={(POSIX_ID,POSIX_REASON)}
REQUIRED_POSIX_SKIPS={(WINDOWS_ID,WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS={(LINK_ID,LINK_REASON)}
FALSE_FLAGS=("real_mail_used","mailboxes_accessed","messages_sent","bodies_rendered","files_extracted",
             "remote_resources_followed","message_authenticity_verified","attachment_safety_verified","real_delivery_verified")
FLOW_IDS={"test_download.Download.test_fictional_generator_exact_multipart_and_report_readback",
          "test_download.Download.test_html_is_hashed_without_rendering_or_remote_actions",
          "test_download.Download.test_default_summary_omits_header_filename_and_body_values"}
COMMON_NATIVE_IDS={"test_download.Download.test_no_overwrite_and_standalone_collection_source_output_guards",
                   "test_download.Download.test_retained_failed_report_is_not_confirmed_or_replaced",
                   "test_download.Download.test_mandatory_hardlink_inputs_and_existing_outputs_are_refused",
                   "test_download.Download.test_linked_parent_read_and_report_routes_are_refused"}
NL=b"\r\n" if os.name=="nt" else b"\n"


def sha(raw):return hashlib.sha256(raw).hexdigest()


def plain(body=b"Fictional body.\r\n",kind=b"text/plain; charset=utf-8",extra=b""):
    return PREFIX+b"Content-Type: "+kind+b"\r\n"+extra+b"\r\n"+body


def leaf(body=b"Fictional",kind=b"text/plain; charset=utf-8",extra=b""):
    return b"Content-Type: "+kind+b"\r\n"+extra+b"\r\n"+body


def container(parts,boundary=b"root",kind=b"mixed"):
    return (b'Content-Type: multipart/'+kind+b'; boundary="'+boundary+b'"\r\n\r\n'+
            b"".join(b"--"+boundary+b"\r\n"+part+b"\r\n" for part in parts)+b"--"+boundary+b"--\r\n")


def canonical(value):
    return (json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(",",":"))+"\n").encode()


CHILD=r'''
import base64,hashlib,importlib.metadata,json,os,runpy,sys
from pathlib import Path
from types import SimpleNamespace
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();mode=sys.argv[2];args=sys.argv[3:];sys.path.insert(0,str(base))
def audit(event,values):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open'):
  raise AssertionError('UNEXPECTED_NETWORK_RENDER_OR_PROCESS')
sys.addaudithook(audit)
import inspect_eml as i
import fictional_eml as g
import message_core as m
import toolkit as t
import native_windows as n
for module,name in ((i,'inspect_eml.py'),(g,'fictional_eml.py'),(m,'message_core.py'),(t,'toolkit.py'),(n,'native_windows.py')):
 assert Path(module.__file__).resolve()==base/name
assert i.t is g.t is m.t is t and i.address is m.address and i.filename is m.filename and i.text is m.text
assert t.read.__globals__ is t.__dict__ and t.write_new.__globals__ is t.__dict__
def no_xml(*a,**kw):raise AssertionError('MIME_INSPECTION_CALLED_XML_READER')
t.xml=no_xml
if mode=='affinity':
 sys.stdout.write(t.encode(dict(status='COPIED_RUNTIME_AFFINITY',runtime_files=5)).decode());raise SystemExit(0)
if mode=='generator':
 sys.argv=[str(base/'fictional_eml.py'),*args]
 runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('GENERATOR_ENTRYPOINT_DID_NOT_EXIT')
if mode in ('api','decoded-budget'):
 path=Path(args[0]);assert path.is_absolute()
 if mode=='decoded-budget':
  compact=b'QQ==';i.base64.b64decode=lambda *a,**kw:b'x'*(2*1024*1024+1);i.base64.b64encode=lambda *a,**kw:compact
 try:value=i.inspect(path.read_bytes())
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
  fields={name:getattr(value,name) for name in dir(value) if name.startswith('st_')}
  fields['st_mtime_ns']+=1
  return SimpleNamespace(**fields)
 os.read=read;os.fstat=info
elif mode=='write-failure':
 def failed(unused):raise OSError('FICTIONAL_PRIVATE_WRITE_FAILURE')
 os.fsync=failed
elif mode=='output-budget':t.MAX_OUTPUT=1
elif mode!='normal':raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
sys.argv=[str(base/'inspect_eml.py'),*args]
runpy.run_path(sys.argv[0],run_name='__main__');raise AssertionError('INSPECTOR_ENTRYPOINT_DID_NOT_EXIT')
'''


class Download(unittest.TestCase):
    strict_links=None
    native_events=[]
    @classmethod
    def setUpClass(cls):
        cls.python_binary=Path(sys._base_executable).resolve()
        cls.python_pin=sha(cls.python_binary.read_bytes());cls.python_bytes=cls.python_binary.stat().st_size
        cls.python_version=".".join(map(str,sys.version_info[:3]))
        if cls.python_pin!=os.environ["OUTLANDS_TEST_PYTHON_SHA256"] or cls.python_version!=os.environ["OUTLANDS_TEST_PYTHON_VERSION"]:
            raise AssertionError("EXPECTED_PYTHON_BINARY_OR_VERSION_DIFFERS")
    @classmethod
    def tearDownClass(cls):
        if sha(cls.python_binary.read_bytes())!=cls.python_pin or cls.python_binary.stat().st_size!=cls.python_bytes:
            raise AssertionError("PYTHON_BINARY_CHANGED")
    def setUp(self):
        self.assertNotEqual(sys.prefix,sys.base_prefix);self.assertEqual(list(importlib.metadata.distributions()),[])
        parent=Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp=tempfile.TemporaryDirectory(prefix="eml-cli-",dir=parent);self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve();self.copy=self.work/"copied runtime";self.copy.mkdir();self.pins={}
        for name in RUNTIME:
            raw=(ROOT/name).read_bytes();(self.copy/name).write_bytes(raw);self.pins[name]=sha(raw)
        self.input=self.work/"fictional.eml";self.input.write_bytes(plain());self.output=self.work/"summary.json"
        self.env={key:value for key,value in os.environ.items() if not key.upper().startswith(("PYTHON","PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHON_COLORS="0",NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
    def runtime_preserved(self):
        self.assertEqual({p.name for p in self.copy.iterdir()},set(RUNTIME))
        self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME},self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")),[])
    def owned(self,path):
        path=Path(path);self.assertTrue(path.is_absolute() and path.resolve().is_relative_to(self.work));return path
    def write(self,raw):
        self.input.write_bytes(raw)
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
        allowed={self.owned(path).relative_to(self.work).as_posix() for path in allow}
        self.assertEqual(sorted(after.keys()-before.keys()-allowed),[],"Unexpected relative file creation")
        self.runtime_preserved()
        if text:return done.stdout.decode("ascii")
        value=json.loads(done.stdout)
        if code==2:
            self.assertEqual(set(value),{"status","code"});self.assertEqual(value["status"],"ERROR");self.assertRegex(value["code"],r"^[A-Z][A-Z0-9_]{0,100}$")
            if error is not None:self.assertEqual(value["code"],error)
        elif value.get("format")=="outlands-mime-summary-v1":self.check_summary(value)
        return value
    def cli(self,*,out=False,**options):
        return self.invoke(["--input",self.input,*(['--out',self.output] if out else [])],**options)
    def api(self,**options):return self.invoke([self.input],mode=options.pop("mode","api"),**options)
    def refused(self,raw,code=None):
        self.write(raw);self.api(code=2,error=code);self.cli(code=2,error=code)
    def check_summary(self,value):
        self.assertEqual(set(value),{"status","format","input_sha256","parts","decoded_bytes","attachment_count","bodies_rendered","files_extracted","real_delivery_verified"})
        self.assertEqual((value["status"],value["format"]),("PASS","outlands-mime-summary-v1"));self.assertEqual(value["input_sha256"],sha(self.input.read_bytes()))
        self.assertIs(value["bodies_rendered"],False);self.assertIs(value["files_extracted"],False);self.assertIs(value["real_delivery_verified"],False)
        self.assertEqual([row["part"] for row in value["parts"]],list(range(1,len(value["parts"])+1)))
        total=0;attachments=0
        for row in value["parts"]:
            self.assertTrue(0<=row["depth"]<=8)
            if row["media_type"].startswith("multipart/"):
                self.assertEqual(set(row),{"part","depth","media_type","children"});self.assertTrue(1<=row["children"]<=16)
            else:
                self.assertEqual(set(row),{"part","depth","media_type","bytes","sha256","attachment"})
                self.assertIs(type(row["attachment"]),bool);self.assertTrue(row["bytes"]>=0);self.assertRegex(row["sha256"],r"^[a-f0-9]{64}$")
                total+=row["bytes"];attachments+=row["attachment"]
        self.assertEqual(value["decoded_bytes"],total);self.assertEqual(value["attachment_count"],attachments);self.assertTrue(len(value["parts"])<=32 and total<=2097152)
    def symlink(self,path,target,directory=False):
        self.owned(path);self.owned(target)
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            strict=self.strict_links if self.strict_links is not None else os.name!="nt" or os.environ.get("OUTLANDS_EML_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
            actual=os.name=="nt" and getattr(error,"winerror",None)==1314
            if actual and not strict:
                self.assertEqual(self.id(),LINK_ID);self.assertFalse(directory)
                self.native_events.append(dict(test=self.id(),reason=LINK_REASON,policy="actual_windows_1314",actual_windows_1314=True,winerror=1314,strict=False,provenance="test_download.Download.symlink/caught-OSError"))
                self.skipTest(LINK_REASON)
            raise

    def test_copied_affinity_and_both_entrypoint_help_are_inert(self):
        self.assertEqual(self.invoke(mode="affinity"),dict(status="COPIED_RUNTIME_AFFINITY",runtime_files=5))
        self.assertIn("--input",self.invoke(["--help"],text=True));self.assertIn("--out",self.invoke(["--help"],mode="generator",text=True))
    def test_fictional_generator_exact_multipart_and_report_readback(self):
        target=self.owned(self.work/"generated.eml")
        self.assertEqual(self.invoke(["--out",target],mode="generator",allow=[target]),dict(status="PASS",fictional_message_written=True))
        expected=("\r\n".join(['From: robot@example.invalid','To: reviewer@example.invalid','Subject: Fictional sample','MIME-Version: 1.0','Content-Type: multipart/mixed; boundary="fictional_boundary"','','--fictional_boundary','Content-Type: text/plain; charset=utf-8','Content-Transfer-Encoding: base64','',base64.b64encode(b'Invented notice.\n').decode(),'--fictional_boundary','Content-Type: application/octet-stream','Content-Disposition: attachment; filename="sample.txt"','Content-Transfer-Encoding: base64','',base64.b64encode(b'sample\n').decode(),'--fictional_boundary--',''])).encode("ascii")
        self.assertEqual(target.read_bytes(),expected);self.input=target;report=self.cli();self.assertEqual(report["parts"],[dict(part=1,depth=0,media_type="multipart/mixed",children=2),dict(part=2,depth=1,media_type="text/plain",attachment=False,bytes=17,sha256=sha(b"Invented notice.\n")),dict(part=3,depth=1,media_type="application/octet-stream",attachment=True,bytes=7,sha256=sha(b"sample\n"))])
        self.assertEqual(self.cli(out=True,allow=[self.output]),dict(status="PASS",report_written=True));self.assertEqual(self.output.read_bytes(),canonical(report))
        self.invoke(["--out",target],mode="generator",code=2)
    def test_plain_seven_bit_crlf_and_tab_payload_hashes_are_exact(self):
        body=b"Fictional\tplain\r\nsecond line\r\n";self.write(plain(body,kind=b"text/plain; charset=us-ascii"))
        report=self.api();self.assertEqual(report["parts"][0]["sha256"],sha(body));self.assertEqual(report["decoded_bytes"],len(body));self.assertEqual(self.cli(),report)
    def test_utf8_canonical_base64_wrapped_only_at_crlf(self):
        body=("Fictional café 🧪\n"*8).encode();encoded=base64.b64encode(body);wrapped=b"\r\n".join(encoded[i:i+76] for i in range(0,len(encoded),76))
        self.write(plain(wrapped+b"\r\n",extra=b"Content-Transfer-Encoding: base64\r\n"));report=self.api();self.assertEqual(report["decoded_bytes"],len(body));self.assertEqual(report["parts"][0]["sha256"],sha(body));self.assertEqual(self.cli(),report)
    def test_html_is_hashed_without_rendering_or_remote_actions(self):
        body=b'<script>FICTIONAL_PRIVATE_SCRIPT</script><img src="https://asset.example.invalid/never"><p>fictional</p>'
        self.write(plain(body,kind=b"text/html; charset=utf-8"));report=self.cli();self.assertEqual(report["parts"][0]["media_type"],"text/html");self.assertEqual(report["parts"][0]["sha256"],sha(body));self.assertNotIn("SCRIPT",json.dumps(report))
    def test_nested_multipart_preorder_counts_depth_and_binary_hashes(self):
        binary=bytes(range(256))
        alternative=container([leaf(b"plain"),leaf(b"<p>html</p>",kind=b"text/html; charset=utf-8")],boundary=b"alternative",kind=b"alternative")
        attachment=leaf(base64.b64encode(binary),kind=b"application/octet-stream",extra=b'Content-Disposition: attachment; filename="safe.bin"\r\nContent-Transfer-Encoding: base64\r\n')
        self.write(PREFIX+container([alternative,attachment]));report=self.api();self.assertEqual([(row["depth"],row["media_type"]) for row in report["parts"]],[(0,"multipart/mixed"),(1,"multipart/alternative"),(2,"text/plain"),(2,"text/html"),(1,"application/octet-stream")]);self.assertEqual(report["parts"][-1]["sha256"],sha(binary));self.assertEqual(report["attachment_count"],1);self.assertEqual(self.cli(),report)
    def test_raw_crlf_seven_bit_and_line_bounds_refuse_without_reports(self):
        self.write(plain(b"x"*998));self.api()
        for raw,code in ((b"","EML_SIZE_LIMIT"),(plain().replace(b"\r\n",b"\n"),"EML_7BIT_CRLF_REQUIRED"),(plain(b"a\rb"),"EML_7BIT_CRLF_REQUIRED"),(plain(b"\xff"),"EML_7BIT_CRLF_REQUIRED"),(plain(b"\0"),"EML_7BIT_CRLF_REQUIRED"),(plain(b"x"*999),"EML_LINE_LIMIT")):self.refused(raw,code)
        self.assertFalse(self.output.exists())
    def test_actual_two_mebibyte_input_boundary_and_api_size_refusal(self):
        header=plain(b"");size=2097152-len(header);count,last=divmod(size,902);body=(b"x"*900+b"\r\n")*count+b"x"*last;raw=header+body
        self.assertEqual(len(raw),2097152);self.write(raw);report=self.api();self.assertEqual(report["decoded_bytes"],size);self.assertEqual(report["parts"][0]["sha256"],sha(body));self.assertEqual(self.cli(),report)
        self.write(raw+b"x");self.api(code=2,error="EML_SIZE_LIMIT");self.cli(code=2,error="INPUT_SIZE_LIMIT" if os.name=="nt" else "INPUT_LIMIT")
    def test_required_duplicate_unknown_and_nested_forbidden_headers(self):
        for raw in (plain().replace(b"MIME-Version: 1.0\r\n",b""),plain(extra=b"Unknown: fictional\r\n"),plain(extra=b"Subject: duplicate\r\n"),plain().replace(b"To: reviewer@example.invalid",b"To: reviewer@example.invalid\r\nTo: another@example.invalid"),PREFIX+container([leaf(extra=b"Subject: forbidden\r\n")])):
            self.refused(raw)
    def test_addresses_recipient_groups_and_nonempty_subject_are_narrow(self):
        to=b",".join(("to"+str(i)+"@example.invalid").encode() for i in range(32));cc=b",".join(("cc"+str(i)+"@example.invalid").encode() for i in range(32))
        good=plain().replace(b"To: reviewer@example.invalid",b"To: "+to+b"\r\nCc: "+cc);self.write(good);self.api()
        for raw in (plain().replace(b"robot@example.invalid",b"Robot <robot@example.invalid>"),plain().replace(b"Subject: Fictional",b"Subject:"),plain(extra=b"Bcc: REVIEWER@example.invalid\r\n"),good.replace(b"To: "+to,b"To: "+to+b",extra@example.invalid")):
            self.refused(raw)
    def test_header_count_block_and_exact_unfolded_length_limits(self):
        folded=b"X-Reference: "+b"a"*900+(b"\r\n "+b"a"*900)*7+b"\r\n "+b"a"*984+b"\r\n"
        self.write(plain(extra=folded));self.api()
        self.refused(plain(extra=folded[:-2]+b"a\r\n"),"HEADER_INVALID")
        self.refused(plain(extra=b"X-Reference: a\r\n"*61),"HEADER_LIMIT")
        self.refused(plain(extra=b"X-Reference: "+b"a"*900+(b"\r\n "+b"a"*900)*74+b"\r\n"),"HEADER_LIMIT")
    def test_no_guessed_content_types_charsets_or_format_parameters(self):
        for raw in (plain().replace(b"Content-Type: text/plain; charset=utf-8\r\n",b""),plain(kind=b"text/plain"),plain(kind=b"image/png"),plain(kind=b"message/rfc822"),plain(kind=b'text/plain; charset="utf-8"'),plain(kind=b"text/plain; charset=utf-8; format=flowed"),plain(kind=b"text/plain; charset=iso-8859-1")):self.refused(raw)
    def test_transfer_encoding_subset_has_no_quoted_printable_or_binary_fallback(self):
        for encoding in (b"quoted-printable",b"8bit",b"binary",b"unknown"):
            self.refused(plain(b"Fictional",extra=b"Content-Transfer-Encoding: "+encoding+b"\r\n"),"TRANSFER_ENCODING_UNSUPPORTED")
    def test_base64_padding_canonicality_and_whitespace_are_strict(self):
        for encoded in (b"%%%=",b"YQ===",b"YR==",b"YQ== trailing",b" YQ==",b"YQ==\t",b"YQ="):
            self.refused(plain(encoded,extra=b"Content-Transfer-Encoding: base64\r\n"))
        self.refused(plain(b"YR==",extra=b"Content-Transfer-Encoding: base64\r\n"),"BASE64_NONCANONICAL")
    def test_decoded_charset_unicode_and_control_failures_are_not_repaired(self):
        for decoded,kind in ((b"\xff",b"text/plain; charset=utf-8"),("café".encode(),b"text/plain; charset=us-ascii"),(b"a\0b",b"text/plain; charset=utf-8"),(b"a\rb",b"text/plain; charset=utf-8"),("a\u202eb".encode(),b"text/plain; charset=utf-8")):
            self.refused(plain(base64.b64encode(decoded),kind=kind,extra=b"Content-Transfer-Encoding: base64\r\n"))
    def test_attachment_names_dispositions_and_binary_encoding_are_explicit(self):
        good=plain(base64.b64encode(b"fictional"),kind=b"application/octet-stream",extra=b'Content-Disposition: attachment; filename="safe-01.bin"\r\nContent-Transfer-Encoding: base64\r\n')
        self.write(good);self.assertTrue(self.api()["parts"][0]["attachment"])
        for name in (b"../escape.bin",b"CON.txt",b"a:stream",b"a..txt",b"a.",b"COM0.txt"):
            self.refused(good.replace(b"safe-01.bin",name))
        for raw in (good.replace(b'Content-Disposition: attachment; filename="safe-01.bin"\r\n',b""),good.replace(b"Content-Transfer-Encoding: base64",b"Content-Transfer-Encoding: 7bit"),good.replace(b'filename="safe-01.bin"',b"filename*=utf-8''safe.bin"),good.replace(b'filename="safe-01.bin"',b'filename="safe.bin"; filename="other.bin"')):self.refused(raw)
    def test_attachment_names_are_unique_case_insensitively_without_extraction(self):
        def attachment(name):
            return leaf(b"eA==",kind=b"application/octet-stream",extra=b'Content-Disposition: attachment; filename="'+name+b'"\r\nContent-Transfer-Encoding: base64\r\n')
        self.write(PREFIX+container([attachment(b"one.bin"),attachment(b"two.bin")]));self.assertEqual(self.api()["attachment_count"],2)
        self.refused(PREFIX+container([attachment(b"one.bin"),attachment(b"ONE.BIN")]),"DUPLICATE_ATTACHMENT")
        self.assertFalse((self.work/"one.bin").exists())
    def test_broken_boundaries_and_nonempty_surroundings_are_refused(self):
        raw=PREFIX+container([leaf()])
        for value in (raw.replace(b"--root--",b""),raw.replace(b'boundary="root"',b'boundary="bad boundary"'),raw.replace(b"\r\n\r\n--root",b"\r\n\r\nFICTIONAL_PRIVATE_PREAMBLE\r\n--root",1),raw+b"FICTIONAL_PRIVATE_EPILOGUE\r\n"):
            self.refused(value)
    def test_actual_depth_eight_and_sixteen_children_structure_limits(self):
        raw=leaf()
        for index in range(8):raw=container([raw],boundary=("depth"+str(index)).encode())
        self.write(PREFIX+raw);self.assertEqual(max(row["depth"] for row in self.api()["parts"]),8)
        self.refused(PREFIX+container([raw],boundary=b"too-deep"),"MIME_STRUCTURE_LIMIT")
        self.write(PREFIX+container([leaf()]*16));self.assertEqual(len(self.api()["parts"]),17)
        self.refused(PREFIX+container([leaf()]*17),"MIME_STRUCTURE_LIMIT")
    def test_global_thirty_two_parts_and_controlled_decoded_byte_guard(self):
        self.write(PREFIX+container([container([leaf()]*15,boundary=b"a"),container([leaf()]*14,boundary=b"b")]))
        self.assertEqual(len(self.api()["parts"]),32)
        self.refused(PREFIX+container([container([leaf()]*15,boundary=b"a"),container([leaf()]*15,boundary=b"b")]),"MIME_STRUCTURE_LIMIT")
        self.write(plain(b"QQ==",extra=b"Content-Transfer-Encoding: base64\r\n"));self.api(mode="decoded-budget",code=2,error="DECODED_LIMIT")
    def test_default_summary_omits_header_filename_and_body_values(self):
        raw=plain(b"FICTIONAL_PRIVATE_BODY",extra=b'Content-Disposition: attachment; filename="private-name.txt"\r\n').replace(b"Subject: Fictional",b"Subject: FICTIONAL_PRIVATE_SUBJECT")
        self.write(raw);value=self.cli();encoded=json.dumps(value)
        for marker in ("robot@","reviewer@","private-name","BODY","SUBJECT"):self.assertNotIn(marker,encoded)
        self.assertEqual(value["parts"][0]["sha256"],sha(b"FICTIONAL_PRIVATE_BODY"));self.assertEqual(self.api(),value)
    def test_fixed_cli_diagnostics_never_echo_supplied_paths_or_values(self):
        for args in ([],["--input",self.input,"--FICTIONAL_PRIVATE_OPTION=value"],["--input",self.work/"FICTIONAL_PRIVATE_MISSING.eml"]):
            self.invoke(args,code=2)
        self.invoke(["--out",self.work/"FICTIONAL_PRIVATE_MISSING"/"new.eml"],mode="generator",code=2)
    def test_no_overwrite_and_standalone_collection_source_output_guards(self):
        self.cli(out=True,allow=[self.output]);self.cli(out=True,code=2)
        self.invoke(["--input",self.input,"--out",self.input],code=2)
        self.invoke(["--input",self.input,"--out",self.copy/"must-not-exist.json"],code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE")
        collection=self.owned(self.work/"collection");tool=collection/"tools"/"fictional-tool";tool.mkdir(parents=True);(collection/"systems").mkdir();(collection/"catalog").mkdir();(collection/"catalog/registry.json").write_bytes(b"{}")
        for name in RUNTIME:(tool/name).write_bytes((self.copy/name).read_bytes())
        self.invoke(["--input",self.input,"--out",collection/"must-not-exist.json"],base=tool,code=2,error="OUTPUT_INSIDE_REPOSITORY" if os.name=="nt" else "OUTPUT_INSIDE_SOURCE")
        self.assertFalse((collection/"must-not-exist.json").exists());self.assertEqual({p.name for p in tool.iterdir()},set(RUNTIME))
    def test_retained_failed_report_is_not_confirmed_or_replaced(self):
        expected=self.api()
        self.cli(out=True,mode="write-failure",code=2,error="INPUT_OR_OUTPUT_REFUSED",allow=[self.output]);self.assertEqual(self.output.read_bytes(),canonical(expected));self.cli(out=True,code=2)
        self.output=self.work/"budget.json";self.cli(out=True,mode="output-budget",code=2,error="OUTPUT_LIMIT");self.assertFalse(self.output.exists())
    def test_short_and_changed_metadata_reads_are_refused_without_mutation(self):
        self.cli(mode="short-read",code=2,error="INPUT_CHANGED");self.cli(mode="changed-stat",code=2,error="INPUT_CHANGED")
        self.assertFalse(self.output.exists())
    def test_mandatory_hardlink_inputs_and_existing_outputs_are_refused(self):
        alias=self.owned(self.work/"hardlinked.eml");os.link(self.input,alias);self.assertTrue(alias.samefile(self.input))
        for path in (self.input,alias):self.invoke(["--input",path],code=2,error="CONTROL_NOT_SINGLE_LINK" if os.name=="nt" else "INPUT_UNSAFE")
        self.invoke(["--out",alias],mode="generator",code=2)
    def test_linked_parent_read_and_report_routes_are_refused(self):
        target=self.owned(self.work/"target");target.mkdir();(target/"input.eml").write_bytes(plain());route=self.owned(self.work/"route")
        if os.name=="nt":
            done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(route),str(target)],capture_output=True,timeout=15)
            self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:route.rmdir() if route.exists() else None)
        else:route.symlink_to(target,target_is_directory=True)
        self.invoke(["--input",route/"input.eml"],code=2);self.invoke(["--input",self.input,"--out",route/"new.json"],code=2);self.assertFalse((target/"new.json").exists())
    def test_native_leaf_symlink_and_dangling_output_refusal(self):
        link=self.owned(self.work/"linked.eml");self.symlink(link,self.input);self.invoke(["--input",link],code=2)
        original=self.input.read_bytes()
        for name,target in (("dangling",self.work/"never-created.json"),("source-pointing",self.copy/"never-created.json")):
            target=self.owned(target);self.assertFalse(os.path.lexists(target))
            route=self.owned(self.work/(name+".json"));self.symlink(route,target)
            self.invoke(["--input",self.input,"--out",route],code=2)
            self.assertFalse(os.path.lexists(target),"Refused output must not create a symlink target")
            self.assertTrue(route.is_symlink())
        for name,target in (("input-pointing",self.input),("runtime-pointing",self.copy/"toolkit.py")):
            target=self.owned(target);raw=target.read_bytes();route=self.owned(self.work/(name+".json"));self.symlink(route,target)
            self.invoke(["--input",self.input,"--out",route],code=2);self.assertEqual(target.read_bytes(),raw)
        self.assertEqual(self.input.read_bytes(),original)
    @unittest.skipUnless(os.name=="nt",WINDOWS_REASON)
    def test_native_windows_path_grammar_and_named_stream_routes(self):
        for path in (str(self.input)+":stream",str(self.work/"CON"),str(self.input)+".",str(self.input)+" ","x:relative","//example.invalid/share"):
            self.invoke(["--input",path],code=2)
        self.invoke(["--input",self.input,"--out",str(self.output)+":stream"],code=2)
    @unittest.skipUnless(os.name!="nt",POSIX_REASON)
    def test_native_posix_special_inputs_and_private_report_mode(self):
        fifo=self.owned(self.work/"fictional.fifo");os.mkfifo(fifo)
        sock=socket.socket(socket.AF_UNIX);sock.bind(str(self.owned(self.work/"fictional.sock")));self.addCleanup(sock.close)
        for path in (fifo,self.work/"fictional.sock",self.work):self.invoke(["--input",path],code=2)
        self.cli(out=True,allow=[self.output]);self.assertEqual(stat.S_IMODE(self.output.stat().st_mode),0o600)


class TrackedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.started_ids=set();self.successful_ids=set()
    def startTest(self,test):
        self.started_ids.add(test.id());super().startTest(test)
    def addSuccess(self,test):
        self.successful_ids.add(test.id());super().addSuccess(test)


def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item


def load_copied_suite(strict=None):
    if strict is None:strict=os.name!="nt" or os.environ.get("OUTLANDS_EML_REQUIRE_LINKS")=="1" or os.environ.get("OUTLANDS_INTAKE_REQUIRE_LINKS")=="1"
    assert type(strict) is bool
    Download.strict_links=os.name!="nt" or strict;Download.native_events=[]
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Download);ids=[test.id() for test in flatten(suite)]
    assert len(ids)==len(set(ids))==30 and all(name.startswith("test_download.Download.test_") for name in ids)
    policies=REQUIRED_WINDOWS_SKIPS|REQUIRED_POSIX_SKIPS|OPTIONAL_WINDOWS_LINK_SKIPS
    assert all(name in set(ids) for name,reason in policies) and FLOW_IDS|COMMON_NATIVE_IDS<=set(ids)
    return suite


def run_copied_tests(strict=None,log_stream=None):
    suite=load_copied_suite(strict);strict=Download.strict_links;ids=[test.id() for test in flatten(suite)]
    result=unittest.TextTestRunner(stream=log_stream if log_stream is not None else sys.stderr,verbosity=2,resultclass=TrackedResult).run(suite)
    skips=[dict(test=test.id(),reason=reason) for test,reason in result.skipped]
    required=REQUIRED_WINDOWS_SKIPS if os.name=="nt" else REQUIRED_POSIX_SKIPS
    optional=OPTIONAL_WINDOWS_LINK_SKIPS if os.name=="nt" and not strict else set()
    observed={(row["test"],row["reason"]) for row in skips}
    unexpected=[row for row in skips if (row["test"],row["reason"]) not in required|optional]
    failed=sorted({getattr(test,"test_case",test).id() for test,trace in result.failures+result.errors})
    all_started=set(ids)<=result.started_ids
    valid_successes=result.successful_ids<=result.started_ids&set(ids)
    good=result.wasSuccessful() and result.testsRun==30 and all_started and valid_successes and len(skips)==len(observed) and required<=observed<=required|optional
    native=COMMON_NATIVE_IDS|{WINDOWS_ID if os.name=="nt" else POSIX_ID}
    flow_checked=good and FLOW_IDS<=result.successful_ids
    native_checked=good and native<=result.successful_ids
    return dict(schema=1,status="PASS" if good and flow_checked and native_checked else "FAIL",tests=result.testsRun,selected_tests=30,
        passed=len(result.successful_ids),skipped=len(skips),failures=len(result.failures),errors=len(result.errors),
        skips=skips,unexpected_skips=unexpected,missing_required_skips=[dict(test=name,reason=reason) for name,reason in sorted(required-observed)],
        failed_tests=failed,test_ids=ids,started_test_ids=sorted(result.started_ids),successful_test_ids=sorted(result.successful_ids),
        all_selected_tests_started=all_started,successful_ids_exclude_setup_failures=valid_successes,
        module_counts={"test_download":30},native_links_required=strict,native_fixture_events=Download.native_events,
        fictional_eml_flow_checked=flow_checked,native_file_guards_checked=native_checked,
        fictional_eml_flow_test_ids=sorted(FLOW_IDS),native_file_guard_test_ids=sorted(native),
        positive_asserted_test_ids=dict(fictional_eml_flow_checked=sorted(FLOW_IDS),native_file_guards_checked=sorted(native)),
        copied_runtime_only=True,copied_runtime_cli=True,fictional_inputs_only=True,
        **{name:False for name in FALSE_FLAGS})


if __name__=="__main__":
    raise SystemExit(0 if run_copied_tests()["status"]=="PASS" else 1)
