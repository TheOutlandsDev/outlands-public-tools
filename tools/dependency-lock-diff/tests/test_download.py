"""Fresh single-script process checks using invented lock declarations only."""

import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
FLAGS = dict.fromkeys(("filesystem_scanned", "packages_downloaded", "packages_installed", "environment_inspected",
                      "artifacts_verified", "dependencies_resolved", "advisories_checked", "upgrade_direction_inferred",
                      "locks_modified", "network_probed"), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def declared(name="fictional-demo", version="1.0", digest=None):
    return (name, version, digest or sha(("Fictional artifact declaration: " + name).encode("utf-8")))


def lock_bytes(records, *, newline="\n", comments=(), bom=False, uppercase=False):
    lines = list(comments)
    for name, version, digest in records:
        lines.extend([name + "==" + version + " " + chr(92), "    --hash=sha256:" + (digest.upper() if uppercase else digest)])
    raw = (newline.join(lines) + newline).encode("utf-8")
    return (b"\xef\xbb\xbf" if bom else b"") + raw


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="lock-diff-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied single script"
        self.runtime.mkdir()
        self.source = self.runtime / "lock_diff.py"
        self.source.write_bytes((ROOT / "lock_diff.py").read_bytes())
        self.runtime_hash = sha(self.source.read_bytes())
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def fixture(self, records=None, *, raw=None, **formatting):
        self.serial += 1
        path = self.work / ("FICTIONAL_PRIVATE_LOCK_" + str(self.serial) + ".lock")
        records = list(records if records is not None else [declared()])
        raw = lock_bytes(records, **formatting) if raw is None else raw
        path.write_bytes(raw)
        return dict(path=path, records=records, raw=raw)

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import lock_diff as tool\nevents = []\n" + textwrap.dedent(body)
                          + "\nstatus = tool.main(sys.argv[1:])\n" + textwrap.dedent(postlude)
                          + "\nraise SystemExit(status)\n", encoding="utf-8", newline="\n")
        return script

    def process(self, *arguments, expected=0, code=None, script=None, json_output=True):
        tree = {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")}
        retained = {}
        for path in self.work.rglob("*"):
            if not path.is_symlink() and not path.is_junction():
                info = path.lstat()
                if stat.S_ISREG(info.st_mode):
                    retained[path] = (sha(path.read_bytes()), info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink)
        done = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8", str(script or self.source), *map(str, arguments)],
                              cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60)
        self.assertEqual(done.returncode, expected, done.stdout[:2000] + done.stderr)
        self.assertEqual(done.stderr, "")
        self.assertEqual(tree, {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")})
        for path, before in retained.items():
            info = path.lstat()
            self.assertEqual((sha(path.read_bytes()), info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink), before)
        self.assertEqual(list(self.runtime.iterdir()), [self.source])
        self.assertEqual(sha(self.source.read_bytes()), self.runtime_hash)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
        self.assertNotIn(str(self.work), done.stdout.replace("\\\\", "\\"))
        self.assertNotIn("FICTIONAL_PRIVATE", done.stdout)
        if not json_output:
            return done.stdout
        self.assertEqual(len(done.stdout.splitlines()), 1)
        value = json.loads(done.stdout)
        if expected in (2, 130):
            self.assertEqual(value, dict(status="ERROR", code=code or "INTERRUPTED", **FLAGS))
        else:
            self.assertTrue(all(value[key] is False for key in FLAGS))
        return value

    def run_cli(self, before, after=None, **options):
        return self.process("--before", before["path"], "--after", (after or before)["path"], **options)

    def golden(self, before, after, classifications):
        rows, counts = [], dict(only_in_before=0, only_in_after=0, version_text_changed=0, hash_only_changed=0, unchanged=0)
        for name, kind in classifications:
            left = next((row for row in before["records"] if row[0] == name), None)
            right = next((row for row in after["records"] if row[0] == name), None)
            counts[kind.lower()] += 1
            rows.append(dict(name=name, classification=kind,
                             before=None if left is None else dict(version=left[1], sha256=left[2].lower()),
                             after=None if right is None else dict(version=right[1], sha256=right[2].lower()),
                             version_text_changed=None if left is None or right is None else left[1] != right[1],
                             hash_changed=None if left is None or right is None else left[2].lower() != right[2].lower()))
        return dict(schema_version="outlands.lock_diff.v1",
                    status="LOCK_DIFFERENCES_REPORTED" if any(kind != "UNCHANGED" for name, kind in classifications) else "MATCHING_LOCK_RECORDS",
                    scope="SUPPORTED_LOCK_DECLARATIONS_ONLY", **FLAGS,
                    counts=dict(before=len(before["records"]), after=len(after["records"]), **counts), rows=rows,
                    input_sha256=dict(before=sha(before["raw"]), after=sha(after["raw"])))

    def compare(self, before, after=None, classifications=None):
        after = after or before
        if classifications is None:
            classifications = [(row[0], "UNCHANGED") for row in before["records"]]
        wanted = self.golden(before, after, classifications)
        self.assertEqual(self.run_cli(before, after, expected=int(wanted["status"] != "MATCHING_LOCK_RECORDS")), wanted)
        return wanted

    def symlink(self, path, target):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_LOCK_DIFF_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_matching_records_have_complete_golden_json_and_no_output_files(self):
        run = self.fixture([declared("fictional-a"), declared("fictional-z")])
        self.compare(run)
        self.assertEqual({path.name for path in self.work.iterdir()}, {self.runtime.name, run["path"].name})

    def test_five_mutually_exclusive_classes_keep_separate_change_flags(self):
        old = [declared("fictional-gone"), declared("fictional-hash"), declared("fictional-same"),
               declared("fictional-version", "1.0"), declared("fictional-version-hash", "1.0")]
        new = [declared("fictional-added"), declared("fictional-hash", digest=sha(b"Fictional changed hash")),
               declared("fictional-same"), declared("fictional-version", "1.0.0"),
               declared("fictional-version-hash", "2.0", digest=sha(b"Fictional changed version and hash"))]
        self.compare(self.fixture(old), self.fixture(new),
                     [("fictional-added", "ONLY_IN_AFTER"), ("fictional-gone", "ONLY_IN_BEFORE"),
                      ("fictional-hash", "HASH_ONLY_CHANGED"), ("fictional-same", "UNCHANGED"),
                      ("fictional-version", "VERSION_TEXT_CHANGED"), ("fictional-version-hash", "VERSION_TEXT_CHANGED")])

    def test_version_comparison_preserves_text_without_semantic_ranking(self):
        for old, new in (("1.0", "1.0.0"), ("1.00", "1.0"), ("2!1.0", "1!9.0"), ("1.0+local-1", "1.0+local.1")):
            with self.subTest(old=old, new=new):
                value = self.compare(self.fixture([declared(version=old)]), self.fixture([declared(version=new)]),
                                     [("fictional-demo", "VERSION_TEXT_CHANGED")])
                self.assertFalse(value["upgrade_direction_inferred"])

    def test_seeded_list_search_oracle_and_reversal_cover_declaration_permutations(self):
        selected = random.Random(1837)
        names = ["fictional-" + str(index).zfill(2) for index in range(12)]
        for iteration in range(8):
            sides = []
            for side in range(2):
                rows = [declared(name, selected.choice(("1.0", "1.0.0", "2.0rc1")),
                                 sha(("Fictional digest " + str(selected.randrange(4))).encode()))
                        for name in names if selected.randrange(3)]
                sides.append(self.fixture(rows or [declared(names[0])]))
            for before, after in (sides, list(reversed(sides))):
                classifications = []
                for name in names:
                    left = next((row for row in before["records"] if row[0] == name), None)
                    right = next((row for row in after["records"] if row[0] == name), None)
                    if left is None and right is None:
                        continue
                    if left is None:
                        kind = "ONLY_IN_AFTER"
                    elif right is None:
                        kind = "ONLY_IN_BEFORE"
                    elif left[1] != right[1]:
                        kind = "VERSION_TEXT_CHANGED"
                    elif left[2] != right[2]:
                        kind = "HASH_ONLY_CHANGED"
                    else:
                        kind = "UNCHANGED"
                    classifications.append((name, kind))
                self.compare(before, after, classifications)

    def test_raw_hashes_distinguish_bom_comments_hash_case_and_all_three_newlines(self):
        rows = [declared("fictional-a"), declared("fictional-z")]
        before = self.fixture(rows)
        for ending in ("\n", "\r\n", "\r"):
            after = self.fixture(rows, newline=ending, comments=["# Fictional comment 雪", ""], bom=True, uppercase=True)
            value = self.compare(before, after)
            self.assertNotEqual(value["input_sha256"]["before"], value["input_sha256"]["after"])

    def test_canonical_names_include_exact_length_bounds_and_reject_normalization(self):
        for name in ("a", "a"*200, "fictional-1"):
            self.compare(self.fixture([declared(name)]))
        for name, code in (("Upper", "PACKAGE_NAME_NONCANONICAL"), ("a_b", "PACKAGE_NAME_NONCANONICAL"),
                           ("a.b", "PACKAGE_NAME_NONCANONICAL"), ("a--b", "PACKAGE_NAME_NONCANONICAL"),
                           ("_a", "PACKAGE_NAME_INVALID"), ("a-", "PACKAGE_NAME_INVALID"),
                           ("a"*201, "PACKAGE_NAME_INVALID"), ("雪", "LOCK_LINE_INVALID")):
            self.run_cli(self.fixture([declared(name)]), expected=2, code=code)

    def test_supported_version_subset_and_exact_text_length_are_enforced(self):
        for version in ("1", "01.002", "2!1.2rc3.post4.dev5+local-7.8", "1.0a1", "1.0b2", "1"*128):
            self.compare(self.fixture([declared(version=version)]))
        for version in ("v1.0", "latest", "1.0RC1", "1.*", "1.0+LOCAL", "1"*129):
            self.run_cli(self.fixture([declared(version=version)]), expected=2, code="VERSION_UNSUPPORTED")

    def test_hash_must_be_one_exact_immediately_adjacent_indented_line(self):
        valid = lock_bytes([declared()])
        lines = valid.decode().splitlines()
        cases = [(lines[0] + "\n", "ADJACENT_SHA256_REQUIRED"),
                 (lines[0] + "\n# comment\n" + lines[1] + "\n", "ADJACENT_SHA256_REQUIRED"),
                 (lines[0] + "\n\n" + lines[1] + "\n", "ADJACENT_SHA256_REQUIRED"),
                 (lines[0] + "\n" + lines[1][1:] + "\n", "ADJACENT_SHA256_REQUIRED"),
                 (lines[0] + "\n" + lines[1][:-1] + "\n", "ADJACENT_SHA256_REQUIRED"),
                 (valid.decode() + lines[1] + "\n", "LOCK_LINE_INVALID")]
        for raw, code in cases:
            self.run_cli(self.fixture(raw=raw.encode()), expected=2, code=code)

    def test_unsupported_package_operations_and_private_values_are_fixed_errors(self):
        for text in ("--index-url https://FICTIONAL_PRIVATE.invalid/", "-r FICTIONAL_PRIVATE.lock",
                     "-e git+https://FICTIONAL_PRIVATE.invalid/repo", "fictional[extra]==1.0",
                     "fictional>=1.0", "fictional==1.0 ; python_version > '3'", "FICTIONAL_PRIVATE_UNSUPPORTED"):
            self.run_cli(self.fixture(raw=(text + "\n").encode()), expected=2, code="LOCK_LINE_INVALID")

    def test_utf8_bom_placement_and_control_characters_have_exact_errors(self):
        self.run_cli(self.fixture(raw=b"\xff"), expected=2, code="LOCK_ENCODING_INVALID")
        for value in (b"\x00", b"\t", b"\x1b", b"\x0b", b"\x0c"):
            self.run_cli(self.fixture(raw=b"# Fictional " + value + b"\n"), expected=2, code="LOCK_CONTROL_CHARACTER")
        self.run_cli(self.fixture(raw=b"# First line\n\xef\xbb\xbf" + lock_bytes([declared()])), expected=2, code="LOCK_LINE_INVALID")

    def test_duplicate_unsorted_empty_and_comment_only_locks_are_refused(self):
        for rows, code in (([declared(), declared()], "DUPLICATE_PACKAGE"),
                           ([declared("fictional-z"), declared("fictional-a")], "PACKAGE_ORDER_INVALID")):
            self.run_cli(self.fixture(rows), expected=2, code=code)
        self.run_cli(self.fixture(raw=b""), expected=2, code="INPUT_SIZE_LIMIT")
        for raw in (b"\n", b"# Fictional comment only\r\n"):
            self.run_cli(self.fixture(raw=raw), expected=2, code="EMPTY_LOCK")

    def test_actual_one_mib_lock_boundary_and_one_extra_byte(self):
        raw = lock_bytes([declared()])
        remaining = 1024*1024 - len(raw)
        count, tail = divmod(remaining, 513)
        raw += (b"#" + b"x"*511 + b"\n")*count
        if tail:
            raw += b"\n" if tail == 1 else b"#" + b"x"*(tail-2) + b"\n"
        self.assertEqual(len(raw), 1024*1024)
        self.compare(self.fixture(raw=raw))
        self.run_cli(self.fixture(raw=raw + b"x"), expected=2, code="INPUT_BYTE_LIMIT")

    def test_six_thousand_lines_and_five_hundred_twelve_character_line_limits(self):
        raw = lock_bytes([declared()])
        exact = raw + b"#\n"*5998
        self.compare(self.fixture(raw=exact))
        self.run_cli(self.fixture(raw=exact + b"\n"), expected=2, code="LOCK_STRUCTURE_LIMIT")
        self.compare(self.fixture(raw=raw + b"#" + b"x"*511 + b"\n"))
        self.run_cli(self.fixture(raw=raw + b"#" + b"x"*512 + b"\n"), expected=2, code="LOCK_STRUCTURE_LIMIT")

    def test_two_thousand_packages_are_accepted_and_next_package_is_refused(self):
        rows = [declared("fictional-" + str(index).zfill(4)) for index in range(2000)]
        self.compare(self.fixture(rows))
        self.run_cli(self.fixture(rows + [declared("fictional-2000")]), expected=2, code="LOCK_PACKAGE_LIMIT")

    def test_four_mib_serialization_guard_refuses_before_printing_partial_json(self):
        run = self.fixture()
        wanted = self.golden(run, run, [("fictional-demo", "UNCHANGED")])
        length = len(json.dumps(wanted, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        for limit in (length, length-1):
            script = self.wrapper("assert tool.MAX_OUTPUT_BYTES == 4*1024*1024\ntool.MAX_OUTPUT_BYTES = " + str(limit) + "\n")
            value = self.run_cli(run, script=script, expected=0 if limit == length else 2,
                                 code=None if limit == length else "OUTPUT_BYTE_LIMIT")
            if limit == length:
                self.assertEqual(value, wanted)
        script = self.wrapper("""
            assert tool.MAX_OUTPUT_BYTES == 4*1024*1024
            original = tool.read_and_compare
            def oversized(*args):
                value = original(*args)
                value['controlled_oversized_render_fixture'] = 'x'*(4*1024*1024+1)
                events.append(True)
                return value
            tool.read_and_compare = oversized
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(run, script=script, expected=2, code="OUTPUT_BYTE_LIMIT")

    def test_help_version_arguments_missing_files_and_ambiguous_paths_are_fixed(self):
        self.assertIn("--before", self.process("--help", json_output=False))
        self.assertEqual(self.process("--version", json_output=False), "dependency-lock-diff 0.1.0\n")
        for args in ((), ("--before", "FICTIONAL_PRIVATE_MISSING"), ("--bef", "x", "--after", "y")):
            self.process(*args, expected=2, code="ARGUMENTS_INVALID")
        run = self.fixture()
        self.process("--before", self.work / "FICTIONAL_PRIVATE_MISSING.lock", "--after", run["path"],
                     expected=2, code="INPUT_OR_LOCK_FAILED")
        for path in (str(run["path"]) + ".", str(run["path"]) + " ", str(self.work / "CON.lock"),
                     str(self.work / "file:stream"), str(self.work / ".." / "escape.lock")):
            self.process("--before", path, "--after", run["path"], expected=2, code="INPUT_PATH_INVALID")
        self.assertEqual(self.process("--before", run["path"].name, "--after", run["path"].name),
                         self.golden(run, run, [("fictional-demo", "UNCHANGED")]))

    def test_only_two_lock_files_are_read_without_package_environment_or_network_operations(self):
        run = self.fixture()
        (self.work / "fictional-artifact.whl").write_bytes(b"FICTIONAL_PRIVATE_ARTIFACT_NEVER_OPEN")
        script = self.wrapper("""
            allowed = Path(INPUT_VALUE)
            original = os.open
            def opened(path, *args, **kwargs):
                assert Path(path) == allowed, 'Unselected artifact or environment file opened'
                events.append(True)
                return original(path, *args, **kwargs)
            def forbidden(*args, **kwargs):
                raise AssertionError('Package, environment, enumeration or network operation attempted')
            os.open = opened
            os.scandir = forbidden
            os.listdir = forbidden
            Path.iterdir = forbidden
            Path.open = forbidden
            socket.socket = forbidden
            socket.create_connection = forbidden
            urllib.request.urlopen = forbidden
            subprocess.Popen = forbidden
            runpy.run_path = forbidden
            os.system = forbidden
            importlib.metadata.distributions = forbidden
            importlib.metadata.version = forbidden
            """.replace("INPUT_VALUE", repr(str(run["path"]))),
                              prelude="import socket, urllib.request, subprocess, runpy\n",
                              postlude="assert events == [True, True] and status == 0\n")
        self.assertEqual(self.run_cli(run, script=script), self.golden(run, run, [("fictional-demo", "UNCHANGED")]))

    def test_native_hardlinked_lock_inputs_are_refused_without_modifying_targets(self):
        run = self.fixture()
        alias = self.work / "owned-hardlink.lock"
        os.link(run["path"], alias)
        self.assertGreaterEqual(alias.stat().st_nlink, 2)
        self.run_cli(run, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    def test_controlled_interruption_releases_open_input_descriptor(self):
        run = self.fixture()
        script = self.wrapper("""
            original = os.fdopen
            descriptors = []
            class Interrupted:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    self.stream.__enter__()
                    return self
                def __exit__(self, *args):
                    return self.stream.__exit__(*args)
                def fileno(self):
                    return self.stream.fileno()
                def read(self, maximum):
                    events.append(True)
                    raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT')
            def opened(fd, *args, **kwargs):
                descriptors.append(fd)
                return Interrupted(original(fd, *args, **kwargs))
            os.fdopen = opened
            """, postlude="""
            assert events == [True] and status == 130
            for fd in descriptors:
                try:
                    os.fstat(fd)
                except OSError as error:
                    assert error.errno == 9
                else:
                    raise AssertionError('Owned input descriptor remained open')
            """)
        self.run_cli(run, script=script, expected=130)

    def test_observed_short_read_and_final_identity_change_are_fixed_errors(self):
        run = self.fixture()
        changed = self.wrapper("""
            original = tool._fingerprint
            def fingerprint(path):
                events.append(True)
                return ('controlled observed change', original(path))
            tool._fingerprint = fingerprint
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(run, script=changed, expected=2, code="INPUT_CHANGED")
        short = self.wrapper("""
            original = os.fdopen
            class Short:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    self.stream.__enter__()
                    return self
                def __exit__(self, *args):
                    return self.stream.__exit__(*args)
                def fileno(self):
                    return self.stream.fileno()
                def read(self, maximum):
                    events.append(True)
                    return self.stream.read(maximum)[:-1]
            os.fdopen = lambda *args, **kwargs: Short(original(*args, **kwargs))
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(run, script=short, expected=2, code="INPUT_CHANGED")

    def test_native_symlink_leaf_and_dangling_inputs_are_refused(self):
        run = self.fixture()
        alias = self.work / "linked.lock"
        self.symlink(alias, run["path"])
        self.process("--before", alias, "--after", run["path"], expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        absent = self.work / "owned-absent-target.lock"
        dangling = self.work / "dangling.lock"
        self.symlink(dangling, absent)
        self.process("--before", dangling, "--after", run["path"], expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        self.assertFalse(absent.exists())

    def test_native_symlink_input_parent_is_refused(self):
        run = self.fixture()
        target = self.work / "owned-input-parent"
        target.mkdir()
        moved = target / "input.lock"
        run["path"].rename(moved)
        alias = self.work / "linked-parent"
        self.symlink(alias, target)
        self.process("--before", alias / "input.lock", "--after", moved, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_input_parents_are_refused(self):
        run = self.fixture()
        target = self.work / "owned-input-parent"
        target.mkdir()
        moved = target / "input.lock"
        run["path"].rename(moved)
        alias = self.work / "junction-parent"
        self.junction(alias, target)
        self.process("--before", alias / "input.lock", "--after", moved, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows alternate stream fixture")
    def test_native_windows_named_streams_are_outside_unnamed_input_scope(self):
        run = self.fixture()
        stream = str(run["path"]) + ":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b"FICTIONAL_PRIVATE_NAMED_STREAM")
        self.compare(run)
        self.process("--before", stream, "--after", run["path"], expected=2, code="INPUT_PATH_INVALID")
        with open(stream, "rb") as handle:
            self.assertEqual(handle.read(), b"FICTIONAL_PRIVATE_NAMED_STREAM")

    @unittest.skipUnless(os.name == "nt", "Native Windows held writer fixture")
    def test_native_windows_exclusive_writer_causes_open_refusal_then_release(self):
        run = self.fixture()
        script = self.wrapper("""
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                          wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            held = kernel.CreateFileW(INPUT_VALUE, 0x40000000, 0, None, 3, 0x80, None)
            if held == ctypes.c_void_p(-1).value:
                raise AssertionError('Native held writer fixture creation failed') from ctypes.WinError(ctypes.get_last_error())
            events.append(True)
            """.replace("INPUT_VALUE", repr(str(run["path"]))),
                              postlude="assert kernel.CloseHandle(held)\nassert events == [True] and status == 2\n")
        self.run_cli(run, script=script, expected=2, code="INPUT_OR_LOCK_FAILED")
        self.compare(run)

    @unittest.skipUnless(os.name != "nt", "Native POSIX FIFO fixture")
    def test_native_posix_fifo_inputs_are_refused_before_open(self):
        run = self.fixture()
        fifo = self.work / "owned-fifo.lock"
        os.mkfifo(fifo, 0o600)
        self.process("--before", fifo, "--after", run["path"], expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    def junction(self, link, target):
        from ctypes import wintypes

        self.assertTrue(link.is_relative_to(self.work) and target.is_relative_to(self.work))
        link.mkdir()
        self.addCleanup(link.rmdir)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                                          wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                          ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        kernel.DeviceIoControl.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        substitute = ("\\??\\" + str(target)).encode("utf-16-le")
        printable = str(target).encode("utf-16-le")
        payload = substitute + b"\x00\x00" + printable + b"\x00\x00"
        data = struct.pack("<LHHHHHH", 0xA0000003, 8 + len(payload), 0,
                           0, len(substitute), len(substitute) + 2, len(printable)) + payload
        held = kernel.CreateFileW(str(link), 0x40000000, 0, None, 3, 0x02200000, None)
        if held == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            buffer = ctypes.create_string_buffer(data)
            returned = wintypes.DWORD()
            if not kernel.DeviceIoControl(held, 0x000900A4, buffer, len(data), None, 0,
                                          ctypes.byref(returned), None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(held)
        self.assertTrue(link.is_junction())


if __name__ == "__main__":
    unittest.main()
