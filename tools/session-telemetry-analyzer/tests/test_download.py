"""Independent copied-runtime consumers of fictional saved telemetry; no live collection. MIT."""
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
RUNTIME = ("telemetry_analyzer.py", "inspection_support.py", "examples/generate.py")
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


def event(kind="snapshot", **payload):
    return dict(type=kind, payload=payload)


def records(*values):
    return ("\n".join(json.dumps(value, ensure_ascii=True, separators=(",", ":")) for value in values) + "\n").encode()


def population(values=(), missing=0, invalid=0):
    return dict(samples=len(values), missing_samples=missing, invalid_samples=invalid, sum=str(sum(values)),
                maximum=max(values) if values else None,
                sample_mean=dict(numerator=str(sum(values)), denominator=len(values)) if values else None)


PROBE = r'''
import hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import telemetry_analyzer as e
import inspection_support as s
assert Path(e.__file__).resolve()==base/'telemetry_analyzer.py'
assert Path(s.__file__).resolve()==base/'inspection_support.py'
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
 e.parse_record('{"type":"snapshot","payload":{"raid_seconds":0.1}}')
 allowed={base/name for name in ('telemetry_analyzer.py','inspection_support.py','examples/generate.py')}
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
  assert name in ('MAX_RECORDS','MAX_NODES','MAX_LOS','MAX_ITEMS','MAX_REPORT','MAX_LINE','MAX_LINES')
  setattr(e if name in ('MAX_RECORDS','MAX_NODES','MAX_LOS') else s,name,value)
elif kind=='scope_escape':
 original=e.summarize
 def summarized(*values):
  report=original(*values);report['scope']='Fictional </pre><script>never_execute</script> & "quoted"';return report
 e.summarize=summarized
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
        self.temp = tempfile.TemporaryDirectory(prefix="telemetry-cli-", dir=parent)
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
        self.fixture(records(event()))
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
            path = self.work/("fictional capture "+str(number)+".jsonl"); path.write_bytes(raw); self.inputs.append(path)
    def new_output(self, suffix):
        self.output = self.work/("new report "+str(suffix))
    def args(self):
        return [item for path in self.inputs for item in ("--file",path)] + ["--output",self.output]
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot(); prefix = ["-c",PROBE,self.copy,probe] if probe else [self.copy/"telemetry_analyzer.py"]
        done = self.run_child([*prefix,*args], env=env)
        self.assertEqual(done.stderr,b"",done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout,json.dumps(value,sort_keys=probe!="affinity").encode()+NEWLINE)
        if error is not None: self.assertEqual(value,dict(status="INCOMPLETE",error=error)); code = 2
        elif probe == "affinity": self.assertEqual(value,dict(status="COPIED_RUNTIME_AFFINITY",dependencies=0)); code = 0
        else:
            report = self.check_report(output,args)
            self.assertEqual(value,dict(status=report["status"],selected_files=report["selected_files"],nonblank_records_observed=report["nonblank_records_observed"],findings=len(report["findings"]),coverage_issues=len(report["coverage_issues"])))
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
        self.assertEqual(set(report),{"schema_version","tool","scope","sources","captures","findings","coverage_issues","selected_files","nonblank_records_observed","status"})
        self.assertEqual((report["schema_version"],report["tool"]),(1,"Offline Session Telemetry Analyzer"))
        self.assertEqual(report["status"],"REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        selected = [Path(args[i+1]) for i,item in enumerate(args[:-1]) if item=="--file"]
        self.assertEqual(report["sources"],[dict(id="input-"+str(i).zfill(4),bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for i,path in enumerate(selected,1)])
        self.assertEqual([c["source"] for c in report["captures"]],[r["id"] for r in report["sources"]]); self.assertEqual(report["selected_files"],len(selected))
        self.assertEqual(report["nonblank_records_observed"],sum(c["nonblank_rows"] for c in report["captures"]))
        for capture in report["captures"]:
            self.assertEqual(set(capture),{"source","physical_lines","blank_rows","nonblank_rows","decoded_rows","accepted_events","malformed_json_rows","invalid_envelope_rows","unsupported_event_rows","event_counts","populations","line_of_sight","declared_time","dropped_data"})
            self.assertEqual(capture["physical_lines"],capture["blank_rows"]+capture["nonblank_rows"])
            self.assertEqual(capture["nonblank_rows"],capture["decoded_rows"]+capture["malformed_json_rows"])
            self.assertEqual(capture["decoded_rows"],capture["accepted_events"]+capture["invalid_envelope_rows"]+capture["unsupported_event_rows"])
            self.assertEqual(set(capture["event_counts"]),{"raid_start","snapshot","tracking_assigned","raid_end"})
            self.assertEqual(sum(capture["event_counts"].values()),capture["accepted_events"])
            self.assertEqual(set(capture["populations"]),{"players","bots","tracked_active"})
            for row in capture["populations"].values():
                self.assertEqual(set(row),{"samples","missing_samples","invalid_samples","sum","maximum","sample_mean"})
                self.assertEqual(row["samples"]+row["missing_samples"]+row["invalid_samples"],capture["event_counts"]["snapshot"])
                self.assertEqual(row["sample_mean"],dict(numerator=row["sum"],denominator=row["samples"]) if row["samples"] else None)
                self.assertEqual(row["maximum"] is None,row["samples"]==0)
            los = capture["line_of_sight"]
            self.assertEqual(set(los),{"present_collections","missing_collections","invalid_collections","declared_entries","valid_boolean_samples","visible_samples","missing_entry_values","invalid_entry_values","visible_fraction"})
            self.assertEqual(los["present_collections"]+los["missing_collections"]+los["invalid_collections"],capture["event_counts"]["snapshot"])
            self.assertEqual(los["declared_entries"],los["valid_boolean_samples"]+los["missing_entry_values"]+los["invalid_entry_values"])
            self.assertEqual(los["visible_fraction"],dict(numerator=str(los["visible_samples"]),denominator=los["valid_boolean_samples"]) if los["valid_boolean_samples"] else None)
            self.assertEqual(set(capture["declared_time"]),{"valid_declarations","invalid_declarations","last_in_file_seconds"})
            self.assertEqual(set(capture["dropped_data"]),{"end_rows","valid_declarations","invalid_declarations","state","declared_dropped_lines"})
        for row in report["findings"]+report["coverage_issues"]:
            self.assertIn(set(row),({"code","source","line"},{"code","source","line","field"})); self.assertIn(row["source"],[r["id"] for r in report["sources"]])
            if "field" in row: self.assertIn(row["field"],{"players","bots","tracked_active"})
        for private in (str(self.work),"fictional capture","FICTIONAL_PRIVATE"): self.assertNotIn(private,raw.decode())
        markup = (output/"report.html").read_bytes(); parsed = StaticHTML(); parsed.feed(markup.decode()); parsed.close()
        self.assertEqual(parsed.tags.count("html"),1); self.assertEqual(parsed.csp,["default-src 'none'; style-src 'unsafe-inline'"])
        self.assertIn(html.escape(raw.decode(),quote=True).encode(),markup)
        members = {name:(output/name).read_bytes() for name in ("report.json","report.html")}
        manifest = dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=sha(data)) for name,data in sorted(members.items())])
        self.assertEqual((output/"MANIFEST.json").read_bytes(),encoded(manifest)); return report
    def report(self, **kwargs):
        return self.call(self.args(),output=self.output,allow=[self.output],**kwargs)
    def codes(self, report):
        return {row["code"] for row in report["findings"]+report["coverage_issues"]}
    def symlink(self, path, target, directory=False):
        try: path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            if os.name=="nt" and getattr(error,"winerror",None)==1314 and os.environ.get("OUTLANDS_TELEMETRY_REQUIRE_LINKS")!="1": self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_copied_runtime_affinity_and_help(self):
        self.call([],probe="affinity")
        for script in (self.copy/"telemetry_analyzer.py",self.copy/"examples/generate.py"):
            before=self.snapshot();done=self.run_child([script,"--help"])
            self.assertEqual((done.returncode,done.stderr),(0,b""));self.assertIn(b"--output",done.stdout);self.assertEqual(self.snapshot(),before)
    def test_generator_cli_three_fictional_inputs_and_fresh_destination(self):
        target=self.work/"generated";before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(0,b"",json.dumps(dict(status="FICTIONAL_EXAMPLES_CREATED",files=3)).encode()+NEWLINE))
        self.assertEqual({p.name for p in target.iterdir()},{"clean.jsonl","review.jsonl","missing-fields.jsonl"});self.assertEqual({k:self.snapshot().get(k) for k in before},before)
        for name,status in (("clean","NO_SCOPE_FINDINGS"),("review","REVIEW_REQUIRED"),("missing-fields","NO_SCOPE_FINDINGS")):
            self.inputs=[target/(name+".jsonl")];self.new_output(name);report=self.report();self.assertEqual(report["status"],status)
            if name=="clean":
                capture=report["captures"][0];self.assertEqual(capture["accepted_events"],6)
                self.assertEqual(capture["populations"],dict(players=population([2,4],missing=1),bots=population([4,8],missing=1),tracked_active=population([3,1],missing=1)))
            elif name=="review":self.assertEqual(report["captures"][0]["dropped_data"]["state"],"ambiguous_multiple_end_rows")
        before=self.snapshot();done=self.run_child([self.copy/"examples/generate.py","--output",target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(2,b"",json.dumps(dict(status="INCOMPLETE",error="OUTPUT_EXISTS"),sort_keys=True).encode()+NEWLINE));self.assertEqual(self.snapshot(),before)
    def test_independent_valid_present_denominators_are_exact(self):
        self.fixture(records(event(player_count=2,bot_count=4,tracking=dict(active_count=9)),event(player_count=8),event(bot_count=14),event(tracking=dict(active_count=3))))
        capture=self.report()["captures"][0]
        self.assertEqual(capture["populations"],dict(players=population([2,8],missing=2),bots=population([4,14],missing=2),tracked_active=population([9,3],missing=2)))
        self.assertEqual(capture["event_counts"],dict(raid_start=0,snapshot=4,tracking_assigned=0,raid_end=0))
    def test_explicit_zero_missing_and_absent_means_remain_distinct(self):
        self.fixture(records(event(player_count=0),event(),event("raid_start",raid_seconds=0),event("raid_end",dropped_lines=0)))
        report=self.report();capture=report["captures"][0];self.assertEqual(report["status"],"NO_SCOPE_FINDINGS")
        self.assertEqual(capture["populations"],dict(players=population([0],missing=1),bots=population(missing=2),tracked_active=population(missing=2)))
        self.assertEqual(capture["declared_time"],dict(valid_declarations=1,invalid_declarations=0,last_in_file_seconds="0"))
        self.assertEqual(capture["line_of_sight"]["visible_fraction"],None)
    def test_invalid_population_values_never_enter_denominators_as_zero(self):
        values=(True,False,None,"4",4.0,-1,1000000001,[],{})
        self.fixture(records(*(event(player_count=value,bot_count=value) for value in values),event(player_count=1000000000,bot_count=0)))
        report=self.report();capture=report["captures"][0]
        self.assertEqual(capture["populations"]["players"],population([1000000000],invalid=9));self.assertEqual(capture["populations"]["bots"],population([0],invalid=9))
        self.assertEqual(capture["populations"]["tracked_active"],population(missing=10));self.assertEqual(self.codes(report),{"POPULATION_VALUE_INVALID"})
        self.assertEqual(len(report["coverage_issues"]),18)
    def test_tracking_missing_empty_invalid_container_and_value_accounting(self):
        self.fixture(records(event(),event(tracking={}),event(tracking=None),event(tracking=[]),event(tracking=True),event(tracking=dict(active_count=None)),event(tracking=dict(active_count=0)),event(tracking=dict(active_count=5))))
        report=self.report();self.assertEqual(report["captures"][0]["populations"]["tracked_active"],population([0,5],missing=2,invalid=4))
        self.assertEqual(self.codes(report),{"POPULATION_CONTAINER_INVALID","POPULATION_VALUE_INVALID"})
    def test_line_of_sight_counts_only_boolean_present_values(self):
        entries=[dict(main_can_see_bot=True),dict(main_can_see_bot=False),{},dict(main_can_see_bot=1),None,dict(main_can_see_bot=None)]
        self.fixture(records(event(line_of_sight=entries),event(),event(line_of_sight=[]),event(line_of_sight=None)))
        report=self.report();los=report["captures"][0]["line_of_sight"]
        self.assertEqual(los,dict(present_collections=2,missing_collections=1,invalid_collections=1,declared_entries=6,valid_boolean_samples=2,visible_samples=1,missing_entry_values=1,invalid_entry_values=3,visible_fraction=dict(numerator="1",denominator=2)))
        self.assertEqual(self.codes(report),{"LOS_VALUE_INVALID","LOS_ENTRY_INVALID","LOS_COLLECTION_INVALID"})
    def test_los_empty_missing_invalid_and_entry_limit_are_not_coerced(self):
        self.fixture(records(event(line_of_sight=[]),event(),event(line_of_sight={}),event(line_of_sight="private")))
        los=self.report()["captures"][0]["line_of_sight"]
        self.assertEqual((los["present_collections"],los["missing_collections"],los["invalid_collections"],los["declared_entries"],los["visible_fraction"]),(1,1,2,0,None))
        self.fixture(records(event(line_of_sight=[dict(main_can_see_bot=False)]*256)));self.new_output("exact");self.assertEqual(self.report()["captures"][0]["line_of_sight"]["valid_boolean_samples"],256)
        self.fixture(records(event(line_of_sight=[{}]*257)));self.new_output("over");self.report(error="LOS_ENTRY_LIMIT");self.assertFalse(self.output.exists())
    def test_declared_seconds_preserve_decimal_digits_and_exponents(self):
        raw=b'{"type":"snapshot","payload":{"raid_seconds":0.1000000000000000000000000001}}\n'
        self.fixture(raw);self.assertEqual(self.report()["captures"][0]["declared_time"],dict(valid_declarations=1,invalid_declarations=0,last_in_file_seconds="0.1000000000000000000000000001"))
        self.fixture(b'{"type":"raid_start","payload":{"raid_seconds":1e2}}\n');self.new_output("exponent")
        self.assertEqual(self.report()["captures"][0]["declared_time"]["last_in_file_seconds"],"1E+2")
        self.fixture(b'{"type":"snapshot","payload":{"raid_seconds":1e-1000}}\n');self.new_output("tiny")
        self.assertEqual(self.report()["captures"][0]["declared_time"]["last_in_file_seconds"],"1E-1000")
    def test_invalid_seconds_do_not_reset_last_valid_or_hide_decrease(self):
        invalid=(True,None,"9",-1,315360001)
        self.fixture(records(event(raid_seconds=10),*(event(raid_seconds=value) for value in invalid))+b'{"type":"snapshot","payload":{"raid_seconds":9.9999999999999999999999999999}}\n')
        report=self.report();self.assertEqual(report["captures"][0]["declared_time"],dict(valid_declarations=2,invalid_declarations=5,last_in_file_seconds="9.9999999999999999999999999999"))
        self.assertEqual(self.codes(report),{"DECLARED_SECONDS_INVALID","DECLARED_TIME_DECREASE"});self.assertEqual(report["findings"],[dict(code="DECLARED_TIME_DECREASE",source="input-0001",line=7)])
        self.fixture(records(event(raid_seconds=315360000),event(raid_seconds=315360000)));self.new_output("bound");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
    def test_drop_zero_unspecified_positive_are_separate_declarations(self):
        cases=((records(event()),0,0,"unspecified",None),(records(event("raid_end")),1,0,"unspecified",None),(records(event("raid_end",dropped_lines=0)),1,1,"declared","0"),(records(event("raid_end",dropped_lines=7)),1,1,"declared","7"))
        for index,(raw,ends,valid,state,declared) in enumerate(cases):
            self.fixture(raw);self.new_output(index);report=self.report();self.assertEqual(report["captures"][0]["dropped_data"],dict(end_rows=ends,valid_declarations=valid,invalid_declarations=0,state=state,declared_dropped_lines=declared))
            self.assertEqual(report["status"],"REVIEW_REQUIRED" if declared=="7" else "NO_SCOPE_FINDINGS")
    def test_multiple_end_rows_hold_drops_without_first_last_or_sum(self):
        pairs=((7,7),(7,9),(9,7),(0,0),(None,7),(7,None))
        for index,(first,last) in enumerate(pairs):
            self.fixture(records(event("raid_end",**({} if first is None else dict(dropped_lines=first))),event("raid_end",**({} if last is None else dict(dropped_lines=last)))))
            self.new_output(index);report=self.report();dropped=report["captures"][0]["dropped_data"]
            self.assertEqual(dropped,dict(end_rows=2,valid_declarations=int(first is not None)+int(last is not None),invalid_declarations=0,state="ambiguous_multiple_end_rows",declared_dropped_lines=None))
            self.assertEqual(self.codes(report),{"MULTIPLE_END_MARKERS"});self.assertEqual(report["findings"],[])
    def test_invalid_drop_types_and_bounds_do_not_create_a_numeric_winner(self):
        for index,value in enumerate((True,None,"3",3.0,-1,1000000000001)):
            self.fixture(records(event("raid_end",dropped_lines=value)));self.new_output(index);report=self.report()
            self.assertEqual(report["captures"][0]["dropped_data"],dict(end_rows=1,valid_declarations=0,invalid_declarations=1,state="invalid",declared_dropped_lines=None));self.assertEqual(self.codes(report),{"DROPPED_LINES_INVALID"})
        self.fixture(records(event("raid_end",dropped_lines=1000000000000)));self.new_output("bound");self.assertEqual(self.report()["captures"][0]["dropped_data"]["declared_dropped_lines"],"1000000000000")
        self.fixture(records(event("raid_end",dropped_lines=True),event("raid_end",dropped_lines=8)));self.new_output("mixed")
        report=self.report();self.assertEqual(report["captures"][0]["dropped_data"]["state"],"ambiguous_multiple_end_rows");self.assertEqual(self.codes(report),{"DROPPED_LINES_INVALID","MULTIPLE_END_MARKERS"})
    def test_repeated_markers_and_observations_are_not_unique_entities(self):
        repeated=event(player_count=5,bot_count=2)
        self.fixture(records(event("raid_start"),event("raid_start"),repeated,repeated,event("tracking_assigned"),event("tracking_assigned")))
        report=self.report();capture=report["captures"][0]
        self.assertEqual(capture["event_counts"],dict(raid_start=2,snapshot=2,tracking_assigned=2,raid_end=0));self.assertEqual(capture["populations"]["players"],population([5,5]));self.assertEqual(capture["populations"]["bots"],population([2,2]));self.assertEqual(self.codes(report),{"MULTIPLE_START_MARKERS"})
        self.assertFalse(any("unique" in key or "duration" in key for key in capture))
    def test_separate_files_are_not_pooled_deduplicated_or_time_compared(self):
        first=records(event(player_count=2,raid_seconds=10));second=records(event(player_count=8,raid_seconds=1))
        self.fixture(first,second,first);report=self.report(probe="audit")
        self.assertEqual(report["status"],"NO_SCOPE_FINDINGS");self.assertEqual(report["nonblank_records_observed"],3)
        self.assertEqual([c["populations"]["players"] for c in report["captures"]],[population([2]),population([8]),population([2])])
        self.assertEqual([c["declared_time"]["last_in_file_seconds"] for c in report["captures"]],["10","1","10"])
        self.assertEqual(report["sources"][0]["sha256"],report["sources"][2]["sha256"])
        self.inputs.reverse();self.new_output("reordered");again=self.report();self.assertEqual([r["sha256"] for r in again["sources"]],[sha(path.read_bytes()) for path in self.inputs])
    def test_malformed_json_rows_recover_without_duplicate_key_winners(self):
        bad=[b'{"type":"snapshot","type":"raid_end","payload":{}}',b'{"type":"snapshot","payload":{"player_count":1,"player_count":9}}',b'{"type":"snapshot","payload":{"raid_seconds":NaN}}',b'{"type":"snapshot","payload":{"raid_seconds":Infinity}}',b'{unfinished']
        self.fixture(b"\n".join(bad)+b"\n"+records(event(player_count=3)))
        report=self.report();capture=report["captures"][0]
        self.assertEqual((capture["nonblank_rows"],capture["decoded_rows"],capture["malformed_json_rows"],capture["accepted_events"]),(6,1,5,1))
        self.assertEqual(capture["populations"]["players"],population([3]));self.assertEqual(capture["event_counts"]["raid_end"],0)
        self.assertEqual(self.codes(report),{"DUPLICATE_JSON_KEY","JSON_NONFINITE_UNSUPPORTED","INVALID_JSON"})
    def test_envelope_unknown_types_and_extra_fields_keep_scope_explicit(self):
        invalid=(None,[],3,{},dict(type=3,payload={}),dict(type="",payload={}),dict(type="snapshot"),dict(type="snapshot",payload=None))
        extra=event(player_count=4,map="FICTIONAL_PRIVATE_MAP",private_payload="FICTIONAL_PRIVATE_PAYLOAD",tracking=dict(active_count=2,private_key="FICTIONAL_PRIVATE_TRACK"),line_of_sight=[dict(main_can_see_bot=True,private_key="FICTIONAL_PRIVATE_LOS")]);extra["private_root"]="FICTIONAL_PRIVATE_ROOT"
        self.fixture(records(*invalid,extra,event("FICTIONAL_PRIVATE_KIND")));report=self.report();capture=report["captures"][0]
        self.assertEqual((capture["invalid_envelope_rows"],capture["unsupported_event_rows"],capture["accepted_events"]),(8,1,1))
        self.assertEqual(capture["populations"]["players"],population([4]));self.assertEqual(self.codes(report),{"EVENT_ENVELOPE_INVALID","PAYLOAD_OBJECT_REQUIRED","ENVELOPE_FIELDS_UNSUPPORTED","PAYLOAD_FIELDS_UNSUPPORTED","TRACKING_FIELDS_UNSUPPORTED","LOS_FIELDS_UNSUPPORTED","EVENT_TYPE_UNSUPPORTED"})
        self.fixture(records(*invalid));self.new_output("none");self.assertIn("NO_SUPPORTED_EVENTS",self.codes(self.report()))
    def test_encoding_physical_controls_and_decoded_controls_have_distinct_results(self):
        for index,(raw,code) in enumerate(((b"\xff","UTF8_REQUIRED"),(b"\0","TEXT_CONTROL_UNSUPPORTED"),(b"a\rb","TEXT_CONTROL_UNSUPPORTED"),(chr(0x2028).encode(),"TEXT_CONTROL_UNSUPPORTED"),(chr(0x202e).encode(),"TEXT_CONTROL_UNSUPPORTED"))):
            self.fixture(raw);self.new_output(index);self.report(error=code);self.assertFalse(self.output.exists())
        for index,escape in enumerate((b"\\u0000",b"\\u2028",b"\\u2029",b"\\u202e")):
            self.fixture(b'{"type":"snapshot","payload":{"map":"'+escape+b'FICTIONAL_PRIVATE"}}\n');self.new_output("decoded"+str(index));report=self.report()
            self.assertEqual(report["captures"][0]["malformed_json_rows"],1);self.assertEqual(self.codes(report),{"JSON_TEXT_UNSUPPORTED","NO_SUPPORTED_EVENTS"})
    def test_bom_crlf_terminal_newlines_blanks_and_empty_capture_accounting(self):
        raw=records(event())
        for index,data in enumerate((raw,raw.rstrip(b"\n"),raw.replace(b"\n",b"\r\n"))):
            self.fixture(data);self.new_output(index);capture=self.report()["captures"][0]
            self.assertEqual((capture["physical_lines"],capture["nonblank_rows"],capture["blank_rows"]),(1,1,0))
        self.fixture(b"\xef\xbb\xbf"+raw+b" \t\n");self.new_output("extensions");report=self.report()
        self.assertEqual(self.codes(report),{"UTF8_BOM_EXTENSION","BLANK_RECORD_LINE"});self.assertEqual(report["captures"][0]["physical_lines"],2)
        for index,data in enumerate((b"",b"\xef\xbb\xbf",b"\n")):
            self.fixture(data);self.new_output("empty"+str(index));report=self.report();capture=report["captures"][0]
            self.assertEqual((capture["physical_lines"],capture["blank_rows"],capture["nonblank_rows"]),(int(data==b"\n"),int(data==b"\n"),0));self.assertIn("NO_SUPPORTED_EVENTS",self.codes(report))
            self.assertEqual(capture["populations"]["players"],population())
    def test_structure_string_and_exact_number_resource_limits(self):
        cases=((b"["*10+b"0"+b"]"*10,"JSON_STRUCTURE_LIMIT"),(json.dumps([0]*1000).encode(),"JSON_STRUCTURE_LIMIT"),(json.dumps({"map":"x"*1025}).encode(),"JSON_STRING_LIMIT"),(json.dumps({"k"*257:0}).encode(),"JSON_STRING_LIMIT"),(b"1"*25,"JSON_NUMBER_LIMIT"),(b"1e1001","JSON_NUMBER_LIMIT"),(b"1e-1001","JSON_NUMBER_LIMIT"),(b"0."+b"1"*63,"JSON_NUMBER_LIMIT"))
        for index,(raw,code) in enumerate(cases):
            self.fixture(raw);self.new_output(index);self.report(error=code);self.assertFalse(self.output.exists())
        self.fixture(records(event(map="x"*1024)));self.new_output("text-exact");self.assertEqual(self.report()["status"],"NO_SCOPE_FINDINGS")
        self.fixture(b'{"type":"snapshot","payload":{"raid_seconds":'+b"0."+b"1"*62+b'}}\n');self.new_output("number-exact")
        self.assertEqual(self.report()["captures"][0]["declared_time"]["last_in_file_seconds"],"0."+"1"*62)
    def test_file_bytes_physical_lines_input_count_and_total_limits(self):
        self.fixture(b" "*8192);self.assertIn("NO_SUPPORTED_EVENTS",self.codes(self.report()))
        self.fixture(b" "*8193);self.new_output("line-over");self.report(error="TEXT_LINE_LIMIT")
        self.fixture(b"\n"*20000);self.new_output("lines-over");self.report(error="TEXT_LINE_LIMIT")
        self.fixture(b" "*4095+b"\n");raw=self.inputs[0].read_bytes()*256;self.inputs[0].write_bytes(raw);self.new_output("bytes-exact");self.assertEqual(self.report()["sources"][0]["bytes"],1048576)
        with self.inputs[0].open("ab") as stream:stream.write(b" ")
        self.new_output("bytes-over");self.report(error="INPUT_BYTE_LIMIT")
        self.fixture(*(b"" for _ in range(33)));self.new_output("count-over");self.report(error="INPUT_COUNT_LIMIT")
        self.inputs.pop();self.new_output("count-exact");self.assertEqual(self.report()["selected_files"],32)
        self.fixture(*(raw for _ in range(5)));self.new_output("total-over");self.report(error="TOTAL_BYTE_LIMIT");self.assertFalse(self.output.exists())
    def test_record_and_collection_caps_are_global_and_fail_closed(self):
        raw=records(event(player_count=1));self.fixture(raw*4000);report=self.report();self.assertEqual(report["nonblank_records_observed"],4000);self.assertEqual(report["captures"][0]["populations"]["players"],population([1]*4000))
        self.fixture(raw*2000,raw*2001);self.new_output("global");self.report(error="TELEMETRY_RECORD_LIMIT")
        self.fixture(records(event("unknown"))*4000);self.new_output("coverage");self.report(error="RECORD_LIMIT")
        self.fixture(raw*2);self.new_output("lowered");self.report(probe='limit:{"MAX_RECORDS":1}',error="TELEMETRY_RECORD_LIMIT")
    def test_payload_privacy_no_details_and_selected_file_audit(self):
        private="FICTIONAL_PRIVATE</pre><script>never_execute</script>"
        self.fixture(records(event(player_count=2,map=private),event("tracking_assigned")),records(event(bot_count=3,map=private)))
        (self.work/"not-selected.jsonl").write_bytes(b"FICTIONAL_PRIVATE_NOT_SELECTED")
        report=self.report(probe="audit");self.assertEqual(report["status"],"NO_SCOPE_FINDINGS")
        for path in self.output.iterdir():
            self.assertNotIn(b"FICTIONAL_PRIVATE",path.read_bytes());self.assertNotIn(b"<script>",path.read_bytes());self.assertNotIn(b"never_execute",path.read_bytes())
        self.new_output("no-details");self.call(self.args()+["--include-details"],error="ARGUMENTS_INVALID")
        self.new_output("escaping");report=self.report(probe="scope_escape");self.assertEqual(report["scope"],'Fictional </pre><script>never_execute</script> & "quoted"')
        self.assertIn(b"&lt;script&gt;never_execute&lt;/script&gt;",(self.output/"report.html").read_bytes());self.assertNotIn(b"<script>",(self.output/"report.html").read_bytes())
    def test_source_hashes_manifests_order_and_no_overwrite(self):
        one=records(event(player_count=1));two=b"\xef\xbb\xbf"+records(event(bot_count=2)).replace(b"\n",b"\r\n")
        self.fixture(one,two);report=self.report();self.assertEqual([r["sha256"] for r in report["sources"]],[sha(one),sha(two)])
        self.assertEqual([row["path"] for row in json.loads((self.output/"MANIFEST.json").read_bytes())["files"]],["report.html","report.json"])
        self.report(error="OUTPUT_EXISTS");self.new_output("reverse");self.inputs.reverse();again=self.report();self.assertEqual([r["sha256"] for r in again["sources"]],[sha(two),sha(one)])
        for destination in (self.inputs[0],self.work,self.copy):
            args=self.args();args[-1]=destination;self.call(args,error="OUTPUT_EXISTS")
    def test_cli_arguments_local_paths_and_missing_parents_have_fixed_codes(self):
        for args in ([],["--file",self.inputs[0]],["--private-unknown=secret"],["--output",self.output]):self.call(args,error="ARGUMENTS_INVALID")
        for path,code in (("relative.jsonl","LOCAL_ABSOLUTE_PATH_REQUIRED"),(self.work/".."/"capture.jsonl","LOCAL_ABSOLUTE_PATH_REQUIRED"),("//fictional/share/capture.jsonl","LOCAL_ABSOLUTE_PATH_REQUIRED"),(str(self.inputs[0])+"\nprivate","INVALID_LOCAL_PATH"),(self.copy,"REGULAR_FILE_REQUIRED"),(self.work/"missing.jsonl","IO_OR_INPUT_ERROR")):
            self.call(["--file",path,"--output",self.output],error=code)
        for output,code in (("relative-report","LOCAL_ABSOLUTE_PATH_REQUIRED"),(self.work/"missing"/"report","IO_OR_INPUT_ERROR")):
            self.call(["--file",self.inputs[0],"--output",output],error=code)
        self.assertFalse(self.output.exists())
    def test_changed_short_read_partial_report_and_budget_failures(self):
        self.report(probe="changed_input",error="INPUT_CHANGED",ignore=self.inputs);self.assertFalse(self.output.exists())
        self.fixture(records(event()));self.report(probe="short_read",error="INPUT_CHANGED");self.assertFalse(self.output.exists())
        self.report(probe="manifest_failure",error="IO_OR_INPUT_ERROR");self.assertEqual({p.name for p in self.output.iterdir()},{"report.json","report.html"});self.report(error="OUTPUT_EXISTS")
        self.new_output("budget");self.report(probe='limit:{"MAX_REPORT":100}',error="REPORT_BYTE_LIMIT");self.assertFalse(self.output.exists())
    def test_duplicate_hardlink_inputs_and_hostile_imports_are_controlled(self):
        path=self.inputs[0];alias=self.work/"hardlink.jsonl";os.link(path,alias);self.assertTrue(path.samefile(alias))
        for second in (path,alias):self.call(["--file",path,"--file",second,"--output",self.output],error="DUPLICATE_INPUT_FILE")
        hostile=self.work/"hostile imports";hostile.mkdir()
        for name in ("sitecustomize.py","usercustomize.py","json.py","decimal.py"):(hostile/name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env=dict(self.env,PYTHONPATH=str(hostile),PYTHONHOME=str(hostile),PYTHONSTARTUP=str(hostile/"sitecustomize.py"));self.report(env=env)
    def test_native_symlink_inputs_and_output_parents(self):
        alias=self.work/"linked.jsonl";self.symlink(alias,self.inputs[0]);self.call(["--file",alias,"--output",self.output],error="LINKED_PATH_REJECTED")
        route=self.work/"linked directory";self.symlink(route,self.work,directory=True)
        self.call(["--file",route/self.inputs[0].name,"--output",self.output],error="LINKED_PATH_REJECTED")
        self.call(["--file",self.inputs[0],"--output",route/"new-report"],error="LINKED_PATH_REJECTED")
        dangling=self.work/"dangling report";self.symlink(dangling,self.work/"nonexistent")
        self.call(["--file",self.inputs[0],"--output",dangling],error="OUTPUT_EXISTS")
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
        sparse=self.work/"fictional sparse.jsonl"
        with sparse.open("wb") as stream:stream.truncate(1<<34)
        self.assertEqual(sparse.stat().st_size,1<<34);self.assertLess(sparse.stat().st_blocks*512,1<<20)
        self.call(["--file",sparse,"--output",self.output],error="INPUT_BYTE_LIMIT");self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
