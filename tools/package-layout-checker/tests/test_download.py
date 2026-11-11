"""Copied-runtime process checks with caller-authored fictional packages."""

import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("layout_check.py", "layout_windows.py")


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="layout-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied runtime"
        self.runtime.mkdir()
        self.runtime_hashes = {}
        for name in RUNTIME:
            data = (ROOT / name).read_bytes()
            (self.runtime / name).write_bytes(data)
            self.runtime_hashes[name] = hashlib.sha256(data).hexdigest()
        self.root = self.work / "FICTIONAL_PRIVATE_PACKAGE"
        self.root.mkdir()
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def fixture(self, name, body=b"Fictional package documentation.\n", *, selected=True):
        path = (self.root if selected else self.work) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return path

    def manifest(self, entries):
        self.serial += 1
        return self.fixture("manifest-" + str(self.serial) + ".json",
                            json.dumps(dict(schema_version=1, files=entries)).encode("utf-8"), selected=False)

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import layout_check as tool\nevents = []\n" + textwrap.dedent(body)
                          + "\nstatus = tool.main(sys.argv[1:])\n" + textwrap.dedent(postlude)
                          + "\nraise SystemExit(status)\n", encoding="utf-8", newline="\n")
        return script

    def process(self, *arguments, expected=0, code=None, script=None, json_output=True):
        tree = {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")}
        retained = {path: digest(path) for path in self.work.rglob("*")
                    if not path.is_symlink() and not path.is_junction() and stat.S_ISREG(path.lstat().st_mode)}
        done = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8",
                               str(script or self.runtime / "layout_check.py"), *map(str, arguments)],
                              cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=40)
        self.assertEqual(done.returncode, expected, done.stdout + done.stderr)
        self.assertEqual(done.stderr, "")
        self.assertEqual(tree, {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")})
        for path, checksum in retained.items():
            self.assertEqual(digest(path), checksum)
        self.assertEqual({p.name for p in self.runtime.iterdir()}, set(RUNTIME))
        self.assertEqual({name: digest(self.runtime / name) for name in RUNTIME}, self.runtime_hashes)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
        self.assertNotIn(str(self.work), done.stdout.replace("\\\\", "\\"))
        self.assertNotIn("FICTIONAL_PRIVATE", done.stdout)
        if not json_output:
            return done.stdout
        self.assertEqual(len(done.stdout.splitlines()), 1)
        value = json.loads(done.stdout)
        if expected in (2, 130):
            self.assertEqual(value, dict(status="REJECTED", code=code or "INTERRUPTED"))
        else:
            self.assertEqual(set(value), {"schema_version", "status", "checked_files", "failed_files", "results"})
            self.assertEqual(value["schema_version"], 1)
            self.assertEqual(value["status"], "FAIL" if expected else "PASS")
        return value

    def run_cli(self, entries=None, *, manifest=None, root=None, **options):
        if manifest is None:
            manifest = self.manifest(entries or [dict(path="example.txt")])
        return self.process("--root", self.root if root is None else root, "--manifest", manifest, **options)

    def assert_rows(self, value, rows):
        expected = [dict(path=path, status="FAIL" if codes else "PASS", codes=list(codes)) for path, codes in rows]
        failed = sum(bool(codes) for path, codes in rows)
        self.assertEqual(value, dict(schema_version=1, status="FAIL" if failed else "PASS",
                                     checked_files=len(rows), failed_files=failed, results=expected))

    def symlink(self, path, target, directory=False):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_LAYOUT_REQUIRE_NATIVE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_passing_manifest_order_schema_and_no_outputs(self):
        self.fixture("z.txt")
        self.fixture("nested/a.py", b"answer = 42\n")
        entries = [dict(path="z.txt"), dict(path="nested/a.py", python_syntax=True)]
        self.assert_rows(self.run_cli(entries), [("z.txt", []), ("nested/a.py", [])])
        self.assertEqual({p.name for p in self.work.iterdir()}, {self.runtime.name, self.root.name, "manifest-1.json"})

    def test_aggregated_findings_preserve_relative_names_without_private_contents(self):
        self.fixture("bad.py", b"def broken(:\n# FICTIONAL_PRIVATE_MARKER\n")
        self.fixture("good.txt")
        value = self.run_cli([dict(path="bad.py", python_syntax=True, forbidden_literals=["fictional_private_marker"]),
                              dict(path="missing.txt"), dict(path="good.txt")], expected=1)
        self.assert_rows(value, [("bad.py", ["PYTHON_SYNTAX", "FORBIDDEN_LITERAL"]),
                                 ("missing.txt", ["MISSING"]), ("good.txt", [])])
        self.assertNotIn("broken", json.dumps(value))
        self.assertNotIn("fictional_private_marker", json.dumps(value))

    def test_presence_only_and_undeclared_files_are_never_read_or_enumerated(self):
        self.fixture("opaque.bin", b"\xff\x00FICTIONAL_PRIVATE_NEVER_READ")
        self.fixture("undeclared/never.py", b"raise AssertionError('FICTIONAL_PRIVATE_EXECUTION')\n")
        script = self.wrapper("""
            def forbidden(*args, **kwargs):
                raise AssertionError('Undeclared tree enumeration attempted')
            os.scandir = forbidden
            Path.iterdir = forbidden
            original = tool.read_bounded
            def read(fd, limit):
                events.append(limit)
                return original(fd, limit)
            tool.read_bounded = read
            """, postlude="assert events == [65536] and status == 0\n")
        self.assert_rows(self.run_cli([dict(path="opaque.bin")], script=script), [("opaque.bin", [])])

    def test_python_syntax_is_static_and_inputs_do_not_use_network(self):
        self.fixture("fictional.py", b"raise RuntimeError('FICTIONAL_PRIVATE_NEVER_EXECUTE')\n")
        self.fixture("link.txt", b"https://example.invalid/fictional\n")
        script = self.wrapper("", prelude="""
            import socket, urllib.request, subprocess, runpy
            def forbidden(*args, **kwargs):
                raise AssertionError('Input execution or network attempted')
            socket.socket = forbidden
            socket.create_connection = forbidden
            urllib.request.urlopen = forbidden
            subprocess.Popen = forbidden
            runpy.run_path = forbidden
            os.system = forbidden
            """)
        self.assert_rows(self.run_cli([dict(path="fictional.py", python_syntax=True),
                                       dict(path="link.txt", forbidden_literals=["not present"])], script=script),
                         [("fictional.py", []), ("link.txt", [])])

    def test_strict_json_duplicate_nonfinite_bom_and_utf8_controls(self):
        bodies = [b'{"schema_version":1,"schema_version":1,"files":[{"path":"a"}]}',
                  b'{"schema_version":1,"files":[{"path":"a","path":"b"}]}',
                  b'{"schema_version":NaN,"files":[]}', b'{"schema_version":Infinity,"files":[]}',
                  b'{"schema_version":-Infinity,"files":[]}', b"\xef\xbb\xbf{}", b"\xff", b"{", b"{} {}"]
        for index, raw in enumerate(bodies):
            with self.subTest(index=index):
                manifest = self.fixture("bad-json.json", raw, selected=False)
                self.run_cli(manifest=manifest, expected=2, code="MANIFEST_INVALID")

    def test_manifest_schema_and_field_types_are_exact(self):
        values = [None, [], {}, dict(schema_version=True, files=[dict(path="a")]),
                  dict(schema_version=1.0, files=[dict(path="a")]), dict(schema_version=2, files=[dict(path="a")]),
                  dict(schema_version=1, files=[], extra=1), dict(schema_version=1, files=[]),
                  dict(schema_version=1, files={}), dict(schema_version=1, files=[None])]
        for row in ({}, dict(path="a", extra=True), dict(path="a", python_syntax=1),
                    dict(path="a", forbidden_literals="needle"), dict(path="a", forbidden_literals=[3])):
            values.append(dict(schema_version=1, files=[row]))
        for index, value in enumerate(values):
            with self.subTest(index=index):
                manifest = self.fixture("invalid-schema.json", json.dumps(value).encode(), selected=False)
                self.run_cli(manifest=manifest, expected=2, code="MANIFEST_INVALID")

    def test_manifest_paths_and_casefold_duplicates_are_rejected(self):
        for path in (None, 1, True, [], "", "../a", "/a", "a//b", "a/./b", "a\\b", "a:stream", "a?b", "a\nname", "a\x7fname", "x"*513):
            with self.subTest(path=repr(path)):
                self.run_cli([dict(path=path)], expected=2, code="MANIFEST_PATH_INVALID")
        for rows in ([dict(path="a"), dict(path="a")], [dict(path="a"), dict(path="A")]):
            self.run_cli(rows, expected=2, code="MANIFEST_PATH_DUPLICATE")

    def test_manifest_exact_sixty_four_kib_and_one_byte_excess(self):
        self.fixture("example.txt")
        raw = b'{"schema_version":1,"files":[{"path":"example.txt"}]}'
        exact = self.fixture("exact.json", raw + b" "*(65536-len(raw)), selected=False)
        self.assert_rows(self.run_cli(manifest=exact), [("example.txt", [])])
        over = self.fixture("over.json", exact.read_bytes() + b" ", selected=False)
        self.run_cli(manifest=over, expected=2, code="INPUT_OR_IO")

    def test_manifest_hundred_entries_exact_and_one_extra(self):
        entries = []
        for index in range(100):
            name = "item-" + str(index) + ".txt"
            self.fixture(name, b"")
            entries.append(dict(path=name))
        self.assert_rows(self.run_cli(entries), [(row["path"], []) for row in entries])
        self.run_cli(entries + [dict(path="extra.txt")], expected=2, code="MANIFEST_INVALID")

    def test_literal_count_and_character_bounds_are_enforced(self):
        self.fixture("example.txt", b"Fictional matching plain text\n")
        self.assert_rows(self.run_cli([dict(path="example.txt", forbidden_literals=[str(i).zfill(2)+"x"*254 for i in range(16)])]),
                         [("example.txt", [])])
        for literals in (["x"]*17, ["x"*257], [""]):
            self.run_cli([dict(path="example.txt", forbidden_literals=literals)], expected=2, code="MANIFEST_INVALID")
        self.assert_rows(self.run_cli([dict(path="example.txt", forbidden_literals=["FICTIONAL"])], expected=1),
                         [("example.txt", ["FORBIDDEN_LITERAL"])])

    def test_selected_file_exact_quarter_mib_and_excess_are_bounded(self):
        self.fixture("exact.txt", b" "*262144)
        self.fixture("over.txt", b" "*262145)
        rows = [dict(path="exact.txt"), dict(path="over.txt"),
                dict(path="exact.txt.copy", forbidden_literals=["not present"])]
        self.fixture("exact.txt.copy", b" "*262144)
        self.assert_rows(self.run_cli(rows, expected=1),
                         [("exact.txt", []), ("over.txt", ["BYTE_LIMIT"]), ("exact.txt.copy", [])])

    def test_two_mib_text_budget_follows_manifest_order(self):
        entries = []
        for index in range(9):
            name = "text-" + str(index) + ".txt"
            self.fixture(name, b" "*262144)
            entries.append(dict(path=name, forbidden_literals=["not present"]))
        self.assert_rows(self.run_cli(entries, expected=1),
                         [(row["path"], [] if index < 8 else ["TOTAL_BYTE_LIMIT"]) for index, row in enumerate(entries)])
        reverse = list(reversed(entries))
        self.assert_rows(self.run_cli(reverse, expected=1),
                         [(row["path"], [] if index < 8 else ["TOTAL_BYTE_LIMIT"]) for index, row in enumerate(reverse)])

    def test_selected_text_bom_utf8_and_nul_syntax_results(self):
        self.fixture("bom.py", b"\xef\xbb\xbfvalue = 42\n")
        self.fixture("bad.txt", b"\xff")
        self.fixture("embedded-zero.py", b"answer=1\x00\n")
        entries = [dict(path="bom.py", python_syntax=True), dict(path="bad.txt", forbidden_literals=["x"]),
                   dict(path="embedded-zero.py", python_syntax=True)]
        self.assert_rows(self.run_cli(entries, expected=1),
                         [("bom.py", []), ("bad.txt", ["TEXT_INVALID"]), ("embedded-zero.py", ["PYTHON_SYNTAX"])])

    def test_help_explicit_arguments_and_fixed_errors(self):
        help_text = self.process("--help", json_output=False)
        self.assertIn("--manifest", help_text)
        for arguments in ((), ("--root", self.root), ("--unknown", "FICTIONAL_PRIVATE_ARGUMENT")):
            self.process(*arguments, expected=2, code="ARGUMENTS_INVALID")
        manifest = self.manifest([dict(path="example.txt")])
        self.run_cli(manifest=manifest, root=self.work / "missing-root", expected=2, code="INPUT_OR_IO")
        self.run_cli(manifest=self.work / "missing-manifest.json", expected=2, code="INPUT_OR_IO")
        self.run_cli(manifest=manifest, root=self.root.anchor, expected=2, code="ROOT_INVALID")
        self.fixture("example.txt")
        self.assert_rows(self.run_cli(manifest=manifest.name, root=self.root.name), [("example.txt", [])])

    def test_native_hardlinked_selected_files_and_manifest_are_rejected(self):
        source = self.fixture("example.txt")
        os.link(source, self.work / "owned-file-hardlink.txt")
        self.assertGreaterEqual(source.stat().st_nlink, 2)
        self.assert_rows(self.run_cli(expected=1), [("example.txt", ["UNSAFE_FILE"])])
        manifest = self.manifest([dict(path="example.txt")])
        alias = self.work / "owned-manifest-hardlink.json"
        os.link(manifest, alias)
        self.run_cli(manifest=alias, expected=2, code="INPUT_OR_IO")

    def test_interrupt_reports_fixed_code_and_releases_descriptors(self):
        selected = self.fixture("example.txt")
        script = self.wrapper("""
            selected = Path(SELECTED)
            target = selected.stat().st_ino
            descriptors = []
            original = tool.read_bounded
            def read(fd, limit):
                descriptors.append(fd)
                if os.fstat(fd).st_ino == target:
                    events.append(True)
                    raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT')
                return original(fd, limit)
            tool.read_bounded = read
            """.replace("SELECTED", repr(str(selected))), postlude="""
            assert status == 130 and events == [True]
            for fd in descriptors:
                try:
                    os.fstat(fd)
                except OSError as error:
                    assert error.errno == 9
                else:
                    raise AssertionError('Owned descriptor remained open')
            fd = os.open(selected, os.O_WRONLY)
            os.close(fd)
            """)
        self.run_cli([dict(path="example.txt", python_syntax=True)], script=script, expected=130)

    def test_native_symlink_root_is_rejected(self):
        self.fixture("example.txt")
        alias = self.work / "linked-root"
        self.symlink(alias, self.root, directory=True)
        self.run_cli(root=alias, expected=2, code="INPUT_OR_IO")

    def test_native_symlink_manifest_leaf_and_parent_are_rejected(self):
        self.fixture("example.txt")
        manifest = self.manifest([dict(path="example.txt")])
        alias = self.work / "linked-manifest.json"
        self.symlink(alias, manifest)
        self.run_cli(manifest=alias, expected=2, code="INPUT_OR_IO")
        folder = self.work / "owned-controls"
        folder.mkdir()
        (folder / "manifest.json").write_bytes(manifest.read_bytes())
        linked = self.work / "linked-control-parent"
        self.symlink(linked, folder, directory=True)
        self.run_cli(manifest=linked / "manifest.json", expected=2, code="INPUT_OR_IO")

    def test_native_symlink_selected_leaf_and_parent_are_findings(self):
        source = self.fixture("outside-owned-target.txt", b"\xff"*262145, selected=False)
        self.symlink(self.root / "linked.txt", source)
        folder = self.work / "owned-target-directory"
        folder.mkdir()
        (folder / "example.txt").write_bytes(b"\xff")
        self.symlink(self.root / "linked-parent", folder, directory=True)
        entries = [dict(path="linked.txt", python_syntax=True), dict(path="linked-parent/example.txt", python_syntax=True)]
        leaf = "UNSAFE_FILE" if os.name == "nt" else "UNSAFE_PATH"
        self.assert_rows(self.run_cli(entries, expected=1), [("linked.txt", [leaf]), ("linked-parent/example.txt", ["UNSAFE_PATH"])])

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_boundaries_are_refused(self):
        self.fixture("example.txt")
        root_alias = self.work / "root-junction"
        self.junction(root_alias, self.root)
        self.run_cli(root=root_alias, expected=2, code="INPUT_OR_IO")
        controls = self.work / "owned-controls"
        controls.mkdir()
        manifest = self.manifest([dict(path="example.txt")])
        (controls / "manifest.json").write_bytes(manifest.read_bytes())
        control_alias = self.work / "control-junction"
        self.junction(control_alias, controls)
        self.run_cli(manifest=control_alias / "manifest.json", expected=2, code="INPUT_OR_IO")
        target = self.work / "owned-selected-target"
        target.mkdir()
        (target / "example.txt").write_bytes(b"Fictional selected target\n")
        selected_alias = self.root / "selected-junction"
        self.junction(selected_alias, target)
        self.assert_rows(self.run_cli([dict(path="selected-junction/example.txt")], expected=1),
                         [("selected-junction/example.txt", ["UNSAFE_PATH"])])

    @unittest.skipUnless(os.name == "nt", "Native Windows alias fixture")
    def test_native_windows_alternate_stream_and_alias_names_are_refused(self):
        source = self.fixture("example.txt")
        stream = str(source) + ":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b"Fictional named stream")
        self.assert_rows(self.run_cli(), [("example.txt", [])])
        self.run_cli(manifest=stream, expected=2, code="PATH_INVALID")
        for path in ("example.txt:fictional-stream",):
            self.run_cli([dict(path=path)], expected=2, code="MANIFEST_PATH_INVALID")
        for path in ("CON.txt", "example.txt.", "example.txt "):
            self.assert_rows(self.run_cli([dict(path=path)], expected=1), [(path, ["UNSAFE_PATH"])])
        self.run_cli(root=str(self.root) + ".", expected=2, code="PATH_INVALID")
        with open(stream, "rb") as handle:
            self.assertEqual(handle.read(), b"Fictional named stream")

    @unittest.skipUnless(os.name == "nt", "Native Windows held input fixture")
    def test_native_windows_held_selected_input_refuses_conflicting_writer_and_releases(self):
        selected = self.fixture("example.txt", b"answer = 42\n")
        script = self.wrapper("""
            selected = Path(SELECTED)
            target = selected.stat().st_ino
            original = tool.read_bounded
            def read(fd, limit):
                if os.fstat(fd).st_ino == target:
                    try:
                        conflicting = os.open(selected, os.O_WRONLY)
                    except PermissionError as error:
                        assert error.errno == 13
                    except OSError as error:
                        raise AssertionError('Unexpected native sharing fixture error') from error
                    else:
                        os.close(conflicting)
                        raise AssertionError('Selected source unexpectedly allowed a data writer')
                    events.append(True)
                return original(fd, limit)
            tool.read_bounded = read
            """.replace("SELECTED", repr(str(selected))), postlude="""
            assert events == [True] and status == 0
            reopened = os.open(selected, os.O_WRONLY)
            os.close(reopened)
            """)
        self.assert_rows(self.run_cli([dict(path="example.txt", python_syntax=True)], script=script), [("example.txt", [])])

    @unittest.skipUnless(os.name != "nt", "Native POSIX FIFO fixture")
    def test_native_posix_fifo_selected_and_manifest_fail_without_blocking(self):
        selected = self.root / "owned-fifo.txt"
        os.mkfifo(selected, 0o600)
        self.assert_rows(self.run_cli([dict(path="owned-fifo.txt")], expected=1), [("owned-fifo.txt", ["UNSAFE_FILE"])])
        control = self.work / "owned-manifest-fifo"
        os.mkfifo(control, 0o600)
        self.run_cli(manifest=control, expected=2, code="INPUT_OR_IO")

    def test_controlled_short_read_and_identity_change_are_findings(self):
        selected = self.fixture("example.txt", b"answer = 42\n")
        for mode in ("short", "identity"):
            script = self.wrapper("""
                target = Path(SELECTED).stat().st_ino
                original = tool.read_bounded
                def read(fd, limit):
                    if os.fstat(fd).st_ino != target:
                        return original(fd, limit)
                    events.append(True)
                    if MODE == 'short':
                        previous = os.read
                        def empty(selected_fd, size):
                            return b'' if selected_fd == fd else previous(selected_fd, size)
                        os.read = empty
                        try:
                            return original(fd, limit)
                        finally:
                            os.read = previous
                    previous = tool.identity
                    calls = []
                    def changed(info):
                        calls.append(True)
                        return previous(info) + (len(calls),)
                    tool.identity = changed
                    try:
                        return original(fd, limit)
                    finally:
                        tool.identity = previous
                tool.read_bounded = read
                """.replace("SELECTED", repr(str(selected))).replace("MODE", repr(mode)),
                                  postlude="assert events == [True] and status == 1\n")
            self.assert_rows(self.run_cli([dict(path="example.txt", python_syntax=True)], script=script, expected=1),
                             [("example.txt", ["FILE_CHANGED"])])

    def test_failed_read_still_reserves_observed_text_budget(self):
        entries = []
        for index in range(9):
            name = "reserved-" + str(index) + ".txt"
            self.fixture(name, b" "*262144)
            entries.append(dict(path=name, forbidden_literals=["not present"]))
        script = self.wrapper("""
            original = tool.read_bounded
            def read(fd, limit):
                if limit == 262144 and not events:
                    events.append(True)
                    raise tool.EntryFailure('FILE_CHANGED')
                return original(fd, limit)
            tool.read_bounded = read
            """, postlude="assert events == [True] and status == 1\n")
        self.assert_rows(self.run_cli(entries, script=script, expected=1),
                         [(row["path"], ["FILE_CHANGED"] if index == 0 else ["TOTAL_BYTE_LIMIT"] if index == 8 else [])
                          for index, row in enumerate(entries)])

    def test_repeated_control_and_entry_failures_release_owned_descriptors(self):
        selected = self.fixture("example.txt", b"answer = 42\n")
        for mode in ("control", "entry"):
            script = self.wrapper("""
                import contextlib, io, json
                target = Path(SELECTED).stat().st_ino
                descriptors = []
                original = tool.read_bounded
                def read(fd, limit):
                    descriptors.append(fd)
                    if MODE == 'control' or os.fstat(fd).st_ino == target:
                        events.append(True)
                        raise OSError('FICTIONAL_PRIVATE_OS_ERROR')
                    return original(fd, limit)
                tool.read_bounded = read
                def closed():
                    for fd in descriptors:
                        try:
                            os.fstat(fd)
                        except OSError as error:
                            assert error.errno == 9
                        else:
                            raise AssertionError('Owned descriptor remained open')
                for iteration in range(16):
                    capture = io.StringIO()
                    with contextlib.redirect_stdout(capture):
                        observed = tool.main(sys.argv[1:])
                    assert observed == (2 if MODE == 'control' else 1)
                    value = json.loads(capture.getvalue())
                    if MODE == 'control':
                        assert value == dict(status='REJECTED', code='INPUT_OR_IO')
                    else:
                        assert value['results'][0]['codes'] == ['READ_ERROR']
                    closed()
                """.replace("SELECTED", repr(str(selected))).replace("MODE", repr(mode)),
                                  postlude="assert len(events) == 17\nclosed()\n")
            value = self.run_cli([dict(path="example.txt", python_syntax=True)], script=script,
                                 expected=2 if mode == "control" else 1, code="INPUT_OR_IO" if mode == "control" else None)
            if mode == "entry":
                self.assert_rows(value, [("example.txt", ["READ_ERROR"])])

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
        handle = kernel.CreateFileW(str(link), 0x40000000, 0, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            buffer = ctypes.create_string_buffer(data)
            returned = wintypes.DWORD()
            if not kernel.DeviceIoControl(handle, 0x000900A4, buffer, len(data), None, 0,
                                          ctypes.byref(returned), None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(handle)
        self.assertTrue(link.is_junction())


if __name__ == "__main__":
    unittest.main()
