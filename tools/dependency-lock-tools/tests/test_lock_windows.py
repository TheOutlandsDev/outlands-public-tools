"""Fictional Windows file fixtures and portable public lock-contract checks."""

import contextlib
import ctypes
from ctypes import wintypes as w
import io
import json
import os
from pathlib import Path
import random
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import lock_common as common
import lock_windows as win
import report_to_lock as converter
import verify_locks as verifier


HERE = Path(__file__).resolve().parents[1]
HASH_A = "a" * 64
HASH_B = "b" * 64
CORE = {"Rejected": common.LockError, "EntryFailure": common.LockError}


def item(name="sample-package", version="1.2.3", digest=HASH_A):
    return {
        "metadata": {"name": name, "version": version},
        "download_info": {"archive_info": {"hashes": {"sha256": digest}}},
    }


def report(*records):
    return {"version": "1", "install": list(records or (item(),))}


def lock(name="sample-package", version="1.2.3", digest=HASH_A):
    return f"{name}=={version} \\\n    --hash=sha256:{digest}\n".encode()


class PortableContractTests(unittest.TestCase):
    def test_partial_native_writes_retry_all_bytes(self):
        observed = bytearray()

        def write(_handle, buffer, length, written, _overlapped):
            size = min(length, 7)
            observed.extend(buffer.raw[:size])
            written._obj.value = size
            return 1

        native = object.__new__(win.Native)
        native.core = CORE
        native.dll = SimpleNamespace(WriteFile=write)
        data = bytes(range(256)) * 300
        native.write(None, data)
        self.assertEqual(bytes(observed), data)

    def test_zero_invalid_and_failed_native_writes_are_rejected(self):
        native = object.__new__(win.Native)
        native.core = CORE
        for reported, succeeded in ((0, 1), (999, 1), (1, 0)):

            def write(_handle, _buffer, _length, written, _overlapped):
                written._obj.value = reported
                return succeeded

            native.dll = SimpleNamespace(WriteFile=write)
            with self.assertRaises(common.LockError):
                native.write(None, b"Fictional bytes")

    def test_native_flush_failure_is_a_fixed_error(self):
        native = object.__new__(win.Native)
        native.core = CORE
        native.dll = SimpleNamespace(FlushFileBuffers=lambda _handle: 0)
        with self.assertRaises(common.LockError) as caught:
            native.flush(None)
        self.assertEqual(str(caught.exception), "OUTPUT_IO_ERROR")

    def test_windows_components_refuse_ambiguous_names(self):
        for name in (
            "nul.txt",
            "CON",
            "COM1.json",
            "LPT" + chr(0xB9),
            "file.",
            "file ",
            "a:b",
            "a/b",
            "a\\b",
            "..",
            "bad\x00name",
        ):
            self.assertFalse(win._component(name), name)
        for name in ("sample.lock", "fictional folder", "README.md"):
            self.assertTrue(win._component(name), name)

    def test_windows_api_rejects_unsupported_platform(self):
        if os.name == "nt":
            self.skipTest("Unsupported-platform check runs on POSIX")
        with self.assertRaises(common.LockError):
            win.Native(CORE)

    def test_seeded_reports_preserve_public_strict_roundtrip(self):
        rng = random.Random(9321)
        for count in range(1, 41):
            records = [
                item(f"Sample_Package_{i:03}", f"1.{i}", HASH_A if i % 2 else HASH_B)
                for i in range(count)
            ]
            first = converter.render_lock(
                converter.records_from_report(report(*records))
            )
            rng.shuffle(records)
            second = converter.render_lock(
                converter.records_from_report(report(*records))
            )
            self.assertEqual(first, second)
            self.assertEqual(verifier.validate_lock(first), count)

    def test_unsupported_active_requirements_remain_rejected(self):
        for value in (
            b"--index-url fictional-index\n",
            b"-r fictional.txt\n",
            b"sample @ fictional:artifact\n",
            b"sample==1.*\n",
            lock() + lock(),
            lock("Sample_Package"),
            lock("sample-zeta") + lock("sample-alpha"),
            b"sample==1.0 \\\n# fictional intervening comment\n    --hash=sha256:"
            + HASH_A.encode()
            + b"\n",
        ):
            with self.assertRaises(common.LockError):
                verifier.validate_lock(value)

    def test_json_limits_duplicates_and_encoding_remain_strict(self):
        for value in (
            b'{"version":"1","version":"1"}',
            b'{"sample":NaN}',
            b'{"sample":1e999}',
            b"\xff",
            b"[" * 65 + b"0" + b"]" * 65,
            b"x" * (common.MAX_REPORT_BYTES + 1),
        ):
            with self.assertRaises(common.LockError):
                common.strict_json(value)

    def test_modern_legacy_hash_and_conflict_behavior_is_preserved(self):
        record = item()
        archive = record["download_info"]["archive_info"]
        archive["hash"] = "sha256=" + HASH_A.upper()
        self.assertEqual(len(converter.records_from_report(report(record))), 1)
        archive["hash"] = "sha256=" + HASH_B
        with self.assertRaises(common.LockError):
            converter.records_from_report(report(record))
        archive.pop("hashes")
        self.assertEqual(
            converter.records_from_report(report(record))["sample-package"][1], HASH_B
        )

    def test_lock_and_report_counts_types_and_bounds_are_preserved(self):
        for value in (b"", b"# Fictional comment only\n", b"\xff", b"\t" + lock()):
            with self.assertRaises(common.LockError):
                verifier.validate_lock(value)
        with patch.object(
            verifier, "read_bounded", side_effect=AssertionError("NO_READ")
        ):
            for paths in ([], [Path("fictional.lock")] * (common.MAX_LOCKS + 1)):
                with self.assertRaises(common.LockError):
                    verifier.verify(paths)
        for payload in (
            {"version": True},
            {"version": "2"},
            {"version": "1", "install": []},
        ):
            with self.assertRaises(common.LockError):
                converter.records_from_report(payload)


@unittest.skipUnless(os.name == "nt", "Native Windows fixture")
class NativeWindowsTests(unittest.TestCase):
    def setUp(self):
        loader = patch.object(common, "windows_backend", return_value=win)
        loader.start()
        self.addCleanup(loader.stop)
        base = Path(
            os.environ.get("OUTLANDS_TEST_TEMP", tempfile.gettempdir())
        ).resolve()
        self.temporary = tempfile.TemporaryDirectory(dir=base)
        self.fixture = Path(self.temporary.name)

        def cleanup():
            target = self.fixture.resolve()
            if target == base or not target.is_relative_to(base):
                raise RuntimeError("UNEXPECTED_CLEANUP_TARGET")
            self.temporary.cleanup()

        self.addCleanup(cleanup)
        self.folder = self.fixture / "fictional-long-directory"
        self.folder.mkdir()
        self.source = self.folder / "fictional-input-report-long.json"
        self.source.write_text(json.dumps(report()), encoding="utf-8")
        self.output = self.folder / "fictional-output-lock-long.lock"

    def unavailable_link(self, message):
        if os.environ.get("OUTLANDS_LOCK_REQUIRE_NATIVE_LINKS") == "1":
            self.fail(message)
        self.skipTest(message)

    def invoke(self, command, args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = command(args)
        self.assertEqual(errors.getvalue(), "")
        self.assertNotIn(str(self.fixture), output.getvalue())
        return code, json.loads(output.getvalue()), output.getvalue()

    def convert(self, source=None, output=None):
        return self.invoke(
            converter.main,
            [
                "--report",
                str(source or self.source),
                "--output",
                str(output or self.output),
            ],
        )

    def test_conversion_is_deterministic_strict_and_preserves_source_bytes(self):
        before = self.source.read_bytes()
        self.assertEqual(converter.convert(self.source, self.output), 1)
        second = self.folder / "fictional-second.lock"
        self.assertEqual(converter.convert(self.source, second), 1)
        self.assertEqual(self.output.read_bytes(), second.read_bytes())
        self.assertEqual(verifier.verify([self.output]), 1)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(verifier.validate_lock(self.output.read_bytes()), 1)

    def test_cli_counts_and_rejection_details_are_redacted(self):
        code, value, _ = self.convert()
        self.assertEqual((code, value), (0, {"result": "LOCK_WRITTEN", "packages": 1}))
        code, value, _ = self.invoke(verifier.main, [str(self.output)])
        self.assertEqual(
            (code, value), (0, {"result": "PASS", "locks": 1, "package_records": 1})
        )
        for command in (converter.main, verifier.main):
            code, _, text = self.invoke(
                command, ["--unexpected", "fictional-private-canary"]
            )
            self.assertEqual(code, 2)
            self.assertNotIn("fictional-private-canary", text)

    def test_both_cli_scripts_work_in_fresh_processes(self):
        commands = [
            [
                str(HERE / "report_to_lock.py"),
                "--report",
                str(self.source),
                "--output",
                str(self.output),
            ],
            [str(HERE / "verify_locks.py"), str(self.output)],
        ]
        for args in commands:
            done = subprocess.run(
                [sys.executable, "-B", *args],
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stderr, "")
            self.assertNotIn(str(self.fixture), done.stdout)
            self.assertIn(json.loads(done.stdout)["result"], ("LOCK_WRITTEN", "PASS"))

    def test_existing_file_and_directory_are_never_replaced(self):
        self.output.write_bytes(b"Fictional existing bytes\n")
        code, _, _ = self.convert()
        self.assertEqual(code, 2)
        self.assertEqual(self.output.read_bytes(), b"Fictional existing bytes\n")
        self.output.unlink()
        self.output.mkdir()
        (self.output / "fictional-kept.txt").write_bytes(b"kept")
        self.assertEqual(self.convert()[0], 2)
        self.assertEqual((self.output / "fictional-kept.txt").read_bytes(), b"kept")

    def test_report_cannot_be_overwritten_as_output(self):
        before = self.source.read_bytes()
        self.assertEqual(self.convert(output=self.source)[0], 2)
        self.assertEqual(self.source.read_bytes(), before)

    def test_missing_output_parent_is_not_created(self):
        destination = self.fixture / "fictional-missing" / "never.lock"
        self.assertEqual(self.convert(output=destination)[0], 2)
        self.assertFalse(destination.parent.exists())

    def test_invalid_output_data_is_rejected_before_creation(self):
        for value in (b"", "fictional", b"x" * (common.MAX_LOCK_BYTES + 1)):
            with self.assertRaises(common.LockError):
                common.write_new(self.output, value)
            self.assertFalse(self.output.exists())

    def test_empty_oversized_and_directory_inputs_are_refused(self):
        for value in (b"", b"x" * (common.MAX_REPORT_BYTES + 1)):
            self.source.write_bytes(value)
            self.assertEqual(self.convert()[0], 2)
            self.assertFalse(self.output.exists())
        self.assertEqual(self.convert(source=self.folder)[0], 2)
        self.assertFalse(self.output.exists())

    def test_report_size_bound_precedes_decoder(self):
        self.source.write_bytes(b"x" * (common.MAX_REPORT_BYTES + 1))
        with patch.object(
            converter, "strict_json", side_effect=AssertionError("NO_DECODE")
        ):
            self.assertEqual(self.convert()[0], 2)
        self.assertFalse(self.output.exists())

    def test_invalid_report_creates_no_output(self):
        for value in (
            b"{",
            b"\xff",
            b'{"version":"1","version":"1"}',
            b'{"sample":NaN}',
            json.dumps(report(item(version="unsupported"))).encode(),
        ):
            self.source.write_bytes(value)
            self.assertEqual(self.convert()[0], 2)
            self.assertFalse(self.output.exists())

    def test_report_metadata_is_omitted_without_runtime_or_network_actions(self):
        record = item()
        record["metadata"]["summary"] = "fictional-private-canary"
        record["download_info"]["url"] = "fictional-private-canary"
        self.source.write_text(json.dumps(report(record)), encoding="utf-8")
        with (
            patch.object(socket, "socket", side_effect=AssertionError("NO_SOCKET")),
            patch.object(subprocess, "Popen", side_effect=AssertionError("NO_PROCESS")),
            patch.object(os, "system", side_effect=AssertionError("NO_COMMAND")),
            patch.object(os, "scandir", side_effect=AssertionError("NO_SCAN")),
        ):
            self.assertEqual(self.convert()[0], 0)
            self.assertEqual(verifier.verify([self.output]), 1)
        self.assertNotIn(b"fictional-private-canary", self.output.read_bytes())

    def test_multiple_locks_keep_combined_byte_and_count_bounds(self):
        self.output.write_bytes(lock())
        self.assertEqual(verifier.verify([self.output, self.output]), 2)
        with patch.object(verifier, "MAX_TOTAL_LOCK_BYTES", len(lock()) * 2 - 1):
            self.assertEqual(
                self.invoke(verifier.main, [str(self.output), str(self.output)])[0], 2
            )

    def test_held_read_handles_refuse_writers_delete_and_parent_rename(self):
        native = win.Native(CORE)
        with win.Chain(native, self.folder) as chain:
            with chain.regular(self.source.name) as fd:
                self.assertFalse(os.get_inheritable(fd))
                for action in (
                    lambda: self.source.open("r+b"),
                    self.source.unlink,
                    lambda: self.folder.rename(self.fixture / "fictional-renamed"),
                ):
                    with self.assertRaises(PermissionError):
                        action()
        self.assertTrue(self.source.is_file())

    def test_existing_data_writer_causes_fixed_rejection(self):
        with self.source.open("r+b"):
            self.assertEqual(self.convert()[0], 2)
        self.assertFalse(self.output.exists())

    def test_ambiguous_control_paths_are_refused_before_native_open(self):
        for value in (
            "../fictional",
            "//fictional-host/share",
            "C:fictional",
            "nul",
            "fictional. ",
            "fictional:stream",
            "fictional.",
            "fictional ",
        ):
            with patch.object(
                win.Native, "open", side_effect=AssertionError("NO_OPEN")
            ):
                self.assertEqual(self.convert(source=value)[0], 2)
            with patch.object(
                win.Native, "create", side_effect=AssertionError("NO_CREATE")
            ):
                self.assertEqual(self.convert(output=value)[0], 2)

    def test_drive_root_is_not_a_regular_input_or_new_output(self):
        root = Path(self.source.anchor)
        self.assertEqual(self.convert(source=root)[0], 2)
        self.assertEqual(self.convert(output=root)[0], 2)

    def test_hardlinked_input_is_refused_and_existing_output_is_preserved(self):
        second = self.fixture / "fictional-second-report.json"
        try:
            os.link(self.source, second)
        except OSError:
            self.unavailable_link("Native hardlink creation unavailable")
        self.assertEqual(self.convert()[0], 2)
        self.assertFalse(self.output.exists())
        second.unlink()
        target = self.fixture / "fictional-output-target.lock"
        target.write_bytes(b"Fictional existing hardlink\n")
        os.link(target, self.output)
        self.assertEqual(self.convert()[0], 2)
        self.assertEqual(target.read_bytes(), b"Fictional existing hardlink\n")
        self.assertEqual(self.output.read_bytes(), target.read_bytes())

    def test_symlink_inputs_and_output_leaf_or_parent_are_refused(self):
        link = self.fixture / "fictional-input-link.json"
        parent = self.fixture / "fictional-parent-link"
        try:
            link.symlink_to(self.source)
            parent.symlink_to(self.folder, target_is_directory=True)
        except OSError:
            self.unavailable_link("Native symlink privilege unavailable")
        self.assertEqual(self.convert(source=link)[0], 2)
        self.assertEqual(self.convert(source=parent / self.source.name)[0], 2)
        self.assertEqual(self.convert(output=parent / self.output.name)[0], 2)
        self.output.symlink_to(self.source)
        before = self.source.read_bytes()
        self.assertEqual(self.convert()[0], 2)
        self.assertTrue(self.output.is_symlink())
        self.assertEqual(self.source.read_bytes(), before)

    def test_junction_input_and_output_parents_are_refused(self):
        link = self.fixture / "fictional-junction"
        done = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(self.folder)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if done.returncode:
            self.unavailable_link("Native junction creation unavailable")
        self.assertEqual(self.convert(source=link / self.source.name)[0], 2)
        self.assertEqual(self.convert(output=link / self.output.name)[0], 2)
        self.assertFalse(self.output.exists())

    def short_path(self, path):
        function = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
        function.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD]
        function.restype = w.DWORD
        output = ctypes.create_unicode_buffer(32768)
        size = function(str(path), output, len(output))
        if (
            not size
            or size >= len(output)
            or output.value.casefold() == str(path).casefold()
        ):
            self.skipTest("Native alternate short spelling unavailable")
        return Path(output.value)

    def test_short_input_and_output_parent_aliases_are_refused(self):
        self.assertEqual(self.convert(source=self.short_path(self.source))[0], 2)
        parent = self.short_path(self.folder)
        self.assertEqual(self.convert(output=parent / self.output.name)[0], 2)
        self.assertFalse(self.output.exists())

    def test_short_existing_output_alias_is_never_replaced(self):
        self.output.write_bytes(b"Fictional existing alias\n")
        alias = self.short_path(self.output)
        self.assertEqual(self.convert(output=alias)[0], 2)
        self.assertEqual(self.output.read_bytes(), b"Fictional existing alias\n")

    def test_write_failure_keeps_only_new_partial_file(self):
        original = win.Native.write

        def interrupted(native, handle, data):
            original(native, handle, data[:11])
            raise common.LockError("FICTIONAL_WRITE_FAILURE")

        before = self.source.read_bytes()
        with patch.object(win.Native, "write", new=interrupted):
            self.assertEqual(self.convert()[0], 2)
        self.assertEqual(
            self.output.read_bytes(),
            converter.render_lock(converter.records_from_report(report()))[:11],
        )
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.convert()[0], 2)

    def test_flush_failure_keeps_new_file_without_replacing_another(self):
        with patch.object(
            win.Native, "flush", side_effect=common.LockError("FICTIONAL_FLUSH_FAILURE")
        ):
            self.assertEqual(self.convert()[0], 2)
        self.assertEqual(
            self.output.read_bytes(),
            converter.render_lock(converter.records_from_report(report())),
        )
        self.assertEqual(self.convert()[0], 2)

    def test_new_output_handle_refuses_reader_writer_and_delete(self):
        original = win.Native.write

        def checked(native, handle, data):
            for action in (
                lambda: self.output.open("rb"),
                lambda: self.output.open("r+b"),
                self.output.unlink,
            ):
                with self.assertRaises(PermissionError):
                    action()
            original(native, handle, data)

        with patch.object(win.Native, "write", new=checked):
            self.assertEqual(self.convert()[0], 0)

    def test_output_byte_limit_is_written_exactly_across_native_chunks(self):
        data = bytes(range(256)) * (common.MAX_LOCK_BYTES // 256)
        self.assertEqual(len(data), common.MAX_LOCK_BYTES)
        common.write_new(self.output, data)
        self.assertEqual(self.output.read_bytes(), data)
        with self.assertRaises(common.LockError):
            common.write_new(self.output, b"Fictional replacement")
        self.assertEqual(self.output.read_bytes(), data)

    def test_changed_output_identity_keeps_the_unconfirmed_new_file(self):
        original = win.Native.describe
        observed = 0

        def sampled(native, handle, directory):
            nonlocal observed
            identity, name = original(native, handle, directory)
            if not directory and name.casefold().endswith(
                "\\" + self.output.name.casefold()
            ):
                observed += 1
                if observed > 1:
                    identity = (identity[0], identity[1] + 1, *identity[2:])
            return identity, name

        with patch.object(win.Native, "describe", new=sampled):
            self.assertEqual(self.convert()[0], 2)
        self.assertGreaterEqual(observed, 2)
        self.assertEqual(
            self.output.read_bytes(),
            converter.render_lock(converter.records_from_report(report())),
        )

    def test_postcreation_name_failure_keeps_an_unconfirmed_new_file(self):
        original = win.Native.create

        def mismatched(native, path, expected=None):
            return original(native, path, "fictional-unexpected-native-name")

        with patch.object(win.Native, "create", new=mismatched):
            self.assertEqual(self.convert()[0], 2)
        self.assertTrue(self.output.is_file())
        self.assertEqual(self.output.read_bytes(), b"")
        self.assertEqual(self.convert()[0], 2)

    def test_descriptor_transfer_failure_closes_owned_native_handle(self):
        import msvcrt

        before = self.source.read_bytes()
        with patch.object(
            msvcrt, "open_osfhandle", side_effect=OSError("fictional-native-transfer")
        ):
            self.assertEqual(self.convert()[0], 2)
        self.assertFalse(self.output.exists())
        with self.source.open("r+b"):
            pass
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.convert()[0], 0)

    def test_close_error_still_attempts_every_retained_parent_handle(self):
        original = win.Native.close
        closed = []

        def close(native, handle):
            original(native, handle)
            closed.append(handle)
            raise common.LockError("FICTIONAL_CLOSE_FAILURE")

        native = win.Native(CORE)
        with self.assertRaises(common.LockError):
            with win.Chain(native, self.folder) as chain:
                expected = len(chain.items)
                with patch.object(win.Native, "close", new=close):
                    chain.__exit__(None, None, None)
        self.assertEqual(len(closed), expected)
        self.assertEqual(len(set(closed)), expected)
        self.assertEqual(self.convert()[0], 0)

    def test_changed_native_file_identity_is_rejected(self):
        original = win.Native.describe
        seen = set()

        def sampled(native, handle, directory):
            identity, name = original(native, handle, directory)
            key = (handle, name)
            if not directory and key in seen:
                return (*identity[:-1], identity[-1] + 1), name
            seen.add(key)
            return identity, name

        with patch.object(win.Native, "describe", new=sampled):
            self.assertEqual(self.convert()[0], 2)
        self.assertFalse(self.output.exists())

    def test_normalized_name_mismatch_is_rejected(self):
        native = win.Native(CORE)
        with self.assertRaises(common.LockError):
            native.open(self.folder, True, "fictional-mismatched-final-name")

    def test_repeated_success_and_rejection_do_not_grow_native_handles(self):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.argtypes = []
        kernel.GetCurrentProcess.restype = w.HANDLE
        kernel.GetProcessHandleCount.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
        kernel.GetProcessHandleCount.restype = w.BOOL

        def count():
            value = w.DWORD()
            self.assertTrue(
                kernel.GetProcessHandleCount(
                    kernel.GetCurrentProcess(), ctypes.byref(value)
                )
            )
            return value.value

        self.assertEqual(self.convert()[0], 0)
        before = count()
        for index in range(20):
            output = self.folder / f"fictional-{index}.lock"
            self.assertEqual(self.convert(output=output)[0], 0)
            self.assertEqual(self.convert(output=output)[0], 2)
            self.assertEqual(
                self.convert(
                    source=self.fixture / "fictional-missing.json", output=output
                )[0],
                2,
            )
        self.assertEqual(count(), before)

    def test_interruptions_return_fixed_json_without_input_values(self):
        with patch.object(converter, "read_bounded", side_effect=KeyboardInterrupt):
            code, result, _ = self.convert()
        self.assertNotEqual(code, 0)
        self.assertEqual(result, {"result": "ERROR", "code": "INTERRUPTED"})
        with patch.object(verifier, "read_bounded", side_effect=KeyboardInterrupt):
            code, result, _ = self.invoke(verifier.main, [str(self.output)])
        self.assertNotEqual(code, 0)
        self.assertEqual(result, {"result": "ERROR", "code": "INTERRUPTED"})


if __name__ == "__main__":
    unittest.main()
