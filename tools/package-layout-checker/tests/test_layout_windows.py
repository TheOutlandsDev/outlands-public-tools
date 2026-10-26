"""Fictional Windows native fixtures and portable manifest-contract checks."""

import contextlib
import ctypes
from ctypes import wintypes as w
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load("layout_native_test_core", "layout_check.py")
win = load("layout_native_test_backend", "layout_windows.py")


class PortableContractTests(unittest.TestCase):
    def test_windows_component_rejections_do_not_change_common_manifest_parser(self):
        for name in (
            "CON",
            "nul.txt",
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
        for name in ("README.md", "src", "fictional name.py", "échantillon.txt"):
            self.assertTrue(win._component(name), name)
        for name in ("nul.txt", "file.", "file "):
            self.assertEqual(
                core.validate_manifest(
                    {"schema_version": 1, "files": [{"path": name}]}
                ),
                [{"path": name}],
            )

    def test_shared_manifest_fields_and_types_are_exact(self):
        for value in (
            {},
            [],
            {"schema_version": True, "files": []},
            {"schema_version": 1, "files": []},
            {"schema_version": 1, "files": [{"path": "sample.py", "unknown": True}]},
        ):
            with self.assertRaises(core.Rejected):
                core.validate_manifest(value)
        with self.assertRaises(core.Rejected):
            core.validate_manifest(
                {
                    "schema_version": 1,
                    "files": [{"path": "Sample.py"}, {"path": "sample.py"}],
                }
            )

    def test_windows_backend_is_fixed_unsupported_outside_windows(self):
        if os.name == "nt":
            self.skipTest("Only an unsupported-platform check on POSIX")
        with self.assertRaises(core.Rejected) as caught:
            win.Native(vars(core))
        self.assertEqual(str(caught.exception), "WINDOWS_API_UNAVAILABLE")


@unittest.skipUnless(os.name == "nt", "Native Windows fixture")
class NativeWindowsTests(unittest.TestCase):
    def setUp(self):
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
        self.root = self.fixture / "fictional-package-long"
        self.root.mkdir()
        (self.root / "src").mkdir()
        (self.root / "README.md").write_bytes(b"Fictional sample package\n")
        (self.root / "src/demo.py").write_bytes(b"def add(a,b):\n    return a+b\n")
        self.manifest = self.fixture / "fictional-manifest-long.json"
        self.entries = [
            {"path": "README.md"},
            {
                "path": "src/demo.py",
                "python_syntax": True,
                "forbidden_literals": ["FICTIONAL_DO_NOT_SHIP"],
            },
        ]
        self.write_manifest()

    def write_manifest(self, entries=None):
        self.manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "files": self.entries if entries is None else entries,
                }
            ),
            encoding="utf-8",
        )

    def unavailable_link(self, message):
        if os.environ.get("OUTLANDS_LAYOUT_REQUIRE_NATIVE_LINKS") == "1":
            self.fail(message)
        self.skipTest(message)

    def invoke(self, root=None, manifest=None):
        output, errors = io.StringIO(), io.StringIO()
        with (
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
            patch.object(
                core,
                "windows_report",
                side_effect=lambda a, b: win.check_windows(a, b, vars(core)),
            ),
        ):
            code = core.main(
                [
                    "--root",
                    str(root or self.root),
                    "--manifest",
                    str(manifest or self.manifest),
                ]
            )
        self.assertNotIn(str(self.fixture), output.getvalue() + errors.getvalue())
        self.assertEqual(errors.getvalue(), "")
        return code, json.loads(output.getvalue()), output.getvalue()

    def test_fictional_layout_report_shape_and_input_bytes_preserved(self):
        files = [self.root / "README.md", self.root / "src/demo.py", self.manifest]
        before = {p: p.read_bytes() for p in files}
        code, result, _ = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(
            set(result),
            {"schema_version", "status", "checked_files", "failed_files", "results"},
        )
        self.assertEqual(result["checked_files"], 2)
        self.assertEqual(before, {p: p.read_bytes() for p in files})

    def test_native_cli_loader_in_a_fresh_process(self):
        done = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HERE / "layout_check.py"),
                "--root",
                str(self.root),
                "--manifest",
                str(self.manifest),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["status"], "PASS")
        self.assertEqual(done.stderr, "")

    def test_missing_file_is_a_row_finding(self):
        (self.root / "README.md").unlink()
        code, result, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result["results"][0]["codes"], ["MISSING"])

    def test_missing_root_or_manifest_is_rejected(self):
        self.assertEqual(self.invoke(root=self.fixture / "missing-root")[0], 2)
        self.assertEqual(
            self.invoke(manifest=self.fixture / "missing-manifest.json")[0], 2
        )

    def test_syntax_and_marker_findings_omit_source_and_literal(self):
        (self.root / "src/demo.py").write_bytes(b"def FICTIONAL_DO_NOT_SHIP(\n")
        code, result, text = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(
            result["results"][1]["codes"], ["PYTHON_SYNTAX", "FORBIDDEN_LITERAL"]
        )
        self.assertNotIn("FICTIONAL_DO_NOT_SHIP", text)

    def test_casefolded_markers_and_bom_source_are_checked(self):
        (self.root / "src/demo.py").write_bytes(
            b"\xef\xbb\xbf# fictional_do_not_ship\n"
        )
        code, result, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result["results"][1]["codes"], ["FORBIDDEN_LITERAL"])

    def test_selected_source_is_not_imported_or_executed(self):
        (self.root / "src/demo.py").write_bytes(
            b'raise RuntimeError("Fictional code must not execute")\n'
        )
        with patch.object(
            subprocess, "Popen", side_effect=AssertionError("NO_PROCESS")
        ):
            self.assertEqual(self.invoke()[0], 0)

    def test_presence_only_does_not_read_or_decode_body(self):
        self.write_manifest([{"path": "README.md"}])
        (self.root / "README.md").write_bytes(b"\xff\x00")
        original = core.read_bounded
        calls = []

        def track(fd, limit):
            calls.append(limit)
            return original(fd, limit)

        with patch.object(core, "read_bounded", side_effect=track):
            self.assertEqual(self.invoke()[0], 0)
        self.assertEqual(calls, [core.MAX_MANIFEST_BYTES])

    def test_invalid_source_text_fails_without_echo(self):
        (self.root / "src/demo.py").write_bytes(b"\xff")
        code, result, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("TEXT_INVALID", result["results"][1]["codes"])

    def test_duplicate_nonfinite_unknown_and_bom_manifests_fail(self):
        values = [
            b'{"schema_version":1,"schema_version":1}',
            b'{"x":NaN}',
            b"{",
            b"\xff",
            b"\xef\xbb\xbf" + self.manifest.read_bytes(),
        ]
        for value in values:
            self.manifest.write_bytes(value)
            self.assertEqual(self.invoke()[0], 2)
        self.write_manifest(
            [{"path": "README.md", "private_schema": "fictional-canary"}]
        )
        self.assertEqual(self.invoke()[0], 2)

    def test_manifest_and_per_file_byte_bounds(self):
        self.manifest.write_bytes(b" " * (core.MAX_MANIFEST_BYTES + 1))
        self.assertEqual(self.invoke()[0], 2)
        self.write_manifest()
        (self.root / "README.md").write_bytes(b"x" * (core.MAX_FILE_BYTES + 1))
        code, result, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result["results"][0]["codes"], ["BYTE_LIMIT"])

    def test_total_read_budget_reservation_is_preserved(self):
        entries = []
        for index in range(9):
            name = f"sample-{index}.py"
            (self.root / name).write_bytes(b" " * core.MAX_FILE_BYTES)
            entries.append({"path": name, "python_syntax": True})
        self.write_manifest(entries)
        code, result, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result["results"][-1]["codes"], ["TOTAL_BYTE_LIMIT"])

    def test_unlisted_files_are_not_enumerated_or_read(self):
        (self.root / "unlisted.py").write_bytes(b"fictional-invalid @@")
        with patch.object(os, "scandir", side_effect=AssertionError("NO_SCAN")):
            code, result, text = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(result["checked_files"], 2)
        self.assertNotIn("unlisted.py", text)

    def test_manifest_traversal_ads_and_case_collisions_are_rejected(self):
        for path in (
            "../sample.py",
            "src//demo.py",
            "src/./demo.py",
            "src\\demo.py",
            "README.md:stream",
        ):
            self.write_manifest([{"path": path}])
            self.assertEqual(self.invoke()[0], 2)
        self.write_manifest([{"path": "README.md"}, {"path": "readme.md"}])
        self.assertEqual(self.invoke()[0], 2)

    def test_windows_reserved_and_trailing_names_refused_before_open(self):
        for path in (
            "nul.txt",
            "COM1.json",
            "LPT" + chr(0xB9),
            "README.md.",
            "README.md ",
        ):
            self.write_manifest([{"path": path}])
            code, result, _ = self.invoke()
            self.assertEqual(code, 1)
            self.assertEqual(result["results"][0]["codes"], ["UNSAFE_PATH"])

    def test_control_path_alias_forms_refused_before_native_open(self):
        for value in (
            "../fictional",
            "//fictional-host/share",
            "C:fictional",
            "nul",
            "fictional. ",
            "fictional:stream",
        ):
            with patch.object(
                win.Native, "open", side_effect=AssertionError("NO_OPEN")
            ):
                self.assertEqual(self.invoke(root=value)[0], 2)

    def test_drive_root_and_manifest_root_are_rejected(self):
        self.assertEqual(self.invoke(root=Path(self.root.anchor))[0], 2)
        self.assertEqual(self.invoke(manifest=Path(self.root.anchor))[0], 2)

    def test_declared_directory_is_not_a_regular_file(self):
        (self.root / "README.md").unlink()
        (self.root / "README.md").mkdir()
        code, result, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result["results"][0]["codes"], ["UNSAFE_FILE"])

    def test_hardlinked_selected_file_and_manifest_are_refused(self):
        try:
            os.link(self.root / "README.md", self.fixture / "fictional-second.md")
        except OSError:
            self.unavailable_link("Native hardlink creation unavailable")
        self.assertEqual(self.invoke()[0], 1)
        os.link(self.manifest, self.fixture / "fictional-second.json")
        self.assertEqual(self.invoke()[0], 2)

    def test_symlink_root_manifest_selected_and_intermediate_are_refused(self):
        root_link = self.fixture / "fictional-root-link"
        manifest_link = self.fixture / "fictional-manifest-link.json"
        try:
            root_link.symlink_to(self.root, target_is_directory=True)
            manifest_link.symlink_to(self.manifest)
        except OSError:
            self.unavailable_link("Native symlink privilege unavailable")
        self.assertEqual(self.invoke(root=root_link)[0], 2)
        self.assertEqual(self.invoke(manifest=manifest_link)[0], 2)
        outside = self.fixture / "fictional-outside.md"
        outside.write_bytes(b"Fictional outside\n")
        (self.root / "README.md").unlink()
        (self.root / "README.md").symlink_to(outside)
        self.assertEqual(self.invoke()[0], 1)
        (self.root / "src/demo.py").unlink()
        (self.root / "src").rmdir()
        folder = self.fixture / "fictional-external-src"
        folder.mkdir()
        (folder / "demo.py").write_bytes(b"pass\n")
        (self.root / "src").symlink_to(folder, target_is_directory=True)
        self.assertEqual(self.invoke()[0], 1)

    def junction(self, link, target):
        done = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if done.returncode:
            self.unavailable_link("Native junction creation unavailable")

    def test_junction_root_and_intermediate_are_refused(self):
        link = self.fixture / "fictional-junction"
        self.junction(link, self.root)
        self.assertEqual(self.invoke(root=link)[0], 2)
        (self.root / "src/demo.py").unlink()
        (self.root / "src").rmdir()
        target = self.fixture / "fictional-junction-target"
        target.mkdir()
        (target / "demo.py").write_bytes(b"pass\n")
        self.junction(self.root / "src", target)
        code, result, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("UNSAFE_PATH", result["results"][1]["codes"])

    def test_held_handles_deny_data_writer_delete_and_parent_rename(self):
        native = win.Native(vars(core))
        path = self.root / "src/demo.py"
        with win.Chain(native, self.root) as chain:
            with chain.regular("src/demo.py") as fd:
                self.assertFalse(os.get_inheritable(fd))
                with self.assertRaises(PermissionError):
                    with path.open("r+b"):
                        pass
                with self.assertRaises(PermissionError):
                    path.unlink()
                with self.assertRaises(PermissionError):
                    (self.root / "src").rename(self.root / "renamed-src")
        before = path.read_bytes()
        with path.open("r+b"):
            pass
        self.assertEqual(path.read_bytes(), before)

    def test_existing_data_writer_causes_a_fixed_finding(self):
        path = self.root / "README.md"
        with path.open("r+b"):
            code, result, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result["results"][0]["codes"], ["READ_ERROR"])

    def test_normalized_parent_and_file_identity_mismatch_fails(self):
        native = win.Native(vars(core))
        with self.assertRaises(core.EntryFailure):
            native.open(self.root, True, "fictional-mismatched-final-name")
        original = win.Native.describe

        # Make the second observation of each file differ while preserving native calls.
        seen = set()

        def sampled(native, handle, directory):
            identity, name = original(native, handle, directory)
            key = (handle, name)
            if not directory and key in seen:
                return (*identity[:-1], identity[-1] + 1), name
            seen.add(key)
            return identity, name

        with patch.object(win.Native, "describe", new=sampled):
            self.assertEqual(
                self.invoke()[0], 2
            )  # manifest changed during its guarded read

    def short_path(self, path):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        function = kernel.GetShortPathNameW
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

    def test_short_path_root_and_manifest_aliases_are_refused(self):
        self.assertEqual(self.invoke(root=self.short_path(self.root))[0], 2)
        self.assertEqual(self.invoke(manifest=self.short_path(self.manifest))[0], 2)

    def test_short_declared_filename_alias_is_refused(self):
        path = self.root / "fictional-long-file-name.txt"
        path.write_bytes(b"Fictional only\n")
        alias = self.short_path(path).name
        if alias.casefold() == path.name.casefold():
            self.skipTest("Native alternate file spelling unavailable")
        self.write_manifest([{"path": alias}])
        code, result, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result["results"][0]["codes"], ["UNSAFE_PATH"])

    def test_no_handle_growth_after_repeated_success_and_failure(self):
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

        self.invoke()
        before = count()
        for index in range(20):
            self.invoke()
            self.invoke(manifest=self.fixture / "fictional-missing.json")
        self.assertEqual(count(), before)

    def test_rejected_arguments_and_interrupt_omit_values(self):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(core.main(["--unknown", "fictional-private-canary"]), 2)
        self.assertNotIn(
            "fictional-private-canary", output.getvalue() + errors.getvalue()
        )
        with (
            patch.object(core, "windows_report", side_effect=KeyboardInterrupt),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(
                core.main(["--root", str(self.root), "--manifest", str(self.manifest)]),
                130,
            )


if __name__ == "__main__":
    unittest.main()
