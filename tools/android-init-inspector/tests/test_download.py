"""Independent copied-runtime CLI consumers of fictional init text; no configurations are executed. MIT."""
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
RUNTIME = ("init_inspector.py", "text_support.py", "examples/generate.py")
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
import init_inspector as e
import text_support as s
assert Path(e.__file__).resolve()==base/'init_inspector.py'
assert Path(s.__file__).resolve()==base/'text_support.py'
assert e.source_inputs is s.source_inputs and e.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py'
 assert g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
selected=[Path(args[i+1]) for i,value in enumerate(args[:-1]) if value=='--file']
output=Path(args[args.index('--output')+1])
if kind=='audit':
 e.Parser(description=e.__doc__);b'\xef\xbb\xbfprewarm'.decode('utf-8-sig')
 allowed={base/name for name in ('init_inspector.py','text_support.py','examples/generate.py')}
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
        self.temp = tempfile.TemporaryDirectory(prefix="init-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.copy = self.work / "copied runtime"; self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT/name).read_bytes(); target = self.copy/name
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw); self.pins[name] = sha(raw)
        self.inputs = []; self.output = self.work/"new report"
        self.env = {k:v for k,v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
        self.fixture(b"service demo /fictional/bin/demo --never-executed\non boot\n start demo\n")
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
    def fixture(self, *raws):
        self.inputs = []
        for number,raw in enumerate(raws,1):
            path = self.work/("fictional init "+str(number)+".rc"); path.write_bytes(raw); self.inputs.append(path)
    def new_output(self, suffix):
        self.output = self.work/("new report "+str(suffix))
    def args(self):
        return [item for path in self.inputs for item in ("--file",path)] + ["--output",self.output]
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot(); prefix = ["-c",PROBE,self.copy,probe] if probe else [self.copy/"init_inspector.py"]
        done = self.run_child([*prefix,*args], env=env)
        self.assertEqual(done.stderr,b"",done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout,json.dumps(value,sort_keys=probe!="affinity").encode()+NEWLINE)
        if error is not None: self.assertEqual(value,dict(status="INCOMPLETE",error=error)); code = 2
        elif probe == "affinity": self.assertEqual(value,dict(status="COPIED_RUNTIME_AFFINITY",dependencies=0)); code = 0
        else:
            report = self.check_report(output,args)
            self.assertEqual(value,dict(status=report["status"],services=len(report["services"]),findings=len(report["findings"]),coverage_issues=len(report["coverage_issues"])))
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
        raw = (output/"report.json").read_bytes(); report = json.loads(raw); self.assertEqual(raw,encoded(report))
        self.assertEqual(set(report),{"schema_version","tool","scope","details_included","inputs","services","actions","imports","references","mount_all","findings","coverage_issues","status"})
        self.assertEqual((report["schema_version"],report["tool"]),(1,"Android Init Service Inspector"))
        self.assertEqual(report["status"],"REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        details = "--include-details" in args; self.assertIs(report["details_included"],details)
        selected = [Path(args[i+1]) for i,item in enumerate(args[:-1]) if item=="--file"]
        sources = [dict(id="input-"+str(i).zfill(4),bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for i,path in enumerate(selected,1)]
        self.assertEqual(report["inputs"],sources)
        service_ids = []
        for index,row in enumerate(report["services"],1):
            self.assertEqual(set(row),{"id","source","line","argument_count","options","restart_commands"}|({"name","executable"} if details else set()))
            self.assertEqual(row["id"],"service-"+str(index).zfill(4)); service_ids.append(row["id"])
            self.assertEqual(len(row["options"]),len(set(row["options"]))); self.assertGreaterEqual(row["argument_count"],0)
            self.assertTrue(set(row["options"])<={"disabled","oneshot","override","class","user","group","critical","reboot_on_failure","onrestart"})
        action_ids = []
        for index,row in enumerate(report["actions"],1):
            self.assertEqual(set(row),{"id","source","line"}|({"trigger_text"} if details else set()))
            self.assertEqual(row["id"],"action-"+str(index).zfill(4)); action_ids.append(row["id"])
        for row in report["imports"]:
            self.assertEqual(set(row),{"source","line","operand_count"}|({"declared_path"} if details and row["operand_count"]==1 else set()))
        for row in report["references"]:
            self.assertEqual(set(row),{"source","line","command","context","resolution","service_ids"}|({"declared_name"} if details else set()))
            self.assertIn(row["command"],{"start","stop","restart","exec_start"}); self.assertIn(row["context"],service_ids+action_ids)
            self.assertTrue(set(row["service_ids"])<=set(service_ids))
            expected = "unique_selected_declaration" if len(row["service_ids"])==1 else "ambiguous_selected_declarations" if row["service_ids"] else "not_declared_in_selected_files"
            self.assertEqual(row["resolution"],expected)
        for row in report["mount_all"]:
            self.assertEqual(set(row),{"source","line","mode"}|({"declared_path"} if details else set()))
            self.assertIn(row["mode"],{"--early","--late","unspecified"})
        for group in ("services","actions","imports","references","mount_all","findings","coverage_issues"):
            for row in report[group]:
                self.assertIn(row["source"],[r["id"] for r in sources]); self.assertGreaterEqual(row["line"],1)
        for row in report["findings"]+report["coverage_issues"]: self.assertEqual(set(row),{"code","source","line"})
        self.assertNotIn(str(self.work),raw.decode()); self.assertNotIn("FICTIONAL_PRIVATE_ARGV",raw.decode())
        markup = (output/"report.html").read_bytes(); parsed = StaticHTML(); parsed.feed(markup.decode()); parsed.close()
        self.assertEqual(parsed.tags.count("html"),1); self.assertEqual(parsed.csp,["default-src 'none'; style-src 'unsafe-inline'"])
        self.assertIn(html.escape(raw.decode(),quote=True).encode(),markup)
        members = {name:(output/name).read_bytes() for name in ("report.json","report.html")}
        manifest = dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=sha(data)) for name,data in sorted(members.items())])
        self.assertEqual((output/"MANIFEST.json").read_bytes(),encoded(manifest)); return report
    def report(self, details=False, **kwargs):
        return self.call(self.args()+(["--include-details"] if details else []),output=self.output,allow=[self.output],**kwargs)
    def codes(self, report):
        return {row["code"] for row in report["findings"]+report["coverage_issues"]}
    def symlink(self, path, target, directory=False):
        try: path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            if os.name=="nt" and getattr(error,"winerror",None)==1314 and os.environ.get("OUTLANDS_INIT_REQUIRE_LINKS")!="1": self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_copied_runtime_affinity_and_help(self):
        self.call([],probe="affinity")
        for script in (self.copy/"init_inspector.py",self.copy/"examples/generate.py"):
            before=self.snapshot();done=self.run_child([script,"--help"])
            self.assertEqual((done.returncode,done.stderr),(0,b""));self.assertIn(b"--output",done.stdout);self.assertEqual(self.snapshot(),before)
    def test_generator_cli_two_fictional_inputs_and_new_only_output(self):
        target=self.work/"generated";before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(0,b"",json.dumps(dict(status="FICTIONAL_EXAMPLES_CREATED",files=2),sort_keys=True).encode()+NEWLINE))
        self.assertEqual({p.name for p in target.iterdir()},{"clean.rc","review.rc"});self.assertEqual({k:self.snapshot().get(k) for k in before},before)
        for name,status,services in (("clean","NO_SCOPE_FINDINGS",1),("review","REVIEW_REQUIRED",2)):
            self.inputs=[target/(name+".rc")];self.new_output(name);report=self.report();self.assertEqual((report["status"],len(report["services"])),(status,services))
            if name=="clean":self.assertEqual(report["references"][0]["resolution"],"unique_selected_declaration")
            else:self.assertEqual([r["resolution"] for r in report["references"]],["ambiguous_selected_declarations","not_declared_in_selected_files"])
        before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(2,b"",json.dumps(dict(status="INCOMPLETE",error="OUTPUT_EXISTS"),sort_keys=True).encode()+NEWLINE));self.assertEqual(self.snapshot(),before)
    def test_literal_service_action_names_lines_and_argument_counts(self):
        self.fixture(b"# fictional\n\tservice worker-1.name /fictional/bin/worker --one two\n\tclass main\non boot\n\tstart worker-1.name\n")
        report=self.report(details=True)
        self.assertEqual(report["status"],"NO_SCOPE_FINDINGS")
        self.assertEqual(report["services"],[dict(id="service-0001",source="input-0001",line=2,argument_count=2,options=["class"],restart_commands=0,name="worker-1.name",executable="/fictional/bin/worker")])
        self.assertEqual(report["actions"],[dict(id="action-0001",source="input-0001",line=4,trigger_text="boot")])
        self.assertEqual(report["references"],[dict(source="input-0001",line=5,command="start",context="action-0001",resolution="unique_selected_declaration",service_ids=["service-0001"],declared_name="worker-1.name")])
    def test_supported_options_are_distinct_observations_without_operand_leaks(self):
        raw=b"service demo /fictional/bin\n disabled\n oneshot\n override\n class main late\n user FICTIONAL_PRIVATE_ARGV_USER\n group FICTIONAL_PRIVATE_ARGV_GROUP other\n disabled\n"
        self.fixture(raw);report=self.report(details=True)
        self.assertEqual(report["services"][0]["options"],["disabled","oneshot","override","class","user","group"])
        self.assertEqual(report["services"][0]["restart_commands"],0);self.assertEqual(self.codes(report),set())
        for member in self.output.iterdir():self.assertNotIn(b"FICTIONAL_PRIVATE_ARGV",member.read_bytes())
    def test_critical_reboot_and_restart_markers_are_findings_only(self):
        self.fixture(b"service demo /fictional/bin\n critical\n critical 1 FICTIONAL_PRIVATE_ARGV_WINDOW\n reboot_on_failure FICTIONAL_PRIVATE_ARGV_TARGET\n onrestart reboot FICTIONAL_PRIVATE_ARGV_REASON\n")
        report=self.report();self.assertEqual(report["services"][0]["options"],["critical","reboot_on_failure","onrestart"]);self.assertEqual(report["services"][0]["restart_commands"],1)
        self.assertEqual(report["findings"],[dict(code="CRITICAL_SERVICE_DECLARED",source="input-0001",line=2),dict(code="CRITICAL_SERVICE_DECLARED",source="input-0001",line=3),dict(code="REBOOT_ON_FAILURE_DECLARED",source="input-0001",line=4),dict(code="RESTART_REBOOT_DECLARED",source="input-0001",line=5)])
        self.assertEqual(report["references"],[]);self.assertEqual(report["coverage_issues"],[])
    def test_restart_commands_count_and_references_use_service_context(self):
        raw=b"service first /fictional/first\n onrestart start second\n onrestart stop second\n onrestart restart second\n onrestart exec_start second\n onrestart setprop FICTIONAL_PRIVATE_ARGV value\n onrestart restart second extra\nservice second /fictional/second\n"
        self.fixture(raw);report=self.report(details=True)
        self.assertEqual(report["services"][0]["restart_commands"],6);self.assertEqual(report["services"][0]["options"],["onrestart"])
        self.assertEqual([r["command"] for r in report["references"]],["start","stop","restart","exec_start"])
        self.assertEqual([(r["context"],r["service_ids"],r["resolution"]) for r in report["references"]],[("service-0001",["service-0002"],"unique_selected_declaration")]*4)
        self.assertEqual([(r["code"],r["line"]) for r in report["coverage_issues"]],[("UNINSPECTED_RESTART_COMMAND",6),("UNINSPECTED_RESTART_COMMAND",7)])
    def test_action_references_resolve_unique_ambiguous_and_undeclared_names(self):
        self.fixture(b"on boot\n start one\n stop one\n restart repeated\n exec_start absent\n",b"service one /fictional/a\nservice repeated /fictional/b\nservice repeated /fictional/c\n")
        report=self.report(details=True)
        self.assertEqual([r["declared_name"] for r in report["references"]],["one","one","repeated","absent"])
        self.assertEqual([r["service_ids"] for r in report["references"]],[["service-0001"],["service-0001"],["service-0002","service-0003"],[]])
        self.assertEqual([r["resolution"] for r in report["references"]],["unique_selected_declaration","unique_selected_declaration","ambiguous_selected_declarations","not_declared_in_selected_files"])
        self.assertEqual(self.codes(report),{"DUPLICATE_SERVICE_DECLARATION","REFERENCE_NEEDS_SELECTED_FILE_REVIEW"})
    def test_duplicate_override_declarations_never_choose_a_winner(self):
        self.fixture(b"service same /fictional/a\n override\nservice same /fictional/b\n override\nservice same /fictional/c\non boot\n start same\n")
        report=self.report(details=True)
        self.assertEqual([r["executable"] for r in report["services"]],["/fictional/a","/fictional/b","/fictional/c"])
        self.assertEqual(report["references"][0]["service_ids"],["service-0001","service-0002","service-0003"])
        self.assertEqual(report["references"][0]["resolution"],"ambiguous_selected_declarations")
        self.assertEqual([r["line"] for r in report["findings"] if r["code"]=="DUPLICATE_SERVICE_DECLARATION"],[1,3,5])
    def test_import_target_and_mount_target_are_never_opened_or_evaluated(self):
        foreign=self.work/"not-selected.rc";foreign.write_bytes(b"service hidden /fictional/hidden\n")
        fstab=self.work/"not-selected.fstab";fstab.write_bytes(b"FICTIONAL_PRIVATE_ARGV_DO_NOT_OPEN\n")
        raw=("import "+foreign.name+"\non boot\n start hidden\n mount_all "+fstab.name+" --early\n").encode()
        self.fixture(raw);report=self.report(probe="audit")
        self.assertEqual(report["services"],[]);self.assertEqual(report["references"][0]["resolution"],"not_declared_in_selected_files");self.assertEqual(len(report["mount_all"]),1)
        self.assertEqual(self.codes(report),{"IMPORTS_NOT_FOLLOWED","REFERENCE_NEEDS_SELECTED_FILE_REVIEW"})
        self.inputs.append(foreign);self.new_output("explicitly-selected");report=self.report(probe="audit")
        self.assertEqual(report["references"][0]["resolution"],"unique_selected_declaration");self.assertEqual(report["references"][0]["service_ids"],["service-0001"])
    def test_import_operand_counts_and_context_reset_are_explicit(self):
        self.fixture(b"service a /fictional/a\nimport\n disabled\non boot\nimport /fictional/missing.rc extra\n start a\nimport /fictional/single.rc\n")
        report=self.report(details=True)
        self.assertEqual([r["operand_count"] for r in report["imports"]],[0,2,1]);self.assertEqual(report["imports"][2]["declared_path"],"/fictional/single.rc")
        self.assertNotIn("declared_path",report["imports"][0]);self.assertNotIn("declared_path",report["imports"][1]);self.assertEqual(report["services"][0]["options"],[]);self.assertEqual(report["references"],[])
        self.assertEqual([(r["code"],r["line"]) for r in report["coverage_issues"]],[("IMPORTS_NOT_FOLLOWED",2),("STATEMENT_WITHOUT_SUPPORTED_SECTION",3),("IMPORTS_NOT_FOLLOWED",5),("STATEMENT_WITHOUT_SUPPORTED_SECTION",6),("IMPORTS_NOT_FOLLOWED",7)])
    def test_mount_modes_and_malformed_action_commands_are_not_executed(self):
        self.fixture(b"on boot\n mount_all /fictional/fstab --early\n mount_all /fictional/fstab --late\n mount_all /fictional/fstab\n mount_all /fictional/fstab --wrong\n mount_all\n mount_all /fictional/fstab --early extra\n")
        report=self.report(details=True,probe="audit")
        self.assertEqual([r["mode"] for r in report["mount_all"]],["--early","--late","unspecified"]);self.assertEqual([r["declared_path"] for r in report["mount_all"]],["/fictional/fstab"]*3)
        self.assertEqual([(r["code"],r["line"]) for r in report["coverage_issues"]],[("UNINSPECTED_ACTION_COMMAND",5),("UNINSPECTED_ACTION_COMMAND",6),("UNINSPECTED_ACTION_COMMAND",7)])
    def test_wrong_context_does_not_reclassify_options_or_action_commands(self):
        self.fixture(b"start demo\non boot\n disabled\n onrestart restart demo\nservice demo /fictional/bin\n mount_all /fictional/fstab\n start demo\n socket marker stream 0660\n disabled\n")
        report=self.report();self.assertEqual(report["references"],[]);self.assertEqual(report["mount_all"],[]);self.assertEqual(report["services"][0]["options"],["disabled"])
        self.assertEqual([r["code"] for r in report["coverage_issues"]],["STATEMENT_WITHOUT_SUPPORTED_SECTION","UNINSPECTED_ACTION_COMMAND","UNINSPECTED_ACTION_COMMAND","UNINSPECTED_SERVICE_OPTION","UNINSPECTED_SERVICE_OPTION","UNINSPECTED_SERVICE_OPTION"])
    def test_service_name_boundaries_and_invalid_headers_reset_context(self):
        for index,header in enumerate(("service","service only","service bad/name /fictional/a","service bad:name /fictional/a","service "+"a"*129+" /fictional/a","service "+chr(960)+" /fictional/a")):
            self.fixture(("service valid /fictional/valid\n"+header+"\n disabled\n").encode());self.new_output(index);report=self.report()
            self.assertEqual(len(report["services"]),1);self.assertEqual(report["services"][0]["options"],[])
            self.assertEqual([r["code"] for r in report["coverage_issues"]],["INVALID_SERVICE_DECLARATION","STATEMENT_WITHOUT_SUPPORTED_SECTION"])
        name="a"*128;self.fixture(("service "+name+" /fictional/a\non boot\n start "+name+"\n").encode());self.new_output("exact");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
    def test_action_headers_and_literal_triggers_are_not_property_evaluation(self):
        self.fixture(b"service demo /fictional/bin\non\n disabled\non property:fictional=1 && boot\n start demo\n")
        report=self.report(details=True);self.assertEqual(report["services"][0]["options"],[])
        self.assertEqual(report["actions"],[dict(id="action-0001",source="input-0001",line=4,trigger_text="property:fictional=1 && boot")])
        self.assertEqual(report["references"][0]["service_ids"],["service-0001"])
        self.assertEqual([r["code"] for r in report["coverage_issues"]],["INVALID_ACTION_DECLARATION","STATEMENT_WITHOUT_SUPPORTED_SECTION"])
    def test_quotes_backslashes_and_expansions_reset_both_section_contexts(self):
        tokens=('"quoted"',"'quoted'",r"escaped\word","${fictional}")
        for index,token in enumerate(tokens):
            self.fixture(("service demo /fictional/bin\n disabled "+token+"\n oneshot\non boot\n start "+token+"\n start demo\n").encode());self.new_output(index);report=self.report()
            self.assertEqual(report["services"][0]["options"],[]);self.assertEqual(report["references"],[])
            self.assertEqual([r["code"] for r in report["coverage_issues"]],["NONLITERAL_STATEMENT","STATEMENT_WITHOUT_SUPPORTED_SECTION","NONLITERAL_STATEMENT","STATEMENT_WITHOUT_SUPPORTED_SECTION"])
    def test_physical_continuations_are_not_joined_and_new_headers_recover(self):
        self.fixture(b"service bad /fictional/bin \\\n FICTIONAL_PRIVATE_ARGV_CONTINUED\n disabled\nservice good /fictional/good\non boot \\\n start good\non boot\n start good\n")
        report=self.report(details=True);self.assertEqual([r["name"] for r in report["services"]],["good"]);self.assertEqual(len(report["actions"]),1);self.assertEqual([r["line"] for r in report["references"]],[8])
        self.assertEqual([r["code"] for r in report["coverage_issues"]],["NONLITERAL_STATEMENT","STATEMENT_WITHOUT_SUPPORTED_SECTION","STATEMENT_WITHOUT_SUPPORTED_SECTION","NONLITERAL_STATEMENT","STATEMENT_WITHOUT_SUPPORTED_SECTION"])
    def test_full_line_comments_are_ignored_but_inline_comments_are_tokens(self):
        self.fixture(b" # service fake /fictional/fake $quoted \\\n\t# on boot 'ignored'\nservice demo /fictional/bin # FICTIONAL_PRIVATE_ARGV_COMMENT\n disabled # inline\non boot\n start demo # inline\n")
        report=self.report();self.assertEqual(len(report["services"]),1);self.assertEqual(report["services"][0]["argument_count"],2);self.assertEqual(report["services"][0]["options"],[]);self.assertEqual(report["references"],[])
        self.assertEqual([r["code"] for r in report["coverage_issues"]],["UNINSPECTED_SERVICE_OPTION","UNINSPECTED_ACTION_COMMAND"])
        self.fixture(b"# comment only\n \t\n");self.new_output("comments");report=self.report();self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertEqual(report["services"],[]);self.assertEqual(report["actions"],[])
        self.fixture(b"");self.new_output("empty");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
    def test_section_context_never_leaks_between_selected_files(self):
        self.fixture(b"service first /fictional/a\n",b" disabled\n start first\non boot\n start first\n",b" start first\nservice second /fictional/b\n")
        report=self.report();self.assertEqual([r["options"] for r in report["services"]],[[],[]]);self.assertEqual([(r["source"],r["line"],r["context"]) for r in report["references"]],[("input-0002",4,"action-0001")])
        self.assertEqual([(r["source"],r["line"]) for r in report["coverage_issues"]],[("input-0002",1),("input-0002",2),("input-0003",1)])
    def test_selected_order_controls_ids_and_exact_byte_hashes(self):
        first=b"service alpha /fictional/a\n";second=b"\xef\xbb\xbfservice beta /fictional/b\r\non boot\r\n start alpha\r\n start beta\r\n"
        self.fixture(first,second);report=self.report(details=True)
        self.assertEqual([r["name"] for r in report["services"]],["alpha","beta"]);self.assertEqual([r["service_ids"] for r in report["references"]],[["service-0001"],["service-0002"]]);self.assertEqual([r["sha256"] for r in report["inputs"]],[sha(first),sha(second)])
        self.inputs.reverse();self.new_output("reversed");report=self.report(details=True)
        self.assertEqual([r["name"] for r in report["services"]],["beta","alpha"]);self.assertEqual([r["service_ids"] for r in report["references"]],[["service-0002"],["service-0001"]]);self.assertEqual(report["references"][0]["line"],3)
    def test_details_optin_never_includes_raw_service_or_option_argv(self):
        raw=b"service private_name /fictional/private_executable FICTIONAL_PRIVATE_ARGV_ONE --FICTIONAL_PRIVATE_ARGV_TWO\n user FICTIONAL_PRIVATE_ARGV_USER\n group FICTIONAL_PRIVATE_ARGV_GROUP\non private_trigger\n start private_name\n mount_all /fictional/private_fstab\nimport /fictional/private_import.rc\n"
        self.fixture(raw);basic=self.report();self.new_output("details");detailed=self.report(details=True)
        for group in ("services","actions","imports","references","mount_all"):
            self.assertEqual(len(basic[group]),len(detailed[group]))
        for word in ("private_name","private_executable","private_trigger","private_fstab","private_import"):
            self.assertNotIn(word,json.dumps(basic));self.assertIn(word,json.dumps(detailed))
        self.assertEqual(detailed["services"][0]["argument_count"],2)
        for report in (basic,detailed):self.assertNotIn("FICTIONAL_PRIVATE_ARGV",json.dumps(report));self.assertNotIn("argv",json.dumps(report))
    def test_html_escapes_declared_details_and_audit_blocks_external_actions(self):
        self.fixture(b"service demo /fictional/<worker>& FICTIONAL_PRIVATE_ARGV\non </pre><script>never_execute</script>&\n start demo\n mount_all /fictional/<fstab>& --late\nimport /fictional/<import>&\n")
        report=self.report(details=True,probe="audit");self.assertEqual(report["actions"][0]["trigger_text"],"</pre><script>never_execute</script>&")
        markup=(self.output/"report.html").read_bytes();self.assertNotIn(b"<script>",markup);self.assertIn(b"&lt;script&gt;never_execute&lt;/script&gt;&amp;",markup)
        for member in self.output.iterdir():self.assertNotIn(b"FICTIONAL_PRIVATE_ARGV",member.read_bytes())
        self.assertEqual([r["path"] for r in json.loads((self.output/"MANIFEST.json").read_bytes())["files"]],["report.html","report.json"])
    def test_utf8_bom_crlf_unicode_and_physical_controls(self):
        self.fixture(b"\xef\xbb\xbfservice demo /fictional/bin\r\non boot\r\n start demo\r\n");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        for index,(raw,code) in enumerate(((b"\xff","UTF8_REQUIRED"),(b"\0","TEXT_CONTROL_UNSUPPORTED"),(b"a\rb","TEXT_CONTROL_UNSUPPORTED"),(chr(0x2028).encode(),"TEXT_CONTROL_UNSUPPORTED"),(chr(0x202e).encode(),"TEXT_CONTROL_UNSUPPORTED"),(b"service demo /a\x1b","TEXT_CONTROL_UNSUPPORTED"))):
            self.fixture(raw);self.new_output(index);self.report(error=code);self.assertFalse(self.output.exists())
    def test_byte_line_input_count_and_aggregate_limits(self):
        self.fixture(b"#"+b"x"*8191);self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        self.fixture(b"#"+b"x"*8192);self.new_output("line-over");self.report(error="TEXT_LINE_LIMIT")
        self.fixture(b"\n"*19999);self.new_output("lines-exact");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        self.fixture(b"\n"*20000);self.new_output("lines-over");self.report(error="TEXT_LINE_LIMIT")
        raw=(b"#"+b"x"*4094+b"\n")*256;self.fixture(raw);self.new_output("bytes-exact");self.assertEqual(self.report()["inputs"][0]["bytes"],1048576)
        self.fixture(raw+b" ");self.new_output("bytes-over");self.report(error="INPUT_BYTE_LIMIT")
        self.fixture(*(b"" for _ in range(33)));self.new_output("count-over");self.report(error="INPUT_COUNT_LIMIT")
        self.inputs.pop();self.new_output("count-exact");self.assertEqual(len(self.report()["inputs"]),32)
        self.fixture(*(raw for _ in range(5)));self.new_output("total-over");self.report(error="TOTAL_BYTE_LIMIT")
    def test_record_and_finding_collection_bounds_refuse_before_reports(self):
        raw=b"".join(("service s"+str(i)+" /fictional/bin\n").encode() for i in range(4000));self.fixture(raw);self.assertEqual(len(self.report()["services"]),4000)
        self.fixture(raw+b"service extra /fictional/bin\n");self.new_output("records-over");self.report(error="RECORD_LIMIT")
        self.fixture(b"outside\n"*4001);self.new_output("findings-over");self.report(error="FINDING_LIMIT")
        self.fixture(b"service first /fictional/a\nservice second /fictional/b\n");self.new_output("lowered");self.report(probe='limit:{"MAX_ITEMS":1}',error="RECORD_LIMIT")
    def test_cli_arguments_local_paths_and_no_overwrite_are_fixed_private_codes(self):
        for args in ([],["--file",self.inputs[0]],["--private-unknown=secret"],["--output",self.output]):self.call(args,error="ARGUMENTS_INVALID")
        for path,code in (("relative.rc","LOCAL_ABSOLUTE_PATH_REQUIRED"),(self.work/".."/"fictional.rc","LOCAL_ABSOLUTE_PATH_REQUIRED"),("//fictional/share/file.rc","LOCAL_ABSOLUTE_PATH_REQUIRED"),(str(self.inputs[0])+"\nprivate","INVALID_LOCAL_PATH"),(self.copy,"REGULAR_FILE_REQUIRED"),(self.work/"missing.rc","IO_OR_INPUT_ERROR")):
            self.call(["--file",path,"--output",self.output],error=code)
        self.call(["--file",self.inputs[0],"--output","relative-report"],error="LOCAL_ABSOLUTE_PATH_REQUIRED")
        self.call(["--file",self.inputs[0],"--output",self.work/"missing"/"report"],error="IO_OR_INPUT_ERROR")
        self.report();self.report(error="OUTPUT_EXISTS")
        for destination in (self.inputs[0],self.work,self.copy):self.call(["--file",self.inputs[0],"--output",destination],error="OUTPUT_EXISTS")
    def test_changed_short_reads_partial_report_and_report_budget_failures(self):
        self.report(probe="changed_input",error="INPUT_CHANGED",ignore=self.inputs);self.assertFalse(self.output.exists())
        self.fixture(b"service demo /fictional/bin\n");self.report(probe="short_read",error="INPUT_CHANGED");self.assertFalse(self.output.exists())
        self.report(probe="manifest_failure",error="IO_OR_INPUT_ERROR");self.assertEqual({p.name for p in self.output.iterdir()},{"report.json","report.html"});self.report(error="OUTPUT_EXISTS")
        self.new_output("budget");self.report(probe='limit:{"MAX_REPORT":100}',error="REPORT_BYTE_LIMIT");self.assertFalse(self.output.exists())
    def test_same_file_hardlink_aliases_and_hostile_environment(self):
        path=self.inputs[0];alias=self.work/"hardlink.rc";os.link(path,alias);self.assertTrue(path.samefile(alias))
        for second in (path,alias):self.call(["--file",path,"--file",second,"--output",self.output],error="DUPLICATE_INPUT_FILE")
        hostile=self.work/"hostile imports";hostile.mkdir()
        for name in ("sitecustomize.py","usercustomize.py","json.py","re.py"):(hostile/name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env=dict(self.env,PYTHONPATH=str(hostile),PYTHONHOME=str(hostile),PYTHONSTARTUP=str(hostile/"sitecustomize.py"));self.report(env=env)
    def test_native_symlink_inputs_and_output_parents(self):
        alias=self.work/"linked.rc";self.symlink(alias,self.inputs[0]);self.call(["--file",alias,"--output",self.output],error="LINKED_PATH_REJECTED")
        route=self.work/"linked directory";self.symlink(route,self.work,directory=True)
        self.call(["--file",route/self.inputs[0].name,"--output",self.output],error="LINKED_PATH_REJECTED")
        self.call(["--file",self.inputs[0],"--output",route/"new-report"],error="LINKED_PATH_REJECTED")
        dangling=self.work/"dangling report";self.symlink(dangling,self.work/"nonexistent");self.call(["--file",self.inputs[0],"--output",dangling],error="OUTPUT_EXISTS")
    @unittest.skipUnless(os.name=="nt",PROCESS_WINDOWS_REASON)
    def test_native_windows_junction_and_stream_routes(self):
        junction=self.work/"junction";done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(junction),str(self.work)],capture_output=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:junction.rmdir() if junction.exists() else None)
        self.call(["--file",junction/self.inputs[0].name,"--output",self.output],error="LINKED_PATH_REJECTED")
        self.call(["--file",self.inputs[0],"--output",junction/"new-report"],error="LINKED_PATH_REJECTED")
        self.call(["--file",str(self.inputs[0])+":stream","--output",self.output],error="DEVICE_OR_STREAM_PATH_REJECTED")
        self.call(["--file",self.inputs[0],"--output",str(self.output)+":stream"],error="DEVICE_OR_STREAM_PATH_REJECTED")
    @unittest.skipUnless(os.name!="nt",PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_bounds(self):
        fifo=self.work/"fictional.fifo";os.mkfifo(fifo)
        connection=socket.socket(socket.AF_UNIX);connection.bind(str(self.work/"fictional.sock"));self.addCleanup(connection.close)
        for path in (fifo,self.work/"fictional.sock"):self.call(["--file",path,"--output",self.output],error="REGULAR_FILE_REQUIRED")
        sparse=self.work/"fictional sparse.rc"
        with sparse.open("wb") as stream:stream.truncate(1<<34)
        self.assertEqual(sparse.stat().st_size,1<<34);self.assertLess(sparse.stat().st_blocks*512,1<<20)
        self.call(["--file",sparse,"--output",self.output],error="INPUT_BYTE_LIMIT");self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
