"""Independent copied-runtime consumers of fictional copy-map text; no Make or payload execution. MIT."""
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
RUNTIME = ("copy_map_inspector.py", "text_support.py", "examples/generate.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junction_and_stream_routes"
PROCESS_WINDOWS_REASON = "Native Windows junction and stream fixtures"
PROCESS_POSIX_ID = "test_download.Download.test_native_posix_special_files_and_sparse_bounds"
PROCESS_POSIX_REASON = "Native POSIX FIFO, socket and sparse fixtures"
PROCESS_SYMLINK_ID = "test_download.Download.test_native_symlink_inputs_roots_and_output_parents"
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
import copy_map_inspector as e
import text_support as s
assert Path(e.__file__).resolve()==base/'copy_map_inspector.py'
assert Path(s.__file__).resolve()==base/'text_support.py'
assert e.source_inputs is s.source_inputs and e.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py'
 assert g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
selected=[Path(args[i+1]) for i,value in enumerate(args[:-1]) if value=='--file']
if '--roots' in args:selected.append(Path(args[args.index('--roots')+1]))
output=Path(args[args.index('--output')+1])
if kind=='audit':
 e.Parser(description=e.__doc__);b'\xef\xbb\xbfprewarm'.decode('utf-8-sig')
 allowed={base/name for name in ('copy_map_inspector.py','text_support.py','examples/generate.py')}
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
        self.temp = tempfile.TemporaryDirectory(prefix="copy-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.copy = self.work / "copied runtime"; self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT/name).read_bytes(); target = self.copy/name
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw); self.pins[name] = sha(raw)
        self.inputs = []; self.roots = None; self.output = self.work/"new report"
        self.env = {k:v for k,v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
        self.fixture(b"PRODUCT_COPY_FILES += fictional/a:vendor/a\n")
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
            path = self.work/("fictional map "+str(number)+".mk"); path.write_bytes(raw); self.inputs.append(path)
    def new_output(self, suffix):
        self.output = self.work/("new report "+str(suffix))
    def args(self):
        return [item for path in self.inputs for item in ("--file",path)] + (["--roots",self.roots] if self.roots is not None else []) + ["--output",self.output]
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot(); prefix = ["-c",PROBE,self.copy,probe] if probe else [self.copy/"copy_map_inspector.py"]
        done = self.run_child([*prefix,*args], env=env)
        self.assertEqual(done.stderr,b"",done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout,json.dumps(value,sort_keys=probe!="affinity").encode()+NEWLINE)
        if error is not None: self.assertEqual(value,dict(status="INCOMPLETE",error=error)); code = 2
        elif probe == "affinity": self.assertEqual(value,dict(status="COPIED_RUNTIME_AFFINITY",dependencies=0)); code = 0
        else:
            report = self.check_report(output,args)
            self.assertEqual(value,dict(status=report["status"],entries=len(report["entries"]),conflicts=len(report["conflicts"]),coverage_issues=len(report["coverage_issues"])))
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
        has_roots = "--roots" in args
        self.assertEqual(set(report),{"schema_version","tool","scope","details_included","root_count","inputs","entries","conflicts","findings","coverage_issues","status"}|({"roots_input"} if has_roots else set()))
        self.assertEqual((report["schema_version"],report["tool"]),(1,"Android Build Copy-Map Inspector"))
        self.assertEqual(report["status"],"REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        details = "--include-details" in args; self.assertIs(report["details_included"],details)
        selected = [Path(args[i+1]) for i,item in enumerate(args[:-1]) if item=="--file"]
        sources = [dict(id="input-"+str(i).zfill(4),bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for i,path in enumerate(selected,1)]
        self.assertEqual(report["inputs"],sources)
        if has_roots:
            root_bytes=Path(args[args.index("--roots")+1]).read_bytes()
            self.assertEqual(report["roots_input"],dict(id="roots-input",bytes=len(root_bytes),sha256=sha(root_bytes)))
            self.assertEqual(report["root_count"],len(json.loads(root_bytes)["roots"]))
        else: self.assertEqual(report["root_count"],0)
        ids = []
        for index,row in enumerate(report["entries"],1):
            self.assertEqual(set(row),{"id","source","line","resolution","owner_present"}|({"declared_source","declared_destination","declared_owner","resolved_source","resolved_destination"} if details else set()))
            self.assertEqual(row["id"],"entry-"+str(index).zfill(4)); ids.append(row["id"])
            self.assertIn(row["source"],[r["id"] for r in sources]); self.assertGreaterEqual(row["line"],1)
            self.assertIn(row["resolution"],{"literal_or_explicit_root","unresolved"}); self.assertIs(type(row["owner_present"]),bool)
            if details:
                self.assertEqual(row["owner_present"],row["declared_owner"] is not None)
                self.assertEqual(row["resolution"]=="literal_or_explicit_root",row["resolved_source"] is not None and row["resolved_destination"] is not None)
        for row in report["conflicts"]:
            self.assertEqual(set(row),{"code","entries"}); self.assertEqual(len(row["entries"]),2)
            self.assertLess(ids.index(row["entries"][0]),ids.index(row["entries"][1]))
            self.assertIn(row["code"],{"DUPLICATE_DECLARED_COPY","DECLARED_DESTINATION_CONFLICT","PORTABILITY_DESTINATION_COLLISION","FILE_PARENT_DESTINATION_CONFLICT"})
            self.assertTrue(all(report["entries"][ids.index(key)]["resolution"]=="literal_or_explicit_root" for key in row["entries"]))
        for row in report["findings"]+report["coverage_issues"]:
            self.assertEqual(set(row),{"code","source","line"});self.assertIn(row["source"],[r["id"] for r in sources]);self.assertGreaterEqual(row["line"],1)
        self.assertNotIn(str(self.work),raw.decode())
        markup = (output/"report.html").read_bytes(); parsed = StaticHTML(); parsed.feed(markup.decode()); parsed.close()
        self.assertEqual(parsed.tags.count("html"),1); self.assertEqual(parsed.csp,["default-src 'none'; style-src 'unsafe-inline'"])
        self.assertIn(html.escape(raw.decode(),quote=True).encode(),markup)
        members = {name:(output/name).read_bytes() for name in ("report.json","report.html")}
        manifest = dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=sha(data)) for name,data in sorted(members.items())])
        self.assertEqual((output/"MANIFEST.json").read_bytes(),encoded(manifest)); return report
    def root_fixture(self, value=None, raw=None):
        self.roots=self.work/"explicit roots.json"
        self.roots.write_bytes(encoded(dict(schema_version=1,roots={} if value is None else value)) if raw is None else raw)
    def report(self, details=False, **kwargs):
        return self.call(self.args()+(["--include-details"] if details else []),output=self.output,allow=[self.output],**kwargs)
    def codes(self, report):
        return {row["code"] for row in report["findings"]+report["coverage_issues"]}
    def symlink(self, path, target, directory=False):
        try: path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            if os.name=="nt" and getattr(error,"winerror",None)==1314 and os.environ.get("OUTLANDS_COPY_MAP_REQUIRE_LINKS")!="1": self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_copied_runtime_affinity_and_help(self):
        self.call([],probe="affinity")
        for script in (self.copy/"copy_map_inspector.py",self.copy/"examples/generate.py"):
            before=self.snapshot();done=self.run_child([script,"--help"])
            self.assertEqual((done.returncode,done.stderr),(0,b""));self.assertIn(b"--output",done.stdout);self.assertEqual(self.snapshot(),before)
    def test_generator_cli_four_fictional_files_and_new_only_destination(self):
        target=self.work/"generated";before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(0,b"",json.dumps(dict(status="FICTIONAL_EXAMPLES_CREATED",files=4),sort_keys=True).encode()+NEWLINE))
        self.assertEqual({p.name for p in target.iterdir()},{"clean.mk","review.mk","roots.mk","roots.json"});self.assertEqual({k:self.snapshot().get(k) for k in before},before)
        for name,status in (("clean","NO_SCOPE_FINDINGS"),("review","REVIEW_REQUIRED")):
            self.inputs=[target/(name+".mk")];self.new_output(name);self.assertEqual(self.report()["status"],status)
        self.inputs=[target/"roots.mk"];self.roots=target/"roots.json";self.new_output("roots");report=self.report(details=True)
        self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertEqual(report["entries"][0]["resolved_destination"],"vendor/etc/demo.conf")
        before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(2,b"",json.dumps(dict(status="INCOMPLETE",error="OUTPUT_EXISTS"),sort_keys=True).encode()+NEWLINE));self.assertEqual(self.snapshot(),before)
    def test_literal_entries_optional_owner_and_line_ids_are_exact(self):
        self.fixture(b"# fictional\n PRODUCT_COPY_FILES\t+=\tfictional/a:vendor/a fictional/b:vendor/b:owner-1\n")
        report=self.report(details=True);self.assertEqual(report["status"],"NO_SCOPE_FINDINGS")
        self.assertEqual(report["entries"],[dict(id="entry-0001",source="input-0001",line=2,resolution="literal_or_explicit_root",owner_present=False,declared_source="fictional/a",declared_destination="vendor/a",declared_owner=None,resolved_source="fictional/a",resolved_destination="vendor/a"),dict(id="entry-0002",source="input-0001",line=2,resolution="literal_or_explicit_root",owner_present=True,declared_source="fictional/b",declared_destination="vendor/b",declared_owner="owner-1",resolved_source="fictional/b",resolved_destination="vendor/b")])
        self.assertEqual(report["conflicts"],[])
    def test_duplicate_copies_are_retained_with_ordered_pairs(self):
        self.fixture(b"PRODUCT_COPY_FILES += a:vendor/a:owner a:vendor/a:owner a:vendor/a:owner\n")
        report=self.report();self.assertEqual(len(report["entries"]),3)
        self.assertEqual(report["conflicts"],[dict(code="DUPLICATE_DECLARED_COPY",entries=pair) for pair in (["entry-0001","entry-0002"],["entry-0001","entry-0003"],["entry-0002","entry-0003"])])
        self.assertEqual(report["findings"],[dict(code="DUPLICATE_DECLARED_COPY",source="input-0001",line=1)])
    def test_source_and_owner_differences_are_destination_conflicts(self):
        cases=("a:vendor/a b:vendor/a","a:vendor/a:one a:vendor/a:two","a:vendor/a a:vendor/a:one")
        for index,words in enumerate(cases):
            self.fixture(("PRODUCT_COPY_FILES += "+words+"\n").encode());self.new_output(index);report=self.report(details=True)
            self.assertEqual(report["conflicts"],[dict(code="DECLARED_DESTINATION_CONFLICT",entries=["entry-0001","entry-0002"])])
            self.assertEqual(self.codes(report),{"DECLARED_DESTINATION_CONFLICT"})
    def test_nfc_and_casefold_collisions_are_portability_observations(self):
        destinations=(("vendor/Alpha","Vendor/alpha"),("vendor/caf"+chr(233),"vendor/cafe"+chr(769)),("vendor/stra"+chr(223)+"e","vendor/STRASSE"))
        for index,(first,second) in enumerate(destinations):
            self.fixture(("PRODUCT_COPY_FILES += a:"+first+" b:"+second+"\n").encode());self.new_output(index);report=self.report(details=True)
            self.assertEqual([r["declared_destination"] for r in report["entries"]],[first,second]);self.assertEqual(report["conflicts"],[dict(code="PORTABILITY_DESTINATION_COLLISION",entries=["entry-0001","entry-0002"])])
    def test_file_parent_conflicts_require_a_slash_boundary(self):
        self.fixture(b"PRODUCT_COPY_FILES += a:Vendor/Etc b:vendor/etc/child c:vendor/etc2 d:vendor/etc-suffix\n")
        report=self.report();self.assertEqual(report["conflicts"],[dict(code="FILE_PARENT_DESTINATION_CONFLICT",entries=["entry-0001","entry-0002"])])
        self.fixture(b"PRODUCT_COPY_FILES += a:vendor/etc/child b:VENDOR/ETC\n");self.new_output("reverse");self.assertEqual(self.report()["conflicts"][0]["code"],"FILE_PARENT_DESTINATION_CONFLICT")
    def test_unresolved_entries_are_retained_but_excluded_from_pairs(self):
        self.fixture(b"PRODUCT_COPY_FILES += $(UNKNOWN)/a:vendor/same ../bad:vendor/same literal:vendor/same literal:$(UNKNOWN)/same\n")
        report=self.report(details=True);self.assertEqual([r["resolution"] for r in report["entries"]],["unresolved","unresolved","literal_or_explicit_root","unresolved"])
        self.assertEqual(report["conflicts"],[]);self.assertEqual(report["findings"],[])
        self.assertEqual(self.codes(report),{"UNRESOLVED_ROOT_VARIABLE","UNSAFE_OR_UNSUPPORTED_RELATIVE_PATH"})
        self.assertEqual([r["resolved_destination"] for r in report["entries"]],["vendor/same","vendor/same","vendor/same",None])
    def test_only_explicit_whole_leading_roots_are_substituted(self):
        self.fixture(b"PRODUCT_COPY_FILES += $(SOURCE)/a:$(DEST)/etc/a $(SOURCE):$(DEST)\n");self.root_fixture(dict(SOURCE="fictional/base",DEST="vendor"))
        report=self.report(details=True,probe="audit");self.assertEqual(report["root_count"],2)
        self.assertEqual([(r["resolved_source"],r["resolved_destination"]) for r in report["entries"]],[("fictional/base/a","vendor/etc/a"),("fictional/base","vendor")])
        self.assertEqual(report["conflicts"],[dict(code="FILE_PARENT_DESTINATION_CONFLICT",entries=["entry-0001","entry-0002"])])
        self.assertEqual(report["roots_input"]["sha256"],sha(self.roots.read_bytes()))
    def test_environment_defaults_functions_and_nested_expressions_are_not_used(self):
        self.fixture(b"PRODUCT_COPY_FILES += $(LOCAL_PATH)/a:$(TARGET_COPY_OUT_VENDOR)/a\n")
        env=dict(self.env,LOCAL_PATH="fictional",TARGET_COPY_OUT_VENDOR="vendor")
        report=self.report(details=True,env=env);self.assertEqual(report["root_count"],0);self.assertEqual(report["entries"][0]["resolution"],"unresolved")
        self.assertEqual(self.codes(report),{"UNRESOLVED_ROOT_VARIABLE"})
        cases=("$(shell echo fictional:vendor/fake)","$(nested$(NAME))/a:vendor/a","${NAME}/a:vendor/a","$(lower)/a:vendor/a","a:$(call COPY,x)")
        for index,words in enumerate(cases):
            self.fixture(("PRODUCT_COPY_FILES += "+words+"\n").encode());self.new_output(index);report=self.report(probe="audit")
            self.assertEqual(report["entries"],[]);self.assertEqual(self.codes(report),{"MAKE_EXPRESSION_NOT_EVALUATED"})
        self.fixture(b"PRODUCT_COPY_FILES += path/$(NAME):vendor/a $(NAME)/$(NAME):vendor/b\n");self.root_fixture(dict(NAME="fictional"));self.new_output("embedded")
        report=self.report(details=True);self.assertEqual([r["resolution"] for r in report["entries"]],["unresolved","unresolved"]);self.assertEqual(self.codes(report),{"MAKE_EXPRESSION_NOT_EVALUATED"})
    def test_roots_schema_exact_types_fields_and_sixteen_map_limit(self):
        valid={"ROOT"+str(i):"fictional/r"+str(i) for i in range(16)};self.root_fixture(valid);self.assertEqual(self.report()["root_count"],16)
        cases=(None,[],{},dict(schema_version=True,roots={}),dict(schema_version=2,roots={}),dict(schema_version=1,roots=[]),dict(schema_version=1,roots={},extra=0),dict(schema_version=1,roots=dict(valid,OVER="extra")))
        for index,value in enumerate(cases):
            self.root_fixture(raw=encoded(value));self.new_output(index);self.report(error="INVALID_ROOTS_SCHEMA");self.assertFalse(self.output.exists())
    def test_root_names_and_values_are_literal_portable_relative_strings(self):
        cases=({"lower":"fictional"},{"A"*65:"fictional"},{"_ROOT":"fictional"},{"ROOT":1},{"ROOT":None},{"ROOT":""},{"ROOT":"../bad"},{"ROOT":"/absolute"},{"ROOT":"a/NUL.txt"},{"ROOT":"a//b"},{"ROOT":"$(OTHER)"},{"ROOT":"a\\b"},{"ROOT":"a/trailing."})
        for index,value in enumerate(cases):
            self.root_fixture(value);self.new_output(index);self.report(error="INVALID_ROOT_VALUE");self.assertFalse(self.output.exists())
        self.root_fixture({"A"*64:"fictional"});self.new_output("name-exact");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
    def test_roots_strict_json_duplicate_number_control_and_resource_errors(self):
        cases=((b"{","INVALID_JSON"),(b"\xff","INVALID_JSON"),(b'\xef\xbb\xbf{"schema_version":1,"roots":{}}',"INVALID_JSON"),(b'{"schema_version":1,"roots":{},"roots":{}}',"DUPLICATE_JSON_KEY"),(b'{"schema_version":1.0,"roots":{}}',"JSON_NUMBER_UNSUPPORTED"),(b'{"schema_version":NaN,"roots":{}}',"JSON_NUMBER_UNSUPPORTED"),(b'{"schema_version":1,"roots":{"ROOT":"a\\u0000b"}}',"JSON_TEXT_UNSUPPORTED"),(b"["*10+b"0"+b"]"*10,"JSON_STRUCTURE_LIMIT"),(json.dumps([0]*1000).encode(),"JSON_STRUCTURE_LIMIT"),(json.dumps({"x":"a"*1025}).encode(),"JSON_TEXT_UNSUPPORTED"))
        for index,(raw,code) in enumerate(cases):
            self.root_fixture(raw=raw);self.new_output(index);self.report(error=code);self.assertFalse(self.output.exists())
    def test_only_append_assignments_and_comments_are_supported(self):
        self.fixture(b"# generated\nPRODUCT_COPY_FILES += # empty\nPRODUCT_COPY_FILES += a:vendor/a # comment\nPRODUCT_COPY_FILES := b:vendor/a\nPRODUCT_COPY_FILES = c:vendor/a\nPRODUCT_COPY_FILES ?= d:vendor/a\nPRODUCT_COPY_FILES += e:vendor/a\n")
        report=self.report(details=True);self.assertEqual([r["declared_source"] for r in report["entries"]],["a","e"])
        self.assertEqual([r["line"] for r in report["coverage_issues"]],[4,5,6]);self.assertEqual(self.codes(report),{"UNINSPECTED_MAKE_STATEMENT","DECLARED_DESTINATION_CONFLICT"})
        self.fixture(b"# comment only\nPRODUCT_COPY_FILES += # empty\n");self.new_output("empty");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
    def test_bounded_continuations_retain_first_line_and_entry_order(self):
        raw=b"# heading\nPRODUCT_COPY_FILES += \\\n  fictional/a:vendor/a \\\n\tfictional/b:vendor/b:owner # tail\n"
        self.fixture(raw);report=self.report(details=True)
        self.assertEqual([r["line"] for r in report["entries"]],[2,2]);self.assertEqual([r["declared_source"] for r in report["entries"]],["fictional/a","fictional/b"]);self.assertEqual(report["status"],"NO_SCOPE_FINDINGS")
        self.fixture(b"\\\nPRODUCT_COPY_FILES += a:b\n");self.new_output("empty-fold");self.assertEqual(self.report()["entries"][0]["line"],1)
    def test_dangling_interrupted_and_escaped_comment_continuations_are_held(self):
        cases=((b"PRODUCT_COPY_FILES += "+bytes([92]),"DANGLING_CONTINUATION"),(b"PRODUCT_COPY_FILES += \\\n# interrupted\n","INTERRUPTED_CONTINUATION"),(b"PRODUCT_COPY_FILES += \\\n \t\n","INTERRUPTED_CONTINUATION"),(b"PRODUCT_COPY_FILES += a:vendor/a\\#literal\n","QUOTING_OR_ESCAPING_UNSUPPORTED"))
        for index,(raw,code) in enumerate(cases):
            self.fixture(raw);self.new_output(index);report=self.report();self.assertEqual(report["entries"],[]);self.assertEqual(self.codes(report),{code})
        self.fixture(b"PRODUCT_COPY_FILES += \\\n# stop\na:vendor/a\nPRODUCT_COPY_FILES += b:vendor/b\n");self.new_output("recovery");report=self.report(details=True)
        self.assertEqual([r["declared_source"] for r in report["entries"]],["b"]);self.assertEqual([r["line"] for r in report["coverage_issues"]],[1,3])
    def test_quotes_backslash_escaping_and_conditional_statements_are_not_make(self):
        for index,word in enumerate(('"a:vendor/a"',"'a:vendor/a'",r"a\ b:vendor/a")):
            self.fixture(("PRODUCT_COPY_FILES += "+word+"\n").encode());self.new_output(index);report=self.report();self.assertEqual(report["entries"],[]);self.assertEqual(self.codes(report),{"QUOTING_OR_ESCAPING_UNSUPPORTED"})
        self.fixture(b"ifeq ($(MODE),yes)\nPRODUCT_COPY_FILES += a:vendor/a\nelse\nPRODUCT_COPY_FILES += b:vendor/a\nendif\n")
        self.new_output("branches");report=self.report();self.assertEqual(len(report["entries"]),2);self.assertEqual(report["conflicts"][0]["code"],"DECLARED_DESTINATION_CONFLICT");self.assertEqual(len(report["coverage_issues"]),3)
    def test_copy_word_field_and_owner_grammar_never_guesses(self):
        bad=("no-colon","a:b:owner:extra","a:b:","a:b:bad!owner","a:b:"+"x"*129)
        self.fixture(("PRODUCT_COPY_FILES += "+" ".join(bad)+" valid:vendor/ok:owner\n").encode());report=self.report(details=True)
        self.assertEqual([r["declared_source"] for r in report["entries"]],["valid"]);self.assertEqual(self.codes(report),{"INVALID_COPY_WORD"});self.assertEqual(len(report["coverage_issues"]),1)
        self.fixture(("PRODUCT_COPY_FILES += a:b:"+"x"*128+"\n").encode());self.new_output("owner-exact");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
    def test_portable_path_restrictions_apply_to_sources_and_destinations(self):
        bad=("../bad","/absolute","a//b","a/./b","a/NUL.txt","a/COM1","a/trailing.","a/*","a/?","a/|pipe")
        for index,value in enumerate(bad):
            self.fixture(("PRODUCT_COPY_FILES += "+value+":vendor/a literal:"+value+"\n").encode());self.new_output(index);report=self.report(details=True)
            self.assertEqual([r["resolution"] for r in report["entries"]],["unresolved","unresolved"]);self.assertEqual(self.codes(report),{"UNSAFE_OR_UNSUPPORTED_RELATIVE_PATH"});self.assertEqual(report["conflicts"],[])
        value="a"*1024;self.fixture(("PRODUCT_COPY_FILES += "+value+":vendor/a\n").encode());self.new_output("path-exact");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        self.fixture(("PRODUCT_COPY_FILES += "+value+"a:vendor/a\n").encode());self.new_output("path-over");self.assertEqual(self.report()["entries"][0]["resolution"],"unresolved")
    def test_selected_file_order_hashes_and_continuations_never_cross_files(self):
        first=b"PRODUCT_COPY_FILES += a:vendor/a\n";second=b"PRODUCT_COPY_FILES += b:vendor/b\n"
        self.fixture(first,second);report=self.report(details=True);self.assertEqual([r["sha256"] for r in report["inputs"]],[sha(first),sha(second)])
        self.inputs.reverse();self.new_output("reversed");report=self.report(details=True);self.assertEqual([r["declared_source"] for r in report["entries"]],["b","a"])
        self.fixture(b"PRODUCT_COPY_FILES += "+bytes([92]),b" a:vendor/a\nPRODUCT_COPY_FILES += b:vendor/b\n");self.new_output("sections");report=self.report(details=True)
        self.assertEqual([r["declared_source"] for r in report["entries"]],["b"]);self.assertEqual([(r["source"],r["line"],r["code"]) for r in report["coverage_issues"]],[("input-0001",1,"DANGLING_CONTINUATION"),("input-0002",1,"UNINSPECTED_MAKE_STATEMENT")])
    def test_existing_payloads_includes_privacy_and_static_html_audit(self):
        payload=self.work/"payload.bin";payload.write_bytes(b"FICTIONAL_PRIVATE_PAYLOAD")
        destination=self.work/"destination.bin";destination.write_bytes(b"FICTIONAL_PRIVATE_DESTINATION")
        included=self.work/"included.mk";included.write_bytes(b"PRODUCT_COPY_FILES += hidden:vendor/hidden\n")
        self.fixture(("PRODUCT_COPY_FILES += "+payload.name+":"+destination.name+":fictional_owner\ninclude "+included.name+"\n").encode());self.root_fixture(dict(ROOT="fictional"))
        basic=self.report(probe="audit");self.new_output("details");detailed=self.report(details=True,probe="audit")
        self.assertEqual(len(detailed["entries"]),1);self.assertEqual(detailed["entries"][0]["resolved_source"],payload.name)
        for text in (payload.name,destination.name,"fictional_owner"):
            self.assertNotIn(text,json.dumps(basic));self.assertIn(text,json.dumps(detailed))
        for member in self.output.iterdir():self.assertNotIn(b"FICTIONAL_PRIVATE",member.read_bytes())
        self.fixture(b"PRODUCT_COPY_FILES += a/<script>never_execute</script>:vendor/out\n");self.roots=None;self.new_output("html");report=self.report(details=True)
        self.assertEqual(report["entries"][0]["resolution"],"unresolved");self.assertNotIn(b"<script>",(self.output/"report.html").read_bytes());self.assertIn(b"&lt;script&gt;never_execute&lt;/script&gt;",(self.output/"report.html").read_bytes())
    def test_encoding_bom_crlf_nonbreaking_space_and_controls(self):
        name="caf"+chr(160)+"e";raw=("PRODUCT_COPY_FILES += fictional/"+name+":vendor/"+name+"\n").encode()
        self.fixture(b"\xef\xbb\xbf"+raw.replace(b"\n",b"\r\n"));report=self.report(details=True);self.assertEqual(report["entries"][0]["resolved_destination"],"vendor/"+name);self.assertEqual(report["status"],"NO_SCOPE_FINDINGS")
        for index,(raw,code) in enumerate(((b"\xff","UTF8_REQUIRED"),(b"\0","TEXT_CONTROL_UNSUPPORTED"),(b"a\rb","TEXT_CONTROL_UNSUPPORTED"),(chr(0x2028).encode(),"TEXT_CONTROL_UNSUPPORTED"),(chr(0x202e).encode(),"TEXT_CONTROL_UNSUPPORTED"))):
            self.fixture(raw);self.new_output(index);self.report(error=code);self.assertFalse(self.output.exists())
    def test_file_line_logical_line_roots_and_separate_role_limits(self):
        self.fixture(b"#"+b"x"*8191);self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        self.fixture(b"#"+b"x"*8192);self.new_output("physical-over");self.report(error="TEXT_LINE_LIMIT")
        self.fixture(b"PRODUCT_COPY_FILES += \\\n"+b"x"*8192);self.new_output("logical-over");self.report(error="LOGICAL_LINE_LIMIT")
        self.fixture(b"\n"*20000);self.new_output("lines-over");self.report(error="TEXT_LINE_LIMIT")
        raw=(b"#"+b"x"*4094+b"\n")*256;self.fixture(raw);self.new_output("bytes-exact");self.assertEqual(self.report()["inputs"][0]["bytes"],1048576)
        self.fixture(raw+b" ");self.new_output("bytes-over");self.report(error="INPUT_BYTE_LIMIT")
        self.fixture(*(b"" for _ in range(33)));self.new_output("count-over");self.report(error="INPUT_COUNT_LIMIT")
        self.inputs.pop();self.root_fixture({});self.new_output("separate-root");report=self.report();self.assertEqual(len(report["inputs"]),32);self.assertIn("roots_input",report)
        root_raw=self.roots.read_bytes();self.roots.write_bytes(root_raw+b" "*(65536-len(root_raw)));self.new_output("roots-exact");self.report()
        with self.roots.open("ab") as stream:stream.write(b" ")
        self.new_output("roots-over");self.report(error="INPUT_BYTE_LIMIT")
        self.roots=None;self.fixture(*(raw for _ in range(5)));self.new_output("total-over");self.report(error="TOTAL_BYTE_LIMIT")
    def test_entry_conflict_and_coverage_caps_fail_without_truncation(self):
        raw=b"PRODUCT_COPY_FILES += $(UNKNOWN)/a:vendor/a\n";self.fixture(raw*4000);report=self.report();self.assertEqual(len(report["entries"]),4000);self.assertEqual(report["conflicts"],[])
        self.fixture(raw*4001);self.new_output("entry-over");self.report(error="RECORD_LIMIT")
        self.fixture(b"outside\n"*4001);self.new_output("coverage-over");self.report(error="FINDING_LIMIT")
        self.fixture(b"PRODUCT_COPY_FILES += "+b"a:vendor/a "*90+b"\n");self.new_output("dense");self.report(error="RECORD_LIMIT");self.assertFalse(self.output.exists())
    def test_cli_arguments_paths_missing_parents_and_no_overwrite(self):
        for args in ([],["--file",self.inputs[0]],["--private-unknown=secret"],["--output",self.output]):self.call(args,error="ARGUMENTS_INVALID")
        for path,code in (("relative.mk","LOCAL_ABSOLUTE_PATH_REQUIRED"),(self.work/".."/"fictional.mk","LOCAL_ABSOLUTE_PATH_REQUIRED"),("//fictional/share/file.mk","LOCAL_ABSOLUTE_PATH_REQUIRED"),(str(self.inputs[0])+"\nprivate","INVALID_LOCAL_PATH"),(self.copy,"REGULAR_FILE_REQUIRED"),(self.work/"missing.mk","IO_OR_INPUT_ERROR")):
            self.call(["--file",path,"--output",self.output],error=code)
        self.call(["--file",self.inputs[0],"--roots","relative.json","--output",self.output],error="LOCAL_ABSOLUTE_PATH_REQUIRED")
        self.call(["--file",self.inputs[0],"--output",self.work/"missing"/"report"],error="IO_OR_INPUT_ERROR")
        self.root_fixture({});self.report();self.report(error="OUTPUT_EXISTS")
        for destination in (self.inputs[0],self.roots,self.work,self.copy):
            args=self.args();args[-1]=destination;self.call(args,error="OUTPUT_EXISTS")
    def test_changed_short_reads_partial_manifest_and_report_limits(self):
        self.report(probe="changed_input",error="INPUT_CHANGED",ignore=self.inputs);self.assertFalse(self.output.exists())
        self.fixture(b"PRODUCT_COPY_FILES += a:vendor/a\n");self.report(probe="short_read",error="INPUT_CHANGED");self.assertFalse(self.output.exists())
        self.report(probe="manifest_failure",error="IO_OR_INPUT_ERROR");self.assertEqual({p.name for p in self.output.iterdir()},{"report.json","report.html"});self.report(error="OUTPUT_EXISTS")
        self.new_output("budget");self.report(probe='limit:{"MAX_REPORT":100}',error="REPORT_BYTE_LIMIT");self.assertFalse(self.output.exists())
    def test_native_file_aliases_cross_role_limits_and_hostile_environment(self):
        path=self.inputs[0];alias=self.work/"hardlink.mk";os.link(path,alias);self.assertTrue(path.samefile(alias))
        for second in (path,alias):self.call(["--file",path,"--file",second,"--output",self.output],error="DUPLICATE_INPUT_FILE")
        value=encoded(dict(schema_version=1,roots={}));path.write_bytes(value);self.roots=alias;report=self.report()
        self.assertEqual(report["inputs"][0]["sha256"],report["roots_input"]["sha256"]);self.assertEqual(self.codes(report),{"UNINSPECTED_MAKE_STATEMENT"})
        self.roots=None;self.fixture(b"PRODUCT_COPY_FILES += a:vendor/a\n");self.new_output("hostile");hostile=self.work/"hostile imports";hostile.mkdir()
        for name in ("sitecustomize.py","usercustomize.py","json.py","re.py"):(hostile/name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env=dict(self.env,PYTHONPATH=str(hostile),PYTHONHOME=str(hostile),PYTHONSTARTUP=str(hostile/"sitecustomize.py"));self.report(env=env)
    def test_native_symlink_inputs_roots_and_output_parents(self):
        alias=self.work/"linked.mk";self.symlink(alias,self.inputs[0]);self.call(["--file",alias,"--output",self.output],error="LINKED_PATH_REJECTED")
        self.root_fixture({});root_alias=self.work/"linked-roots.json";self.symlink(root_alias,self.roots);self.call(["--file",self.inputs[0],"--roots",root_alias,"--output",self.output],error="LINKED_PATH_REJECTED")
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
        self.root_fixture({});self.call(["--file",self.inputs[0],"--roots",junction/self.roots.name,"--output",self.output],error="LINKED_PATH_REJECTED")
        for flag,path in (("--file",self.inputs[0]),("--roots",self.roots),("--output",self.output)):
            args=self.args();args[args.index(flag)+1]=str(path)+":stream";self.call(args,error="DEVICE_OR_STREAM_PATH_REJECTED")
    @unittest.skipUnless(os.name!="nt",PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_bounds(self):
        fifo=self.work/"fictional.fifo";os.mkfifo(fifo)
        connection=socket.socket(socket.AF_UNIX);connection.bind(str(self.work/"fictional.sock"));self.addCleanup(connection.close)
        for path in (fifo,self.work/"fictional.sock"):
            self.call(["--file",path,"--output",self.output],error="REGULAR_FILE_REQUIRED")
            self.call(["--file",self.inputs[0],"--roots",path,"--output",self.output],error="REGULAR_FILE_REQUIRED")
        sparse=self.work/"fictional sparse.mk"
        with sparse.open("wb") as stream:stream.truncate(1<<34)
        self.assertEqual(sparse.stat().st_size,1<<34);self.assertLess(sparse.stat().st_blocks*512,1<<20)
        self.call(["--file",sparse,"--output",self.output],error="INPUT_BYTE_LIMIT");self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
