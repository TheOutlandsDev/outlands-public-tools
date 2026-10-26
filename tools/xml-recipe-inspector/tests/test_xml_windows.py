"""Fictional XML contracts and native Windows input/new-directory fixtures."""

import contextlib
import csv
import ctypes
from ctypes import wintypes as w
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import xml_recipe_inspector as tool
import xml_windows as win


HERE = Path(__file__).resolve().parents[1]
CORE = {"Rejected": tool.RecipeError, "EntryFailure": tool.RecipeError}


def fixture(identifier="fictional-measurement"):
    return f"""<Recipe><PixelSize><X>0.25</X></PixelSize>
    <Modules><Module><ID>fictional-module</ID><GeometryImages><GeometryImage>
    <ImageID>fictional-image</ImageID><Location>fixture-only</Location>
    <Origin><X>2</X><Y>3</Y></Origin><PixelSize><X>0.25</X><Y>0.5</Y></PixelSize>
    </GeometryImage></GeometryImages></Module></Modules>
    <Measurements><Measurement><ID>{identifier}</ID><Type>OVL_LN_LN</Type>
    <ImageID>fictional-image</ImageID><Orientation>X</Orientation>
    <NominalValue>0.5</NominalValue>
    <PointProperty><UserPoints><Point><X>1</X><Y>2</Y></Point>
    <Point><X>5</X><Y>2</Y></Point></UserPoints></PointProperty>
    <PointProperty><UserPoints><Point><X>3</X><Y>6</Y></Point>
    <Point><X>7</X><Y>6</Y></Point></UserPoints></PointProperty>
    </Measurement></Measurements></Recipe>""".encode()


class PortableContractTests(unittest.TestCase):
    def test_geometry_and_retained_single_x_calibration(self):
        pixel, modules, measurements, overlays = tool.inspect_xml(fixture())
        self.assertEqual(pixel, 0.25)
        self.assertEqual(modules[0]["origin_x"], 2)
        self.assertEqual(modules[0]["pixel_size_y_um"], 0.5)
        self.assertEqual(measurements[0]["point_properties"][0]["length_px"], 4)
        self.assertEqual(overlays[0]["delta_mid_x_px"], 2)
        self.assertEqual(overlays[0]["delta_mid_y_px"], 4)
        self.assertEqual(overlays[0]["delta_mid_x_um"], 0.5)
        self.assertEqual(overlays[0]["delta_mid_y_um"], 1)

    def test_utf16_and_ordinary_character_references_remain_supported(self):
        plain = fixture("fictional&amp;escaped")
        encoded = '<?xml version="1.0" encoding="UTF-16"?>' + plain.decode()
        self.assertEqual(
            tool.inspect_xml(plain), tool.inspect_xml(encoded.encode("utf-16"))
        )
        self.assertEqual(tool.inspect_xml(plain)[2][0]["id"], "fictional&escaped")

    def test_dtd_entities_and_processing_instructions_remain_refused(self):
        samples = (
            '<!DOCTYPE Recipe [<!ENTITY x "fictional">]><Recipe>&x;</Recipe>',
            '<!DOCTYPE Recipe SYSTEM "urn:fictional:never-resolve"><Recipe/>',
            '<!DOCTYPE Recipe [<!ENTITY x SYSTEM "urn:fictional:never-resolve">]><Recipe>&x;</Recipe>',
            "<?fictional ignore?><Recipe/>",
        )
        for sample in samples:
            for data in (sample.encode(), sample.encode("utf-16")):
                with self.assertRaises(tool.RecipeError) as caught:
                    tool.parse_xml(data)
                self.assertEqual(str(caught.exception), "XML_DECLARATION_FORBIDDEN")

    def test_namespace_and_malformed_xml_remain_fixed_rejections(self):
        for data, code in (
            (b'<Recipe xmlns="urn:fictional"/>', "XML_NAMESPACE_UNSUPPORTED"),
            (b"<fictional-unclosed>", "XML_MALFORMED"),
            (b"\xff", "XML_MALFORMED"),
        ):
            with self.assertRaises(tool.RecipeError) as caught:
                tool.parse_xml(data)
            self.assertEqual(str(caught.exception), code)

    def test_xml_depth_element_text_and_field_caps_remain_bounded(self):
        tool.parse_xml(b"<x>" * tool.MAX_DEPTH + b"</x>" * tool.MAX_DEPTH)
        cases = (
            ("MAX_DEPTH", 2, tool.parse_xml, b"<x><y><z/></y></x>"),
            ("MAX_ELEMENTS", 2, tool.parse_xml, b"<r><a/><b/></r>"),
            ("MAX_TEXT_CHARS", 3, tool.parse_xml, b"<r>four</r>"),
            ("MAX_FIELD_CHARS", 3, tool.inspect_xml, fixture()),
        )
        for name, limit, function, data in cases:
            with patch.object(tool, name, limit), self.assertRaises(tool.RecipeError):
                function(data)

    def test_numbers_missing_values_and_overflow_remain_strict(self):
        self.assertIsNone(tool.number(None, optional=True))
        for value in ("NaN", "Infinity", "-Infinity", "1e999", None, "fictional"):
            with self.assertRaises(tool.RecipeError):
                tool.number(value)
        with self.assertRaises(tool.RecipeError):
            tool.inspect_xml(fixture().replace(b"<X>0.25</X>", b"<X>0</X>", 1))
        overflow = fixture().replace(b"<X>1</X>", b"<X>-1e308</X>", 1)
        overflow = overflow.replace(b"<X>5</X>", b"<X>1e308</X>", 1)
        with self.assertRaises(tool.RecipeError):
            tool.inspect_xml(overflow)

    def test_csv_formula_escaping_and_json_text_are_preserved(self):
        for identifier in ("=1+1", " +1", "&#9;-1", "@fictional", "&#xfeff;=1"):
            _, modules, measurements, overlays = tool.inspect_xml(fixture(identifier))
            outputs = tool.render_outputs(modules, measurements, overlays)
            source_id = measurements[0]["id"]
            row = list(
                csv.DictReader(
                    io.StringIO(outputs["overlay_line_line_summary.csv"].decode())
                )
            )[0]
            self.assertEqual(row["id"], "'" + source_id)
            self.assertEqual(
                json.loads(outputs["measurements_summary.json"])[0]["id"], source_id
            )
        self.assertEqual(tool.csv_cell(-1.5), -1.5)

    def test_non_overlay_and_missing_optional_geometry_keep_three_json_outputs(self):
        plain = b"<Recipe><PixelSize><X>1</X></PixelSize><Modules><Module><ID>fictional</ID></Module></Modules></Recipe>"
        _, modules, measurements, overlays = tool.inspect_xml(plain)
        outputs = tool.render_outputs(modules, measurements, overlays)
        self.assertEqual(len(outputs), 3)
        self.assertIsNone(modules[0]["origin_x"])
        self.assertEqual(
            tool.inspect_xml(fixture().replace(b"OVL_LN_LN", b"FICTIONAL_OTHER"))[3], []
        )

    def test_rendered_output_bound_is_checked_before_native_creation(self):
        _, modules, measurements, overlays = tool.inspect_xml(fixture())
        with (
            patch.object(tool, "MAX_OUTPUT_BYTES", 1),
            self.assertRaises(tool.RecipeError),
        ):
            tool.render_outputs(modules, measurements, overlays)

    def test_native_short_zero_failed_writes_and_flush_failure(self):
        native = object.__new__(win.Native)
        native.core = CORE
        observed = bytearray()

        def partial(_handle, buffer, length, written, _overlapped):
            size = min(7, length)
            observed.extend(buffer.raw[:size])
            written._obj.value = size
            return 1

        native.dll = SimpleNamespace(WriteFile=partial)
        data = bytes(range(256)) * 300
        native.write(None, data)
        self.assertEqual(bytes(observed), data)
        for amount, success in ((0, 1), (999, 1), (1, 0)):

            def failed(_handle, _buffer, _length, written, _overlapped):
                written._obj.value = amount
                return success

            native.dll = SimpleNamespace(WriteFile=failed)
            with self.assertRaises(tool.RecipeError):
                native.write(None, b"fictional")
        native.dll = SimpleNamespace(FlushFileBuffers=lambda _handle: 0)
        with self.assertRaises(tool.RecipeError):
            native.flush(None)

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
        for name in ("fictional.xml", "fictional folder", "modules_summary.json"):
            self.assertTrue(win._component(name), name)

    def test_windows_api_refuses_unsupported_platform(self):
        if os.name == "nt":
            self.skipTest("Unsupported-platform check runs on POSIX")
        with self.assertRaises(tool.RecipeError):
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
        self.folder = self.fixture / "fictional-long-parent-directory"
        self.folder.mkdir()
        self.source = self.folder / "fictional-long-recipe-input.xml"
        self.source.write_bytes(fixture())
        self.output = self.folder / "fictional-new-output-directory"

    def unavailable_link(self, message):
        if os.environ.get("OUTLANDS_XML_REQUIRE_NATIVE_LINKS") == "1":
            self.fail(message)
        self.skipTest(message)

    def invoke(self, source=None, output=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = tool.main(
                [str(source or self.source), "--out-dir", str(output or self.output)]
            )
        self.assertNotIn(str(self.fixture), stdout.getvalue() + stderr.getvalue())
        self.assertNotIn("fictional-measurement", stdout.getvalue() + stderr.getvalue())
        self.assertEqual(stderr.getvalue() if code == 0 else stdout.getvalue(), "")
        value = json.loads(stdout.getvalue() if code == 0 else stderr.getvalue())
        return code, value

    def outputs(self):
        _, modules, measurements, overlays = tool.inspect_xml(fixture())
        return tool.render_outputs(modules, measurements, overlays)

    def test_complete_output_is_deterministic_and_source_is_unchanged(self):
        before = self.source.read_bytes()
        self.assertEqual(
            self.invoke(),
            (
                0,
                {
                    "status": "ok",
                    "modules": 1,
                    "measurements": 1,
                    "overlay_rows": 1,
                    "files_written": 4,
                },
            ),
        )
        second = self.folder / "fictional-second-directory"
        self.assertEqual(self.invoke(output=second)[0], 0)
        for name, payload in self.outputs().items():
            self.assertEqual((self.output / name).read_bytes(), payload)
            self.assertEqual((second / name).read_bytes(), payload)
        self.assertEqual(self.source.read_bytes(), before)

    def test_native_cli_loader_works_in_a_fresh_process(self):
        done = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HERE / "xml_recipe_inspector.py"),
                str(self.source),
                "--out-dir",
                str(self.output),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, "")
        self.assertEqual(json.loads(done.stdout)["files_written"], 4)
        self.assertNotIn(str(self.fixture), done.stdout)

    def test_csv_formula_is_escaped_in_real_new_output(self):
        self.source.write_bytes(fixture("=1+1"))
        self.assertEqual(self.invoke()[0], 0)
        rows = list(
            csv.DictReader(
                io.StringIO((self.output / "overlay_line_line_summary.csv").read_text())
            )
        )
        self.assertEqual(rows[0]["id"], "'=1+1")
        self.assertEqual(
            json.loads((self.output / "measurements_summary.json").read_text())[0][
                "id"
            ],
            "=1+1",
        )

    def test_utf16_input_and_three_file_output_are_supported(self):
        data = "<Recipe><PixelSize><X>1</X></PixelSize></Recipe>"
        self.source.write_bytes(
            ('<?xml version="1.0" encoding="UTF-16"?>' + data).encode("utf-16")
        )
        code, result = self.invoke()
        self.assertEqual((code, result["files_written"]), (0, 3))
        self.assertFalse((self.output / "overlay_line_line_summary.csv").exists())

    def test_invalid_xml_and_declarations_create_no_output(self):
        for data in (
            b"<unclosed>",
            b"\xff",
            b'<!DOCTYPE Recipe [<!ENTITY x "fictional">]><Recipe>&x;</Recipe>',
            b"<?fictional ignore?><Recipe/>",
            b'<Recipe xmlns="urn:fictional"/>',
        ):
            self.source.write_bytes(data)
            self.assertEqual(self.invoke()[0], 2)
            self.assertFalse(self.output.exists())

    def test_input_size_bound_precedes_parser(self):
        for data in (b"", b"x" * (tool.MAX_INPUT_BYTES + 1)):
            self.source.write_bytes(data)
            with patch.object(
                tool, "inspect_xml", side_effect=AssertionError("NO_PARSE")
            ):
                self.assertEqual(self.invoke()[0], 2)
            self.assertFalse(self.output.exists())

    def test_output_size_bound_precedes_directory_creation(self):
        with (
            patch.object(tool, "MAX_OUTPUT_BYTES", 1),
            patch.object(win.Native, "mkdir", side_effect=AssertionError("NO_MKDIR")),
        ):
            self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())

    def test_invalid_output_names_types_and_total_bound_precede_creation(self):
        for value in (
            {},
            [],
            {"../fictional": b"x"},
            {"fictional.json": b"x"},
            {"modules_summary.json": "fictional"},
            {"modules_summary.json": b"x" * (tool.MAX_OUTPUT_BYTES + 1)},
        ):
            with (
                self.assertRaises(tool.RecipeError),
                patch.object(
                    win.Native, "mkdir", side_effect=AssertionError("NO_MKDIR")
                ),
            ):
                tool.write_outputs(self.output, value)
            self.assertFalse(self.output.exists())

    def test_existing_directory_is_not_merged_or_changed(self):
        self.output.mkdir()
        marker = self.output / "modules_summary.json"
        marker.write_bytes(b"Fictional existing bytes")
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(marker.read_bytes(), b"Fictional existing bytes")
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_existing_file_and_input_as_destination_are_unchanged(self):
        self.output.write_bytes(b"Fictional existing bytes")
        before = self.source.read_bytes()
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(self.output.read_bytes(), b"Fictional existing bytes")
        self.assertEqual(self.invoke(output=self.source)[0], 2)
        self.assertEqual(self.source.read_bytes(), before)

    def test_missing_parent_is_not_created(self):
        output = self.fixture / "fictional-missing-parent" / "new"
        self.assertEqual(self.invoke(output=output)[0], 2)
        self.assertFalse(output.parent.exists())

    def test_empty_byte_payload_keeps_existing_low_level_contract(self):
        tool.write_outputs(self.output, {"modules_summary.json": b""})
        self.assertEqual((self.output / "modules_summary.json").read_bytes(), b"")
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_postmkdir_handle_failure_retains_empty_unconfirmed_directory(self):
        original = win.Native.open

        def failed(native, path, directory, expected=None):
            if path == self.output:
                raise tool.RecipeError("FICTIONAL_DIRECTORY_OPEN_FAILURE")
            return original(native, path, directory, expected)

        with patch.object(win.Native, "open", new=failed):
            self.assertEqual(self.invoke()[0], 2)
        self.assertTrue(self.output.is_dir())
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertEqual(self.invoke()[0], 2)

    def test_unexpected_child_is_preserved_by_exclusive_report_creation(self):
        original = win.Native.mkdir
        marker = self.output / "modules_summary.json"

        def populated(native, path):
            original(native, path)
            marker.write_bytes(b"Fictional unexpected existing child")

        with patch.object(win.Native, "mkdir", new=populated):
            self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(marker.read_bytes(), b"Fictional unexpected existing child")
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_missing_and_directory_inputs_create_no_output(self):
        self.assertEqual(
            self.invoke(source=self.fixture / "fictional-missing.xml")[0], 2
        )
        self.assertEqual(self.invoke(source=self.folder)[0], 2)
        self.assertFalse(self.output.exists())

    def test_external_content_is_not_opened_executed_or_enumerated(self):
        with (
            patch.object(socket, "socket", side_effect=AssertionError("NO_SOCKET")),
            patch.object(subprocess, "Popen", side_effect=AssertionError("NO_PROCESS")),
            patch.object(os, "system", side_effect=AssertionError("NO_COMMAND")),
            patch.object(os, "scandir", side_effect=AssertionError("NO_SCAN")),
        ):
            self.assertEqual(self.invoke()[0], 0)
        self.source.write_bytes(
            b'<!DOCTYPE Recipe [<!ENTITY x SYSTEM "urn:fictional:never-resolve">]><Recipe>&x;</Recipe>'
        )
        data = self.source.read_bytes()
        with (
            patch("builtins.open", side_effect=AssertionError("NO_OPEN")),
            patch("io.open", side_effect=AssertionError("NO_IO_OPEN")),
            patch.object(socket, "socket", side_effect=AssertionError("NO_SOCKET")),
        ):
            with self.assertRaises(tool.RecipeError):
                tool.parse_xml(data)

    def test_raw_ambiguous_input_and_output_paths_are_refused(self):
        for value in (
            "../fictional",
            "//fictional-host/share",
            "C:fictional",
            "nul",
            "fictional.",
            "fictional ",
            "fictional:stream",
        ):
            with patch.object(
                win.Native, "open", side_effect=AssertionError("NO_OPEN")
            ):
                self.assertEqual(self.invoke(source=value)[0], 2)
            with patch.object(
                win.Native, "mkdir", side_effect=AssertionError("NO_MKDIR")
            ):
                self.assertEqual(self.invoke(output=value)[0], 2)

    def test_drive_root_is_refused_as_input_or_new_directory(self):
        root = Path(self.source.anchor)
        self.assertEqual(self.invoke(source=root)[0], 2)
        self.assertEqual(self.invoke(output=root)[0], 2)

    def test_held_input_handles_deny_writer_delete_and_parent_rename(self):
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

    def test_existing_data_writer_is_refused(self):
        with self.source.open("r+b"):
            self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())

    def test_hardlinked_input_is_refused_and_existing_destination_preserved(self):
        second = self.fixture / "fictional-second.xml"
        try:
            os.link(self.source, second)
        except OSError:
            self.unavailable_link("Native hardlink creation unavailable")
        self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())
        second.unlink()
        os.link(self.source, self.output)
        before = self.source.read_bytes()
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.output.read_bytes(), before)

    def test_symlink_inputs_output_leaf_and_output_parent_are_refused(self):
        link = self.fixture / "fictional-input-link.xml"
        parent = self.fixture / "fictional-parent-link"
        try:
            link.symlink_to(self.source)
            parent.symlink_to(self.folder, target_is_directory=True)
        except OSError:
            self.unavailable_link("Native symlink privilege unavailable")
        self.assertEqual(self.invoke(source=link)[0], 2)
        self.assertEqual(self.invoke(source=parent / self.source.name)[0], 2)
        self.assertEqual(self.invoke(output=parent / self.output.name)[0], 2)
        self.output.symlink_to(self.folder, target_is_directory=True)
        self.assertEqual(self.invoke()[0], 2)
        self.assertTrue(self.output.is_symlink())
        self.assertFalse((self.folder / "modules_summary.json").exists())

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
        self.assertEqual(self.invoke(output=link)[0], 2)
        self.assertFalse(self.output.exists())

    def short_path(self, path):
        function = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
        function.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD]
        function.restype = w.DWORD
        result = ctypes.create_unicode_buffer(32768)
        size = function(str(path), result, len(result))
        if (
            not size
            or size >= len(result)
            or result.value.casefold() == str(path).casefold()
        ):
            self.skipTest("Native alternate short spelling unavailable")
        return Path(result.value)

    def test_short_input_and_output_parent_aliases_are_refused(self):
        self.assertEqual(self.invoke(source=self.short_path(self.source))[0], 2)
        self.assertEqual(
            self.invoke(output=self.short_path(self.folder) / self.output.name)[0], 2
        )
        self.assertFalse(self.output.exists())

    def test_short_existing_destination_alias_is_not_replaced(self):
        self.output.mkdir()
        marker = self.output / "fictional-kept.txt"
        marker.write_bytes(b"Fictional existing bytes")
        self.assertEqual(self.invoke(output=self.short_path(self.output))[0], 2)
        self.assertEqual(marker.read_bytes(), b"Fictional existing bytes")

    def test_partial_write_retains_new_directory_and_unconfirmed_report(self):
        original = win.Native.write

        def interrupted(native, handle, data):
            original(native, handle, data[:11])
            raise tool.RecipeError("FICTIONAL_WRITE_FAILURE")

        before = self.source.read_bytes()
        with patch.object(win.Native, "write", new=interrupted):
            self.assertEqual(self.invoke()[0], 2)
        first_name, data = next(iter(self.outputs().items()))
        self.assertEqual((self.output / first_name).read_bytes(), data[:11])
        self.assertEqual(len(list(self.output.iterdir())), 1)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.invoke()[0], 2)

    def test_later_write_failure_retains_completed_and_partial_reports(self):
        original = win.Native.write
        calls = 0

        def interrupted(native, handle, data):
            nonlocal calls
            calls += 1
            original(native, handle, data if calls == 1 else data[:7])
            if calls == 2:
                raise tool.RecipeError("FICTIONAL_WRITE_FAILURE")

        with patch.object(win.Native, "write", new=interrupted):
            self.assertEqual(self.invoke()[0], 2)
        names = list(self.outputs())
        self.assertEqual(
            (self.output / names[0]).read_bytes(), self.outputs()[names[0]]
        )
        self.assertEqual(
            (self.output / names[1]).read_bytes(), self.outputs()[names[1]][:7]
        )
        self.assertEqual(len(list(self.output.iterdir())), 2)

    def test_flush_failure_retains_new_unconfirmed_file(self):
        with patch.object(
            win.Native, "flush", side_effect=tool.RecipeError("FICTIONAL_FLUSH_FAILURE")
        ):
            self.assertEqual(self.invoke()[0], 2)
        name, data = next(iter(self.outputs().items()))
        self.assertEqual((self.output / name).read_bytes(), data)
        self.assertEqual(self.invoke()[0], 2)

    def test_created_report_is_exclusive_and_directory_is_retained(self):
        original = win.Native.write
        first_name = next(iter(self.outputs()))

        def checked(native, handle, data):
            path = self.output / first_name
            if path.exists():
                for action in (
                    lambda: path.open("rb"),
                    lambda: path.open("r+b"),
                    path.unlink,
                    lambda: self.output.rename(
                        self.folder / "fictional-renamed-output"
                    ),
                ):
                    with self.assertRaises(PermissionError):
                        action()
            original(native, handle, data)

        with patch.object(win.Native, "write", new=checked):
            self.assertEqual(self.invoke()[0], 0)

    def test_exact_total_output_bound_is_written_across_chunks(self):
        data = bytes(range(256)) * (tool.MAX_OUTPUT_BYTES // 256)
        tool.write_outputs(self.output, {"modules_summary.json": data})
        self.assertEqual((self.output / "modules_summary.json").read_bytes(), data)
        with self.assertRaises(tool.RecipeError):
            tool.write_outputs(
                self.output, {"modules_summary.json": b"fictional replacement"}
            )
        self.assertEqual((self.output / "modules_summary.json").read_bytes(), data)

    def test_postcreation_report_name_failure_retains_empty_report(self):
        original = win.Native.create

        def mismatch(native, path, expected=None):
            return original(native, path, "fictional-unexpected-native-name")

        with patch.object(win.Native, "create", new=mismatch):
            self.assertEqual(self.invoke()[0], 2)
        name = next(iter(self.outputs()))
        self.assertEqual((self.output / name).read_bytes(), b"")

    def test_changed_report_identity_retains_unconfirmed_output(self):
        original = win.Native.describe
        target = next(iter(self.outputs()))
        seen = 0

        def changed(native, handle, directory):
            nonlocal seen
            identity, name = original(native, handle, directory)
            if not directory and name.casefold().endswith("\\" + target.casefold()):
                seen += 1
                if seen > 1:
                    identity = (identity[0], identity[1] + 1, *identity[2:])
            return identity, name

        with patch.object(win.Native, "describe", new=changed):
            self.assertEqual(self.invoke()[0], 2)
        self.assertEqual((self.output / target).read_bytes(), self.outputs()[target])

    def test_descriptor_transfer_failure_closes_native_input_handle(self):
        import msvcrt

        with patch.object(
            msvcrt, "open_osfhandle", side_effect=OSError("fictional-transfer")
        ):
            self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())
        with self.source.open("r+b"):
            pass
        self.assertEqual(self.invoke()[0], 0)

    def test_changed_input_identity_is_rejected_before_output(self):
        original = win.Native.describe
        seen = set()

        def changed(native, handle, directory):
            identity, name = original(native, handle, directory)
            key = (handle, name)
            if not directory and key in seen:
                return (*identity[:-1], identity[-1] + 1), name
            seen.add(key)
            return identity, name

        with patch.object(win.Native, "describe", new=changed):
            self.assertEqual(self.invoke()[0], 2)
        self.assertFalse(self.output.exists())

    def test_close_error_still_attempts_all_retained_parent_handles(self):
        original = win.Native.close
        closed = []

        def close(native, handle):
            original(native, handle)
            closed.append(handle)
            raise tool.RecipeError("FICTIONAL_CLOSE_FAILURE")

        with self.assertRaises(tool.RecipeError):
            with win.Chain(win.Native(CORE), self.folder) as chain:
                expected = len(chain.items)
                with patch.object(win.Native, "close", new=close):
                    chain.__exit__(None, None, None)
        self.assertEqual(len(closed), expected)
        self.assertEqual(len(set(closed)), expected)

    def test_output_close_failure_still_closes_every_report_and_directory(self):
        original = win.Native.close
        closed = []
        failed = False

        # Read attributes directly: describe requires the expected kind.
        def close_checked(native, handle):
            nonlocal failed
            info = win.FileInfo()
            self.assertTrue(
                native.dll.GetFileInformationByHandle(handle, ctypes.byref(info))
            )
            _, name = native.describe(handle, bool(info.attributes & win.DIRECTORY))
            original(native, handle)
            closed.append(name)
            if not failed and name.casefold().endswith(".json"):
                failed = True
                raise tool.RecipeError("FICTIONAL_CLOSE_FAILURE")

        with patch.object(win.Native, "close", new=close_checked):
            self.assertEqual(self.invoke()[0], 2)
        self.assertTrue(failed)
        report_closes = [
            name for name in closed if name.casefold().endswith((".json", ".csv"))
        ]
        self.assertEqual(len(report_closes), 4)
        for name, data in self.outputs().items():
            self.assertEqual((self.output / name).read_bytes(), data)
        renamed = self.folder / "fictional-renamed-after-close-failure"
        self.output.rename(renamed)
        self.assertTrue(renamed.is_dir())

    def test_repeated_success_and_refusal_do_not_grow_handles(self):
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

        self.assertEqual(self.invoke()[0], 0)
        before = count()
        for index in range(15):
            output = self.folder / f"fictional-output-{index}"
            self.assertEqual(self.invoke(output=output)[0], 0)
            self.assertEqual(self.invoke(output=output)[0], 2)
            self.assertEqual(
                self.invoke(
                    source=self.fixture / "fictional-missing.xml", output=output
                )[0],
                2,
            )
        self.assertEqual(count(), before)

    def test_argument_help_and_interruption_privacy(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        canary = "fictional-private-canary"
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(
                tool.main(
                    [
                        str(self.source),
                        "--out-dir",
                        str(self.output),
                        "--unknown",
                        canary,
                    ]
                ),
                2,
            )
        self.assertNotIn(canary, stdout.getvalue() + stderr.getvalue())
        self.assertEqual(json.loads(stderr.getvalue())["code"], "ARGUMENTS_INVALID")
        stdout = io.StringIO()
        with (
            patch.object(tool.sys, "argv", [canary]),
            contextlib.redirect_stdout(stdout),
        ):
            with self.assertRaises(SystemExit) as stopped:
                tool.main(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn("usage: xml_recipe_inspector.py", stdout.getvalue())
        self.assertNotIn(canary, stdout.getvalue())
        with patch.object(tool, "read_xml", side_effect=KeyboardInterrupt):
            code, result = self.invoke()
        self.assertEqual(
            (code, result), (2, {"status": "error", "code": "INTERRUPTED"})
        )


if __name__ == "__main__":
    unittest.main()
