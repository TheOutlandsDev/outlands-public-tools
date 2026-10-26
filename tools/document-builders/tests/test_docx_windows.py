"""Fictional DOCX package contracts and native Windows file fixtures."""

import contextlib
import ctypes
from ctypes import wintypes as w
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
import zipfile

import markdown_docx as tool
import docx_windows as win


HERE = Path(__file__).resolve().parents[1]
CORE = {"Rejected": tool.BuildError, "EntryFailure": tool.BuildError}
MARKDOWN = """# Fictional heading
Fictional paragraph.
- Fictional bullet
1. Fictional numbered item
## Fictional subheading
| Item | Quantity |
| --- | --- |
| DEMO-A | 2 |
| DEMO-B | 3 |
"""
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dcterms": "http://purl.org/dc/terms/",
}


def package(data):
    return zipfile.ZipFile(io.BytesIO(data))


class PortableContractTests(unittest.TestCase):
    def test_heading_list_table_and_layout_xml_are_preserved(self):
        with package(tool.make_document(MARKDOWN, "Fictional title")) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
            styles = [node.get(W + "val") for node in root.iter(W + "pStyle")]
            self.assertIn("Heading1", styles)
            self.assertIn("Heading2", styles)
            self.assertIn("ListBullet", styles)
            self.assertIn("ListNumber", styles)
            self.assertEqual(len(list(root.iter(W + "tbl"))), 1)
            self.assertEqual(len(list(root.iter(W + "tr"))), 3)
            self.assertEqual(len(list(root.iter(W + "tc"))), 6)
            self.assertEqual(len(list(root.iter(W + "tblHeader"))), 1)
            margins = next(root.iter(W + "pgMar"))
            for side in ("top", "bottom", "left", "right"):
                self.assertEqual(margins.get(W + side), "864")
            self.assertIn(b"DEMO-A", archive.read("word/document.xml"))

    def test_neutral_core_properties_are_complete(self):
        with package(tool.make_document(MARKDOWN, "Fictional title")) as archive:
            core = ET.fromstring(archive.read("docProps/core.xml"))
            expected = {
                "dc:title": "Fictional title",
                "dc:subject": "Local Markdown document",
                "dc:creator": "OUTLANDS",
                "cp:lastModifiedBy": "OUTLANDS",
                "dcterms:created": "2000-01-01T00:00:00Z",
                "dcterms:modified": "2000-01-01T00:00:00Z",
                "cp:revision": "1",
                "dc:language": "en",
            }
            for name, value in expected.items():
                self.assertEqual(core.findtext(name, namespaces=NS), value)
            for name in (
                "dc:description",
                "cp:keywords",
                "cp:category",
                "dc:identifier",
            ):
                self.assertFalse(core.findtext(name, namespaces=NS))

    def test_literal_markup_creates_no_remote_relationships_or_media(self):
        markdown = (
            "# Fictional links\n![demo](https://example.invalid/image.png)\n"
            "[demo](https://example.invalid/)\n<script>fictional()</script>\n"
        )
        with (
            patch.object(socket, "socket", side_effect=AssertionError("NO_NETWORK")),
            patch.object(subprocess, "Popen", side_effect=AssertionError("NO_PROCESS")),
            package(tool.make_document(markdown, "Fictional title")) as archive,
        ):
            names = archive.namelist()
            self.assertFalse(any(name.startswith("word/media/") for name in names))
            self.assertFalse(
                any("vbaProject" in name or "embeddings/" in name for name in names)
            )
            for name in names:
                if name.endswith(".rels"):
                    root = ET.fromstring(archive.read(name))
                    self.assertFalse(
                        any(node.get("TargetMode") == "External" for node in root)
                    )
            self.assertIn(
                b"https://example.invalid/", archive.read("word/document.xml")
            )
            self.assertIn(
                b"&lt;script&gt;fictional()&lt;/script&gt;",
                archive.read("word/document.xml"),
            )

    def test_default_template_parts_are_retained_without_anonymity_claim(self):
        with package(
            tool.make_document("Fictional text", "Fictional title")
        ) as archive:
            names = archive.namelist()
            self.assertIn("docProps/app.xml", names)
            self.assertTrue(any(name.startswith("customXml/") for name in names))
            self.assertTrue(
                any(name.startswith("docProps/thumbnail") for name in names)
            )
            for name in names:
                if name.endswith((".xml", ".rels")):
                    ET.fromstring(archive.read(name))
            self.assertTrue(
                all(info.date_time[0] >= 1980 for info in archive.infolist())
            )

    def test_empty_and_bom_markdown_still_produce_valid_packages(self):
        for markdown in (
            "",
            "\ufeff# Fictional text\n",
            "Échantillon fictional Unicode",
        ):
            with package(tool.make_document(markdown, "Fictional title")) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn("word/document.xml", archive.namelist())

    def test_table_validation_remains_strict(self):
        for markdown in (
            "| A | B |\n| --- | --- |\n| one |\n",
            "|" + " A |" * 17 + "\n|" + " --- |" * 17 + "\n",
            "| A | B |\n| --- | --- |\n" + "| one | two |\n" * 1001,
        ):
            with self.assertRaises(tool.BuildError):
                tool.make_document(markdown, "Fictional title")

    def test_short_native_writes_retry_all_bytes(self):
        native = object.__new__(win.Native)
        native.core = CORE
        observed = bytearray()

        def write(_handle, buffer, length, written, _overlapped):
            size = min(13, length)
            observed.extend(buffer.raw[:size])
            written._obj.value = size
            return 1

        native.dll = SimpleNamespace(WriteFile=write)
        data = bytes(range(256)) * 300
        native.write(None, data)
        self.assertEqual(bytes(observed), data)

    def test_zero_invalid_failed_native_writes_and_flush_are_fixed_errors(self):
        native = object.__new__(win.Native)
        native.core = CORE
        for reported, succeeded in ((0, 1), (999, 1), (1, 0)):

            def write(_handle, _buffer, _length, written, _overlapped):
                written._obj.value = reported
                return succeeded

            native.dll = SimpleNamespace(WriteFile=write)
            with self.assertRaises(tool.BuildError):
                native.write(None, b"Fictional bytes")
        native.dll = SimpleNamespace(FlushFileBuffers=lambda _handle: 0)
        with self.assertRaises(tool.BuildError):
            native.flush(None)

    def test_windows_components_refuse_ambiguous_names(self):
        for name in (
            "nul.docx",
            "CON",
            "COM1.md",
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
        for name in ("fictional.md", "fictional.docx", "fictional folder"):
            self.assertTrue(win._component(name), name)

    def test_windows_api_refuses_unsupported_platform(self):
        if os.name == "nt":
            self.skipTest("Unsupported-platform probe runs on POSIX")
        with self.assertRaises(tool.BuildError):
            win.Native(CORE)


@unittest.skipUnless(os.name == "nt", "Native Windows fixture")
class NativeWindowsTests(unittest.TestCase):
    def setUp(self):
        loader = patch.object(tool, "windows_backend", return_value=win)
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
        self.source = self.folder / "fictional-input-long.md"
        self.source.write_text(MARKDOWN, encoding="utf-8")
        self.output = self.folder / "fictional-output-long.docx"

    def unavailable_link(self, message):
        if os.environ.get("OUTLANDS_DOCX_REQUIRE_NATIVE_LINKS") == "1":
            self.fail(message)
        self.skipTest(message)

    def invoke(self, source=None, output=None, title="Fictional title"):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = tool.main(
                [
                    "--input",
                    str(source or self.source),
                    "--output",
                    str(output or self.output),
                    "--title",
                    title,
                ]
            )
        self.assertNotIn(str(self.fixture), out.getvalue() + err.getvalue())
        if code:
            self.assertEqual(out.getvalue(), "")
            self.assertTrue(err.getvalue().startswith("DOCUMENT_BUILD_FAILED:"))
        else:
            self.assertEqual(err.getvalue(), "")
        return code, out.getvalue(), err.getvalue()

    def test_native_output_package_content_metadata_and_source_preservation(self):
        before = self.source.read_bytes()
        self.assertEqual(self.invoke()[0], 0)
        with zipfile.ZipFile(self.output) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn(b"DEMO-A", archive.read("word/document.xml"))
            self.assertIn(b"OUTLANDS", archive.read("docProps/core.xml"))
            for name in archive.namelist():
                if name.endswith((".xml", ".rels")):
                    self.assertNotIn(str(self.fixture).encode(), archive.read(name))
        self.assertEqual(self.source.read_bytes(), before)

    def test_fresh_process_cli_builds_fictional_document(self):
        done = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HERE / "markdown_docx.py"),
                "--input",
                str(self.source),
                "--output",
                str(self.output),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, "")
        self.assertNotIn(str(self.fixture), done.stdout)
        with zipfile.ZipFile(self.output) as archive:
            self.assertIn("word/document.xml", archive.namelist())

    def test_empty_markdown_remains_supported(self):
        self.source.write_bytes(b"")
        self.assertEqual(tool.read_markdown(self.source), "")
        self.assertEqual(self.invoke()[0], 0)
        with zipfile.ZipFile(self.output) as archive:
            self.assertIn(b"OUTLANDS", archive.read("docProps/core.xml"))

    def test_bom_and_unicode_markdown_remain_supported(self):
        self.source.write_bytes(b"\xef\xbb\xbf" + "# Fictional échantillon\n".encode())
        self.assertEqual(self.invoke()[0], 0)
        with zipfile.ZipFile(self.output) as archive:
            self.assertIn("échantillon".encode(), archive.read("word/document.xml"))

    def test_existing_file_directory_and_source_output_are_unchanged(self):
        self.output.write_bytes(b"Fictional existing document")
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(self.output.read_bytes(), b"Fictional existing document")
        self.output.unlink()
        self.output.mkdir()
        (self.output / "fictional-kept.txt").write_bytes(b"kept")
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual((self.output / "fictional-kept.txt").read_bytes(), b"kept")
        before = self.source.read_bytes()
        self.assertEqual(self.invoke(output=self.source)[0], 2)
        self.assertEqual(self.source.read_bytes(), before)

    def test_native_exclusive_decision_preserves_an_unexpected_new_file(self):
        original = win.Native.create

        def collision(native, path, expected=None):
            path.write_bytes(b"Fictional concurrent destination")
            return original(native, path, expected)

        with patch.object(win.Native, "create", new=collision):
            self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(self.output.read_bytes(), b"Fictional concurrent destination")

    def test_missing_output_parent_is_not_created(self):
        output = self.fixture / "fictional-missing" / "never.docx"
        self.assertEqual(self.invoke(output=output)[0], 2)
        self.assertFalse(output.parent.exists())

    def test_wrong_extension_is_refused_before_creation(self):
        output = self.folder / "fictional.txt"
        with patch.object(
            win.Native, "create", side_effect=AssertionError("NO_CREATE")
        ):
            self.assertEqual(self.invoke(output=output)[0], 2)
        self.assertFalse(output.exists())

    def test_input_byte_bound_precedes_document_builder(self):
        self.source.write_bytes(b"x" * (tool.MAX_INPUT_BYTES + 1))
        with patch.object(
            tool, "make_document", side_effect=AssertionError("NO_DOCUMENT")
        ):
            self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())

    def test_text_structure_encoding_and_control_failures_create_no_output(self):
        for data in (
            b"\xff",
            b"\x00",
            b"x" * (tool.MAX_LINE_CHARS + 1),
            b"\n" * (tool.MAX_LINES + 1),
        ):
            self.source.write_bytes(data)
            self.assertEqual(self.invoke()[0], 2)
            self.assertFalse(self.output.exists())

    def test_ragged_table_creates_no_output(self):
        self.source.write_text("| A | B |\n| --- | --- |\n| one |\n", encoding="utf-8")
        self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())

    def test_input_directory_and_missing_input_are_refused(self):
        self.assertEqual(self.invoke(source=self.folder)[0], 2)
        self.assertEqual(
            self.invoke(source=self.fixture / "fictional-missing.md")[0], 2
        )
        self.assertFalse(self.output.exists())

    def test_literal_markup_does_not_fetch_execute_or_enumerate(self):
        self.source.write_text(
            "# Fictional\n![demo](https://example.invalid/a.png)\n"
            "[demo](https://example.invalid/)\n<script>fictional()</script>\n",
            encoding="utf-8",
        )
        with (
            patch.object(socket, "socket", side_effect=AssertionError("NO_NETWORK")),
            patch.object(subprocess, "Popen", side_effect=AssertionError("NO_PROCESS")),
            patch.object(os, "system", side_effect=AssertionError("NO_COMMAND")),
            patch.object(os, "scandir", side_effect=AssertionError("NO_SCAN")),
        ):
            self.assertEqual(self.invoke()[0], 0)
        with zipfile.ZipFile(self.output) as archive:
            self.assertFalse(
                any(name.startswith("word/media/") for name in archive.namelist())
            )

    def test_raw_ambiguous_input_and_output_paths_are_refused(self):
        for value in (
            "../fictional",
            "//fictional-host/share",
            "C:fictional",
            "nul.md",
            "fictional:stream",
            "fictional.",
            "fictional ",
        ):
            with patch.object(
                win.Native, "open", side_effect=AssertionError("NO_OPEN")
            ):
                self.assertEqual(self.invoke(source=value)[0], 2)
            with patch.object(
                win.Native, "create", side_effect=AssertionError("NO_CREATE")
            ):
                self.assertEqual(self.invoke(output=value)[0], 2)

    def test_drive_root_is_not_a_regular_input_or_new_document(self):
        root = Path(self.source.anchor)
        self.assertEqual(self.invoke(source=root)[0], 2)
        self.assertEqual(self.invoke(output=root)[0], 2)

    def test_held_input_handles_deny_writers_delete_and_parent_rename(self):
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
            self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())

    def test_hardlinked_input_is_refused_and_existing_output_is_preserved(self):
        second = self.fixture / "fictional-second.md"
        try:
            os.link(self.source, second)
        except OSError:
            self.unavailable_link("Native hardlink creation unavailable")
        self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())
        second.unlink()
        target = self.fixture / "fictional-existing.docx"
        target.write_bytes(b"Fictional existing hardlink")
        os.link(target, self.output)
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(target.read_bytes(), b"Fictional existing hardlink")

    def test_symlink_input_output_leaf_and_parent_are_refused(self):
        link = self.fixture / "fictional-input-link.md"
        parent = self.fixture / "fictional-parent-link"
        try:
            link.symlink_to(self.source)
            parent.symlink_to(self.folder, target_is_directory=True)
        except OSError:
            self.unavailable_link("Native symlink privilege unavailable")
        self.assertEqual(self.invoke(source=link)[0], 2)
        self.assertEqual(self.invoke(source=parent / self.source.name)[0], 2)
        self.assertEqual(self.invoke(output=parent / self.output.name)[0], 2)
        self.output.symlink_to(self.source)
        before = self.source.read_bytes()
        self.assertEqual(self.invoke()[0], 2)
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
        self.assertEqual(self.invoke(source=link / self.source.name)[0], 2)
        self.assertEqual(self.invoke(output=link / self.output.name)[0], 2)
        self.assertFalse(self.output.exists())

    def short_path(self, path):
        function = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
        function.argtypes, function.restype = [w.LPCWSTR, w.LPWSTR, w.DWORD], w.DWORD
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
        self.assertEqual(self.invoke(source=self.short_path(self.source))[0], 2)
        self.assertEqual(
            self.invoke(output=self.short_path(self.folder) / self.output.name)[0], 2
        )
        self.assertFalse(self.output.exists())

    def test_short_existing_output_alias_is_not_replaced(self):
        self.output.write_bytes(b"Fictional existing alias")
        self.assertEqual(self.invoke(output=self.short_path(self.output))[0], 2)
        self.assertEqual(self.output.read_bytes(), b"Fictional existing alias")

    def test_partial_write_retains_new_unconfirmed_output(self):
        original = win.Native.write

        def interrupted(native, handle, data):
            original(native, handle, data[:11])
            raise tool.BuildError("FICTIONAL_WRITE_FAILURE")

        with patch.object(win.Native, "write", new=interrupted):
            self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(self.output.read_bytes()[:2], b"PK")
        self.assertEqual(self.output.stat().st_size, 11)
        self.assertEqual(self.invoke()[0], 2)

    def test_flush_failure_retains_new_unconfirmed_package(self):
        with patch.object(
            win.Native, "flush", side_effect=tool.BuildError("FICTIONAL_FLUSH_FAILURE")
        ):
            self.assertEqual(self.invoke()[0], 2)
        with zipfile.ZipFile(self.output) as archive:
            self.assertIsNone(archive.testzip())
        self.assertEqual(self.invoke()[0], 2)

    def test_output_handle_denies_read_write_delete_and_parent_rename(self):
        original = win.Native.write

        def checked(native, handle, data):
            for action in (
                lambda: self.output.open("rb"),
                lambda: self.output.open("r+b"),
                self.output.unlink,
                lambda: self.folder.rename(self.fixture / "fictional-renamed"),
            ):
                with self.assertRaises(PermissionError):
                    action()
            original(native, handle, data)

        with patch.object(win.Native, "write", new=checked):
            self.assertEqual(self.invoke()[0], 0)

    def test_native_writer_keeps_existing_no_additional_output_cap_contract(self):
        data = bytes(range(256)) * 4097
        tool.write_new_document(self.output, data)
        self.assertEqual(self.output.read_bytes(), data)

    def test_postcreation_name_failure_retains_empty_new_file(self):
        original = win.Native.create

        def mismatched(native, path, expected=None):
            return original(native, path, "fictional-unexpected-native-name")

        with patch.object(win.Native, "create", new=mismatched):
            self.assertEqual(self.invoke()[0], 2)
        self.assertTrue(self.output.is_file())
        self.assertEqual(self.output.read_bytes(), b"")

    def test_changed_output_identity_retains_unconfirmed_file(self):
        original = win.Native.describe
        seen = 0

        def sampled(native, handle, directory):
            nonlocal seen
            identity, name = original(native, handle, directory)
            if not directory and name.casefold().endswith(
                "\\" + self.output.name.casefold()
            ):
                seen += 1
                if seen > 1:
                    identity = (identity[0], identity[1] + 1, *identity[2:])
            return identity, name

        with patch.object(win.Native, "describe", new=sampled):
            self.assertEqual(self.invoke()[0], 2)
        self.assertGreaterEqual(seen, 2)
        self.assertTrue(self.output.is_file())

    def test_changed_input_identity_is_refused_before_output(self):
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
            self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())

    def test_descriptor_transfer_failure_closes_owned_input_handle(self):
        import msvcrt

        before = self.source.read_bytes()
        with patch.object(
            msvcrt, "open_osfhandle", side_effect=OSError("fictional-transfer")
        ):
            self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())
        with self.source.open("r+b"):
            pass
        self.assertEqual(self.source.read_bytes(), before)

    def test_close_failure_attempts_every_parent(self):
        original = win.Native.close
        closed = []

        def close(native, handle):
            original(native, handle)
            closed.append(handle)
            raise tool.BuildError("FICTIONAL_CLOSE_FAILURE")

        native = win.Native(CORE)
        with self.assertRaises(tool.BuildError):
            with win.Chain(native, self.folder) as chain:
                expected = len(chain.items)
                with patch.object(win.Native, "close", new=close):
                    chain.__exit__(None, None, None)
        self.assertEqual(len(closed), expected)
        self.assertEqual(len(set(closed)), expected)

    def test_output_close_failure_retains_file_and_closes_parents(self):
        original = win.Native.close
        calls = 0

        def close(native, handle):
            nonlocal calls
            original(native, handle)
            calls += 1
            raise tool.BuildError("FICTIONAL_CLOSE_FAILURE")

        with patch.object(win.Native, "close", new=close):
            with self.assertRaises(tool.BuildError):
                tool.write_new_document(self.output, b"Fictional bytes")
        self.assertGreater(calls, 1)
        self.assertEqual(self.output.read_bytes(), b"Fictional bytes")

    def test_repeated_success_and_refusal_do_not_grow_native_handles(self):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.argtypes, kernel.GetCurrentProcess.restype = (
            [],
            w.HANDLE,
        )
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

        tool.read_markdown(self.source)
        before = count()
        for index in range(20):
            destination = self.folder / f"fictional-{index}.docx"
            tool.write_new_document(destination, b"Fictional low-level bytes")
            self.assertEqual(self.invoke(output=destination)[0], 2)
            self.assertEqual(
                self.invoke(
                    source=self.fixture / "fictional-missing.md", output=destination
                )[0],
                2,
            )
        self.assertEqual(count(), before)

    def test_invalid_title_and_argument_values_are_redacted(self):
        for title in ("", "x" * 161, "fictional\x00title"):
            self.assertEqual(self.invoke(title=title)[0], 2)
            self.assertFalse(self.output.exists())
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(tool.main(["--unknown", "fictional-private-canary"]), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "DOCUMENT_BUILD_FAILED:ARGUMENTS_INVALID\n")

    def test_interruption_has_fixed_output_and_no_document(self):
        with patch.object(tool, "read_markdown", side_effect=KeyboardInterrupt):
            code, out, err = self.invoke()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "DOCUMENT_BUILD_FAILED:INTERRUPTED\n")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
