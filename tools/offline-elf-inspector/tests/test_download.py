"""Independent consumers of copied ELF metadata tooling; no ELF is executed."""
import hashlib
import html
from html.parser import HTMLParser
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

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("elf_inspector.py", "examples/make_demo.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junctions_are_not_followed"
PROCESS_WINDOWS_REASON = "Native Windows junction fixture"
PROCESS_POSIX_ID = "test_download.Download.test_native_posix_special_files_are_not_opened"
PROCESS_POSIX_REASON = "Native POSIX FIFO and socket fixture"
PROCESS_ORACLE_ID = "test_download.Download.test_linux_compiler_metadata_matches_pinned_readelf_oracle"
PROCESS_ORACLE_REASON = "Linux GCC and readelf oracle fixture"
PROCESS_SYMLINK_ID = "test_download.Download.test_native_symlink_input_root_and_output_parents"
PROCESS_SYMLINK_REASON = "Native symlink privilege unavailable"
EDGE_STATUSES = ("unique_metadata_candidate", "ambiguous_candidates", "architecture_mismatch",
                 "object_type_mismatch", "unresolved_in_supplied_inputs", "path_dependency_not_resolved")
INTERPRETATION = "Candidates in explicit local inputs only. No loader, linker namespaces, symbol/ABI compatibility, dlopen or runtime success is verified."
FIXTURE = r'''
import importlib.metadata,json,struct,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]);sys.path.insert(0,str(base/'examples'))
import make_demo as d
assert Path(d.__file__).resolve()==base/'examples/make_demo.py'
assert Path(sys.modules['elf_inspector'].__file__).resolve()==base/'elf_inspector.py'
root=Path(sys.argv[2]);root.mkdir()
for name,spec in json.loads(sys.argv[3]).items():
 spec=dict(spec);tail=spec.pop('tail','').encode();padding=spec.pop('padding',0)
 object_type=spec.pop('object_type',3);raw=spec.pop('raw_hex',None);changes=spec.pop('changes',[])
 data=bytearray(bytes.fromhex(raw) if raw is not None else d.make_elf(**spec))
 if raw is None:struct.pack_into(('<' if spec.get('endian','little')=='little' else '>')+'H',data,16,object_type)
 for offset,value in changes:data[offset]=value
 data.extend(b'\0'*padding+tail)
 path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as stream:stream.write(data)
print(json.dumps({'status':'AUTHORED_METADATA_ONLY','files':len(json.loads(sys.argv[3]))}))
'''
PROBE = r'''
import argparse,builtins,errno,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import elf_inspector as e
assert Path(e.__file__).resolve()==base/'elf_inspector.py'
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import make_demo as d
 assert Path(d.__file__).resolve()==base/'examples/make_demo.py'
 assert d.ordinary is e.ordinary and e.VERSION=='1.1.0'
 print(json.dumps({'status':'COPIED_RUNTIME_AFFINITY','dependencies':0}));raise SystemExit(0)
elif kind in ('no_external','default_no_hints'):
 e.argparse.ArgumentParser(description=e.__doc__)  # Initialize the standard formatter before the audit hook.
 allowed={base/name for name in ('elf_inspector.py','examples/make_demo.py')}
 for index,value in enumerate(args):
  if value=='--root':allowed.update(p for p in Path(args[index+1]).rglob('*') if p.is_file() and not p.is_symlink())
  elif value=='--file':allowed.add(Path(args[index+1]))
 if '--output' in args:
  out=Path(args[args.index('--output')+1]);allowed.update(out/name for name in ('report.json','index.html','README.txt','MANIFEST.json'))
 def audit(event,values):
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open','ctypes.dlopen'):
   raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
  if event=='open' and not isinstance(values[0],int):assert Path(values[0]) in allowed,'UNEXPECTED_FILE_OR_REFERENCE_OPEN'
 sys.addaudithook(audit)
 if kind=='default_no_hints':
  def disabled(*unused):raise AssertionError('DEFAULT_HINT_SCAN_CALLED')
  e.scan_runtime_hints=disabled
elif kind.startswith('limit:'):
 for name,value in json.loads(kind[6:]).items():
  assert name in {'MAX_METADATA','MAX_HASH','MAX_REPORT','MAX_HINT_TOTAL_BYTES','MAX_HINTS_TOTAL'}
  setattr(e,name,value)
elif kind=='manifest_failure':
 # Path.open uses io.open, so preserve the exact writer while injecting only its final member.
 original_path_open=Path.open
 def path_open(path,*a,**kw):
  if path.name=='MANIFEST.json' and a and a[0]=='xb':raise OSError('FICTIONAL_PRIVATE_OUTPUT_DETAIL')
  return original_path_open(path,*a,**kw)
 Path.open=path_open
elif kind=='changed_during_parse':
 original=e.parse_stream
 def changed(stream,size,budget):
  result=original(stream,size,budget);path=Path(stream.name)
  with path.open('ab') as other:other.write(b'\0')
  return result
 e.parse_stream=changed
elif kind=='short_read':
 original=e.Reader.read
 def short(reader,offset,length):
  if length>0:raise e.ParseError('ELF_TRUNCATED_DURING_READ')
  return original(reader,offset,length)
 e.Reader.read=short
elif kind=='cli_interrupt':
 def interrupt(*unused):raise KeyboardInterrupt
 e.parse_stream=interrupt
elif kind=='library_interrupt':
 source=Path(args[0]);before=source.read_bytes();handles=[]
 def interrupt(stream,*unused):handles.append(stream.fileno());raise KeyboardInterrupt
 e.parse_stream=interrupt
 try:e.inspect_file(source,e.Budget(e.Limits()))
 except KeyboardInterrupt:pass
 else:raise AssertionError('LIBRARY_INTERRUPT_MUST_PROPAGATE')
 assert len(handles)==1
 try:os.fstat(handles[0])
 except OSError as error:assert error.errno==errno.EBADF
 else:raise AssertionError('INTERRUPTED_DESCRIPTOR_STILL_OPEN')
 assert source.read_bytes()==before
 print(json.dumps({'status':'LIBRARY_INTERRUPT_PROPAGATED','descriptor_closed':True}));raise SystemExit(0)
else:raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
raise SystemExit(e.cli(args))
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n").encode()


class StaticHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.csp = []
    def handle_starttag(self, tag, attributes):
        assert tag in {"html", "head", "meta", "title", "style", "body", "main", "h1", "h2", "p", "nav", "a",
                       "div", "strong", "details", "summary", "table", "thead", "tbody", "tr", "th", "td"}
        for key, value in attributes:
            assert not key.lower().startswith("on") and key not in {"src", "srcdoc"}
            if key == "href":
                assert tag == "a" and value in {"#dependencies", "#metadata", "#coverage"}
            if key == "http-equiv":
                assert value == "Content-Security-Policy"
                self.csp.append(dict(attributes)["content"])
        self.tags.append(tag)
    def handle_pi(self, data):
        raise AssertionError("REPORT_PROCESSING_INSTRUCTION")


class Download(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.python_binary = Path(sys._base_executable).resolve()
        cls.python_pin = sha(cls.python_binary.read_bytes())
        cls.python_bytes = cls.python_binary.stat().st_size
        cls.python_version = ".".join(map(str, sys.version_info[:3]))
        if (cls.python_pin != os.environ["OUTLANDS_TEST_PYTHON_SHA256"] or
                cls.python_version != os.environ["OUTLANDS_TEST_PYTHON_VERSION"]):
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
        self.temp = tempfile.TemporaryDirectory(prefix="elf-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.copy = self.work / "copied runtime"
        self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT / name).read_bytes()
            target = self.copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            self.pins[name] = sha(raw)
        self.input = self.work / "fictional inputs"
        self.output = self.work / "new report"
        self.env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
    def runtime_preserved(self):
        self.assertEqual({p.relative_to(self.copy).as_posix() for p in self.copy.rglob("*") if p.is_file()}, set(RUNTIME))
        self.assertEqual({name: sha((self.copy / name).read_bytes()) for name in RUNTIME}, self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
    def snapshot(self):
        result = {}
        def walk(folder):
            for path in folder.iterdir():
                key = path.relative_to(self.work).as_posix()
                info = path.lstat()
                if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                    result[key] = ("LINK", os.readlink(path))
                elif stat.S_ISDIR(info.st_mode):
                    result[key] = ("DIRECTORY",)
                    walk(path)
                elif stat.S_ISREG(info.st_mode):
                    result[key] = (sha(path.read_bytes()), info.st_size, info.st_mtime_ns,
                                   info.st_ctime_ns, info.st_ino, info.st_nlink)
                else:
                    result[key] = ("SPECIAL", info.st_mode)
        walk(self.work)
        return result
    def run_child(self, command, *, timeout=90, env=None):
        return subprocess.run([sys.executable, "-I", "-B", "-W", "error", *map(str, command)],
                              cwd=self.work, env=self.env if env is None else env, stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=timeout)
    def fixture(self, members, name=None):
        root = self.input if name is None else self.work / name
        done = self.run_child(["-c", FIXTURE, self.copy, root, json.dumps(members)])
        self.assertEqual((done.returncode, done.stderr), (0, b""), done.stderr.decode(errors="replace"))
        self.assertEqual(done.stdout, json.dumps(dict(status="AUTHORED_METADATA_ONLY", files=len(members))).encode() + NEWLINE)
        self.runtime_preserved()
        return root
    def call(self, args, *, probe=None, code=None, error=None, output=None, allow=(), ignore=(), env=None):
        before = self.snapshot()
        command = ["-c", PROBE, self.copy, probe] if probe else [self.copy / "elf_inspector.py"]
        done = self.run_child([*command, *args], env=env)
        if error:
            code = 130 if error == "PARTIAL_NEW_OUTPUT_MAY_REMAIN" else 1
            wanted = dict(status="CANCELLED" if code == 130 else "ERROR", code=error)
            self.assertEqual(done.stdout, b"")
            self.assertEqual(done.stderr, json.dumps(wanted).encode() + NEWLINE)
            value = wanted
        else:
            self.assertEqual(done.stderr, b"", done.stderr.decode(errors="replace"))
            value = json.loads(done.stdout)
            if probe in {"affinity", "library_interrupt"}:
                wanted = (dict(status="COPIED_RUNTIME_AFFINITY", dependencies=0) if probe == "affinity" else
                          dict(status="LIBRARY_INTERRUPT_PROPAGATED", descriptor_closed=True))
                self.assertEqual(value, wanted)
                self.assertEqual(done.stdout, json.dumps(wanted).encode() + NEWLINE)
                code = 0
            elif output is None:
                self.check_schema(value)
                self.assertEqual(done.stdout, encoded(value).replace(b"\n", NEWLINE))
                code = 2 if value["status"] == "REVIEW_REQUIRED" else 0
            else:
                report = self.check_report(output)
                self.assertEqual(value, dict(status=report["status"], report_files=4, summary=report["summary"]))
                self.assertEqual(done.stdout, json.dumps(value).encode() + NEWLINE)
                value = report
                code = 2 if value["status"] == "REVIEW_REQUIRED" else 0
        self.assertEqual(done.returncode, code, (done.stdout + done.stderr).decode(errors="replace")[:3000])
        for private in (str(self.work).encode(), b"FICTIONAL_PRIVATE", b"Traceback"):
            self.assertNotIn(private, done.stdout + done.stderr)
        after = self.snapshot()
        ignored = {Path(path).relative_to(self.work).as_posix() for path in ignore}
        self.assertEqual({k: v for k, v in before.items() if k not in ignored},
                         {k: after.get(k) for k in before if k not in ignored})
        for key in after.keys() - before.keys():
            path = self.work / key
            self.assertTrue(any(path == Path(root) or path.is_relative_to(root) for root in allow), "Unexpected application write: " + key)
        self.runtime_preserved()
        return value
    def check_schema(self, report):
        self.assertEqual(set(report), {"schema", "tool_version", "status", "interpretation", "limits", "summary",
                                     "roots", "entry_files", "files", "dependencies", "issues"} | ({"runtime_hints"} if "runtime_hints" in report else set()))
        self.assertEqual(report["schema"], "outlands-offline-elf-dependencies/1")
        self.assertEqual(report["tool_version"], "1.1.0")
        self.assertEqual(report["interpretation"], INTERPRETATION)
        self.assertEqual(report["files"], sorted(report["files"], key=lambda row: row["id"]))
        self.assertEqual(report["entry_files"], sorted(set(report["entry_files"])))
        self.assertEqual(report["summary"]["elf_files"], len(report["files"]))
        self.assertEqual(report["summary"]["dependency_edges"], len(report["dependencies"]))
        self.assertEqual(report["summary"]["issue_count"], len(report["issues"]) + report["summary"]["issues_omitted"])
        for status in EDGE_STATUSES:
            self.assertEqual(report["summary"][status], sum(edge["status"] == status for edge in report["dependencies"]))
        review = bool(report["issues"] or report["summary"]["issues_omitted"] or any(edge["status"] != EDGE_STATUSES[0] for edge in report["dependencies"]))
        self.assertEqual(report["status"], "REVIEW_REQUIRED" if review else "NO_SCOPE_FINDINGS")
        self.assertNotIn(str(self.work), json.dumps(report))
    def check_report(self, output):
        self.assertEqual({p.name for p in output.iterdir()}, {"report.json", "index.html", "README.txt", "MANIFEST.json"})
        raw = (output / "report.json").read_bytes()
        report = json.loads(raw)
        self.check_schema(report)
        self.assertEqual(raw, encoded(report))
        markup = (output / "index.html").read_bytes()
        parsed = StaticHTML()
        parsed.feed(markup.decode()); parsed.close()
        self.assertEqual(parsed.tags.count("html"), 1)
        self.assertEqual(parsed.csp, ["default-src 'none';style-src 'unsafe-inline';base-uri 'none';form-action 'none'"])
        members = {name: (output / name).read_bytes() for name in ("report.json", "index.html", "README.txt")}
        expected = dict(schema="outlands-elf-report-files/1", files=[dict(path=name, bytes=len(data), sha256=sha(data)) for name, data in sorted(members.items())])
        self.assertEqual((output / "MANIFEST.json").read_bytes(), encoded(expected))
        self.assertIn(b"No inspected binaries are included.", members["README.txt"])
        return report
    def report(self, args, **kwargs):
        return self.call([*args, "--output", self.output], output=self.output, allow=[self.output], **kwargs)
    def issues(self, report):
        return {row["code"] for row in report["issues"]}
    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314 and os.environ.get("OUTLANDS_ELF_REQUIRE_LINKS") != "1":
                self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_copied_runtime_demo_affinity_version_and_help(self):
        self.call([], probe="affinity")
        done = self.run_child([self.copy / "elf_inspector.py", "--version"])
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, b"1.1.0" + NEWLINE, b""))
        done = self.run_child([self.copy / "elf_inspector.py", "--help"])
        self.assertEqual((done.returncode, done.stderr), (0, b""))
        for flag in (b"--root", b"--file", b"--runtime-hints", b"--sha256"):
            self.assertIn(flag, done.stdout)

    def test_demo_cli_clean_mixed_hints_and_new_only_destination(self):
        for clean in (False, True):
            root = self.work / ("clean demo" if clean else "mixed demo")
            args = [self.copy / "examples/make_demo.py", "--destination", root, "--runtime-hints"] + (["--clean"] if clean else [])
            before = self.snapshot()
            done = self.run_child(args)
            wanted = dict(files=4 if clean else 7, fixture="clean" if clean else "mixed", machine_code=False)
            self.assertEqual((done.returncode, done.stderr, done.stdout), (0, b"", json.dumps(wanted).encode() + NEWLINE))
            self.assertEqual({k: self.snapshot().get(k) for k in before}, before)
            report = self.call(["--root", root, "--runtime-hints"])
            self.assertEqual(report["status"], "NO_SCOPE_FINDINGS" if clean else "REVIEW_REQUIRED")
            self.assertEqual(report["summary"]["elf_files"], 3 if clean else 6)
            # Declared library strings are observations too, in addition to the three appended tokens.
            self.assertEqual(report["runtime_hints"]["observations"], 8 if clean else 14)
            before = self.snapshot(); done = self.run_child(args)
            self.assertEqual((done.returncode, done.stdout), (1, b""))
            self.assertEqual(done.stderr, b"Could not create demo; use a new local directory with an existing parent." + NEWLINE)
            self.assertEqual(self.snapshot(), before)

    def test_all_four_class_endian_formats_and_static_metadata(self):
        members = {str(bits) + endian + ".elf": dict(bits=bits, endian=endian, soname="fixture.so", rpath="/fictional/rpath", runpath="$ORIGIN/lib", interpreter="/fictional/linker") for bits in (32, 64) for endian in ("little", "big")}
        self.fixture(members)
        report = self.call(["--root", self.input])
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        self.assertEqual({(f["class"], f["endian"]) for f in report["files"]}, {(32, "little"), (32, "big"), (64, "little"), (64, "big")})
        for item in report["files"]:
            self.assertEqual((item["type"], item["metadata"], item["rpath"], item["runpath"], item["interpreter"]), ("DYN", "dynamic_segment", "/fictional/rpath", "$ORIGIN/lib", "/fictional/linker"))

    def test_default_mode_does_not_read_optional_hint_payload(self):
        self.fixture({"entry.elf": dict(tail="\u0000liboptional.so\u0000/vendor/etc/fictional.xml\u0000")})
        report = self.call(["--root", self.input], probe="default_no_hints")
        self.assertNotIn("runtime_hints", report)
        self.assertNotIn("runtime_hint_scan", report["files"][0])
        self.assertEqual(report["dependencies"], [])
        self.assertEqual(report["summary"]["hash_bytes_read"], 0)

    def test_unique_soname_candidates_follow_cycle_once(self):
        self.fixture({"entry.elf": dict(needed=["liba.so"]), "a.bin": dict(soname="liba.so", needed=["libb.so"]), "b.bin": dict(soname="libb.so", needed=["liba.so"])})
        report = self.call(["--root", self.input, "--file", self.input / "entry.elf"])
        self.assertEqual((report["summary"]["visited_in_graph"], report["summary"]["dependency_edges"]), (3, 3))
        self.assertTrue(all(e["status"] == "unique_metadata_candidate" and e["candidate_count"] == 1 for e in report["dependencies"]))
        self.assertEqual(report["entry_files"], ["selected-1/entry.elf"])

    def test_identical_ambiguous_candidates_never_choose_and_display_is_bounded(self):
        members = {"entry.elf": dict(needed=["libsame.so"])}
        members.update({"candidate-%02d.bin" % n: dict(soname="libsame.so", needed=["not-followed.so"]) for n in range(19)})
        self.fixture(members)
        report = self.call(["--root", self.input, "--file", self.input / "entry.elf"])
        edge, = report["dependencies"]
        self.assertEqual((edge["status"], edge["candidate"], edge["candidate_count"], len(edge["candidates"]), edge["candidates_omitted"]), ("ambiguous_candidates", None, 19, 16, 3))
        self.assertEqual(report["summary"]["visited_in_graph"], 1)
        self.assertEqual(len({sha((self.input / ("candidate-%02d.bin" % n)).read_bytes()) for n in range(19)}), 1)

    def test_class_endian_and_machine_mismatches_are_metadata_findings(self):
        self.fixture({"entry.elf": dict(needed=["class.so", "endian.so", "machine.so"]), "class.so": dict(bits=32), "endian.so": dict(endian="big"), "machine.so": dict(machine=62)})
        report = self.call(["--root", self.input, "--file", self.input / "entry.elf"])
        self.assertEqual(len(report["dependencies"]), 3)
        self.assertTrue(all(edge["status"] == "architecture_mismatch" and edge["candidate"] is None for edge in report["dependencies"]))

    def test_exec_candidate_is_not_a_shared_library_and_static_exec_is_inspected(self):
        self.fixture({"entry.elf": dict(needed=["program.so"]), "program.so": dict(object_type=2, dynamic=False)})
        report = self.call(["--root", self.input, "--file", self.input / "entry.elf"])
        self.assertEqual(report["dependencies"][0]["status"], "object_type_mismatch")
        candidate = next(f for f in report["files"] if f["name"] == "program.so")
        self.assertEqual((candidate["type"], candidate["metadata"]), ("EXEC", "no_dynamic_segment"))

    def test_path_dependencies_case_and_absent_names_never_open_external_paths(self):
        self.fixture({"entry.elf": dict(needed=["../external.so", "C:\\fictional\\library.so", "Case.so", "absent.so"]), "case.so": {}, "external.so": {}})
        (self.work / "external.so").write_bytes(b"fictional outside-root reference must stay unopened")
        report = self.call(["--root", self.input, "--file", self.input / "entry.elf"], probe="no_external")
        edges = {e["needed"]: e for e in report["dependencies"]}
        self.assertEqual(edges["../external.so"]["status"], "path_dependency_not_resolved")
        self.assertEqual(edges["C:\\fictional\\library.so"]["status"], "path_dependency_not_resolved")
        self.assertEqual(edges["Case.so"]["status"], "unresolved_in_supplied_inputs")
        self.assertEqual(edges["absent.so"]["candidates"], [])

    def test_selected_entry_only_and_root_deduplication_are_explicit(self):
        self.fixture({"entry.elf": dict(needed=["sibling.so"]), "sibling.so": {}})
        only = self.call(["--file", self.input / "entry.elf"])
        self.assertEqual((len(only["files"]), only["roots"], only["summary"]["directory_entries"]), (1, [], 0))
        self.assertEqual(only["dependencies"][0]["status"], "unresolved_in_supplied_inputs")
        rooted = self.call(["--file", self.input / "entry.elf", "--root", self.input])
        self.assertEqual((rooted["summary"]["files_examined"], len(rooted["files"])), (2, 2))
        self.assertEqual(rooted["dependencies"][0]["status"], "unique_metadata_candidate")

    def test_disjoint_root_selection_and_invalid_bounds_have_fixed_errors(self):
        self.fixture({"sub/entry.elf": {}})
        cases = [([], "SELECT_AT_LEAST_ONE_ROOT_OR_FILE"), (["--root", self.input, "--root", self.input / "sub"], "ROOTS_MUST_BE_DISJOINT"), (["--root", self.input, "--root", self.input], "ROOTS_MUST_BE_DISJOINT"), (["--root", self.input / "sub/entry.elf"], "ROOT_MUST_BE_DIRECTORY")]
        cases += [(["--file", self.input / "sub/entry.elf", flag, str(value)], "INVALID_SCAN_LIMIT") for flag, value in (("--max-files", 0), ("--max-entries", 100001), ("--max-depth", 65), ("--seconds", 301))]
        cases.append((["--root", self.input] * 9, "TOO_MANY_ROOTS_OR_SELECTED_FILES"))
        cases.append((["--file", self.input / "sub/entry.elf"] * 33, "TOO_MANY_ROOTS_OR_SELECTED_FILES"))
        for args, code in cases:
            with self.subTest(code=code, args=len(args)):
                self.call(args, error=code)

    def test_nonelf_malformed_headers_and_strings_report_incomplete_coverage(self):
        self.fixture({"ordinary.txt": dict(raw_hex=b"ordinary text".hex()), "truncated.elf": dict(raw_hex=b"\x7fELF".hex()), "bad-class.elf": dict(changes=[[4, 0]]), "invalid-utf8.elf": dict(needed=["liba.so"], changes=[[577, 255]])})
        report = self.call(["--root", self.input, "--runtime-hints"])
        self.assertEqual(report["summary"]["non_elf_ignored"], 1)
        self.assertEqual(report["summary"]["elf_files"], 0)
        self.assertIn("NO_SUPPORTED_ELF_FILES", self.issues(report))
        self.assertGreaterEqual(report["summary"]["issue_count"], 4)
        selected = self.call(["--file", self.input / "ordinary.txt"])
        self.assertIn("SELECTED_FILE_NOT_ELF", self.issues(selected))

    def test_hashes_cover_exact_source_bytes_with_separate_read_budget(self):
        self.fixture({"entry.elf": dict(tail="\u0000unparsed-trailing-bytes\u0000")})
        plain = self.call(["--root", self.input])
        hashed = self.call(["--root", self.input, "--sha256"])
        item, = hashed["files"]
        raw = (self.input / "entry.elf").read_bytes()
        self.assertEqual((item["sha256"], item["bytes"], hashed["summary"]["hash_bytes_read"]), (sha(raw), len(raw), len(raw)))
        self.assertNotIn("sha256", plain["files"][0])
        self.assertEqual(plain["summary"]["metadata_bytes_read"], hashed["summary"]["metadata_bytes_read"])

    def test_hint_tokens_offsets_duplicates_and_interpretation_are_text_only(self):
        tail = b"\0liboptional.so.2\0liboptional.so.2\0/vendor/etc/fictional.xml\0/vendor/firmware/fictional.bin\0"
        self.fixture({"entry.elf": dict(tail=tail.decode())})
        report = self.call(["--root", self.input, "--runtime-hints"])
        item, = report["files"]; scan = item["runtime_hint_scan"]
        observations = {h["text"]: h for h in scan["observations"]}
        raw = (self.input / "entry.elf").read_bytes()
        self.assertEqual(observations["liboptional.so.2"], dict(kind="library_text", text="liboptional.so.2", first_offset=raw.index(b"liboptional.so.2"), occurrences=2))
        self.assertIn("/vendor/etc/fictional.xml", observations)
        self.assertIn("/vendor/firmware/fictional.bin", observations)
        self.assertEqual((scan["coverage"], scan["bytes_scanned"], report["dependencies"]), ("complete_ascii_scan", len(raw), []))
        self.assertIn("do not prove dependencies", report["runtime_hints"]["interpretation"])

    def test_matching_hint_library_is_never_a_dependency_or_external_read(self):
        self.fixture({"entry.elf": dict(tail="\u0000liboptional.so\u0000/vendor/etc/never-open.xml\u0000"), "liboptional.so": dict(needed=["unvisited.so"])})
        report = self.report(["--root", self.input, "--file", self.input / "entry.elf", "--runtime-hints"], probe="no_external")
        self.assertEqual(report["dependencies"], [])
        self.assertEqual(report["summary"]["visited_in_graph"], 1)
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")

    def test_hint_chunk_boundary_nonascii_and_control_separators(self):
        self.fixture({"entry.elf": {}})
        path = self.input / "entry.elf"
        raw = path.read_bytes()
        start = 65536 - 5
        path.write_bytes(raw + b"\0" * (start - len(raw)) + b"libboundary.so.7\0\xfflibnext.so\x01")
        report = self.call(["--file", path, "--runtime-hints"])
        found = {x["text"]: x for x in report["files"][0]["runtime_hint_scan"]["observations"]}
        self.assertEqual(found["libboundary.so.7"]["first_offset"], start)
        self.assertEqual(found["libnext.so"]["occurrences"], 1)

    def test_actual_eight_mib_hint_byte_cap_drops_partial_token(self):
        self.fixture({"entry.elf": {}})
        path = self.input / "entry.elf"; raw = path.read_bytes(); cap = 8 * 1024 * 1024
        path.write_bytes(raw + b"\0" * (cap - 5 - len(raw)) + b"libcut.so.9\0")
        report = self.call(["--file", path, "--runtime-hints"])
        scan = report["files"][0]["runtime_hint_scan"]
        self.assertEqual((scan["bytes_scanned"], scan["coverage"], scan["reasons"]), (cap, "partial_ascii_scan", ["PER_FILE_BYTE_LIMIT"]))
        self.assertEqual(scan["observations"], [])
        self.assertIn("RUNTIME_HINT_PER_FILE_BYTE_LIMIT", self.issues(report))

    def test_actual_hint_string_and_observation_caps_are_visible(self):
        tail = "\u0000" + "x" * 1025 + "\u0000" + "\u0000".join("libfixture%03d.so" % n for n in range(130)) + "\u0000"
        self.fixture({"entry.elf": dict(tail=tail)})
        report = self.call(["--file", self.input / "entry.elf", "--runtime-hints"])
        scan = report["files"][0]["runtime_hint_scan"]
        self.assertEqual((len(scan["observations"]), scan["overlong_ascii_runs_omitted"]), (128, 1))
        self.assertEqual(scan["reasons"], ["FILE_HINT_COUNT_LIMIT", "STRING_LENGTH_LIMIT"])
        self.assertEqual(report["runtime_hints"]["observation_slots_used"], 128)

    def test_controlled_metadata_hash_hint_and_report_budget_boundaries(self):
        self.fixture({"entry.elf": dict(tail="\u0000libone.so\u0000libtwo.so\u0000")})
        for constant, args, issue in (("MAX_METADATA", [], "METADATA_BYTE_BUDGET_REACHED"), ("MAX_HASH", ["--sha256"], "HASH_BYTE_BUDGET_REACHED")):
            report = self.call(["--file", self.input / "entry.elf", *args], probe="limit:" + json.dumps({constant: 1}))
            self.assertIn(issue, self.issues(report))
        report = self.call(["--file", self.input / "entry.elf", "--runtime-hints"], probe='limit:{"MAX_HINT_TOTAL_BYTES":1}')
        self.assertIn("RUNTIME_HINT_GLOBAL_BYTE_LIMIT", self.issues(report))
        report = self.call(["--file", self.input / "entry.elf", "--runtime-hints"], probe='limit:{"MAX_HINTS_TOTAL":1}')
        self.assertIn("RUNTIME_HINT_GLOBAL_HINT_COUNT_LIMIT", self.issues(report))
        self.call(["--file", self.input / "entry.elf"], probe='limit:{"MAX_REPORT":1}', error="JSON_REPORT_SIZE_LIMIT")

    def test_file_entry_and_depth_scan_caps_preserve_partial_results(self):
        self.fixture({"entry.elf": {}, "sub/deeper/second.elf": {}})
        limited = self.call(["--file", self.input / "entry.elf", "--root", self.input, "--max-files", "1"])
        self.assertEqual(limited["summary"]["elf_files"], 1)
        self.assertIn("FILE_COUNT_LIMIT", self.issues(limited))
        entries = self.call(["--root", self.input, "--max-entries", "1"])
        self.assertIn("ENTRY_COUNT_LIMIT", self.issues(entries))
        depth = self.call(["--root", self.input, "--max-depth", "1"])
        self.assertIn("DEPTH_LIMIT", self.issues(depth))

    def test_report_four_files_independent_hashes_static_html_and_escaping(self):
        token = 'lib<fictional&"quoted>.so'
        self.fixture({"entry.elf": dict(needed=[token], soname=token, interpreter='/fictional/<linker>&"', runpath='<img src=x onerror=fictional>')})
        report = self.report(["--root", self.input, "--sha256"])
        self.assertEqual(report["dependencies"][0]["needed"], token)
        markup = (self.output / "index.html").read_text()
        self.assertIn(html.escape(token, quote=True), markup)
        self.assertNotIn("<img", markup)
        self.assertNotIn("<script", markup)

    def test_existing_output_inside_root_and_missing_parent_never_overwrite(self):
        self.fixture({"entry.elf": {}})
        self.output.mkdir(); (self.output / "sentinel").write_bytes(b"fictional retained output")
        self.call(["--root", self.input, "--output", self.output], error="OUTPUT_MUST_BE_NEW_DIRECTORY")
        self.call(["--root", self.input, "--output", self.input / "report"], error="OUTPUT_MUST_BE_OUTSIDE_SCAN_ROOTS")
        self.call(["--root", self.input, "--output", self.work / "missing/report"], error="INPUT_OR_PARENT_NOT_FOUND")
        self.assertFalse((self.input / "report").exists())

    def test_failed_final_manifest_write_retains_exact_partial_new_output(self):
        self.fixture({"entry.elf": {}})
        self.call(["--root", self.input, "--output", self.output], probe="manifest_failure", error="FILESYSTEM_OPERATION_FAILED_PARTIAL_NEW_OUTPUT_MAY_REMAIN", allow=[self.output])
        self.assertEqual({p.name for p in self.output.iterdir()}, {"report.json", "index.html", "README.txt"})
        report = json.loads((self.output / "report.json").read_bytes())
        self.check_schema(report)
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        self.call(["--root", self.input, "--output", self.output], error="OUTPUT_MUST_BE_NEW_DIRECTORY")

    def test_observed_source_mutation_and_short_reads_discard_metadata(self):
        self.fixture({"entry.elf": {}})
        path = self.input / "entry.elf"; before = path.read_bytes()
        changed = self.call(["--file", path], probe="changed_during_parse", ignore=[path])
        self.assertIn("FILE_CHANGED_DURING_READ", self.issues(changed))
        self.assertEqual(changed["files"], [])
        self.assertEqual(path.read_bytes(), before + b"\0")
        short = self.call(["--file", path], probe="short_read")
        self.assertIn("ELF_TRUNCATED_DURING_READ", self.issues(short))
        self.assertEqual(short["files"], [])

    def test_interruption_returns_cancelled_and_library_closes_descriptor(self):
        self.fixture({"entry.elf": {}})
        path = self.input / "entry.elf"
        self.call(["--file", path, "--output", self.output], probe="cli_interrupt", error="PARTIAL_NEW_OUTPUT_MAY_REMAIN")
        self.assertFalse(self.output.exists())
        self.call([path], probe="library_interrupt")

    def test_native_symlink_input_root_and_output_parents(self):
        self.fixture({"entry.elf": {}})
        linked = self.work / "linked.elf"
        self.symlink(linked, self.input / "entry.elf")
        self.call(["--file", linked], error="LINK_OR_REPARSE_PATH_UNSUPPORTED")
        directory = self.work / "linked root"
        self.symlink(directory, self.input, True)
        self.call(["--root", directory], error="LINK_OR_REPARSE_PATH_UNSUPPORTED")
        report = self.call(["--root", self.work])
        self.assertIn("LINK_OR_REPARSE_SKIPPED", self.issues(report))
        self.call(["--file", self.input / "entry.elf", "--output", directory / "new report"], error="LINK_OR_REPARSE_PATH_UNSUPPORTED")

    @unittest.skipUnless(os.name == "nt", PROCESS_WINDOWS_REASON)
    def test_native_windows_junctions_are_not_followed(self):
        self.fixture({"entry.elf": {}})
        junction = self.work / "junction"
        done = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(self.input)], capture_output=True, timeout=15)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace"))
        self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
        self.call(["--root", junction], error="LINK_OR_REPARSE_PATH_UNSUPPORTED")
        self.call(["--file", self.input / "entry.elf", "--output", junction / "new report"], error="LINK_OR_REPARSE_PATH_UNSUPPORTED")
        report = self.call(["--root", self.work])
        self.assertIn("LINK_OR_REPARSE_SKIPPED", self.issues(report))

    @unittest.skipUnless(os.name != "nt", PROCESS_POSIX_REASON)
    def test_native_posix_special_files_are_not_opened(self):
        self.fixture({"entry.elf": {}})
        os.mkfifo(self.input / "fictional.fifo")
        connection = socket.socket(socket.AF_UNIX)
        connection.bind(str(self.input / "fictional.sock")); self.addCleanup(connection.close)
        report = self.call(["--root", self.input])
        self.assertEqual([i["code"] for i in report["issues"]].count("SPECIAL_FILE_SKIPPED"), 2)
        self.call(["--file", self.input / "fictional.fifo"], error="SELECTED_FILE_MUST_BE_REGULAR")

    def test_hostile_python_environment_relative_paths_and_hardlinks(self):
        self.fixture({"entry.elf": {}})
        hostile = self.work / "hostile imports"; hostile.mkdir()
        for name in ("sitecustomize.py", "usercustomize.py", "struct.py", "json.py"):
            (hostile / name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env = dict(self.env, PYTHONPATH=str(hostile), PYTHONSTARTUP=str(hostile / "sitecustomize.py"), PYTHONINSPECT="1", PYTHONHOME=str(hostile))
        relative = self.call(["--file", "fictional inputs/entry.elf"], env=env)
        self.assertEqual(relative["status"], "NO_SCOPE_FINDINGS")
        alias = self.input / "hardlink.elf"; os.link(self.input / "entry.elf", alias)
        report = self.call(["--root", self.input, "--sha256"])
        self.assertEqual(report["summary"]["elf_files"], 2)
        self.assertEqual(len({item["sha256"] for item in report["files"]}), 1)
        self.call(["--file", self.work / "FICTIONAL_PRIVATE_missing"], error="INPUT_OR_PARENT_NOT_FOUND")

    @unittest.skipUnless(sys.platform == "linux", PROCESS_ORACLE_REASON)
    def test_linux_compiler_metadata_matches_pinned_readelf_oracle(self):
        pins = json.loads(Path(os.environ["OUTLANDS_ELF_ORACLE_REPORT"]).read_bytes())
        self.assertEqual((pins["schema"], pins["status"], pins["platform"], pins["oracle_required"]), (1, "PASS", "linux", True))
        self.assertEqual(pins["oracle_lock_sha256"], sha((ROOT / "ORACLE-LOCK.json").read_bytes()))
        self.assertEqual(pins["preparation_helper_sha256"], sha((ROOT / "packaging/prepare_oracle.py").read_bytes()))
        for flag in ("application_uses_oracle", "fixture_binaries_executed", "binary_reproducibility_claimed", "global_install_performed"):
            self.assertIs(pins[flag], False)
        tools = {name: Path(os.environ["OUTLANDS_ELF_" + name.upper()]).resolve() for name in ("gcc", "readelf")}
        for name, tool in tools.items():
            self.assertTrue(tool.is_absolute() and tool.is_file())
            self.assertEqual((tool.name, tool.stat().st_size, sha(tool.read_bytes())), (pins["tools"][name]["basename"], pins["tools"][name]["bytes"], pins["tools"][name]["sha256"]))
            self.assertEqual(pins["tools"][name]["version"], "15.2.0" if name == "gcc" else "2.46")
        self.input.mkdir(); source = self.input / "fictional.c"; binary = self.input / "libfictional.so"
        source.write_text("int fictional_value(void) { return 7; }\n")
        done = subprocess.run([str(tools["gcc"]), "-shared", "-fPIC", "-Wl,-soname,libfictional.so.1", "-Wl,-rpath,/fictional/oracle", "-o", str(binary), str(source)], env=self.env, capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace"))
        before = self.snapshot()
        oracle = subprocess.run([str(tools["readelf"]), "--file-header", "--dynamic", "--wide", str(binary)], env=dict(self.env, LC_ALL="C"), capture_output=True, timeout=30)
        self.assertEqual((oracle.returncode, oracle.stderr), (0, b""))
        report = self.call(["--file", binary, "--sha256"])
        item, = report["files"]
        text = oracle.stdout.decode()
        self.assertIn("ELF%d" % item["class"], text)
        self.assertIn("2's complement, " + item["endian"] + " endian", text)
        self.assertIn("(SONAME)", text); self.assertIn("[libfictional.so.1]", text)
        self.assertIn("[/fictional/oracle]", text)
        self.assertEqual(item["needed"], re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", text))
        if item["machine"] == 62:
            self.assertIn("Advanced Micro Devices X86-64", text)
        self.assertEqual((item["type"], item["soname"], item["runpath"], item["sha256"]), ("DYN", "libfictional.so.1", "/fictional/oracle", sha(binary.read_bytes())))
        self.assertEqual(before, self.snapshot())
        for name, tool in tools.items():
            version = subprocess.run([str(tool), "--version"], env=dict(self.env, LC_ALL="C"), capture_output=True, timeout=30)
            self.assertEqual(version.returncode, 0)
            self.assertEqual(version.stdout.decode().splitlines()[0], pins["tools"][name]["version_text"])
            self.assertEqual(sha(tool.read_bytes()), pins["tools"][name]["sha256"])
