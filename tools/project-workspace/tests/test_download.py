"""Fresh copied-runtime CLI checks with authored opaque input and owned outputs."""

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
RUNTIME = ("workspace.py", "workspace_windows.py")
FOLDERS = ("original", "working", "evidence/screenshots", "evidence/test-output", "deliverables", "logs", "rollback")
CONTROL = """# Private project control record

Status: INTAKE

- Preserve original input bytes. Work on a separate copy.
- Record scope, acceptance criteria, dependencies, and unresolved decisions.
- Record actual commands and results; distinguish static checks from runtime proof.
- Keep credentials, personal data, operational records, and private evidence local.
- Prepare a separately reviewed export for sharing.
- Record rollback instructions and acceptance before closure.

## Decisions

Pending.

## Validation

Not run.

## Handoff

Pending.
"""


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
        self.temp = tempfile.TemporaryDirectory(prefix="workspace-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied runtime"
        self.runtime.mkdir()
        self.runtime_hashes = {}
        for name in RUNTIME:
            data = (ROOT / name).read_bytes()
            (self.runtime / name).write_bytes(data)
            self.runtime_hashes[name] = hashlib.sha256(data).hexdigest()
        self.root = self.work / "private parent"
        self.root.mkdir()
        self.source = self.work / "FICTIONAL_PRIVATE_SOURCE.bin"
        self.payload = b"Fictional opaque intake\r\n\x00\xff\n"
        self.source.write_bytes(self.payload)
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import workspace as tool\nevents = []\n" + textwrap.dedent(body)
                          + "\nstatus = tool.main(sys.argv[1:])\n" + textwrap.dedent(postlude)
                          + "\nraise SystemExit(status)\n", encoding="utf-8", newline="\n")
        return script

    def process(self, *arguments, expected=0, script=None, json_output=True):
        retained = {path: digest(path) for path in self.work.rglob("*")
                    if not path.is_symlink() and not path.is_junction() and stat.S_ISREG(path.lstat().st_mode)}
        result = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8",
                                 str(script or self.runtime / "workspace.py"), *map(str, arguments)],
                                cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=40)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        for path, checksum in retained.items():
            self.assertEqual(digest(path), checksum)
        self.assertEqual({p.name for p in self.runtime.iterdir()}, set(RUNTIME))
        self.assertEqual({name: digest(self.runtime / name) for name in RUNTIME}, self.runtime_hashes)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
        self.assertNotIn(str(self.work), result.stdout.replace("\\\\", "\\"))
        self.assertNotIn("FICTIONAL_PRIVATE", result.stdout)
        if not json_output:
            return result.stdout
        self.assertEqual(len(result.stdout.splitlines()), 1)
        report = json.loads(result.stdout)
        if expected:
            self.assertEqual(report, dict(status="ERROR", code="WORKSPACE_INTERRUPTED" if expected == 130
                                          else "WORKSPACE_INPUT_OR_OUTPUT_ERROR"))
        return report

    def run_cli(self, *, name="fictional", root=None, source=None, create=False, expected=0, script=None):
        arguments = ["--root", self.root if root is None else root, "--name", name]
        if source is not None:
            arguments += ["--source", source]
        if create:
            arguments += ["--create"]
        return self.process(*arguments, expected=expected, script=script)

    def assert_layout(self, name="fictional", payload=None):
        destination = self.root / name
        directories = {path.relative_to(destination).as_posix() for path in destination.rglob("*") if path.is_dir()}
        self.assertEqual(directories, set(FOLDERS) | {"evidence"})
        expected = {".gitignore", "CONTROL.md"}
        if payload is not None:
            expected |= {"original/intake.bin", "working/intake.bin", "original/SOURCE.json"}
        self.assertEqual({path.relative_to(destination).as_posix() for path in destination.rglob("*") if path.is_file()}, expected)
        self.assertEqual((destination / ".gitignore").read_bytes(), ("*" + os.linesep).encode())
        self.assertEqual((destination / "CONTROL.md").read_bytes(), CONTROL.replace("\n", os.linesep).encode("utf-8"))
        if payload is not None:
            for folder in ("original", "working"):
                self.assertEqual((destination / folder / "intake.bin").read_bytes(), payload)
            metadata = dict(sha256=hashlib.sha256(payload).hexdigest(), size=len(payload))
            raw = (json.dumps(metadata, indent=2) + "\n").replace("\n", os.linesep).encode("utf-8")
            self.assertEqual((destination / "original/SOURCE.json").read_bytes(), raw)
            self.assertNotIn(self.source.name, (destination / "original/SOURCE.json").read_text())
        return destination

    def symlink(self, path, target, directory=False):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_WORKSPACE_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def output_fixture_wrapper(self, action, source=None):
        # Creation errors are fixture failures, not expected application errors.
        # AssertionError escapes workspace.main's handled OSError/ValueError set.
        return self.wrapper("""
            selected = Path(SOURCE_VALUE)
            def insert(path):
                try:
                    ACTION_VALUE
                except OSError as error:
                    raise AssertionError('Native output fixture creation failed') from error
                events.append(str(path))
            if os.name == 'nt':
                backend = tool._windows()
                original = backend.exclusive_write
                def write(path, data, error):
                    if Path(path).name == 'intake.bin' and Path(path).parent.name == 'original':
                        insert(Path(path))
                    return original(path, data, error)
                backend.exclusive_write = write
            else:
                original = Path.open
                def opened(path, mode='r', *args, **kwargs):
                    if path.name == 'intake.bin' and path.parent.name == 'original' and mode == 'xb':
                        insert(path)
                    return original(path, mode, *args, **kwargs)
                Path.open = opened
            """.replace("SOURCE_VALUE", repr(str(source or self.source))).replace("ACTION_VALUE", action),
                            postlude="assert len(events) == 1 and status == 2\n")

    def test_default_plan_writes_nothing_and_does_not_reserve_name(self):
        expected = dict(status="PLAN_ONLY", folders=list(FOLDERS), source_selected=False)
        self.assertEqual(self.run_cli(), expected)
        self.assertEqual(self.run_cli(), expected)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_optional_source_is_read_during_plan_without_writes(self):
        script = self.wrapper("""
            original = tool.source_bytes
            def selected(source):
                events.append(source)
                return original(source)
            tool.source_bytes = selected
            """, postlude="assert len(events) == 1 and status == 0\n")
        report = self.run_cli(source=self.source, script=script)
        self.assertEqual(report, dict(status="PLAN_ONLY", folders=list(FOLDERS), source_selected=True))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_create_without_source_has_only_neutral_empty_layout(self):
        self.assertEqual(self.run_cli(create=True), dict(status="WORKSPACE_CREATED", source_verified=False))
        self.assert_layout()

    def test_empty_and_invalid_binary_sources_are_copied_as_opaque_bytes(self):
        for index, payload in enumerate((b"", b"{invalid fictional JSON\x00\xff", self.payload)):
            selected = self.work / ("opaque-" + str(index) + ".bin")
            selected.write_bytes(payload)
            name = "opaque-" + str(index)
            self.assertEqual(self.run_cli(name=name, source=selected, create=True),
                             dict(status="WORKSPACE_CREATED", source_verified=True))
            self.assert_layout(name, payload)

    def test_source_sixteen_mib_exact_cap_and_one_extra_byte(self):
        exact = self.work / "exact-cap.bin"
        payload = b"\x00\xff" * (8 * 1024 * 1024)
        exact.write_bytes(payload)
        excess = self.work / "over-cap.bin"
        excess.write_bytes(payload + b"x")
        self.run_cli(name="exact", source=exact, create=True)
        self.assert_layout("exact", payload)
        self.run_cli(name="excess-plan", source=excess, expected=2)
        self.run_cli(name="excess-create", source=excess, create=True, expected=2)
        self.assertFalse((self.root / "excess-plan").exists() or (self.root / "excess-create").exists())

    def test_control_source_metadata_and_gitignore_have_exact_platform_bytes(self):
        self.run_cli(source=self.source, create=True)
        destination = self.assert_layout(payload=self.payload)
        self.assertIn("Not run.", (destination / "CONTROL.md").read_text())
        self.assertNotIn(str(self.work), (destination / "CONTROL.md").read_text())
        self.assertEqual(len(list((destination / "original").iterdir())), 2)
        self.assertEqual(len(list((destination / "working").iterdir())), 1)

    def test_existing_file_and_directory_destinations_are_never_overwritten(self):
        file = self.root / "retained-file"
        file.write_bytes(b"Fictional retained bytes")
        directory = self.root / "retained-dir"
        directory.mkdir()
        (directory / "retained.txt").write_bytes(b"Fictional retained bytes")
        for name in (file.name, directory.name):
            for create in (False, True):
                self.run_cli(name=name, source=self.source, create=create, expected=2)

    def test_destination_appearing_after_plan_preserves_external_owned_marker(self):
        self.run_cli()
        destination = self.root / "fictional"
        destination.mkdir()
        marker = destination / "retained.txt"
        marker.write_bytes(b"Fictional independent reservation")
        self.run_cli(create=True, expected=2)
        self.assertEqual(marker.read_bytes(), b"Fictional independent reservation")

    def test_invalid_and_reserved_names_fail_without_output(self):
        for name in ("", "CON", "con", "nul", "a/b", "../outside", "has.dot", "Upper", "x" * 65):
            with self.subTest(name=name):
                self.run_cli(name=name, create=True, expected=2)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_help_explicit_relative_root_and_invalid_arguments(self):
        self.assertIn("--create", self.process("--help", json_output=False))
        self.process(expected=2)
        self.process("--root", expected=2)
        self.process("--FICTIONAL_PRIVATE_OPTION", "FICTIONAL_PRIVATE_VALUE", expected=2)
        self.assertEqual(self.run_cli(root=self.root.relative_to(self.work)), self.run_cli())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_missing_root_file_root_and_invalid_sources_have_fixed_private_errors(self):
        self.run_cli(root=self.work / "FICTIONAL_PRIVATE_MISSING", expected=2)
        self.run_cli(root=self.source, expected=2)
        self.run_cli(source=self.work / "FICTIONAL_PRIVATE_MISSING", create=True, expected=2)
        self.run_cli(source=self.root, create=True, expected=2)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_controlled_child_never_executes_or_fetches_opaque_input(self):
        self.source.write_bytes(b"raise AssertionError('DO_NOT_EXECUTE')\nhttps://fictional.invalid/not-requested\n")
        script = self.wrapper("", prelude="""
            import socket, urllib.request, subprocess
            def forbidden(*args, **kwargs):
                raise AssertionError('UNREQUESTED_EXECUTION_OR_NETWORK')
            socket.socket = forbidden
            socket.create_connection = forbidden
            urllib.request.urlopen = forbidden
            subprocess.run = forbidden
            os.system = forbidden
            """)
        self.run_cli(source=self.source, create=True, script=script)
        self.assert_layout(payload=self.source.read_bytes())

    def test_controlled_late_failure_retains_complete_looking_unconfirmed_output(self):
        script = self.wrapper("""
            if os.name == 'nt':
                backend = tool._windows()
                original = backend.exclusive_write
                def write(path, data, error):
                    original(path, data, error)
                    if Path(path).name == 'CONTROL.md':
                        events.append(True)
                        raise OSError('FICTIONAL_PRIVATE_LATE_FAILURE')
                backend.exclusive_write = write
            else:
                original = Path.write_text
                def write(path, data, *args, **kwargs):
                    result = original(path, data, *args, **kwargs)
                    if path.name == 'CONTROL.md':
                        events.append(True)
                        raise OSError('FICTIONAL_PRIVATE_LATE_FAILURE')
                    return result
                Path.write_text = write
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(source=self.source, create=True, script=script, expected=2)
        self.assert_layout(payload=self.payload)

    @unittest.skipUnless(os.name == "nt", "Native Windows output fixture")
    def test_native_windows_short_writes_complete_all_outputs(self):
        script = self.wrapper("""
            original = os.write
            def short(fd, data):
                events.append(len(data))
                return original(fd, data[:3])
            os.write = short
            """, postlude="assert len(events) > 10 and status == 0\n")
        self.run_cli(source=self.source, create=True, script=script)
        self.assert_layout(payload=self.payload)

    @unittest.skipUnless(os.name == "nt", "Native Windows output fixture")
    def test_native_windows_zero_write_retains_partial_tree(self):
        script = self.wrapper("""
            def zero(fd, data):
                events.append(True)
                return 0
            os.write = zero
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(source=self.source, create=True, script=script, expected=2)
        destination = self.root / "fictional"
        self.assertTrue(destination.is_dir())
        self.assertEqual((destination / ".gitignore").read_bytes(), b"")
        self.assertFalse((destination / "CONTROL.md").exists())

    @unittest.skipUnless(os.name == "nt", "Native Windows output fixture")
    def test_native_windows_flush_failure_retains_unconfirmed_tree(self):
        script = self.wrapper("""
            original_open, original_flush = os.open, os.fsync
            names = {}
            def opened(path, *args, **kwargs):
                fd = original_open(path, *args, **kwargs)
                names[fd] = Path(path).name
                return fd
            def flushed(fd):
                if names.get(fd) == 'CONTROL.md':
                    events.append(True)
                    raise OSError('FICTIONAL_PRIVATE_FLUSH_FAILURE')
                return original_flush(fd)
            os.open, os.fsync = opened, flushed
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(source=self.source, create=True, script=script, expected=2)
        self.assert_layout(payload=self.payload)

    @unittest.skipUnless(os.name == "nt", "Native Windows output fixture")
    def test_native_windows_readback_mismatch_refuses_completion(self):
        script = self.wrapper("""
            backend = tool._windows()
            original = backend.read_bounded
            def mismatched(path, *args, **kwargs):
                data = original(path, *args, **kwargs)
                if Path(path).name == 'CONTROL.md':
                    events.append(True)
                    return b'Fictional incorrect readback'
                return data
            backend.read_bounded = mismatched
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(source=self.source, create=True, script=script, expected=2)
        self.assert_layout(payload=self.payload)

    def test_native_hardlink_source_is_supported_and_output_leaf_is_not_overwritten(self):
        linked = self.work / "hardlinked-source.bin"
        os.link(self.source, linked)
        self.run_cli(name="linked-source", source=linked, create=True)
        self.assert_layout("linked-source", self.payload)
        script = self.output_fixture_wrapper("os.link(selected, path)")
        self.run_cli(source=self.source, create=True, script=script, expected=2)
        self.assertEqual((self.root / "fictional/original/intake.bin").read_bytes(), self.payload)

    def test_native_symlink_root_is_refused(self):
        link = self.work / "linked root"
        self.symlink(link, self.root, directory=True)
        self.run_cli(root=link, create=True, expected=2)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_native_symlink_source_and_parent_are_refused(self):
        link = self.work / "linked source.bin"
        self.symlink(link, self.source)
        self.run_cli(source=link, create=True, expected=2)
        directory = self.work / "real source parent"
        directory.mkdir()
        selected = directory / "source.bin"
        selected.write_bytes(self.payload)
        parent = self.work / "linked source parent"
        self.symlink(parent, directory, directory=True)
        self.run_cli(source=parent / selected.name, create=True, expected=2)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_native_symlink_destination_is_preserved(self):
        target = self.work / "retained destination"
        target.mkdir()
        marker = target / "retained.txt"
        marker.write_bytes(b"Fictional retained target")
        link = self.root / "fictional"
        self.symlink(link, target, directory=True)
        self.run_cli(create=True, expected=2)
        self.run_cli(expected=2)
        self.assertTrue(link.is_symlink())
        self.assertEqual(marker.read_bytes(), b"Fictional retained target")

    def test_native_symlink_output_leaf_preserves_targets(self):
        # Preflight occurs outside the runtime handler so only explicit Windows
        # WinError 1314 can become an optional capability skip.
        probe = self.work / "native privilege probe"
        self.symlink(probe, self.source)
        script = self.output_fixture_wrapper("os.symlink(selected, path)")
        self.run_cli(source=self.source, create=True, script=script, expected=2)
        self.assertTrue((self.root / "fictional/original/intake.bin").is_symlink())
        absent = self.work / "absent output target.bin"
        script = self.output_fixture_wrapper("os.symlink(selected, path)", source=absent)
        self.run_cli(name="dangling", source=self.source, create=True, script=script, expected=2)
        self.assertTrue((self.root / "dangling/original/intake.bin").is_symlink())
        self.assertFalse(absent.exists())

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_boundaries_are_refused(self):
        target = self.work / "junction target"
        target.mkdir()
        selected = target / "source.bin"
        selected.write_bytes(self.payload)
        for link in (self.work / "junction parent", self.root / "fictional"):
            self.junction(link, target)
        self.run_cli(root=self.work / "junction parent", create=True, expected=2)
        self.run_cli(source=self.work / "junction parent/source.bin", create=True, name="new", expected=2)
        self.run_cli(create=True, expected=2)
        self.assertEqual({path.name for path in target.iterdir()}, {"source.bin"})

    @unittest.skipUnless(os.name == "nt", "Native Windows alternate stream fixture")
    def test_native_windows_alternate_stream_is_refused_and_unnamed_data_retained(self):
        stream = str(self.source) + ":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b"Fictional named stream")
        self.run_cli(source=stream, create=True, expected=2)
        self.assertEqual(list(self.root.iterdir()), [])
        self.run_cli(source=self.source, create=True)
        destination = self.assert_layout(payload=self.payload)
        for folder in ("original", "working"):
            with self.assertRaises(FileNotFoundError):
                with open(str(destination / folder / "intake.bin") + ":fictional-stream", "rb"):
                    pass
        with open(stream, "rb") as handle:
            self.assertEqual(handle.read(), b"Fictional named stream")

    @unittest.skipUnless(os.name != "nt", "Native POSIX FIFO fixture")
    def test_native_posix_fifo_source_is_refused_before_open(self):
        fifo = self.work / "fictional-fifo"
        os.mkfifo(fifo, 0o600)
        self.run_cli(source=fifo, create=True, expected=2)
        self.assertEqual(list(self.root.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Native Windows interruption fixture")
    def test_native_windows_interrupt_retains_new_tree(self):
        script = self.wrapper("""
            backend = tool._windows()
            original = backend.exclusive_write
            def interrupted(path, data, error):
                original(path, data, error)
                if Path(path).name == 'CONTROL.md':
                    events.append(True)
                    raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT_DETAIL')
            backend.exclusive_write = interrupted
            """, postlude="assert events == [True] and status == 130\n")
        self.run_cli(source=self.source, create=True, script=script, expected=130)
        self.assert_layout(payload=self.payload)

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
