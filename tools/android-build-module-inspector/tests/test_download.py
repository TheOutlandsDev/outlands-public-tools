"""Independent consumers of copied build-text tooling; no build or device is accessed."""
import hashlib
import html
from html.parser import HTMLParser
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("build_module_inspector.py", "inspection_support.py", "examples/generate.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junctions_are_not_followed"
PROCESS_WINDOWS_REASON = "Native Windows junction fixture"
PROCESS_POSIX_ID = "test_download.Download.test_native_posix_special_files_are_not_opened"
PROCESS_POSIX_REASON = "Native POSIX FIFO and socket fixture"
PROCESS_SYMLINK_ID = "test_download.Download.test_native_symlink_inputs_and_output_parents"
PROCESS_SYMLINK_REASON = "Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS = {(PROCESS_POSIX_ID, PROCESS_POSIX_REASON)}
REQUIRED_POSIX_SKIPS = {(PROCESS_WINDOWS_ID, PROCESS_WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS = {(PROCESS_SYMLINK_ID, PROCESS_SYMLINK_REASON)}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


def bp(name="example.alpha", kind="cc_library"):
    return (kind + " { name: " + json.dumps(name) + ", }\n").encode()


def mk(name="example.beta", kind="BUILD_SHARED_LIBRARY", operator=":="):
    return ("include $(CLEAR_VARS)\nLOCAL_MODULE " + operator + " " + name + "\ninclude $(" + kind + ")\n").encode()


PROBE = r'''
import argparse,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import build_module_inspector as e
import inspection_support as s
assert Path(e.__file__).resolve()==base/'build_module_inspector.py'
assert Path(s.__file__).resolve()==base/'inspection_support.py'
assert e.source_inputs is s.source_inputs and e.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py'
 assert g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
if kind=='audit':
 e.Parser(description=e.__doc__)
 b'\xef\xbb\xbfprewarm'.decode('utf-8-sig')
 selected=[Path(args[i+1]) for i,value in enumerate(args[:-1]) if value in ('--bp','--mk','--wanted')]
 output=Path(args[args.index('--output')+1])
 allowed={base/name for name in ('build_module_inspector.py','inspection_support.py','examples/generate.py')}
 allowed.update(selected);allowed.update(output/name for name in ('report.json','report.html','MANIFEST.json'))
 def audit(event,values):
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open','ctypes.dlopen'):
   raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
  if event=='open' and not isinstance(values[0],int):assert Path(values[0]) in allowed,'UNEXPECTED_FILE_OPEN'
 sys.addaudithook(audit)
elif kind.startswith('limit:'):
 for name,value in json.loads(kind[6:]).items():
  assert name in ('MAX_REPORT','MAX_ITEMS','MAX_LINE','MAX_LINES','MAX_TOKENS','MAX_DEPTH')
  setattr(e if name in ('MAX_TOKENS','MAX_DEPTH') else s,name,value)
elif kind=='write_failure':
 original=os.open
 def failed(path,*a,**kw):
  if Path(path).name=='MANIFEST.json':raise OSError('FICTIONAL_PRIVATE_WRITE_DETAIL')
  return original(path,*a,**kw)
 os.open=failed
elif kind=='changed_input':
 original=os.read;changed=False;flag='--bp' if '--bp' in args else '--mk';source=Path(args[args.index(flag)+1])
 def changed_read(*a):
  global changed
  raw=original(*a)
  if not changed:
   changed=True
   with source.open('ab') as out:out.write(b'fictional mutation')
  return raw
 os.read=changed_read
elif kind=='short_read':
 os.read=lambda *unused:b''
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
        self.temp = tempfile.TemporaryDirectory(prefix="build-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.copy = self.work / "copied runtime"
        self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT / name).read_bytes()
            target = self.copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            self.pins[name] = sha(raw)
        self.bp_paths = [self.work / "selected.bp"]
        self.mk_paths = []
        self.wanted = None
        self.output = self.work / "new report"
        self.env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
    def runtime_preserved(self):
        self.assertEqual({p.relative_to(self.copy).as_posix() for p in self.copy.rglob("*") if p.is_file()}, set(RUNTIME))
        self.assertEqual({name: sha((self.copy / name).read_bytes()) for name in RUNTIME}, self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
    def snapshot(self):
        rows = {}
        def visit(folder):
            for path in folder.iterdir():
                key = path.relative_to(self.work).as_posix()
                info = path.lstat()
                if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                    rows[key] = ("LINK", os.readlink(path))
                elif stat.S_ISDIR(info.st_mode):
                    rows[key] = ("DIRECTORY",)
                    visit(path)
                elif stat.S_ISREG(info.st_mode):
                    if info.st_size > 8 * 1024 * 1024:
                        with path.open("rb") as stream:
                            sample = stream.read(64); stream.seek(-64, os.SEEK_END); sample += stream.read(64)
                        digest = "SPARSE_ENDPOINTS:" + sha(sample)
                    else:
                        digest = sha(path.read_bytes())
                    rows[key] = (digest, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink)
                else:
                    rows[key] = ("SPECIAL", info.st_mode)
        visit(self.work)
        return rows
    def run_child(self, command, timeout=90, env=None):
        if str(command[0]).endswith(".py"):
            bootstrap = "import runpy,sys;from pathlib import Path;p=Path(sys.argv[1]);sys.path.insert(0,str(p.parent));sys.argv=sys.argv[1:];runpy.run_path(str(p),run_name='__main__')"
            command = ["-c", bootstrap, *command]
        return subprocess.run([sys.executable, "-I", "-B", "-W", "error", *map(str, command)],
                              cwd=self.work, env=self.env if env is None else env, stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=timeout)
    def fixture(self, bp_text=None, mk_text=None, wanted_text=None):
        self.bp_paths = []; self.mk_paths = []; self.wanted = None
        for syntax, value in (("bp", bp_text), ("mk", mk_text)):
            if value is None: continue
            path = self.work / ("selected." + syntax)
            path.write_bytes(value.encode() if isinstance(value,str) else value)
            (self.bp_paths if syntax == "bp" else self.mk_paths).append(path)
        if wanted_text is not None:
            self.wanted = self.work / "wanted.txt"
            self.wanted.write_bytes(wanted_text.encode() if isinstance(wanted_text,str) else wanted_text)
    def selected(self, args):
        return [(syntax,Path(args[i+1])) for flag,syntax in (("--bp","bp"),("--mk","mk"),("--wanted","wanted")) for i,value in enumerate(args[:-1]) if value==flag]
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot()
        prefix = ["-c", PROBE, self.copy, probe] if probe else [self.copy / "build_module_inspector.py"]
        done = self.run_child([*prefix, *args], env=env)
        self.assertEqual(done.stderr, b"", done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout, json.dumps(value, sort_keys=probe != "affinity").encode() + NEWLINE)
        if error is not None:
            self.assertEqual(value, dict(status="INCOMPLETE", error=error)); code = 2
        elif probe == "affinity":
            self.assertEqual(value, dict(status="COPIED_RUNTIME_AFFINITY", dependencies=0)); code = 0
        else:
            report = self.check_report(output, self.selected(args))
            self.assertEqual(value, dict(status=report["status"], declarations=len(report["declarations"]), repeated_names=len(report["repeated_names"]), findings=len(report["findings"]), coverage_issues=len(report["coverage_issues"])))
            value = report; code = int(report["status"] != "NO_SCOPE_FINDINGS")
        self.assertEqual(done.returncode, code)
        for private in (str(self.work).encode(), b"FICTIONAL_PRIVATE", b"Traceback"):
            self.assertNotIn(private, done.stdout + done.stderr)
        after = self.snapshot()
        ignored = {Path(p).relative_to(self.work).as_posix() for p in ignore}
        self.assertEqual({k: v for k, v in before.items() if k not in ignored}, {k: after.get(k) for k in before if k not in ignored})
        for key in after.keys() - before.keys():
            path = self.work / key
            self.assertTrue(any(path == Path(root) or path.is_relative_to(root) for root in allow), "Unexpected application write: " + key)
        self.runtime_preserved()
        return value
    def check_report(self, output, sources):
        self.assertIsNotNone(output)
        self.assertEqual({p.name for p in output.iterdir()}, {"report.json", "report.html", "MANIFEST.json"})
        raw = (output / "report.json").read_bytes(); report = json.loads(raw)
        self.assertEqual(raw, encoded(report))
        required = {"schema_version", "tool", "scope", "details_included", "sources", "declarations", "repeated_names", "wanted", "findings", "coverage_issues", "status", "unresolved_identity_or_scope", "ignored_make_rows"}
        self.assertEqual(set(report), required)
        self.assertEqual((report["tool"], report["schema_version"]), ("Android Build Module Declaration Inspector", 1))
        self.assertEqual(report["status"], "REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        self.assertEqual(report["sources"], [dict(id="input-" + str(i).zfill(4), syntax=syntax, bytes=path.stat().st_size, sha256=sha(path.read_bytes())) for i,(syntax,path) in enumerate(sources,1)])
        for row in report["declarations"]:
            expected = {"id", "source", "line", "syntax", "identity_known", "held"}
            self.assertEqual(set(row), expected | ({"declared_name", "module_kind"} if report["details_included"] else set()))
        for row in report["repeated_names"]:
            self.assertEqual(set(row), {"id", "declarations", "count"} | ({"declared_name"} if report["details_included"] else set()))
        for row in report["wanted"]:
            self.assertEqual(set(row), {"id", "declarations", "state"} | ({"declared_name"} if report["details_included"] else set()))
        self.assertNotIn(str(self.work), raw.decode())
        markup = (output / "report.html").read_bytes()
        parsed = StaticHTML(); parsed.feed(markup.decode()); parsed.close()
        self.assertEqual(parsed.tags.count("html"), 1); self.assertEqual(parsed.csp, ["default-src 'none'; style-src 'unsafe-inline'"])
        self.assertIn(html.escape(raw.decode(), quote=True).encode(), markup)
        members = {name: (output / name).read_bytes() for name in ("report.json", "report.html")}
        expected = dict(schema_version=1, files=[dict(path=name, bytes=len(data), sha256=sha(data)) for name, data in sorted(members.items())])
        self.assertEqual((output / "MANIFEST.json").read_bytes(), encoded(expected))
        return report
    def report(self, extra=(), **kwargs):
        args = [item for flag,paths in (("--bp",self.bp_paths),("--mk",self.mk_paths)) for path in paths for item in (flag,path)]
        if self.wanted is not None: args += ["--wanted", self.wanted]
        return self.call([*args,"--output",self.output,*extra],output=self.output,allow=[self.output],**kwargs)
    def codes(self, report, coverage=False):
        return {row["code"] for row in report["coverage_issues" if coverage else "findings"]}
    def new_output(self, suffix):
        self.output = self.work / ("new report " + str(suffix))
    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314 and os.environ.get("OUTLANDS_BUILD_REQUIRE_LINKS") != "1":
                self.skipTest(PROCESS_SYMLINK_REASON)
            raise






    def test_copied_runtime_affinity_and_help(self):
        self.call([], probe="affinity")
        for script in (self.copy / "build_module_inspector.py", self.copy / "examples/generate.py"):
            before = self.snapshot(); done = self.run_child([script, "--help"])
            self.assertEqual((done.returncode, done.stderr), (0, b"")); self.assertIn(b"--output", done.stdout)
            self.assertEqual(self.snapshot(), before)
    def test_generator_cli_five_fictional_texts_and_new_only_destination(self):
        out = self.work / "generated"; before = self.snapshot()
        done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (0, b"", json.dumps(dict(status="FICTIONAL_EXAMPLES_CREATED", files=5)).encode() + NEWLINE))
        self.assertEqual({k: self.snapshot().get(k) for k in before}, before)
        self.assertEqual({p.name for p in out.iterdir()}, {"clean.bp", "clean.mk", "review.bp", "wanted.txt", "wanted-unseen.txt"})
        self.bp_paths = [out / "clean.bp"]; self.mk_paths = [out / "clean.mk"]; self.wanted = out / "wanted.txt"
        report = self.report(); self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual(len(report["declarations"]), 3)
        self.assertEqual([r["state"] for r in report["wanted"]], ["observed_once"] * 3)
        self.bp_paths = [out / "review.bp"]; self.mk_paths = []; self.wanted = out / "wanted-unseen.txt"; self.new_output("review")
        report = self.report(); self.assertEqual(report["status"], "REVIEW_REQUIRED"); self.assertEqual([r["state"] for r in report["wanted"]], ["observed_multiple", "held_incomplete_scope"])
        before = self.snapshot(); done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (2, b"", json.dumps(dict(status="INCOMPLETE", error="OUTPUT_EXISTS"), sort_keys=True).encode() + NEWLINE)); self.assertEqual(self.snapshot(), before)
    def test_literal_direct_bp_names_and_selected_source_hashes(self):
        self.fixture(bp("example.alpha") + bp("example.beta", "java_library"), wanted_text="example.alpha\nexample.beta\n")
        report = self.report(extra=["--include-details"])
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        self.assertEqual([(r["declared_name"], r["module_kind"], r["syntax"], r["held"]) for r in report["declarations"]], [("example.alpha", "cc_library", "bp", False), ("example.beta", "java_library", "bp", False)])
        self.assertEqual([r["declarations"] for r in report["wanted"]], [["declaration-0001"], ["declaration-0002"]])
    def test_make_literal_assignments_and_build_markers_are_text_only(self):
        text = b"LOCAL_PATH := $(call my-dir)\n" + mk("example.alpha") + mk("example.beta", "BUILD_HOST_EXECUTABLE", "=")
        self.fixture(mk_text=text, wanted_text="example.alpha\nexample.beta\n"); report = self.report(extra=["--include-details"])
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual(report["ignored_make_rows"], 1)
        self.assertEqual([(r["declared_name"], r["module_kind"]) for r in report["declarations"]], [("example.alpha", "BUILD_SHARED_LIBRARY"), ("example.beta", "BUILD_HOST_EXECUTABLE")])
    def test_comments_strings_and_nested_names_do_not_become_modules(self):
        text = b'// cc_library{name:"comment.fake"}\n/* name: "block.fake" */\ncc_library { name: "example.alpha", srcs: ["// not a comment { name:"], target: { android: { name: "nested.fake", }, }, }\n'
        self.fixture(text, wanted_text="example.alpha\nnested.fake\n"); report = self.report(extra=["--include-details"])
        self.assertEqual([r["declared_name"] for r in report["declarations"]], ["example.alpha"])
        self.assertEqual([r["state"] for r in report["wanted"]], ["observed_once", "not_observed_selected_supported_scope"])
        self.assertEqual(self.codes(report), {"WANTED_NAME_NOT_OBSERVED"}); self.assertEqual(report["coverage_issues"], [])
    def test_duplicate_direct_properties_hold_identity_without_a_winner(self):
        cases = ((b'cc_library{name:"example.alpha",name:"example.alpha"}', "example.alpha", "observed_held"), (b'cc_library{name:"example.alpha",name:"example.beta"}', None, "held_incomplete_scope"), (b'cc_library{name:"example.alpha",srcs:[],srcs:[]}', "example.alpha", "observed_held"))
        for index, (text, name, state) in enumerate(cases):
            self.fixture(text, wanted_text="example.alpha\n"); self.new_output(index); report = self.report(extra=["--include-details"])
            self.assertEqual(report["declarations"][0]["declared_name"], name); self.assertIs(report["declarations"][0]["held"], True)
            self.assertEqual(report["wanted"][0]["state"], state); self.assertIn("BP_DUPLICATE_DIRECT_PROPERTY", self.codes(report, True))
    def test_repeated_names_across_selected_syntaxes_are_observed_multiple(self):
        self.fixture(bp() + bp(), mk(), "example.alpha\nexample.beta\n")
        report = self.report(extra=["--include-details"])
        self.assertEqual(self.codes(report), {"REPEATED_DECLARED_NAME_OBSERVED"})
        self.assertEqual(report["repeated_names"], [dict(id="repeated-0001", declarations=["declaration-0001", "declaration-0002"], count=2, declared_name="example.alpha")])
        self.assertEqual([r["state"] for r in report["wanted"]], ["observed_multiple", "observed_once"])
    def test_dynamic_missing_list_and_invalid_bp_names_remain_unresolved(self):
        for index, body in enumerate(('name: prefix + ".suffix"', 'srcs:[]', 'name:["example.alpha"]', 'name:"bad name"', 'name:true')):
            self.fixture("cc_library{" + body + "}", wanted_text="example.alpha\n"); self.new_output(index); report = self.report(extra=["--include-details"])
            self.assertTrue(report["unresolved_identity_or_scope"]); self.assertTrue(report["declarations"][0]["held"]); self.assertIsNone(report["declarations"][0]["declared_name"])
            self.assertEqual(report["wanted"][0]["state"], "held_incomplete_scope"); self.assertIn("BP_NAME_UNRESOLVED", self.codes(report, True))
    def test_namespace_package_and_dynamic_module_kind_hold_scope(self):
        for index, kind in enumerate(("soong_namespace", "package", "soong_config_module_type")):
            self.fixture(kind + '{name:"example.alpha",}', wanted_text="example.alpha\n"); self.new_output(index); report = self.report(extra=["--include-details"])
            self.assertEqual(report["wanted"][0]["state"], "observed_held" if index == 2 else "held_incomplete_scope")
            self.assertIn("BP_DYNAMIC_MODULE_KIND_UNEVALUATED" if index == 2 else "BP_SCOPE_DECLARATION_UNEVALUATED", self.codes(report, True))
    def test_unsupported_bp_toplevel_stops_remainder_but_keeps_prior_record(self):
        self.fixture(bp("first") + b'prefix = "unevaluated"\n' + bp("later"), wanted_text="first\nlater\n")
        report = self.report(extra=["--include-details"])
        self.assertEqual([r["declared_name"] for r in report["declarations"]], ["first"])
        self.assertEqual([r["state"] for r in report["wanted"]], ["observed_once", "held_incomplete_scope"])
        self.assertEqual(self.codes(report, True), {"BP_TOPLEVEL_REMAINDER_UNINSPECTED"})
    def test_unterminated_and_malformed_bp_grammar_does_not_emit_partial_names(self):
        cases = ((b'/* never closed', "BP_UNTERMINATED_COMMENT"), (b'cc_library{name:"oops', "BP_STRING_UNTERMINATED"), (b'cc_library{name:"bad\\q"}', "BP_STRING_UNSUPPORTED"), (b'cc_library{name:"example.alpha",srcs:["x"}}', "BP_DELIMITER_MISMATCH"), (b'cc_library {name:}', "BP_EMPTY_PROPERTY_VALUE"))
        for index, (text, code) in enumerate(cases):
            self.fixture(text, wanted_text="example.alpha\n"); self.new_output(index); report = self.report()
            self.assertEqual(report["declarations"], []); self.assertIn(code, self.codes(report, True)); self.assertEqual(report["wanted"][0]["state"], "held_incomplete_scope")
    def test_make_duplicate_or_dynamic_assignments_are_held_not_evaluated(self):
        cases = (("LOCAL_MODULE := example.alpha\nLOCAL_MODULE := example.alpha\n", "example.alpha", "observed_held"), ("LOCAL_MODULE := example.alpha\nLOCAL_MODULE := example.beta\n", None, "held_incomplete_scope"), ("LOCAL_MODULE := $(shell never-run)\n", None, "held_incomplete_scope"), ("LOCAL_MODULE += example.alpha\n", None, "held_incomplete_scope"))
        for index, (body, name, state) in enumerate(cases):
            text = "include $(CLEAR_VARS)\n" + body + "include $(BUILD_SHARED_LIBRARY)\n"
            self.fixture(mk_text=text, wanted_text="example.alpha\n"); self.new_output(index); report = self.report(extra=["--include-details"])
            self.assertEqual(report["declarations"][0]["declared_name"], name); self.assertTrue(report["declarations"][0]["held"]); self.assertEqual(report["wanted"][0]["state"], state)
    def test_make_incomplete_blocks_and_outside_markers_are_coverage(self):
        cases = (("include $(CLEAR_VARS)\nLOCAL_MODULE := example.alpha\n", "MK_BLOCK_WITHOUT_BUILD"), ("include $(BUILD_EXECUTABLE)\n", "MK_BUILD_WITHOUT_CLEAR"), ("LOCAL_MODULE := example.alpha\n", "MK_MODULE_OUTSIDE_BLOCK"))
        for index, (text, code) in enumerate(cases):
            self.fixture(mk_text=text, wanted_text="example.alpha\n"); self.new_output(index); report = self.report()
            self.assertIn(code, self.codes(report, True)); self.assertNotEqual(report["wanted"][0]["state"], "observed_once")
    def test_make_includes_directives_and_recipes_are_not_followed_or_run(self):
        for index, (text, code) in enumerate((("include /fictional/not-selected.mk\n", "MK_INCLUDE_UNFOLLOWED"), ("ifeq ($(FICTION),yes)\n" + mk("later").decode(), "MK_DIRECTIVE_REMAINDER_UNINSPECTED"), ("\tnever-run --fiction\n" + mk("later").decode(), "MK_RECIPE_REMAINDER_UNINSPECTED"))):
            self.fixture(mk_text=text, wanted_text="later\n"); self.new_output(index); report = self.report()
            self.assertIn(code, self.codes(report, True)); self.assertEqual(report["wanted"][0]["state"], "held_incomplete_scope")
    def test_make_comments_and_unsupported_continuations_do_not_guess_names(self):
        clean = "# LOCAL_MODULE := fake\ninclude $(CLEAR_VARS)\nLOCAL_MODULE := example.alpha # ignored\ninclude $(BUILD_SHARED_LIBRARY)\n"
        self.fixture(mk_text=clean, wanted_text="example.alpha\n"); self.assertEqual(self.report()["status"], "NO_SCOPE_FINDINGS")
        for index, body in enumerate(("LOCAL_MODULE := example.alpha\\#tail\n", "LOCAL_MODULE := \\\nexample.alpha\n")):
            self.fixture(mk_text="include $(CLEAR_VARS)\n" + body + "include $(BUILD_SHARED_LIBRARY)\n", wanted_text="example.alpha\n"); self.new_output(index); report = self.report()
            self.assertTrue(report["unresolved_identity_or_scope"]); self.assertEqual(report["wanted"][0]["state"], "held_incomplete_scope")
    def test_wanted_names_are_case_and_suffix_sensitive_without_alias_guessing(self):
        self.fixture(bp(), wanted_text="example.alpha\nexample.alpha.so\nExample.Alpha\nalpha\n")
        report = self.report(extra=["--include-details"])
        self.assertEqual([r["state"] for r in report["wanted"]], ["observed_once"] + ["not_observed_selected_supported_scope"] * 3)
        self.assertEqual(self.codes(report), {"WANTED_NAME_NOT_OBSERVED"}); self.assertFalse(report["unresolved_identity_or_scope"])
    def test_wanted_duplicates_are_retained_once_and_invalid_or_empty_requests_refuse(self):
        self.fixture(bp(), wanted_text="# comment\n example.alpha \nexample.alpha\n"); report = self.report()
        self.assertEqual(len(report["wanted"]), 1); self.assertEqual(self.codes(report, True), {"DUPLICATE_WANTED_NAME"})
        for index, text in enumerate(("", "# comment only\n", '"example.alpha"\n', "example.alpha # inline\n")):
            self.fixture(bp(), wanted_text=text); self.new_output(index); self.report(error="WANTED_NAMES_REQUIRED" if index < 2 else "WANTED_NAME_UNSUPPORTED"); self.assertFalse(self.output.exists())
    def test_utf8_bom_crlf_and_json_escapes_preserve_literal_name(self):
        text = b'\xef\xbb\xbfcc_library { name: "example.\\u0061lpha", srcs:["fictional ' + chr(960).encode() + b'"], }\r\n'
        self.fixture(text, wanted_text="example.alpha\n"); report = self.report(extra=["--include-details"])
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual(report["declarations"][0]["declared_name"], "example.alpha")
    def test_invalid_utf8_and_control_characters_refuse_before_reports(self):
        cases = ((b"\xff", "UTF8_REQUIRED"), (bp() + b"bare\rreturn", "TEXT_CONTROL_UNSUPPORTED"), (bp() + b"\0", "TEXT_CONTROL_UNSUPPORTED"), (bp() + "// hidden\u202e".encode(), "TEXT_CONTROL_UNSUPPORTED"), (bp() + "// separator\u2028".encode(), "TEXT_CONTROL_UNSUPPORTED"))
        for index, (text, code) in enumerate(cases):
            self.fixture(text); self.new_output(index); self.report(error=code); self.assertFalse(self.output.exists())
    def test_exact_file_byte_and_physical_line_boundaries(self):
        data = bytearray(bp())
        while len(data) < 1024 * 1024:
            size = min(4096, 1024 * 1024 - len(data)); data.extend(b"//" + b"x" * (size - 3) + b"\n" if size >= 3 else b" " * size)
        self.fixture(bytes(data)); self.assertEqual(self.report()["status"], "NO_SCOPE_FINDINGS")
        self.fixture(bytes(data) + b" "); self.new_output("bytes-over"); self.report(error="INPUT_BYTE_LIMIT")
        self.fixture(bp() + b"\n" * 19998); self.new_output("lines-exact"); self.assertEqual(self.report()["status"], "NO_SCOPE_FINDINGS")
        self.fixture(bp() + b"\n" * 19999); self.new_output("lines-over"); self.report(error="TEXT_LINE_LIMIT")
        self.fixture(bp() + b"//" + b"x" * 8190); self.new_output("length-exact"); self.assertEqual(self.report()["status"], "NO_SCOPE_FINDINGS")
        self.fixture(bp() + b"//" + b"x" * 8191); self.new_output("length-over"); self.report(error="TEXT_LINE_LIMIT")
    def test_input_file_count_and_aggregate_byte_limits_are_enforced(self):
        self.bp_paths = []; self.mk_paths = []; self.wanted = None
        for i in range(33):
            path = self.work / (str(i) + ".bp"); path.write_bytes(b""); self.bp_paths.append(path)
        self.report(error="INPUT_COUNT_LIMIT"); self.bp_paths.pop(); self.assertEqual(self.report()["status"], "NO_SCOPE_FINDINGS")
        self.new_output("aggregate"); self.bp_paths = self.bp_paths[:5]
        data = b"//" + b"x" * 4093 + b"\n"
        for path in self.bp_paths: path.write_bytes(data * 256)
        self.report(error="TOTAL_BYTE_LIMIT"); self.assertFalse(self.output.exists())
    def test_bp_token_string_identifier_depth_and_collection_limits_refuse(self):
        cases = [
            ((("+ " * 4000 + "\n") * 11).encode(), "BP_TOKEN_LIMIT"),
            (("cc_library{name:\"example.alpha\",srcs:[\"" + "x" * 1025 + "\"]}").encode(), "BP_STRING_LIMIT"),
            (("x" * 257 + "{}").encode(), "BP_IDENTIFIER_LIMIT"),
            (("cc_library{name:\"example.alpha\",srcs:" + "[" * 33 + "0" + "]" * 33 + "}").encode(), "BP_NESTING_LIMIT"),
            (b"".join(bp("module" + str(i)) for i in range(4001)), "RECORD_LIMIT"),
        ]
        for index, (text, code) in enumerate(cases):
            self.fixture(text); self.new_output(index); self.report(error=code); self.assertFalse(self.output.exists())
    def test_details_and_audit_expose_only_selected_literals_never_follow_includes(self):
        text = b'cc_library{name:"example.alpha",srcs:["</pre><script>PRIVATE_PAYLOAD</script>"],target:{android:{name:"nested.private"}}}'
        self.fixture(text, "include /fictional/not-selected.mk\n" + mk().decode(), "example.alpha\nexample.beta\n")
        basic = self.report(probe="audit"); self.new_output("details"); detailed = self.report(extra=["--include-details"], probe="audit")
        self.assertNotIn("example.alpha", json.dumps(basic)); self.assertIn("example.alpha", json.dumps(detailed))
        for value in (basic, detailed): self.assertNotIn("PRIVATE_PAYLOAD", json.dumps(value)); self.assertNotIn("nested.private", json.dumps(value))
        self.assertNotIn(b"<script>", (self.output / "report.html").read_bytes())
        self.assertEqual([r["state"] for r in basic["wanted"]], [r["state"] for r in detailed["wanted"]])
    def test_arguments_paths_and_new_only_outputs_have_fixed_private_codes(self):
        self.fixture(bp())
        for args, code in (([], "ARGUMENTS_INVALID"), (["--output", self.output], "BUILD_INPUT_REQUIRED"), (["--private-unknown=value"], "ARGUMENTS_INVALID"), (["--bp", self.bp_paths[0]], "ARGUMENTS_INVALID")):
            self.call(args, error=code)
        for path, code in (("relative.bp", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (self.work / ".." / "selected.bp", "LOCAL_ABSOLUTE_PATH_REQUIRED"), ("//fictional/share/build", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (str(self.bp_paths[0]) + "\nprivate", "INVALID_LOCAL_PATH"), (self.copy, "REGULAR_FILE_REQUIRED"), (self.work / "missing", "IO_OR_INPUT_ERROR")):
            self.call(["--bp", path, "--output", self.output], error=code)
        self.report(); self.report(error="OUTPUT_EXISTS")
        for output in (self.bp_paths[0], self.work): self.call(["--bp", self.bp_paths[0], "--output", output], error="OUTPUT_EXISTS")
        self.call(["--bp", self.bp_paths[0], "--output", self.work / "missing" / "report"], error="IO_OR_INPUT_ERROR")
        if os.name == "nt": self.call(["--bp", str(self.bp_paths[0]) + ":stream", "--output", self.output], error="DEVICE_OR_STREAM_PATH_REJECTED")
    def test_changed_short_read_partial_write_and_report_limits_are_controlled(self):
        self.fixture(bp()); self.report(probe="changed_input", error="INPUT_CHANGED", ignore=self.bp_paths); self.assertFalse(self.output.exists())
        self.fixture(bp()); self.report(probe="short_read", error="INPUT_CHANGED"); self.assertFalse(self.output.exists())
        self.report(probe="write_failure", error="IO_OR_INPUT_ERROR"); self.assertEqual({p.name for p in self.output.iterdir()}, {"report.json", "report.html"}); self.report(error="OUTPUT_EXISTS")
        self.new_output("budget"); self.report(probe='limit:{"MAX_REPORT":100}', error="REPORT_BYTE_LIMIT"); self.assertFalse(self.output.exists())
    def test_same_file_cross_syntax_hardlinks_and_hostile_environment_are_safe(self):
        self.fixture(bp()); path = self.bp_paths[0]; linked = self.work / "hardlinked.mk"; os.link(path, linked); self.assertTrue(path.samefile(linked))
        for second in (path, linked): self.call(["--bp", path, "--mk", second, "--output", self.output], error="DUPLICATE_INPUT_FILE")
        hostile = self.work / "hostile imports"; hostile.mkdir()
        for name in ("sitecustomize.py", "usercustomize.py", "json.py", "re.py"):
            (hostile / name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env = dict(self.env, PYTHONPATH=str(hostile), PYTHONHOME=str(hostile), PYTHONSTARTUP=str(hostile / "sitecustomize.py")); self.report(env=env)
    def test_native_symlink_inputs_and_output_parents(self):
        self.fixture(bp(), wanted_text="example.alpha\n"); path = self.bp_paths[0]; linked = self.work / "linked.bp"; self.symlink(linked, path)
        self.call(["--bp", linked, "--output", self.output], error="LINKED_PATH_REJECTED")
        wanted_link = self.work / "wanted-link.txt"; self.symlink(wanted_link, self.wanted)
        self.call(["--bp", path, "--wanted", wanted_link, "--output", self.output], error="LINKED_PATH_REJECTED")
        directory = self.work / "linked directory"; self.symlink(directory, self.work, directory=True)
        self.call(["--bp", path, "--output", directory / "report"], error="LINKED_PATH_REJECTED")
    @unittest.skipUnless(os.name == "nt", PROCESS_WINDOWS_REASON)
    def test_native_windows_junctions_are_not_followed(self):
        self.fixture(bp()); junction = self.work / "junction"
        done = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(self.work)], capture_output=True, timeout=15)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace")); self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
        self.call(["--bp", junction / self.bp_paths[0].name, "--output", self.output], error="LINKED_PATH_REJECTED")
        self.call(["--bp", self.bp_paths[0], "--output", junction / "report"], error="LINKED_PATH_REJECTED")
    @unittest.skipUnless(os.name != "nt", PROCESS_POSIX_REASON)
    def test_native_posix_special_files_are_not_opened(self):
        self.fixture(bp()); fifo = self.work / "fictional.fifo"; os.mkfifo(fifo)
        connection = socket.socket(socket.AF_UNIX); connection.bind(str(self.work / "fictional.sock")); self.addCleanup(connection.close)
        for path in (fifo, self.work / "fictional.sock"): self.call(["--bp", path, "--output", self.output], error="REGULAR_FILE_REQUIRED")
    def test_selection_order_and_wanted_references_remain_explicit(self):
        self.fixture(bp("first"), mk("third"), "third\nfirst\nsecond\n")
        second = self.work / "second.bp"; second.write_bytes(bp("second")); self.bp_paths.append(second)
        args = ["--mk", self.mk_paths[0], "--bp", self.bp_paths[0], "--bp", second, "--wanted", self.wanted, "--output", self.output, "--include-details"]
        report = self.call(args, output=self.output, allow=[self.output])
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual([r["declared_name"] for r in report["declarations"]], ["first", "second", "third"])
        self.assertEqual([r["declarations"] for r in report["wanted"]], [["declaration-0003"], ["declaration-0001"], ["declaration-0002"]])


if __name__ == "__main__":
    unittest.main()
