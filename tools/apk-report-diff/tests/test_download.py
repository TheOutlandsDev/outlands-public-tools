"""Independent consumers of copied saved-report tooling; no APK or device is accessed."""
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
RUNTIME = ("apk_report_diff.py", "inspection_support.py", "examples/generate.py")
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


def saved(package="example.fiction", code="1", name="first", rows=""):
    return ("package: name='" + package + "' versionCode='" + code + "' versionName='" + name + "'\n" + rows).encode("utf-8")


PROBE = r'''
import argparse,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import apk_report_diff as e
import inspection_support as s
assert Path(e.__file__).resolve()==base/'apk_report_diff.py'
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
 before=Path(args[args.index('--before')+1]);after=Path(args[args.index('--after')+1]);output=Path(args[args.index('--output')+1])
 allowed={base/name for name in ('apk_report_diff.py','inspection_support.py','examples/generate.py')}
 allowed.update((before,after));allowed.update(output/name for name in ('report.json','report.html','MANIFEST.json'))
 def audit(event,values):
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open','ctypes.dlopen'):
   raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
  if event=='open' and not isinstance(values[0],int):assert Path(values[0]) in allowed,'UNEXPECTED_FILE_OPEN'
 sys.addaudithook(audit)
elif kind.startswith('limit:'):
 for name,value in json.loads(kind[6:]).items():
  assert name in ('MAX_REPORT','MAX_ITEMS','MAX_LINE','MAX_LINES')
  setattr(s,name,value)
elif kind=='write_failure':
 original=os.open
 def failed(path,*a,**kw):
  if Path(path).name=='MANIFEST.json':raise OSError('FICTIONAL_PRIVATE_WRITE_DETAIL')
  return original(path,*a,**kw)
 os.open=failed
elif kind=='changed_input':
 original=os.read;changed=False;source=Path(args[args.index('--before')+1])
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
        self.temp = tempfile.TemporaryDirectory(prefix="apk-cli-", dir=parent)
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
        self.before = self.work / "before.txt"
        self.after = self.work / "after.txt"
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
    def fixture(self, before=None, after=None):
        before = saved() if before is None else before
        after = before if after is None else after
        self.before.write_bytes(before); self.after.write_bytes(after)
        return before, after
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot()
        prefix = ["-c", PROBE, self.copy, probe] if probe else [self.copy / "apk_report_diff.py"]
        done = self.run_child([*prefix, *args], env=env)
        self.assertEqual(done.stderr, b"", done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout, json.dumps(value, sort_keys=probe != "affinity").encode() + NEWLINE)
        if error is not None:
            self.assertEqual(value, dict(status="INCOMPLETE", error=error)); code = 2
        elif probe == "affinity":
            self.assertEqual(value, dict(status="COPIED_RUNTIME_AFFINITY", dependencies=0)); code = 0
        else:
            report = self.check_report(output)
            self.assertEqual(value, dict(status=report["status"], changes=len(report["changes"]), held_comparisons=len(report["held_comparisons"]), coverage_issues=len(report["coverage_issues"])))
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
    def check_report(self, output):
        self.assertIsNotNone(output)
        self.assertEqual({p.name for p in output.iterdir()}, {"report.json", "report.html", "MANIFEST.json"})
        raw = (output / "report.json").read_bytes(); report = json.loads(raw)
        self.assertEqual(raw, encoded(report))
        required = {"schema_version", "tool", "scope", "details_included", "sources", "summaries", "package_identity", "changes", "held_comparisons", "findings", "coverage_issues", "status"}
        optional = {"declared_packages"} if report["details_included"] and report["package_identity"] != "unresolved" else set()
        self.assertEqual(set(report), required | optional)
        self.assertEqual((report["tool"], report["schema_version"]), ("APK Metadata Report Diff", 1))
        self.assertEqual(report["status"], "REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        self.assertEqual(report["sources"], [dict(id=label, bytes=len(data), sha256=sha(data)) for label, data in (("before", self.before.read_bytes()), ("after", self.after.read_bytes()))])
        self.assertEqual(set(report["summaries"]), {"before", "after"})
        for row in report["changes"]:
            if not report["details_included"]:
                self.assertEqual(set(row), {"entity_id", "field", "before_present", "after_present"})
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
        return self.call(["--before", self.before, "--after", self.after, "--output", self.output, *extra], output=self.output, allow=[self.output], **kwargs)
    def codes(self, report, coverage=False):
        return {row["code"] for row in report["coverage_issues" if coverage else "findings"]}
    def new_output(self, suffix):
        self.output = self.work / ("new report " + str(suffix))
    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314 and os.environ.get("OUTLANDS_APK_REQUIRE_LINKS") != "1":
                self.skipTest(PROCESS_SYMLINK_REASON)
            raise




    def test_copied_runtime_affinity_and_help(self):
        self.call([], probe="affinity")
        for script in (self.copy / "apk_report_diff.py", self.copy / "examples/generate.py"):
            before = self.snapshot(); done = self.run_child([script, "--help"])
            self.assertEqual((done.returncode, done.stderr), (0, b"")); self.assertIn(b"--output", done.stdout)
            self.assertEqual(self.snapshot(), before)
    def test_generator_cli_five_saved_examples_and_new_only_destination(self):
        out = self.work / "generated"; before = self.snapshot()
        done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (0, b"", json.dumps(dict(status="FICTIONAL_EXAMPLES_CREATED", files=5)).encode() + NEWLINE))
        self.assertEqual({k: self.snapshot().get(k) for k in before}, before)
        self.assertEqual({p.name for p in out.iterdir()}, {"before.txt", "same.txt", "after.txt", "unsupported.txt", "duplicate.txt"})
        self.before = out / "before.txt"
        for name in ("same", "after", "unsupported", "duplicate"):
            self.after = out / (name + ".txt"); self.new_output(name); report = self.report()
            self.assertEqual(report["status"], "NO_SCOPE_FINDINGS" if name == "same" else "REVIEW_REQUIRED")
            if name == "after": self.assertEqual(len(report["changes"]), 6)
        before = self.snapshot(); done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (2, b"", json.dumps(dict(status="INCOMPLETE", error="OUTPUT_EXISTS"), sort_keys=True).encode() + NEWLINE))
        self.assertEqual(self.snapshot(), before)
    def test_identical_distinct_reports_have_exact_source_hashes_and_private_defaults(self):
        self.fixture(); report = self.report()
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual(report["package_identity"], "same_declared_name")
        self.assertEqual((report["changes"], report["held_comparisons"], report["coverage_issues"]), ([], [], []))
        self.assertNotIn("example.fiction", json.dumps(report)); self.assertNotIn("declared_packages", report)
        self.assertEqual(report["sources"][0]["sha256"], report["sources"][1]["sha256"])
    def test_version_codes_above_binary64_precision_remain_exact_strings(self):
        self.fixture(saved(code="9007199254740993"), saved(code="18446744073709551615"))
        report = self.report(extra=["--include-details"])
        self.assertEqual(report["changes"], [dict(entity_id="package-0001", field="version_code", before_present=True, after_present=True, before="9007199254740993", after="18446744073709551615")])
    def test_leading_zero_version_codes_and_empty_version_names_are_distinct(self):
        self.fixture(saved(code="0001", name=""), saved(code="1", name="first")); report = self.report(extra=["--include-details"])
        self.assertEqual([(r["field"], r["before"], r["after"]) for r in report["changes"]], [("version_code", "0001", "1"), ("version_name", "", "first")])
        self.assertTrue(all(r["before_present"] and r["after_present"] for r in report["changes"]))
    def test_numeric_sdk_strings_and_unspecified_presence_are_literal(self):
        self.fixture(saved(rows="sdkVersion:'023'\nmaxSdkVersion:'35'\n"), saved(rows="sdkVersion:'23'\ntargetSdkVersion:'34'\n"))
        report = self.report(extra=["--include-details"])
        self.assertEqual([(r["field"], r["before_present"], r["after_present"], r["before"], r["after"]) for r in report["changes"]], [("min_sdk", True, True, "023", "23"), ("target_sdk", False, True, None, "34"), ("max_sdk", True, False, "35", None)])
    def test_sdk_codenames_and_duplicate_rows_hold_only_the_affected_field(self):
        for index, rows in enumerate(("sdkVersion:'VanillaIceCream'\n", "sdkVersion:'23'\nsdkVersion:'23'\n")):
            self.fixture(saved(rows="sdkVersion:'23'\n"), saved(name="updated", rows=rows)); self.new_output(index); report = self.report(extra=["--include-details"])
            self.assertEqual([r["field"] for r in report["changes"]], ["version_name"])
            self.assertEqual(report["held_comparisons"], [dict(entity_id="package-0001", reason="UNSUPPORTED_OR_AMBIGUOUS_FIELD", field="min_sdk")])
            self.assertIn("UNSUPPORTED_SDK_ROW" if index == 0 else "AMBIGUOUS_SDK_ROWS", self.codes(report, True))
    def test_required_optional_added_and_removed_libraries_have_precise_presence(self):
        self.fixture(saved(rows="uses-library:'example.alpha'\nuses-library-not-required:'example.beta'\n"), saved(rows="uses-library:'example.beta'\nuses-library-not-required:'example.gamma'\n"))
        report = self.report(extra=["--include-details"])
        self.assertEqual([(r["declared_identity"], r["before"], r["after"], r["before_present"], r["after_present"]) for r in report["changes"]], [("example.alpha", "required", None, True, False), ("example.beta", "optional", "required", True, True), ("example.gamma", None, "optional", False, True)])
        self.assertEqual(self.codes(report), {"DECLARED_METADATA_CHANGED"})
    def test_relative_order_uses_only_uniquely_common_library_names(self):
        self.fixture(saved(rows="uses-library:'example.alpha'\nuses-library:'example.beta'\n"), saved(rows="uses-library:'example.extra'\nuses-library:'example.beta'\nuses-library:'example.alpha'\n"))
        report = self.report(extra=["--include-details"])
        row = next(r for r in report["changes"] if r["field"] == "relative_common_order")
        self.assertEqual((row["before"], row["after"]), (["example.alpha", "example.beta"], ["example.beta", "example.alpha"]))
        self.assertEqual(len(report["changes"]), 2)
    def test_duplicate_cross_kind_and_malformed_known_libraries_are_held(self):
        for index, rows in enumerate(("uses-library:'example.alpha'\nuses-library-not-required:'example.alpha'\n", "uses-library:'example.alpha' version='unsupported'\n")):
            self.fixture(saved(rows="uses-library:'example.alpha'\n"), saved(rows=rows)); self.new_output(index); report = self.report()
            self.assertEqual(report["changes"], [])
            self.assertEqual({r["reason"] for r in report["held_comparisons"]}, {"AMBIGUOUS_LIBRARY_IDENTITY", "INCOMPLETE_OR_AMBIGUOUS_LIBRARY_ORDER"})
            self.assertIn("AMBIGUOUS_LIBRARY_ROWS" if index == 0 else "UNSUPPORTED_KNOWN_LIBRARY_ROW", self.codes(report, True))
    def test_unknown_opposite_rows_hold_additions_but_allow_matched_scalar_changes(self):
        self.fixture(saved(rows="targetSdkVersion:'34'\nfuture-metadata:'opaque'\n"), saved(rows="targetSdkVersion:'35'\nuses-library:'example.new'\n"))
        report = self.report(extra=["--include-details"])
        self.assertEqual([r["field"] for r in report["changes"]], ["target_sdk"])
        self.assertIn(dict(entity_id="library-0001", reason="UNIDENTIFIED_OPPOSITE_ROWS"), report["held_comparisons"])
        self.assertIn(dict(entity_id="library-order", reason="INCOMPLETE_OR_AMBIGUOUS_LIBRARY_ORDER"), report["held_comparisons"])
        self.assertEqual(self.codes(report, True), {"UNSUPPORTED_ROW"})
    def test_different_package_names_stop_all_remaining_comparisons(self):
        self.fixture(saved(), saved(package="example.other", code="2", name="different", rows="targetSdkVersion:'35'\n")); report = self.report(extra=["--include-details"])
        self.assertEqual(report["package_identity"], "different_declared_names"); self.assertEqual(report["changes"], [])
        self.assertEqual(self.codes(report), {"PACKAGE_IDENTITY_CHANGED"})
        self.assertEqual(report["held_comparisons"], [dict(entity_id="package-0001", reason="DIFFERENT_PACKAGES_NOT_COMPARED")])
    def test_missing_duplicate_and_unsupported_package_rows_hold_identity(self):
        cases = ((b"", "MISSING_PACKAGE_ROW"), (saved() + saved(), "AMBIGUOUS_PACKAGE_ROWS"), (b"package: name='example.fiction' versionCode='1'\n", "UNSUPPORTED_PACKAGE_ROW"), (saved().rstrip() + b" split='extra'\n", "UNSUPPORTED_PACKAGE_ROW"))
        for index, (data, code) in enumerate(cases):
            self.fixture(data, saved(code="2")); self.new_output(index); report = self.report()
            self.assertEqual(report["package_identity"], "unresolved"); self.assertEqual(report["changes"], []); self.assertIn(code, self.codes(report, True))
            self.assertEqual(report["held_comparisons"], [dict(entity_id="package-0001", reason="PACKAGE_IDENTITY_UNRESOLVED")])
    def test_discarded_package_attributes_and_known_unselected_rows_do_not_compare(self):
        before = saved().rstrip() + b" platformBuildVersionCode='34' compileSdkVersionCodename='Old'\napplication: private label ignored\napplication-label-fr: private locale\nuses-permission:'fictional.permission'\n"
        after = saved().rstrip() + b" platformBuildVersionCode='35' compileSdkVersionCodename='New'\napplication: changed label ignored\napplication-icon-any: ignored icon\nuses-permission:'other.permission'\n"
        self.fixture(before, after); report = self.report(extra=["--include-details"])
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual(report["changes"], [])
        self.assertEqual([report["summaries"][side]["ignored_rows"] for side in ("before", "after")], [3, 3])
        self.assertNotIn("private label", json.dumps(report)); self.assertNotIn("permission", json.dumps(report))
    def test_strict_quoted_grammar_does_not_repair_escapes_or_extra_attributes(self):
        values = (b"package: name='example.fiction' versionCode='1' versionName='bad\\escape'\n", b"package: name='example.fiction' name='example.fiction' versionCode='1' versionName='x'\n", saved(code="1" * 21), saved(name="x" * 1025), saved(package="not_a_dotted_name"))
        for index, data in enumerate(values):
            self.fixture(data, saved()); self.new_output(index); report = self.report()
            self.assertEqual(report["package_identity"], "unresolved"); self.assertIn("UNSUPPORTED_PACKAGE_ROW", self.codes(report, True))
    def test_unknown_rows_keep_fixed_side_and_physical_line_numbers(self):
        before = b"\xef\xbb\xbf" + saved().replace(b"\n", b"\r\n") + b"\r\nFuture-Metadata:'PRIVATE_UNKNOWN'\r\n"
        self.fixture(before, saved()); report = self.report(extra=["--include-details"])
        self.assertIn(dict(code="UNSUPPORTED_ROW", source="before", line=3), report["coverage_issues"])
        self.assertNotIn("PRIVATE_UNKNOWN", json.dumps(report)); self.assertEqual(report["summaries"]["before"]["unidentified_rows"], 1)
    def test_utf8_bom_crlf_and_lf_compare_text_but_hash_original_bytes(self):
        before = saved(name="fiction π", rows="sdkVersion:'23'\n")
        after = b"\xef\xbb\xbf" + before.replace(b"\n", b"\r\n")
        self.fixture(before, after); report = self.report(extra=["--include-details"])
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual(report["changes"], [])
        self.assertNotEqual(report["sources"][0]["sha256"], report["sources"][1]["sha256"])
    def test_invalid_utf8_and_control_characters_refuse_without_report(self):
        values = ((b"\xff", "UTF8_REQUIRED"), (saved() + b"bare\rreturn", "TEXT_CONTROL_UNSUPPORTED"), (saved() + b"nul\0", "TEXT_CONTROL_UNSUPPORTED"), (saved() + "hidden\u202e".encode(), "TEXT_CONTROL_UNSUPPORTED"), (saved() + "separator\u2028".encode(), "TEXT_CONTROL_UNSUPPORTED"))
        for index, (data, code) in enumerate(values):
            self.fixture(data, saved()); self.new_output(index); self.report(error=code); self.assertFalse(self.output.exists())
    def test_exact_input_byte_boundary_and_one_extra_byte(self):
        data = bytearray(saved())
        while len(data) < 1024 * 1024:
            size = min(4096, 1024 * 1024 - len(data))
            data.extend(b"application:" + b"x" * (size - 13) + b"\n" if size >= 13 else b" " * size)
        self.fixture(bytes(data)); report = self.report(); self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        self.fixture(bytes(data) + b" ", saved()); self.new_output("over"); self.report(error="INPUT_BYTE_LIMIT"); self.assertFalse(self.output.exists())
    def test_exact_physical_line_and_line_length_boundaries(self):
        data = saved() + b"\n" * 19998
        self.fixture(data); self.assertEqual(self.report()["status"], "NO_SCOPE_FINDINGS")
        self.fixture(data + b"\n", saved()); self.new_output("over-lines"); self.report(error="TEXT_LINE_LIMIT")
        data = saved() + b"application:" + b"x" * (8192 - len(b"application:"))
        self.fixture(data); self.new_output("line-exact"); self.assertEqual(self.report()["status"], "NO_SCOPE_FINDINGS")
        self.fixture(data + b"x", saved()); self.new_output("line-over"); self.report(error="TEXT_LINE_LIMIT")
    def test_library_and_merged_coverage_collections_have_hard_bounds(self):
        data = saved(rows="".join("uses-library:'fiction.lib" + str(i) + "'\n" for i in range(4001)))
        self.fixture(data, saved()); self.report(error="RECORD_LIMIT"); self.assertFalse(self.output.exists())
        unknown = saved(rows="future: 'opaque'\n" * 2500)
        self.fixture(unknown); self.new_output("merged"); self.report(error="RECORD_LIMIT"); self.assertFalse(self.output.exists())
    def test_default_omission_and_details_html_escape_selected_values(self):
        text = "</pre><script>fiction</script>"
        self.fixture(saved(), saved(name=text)); basic = self.report(); self.new_output("details"); details = self.report(extra=["--include-details"])
        self.assertNotIn(text, json.dumps(basic)); self.assertIn(text, json.dumps(details))
        markup = (self.output / "report.html").read_bytes(); self.assertIn(b"&lt;script&gt;", markup); self.assertNotIn(b"<script>", markup)
        self.assertEqual(details["changes"][0]["after"], text)
        self.assertEqual([(r["field"], r["before_present"], r["after_present"]) for r in basic["changes"]], [(r["field"], r["before_present"], r["after_present"]) for r in details["changes"]])
    def test_audit_opens_only_selected_saved_text_and_reports_without_external_actions(self):
        self.fixture(saved(), saved(name="updated", rows="targetSdkVersion:'35'\n")); report = self.report(probe="audit")
        self.assertEqual(self.codes(report), {"DECLARED_METADATA_CHANGED"}); self.assertEqual(len(report["changes"]), 2)
    def test_arguments_paths_and_existing_output_guards_are_private_fixed_codes(self):
        self.fixture()
        for args in ([], ["--private-unknown=value"], ["--before", self.before, "--after", self.after], ["--before", self.before, "--after", self.after, "--output", self.output, "--unknown", "private-value"]):
            self.call(args, error="ARGUMENTS_INVALID")
        for path, code in (("relative.txt", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (self.work / ".." / "before.txt", "LOCAL_ABSOLUTE_PATH_REQUIRED"), ("//fictional/share/report", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (str(self.before) + "\nprivate", "INVALID_LOCAL_PATH"), (self.copy, "REGULAR_FILE_REQUIRED"), (self.work / "missing", "IO_OR_INPUT_ERROR")):
            self.call(["--before", path, "--after", self.after, "--output", self.output], error=code)
        self.report(); self.report(error="OUTPUT_EXISTS")
        for output in (self.before, self.after, self.work): self.call(["--before", self.before, "--after", self.after, "--output", output], error="OUTPUT_EXISTS")
        self.call(["--before", self.before, "--after", self.after, "--output", self.work / "missing" / "report"], error="IO_OR_INPUT_ERROR")
        if os.name == "nt": self.call(["--before", str(self.before) + ":stream", "--after", self.after, "--output", self.output], error="DEVICE_OR_STREAM_PATH_REJECTED")
    def test_input_mutation_short_reads_and_partial_report_failures_are_controlled(self):
        self.fixture(); self.report(probe="changed_input", error="INPUT_CHANGED", ignore=[self.before]); self.assertFalse(self.output.exists())
        self.fixture(); self.report(probe="short_read", error="INPUT_CHANGED"); self.assertFalse(self.output.exists())
        self.report(probe="write_failure", error="IO_OR_INPUT_ERROR")
        self.assertEqual({p.name for p in self.output.iterdir()}, {"report.json", "report.html"}); self.report(error="OUTPUT_EXISTS")
        self.new_output("budget"); self.report(probe='limit:{"MAX_REPORT":100}', error="REPORT_BYTE_LIMIT"); self.assertFalse(self.output.exists())
    def test_same_file_hardlink_pairs_and_hostile_python_environment(self):
        self.fixture(); linked = self.work / "hardlinked.txt"; os.link(self.before, linked); self.assertTrue(os.path.samefile(linked, self.before))
        for after in (self.before, linked): self.call(["--before", self.before, "--after", after, "--output", self.output], error="DUPLICATE_INPUT_FILE")
        hostile = self.work / "hostile imports"; hostile.mkdir()
        for name in ("sitecustomize.py", "usercustomize.py", "json.py", "re.py"):
            (hostile / name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env = dict(self.env, PYTHONPATH=str(hostile), PYTHONHOME=str(hostile), PYTHONSTARTUP=str(hostile / "sitecustomize.py"))
        self.report(env=env)
    def test_native_symlink_inputs_and_output_parents(self):
        self.fixture(); linked = self.work / "linked.txt"; self.symlink(linked, self.before)
        self.call(["--before", linked, "--after", self.after, "--output", self.output], error="LINKED_PATH_REJECTED")
        directory = self.work / "linked directory"; self.symlink(directory, self.work, directory=True)
        self.call(["--before", directory / self.before.name, "--after", self.after, "--output", self.output], error="LINKED_PATH_REJECTED")
        self.call(["--before", self.before, "--after", self.after, "--output", directory / "report"], error="LINKED_PATH_REJECTED")
    @unittest.skipUnless(os.name == "nt", PROCESS_WINDOWS_REASON)
    def test_native_windows_junctions_are_not_followed(self):
        self.fixture(); junction = self.work / "junction"
        done = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(self.work)], capture_output=True, timeout=15)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace")); self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
        self.call(["--before", junction / self.before.name, "--after", self.after, "--output", self.output], error="LINKED_PATH_REJECTED")
        self.call(["--before", self.before, "--after", self.after, "--output", junction / "report"], error="LINKED_PATH_REJECTED")
    @unittest.skipUnless(os.name != "nt", PROCESS_POSIX_REASON)
    def test_native_posix_special_files_are_not_opened(self):
        self.fixture(); fifo = self.work / "fictional.fifo"; os.mkfifo(fifo)
        connection = socket.socket(socket.AF_UNIX); connection.bind(str(self.work / "fictional.sock")); self.addCleanup(connection.close)
        for path in (fifo, self.work / "fictional.sock"):
            self.call(["--before", path, "--after", self.after, "--output", self.output], error="REGULAR_FILE_REQUIRED")
    def test_reversing_inputs_swaps_exact_values_presence_and_source_hashes(self):
        self.fixture(saved(code="1", rows="uses-library:'example.alpha'\n"), saved(code="2", rows="uses-library:'example.beta'\n"))
        forward = self.report(extra=["--include-details"]); self.before, self.after = self.after, self.before; self.new_output("reverse"); reverse = self.report(extra=["--include-details"])
        self.assertEqual([(r["entity_id"], r["field"], r["before"], r["after"], r["before_present"], r["after_present"]) for r in forward["changes"]], [(r["entity_id"], r["field"], r["after"], r["before"], r["after_present"], r["before_present"]) for r in reverse["changes"]])
        self.assertEqual([r["sha256"] for r in forward["sources"]], [r["sha256"] for r in reversed(reverse["sources"])])


if __name__ == "__main__":
    unittest.main()
