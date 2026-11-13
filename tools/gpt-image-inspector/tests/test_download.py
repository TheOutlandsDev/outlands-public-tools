"""Independent consumers of copied GPT tooling and authored metadata; no image executes."""
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
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("gpt_inspector.py", "inspection_support.py", "examples/generate.py")
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


def crc32(raw):
    """Independent reflected IEEE CRC-32; deliberately does not import zlib."""
    value = 0xffffffff
    for byte in raw:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xedb88320 if value & 1 else 0)
    return value ^ 0xffffffff


def refresh(data, sector):
    for lba in (1, len(data) // sector - 1):
        start = lba * sector
        table, count, size = struct.unpack_from("<QII", data, start + 72)
        struct.pack_into("<I", data, start + 88, crc32(data[table * sector:table * sector + count * size]))
        struct.pack_into("<I", data, start + 16, 0)
        size = struct.unpack_from("<I", data, start + 12)[0]
        struct.pack_into("<I", data, start + 16, crc32(data[start:start + size]))


def image(sector=512, partitions=None):
    """Author a fictional raw image without importing the copied generator."""
    count = 256
    table_sectors = 16384 // sector
    first, last = 2 + table_sectors, count - 2 - table_sectors
    rows = partitions if partitions is not None else [(first + 2, first + 9, "fiction_alpha"), (first + 12, first + 20, "fiction_beta")]
    table = bytearray(16384)
    for index, (start, end, name) in enumerate(rows):
        offset = index * 128
        table[offset:offset + 16] = uuid.UUID("00000000-0000-4000-8000-000000000001").bytes_le
        table[offset + 16:offset + 32] = uuid.UUID(int=index + 16).bytes_le
        struct.pack_into("<QQQ", table, offset + 32, start, end, 0)
        raw = name.encode("utf-16-le")
        assert len(raw) <= 72
        table[offset + 56:offset + 56 + len(raw)] = raw
    data = bytearray(count * sector)
    data[510:512] = b"\x55\xaa"
    data[450] = 0xee
    struct.pack_into("<II", data, 454, 1, count - 1)
    for role, lba, other, table_lba in (("primary", 1, count - 1, 2), ("backup", count - 1, 1, count - 1 - table_sectors)):
        start = lba * sector
        data[start:start + 8] = b"EFI PART"
        struct.pack_into("<IIIIQQQQ", data, start + 8, 0x10000, 92, 0, 0, lba, other, first, last)
        data[start + 56:start + 72] = uuid.UUID("11111111-2222-4333-8444-555555555555").bytes_le
        struct.pack_into("<QIII", data, start + 72, table_lba, 128, 128, 0)
        data[table_lba * sector:table_lba * sector + len(table)] = table
    refresh(data, sector)
    return data


PROBE = r'''
import argparse,errno,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]);sys.path.insert(0,str(base))
import gpt_inspector as e
import inspection_support as s
assert Path(e.__file__).resolve()==base/'gpt_inspector.py'
assert Path(s.__file__).resolve()==base/'inspection_support.py'
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py'
 assert g.canonical_directory is s.canonical_directory and e.write_report is s.write_report
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
if kind=='audit_metadata':
 e.Parser(description=e.__doc__)
 b'\0\0'.decode('utf-16-le')  # Load the standard codec before enforcing the exact file-open set.
 source=Path(args[args.index('--image')+1]);sector=int(args[args.index('--sector-size')+1]);length=source.stat().st_size
 last=length//sector-1;table_sectors=16384//sector
 ranges=((0,512),(sector,sector),(2*sector,16384),((last-table_sectors)*sector,16384),(last*sector,sector))
 output=Path(args[args.index('--output')+1])
 allowed={base/name for name in ('gpt_inspector.py','inspection_support.py','examples/generate.py')}
 allowed.add(source);allowed.update(output/name for name in ('report.json','report.html','MANIFEST.json'))
 original=os.read
 def bounded_read(fd,count):
  position=os.lseek(fd,0,os.SEEK_CUR)
  assert any(start<=position and position+count<=start+size for start,size in ranges),'PAYLOAD_READ_ATTEMPT'
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
  setattr(s if name=='MAX_REPORT' else e,name,value)
elif kind=='write_failure':
 original=os.open
 def failed(path,*a,**kw):
  if Path(path).name=='MANIFEST.json':raise OSError('FICTIONAL_PRIVATE_WRITE_DETAIL')
  return original(path,*a,**kw)
 os.open=failed
elif kind=='changed_input':
 original=e.ImageReader.read_at;changed=False
 def changed_read(reader,*a):
  global changed
  raw=original(reader,*a)
  if not changed:
   changed=True
   with reader.path.open('ab') as out:out.write(b'fictional mutation')
  return raw
 e.ImageReader.read_at=changed_read
elif kind=='short_read':
 os.read=lambda *unused:b''
elif kind=='sparse':
 source=Path(args[0]);size=source.stat().st_size
 with e.ImageReader(source) as reader:
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
        self.temp = tempfile.TemporaryDirectory(prefix="gpt-cli-", dir=parent)
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
                            sample = stream.read(64)
                            stream.seek(-64, os.SEEK_END)
                            sample += stream.read(64)
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
    def fixture(self, data=None, sector=512):
        raw = image(sector) if data is None else data
        self.input.write_bytes(raw)
        return raw
    def call(self, args, *, error=None, output=None, probe=None, allow=(), ignore=(), env=None):
        before = self.snapshot()
        prefix = ["-c", PROBE, self.copy, probe] if probe else [self.copy / "gpt_inspector.py"]
        done = self.run_child([*prefix, *args], env=env)
        self.assertEqual(done.stderr, b"", done.stderr.decode(errors="replace")[:3000])
        value = json.loads(done.stdout)
        self.assertEqual(done.stdout, json.dumps(value, sort_keys=probe not in {"affinity", "sparse"}).encode() + NEWLINE)
        if error is not None:
            self.assertEqual(value, dict(status="INCOMPLETE", error=error))
            code = 2
        elif probe == "affinity":
            self.assertEqual(value, dict(status="COPIED_RUNTIME_AFFINITY", dependencies=0)); code = 0
        elif probe == "sparse":
            self.assertEqual(value, dict(status="SPARSE_METADATA_ONLY", image_bytes=3 * 1024**3, metadata_bytes_read=512)); code = 0
        else:
            report = self.check_report(output)
            self.assertEqual(value, dict(status=report["status"], metadata_bytes_read=report["metadata_bytes_read"], findings=len(report["findings"]), coverage_issues=len(report["coverage_issues"])))
            value = report
            code = int(report["status"] != "NO_SCOPE_FINDINGS")
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
        raw = (output / "report.json").read_bytes()
        report = json.loads(raw)
        self.assertEqual(raw, encoded(report))
        self.assertEqual(set(report), {"schema_version", "tool", "scope", "details_included", "image_bytes", "sector_size", "whole_image_hashed", "headers", "findings", "coverage_issues", "primary_backup_metadata_compared", "metadata_bytes_read", "metadata_regions", "status"})
        self.assertEqual(report["tool"], "Offline GPT Disk Image Inspector")
        self.assertEqual(report["schema_version"], 1)
        self.assertIs(report["whole_image_hashed"], False)
        self.assertEqual(report["status"], "REVIEW_REQUIRED" if report["findings"] or report["coverage_issues"] else "NO_SCOPE_FINDINGS")
        self.assertEqual(report["metadata_bytes_read"], sum(r["bytes"] for r in report["metadata_regions"]))
        self.assertNotIn(str(self.work), raw.decode())
        markup = (output / "report.html").read_bytes()
        parsed = StaticHTML(); parsed.feed(markup.decode()); parsed.close()
        self.assertEqual(parsed.tags.count("html"), 1)
        self.assertEqual(parsed.csp, ["default-src 'none'; style-src 'unsafe-inline'"])
        self.assertIn(html.escape(raw.decode(), quote=True).encode(), markup)
        members = {name: (output / name).read_bytes() for name in ("report.json", "report.html")}
        expected = dict(schema_version=1, files=[dict(path=name, bytes=len(data), sha256=sha(data)) for name, data in sorted(members.items())])
        self.assertEqual((output / "MANIFEST.json").read_bytes(), encoded(expected))
        return report
    def report(self, *, sector=512, extra=(), **kwargs):
        return self.call(["--image", self.input, "--sector-size", sector, "--output", self.output, *extra], output=self.output, allow=[self.output], **kwargs)
    def codes(self, report):
        return {row["code"] for row in report["findings"]}
    def new_output(self, suffix):
        self.output = self.work / ("new report " + str(suffix))
    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314 and os.environ.get("OUTLANDS_GPT_REQUIRE_LINKS") != "1":
                self.skipTest(PROCESS_SYMLINK_REASON)
            raise
    def test_copied_runtime_affinity_and_help(self):
        self.call([], probe="affinity")
        for script, flags in ((self.copy / "gpt_inspector.py", (b"--image", b"--sector-size", b"--include-details", b"--output")), (self.copy / "examples/generate.py", (b"--output",))):
            before = self.snapshot(); done = self.run_child([script, "--help"])
            self.assertEqual((done.returncode, done.stderr), (0, b""))
            for flag in flags: self.assertIn(flag, done.stdout)
            self.assertEqual(self.snapshot(), before)
    def test_generator_cli_four_examples_and_new_only_output(self):
        out = self.work / "generated"; before = self.snapshot()
        done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (0, b"", json.dumps(dict(status="FICTIONAL_EXAMPLES_CREATED", files=4), sort_keys=True).encode() + NEWLINE))
        self.assertEqual({k: self.snapshot().get(k) for k in before}, before)
        self.assertEqual({p.name for p in out.iterdir()}, {"clean-512.img", "clean-4096.img", "review-crc.img", "review-overlap.img"})
        for index, (name, sector, expected) in enumerate((("clean-512", 512, 0), ("clean-4096", 4096, 0), ("review-crc", 512, 1), ("review-overlap", 512, 1))):
            self.input = out / (name + ".img"); self.new_output(index)
            value = self.report(sector=sector)
            self.assertEqual(value["status"], "NO_SCOPE_FINDINGS" if expected == 0 else "REVIEW_REQUIRED")
        before = self.snapshot(); done = self.run_child([self.copy / "examples/generate.py", "--output", out])
        self.assertEqual((done.returncode, done.stderr, done.stdout), (2, b"", json.dumps(dict(status="INCOMPLETE", error="OUTPUT_EXISTS"), sort_keys=True).encode() + NEWLINE))
        self.assertEqual(self.snapshot(), before)
    def test_clean_512_crc_and_exact_metadata_regions(self):
        self.assertEqual(crc32(b"123456789"), 0xcbf43926)
        self.assertEqual(crc32(b""), 0)
        raw = self.fixture(); report = self.report()
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        self.assertEqual(report["metadata_bytes_read"], 34304)
        self.assertEqual([r["id"] for r in report["metadata_regions"]], ["mbr", "primary-header", "primary-entries", "backup-header", "backup-entries"])
        for region in report["metadata_regions"]:
            self.assertEqual(region["sha256"], sha(raw[region["offset"]:region["offset"] + region["bytes"]]))
        for header in report["headers"]:
            self.assertTrue(header["header_crc_matches"] and header["table_crc_matches"])
            start = header["header_lba"] * 512; data = bytearray(raw[start:start + 92]); stored = struct.unpack_from("<I", data, 16)[0]; data[16:20] = b"\0" * 4
            self.assertEqual(crc32(data), stored)
    def test_clean_4096_sector_and_independent_crc_accounting(self):
        raw = self.fixture(sector=4096); report = self.report(sector=4096)
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        self.assertEqual(report["metadata_bytes_read"], 41472)
        self.assertEqual(report["sector_size"], 4096)
        for header in report["headers"]:
            start = header["header_lba"] * 4096
            table_lba, count, width, stored = struct.unpack_from("<QIII", raw, start + 72)
            self.assertEqual(crc32(raw[table_lba * 4096:table_lba * 4096 + count * width]), stored)
            self.assertTrue(header["header_crc_matches"] and header["table_crc_matches"])
    def test_payload_is_not_read_and_no_external_action(self):
        raw = image(); sentinel = b"FICTIONAL_PRIVATE_PAYLOAD_DO_NOT_READ_" + b"x" * 24
        raw[64 * 512:64 * 512 + len(sentinel)] = sentinel
        self.fixture(raw)
        report = self.report(probe="audit_metadata")
        self.assertEqual(report["status"], "NO_SCOPE_FINDINGS")
        for name in ("report.json", "report.html", "MANIFEST.json"):
            self.assertNotIn(b"FICTIONAL_PRIVATE_PAYLOAD", (self.output / name).read_bytes())
    def test_default_private_fields_and_opt_in_details(self):
        self.fixture(); basic = self.report(); self.new_output("details"); detailed = self.report(extra=["--include-details"])
        self.assertNotIn("fiction_alpha", json.dumps(basic)); self.assertNotIn("disk_guid", json.dumps(basic))
        self.assertIn("fiction_alpha", json.dumps(detailed)); self.assertIn("disk_guid", json.dumps(detailed))
        self.assertEqual(basic["metadata_regions"], detailed["metadata_regions"])
        self.assertEqual((basic["findings"], basic["coverage_issues"]), (detailed["findings"], detailed["coverage_issues"]))
    def test_detail_html_escaping_and_static_manifest(self):
        self.fixture(image(partitions=[(36, 40, "</pre><script>fiction</script>")]))
        report = self.report(extra=["--include-details"])
        self.assertEqual(report["headers"][0]["partitions"][0]["name"], "</pre><script>fiction</script>")
        markup = (self.output / "report.html").read_bytes()
        self.assertIn(b"&lt;script&gt;", markup); self.assertNotIn(b"<script>", markup)
    def test_bad_primary_header_crc_is_review(self):
        data = image(); data[512 + 16] ^= 1; self.fixture(data)
        report = self.report(); self.assertEqual(self.codes(report), {"GPT_HEADER_CRC_MISMATCH"})
        self.assertFalse(report["headers"][0]["header_crc_matches"]); self.assertTrue(report["headers"][1]["header_crc_matches"])
    def test_bad_primary_table_crc_and_split_brain(self):
        data = image(); data[1024 + 56] ^= 1; self.fixture(data)
        report = self.report(); self.assertEqual(self.codes(report), {"GPT_TABLE_CRC_MISMATCH", "PRIMARY_BACKUP_METADATA_MISMATCH"})
        self.assertFalse(report["headers"][0]["table_crc_matches"])
    def test_recomputed_crc_does_not_hide_metadata_disagreement(self):
        data = image(); data[1024 + 56] ^= 1; refresh(data, 512); self.fixture(data)
        report = self.report(); self.assertEqual(self.codes(report), {"PRIMARY_BACKUP_METADATA_MISMATCH"})
        self.assertTrue(all(h["header_crc_matches"] and h["table_crc_matches"] for h in report["headers"]))
    def test_protective_mbr_signature_count_and_hybrid_are_review(self):
        for index, (offset, value, code) in enumerate(((510, 0, "MBR_SIGNATURE_MISMATCH"), (450, 0, "PROTECTIVE_MBR_ENTRY_COUNT"), (466, 0x83, "HYBRID_MBR_DECLARED"), (454, 2, "PROTECTIVE_MBR_RANGE_MISMATCH"))):
            with self.subTest(code=code):
                data = image(); data[offset] = value; self.fixture(data); self.new_output(index)
                self.assertIn(code, self.codes(self.report()))
    def test_missing_backup_header_is_explicit_partial_coverage(self):
        data = image(); data[-512:-504] = b"NO GPT!!"; self.fixture(data)
        report = self.report(); self.assertEqual(self.codes(report), {"GPT_SIGNATURE_MISMATCH"})
        self.assertFalse(report["primary_backup_metadata_compared"])
        self.assertNotIn("backup-entries", {r["id"] for r in report["metadata_regions"]})
    def test_untrusted_table_pointer_is_never_followed(self):
        data = image(); struct.pack_into("<Q", data, 512 + 72, 2**64 - 1); self.fixture(data)
        report = self.report(); self.assertIn("GPT_TABLE_RANGE_INVALID", self.codes(report))
        self.assertFalse(report["headers"][0]["table_inspected"])
        self.assertNotIn("primary-entries", {r["id"] for r in report["metadata_regions"]})
    def test_table_range_cannot_overlap_usable_partitions(self):
        data = image(); struct.pack_into("<Q", data, 512 + 72, 35); self.fixture(data)
        report = self.report(); self.assertIn("GPT_TABLE_RANGE_INVALID", self.codes(report))
        self.assertFalse(report["headers"][0]["table_inspected"])
    def test_nested_overlapping_and_out_of_range_partitions(self):
        for index, (rows, code) in enumerate((([(36, 90, "outer"), (40, 45, "inside"), (80, 100, "overlap")], "PARTITION_OVERLAP_OBSERVED"), ([(40, 39, "backward")], "PARTITION_RANGE_INVALID"), ([(1, 2, "outside")], "PARTITION_RANGE_INVALID"))):
            with self.subTest(code=code):
                self.fixture(image(partitions=rows)); self.new_output(index); self.assertIn(code, self.codes(self.report()))
    def test_guid_unused_entry_and_invalid_name_are_findings(self):
        cases = ((16, b"\0" * 16, "ZERO_PARTITION_GUID"), (128 + 16, uuid.UUID(int=16).bytes_le, "DUPLICATE_PARTITION_GUID"), (2 * 128 + 16, b"x", "NONZERO_UNUSED_ENTRY_DATA"), (56, b"\0\xd8", "PARTITION_NAME_ENCODING_INVALID"))
        for index, (offset, value, code) in enumerate(cases):
            with self.subTest(code=code):
                data = image()
                for lba in (1, 255):
                    table = struct.unpack_from("<Q", data, lba * 512 + 72)[0] * 512
                    data[table + offset:table + offset + len(value)] = value
                refresh(data, 512); self.fixture(data); self.new_output(index)
                self.assertIn(code, self.codes(self.report()))
    def test_unsupported_layouts_and_header_extensions_stay_coverage(self):
        for index, (offset, value, code) in enumerate(((8, 0x20000, "GPT_REVISION_UNSUPPORTED"), (84, 256, "GPT_ENTRY_SIZE_UNSUPPORTED"), (12, 96, "GPT_HEADER_EXTENSION_UNINSPECTED"))):
            with self.subTest(code=code):
                data = image(); struct.pack_into("<I", data, 512 + offset, value)
                if offset == 12: data[512 + 92] = 1
                self.fixture(data); self.new_output(index)
                report = self.report(); self.assertIn(code, {r["code"] for r in report["coverage_issues"]})
    def test_header_size_location_reserved_padding_and_usable_bounds(self):
        cases = ((12, "<I", 91, "GPT_HEADER_SIZE_INVALID"), (24, "<Q", 2, "GPT_HEADER_LOCATION_MISMATCH"), (20, "<I", 1, "GPT_RESERVED_FIELD_NONZERO"), (100, "<B", 1, "GPT_HEADER_PADDING_NONZERO"), (40, "<Q", 250, "GPT_USABLE_RANGE_INVALID"))
        for index, (offset, fmt, value, code) in enumerate(cases):
            with self.subTest(code=code):
                data = image(); struct.pack_into(fmt, data, 512 + offset, value); self.fixture(data); self.new_output(index)
                self.assertIn(code, self.codes(self.report()))
    def test_entry_image_metadata_and_report_budgets_refuse(self):
        for index, (limits, error) in enumerate((({"MAX_IMAGE_BYTES": 1024}, "IMAGE_SIZE_LIMIT"), ({"MAX_METADATA_BYTES": 512}, "METADATA_BYTE_LIMIT"), ({"MAX_TABLE_ENTRIES": 127}, "GPT_ENTRY_COUNT_LIMIT"), ({"MAX_REPORT": 100}, "REPORT_BYTE_LIMIT"))):
            with self.subTest(error=error):
                self.fixture(); self.new_output(index)
                self.report(probe="limit:" + json.dumps(limits), error=error)
                self.assertFalse(self.output.exists())
    def test_empty_truncated_unaligned_and_directory_inputs_refuse(self):
        for index, (data, error) in enumerate(((b"", "IMAGE_SIZE_LIMIT"), (b"x" * 512, "IMAGE_ALIGNMENT_INVALID"), (b"x" * 2049, "IMAGE_ALIGNMENT_INVALID"))):
            with self.subTest(error=error):
                self.fixture(data); self.new_output(index); self.report(error=error); self.assertFalse(self.output.exists())
        self.input = self.copy; self.report(error="REGULAR_FILE_REQUIRED")
    def test_invalid_and_missing_arguments_are_fixed_private_errors(self):
        self.fixture()
        for args in ([], ["--private-unknown=value"], ["--image", self.input, "--sector-size", 1024, "--output", self.output], ["--image", self.input, "--sector-size", "private", "--output", self.output]):
            self.call(args, error="ARGUMENTS_INVALID")
        self.input = self.work / "missing.img"; self.report(error="IO_OR_INPUT_ERROR")
    def test_existing_outputs_inputs_and_report_parents_stay_unchanged(self):
        self.fixture(); self.report(); self.report(error="OUTPUT_EXISTS")
        self.call(["--image", self.input, "--sector-size", 512, "--output", self.input], error="OUTPUT_EXISTS")
        self.call(["--image", self.input, "--sector-size", 512, "--output", self.work], error="OUTPUT_EXISTS")
        self.call(["--image", self.input, "--sector-size", 512, "--output", self.work / "absent" / "report"], error="IO_OR_INPUT_ERROR")
    def test_partial_new_output_write_failure_is_private_and_not_complete(self):
        self.fixture(); self.report(probe="write_failure", error="IO_OR_INPUT_ERROR")
        self.assertEqual({p.name for p in self.output.iterdir()}, {"report.json", "report.html"})
        self.report(error="OUTPUT_EXISTS")
    def test_changed_input_is_detected_before_reports(self):
        self.fixture(); self.report(probe="changed_input", error="INPUT_CHANGED", ignore=[self.input])
        self.assertTrue(self.input.read_bytes().endswith(b"fictional mutation")); self.assertFalse(self.output.exists())
    def test_short_read_is_detected_with_input_preserved(self):
        self.fixture(); self.report(probe="short_read", error="INPUT_CHANGED")
        self.assertFalse(self.output.exists())
    def test_native_symlink_inputs_and_output_parents(self):
        self.fixture(); linked = self.work / "linked.img"; self.symlink(linked, self.input)
        self.call(["--image", linked, "--sector-size", 512, "--output", self.output], error="LINKED_PATH_REJECTED")
        directory = self.work / "linked directory"; self.symlink(directory, self.work, directory=True)
        self.call(["--image", directory / self.input.name, "--sector-size", 512, "--output", self.output], error="LINKED_PATH_REJECTED")
        self.call(["--image", self.input, "--sector-size", 512, "--output", directory / "report"], error="LINKED_PATH_REJECTED")
    def test_hardlink_inputs_and_hostile_environment_keep_identity(self):
        self.fixture(); linked = self.work / "hardlinked.img"; os.link(self.input, linked)
        self.assertTrue(os.path.samefile(linked, self.input))
        hostile = self.work / "hostile imports"; hostile.mkdir()
        for name in ("sitecustomize.py", "usercustomize.py", "json.py", "zlib.py"):
            (hostile / name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env = dict(self.env, PYTHONPATH=str(hostile), PYTHONHOME=str(hostile), PYTHONSTARTUP=str(hostile / "sitecustomize.py"))
        self.call(["--image", linked, "--sector-size", 512, "--output", self.output], output=self.output, allow=[self.output], env=env)
    @unittest.skipUnless(os.name == "nt", PROCESS_WINDOWS_REASON)
    def test_native_windows_junctions_are_not_followed(self):
        self.fixture(); junction = self.work / "junction"
        done = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(self.work)], capture_output=True, timeout=15)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace"))
        self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
        self.call(["--image", junction / self.input.name, "--sector-size", 512, "--output", self.output], error="LINKED_PATH_REJECTED")
        self.call(["--image", self.input, "--sector-size", 512, "--output", junction / "report"], error="LINKED_PATH_REJECTED")
    @unittest.skipUnless(os.name != "nt", PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_metadata(self):
        fifo = self.work / "fictional.fifo"; os.mkfifo(fifo)
        connection = socket.socket(socket.AF_UNIX)
        connection.bind(str(self.work / "fictional.sock")); self.addCleanup(connection.close)
        for path in (fifo, self.work / "fictional.sock"):
            self.call(["--image", path, "--sector-size", 512, "--output", self.output], error="REGULAR_FILE_REQUIRED")
        self.input = self.work / "large fictional sparse.img"
        with self.input.open("wb") as stream: stream.truncate(3 * 1024**3)
        self.call([self.input], probe="sparse")
    def test_relative_traversal_unc_control_and_windows_stream_paths_refuse(self):
        self.fixture()
        for path, error in (("relative.img", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (self.work / ".." / "fictional.img", "LOCAL_ABSOLUTE_PATH_REQUIRED"), ("//fictional/share/image.img", "LOCAL_ABSOLUTE_PATH_REQUIRED"), (str(self.input) + "\nprivate", "INVALID_LOCAL_PATH")):
            self.call(["--image", path, "--sector-size", 512, "--output", self.output], error=error)
        if os.name == "nt":
            self.call(["--image", str(self.input) + ":stream", "--sector-size", 512, "--output", self.output], error="DEVICE_OR_STREAM_PATH_REJECTED")


if __name__ == "__main__":
    unittest.main()
