"""Independent consumers of copied boot metadata tooling; no image executes."""
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
RUNTIME = ("boot_inspector.py", "binary_reader.py", "inspection_support.py", "examples/generate.py")
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


def padded(size, page):
    return size + (-size % page)


def boot_image(version=4, kernel=11, ramdisk=7, signature=9):
    """Author documented numeric fields without importing the inspected code."""
    sizes = [1580 if version == 3 else 1584, kernel, ramdisk]
    if version == 4:
        sizes.append(signature)
    data = bytearray(sum(padded(n, 4096) for n in sizes))
    data[:8] = b"ANDROID!"
    struct.pack_into("<IIII", data, 8, kernel, ramdisk, 0, sizes[0])
    struct.pack_into("<I", data, 40, version)
    if version == 4:
        struct.pack_into("<I", data, 1580, signature)
    return data


def vendor_image(version=4, page=4096, ramdisk=12, dtb=5, entries=None, bootconfig=6):
    """Author fictional v3/v4 layout and numeric fragment entries independently."""
    if entries is None:
        entries = [(5, 0, 1), (7, 5, 3)]
    header = 2112 if version == 3 else 2128
    table_bytes = 108 * len(entries)
    sizes = [header, ramdisk, dtb]
    if version == 4:
        sizes += [table_bytes, bootconfig]
    data = bytearray(sum(padded(n, page) for n in sizes))
    data[:8] = b"VNDRBOOT"
    struct.pack_into("<II", data, 8, version, page)
    struct.pack_into("<I", data, 24, ramdisk)
    struct.pack_into("<II", data, 2096, header, dtb)
    if version == 4:
        struct.pack_into("<IIII", data, 2112, table_bytes, len(entries), 108, bootconfig)
        start = sum(padded(n, page) for n in sizes[:3])
        for index, row in enumerate(entries):
            struct.pack_into("<III", data, start + 108 * index, *row)
    return data


def edited(data, offset, value):
    data = bytearray(data)
    struct.pack_into("<I", data, offset, value)
    return data


def image():
    return boot_image()


PROBE = r'''
import argparse,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import boot_inspector as e
import binary_reader as b
import inspection_support as s
assert Path(e.__file__).resolve()==base/'boot_inspector.py'
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
 assert ranges and all(type(a)is int and type(n)is int and a>=0 and 0<n<=221184 for a,n in ranges)
 source=Path(args[args.index('--image')+1]);output=Path(args[args.index('--output')+1])
 allowed={base/name for name in ('boot_inspector.py','binary_reader.py','inspection_support.py','examples/generate.py')}
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
  assert name in ('MAX_IMAGE_BYTES','MAX_METADATA_BYTES','MAX_TABLE_ENTRIES','MAX_REPORT')
  if name=='MAX_IMAGE_BYTES':b.MAX_IMAGE_BYTES=value
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
        self.temp = tempfile.TemporaryDirectory(prefix="boot-cli-", dir=parent)
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
        self.input = self.work / "fictional.img"
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
        prefix = ["-c", PROBE, self.copy, probe] if probe else [self.copy / "boot_inspector.py"]
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
        required = {"schema_version", "tool", "scope", "image_bytes", "image_kind", "sections", "ramdisk_fragments", "ramdisk_table_inspected", "whole_image_hashed", "payloads_inspected", "strings_and_hardware_identifiers_included", "findings", "coverage_issues", "metadata_bytes_read", "metadata_regions", "status"}
        optional = {"header_version", "header_bytes", "page_size", "table_declared_entries", "table_entry_bytes", "declared_padded_layout_bytes", "trailing_bytes"}
        self.assertTrue(required <= set(report) <= required | optional)
        self.assertEqual((report["tool"], report["schema_version"]), ("Boot / Vendor Boot Header Inspector", 1))
        for flag in ("whole_image_hashed", "payloads_inspected", "strings_and_hardware_identifiers_included"):
            self.assertIs(report[flag], False)
        self.assertEqual(report["status"], "REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        self.assertEqual(report["metadata_bytes_read"], sum(r["bytes"] for r in report["metadata_regions"]))
        self.assertEqual(bool(report["sections"]), "declared_padded_layout_bytes" in report)
        if report["sections"]:
            self.assertEqual(report["sections"][0]["offset_bytes"], 0)
            for section in report["sections"]:
                self.assertEqual(set(section), {"role", "offset_bytes", "declared_bytes", "padded_end_bytes", "within_file"})
                self.assertEqual(section["within_file"], section["offset_bytes"] + section["declared_bytes"] <= report["image_bytes"])
                self.assertEqual(section["padded_end_bytes"] % report["page_size"], 0)
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
            if os.name == "nt" and getattr(error, "winerror", None) == 1314 and os.environ.get("OUTLANDS_BOOT_REQUIRE_LINKS") != "1":
                self.skipTest(PROCESS_SYMLINK_REASON)
            raise


    def test_copied_runtime_affinity_and_help(self):
        self.call([], probe="affinity")
        for script in (self.copy / "boot_inspector.py", self.copy / "examples/generate.py"):
            before = self.snapshot(); done = self.run_child([script, "--help"])
            self.assertEqual((done.returncode, done.stderr), (0, b"")); self.assertIn(b"--output", done.stdout)
            self.assertEqual(self.snapshot(), before)
    def test_generator_cli_six_fictional_images_and_new_only_destination(self):
        out = self.work / "generated"; before = self.snapshot()
        done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (0, b"", b"Generated fictional metadata fixtures: 6" + NEWLINE))
        self.assertEqual({k: self.snapshot().get(k) for k in before}, before)
        names = {"boot-v3.img", "boot-v4.img", "vendor-v3.img", "vendor-v4.img", "truncated-vendor.img", "unsupported-legacy.img"}
        self.assertEqual({p.name for p in out.iterdir()}, names)
        for name in sorted(names):
            self.input = out / name; self.new_output(name)
            self.assertEqual(self.report()["status"], "REVIEW_REQUIRED" if name.startswith(("truncated", "unsupported")) else "NO_SCOPE_FINDINGS")
        before = self.snapshot(); done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (2, b"", json.dumps(dict(status="INCOMPLETE", error="OUTPUT_EXISTS"), sort_keys=True).encode() + NEWLINE))
        self.assertEqual(self.snapshot(), before)
    def test_boot_v3_exact_numeric_sections_and_metadata_hashes(self):
        raw = self.fixture(boot_image(3)); report = self.report()
        self.assertEqual((report["status"], report["image_kind"], report["header_version"], report["metadata_bytes_read"]), ("NO_SCOPE_FINDINGS", "boot", 3, 1632))
        self.assertEqual([(r["role"], r["offset_bytes"], r["declared_bytes"], r["padded_end_bytes"]) for r in report["sections"]], [("header", 0, 1580, 4096), ("kernel", 4096, 11, 8192), ("ramdisk", 8192, 7, 12288)])
        for region in report["metadata_regions"]:
            self.assertEqual(region["sha256"], sha(raw[region["offset_bytes"]:region["offset_bytes"] + region["bytes"]]))
    def test_boot_v4_signature_offsets_and_repeated_header_read_counts(self):
        self.fixture(); report = self.report()
        self.assertEqual((report["status"], report["header_version"], report["metadata_bytes_read"], report["declared_padded_layout_bytes"]), ("NO_SCOPE_FINDINGS", 4, 1636, 16384))
        self.assertEqual(report["sections"][-1], dict(role="boot_signature", offset_bytes=12288, declared_bytes=9, padded_end_bytes=16384, within_file=True))
        self.assertEqual([(r["offset_bytes"], r["bytes"]) for r in report["metadata_regions"]], [(0, 8), (0, 44), (0, 1584)])
    def test_vendor_v3_numeric_layout_and_omitted_table(self):
        self.fixture(vendor_image(3)); report = self.report()
        self.assertEqual((report["status"], report["image_kind"], report["header_version"], report["metadata_bytes_read"]), ("NO_SCOPE_FINDINGS", "vendor_boot", 3, 2132))
        self.assertEqual([(r["role"], r["offset_bytes"], r["declared_bytes"], r["padded_end_bytes"]) for r in report["sections"]], [("header", 0, 2112, 4096), ("vendor_ramdisk", 4096, 12, 8192), ("dtb", 8192, 5, 12288)])
        self.assertFalse(report["ramdisk_table_inspected"]); self.assertEqual(report["ramdisk_fragments"], [])
    def test_vendor_v4_table_and_fragment_numeric_boundaries(self):
        raw = self.fixture(vendor_image()); report = self.report()
        self.assertEqual((report["status"], report["metadata_bytes_read"]), ("NO_SCOPE_FINDINGS", 2364))
        self.assertEqual([r["offset_bytes"] for r in report["sections"]], [0, 4096, 8192, 12288, 16384])
        self.assertEqual([(r["offset_bytes"], r["declared_bytes"], r["type"], r["within_ramdisk_section"]) for r in report["ramdisk_fragments"]], [(0, 5, 1, True), (5, 7, 3, True)])
        self.assertTrue(report["ramdisk_table_inspected"])
        for region in report["metadata_regions"]:
            self.assertEqual(region["sha256"], sha(raw[region["offset_bytes"]:region["offset_bytes"] + region["bytes"]]))
    def test_vendor_header_can_span_multiple_small_pages(self):
        self.fixture(vendor_image(3, page=512, ramdisk=0, dtb=0)); report = self.report()
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        self.assertEqual([r["offset_bytes"] for r in report["sections"]], [0, 2560, 2560])
        self.assertEqual((report["declared_padded_layout_bytes"], report["image_bytes"]), (2560, 2560))
    def test_vendor_supported_page_sizes_have_hand_checked_table_offsets(self):
        cases = ((512, [0, 2560, 3072, 3584, 4096]), (1024, [0, 3072, 4096, 5120, 6144]), (4096, [0, 4096, 8192, 12288, 16384]), (65536, [0, 65536, 131072, 196608, 262144]))
        for page, expected in cases:
            self.fixture(vendor_image(page=page)); self.new_output(page); report = self.report()
            self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual([r["offset_bytes"] for r in report["sections"]], expected)
            self.assertEqual(report["metadata_bytes_read"], 2364)
    def test_zero_components_and_empty_vendor_table_are_declarations(self):
        for index, data in enumerate((boot_image(kernel=0, ramdisk=0, signature=0), vendor_image(ramdisk=0, dtb=0, entries=[], bootconfig=0))):
            self.fixture(data); self.new_output(index); report = self.report()
            self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
            self.assertEqual(report["declared_padded_layout_bytes"], 4096)
            self.assertTrue(all(r["offset_bytes"] == 4096 for r in report["sections"][1:])); self.assertFalse(report["ramdisk_table_inspected"])
    def test_audit_reads_only_headers_and_table_not_payload_padding_or_tail(self):
        marker = b"</pre><script>FICTIONAL_PRIVATE</script>"
        for index, data in enumerate((boot_image(), vendor_image())):
            for offset in ((4096, 8192, 12288, 5000) if index == 0 else (4096, 8192, 16384, 5000)):
                data[offset:offset + len(marker)] = marker
            data[44 if index == 0 else 28:44 + len(marker) if index == 0 else 28 + len(marker)] = marker
            if index == 1:
                data[12300:12300 + len(marker)] = marker
            ranges = [(0, 1584)] if index == 0 else [(0, 2128), (12288, 216)]
            self.fixture(data); self.new_output(index); report = self.report(probe="audit:" + json.dumps(ranges))
            self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
            self.assertEqual(report["metadata_bytes_read"], 1636 if index == 0 else 2364)
            for name in ("report.json", "report.html", "MANIFEST.json"):
                content = (self.output / name).read_bytes(); self.assertNotIn(b"FICTIONAL_PRIVATE", content); self.assertNotIn(b"<script>", content)
    def test_payload_changes_preserve_complete_metadata_observations(self):
        for index, initial in enumerate((boot_image(), vendor_image())):
            self.fixture(initial); self.new_output(str(index) + "a"); before = self.report()
            changed = bytearray(initial)
            for offset in ((4096, 8192, 12288, 6000) if index == 0 else (4096, 8192, 16384, 6000)):
                changed[offset] ^= 0x5a
            self.fixture(changed); self.new_output(str(index) + "b"); self.assertEqual(self.report(), before)
    def test_unsupported_header_versions_do_not_infer_layouts(self):
        for index, (data, offset) in enumerate(((boot_image(), 40), (vendor_image(), 8))):
            for version in (0, 2, 5, 0xffffffff):
                self.fixture(edited(data, offset, version)); self.new_output(str(index) + "-" + str(version)); report = self.report()
                self.assertEqual(self.codes(report, True), {"HEADER_VERSION_UNSUPPORTED"}); self.assertEqual(report["sections"], [])
                self.assertEqual(report["metadata_bytes_read"], 52 if index == 0 else 20)
    def test_unknown_magic_and_short_headers_produce_bounded_review(self):
        cases = ((b"unknown!", "IMAGE_MAGIC_UNRECOGNIZED"), (b"A", "HEADER_TRUNCATED"), (b"ANDROID!", "HEADER_TRUNCATED"), (boot_image()[:100], "HEADER_TRUNCATED"), (b"VNDRBOOT", "HEADER_TRUNCATED"), (vendor_image()[:100], "HEADER_TRUNCATED"))
        for index, (data, code) in enumerate(cases):
            self.fixture(data); self.new_output(index); report = self.report()
            self.assertEqual(self.codes(report), {code}); self.assertEqual(report["sections"], [])
    def test_declared_header_size_extensions_and_reserved_boot_fields(self):
        for index, (data, offset, expected) in enumerate(((boot_image(), 20, 1584), (vendor_image(), 2096, 2128))):
            for delta, code in ((-1, "HEADER_SIZE_INVALID"), (4, "HEADER_SIZE_UNSUPPORTED")):
                self.fixture(edited(data, offset, expected + delta)); self.new_output(str(index) + "-" + str(delta)); report = self.report()
                self.assertIn(code, self.codes(report, delta > 0)); self.assertEqual(report["sections"], [])
        self.fixture(edited(boot_image(), 24, 1)); self.new_output("reserved"); self.assertEqual(self.codes(self.report()), {"RESERVED_HEADER_NONZERO"})
    def test_zero_or_unsupported_vendor_pages_do_not_guess_alignment(self):
        for page in (0, 1, 768, 131072, 0xffffffff):
            self.fixture(edited(vendor_image(), 12, page)); self.new_output(page); report = self.report()
            self.assertIn("PAGE_SIZE_INVALID" if page == 0 else "PAGE_SIZE_UNSUPPORTED", self.codes(report, page != 0)); self.assertEqual(report["sections"], [])
    def test_component_extent_padding_and_trailing_coverage_are_distinct(self):
        data = boot_image()
        for index, (raw, code, coverage) in enumerate(((data[:8195], "SECTION_OUTSIDE_FILE", False), (data[:12297], "SECTION_PADDING_TRUNCATED", False), (data + b"uninspected tail", "TRAILING_BYTES_UNINSPECTED", True))):
            self.fixture(raw); self.new_output(index); report = self.report(); self.assertIn(code, self.codes(report, coverage))
            self.assertEqual(report["metadata_bytes_read"], 1636)
    def test_huge_component_declarations_do_not_allocate_or_read_them(self):
        for index, data in enumerate((edited(boot_image(), 8, 0xffffffff), edited(vendor_image(), 24, 0xffffffff))):
            self.fixture(data); self.new_output(index); report = self.report()
            self.assertIn("SECTION_OUTSIDE_FILE", self.codes(report)); self.assertLess(report["metadata_bytes_read"], 3000)
            self.assertFalse(report["ramdisk_table_inspected"])
    def test_vendor_table_product_mismatch_does_not_read_entries(self):
        self.fixture(edited(vendor_image(), 2112, 217)); report = self.report()
        self.assertIn("TABLE_LENGTH_MISMATCH", self.codes(report)); self.assertFalse(report["ramdisk_table_inspected"])
        self.assertEqual(report["metadata_bytes_read"], 2148)
    def test_vendor_extended_entry_stride_remains_uninspected_coverage(self):
        self.fixture(edited(edited(vendor_image(), 2120, 112), 2112, 224)); report = self.report()
        self.assertEqual(self.codes(report, True), {"TABLE_ENTRY_SIZE_UNSUPPORTED"}); self.assertFalse(report["ramdisk_table_inspected"])
        self.assertEqual(report["ramdisk_fragments"], [])
    def test_vendor_table_count_limits_are_fixed_errors_before_reports(self):
        for count in (2049, 0xffffffff):
            self.fixture(edited(vendor_image(), 2116, count)); self.new_output(count); self.report(error="TABLE_ENTRY_LIMIT"); self.assertFalse(self.output.exists())
    def test_vendor_truncated_table_is_not_partially_read(self):
        self.fixture(vendor_image()[:12400]); report = self.report()
        self.assertIn("SECTION_OUTSIDE_FILE", self.codes(report)); self.assertFalse(report["ramdisk_table_inspected"])
        self.assertNotIn("ramdisk-table", {r["id"] for r in report["metadata_regions"]}); self.assertEqual(report["metadata_bytes_read"], 2148)
    def test_fragment_outside_overlap_gap_and_unknown_type_are_observations(self):
        cases = (([(5, 0, 1), (8, 5, 3)], "FRAGMENT_OUTSIDE_RAMDISK_SECTION", False), ([(5, 0, 1), (7, 4, 3)], "FRAGMENT_OVERLAP_OBSERVED", False), ([(5, 0, 1), (6, 6, 3)], "FRAGMENT_GAP_OBSERVED", False), ([(5, 0, 99), (7, 5, 3)], "FRAGMENT_TYPE_UNSUPPORTED", True))
        for index, (entries, code, coverage) in enumerate(cases):
            self.fixture(vendor_image(entries=entries)); self.new_output(index); report = self.report(); self.assertIn(code, self.codes(report, coverage))
            self.assertEqual([(r["declared_bytes"], r["offset_bytes"], r["type"]) for r in report["ramdisk_fragments"]], entries)
    def test_fragment_order_zero_lengths_and_empty_coverage_are_literal(self):
        for index, entries in enumerate(([(7, 5, 3), (5, 0, 1)], [(0, 12, 0), (12, 0, 1)])):
            self.fixture(vendor_image(entries=entries)); self.new_output(index); report = self.report()
            self.assertEqual(report["status"], "NO_SCOPE_FINDINGS"); self.assertEqual([(r["declared_bytes"], r["offset_bytes"], r["type"]) for r in report["ramdisk_fragments"]], entries)
        self.fixture(vendor_image(entries=[])); self.new_output("empty"); report = self.report()
        self.assertIn("FRAGMENT_COVERAGE_MISMATCH", self.codes(report)); self.assertFalse(report["ramdisk_table_inspected"])
    def test_image_metadata_and_report_budgets_fail_without_outputs(self):
        for index, (limits, code) in enumerate((({"MAX_IMAGE_BYTES": 4096}, "IMAGE_SIZE_LIMIT"), ({"MAX_METADATA_BYTES": 7}, "METADATA_BYTE_LIMIT"), ({"MAX_REPORT": 100}, "REPORT_BYTE_LIMIT"))):
            self.fixture(); self.new_output(index); self.report(probe="limit:" + json.dumps(limits), error=code); self.assertFalse(self.output.exists())
    def test_cli_argument_path_and_new_only_output_guards_are_fixed_codes(self):
        self.fixture()
        for args in ([], ["--private-unknown=value"], ["--image", self.input], ["--image", self.input, "--output", self.output, "--include-details"]):
            self.call(args, error="ARGUMENTS_INVALID")
        for path, code in (("relative.img", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (self.work / ".." / "fictional.img", "LOCAL_ABSOLUTE_PATH_REQUIRED"), ("//fictional/share/image", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (str(self.input) + "\nprivate", "INVALID_LOCAL_PATH"), (self.copy, "REGULAR_FILE_REQUIRED"), (self.work / "missing", "IO_OR_INPUT_ERROR")):
            self.call(["--image", path, "--output", self.output], error=code)
        self.report(); self.report(error="OUTPUT_EXISTS")
        for output in (self.input, self.work): self.call(["--image", self.input, "--output", output], error="OUTPUT_EXISTS")
        self.call(["--image", self.input, "--output", self.work / "missing" / "report"], error="IO_OR_INPUT_ERROR")
        if os.name == "nt": self.call(["--image", str(self.input) + ":stream", "--output", self.output], error="DEVICE_OR_STREAM_PATH_REJECTED")
    def test_changed_short_read_and_partial_write_failures_are_private(self):
        self.fixture(); self.report(probe="changed_input", error="INPUT_CHANGED", ignore=[self.input]); self.assertFalse(self.output.exists())
        self.fixture(); self.report(probe="short_read", error="INPUT_CHANGED"); self.assertFalse(self.output.exists())
        self.report(probe="write_failure", error="IO_OR_INPUT_ERROR")
        self.assertEqual({p.name for p in self.output.iterdir()}, {"report.json", "report.html"}); self.report(error="OUTPUT_EXISTS")
    def test_native_symlink_inputs_and_output_parents(self):
        self.fixture(); linked = self.work / "linked.img"; self.symlink(linked, self.input)
        self.call(["--image", linked, "--output", self.output], error="LINKED_PATH_REJECTED")
        directory = self.work / "linked directory"; self.symlink(directory, self.work, directory=True)
        self.call(["--image", directory / self.input.name, "--output", self.output], error="LINKED_PATH_REJECTED")
        self.call(["--image", self.input, "--output", directory / "report"], error="LINKED_PATH_REJECTED")
    def test_hardlink_and_hostile_environment_preserve_input_identity(self):
        self.fixture(); linked = self.work / "hardlinked.img"; os.link(self.input, linked); self.assertTrue(os.path.samefile(linked, self.input))
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
