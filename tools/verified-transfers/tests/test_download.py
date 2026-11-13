"""Fresh copied-pair CLI consumers; every payload and workspace is fictional."""
import ctypes
from ctypes import wintypes
import hashlib
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
RUNTIME = ("transfer.py", "transfer_windows.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
ERROR = dict(status="ERROR", code="TRANSFER_REFUSED_OR_FAILED", partial_destination="retained")
SOURCE = "reviewed-source-package-v1"
DATA = "opaque-data-handoff-v1"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junction_stream_and_short_spellings_refused"
PROCESS_WINDOWS_REASON = "Native Windows junction and stream fixture"
PROCESS_POSIX_ID = "test_download.Download.test_native_posix_special_entries_refused_before_read"
PROCESS_POSIX_REASON = "Native POSIX FIFO and socket fixture"
PROCESS_SYMLINK_ID = "test_download.Download.test_native_symlink_leaves_and_parents_refused"
PROCESS_SYMLINK_REASON = "Native symlink privilege unavailable"
PROBE = r'''
import errno,importlib.metadata,json,os,socket,subprocess,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(base))
import transfer as m
assert Path(m.__file__).resolve()==base/'transfer.py'
assert Path(m._windows().__file__).resolve()==base/'transfer_windows.py'
kind=sys.argv[2]
args=sys.argv[3:]
def closed(descriptors):
 assert descriptors, 'NO_DESCRIPTOR_OBSERVED'
 for fd in set(descriptors):
  try:os.fstat(fd)
  except OSError as error:assert error.errno==errno.EBADF, 'CLOSED_DESCRIPTOR_ERROR_DIFFERS'
  else:raise AssertionError('INTERRUPTED_DESCRIPTOR_STILL_OPEN')
if kind=='affinity':
 expected=base.parents[1] if base.name=='verified-transfers' and base.parent.name=='tools' else base
 assert m.REPOSITORY==expected
 print(json.dumps(dict(status='COPIED_PAIR_AFFINITY',dependencies=0)))
 raise SystemExit(0)
elif kind=='nul':
 raise SystemExit(m.main(['verify','--bundle','FICTIONAL\x00PRIVATE']))
elif kind=='short':
 incoming,outgoing=os.read,os.write
 os.read=lambda fd,amount:incoming(fd,min(amount,3))
 os.write=lambda fd,data:outgoing(fd,data[:3])
elif kind in ('write_failure','zero_write','cli_interrupt'):
 outgoing=os.write;observed=[];calls=[]
 def fail_write(fd,data):
  observed.append(fd)
  if not calls:
   calls.append(True)
   if kind=='zero_write':return 0
   return outgoing(fd,data[:11])
  if kind=='cli_interrupt':raise KeyboardInterrupt
  raise OSError('FICTIONAL_PRIVATE_WRITE_DETAIL')
 os.write=fail_write
 try:code=m.main(args)
 except KeyboardInterrupt:
  assert os.name!='nt' and kind=='cli_interrupt'
  closed(observed)
  print(json.dumps(dict(status='POSIX_INTERRUPT_PROPAGATED',partial_destination='retained')))
  raise SystemExit(0)
 closed(observed)
 raise SystemExit(code)
elif kind=='read_failure':
 def fail_read(*args):raise OSError('FICTIONAL_PRIVATE_READ_DETAIL')
 os.read=fail_read
elif kind=='mutation':
 incoming=os.read;events=[]
 path=Path(args[args.index('--source')+1])/'state.bin'
 def mutate(fd,amount):
  block=incoming(fd,amount)
  if block and not events:
   original=path.read_bytes()
   path.write_bytes(bytes([original[0]^1])+original[1:])
   events.append(True)
  return block
 os.read=mutate
elif kind=='library_interrupt':
 path,target=map(Path,args);before=path.read_bytes();observed=[]
 original_open=os.open
 def opening(value,flags,*extra,**options):
  fd=original_open(value,flags,*extra,**options)
  if Path(value) in (path,target):observed.append(fd)
  return fd
 def interrupt(fd,amount):
  observed.append(fd)
  raise KeyboardInterrupt
 os.open=opening;os.read=interrupt
 try:m.checked_file(path,output=target)
 except KeyboardInterrupt:pass
 else:raise AssertionError('LIBRARY_INTERRUPT_MUST_PROPAGATE')
 closed(observed)
 assert len(set(observed))==2, 'BOTH_INPUT_OUTPUT_DESCRIPTORS_REQUIRED'
 assert path.read_bytes()==before and target.read_bytes()==b''
 print(json.dumps(dict(status='LIBRARY_INTERRUPT_PROPAGATED',partial_destination='retained')))
 raise SystemExit(0)
else:raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
raise SystemExit(m.main(args))
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def entries(files):
    return [dict(path=name, size=len(raw), sha256=digest(raw)) for name, raw in sorted(files.items())]


def manifest_bytes(files, format_name=DATA):
    return (json.dumps(dict(schema_version=1, format=format_name, inventory=entries(files)),
                       indent=2, ensure_ascii=True) + "\n").encode("utf-8")


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="vt-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.copy = self.work / "copied runtime"
        self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT / name).read_bytes()
            (self.copy / name).write_bytes(raw)
            self.pins[name] = digest(raw)
        self.source = self.work / "fictional input"
        self.source.mkdir()
        self.files = {"state.bin": b"\x00\xffFICTIONAL opaque state\r\n" * 4,
                      "world/player.dat": b"Invented player bytes\x80\n"}
        self.put_files(self.source, self.files)
        self.manifest = self.work / "reviewed inventory.json"
        self.bundle = self.work / "new bundle"
        self.target = self.work / "new restore"
        self.addCleanup(self.runtime_preserved)

    def put_files(self, root, files):
        for name, raw in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    def runtime_preserved(self):
        self.assertEqual({p.name for p in self.copy.iterdir()}, set(RUNTIME))
        self.assertEqual({n: digest((self.copy / n).read_bytes()) for n in RUNTIME}, self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])

    def snapshot(self):
        result = {}
        def walk(folder):
            for path in folder.iterdir():
                key = path.relative_to(self.work).as_posix()
                if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                    result[key] = ("LINK", os.readlink(path))
                elif path.is_dir():
                    result[key] = ("DIRECTORY",)
                    walk(path)
                else:
                    info = path.lstat()
                    if stat.S_ISREG(info.st_mode):
                        result[key] = (digest(path.read_bytes()), info.st_size, info.st_mtime_ns,
                                       info.st_ctime_ns, info.st_ino, info.st_nlink)
                    else:
                        result[key] = ("SPECIAL", info.st_mode)
        walk(self.work)
        return result

    def call(self, args, *, wanted=ERROR, code=2, allow=(), ignore=(), probe=None, runtime=None,
             sorted_output=None, json_output=True):
        runtime = self.copy if runtime is None else runtime
        before = self.snapshot()
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        command = ([sys.executable, "-I", "-B", "-W", "error", "-c", PROBE, str(runtime), probe]
                   if probe else [sys.executable, "-I", "-B", "-W", "error", str(runtime / "transfer.py")])
        done = subprocess.run([*command, *map(str, args)], cwd=self.work, env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=90)
        self.assertEqual(done.returncode, code, (done.stdout + done.stderr).decode(errors="replace")[:2000])
        self.assertEqual(done.stderr, b"")
        for secret in (str(self.work).encode(), b"FICTIONAL_PRIVATE", b"Traceback"):
            self.assertNotIn(secret, done.stdout)
        after = self.snapshot()
        ignored = {Path(p).relative_to(self.work).as_posix() for p in ignore}
        self.assertEqual({k: v for k, v in before.items() if k not in ignored},
                         {k: after.get(k) for k in before if k not in ignored})
        for key in after.keys() - before.keys():
            path = self.work / key
            self.assertTrue(any(path == Path(root) or path.is_relative_to(root) for root in allow),
                            "Unexpected application write: " + key)
        self.runtime_preserved()
        if not json_output:
            return done.stdout
        self.assertEqual(len(done.stdout.splitlines()), 1)
        value = json.loads(done.stdout)
        self.assertEqual(value, wanted)
        ordered = code == 0 and probe not in {"affinity", "library_interrupt", "cli_interrupt"}
        self.assertEqual(done.stdout, json.dumps(wanted, sort_keys=ordered if sorted_output is None else sorted_output).encode() + NEWLINE)
        return value

    def ok(self, args, operation, files=None, format_name=DATA, *, allow=(), **options):
        files = self.files if files is None else files
        wanted = dict(status="VERIFIED", operation=operation, format=format_name, files=len(files),
                      bytes=sum(map(len, files.values())), manifest_sha256=digest(manifest_bytes(files, format_name)))
        return self.call(args, code=0, wanted=wanted, allow=allow, **options)

    def backup_args(self, destination=None):
        return ["backup", "--source", self.source, "--destination", destination or self.bundle, "--confirm-stopped"]

    def source_fixture(self, files=None):
        files = {"README.md": b"# Fictional package\r\n", "src/bomb.py": b"raise RuntimeError('PAYLOAD_EXECUTED')\n"} if files is None else files
        source = self.work / "reviewed source"
        if not source.exists():
            source.mkdir()
        self.put_files(source, files)
        raw = json.dumps(dict(schema_version=1, inventory=entries(files)), ensure_ascii=True).encode()
        self.manifest.write_bytes(raw)
        return source, files, raw

    def package_args(self, source, raw, destination=None):
        return ["package", "--source", source, "--manifest", self.manifest,
                "--expected-manifest-sha", digest(raw), "--destination", destination or self.bundle]

    def fixture_bundle(self, files=None, format_name=DATA, *, path=None, raw=None):
        files = self.files if files is None else files
        path = self.bundle if path is None else path
        path.mkdir()
        (path / "payload").mkdir()
        self.put_files(path / "payload", files)
        self.reseal(path, manifest_bytes(files, format_name) if raw is None else raw)
        return path

    def reseal(self, path, raw):
        (path / "MANIFEST.json").write_bytes(raw)
        (path / "MANIFEST.sha256").write_bytes((digest(raw) + "  MANIFEST.json\n").encode("ascii"))
        return digest(raw)

    def verify_args(self, path=None, pin=None):
        result = ["verify", "--bundle", path or self.bundle]
        if pin is not None:
            result += ["--expected-manifest-sha", pin]
        return result

    def restore_args(self, path=None, pin=None, target=None):
        return ["restore", "--bundle", path or self.bundle, "--destination", target or self.target,
                "--expected-manifest-sha", pin or digest((self.bundle / "MANIFEST.json").read_bytes()), "--confirm-stopped"]

    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                if os.environ.get("OUTLANDS_TRANSFERS_REQUIRE_LINKS") != "1":
                    self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_copied_pair_import_affinity_and_zero_dependencies(self):
        self.call([], probe="affinity", code=0, wanted=dict(status="COPIED_PAIR_AFFINITY", dependencies=0))
        self.assertEqual(list(self.copy.iterdir()).__len__(), 2)

    def test_package_preserves_selected_bytes_and_never_executes_payloads(self):
        source, files, raw = self.source_fixture()
        self.put_files(source, {".env": b"fictional unselected", ".git/config": b"fictional unselected"})
        self.ok(self.package_args(source, raw), "package", files, SOURCE, allow=[self.bundle])
        self.assertEqual((self.bundle / "MANIFEST.json").read_bytes(), manifest_bytes(files, SOURCE))
        self.assertEqual((self.bundle / "MANIFEST.sha256").read_bytes(),
                         (digest(manifest_bytes(files, SOURCE)) + "  MANIFEST.json\n").encode())
        self.assertEqual({p.relative_to(self.bundle / "payload").as_posix() for p in (self.bundle / "payload").rglob("*") if p.is_file()}, set(files))
        for name, data in files.items():
            self.assertEqual((self.bundle / "payload" / name).read_bytes(), data)

    def test_backup_verify_restore_roundtrip_preserves_opaque_binary_bytes(self):
        self.ok(self.backup_args(), "backup", allow=[self.bundle])
        raw = manifest_bytes(self.files)
        self.assertEqual((self.bundle / "MANIFEST.json").read_bytes(), raw)
        self.ok(self.verify_args(pin=digest(raw).upper()), "verify")
        self.ok(self.restore_args(), "restore", allow=[self.target])
        self.assertEqual({p.relative_to(self.target).as_posix(): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}, self.files)

    def test_independently_built_bundle_matches_frozen_format(self):
        self.fixture_bundle()
        self.ok(self.verify_args(pin=digest(manifest_bytes(self.files))), "verify")
        self.ok(self.restore_args(), "restore", allow=[self.target])

    def test_external_pin_detects_resigned_content_without_claiming_authenticity(self):
        self.fixture_bundle()
        old = digest(manifest_bytes(self.files))
        altered = dict(self.files, **{"state.bin": b"Fictional changed opaque data"})
        (self.bundle / "payload/state.bin").write_bytes(altered["state.bin"])
        self.reseal(self.bundle, manifest_bytes(altered))
        self.ok(self.verify_args(), "verify", altered)
        self.call(self.verify_args(pin=old))
        self.call(self.restore_args(pin=old))
        self.assertFalse(self.target.exists())

    def test_existing_destinations_are_never_overwritten(self):
        source, files, raw = self.source_fixture()
        self.fixture_bundle()
        self.target.mkdir()
        (self.target / "keep.txt").write_bytes(b"Fictional retained destination")
        for args in (self.backup_args(), self.package_args(source, raw), self.restore_args(target=self.target)):
            with self.subTest(operation=args[0]):
                self.call(args)
        self.assertEqual((self.target / "keep.txt").read_bytes(), b"Fictional retained destination")

    def test_destinations_require_new_existing_parent_and_disjoint_roots(self):
        self.fixture_bundle()
        source, _, raw = self.source_fixture()
        attempts = [self.backup_args(self.work / "absent/new"), self.backup_args(self.source / "inside"),
                    self.backup_args(self.work), self.package_args(source, raw, source / "inside"),
                    self.restore_args(target=self.bundle / "inside"), self.restore_args(target=self.work / "missing/new")]
        for args in attempts:
            with self.subTest(operation=args[0], destination=str(args[args.index("--destination") + 1]).replace(str(self.work), "<fixture>")):
                self.call(args)
        self.assertFalse((self.work / "absent").exists())
        self.assertFalse((self.work / "missing").exists())

    def test_flat_and_literal_collection_boundaries_protect_source(self):
        self.call(self.backup_args(self.copy / "blocked"))
        # Source data under the flat runtime is refused before inventory.
        self.call(["backup", "--source", self.copy, "--destination", self.bundle, "--confirm-stopped"])
        collection = self.work / "copied collection"
        module = collection / "tools/verified-transfers"
        module.mkdir(parents=True)
        for name in RUNTIME:
            (module / name).write_bytes((self.copy / name).read_bytes())
        self.call([], probe="affinity", runtime=module, code=0,
                  wanted=dict(status="COPIED_PAIR_AFFINITY", dependencies=0))
        self.call(self.backup_args(collection / "blocked"), runtime=module)
        self.call(["backup", "--source", module, "--destination", self.bundle, "--confirm-stopped"], runtime=module)
        self.ok(self.backup_args(), "backup", runtime=module, allow=[self.bundle])
        self.assertEqual({p.name for p in module.iterdir()}, set(RUNTIME))

    def test_stopped_confirmation_is_required_for_backup_and_restore(self):
        self.fixture_bundle()
        self.call(self.backup_args()[:-1])
        self.call(self.restore_args()[:-1])
        self.assertFalse(self.target.exists())

    def test_argument_failures_are_one_redacted_json_line(self):
        for args in ([], ["unknown"], ["backup"], ["verify", "--bundle", self.source, "--invalid"],
                     ["restore", "--bundle", self.bundle, "--destination", self.target, "--confirm-stopped"]):
            with self.subTest(args=args[:1]):
                self.call(args)
        self.call([], probe="nul")
        help_text = self.call(["--help"], code=0, json_output=False)
        for operation in (b"package", b"backup", b"verify", b"restore"):
            self.assertIn(operation, help_text)

    def test_source_manifest_external_pin_is_exact_bytes_and_accepts_bom(self):
        source, files, raw = self.source_fixture()
        self.call(self.package_args(source, raw)[:-3] + ["0" * 64, "--destination", self.bundle])
        padded = b"\xef\xbb\xbf" + raw + b" \n"
        self.manifest.write_bytes(padded)
        self.call(self.package_args(source, raw))
        self.ok(self.package_args(source, padded), "package", files, SOURCE, allow=[self.bundle])

    def test_source_manifest_schema_duplicate_and_nonfinite_values_refused(self):
        source, _, raw = self.source_fixture()
        values = [b'{"schema_version":1,"schema_version":1,"inventory":[]}',
                  b'{"schema_version":NaN,"inventory":[]}', b'{"schema_version":1,"inventory":Infinity}',
                  b'{"schema_version":true,"inventory":[]}', b'[]', b'{"schema_version":1,"inventory":[],"extra":1}',
                  b'\xff', b'{"schema_version":1,']
        for bad in values:
            with self.subTest(raw=bad[:30]):
                self.manifest.write_bytes(bad)
                self.call(self.package_args(source, bad))
        self.assertFalse(self.bundle.exists())

    def test_inventory_entry_types_hashes_sizes_and_count_limits_refused(self):
        source, _, _ = self.source_fixture()
        base = dict(path="README.md", size=1, sha256="a" * 64)
        bad_rows = [[], [dict(base, size=True)], [dict(base, size=-1)], [dict(base, size=1.0)],
                    [dict(base, sha256="A" * 64)], [dict(base, sha256="a" * 63)], [dict(base, extra=1)],
                    [dict(base, path=7)], [None], [dict(base, size=2 * 1024 * 1024 + 1)],
                    [dict(base, path=str(i) + ".txt") for i in range(10001)]]
        for rows in bad_rows:
            with self.subTest(kind=str(rows)[:65]):
                raw = json.dumps(dict(schema_version=1, inventory=rows)).encode()
                self.manifest.write_bytes(raw)
                self.call(self.package_args(source, raw))
        self.assertFalse(self.bundle.exists())

    def test_inventory_paths_traversal_case_unicode_and_prefix_collisions_refused(self):
        source, _, _ = self.source_fixture()
        names = ["../escape.py", "/absolute.py", "x//y.py", "x/./y.py", "x\\y.py", "x:y.py",
                 "CON.py", "x. /a.py", "trailing .", "bad?.py", "bad\u0001.py", "e\u0301.py"]
        groups = [[name] for name in names] + [["A/a.py", "a/b.py"], ["a.py", "a.py"], ["a.py", "a.py/b.py"]]
        for group in groups:
            with self.subTest(paths=group):
                rows = [dict(path=name, size=0, sha256=digest(b"")) for name in group]
                raw = json.dumps(dict(schema_version=1, inventory=rows)).encode()
                self.manifest.write_bytes(raw)
                self.call(self.package_args(source, raw))
        self.assertFalse(self.bundle.exists())

    def test_declared_total_and_metadata_byte_limits_refused_before_copy(self):
        source, _, _ = self.source_fixture()
        rows = [dict(path=str(i) + ".txt", size=2 * 1024 * 1024, sha256="0" * 64) for i in range(33)]
        raw = json.dumps(dict(schema_version=1, inventory=rows)).encode()
        self.manifest.write_bytes(raw)
        self.call(self.package_args(source, raw))
        raw = b" " * (4 * 1024 * 1024 + 1)
        self.manifest.write_bytes(raw)
        self.call(self.package_args(source, raw))
        self.fixture_bundle(raw=json.dumps(dict(schema_version=1, format=DATA,
            inventory=[dict(path=str(i) + ".dat", size=64 * 1024 * 1024, sha256="0" * 64) for i in range(5)])).encode())
        self.call(self.verify_args())

    def test_source_text_limits_binary_nul_and_invalid_utf8_refused(self):
        source, _, _ = self.source_fixture({"sample.txt": b"valid"})
        for raw in (b"abc\x00text", b"\xff\xfe", b"final\xe2\x82", b"x" * (2 * 1024 * 1024 + 1)):
            with self.subTest(size=len(raw)):
                (source / "sample.txt").write_bytes(raw)
                manifest = json.dumps(dict(schema_version=1, inventory=entries({"sample.txt": raw}))).encode()
                self.manifest.write_bytes(manifest)
                self.call(self.package_args(source, manifest))
        self.assertFalse(self.bundle.exists())

    def test_source_policy_and_data_control_or_sidecar_paths_refused(self):
        source, _, _ = self.source_fixture()
        for name in ("payload.exe", ".env", "id_rsa", "private/note.txt", "logs/run.txt",
                     ".git/config", ".venv/site.py", "data.db", "secret.pem"):
            with self.subTest(name=name):
                raw = json.dumps(dict(schema_version=1, inventory=entries({name: b"fictional"}))).encode()
                self.manifest.write_bytes(raw)
                self.call(self.package_args(source, raw))
        for index, name in enumerate((".git/config", ".aws/profile", ".venv-x/a", "state.db-wal", "state.db-shm", "state.db-journal")):
            folder = self.work / ("blocked-data-" + str(index))
            folder.mkdir()
            self.put_files(folder, {name: b"fictional"})
            self.call(["backup", "--source", folder, "--destination", self.bundle, "--confirm-stopped"])

    def test_bundle_top_level_missing_and_extra_entries_refused(self):
        self.fixture_bundle()
        extra = self.bundle / "extra.txt"
        extra.write_bytes(b"fictional extra")
        self.call(self.verify_args())
        extra.unlink()
        for name in ("MANIFEST.json", "MANIFEST.sha256"):
            raw = (self.bundle / name).read_bytes()
            (self.bundle / name).unlink()
            self.call(self.verify_args())
            (self.bundle / name).write_bytes(raw)

    def test_payload_tampering_missing_and_extra_entries_refused(self):
        self.fixture_bundle()
        target = self.bundle / "payload/state.bin"
        raw = target.read_bytes()
        for data in (b"Fictional changed", b"x" * len(raw)):
            target.write_bytes(data)
            self.call(self.verify_args())
            self.call(self.restore_args())
        target.unlink()
        self.call(self.verify_args())
        target.write_bytes(raw)
        extra = self.bundle / "payload/extra.bin"
        extra.write_bytes(b"fictional extra")
        self.call(self.verify_args())
        self.assertFalse(self.target.exists())

    def test_bundle_manifest_schema_duplicates_and_metadata_limit_refused(self):
        self.fixture_bundle()
        original = manifest_bytes(self.files)
        values = [b'{"schema_version":1,"format":"opaque-data-handoff-v1","inventory":[],"inventory":[]}',
                  b'{"schema_version":true,"format":"opaque-data-handoff-v1","inventory":[]}',
                  b'{"schema_version":1,"format":"unknown","inventory":[]}',
                  b'{"schema_version":1,"format":NaN,"inventory":[]}',
                  b'{"schema_version":1,"format":"opaque-data-handoff-v1","inventory":[],"extra":1}',
                  b' ' * (4 * 1024 * 1024 + 1)]
        for raw in values:
            with self.subTest(size=len(raw)):
                self.reseal(self.bundle, raw)
                self.call(self.verify_args(pin=digest(raw)))
        self.reseal(self.bundle, original)

    def test_checksum_format_and_external_pin_are_independent(self):
        self.fixture_bundle()
        checksum = self.bundle / "MANIFEST.sha256"
        raw = checksum.read_bytes()
        for bad in (raw.replace(b"  ", b" "), raw.replace(b"\n", b"\r\n"), raw.upper(), raw[:-1], b"0" * 64 + b"  MANIFEST.json\n"):
            with self.subTest(checksum=bad[:15]):
                checksum.write_bytes(bad)
                self.call(self.verify_args(pin=digest(manifest_bytes(self.files))))
        checksum.write_bytes(raw)
        for pin in ("0" * 64, "a" * 63, "not-a-digest"):
            self.call(self.verify_args(pin=pin))

    def test_source_bundle_is_verified_but_cannot_restore_as_data(self):
        files = {"fictional.txt": b"\xef\xbb\xbfFictional text\r\n"}
        self.fixture_bundle(files, SOURCE)
        self.ok(self.verify_args(), "verify", files, SOURCE)
        self.call(self.restore_args())
        self.assertFalse(self.target.exists())
        changed = {"fictional.txt": b"binary\x00"}
        (self.bundle / "payload/fictional.txt").write_bytes(changed["fictional.txt"])
        self.reseal(self.bundle, manifest_bytes(changed, SOURCE))
        self.call(self.verify_args())

    def test_hardlinked_source_control_payload_and_destination_files_refused(self):
        alias = self.work / "hardlink alias"
        os.link(self.source / "state.bin", alias)
        self.call(self.backup_args())
        alias.unlink()
        source, _, raw = self.source_fixture()
        os.link(self.manifest, alias)
        self.call(self.package_args(source, raw))
        alias.unlink()
        self.fixture_bundle()
        os.link(self.bundle / "payload/state.bin", alias)
        self.call(self.verify_args())
        self.call(self.restore_args())
        alias.unlink()
        os.link(self.bundle / "MANIFEST.json", alias)
        self.call(self.verify_args())
        self.assertFalse(self.target.exists())

    def test_native_symlink_leaves_and_parents_refused(self):
        leaf = self.source / "linked.bin"
        self.symlink(leaf, self.source / "state.bin")
        self.call(self.backup_args())
        leaf.unlink()
        parent = self.work / "linked parent"
        self.symlink(parent, self.source, directory=True)
        self.call(["backup", "--source", parent, "--destination", self.bundle, "--confirm-stopped"])
        self.call(self.backup_args(parent / "output"))
        self.fixture_bundle()
        self.call(self.restore_args(target=parent / "output"))

    @unittest.skipUnless(os.name == "nt", PROCESS_WINDOWS_REASON)
    def test_native_windows_junction_stream_and_short_spellings_refused(self):
        junction = self.work / "junction"
        done = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(self.source)],
                              capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace"))
        self.assertTrue(junction.is_junction())
        self.addCleanup(lambda: os.rmdir(junction) if junction.is_junction() else None)
        self.call(["backup", "--source", junction, "--destination", self.bundle, "--confirm-stopped"])
        self.call(self.backup_args(junction / "output"))
        source, _, raw = self.source_fixture()
        for name in (str(self.manifest) + ":fictional", "\\\\?\\" + str(self.manifest)):
            args = self.package_args(source, raw)
            args[args.index("--manifest") + 1] = name
            self.call(args)
        # A short-name-shaped component must also be refused when no alias exists.
        native = ctypes.WinDLL("kernel32", use_last_error=True)
        getshort = native.GetShortPathNameW
        getshort.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        getshort.restype = wintypes.DWORD
        buffer = ctypes.create_unicode_buffer(32768)
        count = getshort(str(self.source), buffer, len(buffer))
        self.assertTrue(0 < count < len(buffer))
        spelling = buffer.value
        if spelling.casefold() == str(self.source).casefold():
            spelling = str(self.source.parent / "FICTIO~1")
        self.call(["backup", "--source", spelling, "--destination", self.bundle, "--confirm-stopped"])

    @unittest.skipUnless(os.name != "nt", PROCESS_POSIX_REASON)
    def test_native_posix_special_entries_refused_before_read(self):
        fifo = self.source / "fifo"
        os.mkfifo(fifo)
        self.call(self.backup_args())
        fifo.unlink()
        address = self.source / "socket"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(address))
            self.call(self.backup_args())

    def test_short_reads_and_writes_preserve_bundle_and_restore_bytes(self):
        self.ok(self.backup_args(), "backup", probe="short", allow=[self.bundle])
        self.ok(self.verify_args(), "verify", probe="short")
        self.ok(self.restore_args(), "restore", probe="short", allow=[self.target])
        self.assertEqual((self.target / "state.bin").read_bytes(), self.files["state.bin"])

    def test_failed_and_zero_writes_retain_new_partial_destinations(self):
        for index, kind in enumerate(("write_failure", "zero_write")):
            target = self.work / ("partial bundle " + str(index))
            self.call(self.backup_args(target), probe=kind, allow=[target])
            self.assertTrue((target / "payload/state.bin").is_file())
            self.assertEqual((target / "payload/state.bin").read_bytes(),
                             self.files["state.bin"][:11] if kind == "write_failure" else b"")
            self.assertFalse((target / "MANIFEST.json").exists())
            self.call(self.backup_args(target))

    def test_input_read_failures_and_same_length_mutation_are_detected(self):
        self.call(self.backup_args(), probe="read_failure")
        self.assertFalse(self.bundle.exists())
        original = self.files["state.bin"]
        self.call(self.backup_args(), probe="mutation", ignore=[self.source / "state.bin"])
        self.assertEqual((self.source / "state.bin").read_bytes(), bytes([original[0] ^ 1]) + original[1:])
        self.assertFalse(self.bundle.exists())

    def test_interruptions_preserve_platform_contract_and_close_descriptors(self):
        partial = self.work / "interrupted bundle"
        if os.name == "nt":
            self.call(self.backup_args(partial), probe="cli_interrupt", code=130, allow=[partial],
                      wanted=dict(status="ERROR", code="TRANSFER_INTERRUPTED", partial_destination="retained"))
        else:
            self.call(self.backup_args(partial), probe="cli_interrupt", code=0, allow=[partial],
                      wanted=dict(status="POSIX_INTERRUPT_PROPAGATED", partial_destination="retained"))
        self.assertEqual((partial / "payload/state.bin").read_bytes(), self.files["state.bin"][:11])
        target = self.work / "library partial.bin"
        self.call([self.source / "state.bin", target], probe="library_interrupt", code=0, allow=[target],
                  wanted=dict(status="LIBRARY_INTERRUPT_PROPAGATED", partial_destination="retained"))
        self.assertEqual(target.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
