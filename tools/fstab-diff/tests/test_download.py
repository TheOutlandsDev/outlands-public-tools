"""Independent dual-input copied fstab consumers; fictional text only, no filesystem operations. MIT."""
import hashlib
import html
from html.parser import HTMLParser
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

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("fstab_diff.py", "text_support.py", "examples/generate.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junction_and_stream_routes"
PROCESS_WINDOWS_REASON = "Native Windows junction and stream fixtures"
PROCESS_POSIX_ID = "test_download.Download.test_native_posix_special_files_and_sparse_bounds"
PROCESS_POSIX_REASON = "Native POSIX FIFO, socket and sparse fixtures"
PROCESS_SYMLINK_ID = "test_download.Download.test_native_symlink_inputs_and_output_parents"
PROCESS_SYMLINK_REASON = "Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS = {(PROCESS_POSIX_ID, PROCESS_POSIX_REASON)}
REQUIRED_POSIX_SKIPS = {(PROCESS_WINDOWS_ID, PROCESS_WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS = {(PROCESS_SYMLINK_ID, PROCESS_SYMLINK_REASON)}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


PROBE = r'''
import hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import fstab_diff as e
import text_support as s
assert Path(e.__file__).resolve()==base/'fstab_diff.py'
assert Path(s.__file__).resolve()==base/'text_support.py'
assert e.source_inputs is s.source_inputs and e.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py'
 assert g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
selected=[Path(args[args.index(flag)+1]) for flag in ('--before','--after')]
output=Path(args[args.index('--output')+1])
if kind=='audit':
 e.Parser(description=e.__doc__);b'\xef\xbb\xbfprewarm'.decode('utf-8-sig')
 allowed={base/name for name in ('fstab_diff.py','text_support.py','examples/generate.py')}
 allowed.update(selected);allowed.update(output/name for name in ('report.json','report.html','MANIFEST.json'))
 read_counts={path:0 for path in selected};original=os.read
 def audited_read(fd,size):
  before=os.fstat(fd);raw=original(fd,size);matched=[]
  for path in read_counts:
   info=path.stat()
   if (before.st_dev,before.st_ino)==(info.st_dev,info.st_ino):matched.append(path)
  assert len(matched)==1,'UNEXPECTED_FILE_DESCRIPTOR_READ'
  read_counts[matched[0]]+=len(raw);return raw
 os.read=audited_read
 def audit(event,values):
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open','ctypes.dlopen','compile','exec'):
   raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
  if event=='open' and not isinstance(values[0],int):assert Path(values[0]) in allowed,'UNEXPECTED_FILE_OPEN'
 sys.addaudithook(audit);code=e.main(args)
 assert read_counts=={path:path.stat().st_size for path in selected}
 raise SystemExit(code)
elif kind.startswith('limit:'):
 for name,value in json.loads(kind[6:]).items():
  assert name in ('MAX_ITEMS','MAX_REPORT','MAX_LINE','MAX_LINES')
  setattr(s,name,value)
elif kind=='scope_escape':
 original=e.inspect
 def summarized(*values):
  report=original(*values);report['scope']='Fictional </pre><script>never_execute</script> & "quoted"';return report
 e.inspect=summarized
elif kind=='manifest_failure':
 original=os.open
 def failed(path,*a,**kw):
  if Path(path).name=='MANIFEST.json':raise OSError('FICTIONAL_PRIVATE_REPORT_DETAIL')
  return original(path,*a,**kw)
 os.open=failed
elif kind=='changed_input':
 original=os.read;changed=False
 def changed_read(*values):
  global changed
  raw=original(*values)
  if not changed:
   changed=True
   with selected[0].open('ab') as stream:stream.write(b'fictional mutation')
  return raw
 os.read=changed_read
elif kind=='short_read':os.read=lambda *unused:b''
else:raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
raise SystemExit(e.main(args))
'''


class StaticHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.csp = []
    def handle_starttag(self, tag, attributes):
        assert tag in {"html", "meta", "title", "style", "h1", "p", "pre"}
        for key, value in attributes:
            assert not key.lower().startswith("on") and key not in {"src", "srcdoc", "href"}
            if key == "http-equiv":
                assert value == "Content-Security-Policy"
                self.csp.append(dict(attributes)["content"])
        self.tags.append(tag)


class Download(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.python_binary = Path(sys._base_executable).resolve()
        cls.python_pin = sha(cls.python_binary.read_bytes())
        cls.python_bytes = cls.python_binary.stat().st_size
        cls.python_version = ".".join(map(str, sys.version_info[:3]))
        if cls.python_pin != os.environ["OUTLANDS_TEST_PYTHON_SHA256"] or cls.python_version != os.environ["OUTLANDS_TEST_PYTHON_VERSION"]:
            raise AssertionError("EXPECTED_PYTHON_BINARY_OR_VERSION_DIFFERS")
    @classmethod
    def tearDownClass(cls):
        if sha(cls.python_binary.read_bytes()) != cls.python_pin or cls.python_binary.stat().st_size != cls.python_bytes:
            raise AssertionError("PYTHON_BINARY_CHANGED")
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="fstab-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.copy = self.work / "copied runtime"; self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT/name).read_bytes(); target = self.copy/name
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw); self.pins[name] = sha(raw)
        self.inputs = []; self.mode = "linux"; self.output = self.work/"new report"
        self.env = {k:v for k,v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
        self.fixture(b"fictional /demo ext4 rw\n",b"fictional /demo ext4 rw\n")
    def runtime_preserved(self):
        self.assertEqual({p.relative_to(self.copy).as_posix() for p in self.copy.rglob("*") if p.is_file()}, set(RUNTIME))
        self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME}, self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
    def snapshot(self):
        rows = {}
        def visit(folder):
            for path in folder.iterdir():
                key = path.relative_to(self.work).as_posix(); info = path.lstat()
                if path.is_symlink() or getattr(path, "is_junction", lambda:False)(): rows[key] = ("LINK", os.readlink(path))
                elif stat.S_ISDIR(info.st_mode): rows[key] = ("DIRECTORY",); visit(path)
                elif stat.S_ISREG(info.st_mode):
                    if info.st_size > 8*1024*1024:
                        with path.open("rb") as stream:
                            sample = stream.read(64); stream.seek(-64, os.SEEK_END); sample += stream.read(64)
                        digest = "SPARSE_ENDPOINTS:"+sha(sample)
                    else: digest = sha(path.read_bytes())
                    rows[key] = (digest, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink)
                else: rows[key] = ("SPECIAL", info.st_mode)
        visit(self.work); return rows
    def run_child(self, command, env=None):
        if str(command[0]).endswith(".py"):
            bootstrap = "import runpy,sys;from pathlib import Path;p=Path(sys.argv[1]).resolve();sys.path.insert(0,str(p.parent));sys.argv=sys.argv[1:];runpy.run_path(str(p),run_name='__main__')"
            command = ["-c", bootstrap, *command]
        return subprocess.run([sys.executable,"-I","-B","-W","error",*map(str,command)], cwd=self.work,
                              env=self.env if env is None else env, stdin=subprocess.DEVNULL, capture_output=True, timeout=90)
    def fixture(self, before, after=None):
        self.inputs = []
        for name,data in (("before",before),("after",before if after is None else after)):
            path=self.work/("fictional "+name+".fstab");path.write_bytes(data);self.inputs.append(path)
    def new_output(self, suffix):
        self.output = self.work/("new report "+str(suffix))
    def args(self):
        return ["--before",self.inputs[0],"--after",self.inputs[1],"--format",self.mode,"--output",self.output]
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot(); prefix = ["-c",PROBE,self.copy,probe] if probe else [self.copy/"fstab_diff.py"]
        done = self.run_child([*prefix,*args], env=env)
        self.assertEqual(done.stderr,b"",done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout,json.dumps(value,sort_keys=probe!="affinity").encode()+NEWLINE)
        if error is not None: self.assertEqual(value,dict(status="INCOMPLETE",error=error)); code = 2
        elif probe == "affinity": self.assertEqual(value,dict(status="COPIED_RUNTIME_AFFINITY",dependencies=0)); code = 0
        else:
            report = self.check_report(output,args)
            self.assertEqual(value,dict(status=report["status"],changes=len(report["changes"]),ambiguous_targets=len(report["ambiguous_targets"]),relative_order_changed=report["relative_order_changed"],coverage_issues=len(report["coverage_issues"])))
            value = report; code = int(report["status"]!="NO_SCOPE_FINDINGS")
        self.assertEqual(done.returncode,code)
        for private in (str(self.work).encode(),b"FICTIONAL_PRIVATE",b"Traceback"): self.assertNotIn(private,done.stdout+done.stderr)
        after = self.snapshot(); ignored = {Path(p).relative_to(self.work).as_posix() for p in ignore}
        self.assertEqual({k:v for k,v in before.items() if k not in ignored},{k:after.get(k) for k in before if k not in ignored})
        for key in after.keys()-before.keys():
            path = self.work/key
            self.assertTrue(any(path==Path(root) or path.is_relative_to(root) for root in allow),"Unexpected application write: "+key)
        self.runtime_preserved(); return value
    def check_report(self, output, args):
        self.assertIsNotNone(output)
        self.assertEqual({p.name for p in output.iterdir()},{"report.json","report.html","MANIFEST.json"})
        raw=(output/"report.json").read_bytes();report=json.loads(raw);self.assertEqual(raw,encoded(report))
        self.assertEqual(set(report),{"schema_version","tool","format","scope","details_included","inputs","records","changes","ambiguous_targets","relative_order_changed","order_scope","parsed_counts","findings","coverage_issues","status"})
        self.assertEqual((report["schema_version"],report["tool"]),(1,"Fstab Configuration Diff"))
        mode=args[args.index("--format")+1];self.assertEqual(report["format"],mode)
        details="--include-details" in args;self.assertIs(report["details_included"],details)
        self.assertEqual(report["status"],"REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        selected=[Path(args[args.index(flag)+1]) for flag in ("--before","--after")]
        self.assertEqual(report["inputs"],[dict(id=side,bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for side,path in zip(("before","after"),selected)])
        fields={"source","target","fstype","options"}|({"dump","pass_number"} if mode=="linux" else {"fs_mgr_flags"})
        ids=list(dict.fromkeys(row["target_id"] for row in report["records"]))
        self.assertEqual(ids,["target-"+str(i).zfill(4) for i in range(1,len(ids)+1)])
        self.assertEqual(report["parsed_counts"],{side:sum(row["side"]==side for row in report["records"]) for side in ("before","after")})
        for row in report["records"]:
            self.assertEqual(set(row),{"target_id","side","line"}|({"fields"} if details else set()))
            self.assertIn(row["side"],{"before","after"});self.assertGreaterEqual(row["line"],1)
            if details:self.assertEqual(set(row["fields"]),fields)
        ambiguous_ids={row["target_id"] for row in report["ambiguous_targets"]}
        for row in report["ambiguous_targets"]:
            self.assertEqual(set(row),{"target_id","before_lines","after_lines"}|({"target"} if details else set()))
            for side in ("before","after"):
                self.assertEqual(row[side+"_lines"],[r["line"] for r in report["records"] if r["target_id"]==row["target_id"] and r["side"]==side])
            self.assertTrue(len(row["before_lines"])>1 or len(row["after_lines"])>1)
        for row in report["changes"]:
            self.assertEqual(set(row),{"target_id","kind","fields_changed","before_line","after_line"}|({"before","after"} if details else set()))
            self.assertIn(row["target_id"],ids);self.assertNotIn(row["target_id"],ambiguous_ids)
            self.assertIn(row["kind"],{"added","removed","changed"});self.assertTrue(set(row["fields_changed"])<=fields)
            self.assertEqual(len(row["fields_changed"]),len(set(row["fields_changed"])))
            if row["kind"]=="changed":self.assertNotIn("target",row["fields_changed"])
            for side in ("before","after"):
                group=[r for r in report["records"] if r["target_id"]==row["target_id"] and r["side"]==side]
                self.assertEqual(row[side+"_line"],group[0]["line"] if group else None)
                if details:self.assertEqual(row[side],group[0]["fields"] if group else None)
        self.assertEqual(report["order_scope"],"Unique common parsed targets only; additions, removals, ambiguous and unsupported rows excluded.")
        for row in report["findings"]+report["coverage_issues"]:
            self.assertEqual(set(row),{"code","source","line"});self.assertIn(row["source"],{"before","after","comparison"})
            self.assertGreaterEqual(row["line"],0 if row["source"]=="comparison" else 1)
        codes={row["code"] for row in report["findings"]}
        self.assertEqual("RELATIVE_RECORD_ORDER_CHANGED" in codes,report["relative_order_changed"])
        self.assertEqual("CONFIGURATION_VALUES_CHANGED" in codes,bool(report["changes"]))
        self.assertNotIn(str(self.work),raw.decode())
        markup=(output/"report.html").read_bytes();parsed=StaticHTML();parsed.feed(markup.decode());parsed.close()
        self.assertEqual(parsed.tags.count("html"),1);self.assertEqual(parsed.csp,["default-src 'none'; style-src 'unsafe-inline'"])
        self.assertIn(html.escape(raw.decode(),quote=True).encode(),markup)
        members={name:(output/name).read_bytes() for name in ("report.json","report.html")}
        manifest=dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=sha(data)) for name,data in sorted(members.items())])
        self.assertEqual((output/"MANIFEST.json").read_bytes(),encoded(manifest));return report
    def report(self, details=False, **kwargs):
        return self.call(self.args()+(["--include-details"] if details else []),output=self.output,allow=[self.output],**kwargs)
    def codes(self, report):
        return {row["code"] for row in report["findings"]+report["coverage_issues"]}
    def symlink(self, path, target, directory=False):
        try: path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            if os.name=="nt" and getattr(error,"winerror",None)==1314 and os.environ.get("OUTLANDS_FSTAB_REQUIRE_LINKS")!="1": self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_copied_runtime_affinity_and_help(self):
        self.call([],probe="affinity")
        for script in (self.copy/"fstab_diff.py",self.copy/"examples/generate.py"):
            before=self.snapshot();done=self.run_child([script,"--help"])
            self.assertEqual((done.returncode,done.stderr),(0,b""));self.assertIn(b"--output",done.stdout);self.assertEqual(self.snapshot(),before)
    def test_generator_cli_seven_fictional_files_and_fresh_output(self):
        target=self.work/"generated";before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(0,b"",json.dumps(dict(status="FICTIONAL_EXAMPLES_CREATED",files=7),sort_keys=True).encode()+NEWLINE))
        self.assertEqual({p.name for p in target.iterdir()},{"linux-before.fstab","linux-same.fstab","linux-changed.fstab","android-before.fstab","android-same.fstab","android-changed.fstab","ambiguous.fstab"});self.assertEqual({k:self.snapshot().get(k) for k in before},before)
        for mode in ("linux","android"):
            self.mode=mode
            for variant,status in (("same","NO_SCOPE_FINDINGS"),("changed","REVIEW_REQUIRED")):
                self.inputs=[target/(mode+"-before.fstab"),target/(mode+"-"+variant+".fstab")];self.new_output(mode+variant);report=self.report();self.assertEqual(report["status"],status)
        self.mode="linux";self.inputs=[target/"ambiguous.fstab",target/"linux-before.fstab"];self.new_output("ambiguous");self.assertEqual(len(self.report()["ambiguous_targets"]),1)
        before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(2,b"",json.dumps(dict(status="INCOMPLETE",error="OUTPUT_EXISTS"),sort_keys=True).encode()+NEWLINE));self.assertEqual(self.snapshot(),before)
    def test_linux_four_five_six_fields_and_numeric_defaults_are_equivalent(self):
        self.fixture(b"fictional-a /a ext4 rw\nfictional-b /b xfs defaults 0\nfictional-c /c ext4 ro 00001 00002\n",b"fictional-a /a ext4 rw 00 00000\nfictional-b /b xfs defaults 00000 0\nfictional-c /c ext4 ro 1 2\n")
        report=self.report(details=True);self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertEqual(report["changes"],[])
        self.assertEqual([(r["fields"]["dump"],r["fields"]["pass_number"]) for r in report["records"]],[(0,0),(0,0),(0,0),(0,0),(1,2),(1,2)])
        self.assertEqual(report["parsed_counts"],dict(before=3,after=3))
    def test_linux_numeric_bounds_do_not_coerce_unsupported_tokens(self):
        self.fixture(b"fictional /a ext4 rw 65535 65535\n");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        for index,value in enumerate(("-1","+1","65536","000000","1.0","nope",chr(0x0661))):
            self.fixture(("fictional /a ext4 rw "+value+" 0\n").encode());self.new_output(index);report=self.report()
            self.assertEqual(report["parsed_counts"],dict(before=0,after=0));self.assertEqual(report["changes"],[]);self.assertEqual(self.codes(report),{"UNSUPPORTED_NUMERIC_FIELD"})
            self.assertEqual([r["source"] for r in report["coverage_issues"]],["before","after"])
    def test_android_requires_five_fields_and_compares_fs_mgr_text(self):
        self.mode="android";self.fixture(b"/fictional/data /data ext4 rw wait,check\n",b"/fictional/data /data ext4 rw wait,check,quota\n")
        report=self.report(details=True);self.assertEqual(report["changes"][0]["fields_changed"],["fs_mgr_flags"]);self.assertEqual(report["records"][0]["fields"]["fs_mgr_flags"],"wait,check")
        for index,raw in enumerate((b"fictional /a ext4 rw\n",b"fictional /a ext4 rw wait extra\n")):
            self.fixture(raw);self.new_output(index);report=self.report();self.assertEqual(report["parsed_counts"],dict(before=0,after=0));self.assertEqual(self.codes(report),{"UNSUPPORTED_FIELD_COUNT"})
    def test_supported_octal_fields_decode_once_before_grouping(self):
        raw=b"src\\040name /mnt/tab\\011point ty\\134pe rw\\040flag\n"
        self.fixture(raw,raw.rstrip(b"\n")+b" 0 0\n");report=self.report(details=True)
        self.assertEqual(report["changes"],[]);self.assertEqual(report["records"][0]["fields"],dict(source="src name",target="/mnt/tab\tpoint",fstype="ty\\pe",options="rw flag",dump=0,pass_number=0))
        self.assertEqual([r["target_id"] for r in report["records"]],["target-0001","target-0001"])
        self.fixture(b"a /mnt/back\\134040disk ext4 rw\n");self.new_output("once");self.assertEqual(self.report(details=True)["records"][0]["fields"]["target"],"/mnt/back\\040disk")
    def test_unsupported_and_malformed_escapes_are_coverage_not_equal(self):
        for index,escape in enumerate((b"\\041",b"\\400",b"\\777",b"\\12",b"\\x",bytes([92]))):
            self.fixture(b"fictional /bad"+escape+b" ext4 rw\n");self.new_output(index);report=self.report()
            self.assertEqual(report["records"],[]);self.assertEqual(report["changes"],[]);self.assertEqual(self.codes(report),{"UNSUPPORTED_FIELD_ESCAPE"});self.assertEqual(report["status"],"REVIEW_REQUIRED")
    def test_linux_options_are_ordered_text_and_empty_duplicate_tokens_are_findings(self):
        self.fixture(b"a /a ext4 rw,noatime\n",b"a /a ext4 noatime,rw\n");report=self.report();self.assertEqual(report["changes"][0]["fields_changed"],["options"])
        for index,options in enumerate((b"rw,rw",b"rw,",b",rw,,rw,")):
            self.fixture(b"a /a ext4 "+options+b"\n");self.new_output(index);report=self.report();self.assertEqual(report["changes"],[])
            expected={"DUPLICATE_OPTION_TOKEN"} if index==0 else {"EMPTY_OPTION_TOKEN"} if index==1 else {"EMPTY_OPTION_TOKEN","DUPLICATE_OPTION_TOKEN"}
            self.assertEqual(self.codes(report),expected);self.assertEqual(report["status"],"REVIEW_REQUIRED")
    def test_android_option_collections_remain_distinct_and_unevaluated(self):
        self.mode="android";self.fixture(b"a /data ext4 rw,ro wait,check\n",b"a /data ext4 ro,rw check,wait\n")
        report=self.report(details=True);self.assertEqual(report["changes"][0]["fields_changed"],["options","fs_mgr_flags"]);self.assertEqual(report["records"][0]["fields"]["options"],"rw,ro")
        self.fixture(b"a /data ext4 rw,rw wait,,wait\n");self.new_output("tokens");report=self.report();self.assertEqual(report["changes"],[]);self.assertEqual(self.codes(report),{"EMPTY_OPTION_TOKEN","DUPLICATE_OPTION_TOKEN"})
    def test_target_rename_is_removal_and_addition_with_complete_fields(self):
        self.fixture(b"fictional /old ext4 rw\n",b"fictional /new ext4 rw\n");report=self.report(details=True)
        self.assertEqual([r["kind"] for r in report["changes"]],["removed","added"]);self.assertEqual([r["target_id"] for r in report["changes"]],["target-0001","target-0002"])
        self.assertEqual([r["fields_changed"] for r in report["changes"]],[["source","target","fstype","options","dump","pass_number"]]*2)
        self.assertIsNone(report["changes"][0]["after"]);self.assertIsNone(report["changes"][1]["before"]);self.assertFalse(report["relative_order_changed"])
    def test_unique_common_reorder_is_separate_from_value_changes(self):
        self.fixture(b"a /a ext4 rw\nb /b ext4 rw\n",b"b /b ext4 rw\na /a ext4 rw\n")
        report=self.report();self.assertTrue(report["relative_order_changed"]);self.assertEqual(report["changes"],[]);self.assertEqual(self.codes(report),{"RELATIVE_RECORD_ORDER_CHANGED"})
        self.fixture(b"a /a ext4 rw 0 0\n",b"b /a xfs ro 1 2\n");self.new_output("fields");report=self.report()
        self.assertEqual(report["changes"][0]["fields_changed"],["source","fstype","options","dump","pass_number"]);self.assertFalse(report["relative_order_changed"])
    def test_additions_and_removals_do_not_imply_common_target_reorder(self):
        self.fixture(b"old /old ext4 rw\na /a ext4 rw\nb /b ext4 rw\n",b"new /new ext4 rw\na /a ext4 rw\nb /b ext4 rw\n")
        report=self.report();self.assertEqual([r["kind"] for r in report["changes"]],["removed","added"]);self.assertFalse(report["relative_order_changed"])
        self.assertEqual([r["target_id"] for r in report["changes"]],["target-0001","target-0004"])
    def test_duplicate_before_targets_are_shown_without_arbitrary_pairing(self):
        self.fixture(b"a /same ext4 rw\nb /same ext4 ro\n",b"a /same ext4 ro\nc /else ext4 rw\n")
        report=self.report(details=True);self.assertEqual(report["ambiguous_targets"],[dict(target_id="target-0001",before_lines=[1,2],after_lines=[1],target="/same")])
        self.assertEqual([r["kind"] for r in report["changes"]],["added"]);self.assertEqual(report["changes"][0]["target_id"],"target-0002");self.assertFalse(report["relative_order_changed"])
        self.assertEqual([(r["source"],r["line"]) for r in report["findings"] if r["code"]=="AMBIGUOUS_TARGET_NO_PAIRING"],[("before",1),("before",2),("after",1)])
    def test_duplicate_after_or_both_sides_stay_ambiguous_even_when_identical(self):
        one=b"a /same ext4 rw\n";two=one+b"b /same ext4 ro\n"
        for index,(before,after,left,right) in enumerate(((one,two,[1],[1,2]),(two,two,[1,2],[1,2]),(two,b"",[1,2],[]),(b"",two,[],[1,2]))):
            self.fixture(before,after);self.new_output(index);report=self.report()
            self.assertEqual(report["ambiguous_targets"],[dict(target_id="target-0001",before_lines=left,after_lines=right)]);self.assertEqual(report["changes"],[]);self.assertEqual(report["status"],"REVIEW_REQUIRED")
    def test_ambiguous_and_unsupported_rows_are_excluded_from_order(self):
        before=b"a /a ext4 rw\nx /x ext4 rw\ny /x ext4 ro\nb /b ext4 rw\nnot supported\n"
        after=b"not supported\ny /x ext4 ro\na /a ext4 rw\nb /b ext4 rw\nx /x ext4 rw\n"
        self.fixture(before,after);report=self.report();self.assertFalse(report["relative_order_changed"]);self.assertEqual(report["changes"],[]);self.assertEqual(len(report["ambiguous_targets"]),1)
        self.assertEqual(self.codes(report),{"AMBIGUOUS_TARGET_NO_PAIRING","UNSUPPORTED_FIELD_COUNT"})
    def test_identical_unsupported_row_counts_require_review_in_each_mode(self):
        for mode in ("linux","android"):
            self.mode=mode
            for index,raw in enumerate((b"not enough fields\n",b"a /a ext4 rw 0 0 extra\n")):
                self.fixture(raw);self.new_output(mode+str(index));report=self.report();self.assertEqual(report["parsed_counts"],dict(before=0,after=0));self.assertEqual(report["changes"],[]);self.assertEqual(self.codes(report),{"UNSUPPORTED_FIELD_COUNT"})
    def test_comments_ascii_whitespace_hash_data_and_quotes_are_literal(self):
        self.fixture(b"# comment\n\tsshfs#fiction\t/data\tfuse\tdefaults\t0\t0 # ignored\n",b"sshfs#fiction /data fuse defaults\n")
        report=self.report(details=True);self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertEqual(report["records"][0]["fields"]["source"],"sshfs#fiction")
        self.fixture(b'"fictional" /data ext4 rw\n');self.new_output("quotes-data");self.assertEqual(self.report(details=True)["records"][0]["fields"]["source"],'"fictional"')
        self.fixture(b'"fictional with-space" /data ext4 rw\n');self.new_output("quotes-not-shell");self.assertEqual(self.codes(self.report()),{"UNSUPPORTED_NUMERIC_FIELD"})
    def test_targets_match_exactly_without_case_or_unicode_normalization(self):
        target="/my"+chr(160)+"disk";raw=("a "+target+" ext4 rw\n").encode();self.fixture(raw);self.assertEqual(self.report(details=True)["records"][0]["fields"]["target"],target)
        for index,(before,after) in enumerate((("/Data","/data"),("/caf"+chr(233),"/cafe"+chr(769)))):
            self.fixture(("a "+before+" ext4 rw\n").encode(),("a "+after+" ext4 rw\n").encode());self.new_output(index);report=self.report();self.assertEqual([r["kind"] for r in report["changes"]],["removed","added"]);self.assertFalse(report["relative_order_changed"])
    def test_opaque_ids_and_record_groups_follow_first_seen_before_then_after(self):
        self.fixture(b"b /b ext4 rw\na /a ext4 rw\n",b"c /c ext4 rw\na /a ext4 ro\nb /b ext4 rw\n")
        report=self.report();self.assertEqual([(r["target_id"],r["side"],r["line"]) for r in report["records"]],[("target-0001","before",1),("target-0001","after",3),("target-0002","before",2),("target-0002","after",2),("target-0003","after",1)])
        self.assertEqual([(r["target_id"],r["kind"],r["fields_changed"]) for r in report["changes"]],[("target-0002","changed",["options"]),("target-0003","added",["source","target","fstype","options","dump","pass_number"])])
    def test_default_privacy_and_details_include_only_selected_decoded_fields(self):
        self.fixture(b"FICTIONAL_PRIVATE_SOURCE /FICTIONAL_PRIVATE_TARGET privatefs privateflags 0 0\n",b"FICTIONAL_PRIVATE_SOURCE /FICTIONAL_PRIVATE_TARGET privatefs otherflags 0 0\n")
        basic=self.report();self.new_output("details");detailed=self.report(details=True)
        for word in ("FICTIONAL_PRIVATE_SOURCE","FICTIONAL_PRIVATE_TARGET","privatefs","privateflags","otherflags"):
            self.assertNotIn(word,json.dumps(basic));self.assertIn(word,json.dumps(detailed))
        for key in ("parsed_counts","relative_order_changed","findings","coverage_issues"):self.assertEqual(basic[key],detailed[key])
        self.assertEqual(basic["changes"],[{k:v for k,v in row.items() if k not in ("before","after")} for row in detailed["changes"]])
    def test_static_html_escaping_and_selected_file_audit_never_probe_targets(self):
        source=self.work/"fictional-device.bin";source.write_bytes(b"FICTIONAL_PRIVATE_DEVICE")
        target=self.work/"fictional-target";target.mkdir();(target/"keep.txt").write_bytes(b"keep")
        raw=(source.name+" "+target.name+" ext4 rw\n").encode();self.fixture(raw);self.assertEqual(self.report(probe="audit")["status"],"NO_SCOPE_FINDINGS")
        self.fixture(b"fictional<script>never_execute</script> /<target>& ext4 rw\n");self.new_output("html");report=self.report(details=True,probe="audit")
        self.assertEqual(report["records"][0]["fields"]["source"],"fictional<script>never_execute</script>");markup=(self.output/"report.html").read_bytes();self.assertNotIn(b"<script>",markup);self.assertIn(b"&lt;script&gt;never_execute&lt;/script&gt;",markup)
    def test_raw_input_hashes_manifests_empty_and_comment_only_are_scoped(self):
        before=b"\xef\xbb\xbfa /a ext4 rw\r\n";after=b"# comment\na /a ext4 rw 0 0\n";self.fixture(before,after);report=self.report()
        self.assertEqual([r["sha256"] for r in report["inputs"]],[sha(before),sha(after)]);self.assertEqual(report["status"],"NO_SCOPE_FINDINGS")
        self.assertEqual([r["path"] for r in json.loads((self.output/"MANIFEST.json").read_bytes())["files"]],["report.html","report.json"])
        self.fixture(b"",b"# comments only\n \t\n");self.new_output("empty");report=self.report();self.assertEqual(report["parsed_counts"],dict(before=0,after=0));self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertEqual(report["records"],[])
    def test_encoding_controls_fail_both_input_roles_without_reports(self):
        clean=b"a /a ext4 rw\n"
        cases=((b"\xff","UTF8_REQUIRED"),(b"\0","TEXT_CONTROL_UNSUPPORTED"),(b"a\rb","TEXT_CONTROL_UNSUPPORTED"),(chr(0x2028).encode(),"TEXT_CONTROL_UNSUPPORTED"),(chr(0x202e).encode(),"TEXT_CONTROL_UNSUPPORTED"))
        for role in (0,1):
            for index,(raw,code) in enumerate(cases):
                values=[clean,clean];values[role]=raw;self.fixture(*values);self.new_output(str(role)+"-"+str(index));self.report(error=code);self.assertFalse(self.output.exists())
    def test_byte_line_record_and_finding_limits_are_bounded(self):
        self.fixture(b"#"+b"x"*8191);self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        self.fixture(b"#"+b"x"*8192);self.new_output("line-over");self.report(error="TEXT_LINE_LIMIT")
        self.fixture(b"\n"*19999);self.new_output("lines-exact");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        self.fixture(b"\n"*20000);self.new_output("lines-over");self.report(error="TEXT_LINE_LIMIT")
        raw=(b"#"+b"x"*4094+b"\n")*256;self.fixture(raw);self.new_output("bytes-exact");self.assertEqual([r["bytes"] for r in self.report()["inputs"]],[1048576,1048576])
        self.fixture(b"",raw+b" ");self.new_output("bytes-over");self.report(error="INPUT_BYTE_LIMIT")
        rows=b"".join(("a /target"+str(i)+" ext4 rw\n").encode() for i in range(2000));self.fixture(rows);self.new_output("records-exact");self.assertEqual(len(self.report()["records"]),4000)
        self.fixture(rows+b"a /extra ext4 rw\n");self.new_output("records-over");self.report(error="RECORD_LIMIT")
        self.fixture(b"unsupported\n"*4001,b"");self.new_output("findings-over");self.report(error="FINDING_LIMIT")
    def test_cli_requires_dual_inputs_explicit_format_and_new_output(self):
        for args in ([],["--before",self.inputs[0]],["--before",self.inputs[0],"--after",self.inputs[1],"--output",self.output],self.args()+["--private-unknown=secret"]):self.call(args,error="ARGUMENTS_INVALID")
        args=self.args();args[5]="guess";self.call(args,error="ARGUMENTS_INVALID")
        for role in ("--before","--after"):
            for path,code in (("relative.fstab","LOCAL_ABSOLUTE_PATH_REQUIRED"),(self.work/".."/"fictional.fstab","LOCAL_ABSOLUTE_PATH_REQUIRED"),("//fictional/share/file.fstab","LOCAL_ABSOLUTE_PATH_REQUIRED"),(str(self.inputs[0])+"\nprivate","INVALID_LOCAL_PATH"),(self.copy,"REGULAR_FILE_REQUIRED"),(self.work/"missing.fstab","IO_OR_INPUT_ERROR")):
                args=self.args();args[args.index(role)+1]=path;self.call(args,error=code)
        args=self.args();args[-1]=self.work/"missing"/"report";self.call(args,error="IO_OR_INPUT_ERROR")
        self.report();self.report(error="OUTPUT_EXISTS")
        for destination in (*self.inputs,self.work,self.copy):
            args=self.args();args[-1]=destination;self.call(args,error="OUTPUT_EXISTS")
    def test_changed_short_reads_partial_manifest_and_report_budget(self):
        self.report(probe="changed_input",error="INPUT_CHANGED",ignore=[self.inputs[0]]);self.assertFalse(self.output.exists())
        self.fixture(b"a /a ext4 rw\n");self.report(probe="short_read",error="INPUT_CHANGED");self.assertFalse(self.output.exists())
        self.report(probe="manifest_failure",error="IO_OR_INPUT_ERROR");self.assertEqual({p.name for p in self.output.iterdir()},{"report.json","report.html"});self.report(error="OUTPUT_EXISTS")
        self.new_output("budget");self.report(probe='limit:{"MAX_REPORT":100}',error="REPORT_BYTE_LIMIT");self.assertFalse(self.output.exists())
    def test_same_file_hardlink_aliases_and_hostile_environment_are_controlled(self):
        path=self.inputs[0];alias=self.work/"hardlink.fstab";os.link(path,alias);self.assertTrue(path.samefile(alias))
        for second in (path,alias):
            args=self.args();args[3]=second;self.call(args,error="DUPLICATE_INPUT_FILE")
        hostile=self.work/"hostile imports";hostile.mkdir()
        for name in ("sitecustomize.py","usercustomize.py","json.py","re.py"):(hostile/name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env=dict(self.env,PYTHONPATH=str(hostile),PYTHONHOME=str(hostile),PYTHONSTARTUP=str(hostile/"sitecustomize.py"));self.report(env=env)
    def test_native_symlink_inputs_and_output_parents(self):
        alias=self.work/"linked.fstab";self.symlink(alias,self.inputs[0])
        for flag in ("--before","--after"):
            args=self.args();args[args.index(flag)+1]=alias;self.call(args,error="LINKED_PATH_REJECTED")
        route=self.work/"linked directory";self.symlink(route,self.work,directory=True)
        args=self.args();args[1]=route/self.inputs[0].name;self.call(args,error="LINKED_PATH_REJECTED")
        args=self.args();args[-1]=route/"new-report";self.call(args,error="LINKED_PATH_REJECTED")
        dangling=self.work/"dangling report";self.symlink(dangling,self.work/"nonexistent");args=self.args();args[-1]=dangling;self.call(args,error="OUTPUT_EXISTS")
    @unittest.skipUnless(os.name=="nt",PROCESS_WINDOWS_REASON)
    def test_native_windows_junction_and_stream_routes(self):
        junction=self.work/"junction";done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(junction),str(self.work)],capture_output=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:junction.rmdir() if junction.exists() else None)
        for flag,path in (("--before",self.inputs[0]),("--after",self.inputs[1]),("--output",self.output)):
            args=self.args();args[args.index(flag)+1]=junction/path.name;self.call(args,error="LINKED_PATH_REJECTED")
            args=self.args();args[args.index(flag)+1]=str(path)+":stream";self.call(args,error="DEVICE_OR_STREAM_PATH_REJECTED")
    @unittest.skipUnless(os.name!="nt",PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_bounds(self):
        fifo=self.work/"fictional.fifo";os.mkfifo(fifo)
        connection=socket.socket(socket.AF_UNIX);connection.bind(str(self.work/"fictional.sock"));self.addCleanup(connection.close)
        for path in (fifo,self.work/"fictional.sock"):
            for flag in ("--before","--after"):
                args=self.args();args[args.index(flag)+1]=path;self.call(args,error="REGULAR_FILE_REQUIRED")
        sparse=self.work/"fictional sparse.fstab"
        with sparse.open("wb") as stream:stream.truncate(1<<34)
        self.assertEqual(sparse.stat().st_size,1<<34);self.assertLess(sparse.stat().st_blocks*512,1<<20)
        args=self.args();args[1]=sparse;self.call(args,error="INPUT_BYTE_LIMIT");self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
