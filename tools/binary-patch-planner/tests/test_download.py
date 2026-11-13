"""Independent fictional-byte consumers of an isolated copied patch planner. MIT."""
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
RUNTIME = ("binary_patch_planner.py", "inspection_support.py", "examples/generate.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junctions_and_destination_names"
PROCESS_WINDOWS_REASON = "Native Windows junction and destination-name fixtures"
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


def edit(offset, expected, replacement):
    return dict(offset=offset, expected_hex=expected.hex(), replacement_hex=replacement.hex())


def plan(source, rows=None):
    return dict(schema_version=1, source=dict(bytes=len(source), sha256=sha(source)),
                patches=rows if rows is not None else [edit(3, source[3:6], b"XYZ")])


PROBE = r'''
import hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import binary_patch_planner as e
import inspection_support as s
assert Path(e.__file__).resolve()==base/'binary_patch_planner.py'
assert Path(s.__file__).resolve()==base/'inspection_support.py'
assert e.snapshot is s.snapshot and e.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py'
 assert g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
source=Path(args[args.index('--source')+1]);plan=Path(args[args.index('--plan')+1])
output=Path(args[args.index('--output')+1]);applied=Path(args[args.index('--apply-output')+1]) if '--apply-output' in args else None
if kind=='audit':
 e.Parser(description=e.__doc__);b'\xef\xbb\xbfprewarm'.decode('utf-8-sig')
 allowed={base/name for name in ('binary_patch_planner.py','inspection_support.py','examples/generate.py')}
 allowed.update((source,plan));allowed.update(output/name for name in ('report.json','report.html','MANIFEST.json'))
 if applied is not None:allowed.add(applied)
 read_counts={source:0,plan:0};candidate_reads=0;original=os.read
 def audited_read(fd,size):
  global candidate_reads
  before=os.fstat(fd);raw=original(fd,size);matched=False
  for path in read_counts:
   info=path.stat()
   if (before.st_dev,before.st_ino)==(info.st_dev,info.st_ino):read_counts[path]+=len(raw);matched=True
  if not matched:
   assert applied is not None and applied.exists()
   info=applied.stat();assert (before.st_dev,before.st_ino)==(info.st_dev,info.st_ino)
   candidate_reads+=len(raw)
  return raw
 os.read=audited_read
 def audit(event,values):
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open','ctypes.dlopen'):
   raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
  if event=='open' and not isinstance(values[0],int):assert Path(values[0]) in allowed,'UNEXPECTED_FILE_OPEN'
 sys.addaudithook(audit)
 code=e.main(args)
 assert read_counts=={source:source.stat().st_size,plan:plan.stat().st_size}
 assert candidate_reads==(source.stat().st_size if applied is not None else 0)
 raise SystemExit(code)
elif kind.startswith('limit:'):
 for name,value in json.loads(kind[6:]).items():
  assert name in ('MAX_SOURCE_BYTES','MAX_PATCHES','MAX_PATCH_BYTES','MAX_CHANGED_BYTES','MAX_ITEMS','MAX_REPORT')
  setattr(e if name.startswith(('MAX_SOURCE','MAX_PATCH','MAX_CHANGED')) else s,name,value)
elif kind=='scope_escape':
 original=e.analyze
 def analyzed(*values):
  report,candidate=original(*values);report['scope']='Fictional </pre><script>never_execute</script> & "quoted"';return report,candidate
 e.analyze=analyzed
elif kind in ('exclusive_race','report_open_failure'):
 original=os.open
 def open_changed(path,flags,*a,**kw):
  if kind=='exclusive_race' and Path(path)==applied and flags & os.O_CREAT:
   with Path(path).open('wb') as stream:stream.write(b'FICTIONAL_COMPETITOR')
  if kind=='report_open_failure' and Path(path).name=='MANIFEST.json':raise OSError('FICTIONAL_PRIVATE_REPORT_DETAIL')
  return original(path,flags,*a,**kw)
 os.open=open_changed
elif kind=='fsync_failure':
 def fail(*unused):raise OSError('FICTIONAL_PRIVATE_FLUSH_DETAIL')
 os.fsync=fail
elif kind=='write_failure':
 original=os.fdopen
 class FailingStream:
  def __init__(self,stream):self.stream=stream
  def __enter__(self):return self
  def __exit__(self,*args):self.stream.close()
  def write(self,raw):self.stream.write(raw[:2]);self.stream.flush();raise OSError('FICTIONAL_PRIVATE_WRITE_DETAIL')
  def flush(self):self.stream.flush()
 def fdopen(fd,*a,**kw):return FailingStream(original(fd,*a,**kw))
 os.fdopen=fdopen
elif kind in ('readback_mismatch','readback_failure'):
 original=e.snapshot
 def changed_snapshot(path,maximum):
  if Path(path)==applied:
   if kind=='readback_failure':raise OSError('FICTIONAL_PRIVATE_READBACK_DETAIL')
   return b'FICTIONAL_WRONG_READBACK'
  return original(path,maximum)
 e.snapshot=changed_snapshot
elif kind=='late_report_failure':
 def fail(*unused):raise OSError('FICTIONAL_PRIVATE_REPORT_DETAIL')
 e.write_report=fail
elif kind=='changed_input':
 original=os.read;changed=False
 def changed_read(*values):
  global changed
  raw=original(*values)
  if not changed:
   changed=True
   with source.open('ab') as stream:stream.write(b'fictional mutation')
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
        self.temp = tempfile.TemporaryDirectory(prefix="patch-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.copy = self.work / "copied runtime"
        self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT / name).read_bytes(); target = self.copy / name
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            self.pins[name] = sha(raw)
        self.source = self.work / "fictional source.bin"
        self.plan_path = self.work / "selected plan.json"
        self.output = self.work / "new report"
        self.applied = self.work / "new candidate.bin"
        self.env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
        self.fixture()
    def runtime_preserved(self):
        self.assertEqual({p.relative_to(self.copy).as_posix() for p in self.copy.rglob("*") if p.is_file()}, set(RUNTIME))
        self.assertEqual({name: sha((self.copy / name).read_bytes()) for name in RUNTIME}, self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
    def snapshot(self):
        rows = {}
        def visit(folder):
            for path in folder.iterdir():
                key = path.relative_to(self.work).as_posix(); info = path.lstat()
                if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                    rows[key] = ("LINK", os.readlink(path))
                elif stat.S_ISDIR(info.st_mode):
                    rows[key] = ("DIRECTORY",); visit(path)
                elif stat.S_ISREG(info.st_mode):
                    if info.st_size > 8 * 1024 * 1024:
                        with path.open("rb") as stream:
                            sample = stream.read(64); stream.seek(-64, os.SEEK_END); sample += stream.read(64)
                        digest = "SPARSE_ENDPOINTS:" + sha(sample)
                    else: digest = sha(path.read_bytes())
                    rows[key] = (digest, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink)
                else: rows[key] = ("SPECIAL", info.st_mode)
        visit(self.work)
        return rows
    def run_child(self, command, timeout=90, env=None):
        if str(command[0]).endswith(".py"):
            bootstrap = "import runpy,sys;from pathlib import Path;p=Path(sys.argv[1]).resolve();sys.path.insert(0,str(p.parent));sys.argv=sys.argv[1:];runpy.run_path(str(p),run_name='__main__')"
            command = ["-c", bootstrap, *command]
        return subprocess.run([sys.executable, "-I", "-B", "-W", "error", *map(str, command)],
                              cwd=self.work, env=self.env if env is None else env, stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=timeout)
    def fixture(self, source=b"abc123456def\x00\xff\n", value=None):
        self.source.write_bytes(source)
        self.plan_value = plan(source) if value is None else value
        self.plan_path.write_bytes(encoded(self.plan_value))
    def new_output(self, suffix):
        self.output = self.work / ("new report " + str(suffix))
        self.applied = self.work / ("new candidate " + str(suffix) + ".bin")
    def args(self, apply=False):
        result = ["--source", self.source, "--plan", self.plan_path, "--output", self.output]
        return result + (["--apply-output", self.applied] if apply else [])
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot()
        prefix = ["-c", PROBE, self.copy, probe] if probe else [self.copy / "binary_patch_planner.py"]
        done = self.run_child([*prefix, *args], env=env)
        self.assertEqual(done.stderr, b"", done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout, json.dumps(value, sort_keys=probe != "affinity").encode() + NEWLINE)
        if error is not None:
            self.assertEqual(value, dict(status="INCOMPLETE", error=error)); code = 2
        elif probe == "affinity":
            self.assertEqual(value, dict(status="COPIED_RUNTIME_AFFINITY", dependencies=0)); code = 0
        else:
            report = self.check_report(output, args)
            app = report["application"]
            self.assertEqual(value, dict(status=report["status"], patches=len(report["patches"]), findings=len(report["findings"]), application_requested=app["requested"], output_created=app["created"], output_verified=app["verified"]))
            value = report; code = int(report["status"] != "NO_SCOPE_FINDINGS")
        self.assertEqual(done.returncode, code)
        for private in (str(self.work).encode(), b"FICTIONAL_PRIVATE", b"Traceback"):
            self.assertNotIn(private, done.stdout + done.stderr)
        after = self.snapshot(); ignored = {Path(p).relative_to(self.work).as_posix() for p in ignore}
        self.assertEqual({k: v for k, v in before.items() if k not in ignored}, {k: after.get(k) for k in before if k not in ignored})
        for key in after.keys() - before.keys():
            path = self.work / key
            self.assertTrue(any(path == Path(root) or path.is_relative_to(root) for root in allow), "Unexpected application write: " + key)
        self.runtime_preserved()
        return value
    def check_report(self, output, args):
        self.assertIsNotNone(output)
        self.assertEqual({p.name for p in output.iterdir()}, {"report.json", "report.html", "MANIFEST.json"})
        raw = (output / "report.json").read_bytes(); report = json.loads(raw)
        self.assertEqual(raw, encoded(report))
        self.assertEqual(set(report), {"schema_version", "tool", "scope", "sources", "declared_source", "patches", "declared_patch_bytes", "candidate_sha256", "application", "findings", "coverage_issues", "status"})
        self.assertEqual((report["tool"], report["schema_version"]), ("Verified Binary Patch Planner", 1))
        self.assertEqual(report["status"], "REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        self.assertEqual(report["coverage_issues"], [])
        source = Path(args[args.index("--source") + 1]).read_bytes()
        selected_plan = Path(args[args.index("--plan") + 1]).read_bytes()
        value = json.loads(selected_plan.decode("utf-8-sig"))
        self.assertEqual(report["sources"], [dict(id=label, bytes=len(data), sha256=sha(data)) for label,data in (("source",source),("plan",selected_plan))])
        self.assertEqual(report["declared_source"], value["source"])
        patches = []
        for index,row in enumerate(value["patches"], 1):
            expected = bytes.fromhex(row["expected_hex"]); replacement = bytes.fromhex(row["replacement_hex"])
            offset = row["offset"]; inside = offset + len(expected) <= len(source)
            patches.append(dict(index=index, offset_bytes=offset, bytes=len(expected), within_selected_source=inside, expected_bytes_match=inside and source[offset:offset+len(expected)]==expected, changes_bytes=expected!=replacement))
        self.assertEqual(report["patches"], patches)
        self.assertEqual(report["declared_patch_bytes"], sum(len(bytes.fromhex(row["expected_hex"])) for row in value["patches"]))
        for row in report["findings"]: self.assertEqual(set(row), {"code", "patch_index"})
        app = report["application"]; applied = Path(args[args.index("--apply-output")+1]) if "--apply-output" in args else None
        self.assertIs(app["requested"], applied is not None)
        if report["findings"]:
            self.assertIsNone(report["candidate_sha256"]); self.assertFalse(app["created"]); self.assertFalse(app["verified"])
            if applied is not None: self.assertFalse(applied.exists())
        else:
            changes = {row["offset"]+i: byte for row in value["patches"] for i,byte in enumerate(bytes.fromhex(row["replacement_hex"]))}
            candidate = bytes(changes.get(i, byte) for i,byte in enumerate(source))
            self.assertEqual(report["candidate_sha256"], sha(candidate))
            if applied is None:
                self.assertEqual(app, dict(requested=False, created=False, verified=False))
            else:
                self.assertEqual(applied.read_bytes(), candidate)
                self.assertEqual(app, dict(requested=True, created=True, verified=True, bytes=len(candidate), sha256=sha(candidate), receipt_scope="Separate explicitly selected output file; local filename omitted."))
        for private in (str(self.work), self.source.name, self.plan_path.name, "expected_hex", "replacement_hex"):
            self.assertNotIn(private, raw.decode())
        markup = (output / "report.html").read_bytes(); parsed = StaticHTML(); parsed.feed(markup.decode()); parsed.close()
        self.assertEqual(parsed.tags.count("html"), 1); self.assertEqual(parsed.csp, ["default-src 'none'; style-src 'unsafe-inline'"])
        self.assertIn(html.escape(raw.decode(), quote=True).encode(), markup)
        members = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
        manifest = dict(schema_version=1, files=[dict(path=name, bytes=len(data), sha256=sha(data)) for name,data in sorted(members.items())])
        self.assertEqual((output/"MANIFEST.json").read_bytes(), encoded(manifest))
        return report
    def report(self, apply=False, **kwargs):
        return self.call(self.args(apply), output=self.output, allow=[self.output] + ([self.applied] if apply else []), **kwargs)
    def codes(self, report):
        return [(row["code"], row["patch_index"]) for row in report["findings"]]
    def symlink(self, path, target, directory=False):
        try: path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314 and os.environ.get("OUTLANDS_PATCH_REQUIRE_LINKS") != "1":
                self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_copied_runtime_affinity_and_help(self):
        self.call([], probe="affinity")
        for script in (self.copy/"binary_patch_planner.py", self.copy/"examples/generate.py"):
            before = self.snapshot(); done = self.run_child([script, "--help"])
            self.assertEqual((done.returncode, done.stderr), (0, b"")); self.assertIn(b"--output", done.stdout)
            self.assertEqual(self.snapshot(), before)
    def test_generator_cli_fictional_preview_apply_and_refusals(self):
        target = self.work/"generated"; before = self.snapshot()
        done = self.run_child([self.copy/"examples/generate.py", "--output", target])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (0, b"", json.dumps(dict(status="FICTIONAL_EXAMPLES_CREATED", files=4)).encode()+NEWLINE))
        self.assertEqual({p.name for p in target.iterdir()}, {"source.bin", "verified-plan.json", "unexpected-plan.json", "overlap-plan.json"})
        self.assertEqual({key:self.snapshot().get(key) for key in before}, before)
        self.source = target/"source.bin"; self.plan_path = target/"verified-plan.json"
        report = self.report(); self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertFalse(self.applied.exists())
        self.new_output("apply"); self.report(apply=True); self.assertEqual(self.applied.read_bytes(), b"ORCHARD-TEST-v2\n")
        self.new_output("mismatch"); self.plan_path = target/"unexpected-plan.json"
        self.assertEqual(self.codes(self.report(apply=True)), [("EXPECTED_BYTES_MISMATCH", 1)])
        self.new_output("overlap"); self.plan_path = target/"overlap-plan.json"; self.report(error="PATCH_OVERLAP")
        before = self.snapshot(); done = self.run_child([self.copy/"examples/generate.py", "--output", target])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (2, b"", json.dumps(dict(status="INCOMPLETE", error="OUTPUT_EXISTS"), sort_keys=True).encode()+NEWLINE)); self.assertEqual(self.snapshot(), before)
    def test_default_preview_checks_complete_source_and_plan_hashes(self):
        source = b"FICTIONAL_HEADER\x00\xffabc123tail"; value = plan(source, [edit(20, source[20:23], b"XYZ")])
        self.fixture(source, value); report = self.report()
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual(report["application"], dict(requested=False, created=False, verified=False))
        self.assertFalse(self.applied.exists()); self.assertEqual(self.source.read_bytes(), source)
        self.assertEqual(report["candidate_sha256"], sha(source[:20]+b"XYZ"+source[23:]))
    def test_explicit_apply_creates_only_separate_verified_equal_length_file(self):
        source = bytes(range(64)); self.fixture(source, plan(source, [edit(0, source[:2], b"XY"), edit(62, source[62:], b"ZZ")]))
        report = self.report(apply=True); expected = b"XY"+source[2:62]+b"ZZ"
        self.assertEqual(self.applied.read_bytes(), expected); self.assertEqual(self.source.read_bytes(), source)
        self.assertEqual(report["application"]["sha256"], sha(expected)); self.assertEqual(report["application"]["bytes"], len(source))
        self.assertTrue(report["application"]["verified"]); self.assertNotIn(self.applied.name, (self.output/"report.json").read_text())
    def test_unsorted_adjacent_and_noop_patches_preserve_declared_order(self):
        source = b"0123456789ABCDEF"; rows = [edit(8,b"89",b"xy"),edit(2,b"23",b"23"),edit(6,b"67",b"pq"),edit(4,b"45",b"MN")]
        self.fixture(source, plan(source,rows)); report = self.report(apply=True)
        self.assertEqual([row["offset_bytes"] for row in report["patches"]], [8,2,6,4])
        self.assertEqual([row["changes_bytes"] for row in report["patches"]], [True,False,True,True])
        self.assertEqual(report["declared_patch_bytes"], 8); self.assertEqual(self.applied.read_bytes(), b"0123MNpqxyABCDEF")
    def test_size_hash_expected_and_outside_mismatches_withhold_application(self):
        source = self.source.read_bytes()
        cases = []
        value = plan(source); value["source"]["bytes"] += 1; cases.append((value, [("SOURCE_SIZE_MISMATCH",None)]))
        value = plan(source); value["source"]["sha256"] = "0"*64; cases.append((value, [("SOURCE_HASH_MISMATCH",None)]))
        value = plan(source); value["patches"][0]["expected_hex"] = b"bad".hex(); cases.append((value, [("EXPECTED_BYTES_MISMATCH",1)]))
        value = plan(source, [edit(len(source),b"xx",b"yy")]); value["source"]["bytes"] += 2
        cases.append((value, [("SOURCE_SIZE_MISMATCH",None),("PATCH_OUTSIDE_SELECTED_SOURCE",1)]))
        for index,(value, expected) in enumerate(cases):
            self.fixture(source,value); self.new_output(index); report = self.report(apply=True)
            self.assertEqual(self.codes(report), expected); self.assertEqual(report["status"], "REVIEW_REQUIRED"); self.assertFalse(self.applied.exists())
        changed = source[:-1]+b"!"; self.fixture(changed,plan(source)); self.new_output("unpatched-tail")
        self.assertEqual(self.codes(self.report(apply=True)), [("SOURCE_HASH_MISMATCH",None)])
    def test_top_level_schema_has_no_ignored_extra_fields(self):
        source = self.source.read_bytes(); value = plan(source)
        cases = [None, [], True, {"schema_version":1}, dict(value, ignored="FICTIONAL_PRIVATE_PAYLOAD"), {key:item for key,item in value.items() if key!="patches"}]
        for index,item in enumerate(cases):
            self.plan_path.write_bytes(encoded(item)); self.new_output(index); self.report(error="PLAN_FIELDS_INVALID"); self.assertFalse(self.output.exists())
    def test_version_and_source_fields_reject_coercions_and_invalid_hashes(self):
        source = self.source.read_bytes(); cases = []
        for version in (True,0,2,"1",None):
            value=plan(source);value["schema_version"]=version;cases.append((value,"PLAN_VERSION_UNSUPPORTED"))
        for selected in (None,[],dict(bytes=15),dict(bytes=15,sha256=sha(source),filename="secret")):
            value=plan(source);value["source"]=selected;cases.append((value,"SOURCE_FIELDS_INVALID"))
        for size in (True,0,-1,4194305,"15",None):
            value=plan(source);value["source"]["bytes"]=size;cases.append((value,"SOURCE_SIZE_INVALID"))
        for digest in (sha(source).upper(),"a"*63,"a"*65,"g"*64,True,None):
            value=plan(source);value["source"]["sha256"]=digest;cases.append((value,"SOURCE_HASH_INVALID"))
        for index,(value,code) in enumerate(cases):
            self.plan_path.write_bytes(encoded(value)); self.new_output(index); self.report(apply=True,error=code); self.assertFalse(self.applied.exists())
    def test_patch_shape_count_and_offset_require_exact_integers(self):
        source=self.source.read_bytes(); cases=[]
        for rows in ([],None,{},"x"):
            value=plan(source);value["patches"]=rows;cases.append((value,"PATCH_COUNT_LIMIT"))
        for row in (None,[],{},dict(offset=0,expected_hex="61"),dict(offset=0,expected_hex="61",replacement_hex="62",extra=0)):
            value=plan(source);value["patches"]=[row];cases.append((value,"PATCH_FIELDS_INVALID"))
        for offset in (True,-1,len(source),"3",None,10**100):
            value=plan(source);value["patches"][0]["offset"]=offset;cases.append((value,"PATCH_OFFSET_INVALID"))
        for index,(value,code) in enumerate(cases):
            self.plan_path.write_bytes(encoded(value));self.new_output(index);self.report(error=code);self.assertFalse(self.output.exists())
    def test_hex_bytes_lengths_ranges_and_case_are_checked(self):
        source=self.source.read_bytes(); cases=[]
        for field in ("expected_hex","replacement_hex"):
            for text in ("","0","0x61","61 62","GG",True,None,"a"*8194):
                value=plan(source);value["patches"][0][field]=text;cases.append((value,"JSON_TEXT_UNSUPPORTED" if isinstance(text,str) and len(text)>8192 else "PATCH_HEX_INVALID"))
        value=plan(source);value["patches"][0]["replacement_hex"]="61";cases.append((value,"PATCH_LENGTH_MISMATCH"))
        value=plan(source,[edit(len(source)-1,b"ab",b"cd")]);cases.append((value,"PATCH_RANGE_INVALID"))
        for index,(value,code) in enumerate(cases):
            self.plan_path.write_bytes(encoded(value));self.new_output(index);self.report(error=code)
        source=b"\xab\xcd\xef";value=plan(source,[edit(0,source,b"\xfe\xdc\xba")]);value["patches"][0]["expected_hex"]="ABCDEF"
        self.fixture(source,value);self.new_output("uppercase");self.report(apply=True);self.assertEqual(self.applied.read_bytes(),b"\xfe\xdc\xba")
    def test_overlapping_duplicate_nested_and_same_offset_ranges_refuse(self):
        source=self.source.read_bytes()
        for index,rows in enumerate(([edit(2,source[2:5],b"ABC"),edit(4,source[4:6],b"ZZ")], [edit(2,source[2:6],b"ABCD"),edit(3,source[3:4],b"Z")], [edit(3,source[3:6],b"XYZ")]*2)):
            self.fixture(source,plan(source,rows));self.new_output(index);self.report(apply=True,error="PATCH_OVERLAP");self.assertFalse(self.applied.exists());self.assertFalse(self.output.exists())
    def test_strict_json_duplicate_numbers_utf8_controls_and_depth(self):
        good=self.plan_path.read_bytes()
        cases=[(b"{","INVALID_JSON"),(b"\xff","INVALID_JSON"),(b'{"x":1,"x":2}',"DUPLICATE_JSON_KEY"),(good.replace(b'"schema_version": 1',b'"schema_version": 1.0'),"JSON_NUMBER_UNSUPPORTED"),(b'{"x":NaN}',"JSON_NUMBER_UNSUPPORTED"),(b'{"x":Infinity}',"JSON_NUMBER_UNSUPPORTED"),(b'{"x":"\\u0000"}',"JSON_TEXT_UNSUPPORTED"),(b'{"\\u0000":0}',"JSON_TEXT_UNSUPPORTED"),(b'['*10+b'0'+b']'*10,"JSON_STRUCTURE_LIMIT"),(b'{"'+b'k'*257+b'":0}',"JSON_TEXT_UNSUPPORTED"),(good+b' trailing',"INVALID_JSON")]
        for index,(raw,code) in enumerate(cases):
            self.plan_path.write_bytes(raw);self.new_output(index);self.report(error=code);self.assertFalse(self.output.exists())
        self.plan_path.write_bytes(b"\xef\xbb\xbf"+good.replace(b"\n",b"\r\n"));self.new_output("bom-crlf");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
    def test_source_and_plan_byte_boundaries_are_exact(self):
        source=b"x"*4194304;self.fixture(source,plan(source,[edit(4194303,b"x",b"y")]))
        report=self.report();self.assertEqual(report["sources"][0]["bytes"],4194304)
        self.source.write_bytes(source+b"x");self.new_output("source-over");self.report(error="INPUT_BYTE_LIMIT")
        self.fixture();raw=self.plan_path.read_bytes();self.plan_path.write_bytes(raw+b" "*(1048576-len(raw)));self.new_output("plan-exact");self.report()
        with self.plan_path.open("ab") as stream:stream.write(b" ")
        self.new_output("plan-over");self.report(error="INPUT_BYTE_LIMIT");self.assertFalse(self.output.exists())
    def test_patch_count_bytes_total_and_collection_limits(self):
        source=b"x"*1001;self.fixture(source,plan(source,[edit(i,b"x",b"y") for i in range(1000)]));self.report()
        self.fixture(source,plan(source,[edit(i,b"x",b"y") for i in range(1001)]));self.new_output("count");self.report(error="PATCH_COUNT_LIMIT")
        source=b"x"*4097;self.fixture(source,plan(source,[edit(0,b"x"*4096,b"y"*4096)]));self.new_output("bytes");self.report()
        self.fixture();self.new_output("patch-budget");self.report(probe='limit:{"MAX_PATCH_BYTES":2}',error="PATCH_HEX_INVALID")
        self.new_output("total-budget");self.report(probe='limit:{"MAX_CHANGED_BYTES":2}',error="PATCH_TOTAL_LIMIT")
        self.new_output("collection-budget");self.report(probe='limit:{"MAX_ITEMS":0}',error="RECORD_LIMIT")
        self.new_output("source-budget");self.report(probe='limit:{"MAX_SOURCE_BYTES":10}',error="INPUT_BYTE_LIMIT")
    def test_reports_omit_payloads_local_names_and_patch_hex(self):
        private=b"FictionalSecret</pre><script>never_execute</script>"
        self.fixture(private,plan(private,[edit(0,b"Fictional",b"Synthetic")]))
        self.report(apply=True)
        for path in self.output.iterdir():
            raw=path.read_bytes()
            for text in (private,b"Fictional",b"Synthetic",b"never_execute",b"expected_hex",b"replacement_hex",str(self.source).encode(),str(self.applied).encode()):self.assertNotIn(text,raw)
        self.assertEqual(self.applied.read_bytes(),b"Synthetic"+private[9:])
    def test_static_html_escapes_report_strings_and_manifest_hashes(self):
        report=self.report(probe="scope_escape")
        self.assertEqual(report["scope"],'Fictional </pre><script>never_execute</script> & "quoted"')
        raw=(self.output/"report.html").read_bytes();self.assertNotIn(b"<script>",raw);self.assertIn(b"&lt;script&gt;never_execute&lt;/script&gt;",raw)
        self.assertEqual([row["path"] for row in json.loads((self.output/"MANIFEST.json").read_bytes())["files"]],["report.html","report.json"])
    def test_hostile_import_environment_and_nonselected_files_are_ignored(self):
        hostile=self.work/"hostile imports";hostile.mkdir()
        for name in ("sitecustomize.py","usercustomize.py","json.py","hashlib.py"):(hostile/name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        (self.work/"unselected executable.py").write_text("raise AssertionError('FICTIONAL_PRIVATE_EXECUTION')\n")
        env=dict(self.env,PYTHONPATH=str(hostile),PYTHONHOME=str(hostile),PYTHONSTARTUP=str(hostile/"sitecustomize.py"))
        self.report(env=env);self.assertFalse(self.applied.exists())
    def test_arguments_and_local_paths_produce_fixed_private_errors(self):
        for args in ([],["--source",self.source],["--private-unknown=secret"]):self.call(args,error="ARGUMENTS_INVALID")
        for path,code in (("relative.bin","LOCAL_ABSOLUTE_PATH_REQUIRED"),(self.work/".."/"fictional.bin","LOCAL_ABSOLUTE_PATH_REQUIRED"),("//fictional/share/source.bin","LOCAL_ABSOLUTE_PATH_REQUIRED"),(str(self.source)+"\nprivate","INVALID_LOCAL_PATH"),(self.copy,"REGULAR_FILE_REQUIRED"),(self.work/"missing.bin","IO_OR_INPUT_ERROR")):
            args=self.args();args[1]=path;self.call(args,error=code)
        for option in ("--output","--apply-output"):
            args=self.args(apply=True);args[args.index(option)+1]="relative";self.call(args,error="LOCAL_ABSOLUTE_PATH_REQUIRED")
        self.assertFalse(self.output.exists());self.assertFalse(self.applied.exists())
    def test_input_aliases_hardlinks_and_existing_destinations_never_overwrite(self):
        hard=self.work/"hard alias.bin";os.link(self.source,hard);self.assertTrue(self.source.samefile(hard))
        for second in (self.source,hard):
            args=self.args();args[3]=second;self.call(args,error="DUPLICATE_INPUT_FILE")
        for path in (self.source,self.plan_path,self.copy,hard):
            for option in ("--output","--apply-output"):
                args=self.args(apply=True);args[args.index(option)+1]=path;self.call(args,error="OUTPUT_EXISTS")
        os.link(self.source,self.applied);self.report(apply=True,error="OUTPUT_EXISTS");self.applied.unlink()
        self.output.mkdir();(self.output/"keep.txt").write_bytes(b"keep");self.report(apply=True,error="OUTPUT_EXISTS");self.assertFalse(self.applied.exists())
    def test_destination_overlap_and_missing_parents_prevent_any_apply(self):
        args=self.args(apply=True);args[-1]=self.output;self.call(args,error="OUTPUT_DESTINATIONS_OVERLAP")
        args=self.args(apply=True);args[-1]=self.output/"inside.bin";self.call(args,error="IO_OR_INPUT_ERROR")
        args=self.args(apply=True);args[5]=self.applied/"inside-report";self.call(args,error="IO_OR_INPUT_ERROR")
        for option in ("--output","--apply-output"):
            args=self.args(apply=True);args[args.index(option)+1]=self.work/"missing"/"child";self.call(args,error="IO_OR_INPUT_ERROR")
        self.assertFalse(self.output.exists());self.assertFalse(self.applied.exists())
    def test_exclusive_create_race_preserves_competitor_and_reports_failure(self):
        self.report(apply=True,probe="exclusive_race",error="IO_OR_INPUT_ERROR")
        self.assertEqual(self.applied.read_bytes(),b"FICTIONAL_COMPETITOR");self.assertFalse(self.output.exists())
        self.report(apply=True,error="OUTPUT_EXISTS")
    def test_write_and_fsync_failures_leave_new_artifacts_without_success(self):
        source=self.source.read_bytes();candidate=source[:3]+b"XYZ"+source[6:]
        for index,kind in enumerate(("write_failure","fsync_failure")):
            self.new_output(index);self.report(apply=True,probe=kind,error="IO_OR_INPUT_ERROR")
            self.assertEqual(self.applied.read_bytes(),candidate[:2] if kind=="write_failure" else candidate)
            self.assertFalse(self.output.exists());self.assertEqual(self.source.read_bytes(),source)
            self.report(apply=True,error="OUTPUT_EXISTS")
    def test_readback_mismatch_or_io_failure_never_emits_verified_receipt(self):
        source=self.source.read_bytes();candidate=source[:3]+b"XYZ"+source[6:]
        for index,kind in enumerate(("readback_mismatch","readback_failure")):
            self.new_output(index);self.report(apply=True,probe=kind,error="APPLIED_OUTPUT_VERIFICATION_FAILED" if kind=="readback_mismatch" else "IO_OR_INPUT_ERROR")
            self.assertEqual(self.applied.read_bytes(),candidate);self.assertFalse(self.output.exists());self.assertEqual(self.source.read_bytes(),source)
    def test_late_report_and_manifest_failures_preserve_created_candidate(self):
        source=self.source.read_bytes();candidate=source[:3]+b"XYZ"+source[6:]
        for index,kind in enumerate(("late_report_failure","report_open_failure")):
            self.new_output(index);self.report(apply=True,probe=kind,error="IO_OR_INPUT_ERROR")
            self.assertEqual(self.applied.read_bytes(),candidate);self.assertEqual(self.source.read_bytes(),source)
            if kind=="late_report_failure":self.assertFalse(self.output.exists())
            else:
                self.assertEqual({p.name for p in self.output.iterdir()},{"report.json","report.html"})
                app=json.loads((self.output/"report.json").read_bytes())["application"];self.assertTrue(app["created"] and app["verified"])
                self.report(apply=True,error="OUTPUT_EXISTS")
    def test_report_budget_failure_truthfully_leaves_requested_candidate(self):
        self.report(probe='limit:{"MAX_REPORT":100}',error="REPORT_BYTE_LIMIT");self.assertFalse(self.output.exists());self.assertFalse(self.applied.exists())
        self.new_output("apply");self.report(apply=True,probe='limit:{"MAX_REPORT":100}',error="REPORT_BYTE_LIMIT")
        source=self.source.read_bytes();self.assertEqual(self.applied.read_bytes(),source[:3]+b"XYZ"+source[6:]);self.assertFalse(self.output.exists())
    def test_changed_and_short_input_reads_refuse_before_candidate_creation(self):
        self.report(apply=True,probe="changed_input",error="INPUT_CHANGED",ignore=[self.source]);self.assertFalse(self.output.exists());self.assertFalse(self.applied.exists())
        self.fixture();self.report(apply=True,probe="short_read",error="INPUT_CHANGED");self.assertFalse(self.output.exists());self.assertFalse(self.applied.exists())
    def test_native_symlink_inputs_and_output_parents(self):
        alias=self.work/"linked source.bin";self.symlink(alias,self.source)
        args=self.args();args[1]=alias;self.call(args,error="LINKED_PATH_REJECTED")
        linked_plan=self.work/"linked plan.json";self.symlink(linked_plan,self.plan_path)
        args=self.args();args[3]=linked_plan;self.call(args,error="LINKED_PATH_REJECTED")
        route=self.work/"linked directory";self.symlink(route,self.work,directory=True)
        for option in ("--output","--apply-output"):
            args=self.args(apply=True);args[args.index(option)+1]=route/"new-output";self.call(args,error="LINKED_PATH_REJECTED")
        dangling=self.work/"dangling output";self.symlink(dangling,self.work/"nonexistent")
        args=self.args(apply=True);args[-1]=dangling;self.call(args,error="OUTPUT_EXISTS")
    @unittest.skipUnless(os.name=="nt",PROCESS_WINDOWS_REASON)
    def test_native_windows_junctions_and_destination_names(self):
        junction=self.work/"junction";done=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(junction),str(self.work)],capture_output=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stderr.decode(errors="replace"));self.addCleanup(lambda:junction.rmdir() if junction.exists() else None)
        args=self.args();args[1]=junction/self.source.name;self.call(args,error="LINKED_PATH_REJECTED")
        for option in ("--output","--apply-output"):
            args=self.args(apply=True);args[args.index(option)+1]=junction/"new";self.call(args,error="LINKED_PATH_REJECTED")
            for name in ("CON","CONIN$","CONOUT$","nul.bin","COM1","LPT2.txt","name.","name ","COM"+chr(185)):
                args=self.args(apply=True);args[args.index(option)+1]=self.work/name;self.call(args,error="WINDOWS_PATH_COMPONENT_UNSUPPORTED")
            args=self.args(apply=True);args[args.index(option)+1]=str(self.applied)+":stream";self.call(args,error="DEVICE_OR_STREAM_PATH_REJECTED")
        args=self.args();args[1]=str(self.source)+":stream";self.call(args,error="DEVICE_OR_STREAM_PATH_REJECTED")
    @unittest.skipUnless(os.name!="nt",PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_bounds(self):
        fifo=self.work/"fictional.fifo";os.mkfifo(fifo)
        connection=socket.socket(socket.AF_UNIX);connection.bind(str(self.work/"fictional.sock"));self.addCleanup(connection.close)
        for path in (fifo,self.work/"fictional.sock"):
            for option in ("--source","--plan"):
                args=self.args(apply=True);args[args.index(option)+1]=path;self.call(args,error="REGULAR_FILE_REQUIRED")
        sparse=self.work/"fictional sparse.bin"
        with sparse.open("wb") as stream:stream.truncate(1<<34)
        self.assertEqual(sparse.stat().st_size,1<<34);self.assertLess(sparse.stat().st_blocks*512,1<<20)
        args=self.args(apply=True);args[1]=sparse;self.call(args,error="INPUT_BYTE_LIMIT");self.assertFalse(self.applied.exists())
    def test_audit_allows_only_selected_files_and_never_external_actions(self):
        unselected=self.work/"not selected.bin";unselected.write_bytes(b"FICTIONAL_PRIVATE_NOT_SELECTED")
        preview=self.report(probe="audit");self.assertFalse(self.applied.exists())
        self.new_output("apply");applied=self.report(apply=True,probe="audit")
        self.assertEqual(preview["candidate_sha256"],applied["candidate_sha256"]);self.assertTrue(applied["application"]["verified"])


if __name__ == "__main__":
    unittest.main()
