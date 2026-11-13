"""Independent consumers of copied sparse tooling; image payloads remain unverified."""
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
RUNTIME = ("sparse_inspector.py", "binary_reader.py", "inspection_support.py", "examples/generate.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junctions_are_not_followed"
PROCESS_WINDOWS_REASON = "Native Windows junction fixture"
PROCESS_POSIX_ID = "test_download.Download.test_native_posix_special_files_and_sparse_metadata"
PROCESS_POSIX_REASON = "Native POSIX FIFO socket and sparse fixture"
PROCESS_SYMLINK_ID = "test_download.Download.test_native_symlink_inputs_and_output_parents"
PROCESS_SYMLINK_REASON = "Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS = {(PROCESS_POSIX_ID, PROCESS_POSIX_REASON)}
REQUIRED_POSIX_SKIPS = {(PROCESS_WINDOWS_ID, PROCESS_WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS = {(PROCESS_SYMLINK_ID, PROCESS_SYMLINK_REASON)}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


def header(blocks=1, chunks=1, block=4, **changes):
    """Author little-endian sparse base fields without importing the generator."""
    values = dict(magic=0xed26ff3a, major=1, minor=0, file_bytes=28, chunk_bytes=12,
                  block=block, blocks=blocks, chunks=chunks, checksum=0)
    values.update(changes)
    return struct.pack("<IHHHHIIII", *(values[key] for key in
                       ("magic", "major", "minor", "file_bytes", "chunk_bytes", "block", "blocks", "chunks", "checksum")))


def chunk(kind=0xcac1, blocks=1, body=b"DATA", reserved=0, size=None, extension=b""):
    length = 12 + len(extension) + len(body) if size is None else size
    return struct.pack("<HHII", kind, reserved, blocks, length) + extension + body


def image():
    return header(blocks=5, chunks=3) + chunk() + chunk(0xcac2, 2, b"FILL") + chunk(0xcac3, 2, b"")


PROBE = r'''
import argparse,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]);sys.path.insert(0,str(base))
import sparse_inspector as e
import binary_reader as b
import inspection_support as s
assert Path(e.__file__).resolve()==base/'sparse_inspector.py'
assert Path(b.__file__).resolve()==base/'binary_reader.py'
assert Path(s.__file__).resolve()==base/'inspection_support.py'
assert e.ImageReader is b.ImageReader and e.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py'
 assert g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
if kind.startswith('audit:'):
 e.Parser(description=e.__doc__)
 b'prewarm'.decode('utf-8')
 ranges=json.loads(kind[6:])
 assert ranges and all(type(a)is int and type(n)is int and a>=0 and n in (12,28) for a,n in ranges)
 source=Path(args[args.index('--image')+1]);output=Path(args[args.index('--output')+1])
 allowed={base/name for name in ('sparse_inspector.py','binary_reader.py','inspection_support.py','examples/generate.py')}
 allowed.add(source);allowed.update(output/name for name in ('report.json','report.html','MANIFEST.json'))
 original=os.read
 def bounded_read(fd,count):
  position=os.lseek(fd,0,os.SEEK_CUR)
  assert any(start<=position and position+count<=start+size for start,size in ranges),'PAYLOAD_OR_EXTENSION_READ_ATTEMPT'
  return original(fd,count)
 os.read=bounded_read
 def audit(event,values):
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open','ctypes.dlopen'):
   raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
  if event=='open' and not isinstance(values[0],int):assert Path(values[0]) in allowed,'UNEXPECTED_FILE_OPEN'
 sys.addaudithook(audit)
elif kind.startswith('limit:'):
 for name,value in json.loads(kind[6:]).items():
  assert name in ('MAX_IMAGE_BYTES','MAX_METADATA_BYTES','MAX_CHUNKS','MAX_BLOCK_BYTES','MAX_REPORT')
  if name=='MAX_IMAGE_BYTES':b.MAX_IMAGE_BYTES=value;e.MAX_IMAGE_BYTES=value
  elif name=='MAX_METADATA_BYTES':b.MAX_METADATA_BYTES=value
  else:setattr(s if name=='MAX_REPORT' else e,name,value)
elif kind=='write_failure':
 original=os.open
 def failed(path,*a,**kw):
  if Path(path).name=='MANIFEST.json':raise OSError('FICTIONAL_PRIVATE_WRITE_DETAIL')
  return original(path,*a,**kw)
 os.open=failed
elif kind=='changed_input':
 original=b.ImageReader.read_at;changed=False
 def changed_read(reader,*a):
  global changed
  raw=original(reader,*a)
  if not changed:
   changed=True
   with reader.path.open('ab') as out:out.write(b'fictional mutation')
  return raw
 b.ImageReader.read_at=changed_read
elif kind=='short_read':
 os.read=lambda *unused:b''
elif kind=='sparse':
 source=Path(args[0]);size=source.stat().st_size
 with b.ImageReader(source) as reader:
  assert reader.read_at(size-512,512,'tail')==b'\0'*512 and reader.bytes_read==512
 print(json.dumps(dict(status='SPARSE_METADATA_ONLY',image_bytes=size,metadata_bytes_read=512)));raise SystemExit(0)
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
        self.temp = tempfile.TemporaryDirectory(prefix="sparse-cli-", dir=parent)
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
        self.input = self.work / "fictional.sparse"
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
    def fixture(self, data=None):
        raw = image() if data is None else data
        self.input.write_bytes(raw)
        return raw
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot()
        prefix = ["-c", PROBE, self.copy, probe] if probe else [self.copy / "sparse_inspector.py"]
        done = self.run_child([*prefix, *args], env=env)
        self.assertEqual(done.stderr, b"", done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout, json.dumps(value, sort_keys=probe not in {"affinity", "sparse"}).encode() + NEWLINE)
        if error is not None:
            self.assertEqual(value, dict(status="INCOMPLETE", error=error)); code = 2
        elif probe == "affinity":
            self.assertEqual(value, dict(status="COPIED_RUNTIME_AFFINITY", dependencies=0)); code = 0
        elif probe == "sparse":
            self.assertEqual(value, dict(status="SPARSE_METADATA_ONLY", image_bytes=3 * 1024**3, metadata_bytes_read=512)); code = 0
        else:
            report = self.check_report(output)
            self.assertEqual(value, dict(status=report["status"], metadata_bytes_read=report["metadata_bytes_read"], findings=len(report["findings"]), coverage_issues=len(report["coverage_issues"])))
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
        required = {"schema_version", "tool", "scope", "image_bytes", "whole_image_hashed", "payload_crc_checked", "layout_walk_complete", "header", "chunks", "findings", "coverage_issues", "metadata_bytes_read", "metadata_regions", "status"}
        optional = {"observed_output_blocks", "accounted_input_bytes"} if report["layout_walk_complete"] else set()
        self.assertEqual(set(report), required | optional)
        self.assertEqual((report["tool"], report["schema_version"]), ("Android Sparse Image Inspector", 1))
        self.assertIs(report["whole_image_hashed"], False); self.assertIs(report["payload_crc_checked"], False)
        self.assertEqual(report["status"], "REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        self.assertEqual(report["metadata_bytes_read"], sum(r["bytes"] for r in report["metadata_regions"]))
        self.assertEqual(report["metadata_bytes_read"], (28 if report["metadata_regions"] else 0) + 12 * len(report["chunks"]))
        self.assertNotIn(str(self.work), raw.decode())
        markup = (output / "report.html").read_bytes()
        parsed = StaticHTML(); parsed.feed(markup.decode()); parsed.close()
        self.assertEqual(parsed.tags.count("html"), 1); self.assertEqual(parsed.csp, ["default-src 'none'; style-src 'unsafe-inline'"])
        self.assertIn(html.escape(raw.decode(), quote=True).encode(), markup)
        members = {name: (output / name).read_bytes() for name in ("report.json", "report.html")}
        expected = dict(schema_version=1, files=[dict(path=name, bytes=len(data), sha256=sha(data)) for name, data in sorted(members.items())])
        self.assertEqual((output / "MANIFEST.json").read_bytes(), encoded(expected))
        return report
    def report(self, **kwargs):
        return self.call(["--image", self.input, "--output", self.output], output=self.output, allow=[self.output], **kwargs)
    def codes(self, report, coverage=False):
        return {row["code"] for row in report["coverage_issues" if coverage else "findings"]}
    def new_output(self, suffix):
        self.output = self.work / ("new report " + str(suffix))
    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314 and os.environ.get("OUTLANDS_SPARSE_REQUIRE_LINKS") != "1":
                self.skipTest(PROCESS_SYMLINK_REASON)
            raise
    def test_copied_runtime_affinity_and_help(self):
        self.call([], probe="affinity")
        for script in (self.copy / "sparse_inspector.py", self.copy / "examples/generate.py"):
            before = self.snapshot(); done = self.run_child([script, "--help"])
            self.assertEqual((done.returncode, done.stderr), (0, b"")); self.assertIn(b"--output", done.stdout)
            self.assertEqual(self.snapshot(), before)
    def test_generator_cli_three_examples_and_new_only_destination(self):
        out = self.work / "generated"; before = self.snapshot()
        done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (0, b"", b'{"status":"GENERATED","files":3}' + NEWLINE))
        self.assertEqual({k: self.snapshot().get(k) for k in before}, before)
        self.assertEqual({p.name for p in out.iterdir()}, {"valid.sparse", "crc-unverified.sparse", "truncated.sparse"})
        for index, (name, expected) in enumerate((("valid", "NO_SCOPE_FINDINGS"), ("crc-unverified", "REVIEW_REQUIRED"), ("truncated", "REVIEW_REQUIRED"))):
            self.input = out / (name + ".sparse"); self.new_output(index); self.assertEqual(self.report()["status"], expected)
        before = self.snapshot(); done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (2, b"", json.dumps(dict(status="INCOMPLETE", error="OUTPUT_EXISTS"), sort_keys=True).encode() + NEWLINE))
        self.assertEqual(self.snapshot(), before)
    def test_raw_header_regions_and_independent_manifest_hashes(self):
        raw = self.fixture(header() + chunk()); report = self.report()
        self.assertEqual((report["status"], report["metadata_bytes_read"], report["header"]["declared_output_bytes"]), ("NO_SCOPE_FINDINGS", 40, "4"))
        self.assertEqual([(r["id"], r["offset"], r["bytes"]) for r in report["metadata_regions"]], [("file-header", 0, 28), ("chunk-1", 28, 12)])
        for region in report["metadata_regions"]:
            self.assertEqual(region["sha256"], sha(raw[region["offset"]:region["offset"] + region["bytes"]]))
    def test_raw_fill_dontcare_block_accounting_is_exact(self):
        self.fixture(); report = self.report()
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        self.assertEqual([row["kind"] for row in report["chunks"]], ["RAW", "FILL", "DONT_CARE"])
        self.assertEqual([row["output_start_block"] for row in report["chunks"]], [0, 1, 3])
        self.assertEqual((report["observed_output_blocks"], report["header"]["declared_output_bytes"], report["accounted_input_bytes"]), (5, "20", 72))
    def test_crc32_payloads_stay_unverified_and_unread(self):
        observed = []
        for index, stored in enumerate((b"\0" * 4, b"\xff" * 4)):
            self.fixture(header(blocks=1, chunks=2) + chunk() + chunk(0xcac4, 0, stored)); self.new_output(index)
            report = self.report(); observed.append(report)
            self.assertEqual((report["status"], report["findings"], self.codes(report, True)), ("REVIEW_REQUIRED", [], {"CRC32_UNVERIFIED"}))
            self.assertIs(report["payload_crc_checked"], False); self.assertEqual(report["observed_output_blocks"], 1)
        self.assertEqual(observed[0], observed[1])
    def test_nonzero_image_checksum_is_a_boolean_unverified_declaration(self):
        self.fixture(header(checksum=0xfedcba98) + chunk()); report = self.report()
        self.assertIs(report["header"]["image_checksum_declared"], True)
        self.assertEqual(self.codes(report, True), {"IMAGE_CHECKSUM_UNVERIFIED"})
        self.assertIs(report["payload_crc_checked"], False); self.assertNotIn("4275878552", json.dumps(report))
    def test_crc_nonzero_output_blocks_are_flagged_and_not_counted(self):
        self.fixture(header(blocks=1, chunks=2) + chunk() + chunk(0xcac4, 3, b"CRC!")); report = self.report()
        self.assertEqual(self.codes(report), {"CRC32_OUTPUT_BLOCKS_NONZERO"})
        self.assertEqual(self.codes(report, True), {"CRC32_UNVERIFIED"})
        self.assertEqual(report["observed_output_blocks"], 1)
    def test_audit_reads_only_base_headers_not_payload_or_extensions(self):
        extension = b"</pre><script>FICTIONAL_PRIVATE</script>"
        pieces = [chunk(0xcac1, 1, b"RAW!", extension=extension), chunk(0xcac2, 2, b"FILL", extension=extension), chunk(0xcac3, 2, b"", extension=extension), chunk(0xcac4, 0, b"BAD!", extension=extension)]
        offset = 28 + len(extension); ranges = [(0, 28)]
        for value in pieces:
            ranges.append((offset, 12)); offset += len(value)
        raw = header(blocks=5, chunks=4, minor=1, file_bytes=28 + len(extension), chunk_bytes=12 + len(extension)) + extension + b"".join(pieces)
        self.fixture(raw); report = self.report(probe="audit:" + json.dumps(ranges))
        self.assertEqual(report["metadata_bytes_read"], 76)
        self.assertEqual([(r["offset"], r["bytes"]) for r in report["metadata_regions"]], ranges)
        self.assertEqual(report["findings"], [])
        for name in ("report.json", "report.html", "MANIFEST.json"):
            content = (self.output / name).read_bytes(); self.assertNotIn(b"FICTIONAL_PRIVATE", content); self.assertNotIn(b"<script>", content)
    def test_empty_layout_has_complete_zero_accounting(self):
        self.fixture(header(blocks=0, chunks=0)); report = self.report()
        self.assertEqual((report["status"], report["observed_output_blocks"], report["accounted_input_bytes"], report["metadata_bytes_read"]), ("NO_SCOPE_FINDINGS", 0, 28, 28))
        self.assertEqual(report["chunks"], [])
    def test_huge_declared_dontcare_output_uses_decimal_without_expansion(self):
        self.fixture(header(blocks=0xffffffff) + chunk(0xcac3, 0xffffffff, b"")); report = self.report(probe="audit:" + json.dumps([(0, 28), (28, 12)]))
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        self.assertEqual((report["image_bytes"], report["metadata_bytes_read"], report["header"]["declared_output_bytes"]), (40, 40, "17179869180"))
        self.assertEqual(report["observed_output_blocks"], 0xffffffff)
    def test_huge_raw_declaration_stops_without_payload_allocation(self):
        self.fixture(header(blocks=0xffffffff) + chunk(blocks=0xffffffff, body=b"", size=0xffffffff)); report = self.report()
        self.assertEqual(self.codes(report), {"CHUNK_DATA_TRUNCATED"})
        self.assertEqual(report["metadata_bytes_read"], 40); self.assertFalse(report["layout_walk_complete"])
        self.assertNotIn("observed_output_blocks", report)
    def test_truncated_file_header_and_bad_signature_are_explicit_review(self):
        for index, (data, code, read) in enumerate(((b"fictional", "SPARSE_HEADER_TRUNCATED", 0), (header(magic=0) + chunk(), "SPARSE_SIGNATURE_MISMATCH", 28))):
            self.fixture(data); self.new_output(index); report = self.report()
            self.assertEqual(self.codes(report), {code}); self.assertEqual(report["metadata_bytes_read"], read); self.assertIsNone(report["header"])
    def test_unsupported_major_stops_before_chunk_headers(self):
        self.fixture(header(major=2) + chunk()); report = self.report(probe="audit:" + json.dumps([(0, 28)]))
        self.assertEqual(self.codes(report, True), {"SPARSE_MAJOR_VERSION_UNSUPPORTED"})
        self.assertEqual((report["chunks"], report["metadata_bytes_read"], report["layout_walk_complete"]), ([], 28, False))
    def test_minor_and_extended_headers_remain_explicit_coverage(self):
        self.fixture(header(minor=1, file_bytes=32, chunk_bytes=16) + b"EXT!" + chunk(extension=b"SKIP")); report = self.report()
        self.assertEqual(report["findings"], [])
        self.assertEqual(self.codes(report, True), {"SPARSE_MINOR_VERSION_UNINSPECTED", "FILE_HEADER_EXTENSION_UNINSPECTED", "CHUNK_HEADER_EXTENSION_UNINSPECTED"})
        self.assertTrue(report["layout_walk_complete"]); self.assertEqual(report["metadata_bytes_read"], 40)
    def test_invalid_header_sizes_and_out_of_file_extension_stop(self):
        for index, (fields, code) in enumerate((({"file_bytes": 27}, "SPARSE_HEADER_SIZE_INVALID"), ({"chunk_bytes": 11}, "SPARSE_HEADER_SIZE_INVALID"), ({"file_bytes": 200}, "SPARSE_HEADER_TRUNCATED"))):
            self.fixture(header(**fields) + chunk()); self.new_output(index); report = self.report()
            self.assertEqual(self.codes(report), {code}); self.assertEqual(report["chunks"], []); self.assertFalse(report["layout_walk_complete"])
    def test_invalid_block_sizes_are_findings_without_chunk_reads(self):
        for size in (0, 1, 3, 6):
            self.fixture(header(block=size) + chunk()); self.new_output(size); report = self.report()
            self.assertEqual(self.codes(report), {"SPARSE_BLOCK_SIZE_INVALID"}); self.assertEqual(report["metadata_bytes_read"], 28)
    def test_truncated_chunk_header_and_declared_extra_chunk_stop(self):
        cases = (header() + b"\0" * 11, header(chunks=2) + chunk(), header(chunk_bytes=24) + chunk())
        for index, data in enumerate(cases):
            self.fixture(data); self.new_output(index); report = self.report()
            self.assertIn("CHUNK_HEADER_TRUNCATED", self.codes(report)); self.assertFalse(report["layout_walk_complete"])
    def test_chunk_body_truncation_and_size_below_header_stop(self):
        for index, (data, code) in enumerate(((header() + chunk()[:-1], "CHUNK_DATA_TRUNCATED"), (header() + chunk(size=11), "CHUNK_SIZE_BELOW_HEADER"))):
            self.fixture(data); self.new_output(index); report = self.report()
            self.assertEqual(self.codes(report), {code}); self.assertFalse(report["layout_walk_complete"])
    def test_each_known_chunk_payload_size_rule_is_checked(self):
        for index, (kind, body) in enumerate(((0xcac1, b"ABC"), (0xcac2, b"ABC"), (0xcac3, b"X"), (0xcac4, b"ABC"))):
            blocks = 0 if kind == 0xcac4 else 1
            self.fixture(header(blocks=blocks) + chunk(kind, blocks, body)); self.new_output(index); report = self.report()
            self.assertEqual(self.codes(report), {"CHUNK_PAYLOAD_SIZE_MISMATCH"}); self.assertTrue(report["layout_walk_complete"])
            self.assertIs(report["payload_crc_checked"], False)
    def test_reserved_fields_and_unknown_type_have_distinct_findings(self):
        self.fixture(header() + chunk(reserved=1)); self.assertEqual(self.codes(self.report()), {"CHUNK_RESERVED_NONZERO"})
        self.fixture(header() + chunk(kind=0xcaff)); self.new_output("unknown"); report = self.report()
        self.assertEqual(self.codes(report, True), {"CHUNK_TYPE_UNSUPPORTED"}); self.assertFalse(report["layout_walk_complete"])
        self.assertNotIn("OUTPUT_BLOCK_COUNT_MISMATCH", self.codes(report)); self.assertNotIn("observed_output_blocks", report)
    def test_output_block_mismatch_excess_and_trailing_bytes_are_separate(self):
        for index, (data, expected) in enumerate(((header(blocks=0) + chunk(), {"OUTPUT_BLOCK_COUNT_EXCEEDED", "OUTPUT_BLOCK_COUNT_MISMATCH"}), (header(blocks=2) + chunk(), {"OUTPUT_BLOCK_COUNT_MISMATCH"}), (header() + chunk() + b"trailer", {"TRAILING_INPUT_BYTES"}))):
            self.fixture(data); self.new_output(index); report = self.report()
            self.assertEqual(self.codes(report), expected); self.assertTrue(report["layout_walk_complete"])
    def test_input_declared_output_chunk_block_metadata_report_limits_refuse(self):
        cases = ((image(), {"MAX_IMAGE_BYTES": 20}, "IMAGE_SIZE_LIMIT"), (image(), {"MAX_METADATA_BYTES": 28}, "METADATA_BYTE_LIMIT"), (header(chunks=4001) + chunk(), {}, "CHUNK_COUNT_LIMIT"), (header(block=1024**2 + 4) + chunk(), {}, "BLOCK_SIZE_LIMIT"), (header(block=1024**2, blocks=0xffffffff) + chunk(), {}, "DECLARED_OUTPUT_SIZE_LIMIT"), (image(), {"MAX_REPORT": 100}, "REPORT_BYTE_LIMIT"))
        for index, (data, limits, error) in enumerate(cases):
            self.fixture(data); self.new_output(index)
            self.report(probe="limit:" + json.dumps(limits), error=error); self.assertFalse(self.output.exists())
    def test_invalid_arguments_missing_empty_directory_and_private_paths_refuse(self):
        self.fixture()
        for args in ([], ["--private-unknown=value"], ["--image", self.input], ["--image", self.input, "--output", self.output, "--unknown", "private-value"]):
            self.call(args, error="ARGUMENTS_INVALID")
        for path, error in (("relative.sparse", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (self.work / ".." / "fictional.sparse", "LOCAL_ABSOLUTE_PATH_REQUIRED"), ("//fictional/share/image", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (str(self.input) + "\nprivate", "INVALID_LOCAL_PATH"), (self.copy, "REGULAR_FILE_REQUIRED"), (self.work / "missing", "IO_OR_INPUT_ERROR")):
            self.call(["--image", path, "--output", self.output], error=error)
        self.fixture(b""); self.report(error="IMAGE_SIZE_LIMIT")
        if os.name == "nt": self.call(["--image", str(self.input) + ":stream", "--output", self.output], error="DEVICE_OR_STREAM_PATH_REJECTED")
    def test_existing_output_input_and_missing_parent_are_not_overwritten(self):
        self.fixture(); self.report(); self.report(error="OUTPUT_EXISTS")
        self.call(["--image", self.input, "--output", self.input], error="OUTPUT_EXISTS")
        self.call(["--image", self.input, "--output", self.work], error="OUTPUT_EXISTS")
        self.call(["--image", self.input, "--output", self.work / "missing" / "report"], error="IO_OR_INPUT_ERROR")
    def test_partial_report_failure_is_fixed_private_error_and_not_complete(self):
        self.fixture(); self.report(probe="write_failure", error="IO_OR_INPUT_ERROR")
        self.assertEqual({p.name for p in self.output.iterdir()}, {"report.json", "report.html"}); self.report(error="OUTPUT_EXISTS")
    def test_mutated_input_and_short_read_refuse_before_reports(self):
        self.fixture(); self.report(probe="changed_input", error="INPUT_CHANGED", ignore=[self.input])
        self.assertTrue(self.input.read_bytes().endswith(b"fictional mutation")); self.assertFalse(self.output.exists())
        self.fixture(); self.report(probe="short_read", error="INPUT_CHANGED"); self.assertFalse(self.output.exists())
    def test_native_symlink_inputs_and_output_parents(self):
        self.fixture(); linked = self.work / "linked.sparse"; self.symlink(linked, self.input)
        self.call(["--image", linked, "--output", self.output], error="LINKED_PATH_REJECTED")
        directory = self.work / "linked directory"; self.symlink(directory, self.work, directory=True)
        self.call(["--image", directory / self.input.name, "--output", self.output], error="LINKED_PATH_REJECTED")
        self.call(["--image", self.input, "--output", directory / "report"], error="LINKED_PATH_REJECTED")
    def test_hardlink_and_hostile_python_environment_preserve_input_identity(self):
        self.fixture(); linked = self.work / "hardlinked.sparse"; os.link(self.input, linked)
        self.assertTrue(os.path.samefile(linked, self.input))
        hostile = self.work / "hostile imports"; hostile.mkdir()
        for name in ("sitecustomize.py", "usercustomize.py", "json.py", "struct.py"):
            (hostile / name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env = dict(self.env, PYTHONPATH=str(hostile), PYTHONHOME=str(hostile), PYTHONSTARTUP=str(hostile / "sitecustomize.py"))
        self.call(["--image", linked, "--output", self.output], output=self.output, allow=[self.output], env=env)
    @unittest.skipUnless(os.name == "nt", PROCESS_WINDOWS_REASON)
    def test_native_windows_junctions_are_not_followed(self):
        self.fixture(); junction = self.work / "junction"
        done = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(self.work)], capture_output=True, timeout=15)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace")); self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
        self.call(["--image", junction / self.input.name, "--output", self.output], error="LINKED_PATH_REJECTED")
        self.call(["--image", self.input, "--output", junction / "report"], error="LINKED_PATH_REJECTED")
    @unittest.skipUnless(os.name != "nt", PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_metadata(self):
        fifo = self.work / "fictional.fifo"; os.mkfifo(fifo)
        connection = socket.socket(socket.AF_UNIX); connection.bind(str(self.work / "fictional.sock")); self.addCleanup(connection.close)
        for path in (fifo, self.work / "fictional.sock"):
            self.call(["--image", path, "--output", self.output], error="REGULAR_FILE_REQUIRED")
        self.input = self.work / "large fictional sparse.img"
        with self.input.open("wb") as stream: stream.truncate(3 * 1024**3)
        self.call([self.input], probe="sparse")


if __name__ == "__main__":
    unittest.main()
