"""Independent copied module metadata consumers; no module binary loading or evaluation. MIT."""
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
RUNTIME = ("module_inspector.py", "inspection_support.py", "examples/generate.py")
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
import module_inspector as e
import inspection_support as s
assert Path(e.__file__).resolve()==base/'module_inspector.py'
assert Path(s.__file__).resolve()==base/'inspection_support.py'
assert e.source_inputs is s.source_inputs and e.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py'
 assert g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
selected=[Path(args[args.index(flag)+1]) for flag in ('--deps','--load-list','--available') if flag in args]
output=Path(args[args.index('--output')+1])
if kind=='audit':
 e.Parser(description=e.__doc__);b'\xef\xbb\xbfprewarm'.decode('utf-8-sig')
 allowed={base/name for name in ('module_inspector.py','inspection_support.py','examples/generate.py')}
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
  assert name in ('MAX_ITEMS','MAX_REPORT','MAX_LINE','MAX_LINES','MAX_NODES','MAX_EDGES','MAX_CYCLE_NODES')
  setattr(e if name in ('MAX_NODES','MAX_EDGES','MAX_CYCLE_NODES') else s,name,value)
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
        self.temp = tempfile.TemporaryDirectory(prefix="module-cli-", dir=parent)
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
        self.fixture(b"a.ko:\n",b"a\n",b"a.ko\n")
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
    def fixture(self, deps, load=b"", available=None):
        self.inputs = []
        for name,data in (("dependencies.dep",deps),("selection.load",load),("inventory.txt",available)):
            if data is None: continue
            path=self.work/("fictional "+name);path.write_bytes(data);self.inputs.append(path)
    def new_output(self, suffix):
        self.output = self.work/("new report "+str(suffix))
    def args(self):
        result=["--deps",self.inputs[0],"--load-list",self.inputs[1]]
        if len(self.inputs)==3:result += ["--available",self.inputs[2]]
        return result+["--output",self.output]
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot(); prefix = ["-c",PROBE,self.copy,probe] if probe else [self.copy/"module_inspector.py"]
        done = self.run_child([*prefix,*args], env=env)
        self.assertEqual(done.stderr,b"",done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout,json.dumps(value,sort_keys=probe!="affinity").encode()+NEWLINE)
        if error is not None: self.assertEqual(value,dict(status="INCOMPLETE",error=error)); code = 2
        elif probe == "affinity": self.assertEqual(value,dict(status="COPIED_RUNTIME_AFFINITY",dependencies=0)); code = 0
        else:
            report = self.check_report(output,args)
            self.assertEqual(value,dict(status=report["status"],modules=len(report["modules"]),findings=len(report["findings"]),coverage_issues=len(report["coverage_issues"])))
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
        self.assertEqual(set(report),{"schema_version","tool","scope","details_included","inputs","modules","dependencies","load_entries","cycle_witnesses","findings","coverage_issues","declared_inventory_checked","selected_dependency_order","blocked_selected_modules","selected_plan_complete_within_metadata","plan_scope","status"})
        self.assertEqual((report["schema_version"],report["tool"]),(1,"Kernel Module List & Dependency Inspector"))
        details="--include-details" in args;self.assertIs(report["details_included"],details)
        self.assertEqual(report["status"],"REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        selected=[Path(args[args.index(flag)+1]) for flag in ("--deps","--load-list","--available") if flag in args]
        self.assertEqual(report["inputs"],[dict(id=side,bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for side,path in zip(("dependencies","load-list","declared-inventory"),selected)])
        self.assertIs(report["declared_inventory_checked"],"--available" in args)
        ids=[row["id"] for row in report["modules"]]
        self.assertEqual(ids,["module-"+str(i).zfill(4) for i in range(1,len(ids)+1)])
        for row in report["modules"]:
            self.assertEqual(set(row),{"id","source","line","dependency_count"}|({"declared_path"} if details else set()))
            self.assertEqual(row["source"],"dependencies");self.assertGreaterEqual(row["line"],1);self.assertGreaterEqual(row["dependency_count"],0)
        for row in report["dependencies"]:
            self.assertEqual(set(row),{"consumer","resolution","dependency"}|({"declared_path"} if details else set()))
            self.assertIn(row["consumer"],ids)
            self.assertIn(row["resolution"],{"unique_selected_declaration","ambiguous_selected_declarations","not_declared_in_selected_metadata"})
            if row["resolution"]=="unique_selected_declaration":self.assertIn(row["dependency"],ids)
            else:self.assertIsNone(row["dependency"])
        for row in report["load_entries"]:
            self.assertEqual(set(row),{"source","line","resolution","module_ids"}|({"declared_name"} if details else set()))
            self.assertEqual(row["source"],"load-list");self.assertGreaterEqual(row["line"],1)
            self.assertIn(row["resolution"],{"unique_selected_declaration","ambiguous_or_unresolved"})
            self.assertEqual(len(row["module_ids"]),len(set(row["module_ids"])));self.assertTrue(set(row["module_ids"])<=set(ids))
            if row["resolution"]=="unique_selected_declaration":self.assertEqual(len(row["module_ids"]),1)
        order=report["selected_dependency_order"];blocked=report["blocked_selected_modules"]
        self.assertEqual(len(order),len(set(order)));self.assertEqual(len(blocked),len(set(blocked)))
        self.assertTrue(set(order)|set(blocked)<=set(ids));self.assertFalse(set(order)&set(blocked))
        for witness in report["cycle_witnesses"]:
            self.assertGreaterEqual(len(witness),2);self.assertEqual(witness[0],witness[-1]);self.assertTrue(set(witness)<=set(ids))
            self.assertEqual(len(witness[:-1]),len(set(witness[:-1])))
            for consumer,dependency in zip(witness,witness[1:]):
                self.assertTrue(any(row["consumer"]==consumer and row["dependency"]==dependency and row["resolution"]=="unique_selected_declaration" for row in report["dependencies"]))
        for row in report["dependencies"]:
            if row["consumer"] in order and row["dependency"] in order:self.assertLess(order.index(row["dependency"]),order.index(row["consumer"]))
        complete=not report["coverage_issues"] and not blocked and all(row["resolution"]=="unique_selected_declaration" for row in report["load_entries"])
        self.assertIs(report["selected_plan_complete_within_metadata"],complete)
        self.assertEqual(report["plan_scope"],"Unique declared selected dependency closure only; dependencies need not appear separately in the load list. No runtime load authorization.")
        for row in report["findings"]+report["coverage_issues"]:
            self.assertEqual(set(row),{"code","source","line"});self.assertIn(row["source"],{"dependencies","load-list","declared-inventory"});self.assertGreaterEqual(row["line"],1)
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
            if os.name=="nt" and getattr(error,"winerror",None)==1314 and os.environ.get("OUTLANDS_MODULE_REQUIRE_LINKS")!="1": self.skipTest(PROCESS_SYMLINK_REASON)
            raise


    def test_copied_runtime_affinity_and_help(self):
        self.call([],probe="affinity")
        for script in (self.copy/"module_inspector.py",self.copy/"examples/generate.py"):
            before=self.snapshot();done=self.run_child([script,"--help"])
            self.assertEqual((done.returncode,done.stderr),(0,b""));self.assertIn(b"--output",done.stdout);self.assertEqual(self.snapshot(),before)
    def test_generator_cli_five_fictional_files_and_fresh_output(self):
        target=self.work/"generated";before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(0,b"",json.dumps(dict(status="FICTIONAL_EXAMPLES_CREATED",files=5),sort_keys=True).encode()+NEWLINE))
        self.assertEqual({p.name for p in target.iterdir()},{"clean.dep","clean.load","available.txt","review.dep","review.load"});self.assertEqual({k:self.snapshot().get(k) for k in before},before)
        for name,status in (("clean","NO_SCOPE_FINDINGS"),("review","REVIEW_REQUIRED")):
            self.inputs=[target/(name+".dep"),target/(name+".load")];self.new_output(name);report=self.report();self.assertEqual(report["status"],status)
        self.inputs=[target/"clean.dep",target/"clean.load",target/"available.txt"];self.new_output("inventory");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target]);self.assertEqual((done.returncode,done.stderr),(2,b""));self.assertEqual(json.loads(done.stdout),dict(status="INCOMPLETE",error="OUTPUT_EXISTS"));self.assertEqual(self.snapshot(),before)
    def test_dependency_closure_is_dependency_first_not_declaration_or_load_order(self):
        self.fixture(b"demo/feature.ko: demo/helper.ko demo/core.ko\ndemo/helper.ko: demo/core.ko\ndemo/core.ko:\n",b"feature\n")
        report=self.report();self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertEqual(report["selected_dependency_order"],["module-0003","module-0002","module-0001"]);self.assertEqual(report["blocked_selected_modules"],[]);self.assertTrue(report["selected_plan_complete_within_metadata"])
    def test_exact_path_precedence_and_basename_ambiguity(self):
        self.fixture(b"demo.ko:\none/demo.ko:\ntwo/demo.ko:\n",b"demo.ko\n")
        report=self.report();self.assertEqual(report["selected_dependency_order"],["module-0001"]);self.assertEqual(report["load_entries"][0]["module_ids"],["module-0001"])
        self.fixture(b"one/demo.ko:\ntwo/demo.ko:\n",b"demo\n");self.new_output("ambiguous");report=self.report();self.assertFalse(report["selected_plan_complete_within_metadata"]);self.assertEqual(report["load_entries"][0]["module_ids"],["module-0001","module-0002"])
        self.fixture(b"one/demo.ko:\ntwo/demo.ko:\n",b"one/demo.ko\n");self.new_output("explicit");self.assertEqual(self.report()["selected_dependency_order"],["module-0001"])
    def test_duplicate_declarations_remain_ambiguous_in_dependencies_and_aliases(self):
        self.fixture(b"one/demo.ko:\none/demo.ko:\ntwo/demo.ko:\nconsumer.ko: one/demo.ko\n",b"demo\nconsumer\n")
        report=self.report();self.assertEqual(self.codes(report),{"AMBIGUOUS_MODULE_DECLARATION","DEPENDENCY_NEEDS_METADATA_REVIEW","LOAD_SELECTION_NEEDS_METADATA_REVIEW"});self.assertEqual(report["dependencies"],[dict(consumer="module-0004",resolution="ambiguous_selected_declarations",dependency=None)])
        self.assertEqual(report["load_entries"][0]["resolution"],"ambiguous_or_unresolved");self.assertEqual(report["load_entries"][0]["module_ids"],["module-0003"]);self.assertEqual(report["blocked_selected_modules"],["module-0004"])
    def test_unknown_dependency_blocks_consumer_and_all_selected_dependants(self):
        self.fixture(b"a.ko: absent.ko\nb.ko: a.ko\nindependent.ko:\n",b"b\nindependent\nnot_declared\n")
        report=self.report();self.assertEqual(report["selected_dependency_order"],["module-0003"]);self.assertEqual(report["blocked_selected_modules"],["module-0001","module-0002"]);self.assertFalse(report["selected_plan_complete_within_metadata"])
        self.assertEqual(self.codes(report),{"DEPENDENCY_NEEDS_METADATA_REVIEW","LOAD_SELECTION_NEEDS_METADATA_REVIEW"});self.assertEqual(report["dependencies"][0]["resolution"],"not_declared_in_selected_metadata")
    def test_closed_cycle_witness_excludes_merely_blocked_dependants(self):
        self.fixture(b"a.ko: b.ko\nb.ko: a.ko\nc.ko: a.ko\nfree.ko:\n",b"c\nfree\n")
        report=self.report();self.assertEqual(report["cycle_witnesses"],[["module-0001","module-0002","module-0001"]]);self.assertNotIn("module-0003",report["cycle_witnesses"][0]);self.assertEqual(report["blocked_selected_modules"],["module-0001","module-0002","module-0003"]);self.assertEqual(report["selected_dependency_order"],["module-0004"])
    def test_unselected_self_cycle_is_global_review_but_selected_closure_complete(self):
        self.fixture(b"a.ko: a.ko\nb.ko:\n",b"b\n")
        report=self.report();self.assertEqual(report["cycle_witnesses"],[["module-0001","module-0001"]]);self.assertEqual(report["selected_dependency_order"],["module-0002"]);self.assertTrue(report["selected_plan_complete_within_metadata"]);self.assertEqual(report["status"],"REVIEW_REQUIRED")
    def test_compressed_suffix_names_are_literal_without_dash_underscore_guessing(self):
        self.fixture(b"dir/a-b.ko.xz:\ndir/feature.ko.zst: dir/a-b.ko.xz\ndir/unused.ko.gz:\n",b"feature\na-b.ko.xz\n")
        report=self.report(details=True);self.assertEqual(report["selected_dependency_order"],["module-0001","module-0002"]);self.assertEqual(report["modules"][0]["declared_path"],"dir/a-b.ko.xz")
        self.fixture(b"a-b.ko:\n",b"a_b\n");self.new_output("no-conversion");self.assertEqual(self.codes(self.report()),{"LOAD_SELECTION_NEEDS_METADATA_REVIEW"})
    def test_duplicate_dependency_tokens_do_not_duplicate_edges_or_indegree(self):
        self.fixture(b"a.ko:\nb.ko: a.ko a.ko\n",b"b\nb.ko\n")
        report=self.report();self.assertEqual(self.codes(report),{"DUPLICATE_DEPENDENCY_TOKEN","DUPLICATE_LOAD_SELECTION"});self.assertEqual(report["modules"][1]["dependency_count"],2);self.assertEqual(len(report["dependencies"]),1);self.assertEqual(report["selected_dependency_order"],["module-0001","module-0002"]);self.assertTrue(report["selected_plan_complete_within_metadata"])
    def test_optional_inventory_is_exact_declared_membership_not_actual_files(self):
        self.fixture(b"dir/a.ko:\n",b"a\n",b"a.ko\na.ko\n")
        report=self.report();self.assertEqual(self.codes(report),{"DUPLICATE_INVENTORY_ENTRY","NOT_IN_SUPPLIED_INVENTORY"});self.assertTrue(report["declared_inventory_checked"]);self.assertTrue(report["selected_plan_complete_within_metadata"])
        self.fixture(b"dir/a.ko:\n",b"a\n",b"dir/a.ko\n");self.new_output("exact");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
    def test_unrelated_missing_metadata_does_not_enter_selected_closure(self):
        self.fixture(b"base.ko:\nfeature.ko: base.ko\nunrelated.ko: missing.ko\n",b"feature\n")
        report=self.report();self.assertEqual(report["selected_dependency_order"],["module-0001","module-0002"]);self.assertEqual(report["blocked_selected_modules"],[]);self.assertTrue(report["selected_plan_complete_within_metadata"]);self.assertEqual(report["status"],"REVIEW_REQUIRED")
    def test_unsupported_grammar_is_coverage_in_all_three_roles(self):
        dep_cases=(b"missing colon\n",b"a.ko: /absolute.ko\n",b"../a.ko:\n",b"a.ko: b.ko # inline\n",b"a.ko: $(shell command)\n",b"a.ko: b.ko: c.ko\n",b"a.ko: "+b"x"*513+b".ko\n")
        for i,raw in enumerate(dep_cases):
            self.fixture(raw,b"");self.new_output("deps"+str(i));report=self.report();self.assertTrue(report["coverage_issues"]);self.assertFalse(report["selected_plan_complete_within_metadata"]);self.assertEqual(report["modules"],[])
        for role in (1,2):
            for i,raw in enumerate((b"../a\n",b"a arg=1\n",b"/absolute/a\n",b"a\\b\n",b"a\xc2\xa0b\n")):
                values=[b"a.ko:\n",b"a\n",b"a.ko\n"];values[role]=raw;self.fixture(*values);self.new_output(str(role)+str(i));report=self.report();self.assertIn("UNSUPPORTED_LIST_ENTRY",self.codes(report));self.assertFalse(report["selected_plan_complete_within_metadata"])
    def test_full_line_comments_and_ascii_whitespace_are_not_shell_grammar(self):
        self.fixture(b"# comment\n\ta.ko \t: \t\n b.ko:\ta.ko\t\n",b"# comment\n\tb \t\n")
        report=self.report();self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertEqual([r["line"] for r in report["modules"]],[2,3]);self.assertEqual(report["load_entries"][0]["line"],2)
        self.fixture(b'a.ko: "b.ko"\n',b"a\n");self.new_output("no-quotes");self.assertIn("UNSUPPORTED_MODULE_PATH",self.codes(self.report()))
    def test_no_implicit_builtin_softdep_alias_or_installed_module_lookup(self):
        self.fixture(b"a.ko: builtin.ko\nsoftdep a pre: builtin.ko\n",b"pci:fictional\na\n",b"builtin.ko\n")
        report=self.report();self.assertEqual(report["selected_dependency_order"],[]);self.assertEqual(report["blocked_selected_modules"],["module-0001"]);self.assertFalse(report["selected_plan_complete_within_metadata"]);self.assertIn("DEPENDENCY_NEEDS_METADATA_REVIEW",self.codes(report));self.assertTrue(report["coverage_issues"])
    def test_declaration_ids_follow_input_lines_while_ready_order_is_lexical(self):
        self.fixture(b"z.ko:\na.ko:\nm.ko:\n",b"z\na\nm\n")
        report=self.report(details=True);self.assertEqual([r["declared_path"] for r in report["modules"]],["z.ko","a.ko","m.ko"]);self.assertEqual(report["selected_dependency_order"],["module-0002","module-0003","module-0001"])
    def test_default_privacy_and_details_do_not_change_graph_observations(self):
        self.fixture(b"fictional_private/core.ko:\nfictional_private/feature.ko: fictional_private/core.ko\n",b"feature\n")
        basic=self.report();self.new_output("details");detailed=self.report(details=True)
        self.assertNotIn("fictional_private",json.dumps(basic));self.assertIn("fictional_private",json.dumps(detailed))
        for key in ("selected_dependency_order","blocked_selected_modules","selected_plan_complete_within_metadata","cycle_witnesses","findings","coverage_issues","inputs","status"):self.assertEqual(basic[key],detailed[key])
        for key,detail_key in (("modules","declared_path"),("dependencies","declared_path"),("load_entries","declared_name")):self.assertEqual(basic[key],[{k:v for k,v in row.items() if k!=detail_key} for row in detailed[key]])
    def test_selected_file_audit_does_not_open_declared_module_payloads(self):
        payload=self.work/"payload.ko.gz";payload.write_bytes(b"FICTIONAL_PRIVATE_MODULE_BYTES_NOT_COMPRESSED")
        self.fixture(b"payload.ko.gz:\n",b"payload\n",b"payload.ko.gz\n");report=self.report(details=True,probe="audit");self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertEqual(payload.read_bytes(),b"FICTIONAL_PRIVATE_MODULE_BYTES_NOT_COMPRESSED")
        self.new_output("escaped");report=self.report(probe="scope_escape");self.assertIn("<script>",report["scope"]);markup=(self.output/"report.html").read_bytes();self.assertNotIn(b"<script>",markup);self.assertIn(b"&lt;script&gt;never_execute&lt;/script&gt;",markup)
    def test_raw_input_hashes_bom_crlf_empty_and_comment_only_scopes(self):
        deps=b"\xef\xbb\xbfa.ko:\r\n";load=b"# selected\na\r\n";available=b"a.ko\r\n";self.fixture(deps,load,available);report=self.report();self.assertEqual([r["sha256"] for r in report["inputs"]],list(map(sha,(deps,load,available))))
        self.fixture(b"",b"# empty selected scope\n");self.new_output("empty");report=self.report();self.assertEqual(report["modules"],[]);self.assertTrue(report["selected_plan_complete_within_metadata"]);self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertFalse(report["declared_inventory_checked"])
    def test_iterative_deep_graph_is_not_limited_by_python_recursion_depth(self):
        deps=b"".join(("m"+str(i).zfill(4)+".ko: "+("m"+str(i-1).zfill(4)+".ko" if i else "")+"\n").encode() for i in range(1500))
        self.fixture(deps,b"m1499\n");report=self.report();self.assertEqual(len(report["selected_dependency_order"]),1500);self.assertEqual(report["selected_dependency_order"],["module-"+str(i).zfill(4) for i in range(1,1501)]);self.assertEqual(report["cycle_witnesses"],[])
    def test_actual_node_edge_and_cycle_witness_budgets_fail_closed(self):
        nodes=b"".join(("n"+str(i).zfill(4)+".ko:\n").encode() for i in range(2000));self.fixture(nodes,b"n1999\n");self.assertEqual(len(self.report()["modules"]),2000)
        self.fixture(nodes+b"extra.ko:\n");self.new_output("nodes-over");self.report(error="MODULE_NODE_LIMIT");self.assertFalse(self.output.exists())
        exact=b"a.ko:\n"+b"".join(("b"+str(i)+".ko: ").encode()+b"a.ko "*800+b"\n" for i in range(5));self.fixture(exact,b"b4\n");self.new_output("edges-exact");report=self.report();self.assertEqual(sum(r["dependency_count"] for r in report["modules"]),4000);self.assertEqual(len(report["dependencies"]),5)
        self.fixture(exact.rstrip(b"\n")+b"a.ko\n");self.new_output("edges-over");self.report(error="MODULE_EDGE_LIMIT");self.assertFalse(self.output.exists())
        cycle=b"".join(("c"+str(i).zfill(3)+".ko: "+("c"+str(i+1).zfill(3)+".ko " if i<128 else "")+"c000.ko\n").encode() for i in range(129));self.fixture(cycle,b"c128\n");self.new_output("witness-over");self.report(error="CYCLE_WITNESS_LIMIT");self.assertFalse(self.output.exists())
    def test_encoding_controls_fail_all_selected_input_roles_without_reports(self):
        cases=((b"\xff","UTF8_REQUIRED"),(b"\0","TEXT_CONTROL_UNSUPPORTED"),(b"a\rb","TEXT_CONTROL_UNSUPPORTED"),(chr(0x2028).encode(),"TEXT_CONTROL_UNSUPPORTED"),(chr(0x202e).encode(),"TEXT_CONTROL_UNSUPPORTED"))
        for role in (0,1,2):
            for i,(raw,code) in enumerate(cases):
                values=[b"a.ko:\n",b"a\n",b"a.ko\n"];values[role]=raw;self.fixture(*values);self.new_output(str(role)+str(i));self.report(error=code);self.assertFalse(self.output.exists())
    def test_byte_physical_line_collection_and_finding_bounds_are_enforced(self):
        self.fixture(b"#"+b"x"*8191);self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        for i,raw in enumerate((b"#"+b"x"*8192,b"\n"*20000)):
            self.fixture(raw);self.new_output("lines-over"+str(i));self.report(error="TEXT_LINE_LIMIT")
        raw=(b"#"+b"x"*4094+b"\n")*256;self.fixture(raw);self.new_output("bytes-exact");self.assertEqual(self.report()["inputs"][0]["bytes"],1048576)
        self.fixture(b"a.ko:\n",b"a\n",raw+b" ");self.new_output("bytes-over");self.report(error="INPUT_BYTE_LIMIT")
        self.fixture(b"a.ko:\n",b"a\n"*4001);self.new_output("records-over");self.report(error="RECORD_LIMIT")
        self.fixture(b"unsupported\n"*4001);self.new_output("findings-over");self.report(error="FINDING_LIMIT")
    def test_cli_requires_roles_absolute_regular_inputs_and_fresh_output(self):
        for args in ([],["--deps",self.inputs[0]],["--deps",self.inputs[0],"--output",self.output],self.args()+["--private-unknown=secret"]):self.call(args,error="ARGUMENTS_INVALID")
        for role in ("--deps","--load-list","--available"):
            for path,code in (("relative.dep","LOCAL_ABSOLUTE_PATH_REQUIRED"),(self.work/".."/"fictional.dep","LOCAL_ABSOLUTE_PATH_REQUIRED"),("//fictional/share/file.dep","LOCAL_ABSOLUTE_PATH_REQUIRED"),(str(self.inputs[0])+"\nprivate","INVALID_LOCAL_PATH"),(self.copy,"REGULAR_FILE_REQUIRED"),(self.work/"missing.dep","IO_OR_INPUT_ERROR")):
                args=self.args();args[args.index(role)+1]=path;self.call(args,error=code)
        args=self.args();args[-1]=self.work/"missing"/"report";self.call(args,error="IO_OR_INPUT_ERROR")
        self.report();self.report(error="OUTPUT_EXISTS")
        for destination in (*self.inputs,self.work,self.copy):
            args=self.args();args[-1]=destination;self.call(args,error="OUTPUT_EXISTS")
    def test_changed_short_reads_partial_manifest_and_serialized_report_budget(self):
        self.report(probe="changed_input",error="INPUT_CHANGED",ignore=[self.inputs[0]]);self.assertFalse(self.output.exists())
        self.fixture(b"a.ko:\n",b"a\n",b"a.ko\n");self.report(probe="short_read",error="INPUT_CHANGED");self.assertFalse(self.output.exists())
        self.report(probe="manifest_failure",error="IO_OR_INPUT_ERROR");self.assertEqual({p.name for p in self.output.iterdir()},{"report.json","report.html"});self.report(error="OUTPUT_EXISTS")
        self.new_output("budget");self.report(probe='limit:{"MAX_REPORT":100}',error="REPORT_BYTE_LIMIT");self.assertFalse(self.output.exists())
    def test_same_file_hardlink_aliases_across_roles_and_hostile_environment(self):
        alias=self.work/"hardlink.dep";os.link(self.inputs[0],alias);self.assertTrue(self.inputs[0].samefile(alias))
        for role in ("--load-list","--available"):
            for path in (self.inputs[0],alias):
                args=self.args();args[args.index(role)+1]=path;self.call(args,error="DUPLICATE_INPUT_FILE")
        args=self.args();args[args.index("--available")+1]=self.inputs[1];self.call(args,error="DUPLICATE_INPUT_FILE")
        hostile=self.work/"hostile imports";hostile.mkdir()
        for name in ("sitecustomize.py","usercustomize.py","json.py","heapq.py"):(hostile/name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env=dict(self.env,PYTHONPATH=str(hostile),PYTHONHOME=str(hostile),PYTHONSTARTUP=str(hostile/"sitecustomize.py"));self.report(env=env)
    def test_native_symlink_inputs_and_output_parents(self):
        alias=self.work/"linked.dep";self.symlink(alias,self.inputs[0])
        for flag in ("--deps","--load-list","--available"):
            args=self.args();args[args.index(flag)+1]=alias;self.call(args,error="LINKED_PATH_REJECTED")
        route=self.work/"linked directory";self.symlink(route,self.work,directory=True)
        args=self.args();args[1]=route/self.inputs[0].name;self.call(args,error="LINKED_PATH_REJECTED")
        args=self.args();args[-1]=route/"new-report";self.call(args,error="LINKED_PATH_REJECTED")
        dangling=self.work/"dangling report";self.symlink(dangling,self.work/"nonexistent");args=self.args();args[-1]=dangling;self.call(args,error="OUTPUT_EXISTS")
    @unittest.skipUnless(os.name=="nt",PROCESS_WINDOWS_REASON)
    def test_native_windows_junction_and_stream_routes(self):
        junction=self.work/"junction";done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(junction),str(self.work)],capture_output=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:junction.rmdir() if junction.exists() else None)
        for flag,path in (("--deps",self.inputs[0]),("--load-list",self.inputs[1]),("--available",self.inputs[2]),("--output",self.output)):
            args=self.args();args[args.index(flag)+1]=junction/path.name;self.call(args,error="LINKED_PATH_REJECTED")
            args=self.args();args[args.index(flag)+1]=str(path)+":stream";self.call(args,error="DEVICE_OR_STREAM_PATH_REJECTED")
    @unittest.skipUnless(os.name!="nt",PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_bounds(self):
        fifo=self.work/"fictional.fifo";os.mkfifo(fifo)
        connection=socket.socket(socket.AF_UNIX);connection.bind(str(self.work/"fictional.sock"));self.addCleanup(connection.close)
        for path in (fifo,self.work/"fictional.sock"):
            for flag in ("--deps","--load-list","--available"):
                args=self.args();args[args.index(flag)+1]=path;self.call(args,error="REGULAR_FILE_REQUIRED")
        sparse=self.work/"fictional sparse.dep"
        with sparse.open("wb") as stream:stream.truncate(1<<34)
        self.assertEqual(sparse.stat().st_size,1<<34);self.assertLess(sparse.stat().st_blocks*512,1<<20)
        args=self.args();args[1]=sparse;self.call(args,error="INPUT_BYTE_LIMIT");self.assertFalse(self.output.exists())
    def test_duplicate_path_load_priority_does_not_promote_duplicate_metadata(self):
        self.fixture(b"a.ko:\na.ko:\ndir/a.ko:\n",b"a.ko\na\ndir/a.ko\n")
        report=self.report();self.assertEqual([r["resolution"] for r in report["load_entries"]],["ambiguous_or_unresolved","ambiguous_or_unresolved","unique_selected_declaration"]);self.assertEqual(report["selected_dependency_order"],["module-0003"]);self.assertFalse(report["selected_plan_complete_within_metadata"])


if __name__ == '__main__':
    unittest.main()
