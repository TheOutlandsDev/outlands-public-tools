"""Copied CLI checks of fictional SVG text; inputs are never rendered."""
import ctypes
from ctypes import wintypes
import hashlib
import html
from html.parser import HTMLParser
import importlib.metadata
import json
import os
from pathlib import Path
import pyexpat
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from xml.parsers import expat

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("svg_inspector.py", "examples/make_demo.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
SVG = "http://www.w3.org/2000/svg"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junction_stream_and_device_paths_refused"
PROCESS_WINDOWS_REASON = "Native Windows junction and stream fixture"
PROCESS_POSIX_ID = "test_download.Download.test_native_posix_fifo_and_socket_inputs_refused"
PROCESS_POSIX_REASON = "Native POSIX FIFO and socket fixture"
PROCESS_SYMLINK_ID = "test_download.Download.test_native_symlink_input_and_output_parents_refused"
PROCESS_SYMLINK_REASON = "Native symlink privilege unavailable"
LIMITS = dict(max_input_bytes=2097152, max_nodes=20000, max_depth=64, max_attributes=100000,
              max_node_attributes=64, max_attribute_characters=16384, max_text_characters=1048576,
              max_style_characters=65536, max_total_style_characters=262144,
              max_references=2000, max_findings=2000, max_report_bytes_each=8388608)
DIMENSION_NOTE = "Declared literals only; no unit conversion, viewport, CSS cascade or rendered bounds were evaluated."
NOTE = "Static declared markup and a conservative literal-reference subset only. Nothing was rendered, fetched, opened as a reference, executed or sanitized. No safety or visual-quality verdict."
PROBE = r'''
import builtins,errno,hashlib,importlib.metadata,json,os,pyexpat,socket,subprocess,sys
from pathlib import Path
from xml.parsers import expat
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
assert tuple(expat.version_info)==(2,10,0)
binary=Path(pyexpat.__file__).resolve();binary_before=hashlib.sha256(binary.read_bytes()).hexdigest()
python=Path(sys._base_executable).resolve();python_before=hashlib.sha256(python.read_bytes()).hexdigest()
assert binary_before==os.environ['OUTLANDS_TEST_EXPAT_SHA256']
assert python_before==os.environ['OUTLANDS_TEST_PYTHON_SHA256']
assert '.'.join(map(str,sys.version_info[:3]))==os.environ['OUTLANDS_TEST_PYTHON_VERSION']
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import svg_inspector as m
assert Path(m.__file__).resolve()==base/'svg_inspector.py' and m.expat is expat
kind=sys.argv[2];args=sys.argv[3:]
def parser_unchanged():
 assert tuple(expat.version_info)==(2,10,0) and hashlib.sha256(binary.read_bytes()).hexdigest()==binary_before
 assert hashlib.sha256(python.read_bytes()).hexdigest()==python_before
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'))
 import make_demo
 assert Path(make_demo.__file__).resolve()==base/'examples/make_demo.py' and make_demo.s is m
 parser_unchanged()
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0,expat='2.10.0')))
 raise SystemExit(0)
elif kind=='no_external':
 import encodings.utf_8_sig  # Load this standard codec before narrowing file opens.
 m.Parser(description=m.__doc__)  # Initialize the standard CLI formatter before the audit hook.
 source=Path(args[args.index('--svg')+1]);out=Path(args[args.index('--output')+1])
 allowed={source,out/'report.json',out/'report.html',out/'MANIFEST.json',binary,python}
 def audit(event,values):
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open'):
   raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
  if event=='open' and not isinstance(values[0],int):
   assert Path(values[0]) in allowed, 'UNEXPECTED_REFERENCE_OR_FILE_OPEN'
 sys.addaudithook(audit)
elif kind=='manifest_failure':
 original=os.open
 def opening(path,flags,*extra,**options):
  if Path(path).name=='MANIFEST.json' and flags&os.O_WRONLY:raise OSError('FICTIONAL_PRIVATE_OUTPUT_DETAIL')
  return original(path,flags,*extra,**options)
 os.open=opening
elif kind=='short_read':
 original=os.read
 os.read=lambda fd,amount:original(fd,min(amount,3))
elif kind=='read_failure':
 def failure(*args):raise OSError('FICTIONAL_PRIVATE_READ_DETAIL')
 os.read=failure
elif kind=='mutation':
 original=os.read;events=[];source=Path(args[args.index('--svg')+1])
 def mutate(fd,amount):
  block=original(fd,amount)
  if block and not events:
   data=source.read_bytes();source.write_bytes(data.replace(b'<svg',b'<svG',1));events.append(True)
  return block
 os.read=mutate
elif kind=='library_interrupt':
 source=Path(args[0]);before=source.read_bytes();observed=[]
 def interrupt(fd,amount):
  observed.append(fd);raise KeyboardInterrupt
 os.read=interrupt
 try:m.snapshot(source)
 except KeyboardInterrupt:pass
 else:raise AssertionError('LIBRARY_INTERRUPT_MUST_PROPAGATE')
 assert len(observed)==1
 try:os.fstat(observed[0])
 except OSError as error:assert error.errno==errno.EBADF
 else:raise AssertionError('INTERRUPTED_DESCRIPTOR_STILL_OPEN')
 assert source.read_bytes()==before
 parser_unchanged()
 print(json.dumps(dict(status='LIBRARY_INTERRUPT_PROPAGATED',descriptor_closed=True)))
 raise SystemExit(0)
elif kind=='nul':
 source=str(Path(args[0]).parent/'FICTIONAL\x00PRIVATE.svg')
 code=m.main(['--svg',source,'--output',args[0]])
 parser_unchanged();raise SystemExit(code)
else:raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
code=m.main(args);parser_unchanged();raise SystemExit(code)
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def svg(body="", attrs=""):
    return ('<svg xmlns="' + SVG + '"' + (" " + attrs if attrs else "") + ">" + body + "</svg>").encode()


def finding(code, number, line=1):
    return dict(code=code, node="node-%06d" % number, line=line)


def ref(number, node, kind="internal_fragment", resolution="not_inspected", source="href", **extra):
    return dict(id="ref-%06d" % number, node="node-%06d" % node, source=source,
                kind=kind, resolution=resolution, **extra)


def identity(number, nodes, duplicate=False, **extra):
    return dict(id="id-%06d" % number, nodes=["node-%06d" % node for node in nodes], duplicates=duplicate, **extra)


def empty_dimensions():
    return dict(width=dict(present=False), height=dict(present=False), viewBox=dict(present=False),
                interpretation=DIMENSION_NOTE)


class StaticHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.declarations = []
    def handle_decl(self, declaration):
        self.declarations.append(declaration.lower())
    def handle_starttag(self, tag, attributes):
        allowed = {"html", "meta", "title", "style", "h1", "p", "strong", "code", "h2", "pre",
                   "table", "thead", "tr", "th", "tbody", "td"}
        assert tag in allowed, "ACTIVE_OR_SOURCE_MARKUP_IN_REPORT"
        if tag == "html":
            assert attributes == [("lang", "en")]
        elif tag == "meta":
            assert attributes in ([("charset", "utf-8")],
                [("name", "viewport"), ("content", "width=device-width")],
                [("http-equiv", "Content-Security-Policy"), ("content", "default-src 'none'; style-src 'unsafe-inline'")])
        else:
            assert attributes == [], "UNEXPECTED_REPORT_ATTRIBUTE"
        self.tags.append(tag)
    def handle_entityref(self, name):
        raise AssertionError("UNDECODED_ENTITY")
    def handle_pi(self, text):
        raise AssertionError("REPORT_PROCESSING_INSTRUCTION")


class Download(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if tuple(expat.version_info) != (2, 10, 0):
            raise AssertionError("REAL_EXPAT_2_10_0_REQUIRED")
        cls.expat_binary = Path(pyexpat.__file__).resolve()
        cls.expat_pin = sha(cls.expat_binary.read_bytes())
        cls.expat_bytes = cls.expat_binary.stat().st_size
        cls.python_binary = Path(sys._base_executable).resolve()
        cls.python_pin = sha(cls.python_binary.read_bytes())
        cls.python_bytes = cls.python_binary.stat().st_size
        cls.python_version = ".".join(map(str, sys.version_info[:3]))
        if not all(os.environ.get(name) for name in ("OUTLANDS_TEST_EXPAT_SHA256", "OUTLANDS_TEST_PYTHON_SHA256", "OUTLANDS_TEST_PYTHON_VERSION")):
            raise AssertionError("EXPLICIT_EXPECTED_PARSER_AND_PYTHON_PINS_REQUIRED")
        if cls.expat_pin != os.environ["OUTLANDS_TEST_EXPAT_SHA256"]:
            raise AssertionError("EXPECTED_EXPAT_BINARY_DIFFERS")
        if cls.python_pin != os.environ["OUTLANDS_TEST_PYTHON_SHA256"] or cls.python_version != os.environ["OUTLANDS_TEST_PYTHON_VERSION"]:
            raise AssertionError("EXPECTED_PYTHON_BINARY_OR_VERSION_DIFFERS")
    @classmethod
    def tearDownClass(cls):
        if tuple(expat.version_info) != (2, 10, 0) or sha(cls.expat_binary.read_bytes()) != cls.expat_pin or cls.expat_binary.stat().st_size != cls.expat_bytes:
            raise AssertionError("REAL_EXPAT_BINARY_CHANGED")
        if sha(cls.python_binary.read_bytes()) != cls.python_pin or cls.python_binary.stat().st_size != cls.python_bytes:
            raise AssertionError("REAL_PYTHON_BINARY_CHANGED")
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="svg-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.copy = self.work / "copied runtime"
        self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT / name).read_bytes()
            path = self.copy / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.pins[name] = sha(raw)
        self.source = self.work / "fictional input.svg"
        self.source.write_bytes(svg())
        self.output = self.work / "new report"
        self.addCleanup(self.runtime_preserved)

    def runtime_preserved(self):
        self.assertEqual({p.relative_to(self.copy).as_posix() for p in self.copy.rglob("*") if p.is_file()}, set(RUNTIME))
        self.assertEqual({name: sha((self.copy / name).read_bytes()) for name in RUNTIME}, self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])

    def snapshot(self):
        rows = {}
        def walk(folder):
            for path in folder.iterdir():
                key = path.relative_to(self.work).as_posix()
                if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                    rows[key] = ("LINK", os.readlink(path))
                elif path.is_dir():
                    rows[key] = ("DIRECTORY",)
                    walk(path)
                else:
                    info = path.lstat()
                    rows[key] = ((sha(path.read_bytes()), info.st_size, info.st_mtime_ns, info.st_ctime_ns,
                                  info.st_ino, info.st_nlink) if stat.S_ISREG(info.st_mode) else ("SPECIAL", info.st_mode))
        walk(self.work)
        return rows

    def expected(self, raw=None, *, nodes=1, attributes=0, text=0, dimensions=None,
                 ids=(), references=(), findings=(), coverage=(), details=False):
        raw = self.source.read_bytes() if raw is None else raw
        return dict(schema_version=1, tool="svg-content-inspector",
                    status="REVIEW_REQUIRED" if findings or coverage else "NO_SCOPE_FINDINGS",
                    source_sha256=sha(raw), source_bytes=len(raw), parser_expat="2.10.0", details_included=details,
                    node_count=nodes, attribute_count=attributes, text_characters=text,
                    dimensions=empty_dimensions() if dimensions is None else dimensions, ids=list(ids), references=list(references),
                    findings=list(findings), coverage_issues=sorted(coverage), limits=LIMITS, interpretation=NOTE)

    def call(self, *, source=None, output=None, args=None, expected=None, error=None, probe=None,
             allow=(), ignore=(), env_extra=None, demo=False, help_output=False):
        source = self.source if source is None else source
        output = self.output if output is None else output
        if args is None:
            args = ["--destination", output] if demo else ["--svg", source, "--output", output]
        before = self.snapshot()
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        if env_extra:
            env.update(env_extra)
        command = ([sys.executable, "-I", "-B", "-W", "error", "-c", PROBE, str(self.copy), probe]
                   if probe else [sys.executable, "-I", "-B", "-W", "error",
                                  str(self.copy / ("examples/make_demo.py" if demo else "svg_inspector.py"))])
        code = 2 if error else 1 if expected and expected["status"] == "REVIEW_REQUIRED" else 0
        done = subprocess.run([*command, *map(str, args)], cwd=self.work, env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=90)
        self.assertEqual(done.returncode, code, (done.stdout + done.stderr).decode(errors="replace")[:2000])
        self.assertEqual(done.stderr, b"")
        for private in (str(self.work).encode(), b"FICTIONAL_PRIVATE", b"Traceback"):
            self.assertNotIn(private, done.stdout)
        after = self.snapshot()
        ignored = {Path(path).relative_to(self.work).as_posix() for path in ignore}
        self.assertEqual({key: value for key, value in before.items() if key not in ignored},
                         {key: after.get(key) for key in before if key not in ignored})
        for key in after.keys() - before.keys():
            path = self.work / key
            self.assertTrue(any(path == Path(root) or path.is_relative_to(root) for root in allow),
                            "Unexpected application write: " + key)
        self.runtime_preserved()
        if help_output:
            self.assertIn(b"--svg", done.stdout)
            return None
        if probe == "affinity":
            wanted = dict(status="COPIED_RUNTIME_AFFINITY", dependencies=0, expat="2.10.0")
        elif probe == "library_interrupt":
            wanted = dict(status="LIBRARY_INTERRUPT_PROPAGATED", descriptor_closed=True)
        elif demo:
            wanted = dict(status="INCOMPLETE", error="FRESH_TRUSTED_DESTINATION_REQUIRED") if error else dict(status="FICTIONAL_FIXTURES_CREATED", files=2)
        elif error:
            wanted = dict(status="INCOMPLETE", error=error)
        else:
            self.assertIsNotNone(expected)
            wanted = dict(status=expected["status"], node_count=expected["node_count"],
                          reference_count=len(expected["references"]), finding_count=len(expected["findings"]),
                          coverage_issues=expected["coverage_issues"])
        self.assertEqual(len(done.stdout.splitlines()), 1)
        self.assertEqual(json.loads(done.stdout), wanted)
        self.assertEqual(done.stdout, json.dumps(wanted, sort_keys=not demo and probe not in {"affinity", "library_interrupt"}).encode() + NEWLINE)
        if not error and expected is not None:
            self.check_report(output, expected)

    def check_report(self, output, expected):
        self.assertEqual({p.name for p in output.iterdir()}, {"report.json", "report.html", "MANIFEST.json"})
        raw = (output / "report.json").read_bytes()
        self.assertEqual(json.loads(raw), expected)
        self.assertEqual(raw, (json.dumps(expected, indent=2, ensure_ascii=True) + "\n").encode())
        markup = (output / "report.html").read_bytes()
        self.assertTrue(markup.endswith(b"\n") and b"\r" not in markup)
        parsed = StaticHTML()
        parsed.feed(markup.decode("utf-8")); parsed.close()
        self.assertEqual(parsed.declarations, ["doctype html"])
        self.assertEqual(parsed.tags.count("html"), 1)
        self.assertEqual(parsed.tags.count("meta"), 3)
        self.assertEqual(parsed.tags.count("style"), 1)
        self.assertEqual(parsed.tags.count("table"), 1)
        self.assertNotIn(b"<svg", markup.lower())
        self.assertNotIn(str(self.work).encode(), raw)
        manifest = dict(schema_version=1, files=[dict(path=name, bytes=len(data), sha256=sha(data))
                         for name, data in sorted({"report.json": raw, "report.html": markup}.items())])
        self.assertEqual((output / "MANIFEST.json").read_bytes(), (json.dumps(manifest, indent=2) + "\n").encode())

    def report(self, raw=None, *, output=None, details=False, **expected_fields):
        if raw is not None:
            self.source.write_bytes(raw)
        wanted = self.expected(details=details, **expected_fields)
        output = self.output if output is None else output
        args = ["--svg", self.source, "--output", output] + (["--include-details"] if details else [])
        self.call(args=args, output=output, expected=wanted, allow=[output])
        return wanted

    def reject(self, raw, code):
        self.source.write_bytes(raw)
        self.call(error=code)
        self.assertFalse(self.output.exists())

    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            strict = os.environ.get("OUTLANDS_SVG_REQUIRE_LINKS") == "1" or os.environ.get("OUTLANDS_REQUIRE_SYMLINK_TEST") == "1"
            if os.name == "nt" and getattr(error, "winerror", None) == 1314 and not strict:
                self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_real_parser_and_copied_runtime_demo_affinity(self):
        self.call(args=[], probe="affinity")

    def test_demo_cli_creates_only_authored_clean_and_review_inputs(self):
        demo = self.work / "new authored demo"
        self.call(output=demo, demo=True, allow=[demo])
        self.assertEqual({p.name for p in demo.iterdir()}, {"clean.svg", "review.svg", "README.txt"})
        dimensions = dict(width=dict(present=True, status="literal_length", value="320", unit="user_units"),
            height=dict(present=True, status="literal_length", value="180", unit="user_units"),
            viewBox=dict(present=True, status="literal_viewbox", values=["0", "0", "320", "180"]), interpretation=DIMENSION_NOTE)
        raw = (demo / "clean.svg").read_bytes()
        clean = self.expected(raw, nodes=7, attributes=14, text=38, dimensions=dimensions,
            ids=[identity(1, [4])], references=[ref(1, 7, source="presentation_attribute:css_url",
                resolution="resolved_unique", target_nodes=["node-000004"])])
        self.call(source=demo / "clean.svg", expected=clean, allow=[self.output])
        raw = (demo / "review.svg").read_bytes()
        dimensions["width"] = dict(present=True, status="invalid_or_unsupported")
        review = self.expected(raw, nodes=9, attributes=10, text=54, dimensions=dimensions,
            ids=[identity(1, [5, 6], True)],
            references=[ref(1, 7, resolution="missing", target_nodes=[]),
                        ref(2, 8, source="inline_style:css_url", resolution="ambiguous_duplicate_id", target_nodes=["node-000005", "node-000006"]),
                        ref(3, 9, kind="data")],
            findings=[finding("DIMENSION_INVALID_OR_UNSUPPORTED", 1), finding("ACTIVE_OR_ANIMATED_ELEMENT", 3, 4),
                      finding("ACTIVE_OR_ANIMATED_ELEMENT", 4, 5), finding("EVENT_HANDLER_ATTRIBUTE", 8, 8),
                      finding("INLINE_STYLE_DECLARATION", 8, 8), finding("IMAGE_ELEMENT", 9, 9),
                      finding("NON_FRAGMENT_REFERENCE", 9, 9), finding("DUPLICATE_ID", 5, None),
                      finding("INTERNAL_REFERENCE_MISSING", 7, None), finding("INTERNAL_REFERENCE_AMBIGUOUS", 8, None)],
            coverage=["CSS_CASCADE_AND_DECLARATIONS_NOT_EVALUATED"])
        target = self.work / "review report"
        self.call(source=demo / "review.svg", output=target, expected=review, allow=[target])
        self.call(output=demo, demo=True, error="FRESH_TRUSTED_DESTINATION_REQUIRED")

    def test_minimal_clean_report_is_complete_and_repeatable(self):
        self.report()
        target = self.work / "repeat report"
        self.report(output=target)
        for name in ("report.json", "report.html", "MANIFEST.json"):
            self.assertEqual((self.output / name).read_bytes(), (target / name).read_bytes())

    def test_declared_decimal_dimensions_do_not_convert_units(self):
        dimensions = dict(width=dict(present=True, status="literal_length", value="2.5", unit="cm"),
            height=dict(present=True, status="literal_length", value="100", unit="%"),
            viewBox=dict(present=True, status="literal_viewbox", values=["-1", "-2", "300", "400"]), interpretation=DIMENSION_NOTE)
        self.report(svg(attrs='width="2.5cm" height="1e2%" viewBox="-1,-2,300,400"'), attributes=3, dimensions=dimensions)

    def test_unsupported_and_zero_dimensions_require_review(self):
        for index, value in enumerate(("auto", "NaN", "-1", "1e999", "1future", "0")):
            dimensions = empty_dimensions()
            dimensions["width"] = (dict(present=True, status="literal_length", value="0", unit="user_units")
                                   if value == "0" else dict(present=True, status="invalid_or_unsupported"))
            code = "ZERO_DIMENSION_DECLARATION" if value == "0" else "DIMENSION_INVALID_OR_UNSUPPORTED"
            self.report(svg(attrs='width="' + value + '"'), output=self.work / ("dimensions-" + str(index)),
                        attributes=1, dimensions=dimensions, findings=[finding(code, 1)])

    def test_active_markers_and_event_values_are_not_executed(self):
        body = '<script/><foreignObject/><animate/><a/><image/><rect OnClick="FICTIONAL_PRIVATE_EVENT"/>'
        self.report(svg(body), nodes=7, attributes=1,
            findings=[finding("ACTIVE_OR_ANIMATED_ELEMENT", 2), finding("ACTIVE_OR_ANIMATED_ELEMENT", 3),
                      finding("ACTIVE_OR_ANIMATED_ELEMENT", 4), finding("LINK_ELEMENT", 5),
                      finding("IMAGE_ELEMENT", 6), finding("EVENT_HANDLER_ATTRIBUTE", 7)])
        for name in ("report.json", "report.html"):
            self.assertNotIn(b"FICTIONAL_PRIVATE_EVENT", (self.output / name).read_bytes())

    def test_reference_categories_are_text_only_without_external_access(self):
        canary = self.work / "unopened referenced file"
        canary.write_bytes(b"FICTIONAL_PRIVATE_REFERENCE_BYTES")
        values = ["https://fictional.invalid/FICTIONAL_PRIVATE", canary.as_uri(), "fictional-relative.dat",
                  "data:text/plain,FICTIONAL_PRIVATE", "javascript:void(0)", "fictional:opaque", "#not%20simple", " "]
        kinds = ["external_network", "external_file", "external_relative", "data", "active_scheme", "unknown_scheme",
                 "unsupported_fragment", "empty"]
        self.source.write_bytes(svg("".join('<use href="' + html.escape(value, quote=True) + '"/>' for value in values)))
        wanted = self.expected(nodes=9, attributes=8,
            references=[ref(i + 1, i + 2, kind=kind) for i, kind in enumerate(kinds)],
            findings=[finding("NON_FRAGMENT_REFERENCE", node) for node in range(2, 8)],
            coverage=["REFERENCE_TEXT_UNSUPPORTED"])
        self.call(expected=wanted, probe="no_external", allow=[self.output])
        self.assertEqual(canary.read_bytes(), b"FICTIONAL_PRIVATE_REFERENCE_BYTES")
        self.assertNotIn(b"FICTIONAL_PRIVATE", (self.output / "report.json").read_bytes())

    def test_private_details_are_opt_in_and_escaped_in_static_html(self):
        value = 'https://fictional.invalid/"><script>FICTIONAL_PRIVATE</script>'
        raw = svg('<g id="FICTIONAL_PRIVATE_ID"/><use href="' + html.escape(value, quote=True) + '"/>')
        base = dict(nodes=3, attributes=2, ids=[identity(1, [2])],
                    references=[ref(1, 3, kind="external_network")], findings=[finding("NON_FRAGMENT_REFERENCE", 3)])
        self.report(raw, **base)
        self.assertNotIn(b"FICTIONAL_PRIVATE", (self.output / "report.json").read_bytes())
        base["ids"] = [identity(1, [2], id_text="FICTIONAL_PRIVATE_ID")]
        base["references"] = [ref(1, 3, kind="external_network", reference_text=value)]
        target = self.work / "private detail report"
        self.report(raw, output=target, details=True, **base)
        markup = (target / "report.html").read_text()
        self.assertIn(html.escape(value, quote=True), markup)
        self.assertNotIn("<script>", markup)

    def test_unique_fragment_resolution_uses_only_declared_ids(self):
        self.report(svg('<g id="paint"/><use href="#paint"/>'), nodes=3, attributes=2,
            ids=[identity(1, [2])], references=[ref(1, 3, resolution="resolved_unique", target_nodes=["node-000002"])])

    def test_duplicate_and_missing_fragment_targets_have_no_winner(self):
        self.report(svg('<g id="dup"/><g id="dup"/><use href="#dup"/><use href="#absent"/>'), nodes=5, attributes=4,
            ids=[identity(1, [2, 3], True)],
            references=[ref(1, 4, resolution="ambiguous_duplicate_id", target_nodes=["node-000002", "node-000003"]),
                        ref(2, 5, resolution="missing", target_nodes=[])],
            findings=[finding("DUPLICATE_ID", 2, None), finding("INTERNAL_REFERENCE_AMBIGUOUS", 4, None),
                      finding("INTERNAL_REFERENCE_MISSING", 5, None)])

    def test_stylesheet_and_inline_literals_still_require_css_review(self):
        css = "rect{fill:url(#paint)}"
        self.report(svg('<style>' + css + '</style><g id="paint"/><rect style="stroke:url(#paint)"/>'),
            nodes=4, attributes=2, text=len(css), ids=[identity(1, [3])],
            references=[ref(1, 2, source="stylesheet:css_url", resolution="resolved_unique", target_nodes=["node-000003"]),
                        ref(2, 4, source="inline_style:css_url", resolution="resolved_unique", target_nodes=["node-000003"])],
            findings=[finding("STYLESHEET_ELEMENT", 2), finding("INLINE_STYLE_DECLARATION", 4)],
            coverage=["CSS_CASCADE_AND_DECLARATIONS_NOT_EVALUATED", "STYLESHEET_RULES_NOT_EVALUATED"])

    def test_css_escapes_functions_and_nonascii_have_explicit_uncertainty(self):
        samples = [(r"fill:\73 red", "CSS_ESCAPES_UNINSPECTED"),
                   ("fill:var(--fictional)", "CSS_FUNCTION_NOT_INTERPRETED"),
                   ("fill:\u03bb", "CSS_TEXT_OUTSIDE_LITERAL_SUBSET")]
        for index, (value, issue) in enumerate(samples):
            self.report(svg('<rect style="' + value + '"/>'), output=self.work / ("css-" + str(index)),
                        nodes=2, attributes=1, findings=[finding("INLINE_STYLE_DECLARATION", 2)],
                        coverage=["CSS_CASCADE_AND_DECLARATIONS_NOT_EVALUATED", issue])

    def test_foreign_namespaces_and_unknown_markup_do_not_imply_coverage(self):
        raw = svg('<f:rect/><future/>', attrs='xmlns:f="urn:FICTIONAL_PRIVATE_NAMESPACE" f:data="FICTIONAL_PRIVATE_VALUE"')
        self.report(raw, nodes=3, attributes=1,
            findings=[finding("FOREIGN_NAMESPACE_ELEMENT", 2), finding("UNRECOGNIZED_SVG_ELEMENT", 3)],
            coverage=["FOREIGN_NAMESPACE_DECLARATION", "FOREIGN_ATTRIBUTE_NAMESPACE", "FOREIGN_MARKUP_UNINSPECTED",
                      "SVG_ELEMENT_OUTSIDE_SUBSET"])
        self.assertNotIn(b"FICTIONAL_PRIVATE", (self.output / "report.json").read_bytes())

    def test_processing_instructions_are_not_followed(self):
        self.source.write_bytes(svg('<?xml-stylesheet href="https://fictional.invalid/PI"?>'))
        wanted = self.expected(coverage=["PROCESSING_INSTRUCTION_UNINSPECTED"])
        self.call(expected=wanted, probe="no_external", allow=[self.output])

    def test_utf8_bom_and_builtin_entities_preserve_source_bytes(self):
        text = "Fictional & \u03bb < value"
        raw = b"\xef\xbb\xbf" + svg("<title>Fictional &amp; \u03bb &lt; value</title>")
        self.report(raw, nodes=2, text=len(text))
        self.assertNotIn(b"Fictional &", (self.output / "report.json").read_bytes())

    def test_namespace_root_and_encoding_declarations_are_strict(self):
        for raw in (b"<svg/>", b'<svg xmlns="urn:fictional"/>', b'<html xmlns="' + SVG.encode() + b'"/>'):
            self.reject(raw, "SVG_NAMESPACE_ROOT_REQUIRED")
        for prefix in ('<?xml version="1.1"?>', '<?xml version="1.0" encoding="ISO-8859-1"?>'):
            self.reject(prefix.encode() + svg(), "XML_DECLARATION_UNSUPPORTED")

    def test_dtd_and_entities_are_refused_before_expansion_or_resolution(self):
        values = [b"<!DOCTYPE svg>", b'<!DOCTYPE svg [<!ENTITY x "FICTIONAL_PRIVATE">]>',
                  b'<!DOCTYPE svg SYSTEM "file:///fictional/unopened">',
                  b'<!DOCTYPE svg [<!ENTITY x SYSTEM "https://fictional.invalid/unopened">]>']
        for raw in values:
            self.source.write_bytes(raw + svg())
            self.call(error="DTD_AND_ENTITIES_REJECTED", probe="no_external")
            self.assertFalse(self.output.exists())

    def test_malformed_utf8_xml_and_duplicate_attributes_are_incomplete(self):
        for raw in (b"\xff", b"\xef\xbb\xbf\xff"):
            self.reject(raw, "UTF8_REQUIRED")
        for raw in (b"", b"<", svg("<g>"), svg('<g a="1" a="2"/>'), svg() + b"junk"):
            self.reject(raw, "INVALID_XML")

    def test_input_byte_limit_is_exact_at_the_boundary(self):
        raw = svg() + b" " * (2097152 - len(svg()))
        self.report(raw)
        target = self.work / "oversize report"
        self.source.write_bytes(raw + b" ")
        self.call(output=target, error="INPUT_BYTE_LIMIT")
        self.assertFalse(target.exists())

    def test_actual_depth_and_element_limits_fail_closed(self):
        self.reject(svg("<g>" * 64 + "</g>" * 64), "NODE_OR_DEPTH_LIMIT")
        self.reject(svg("<g/>" * 20000), "NODE_OR_DEPTH_LIMIT")
        self.report(svg("<g/>" * 19999), nodes=20000)

    def test_attribute_id_and_namespace_bounds_are_enforced(self):
        self.reject(svg(attrs=" ".join('a%d=""' % i for i in range(65))), "ATTRIBUTE_LIMIT")
        self.reject(svg(attrs='data="' + "x" * 16385 + '"'), "ATTRIBUTE_CHARACTER_LIMIT")
        self.reject(svg('<g id="' + "x" * 1025 + '"/>'), "ID_CHARACTER_LIMIT")
        self.reject(svg(attrs=" ".join('xmlns:n%d="urn:fictional%d"' % (i, i) for i in range(1024))), "NAMESPACE_LIMIT")

    def test_text_individual_style_and_total_style_bounds_are_enforced(self):
        self.reject(svg("<text>" + "x" * 1048577 + "</text>"), "TEXT_CHARACTER_LIMIT")
        self.reject(svg("<style>" + "x" * 65537 + "</style>"), "STYLE_CHARACTER_LIMIT")
        self.reject(svg(('<rect style="' + "x" * 16384 + '"/>') * 17), "TOTAL_STYLE_CHARACTER_LIMIT")

    def test_reference_and_finding_limits_do_not_return_partial_success(self):
        self.reject(svg('<g id="paint"/>' + '<use href="#paint"/>' * 2001), "REFERENCE_LIMIT")
        self.reject(svg("<script/>" * 2001), "FINDING_LIMIT")

    def test_outputs_are_fresh_and_missing_parents_are_not_created(self):
        self.output.mkdir()
        (self.output / "keep.txt").write_bytes(b"Fictional keep\n")
        self.call(error="OUTPUT_EXISTS")
        self.call(output=self.source, error="OUTPUT_EXISTS")
        target = self.work / "absent/new report"
        self.call(output=target, error="IO_OR_METADATA_ERROR")
        self.assertFalse((self.work / "absent").exists())

    def test_arguments_regular_input_and_inherited_python_environment(self):
        for args in ([], ["--svg", self.source], ["--unknown", "FICTIONAL_PRIVATE"]):
            self.call(args=args, error="ARGUMENTS_INVALID")
        self.call(args=["--help"], help_output=True)
        self.call(args=[self.output], probe="nul", error="INVALID_LOCAL_PATH")
        self.call(source=self.work, error="REGULAR_INPUT_REQUIRED")
        self.call(source=self.work / "missing.svg", error="IO_OR_METADATA_ERROR")
        poison = self.work / "poison imports"; poison.mkdir()
        (poison / "sitecustomize.py").write_bytes(b"raise RuntimeError('FICTIONAL_PRIVATE_IMPORT')\n")
        self.call(expected=self.expected(), allow=[self.output], env_extra={"PYTHONPATH": str(poison), "PYTHONHOME": str(poison)})

    def test_native_symlink_input_and_output_parents_refused(self):
        alias = self.work / "linked input.svg"
        self.symlink(alias, self.source)
        self.call(source=alias, error="LINKED_PATH_REJECTED")
        parent = self.work / "linked parent"
        self.symlink(parent, self.work, directory=True)
        self.call(source=parent / self.source.name, error="LINKED_PATH_REJECTED")
        self.call(output=parent / "new report", error="LINKED_PATH_REJECTED")

    @unittest.skipUnless(os.name == "nt", PROCESS_WINDOWS_REASON)
    def test_native_windows_junction_stream_and_device_paths_refused(self):
        junction = self.work / "junction"
        target = self.work / "ordinary target"; target.mkdir()
        (target / "fictional.svg").write_bytes(svg())
        done = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
                              capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace"))
        self.assertTrue(junction.is_junction())
        self.addCleanup(lambda: os.rmdir(junction) if junction.is_junction() else None)
        self.call(source=junction / "fictional.svg", error="LINKED_PATH_REJECTED")
        self.call(output=junction / "report", error="LINKED_PATH_REJECTED")
        self.call(source=str(self.source) + ":fictional", error="DEVICE_OR_STREAM_PATH_REJECTED")
        self.call(source="\\\\?\\" + str(self.source), error="LOCAL_ABSOLUTE_PATH_REQUIRED")

    @unittest.skipUnless(os.name != "nt", PROCESS_POSIX_REASON)
    def test_native_posix_fifo_and_socket_inputs_refused(self):
        fifo = self.work / "fifo"
        os.mkfifo(fifo)
        self.call(source=fifo, error="REGULAR_INPUT_REQUIRED")
        address = self.work / "socket"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(address))
            self.call(source=address, error="REGULAR_INPUT_REQUIRED")

    def test_manifest_failure_retains_reports_and_refuses_overwrite(self):
        wanted = self.expected()
        self.call(probe="manifest_failure", error="IO_OR_METADATA_ERROR", allow=[self.output])
        self.assertEqual({p.name for p in self.output.iterdir()}, {"report.json", "report.html"})
        self.assertEqual((self.output / "report.json").read_bytes(), (json.dumps(wanted, indent=2, ensure_ascii=True) + "\n").encode())
        static = StaticHTML(); static.feed((self.output / "report.html").read_text()); static.close()
        self.call(error="OUTPUT_EXISTS")

    def test_controlled_reads_detect_change_and_close_interrupted_descriptor(self):
        self.call(probe="short_read", expected=self.expected(), allow=[self.output])
        target = self.work / "read failure report"
        self.call(output=target, probe="read_failure", error="IO_OR_METADATA_ERROR")
        self.call(args=[self.source], probe="library_interrupt")
        before = self.source.read_bytes()
        self.call(output=target, probe="mutation", error="INPUT_CHANGED", ignore=[self.source])
        self.assertEqual(self.source.read_bytes(), before.replace(b"<svg", b"<svG", 1))
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
