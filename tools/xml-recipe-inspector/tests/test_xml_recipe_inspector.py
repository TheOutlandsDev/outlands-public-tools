"""Synthetic, stdlib-only fixtures. No original recipes or external services."""
import contextlib
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "reviewed_xml_recipe_inspector", Path(__file__).resolve().parents[1] / "xml_recipe_inspector.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def fixture(identifier="synthetic-measurement"):
    return f"""<Recipe><PixelSize><X>0.25</X></PixelSize>
      <Modules><Module><ID>synthetic-module</ID><GeometryImages><GeometryImage>
        <ImageID>synthetic-image</ImageID><Location>fixture-only</Location>
        <Origin><X>2</X><Y>3</Y></Origin><PixelSize><X>0.25</X><Y>0.25</Y></PixelSize>
      </GeometryImage></GeometryImages></Module></Modules>
      <Measurements><Measurement><ID>{identifier}</ID><Type>OVL_LN_LN</Type>
        <ImageID>synthetic-image</ImageID><Orientation>X</Orientation><Direction>forward</Direction>
        <NominalValue>0.5</NominalValue><NominalValueSecond>1.0</NominalValueSecond>
        <PointProperty><UserPoints><Point><X>1</X><Y>2</Y></Point>
          <Point><X>5</X><Y>2</Y></Point></UserPoints><AlgoPoints/>
          <EdgeFactor1>synthetic</EdgeFactor1></PointProperty>
        <PointProperty><UserPoints><Point><X>3</X><Y>6</Y></Point>
          <Point><X>7</X><Y>6</Y></Point></UserPoints><AlgoPoints/></PointProperty>
      </Measurement></Measurements></Recipe>""".encode()


class InspectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def error(self, code, function, *args):
        with self.assertRaises(tool.RecipeError) as caught:
            function(*args)
        self.assertEqual(str(caught.exception), code)

    def test_synthetic_geometry_and_overlay_math(self):
        pixel, modules, measurements, overlays = tool.inspect_xml(fixture())
        self.assertEqual(pixel, 0.25)
        self.assertEqual(modules[0]["origin_x"], 2)
        self.assertEqual(measurements[0]["point_property_count"], 2)
        first = measurements[0]["point_properties"][0]
        self.assertEqual(first["length_px"], 4)
        self.assertEqual(first["length_um_from_pixels"], 1)
        self.assertEqual(overlays[0]["delta_mid_x_px"], 2)
        self.assertEqual(overlays[0]["delta_mid_y_px"], 4)
        self.assertEqual(overlays[0]["delta_mid_x_um"], 0.5)
        self.assertEqual(overlays[0]["delta_mid_y_um"], 1)

    def test_fresh_output_pipeline_is_private_and_strict_json(self):
        source = self.root / "synthetic.xml"
        source.write_bytes(fixture())
        _, modules, measurements, overlays = tool.parse_recipe(source)
        outputs = tool.render_outputs(modules, measurements, overlays)
        destination = self.root / "fresh"
        tool.write_outputs(destination, outputs)
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o700)
        self.assertEqual(len(list(destination.iterdir())), 4)
        for path in destination.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            if path.suffix == ".json":
                json.loads(path.read_text(), parse_constant=lambda s: self.fail("Nonstandard JSON"))
        self.assertEqual(source.read_bytes(), fixture())

    def test_missing_optional_geometry_is_null(self):
        data = b"<Recipe><PixelSize><X>1</X></PixelSize><Modules><Module><ID>synthetic</ID></Module></Modules></Recipe>"
        _, modules, measurements, overlays = tool.inspect_xml(data)
        self.assertIsNone(modules[0]["origin_x"])
        self.assertEqual(measurements, [])
        self.assertEqual(overlays, [])
        outputs = tool.render_outputs(modules, measurements, overlays)
        self.assertNotIn("overlay_line_line_summary.csv", outputs)
        self.assertIn(b"null", outputs["modules_summary.json"])

    def test_non_overlay_measurement_is_not_treated_as_overlay(self):
        data = fixture().replace(b"OVL_LN_LN", b"SYNTHETIC_OTHER")
        self.assertEqual(tool.inspect_xml(data)[3], [])

    def test_missing_point_coordinate_is_rejected(self):
        self.error("INVALID_NUMBER", tool.inspect_xml, fixture().replace(b"<X>1</X>", b"", 1))

    def test_nonfinite_calibration_is_rejected(self):
        for value in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            with self.subTest(value=value):
                self.error("NONFINITE_NUMBER", tool.inspect_xml,
                           fixture().replace(b"<X>0.25</X>", b"<X>" + value + b"</X>", 1))

    def test_zero_or_negative_calibration_is_rejected(self):
        for value in (b"0", b"-1"):
            self.error("INVALID_PIXEL_SIZE", tool.inspect_xml,
                       fixture().replace(b"<X>0.25</X>", b"<X>" + value + b"</X>", 1))

    def test_derived_numeric_overflow_is_rejected(self):
        data = fixture().replace(b"<X>1</X>", b"<X>-1e308</X>", 1).replace(b"<X>5</X>", b"<X>1e308</X>", 1)
        self.error("NUMERIC_OVERFLOW", tool.inspect_xml, data)

    def test_internal_entity_declarations_are_rejected(self):
        data = b'<!DOCTYPE Recipe [<!ENTITY synthetic "never expanded">]><Recipe>&synthetic;</Recipe>'
        self.error("XML_DECLARATION_FORBIDDEN", tool.parse_xml, data)

    def test_external_file_entity_is_rejected(self):
        protected = self.root / "synthetic-private.txt"
        protected.write_text("synthetic-only-not-a-real-secret")
        data = ('<!DOCTYPE Recipe [<!ENTITY synthetic SYSTEM "' + protected.as_uri()
                + '">]><Recipe>&synthetic;</Recipe>').encode()
        with mock.patch("builtins.open", side_effect=AssertionError("Unexpected file access")):
            self.error("XML_DECLARATION_FORBIDDEN", tool.parse_xml, data)

    def test_external_doctype_is_rejected_without_resolution(self):
        self.error("XML_DECLARATION_FORBIDDEN", tool.parse_xml,
                   b'<!DOCTYPE Recipe SYSTEM "urn:synthetic:never-resolve"><Recipe/>')

    def test_utf16_doctype_is_rejected(self):
        data = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE Recipe [<!ENTITY x "synthetic">]><Recipe>&x;</Recipe>'
        self.error("XML_DECLARATION_FORBIDDEN", tool.parse_xml, data.encode("utf-16"))

    def test_processing_instructions_are_rejected(self):
        self.error("XML_DECLARATION_FORBIDDEN", tool.parse_xml, b'<?synthetic ignore?><Recipe/>')

    def test_ordinary_character_references_still_work(self):
        data = fixture("synthetic&amp;escaped")
        self.assertEqual(tool.inspect_xml(data)[2][0]["id"], "synthetic&escaped")

    def test_namespaces_are_explicitly_unsupported(self):
        self.error("XML_NAMESPACE_UNSUPPORTED", tool.parse_xml, b'<Recipe xmlns="urn:synthetic"/>')

    def test_input_size_limit(self):
        self.error("INPUT_SIZE_LIMIT", tool.parse_xml, b"x" * (tool.MAX_INPUT_BYTES + 1))

    def test_depth_limit_and_boundary(self):
        tool.parse_xml(b"<x>" * tool.MAX_DEPTH + b"</x>" * tool.MAX_DEPTH)
        self.error("XML_DEPTH_LIMIT", tool.parse_xml,
                   b"<x>" * (tool.MAX_DEPTH + 1) + b"</x>" * (tool.MAX_DEPTH + 1))

    def test_element_limit(self):
        with mock.patch.object(tool, "MAX_ELEMENTS", 4):
            self.error("XML_ELEMENT_LIMIT", tool.parse_xml, b"<r><a/><b/><c/><d/></r>")

    def test_text_limit(self):
        with mock.patch.object(tool, "MAX_TEXT_CHARS", 8):
            self.error("XML_TEXT_LIMIT", tool.parse_xml, b"<r>123456789</r>")

    def test_field_limit(self):
        with mock.patch.object(tool, "MAX_FIELD_CHARS", 8):
            self.error("FIELD_SIZE_LIMIT", tool.inspect_xml, fixture("synthetic-too-long"))

    def test_malformed_xml_has_a_fixed_error(self):
        self.error("XML_MALFORMED", tool.parse_xml, b"<synthetic-unclosed>")

    def test_formula_like_csv_text_is_escaped_but_numbers_remain_numeric(self):
        for value in ("=1+1", " +1", "\t-1", "@synthetic", "\ufeff=1"):
            self.assertEqual(tool.csv_cell(value), "'" + value)
        self.assertEqual(tool.csv_cell(-1.5), -1.5)
        self.assertEqual(tool.csv_cell("synthetic"), "synthetic")
        _, modules, measurements, overlays = tool.inspect_xml(fixture("=1+1"))
        payload = tool.render_outputs(modules, measurements, overlays)["overlay_line_line_summary.csv"]
        row = list(csv.DictReader(io.StringIO(payload.decode())))[0]
        self.assertEqual(row["id"], "'=1+1")

    def test_output_size_limit_before_creation(self):
        source = self.root / "synthetic.xml"
        source.write_bytes(fixture())
        destination = self.root / "not-created"
        with mock.patch.object(tool, "MAX_OUTPUT_BYTES", 1), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(tool.main([str(source), "--out-dir", str(destination)]), 2)
        self.assertFalse(destination.exists())

    def test_existing_output_directory_is_untouched(self):
        destination = self.root / "existing"
        destination.mkdir()
        marker = destination / "modules_summary.json"
        marker.write_bytes(b"synthetic-existing")
        self.error("OUTPUT_EXISTS", tool.write_outputs, destination, {"modules_summary.json": b"[]"})
        self.assertEqual(marker.read_bytes(), b"synthetic-existing")
        self.assertEqual(len(list(destination.iterdir())), 1)

    def test_existing_output_file_is_untouched(self):
        destination = self.root / "existing-file"
        destination.write_bytes(b"synthetic-existing")
        self.error("OUTPUT_EXISTS", tool.write_outputs, destination, {"modules_summary.json": b"[]"})
        self.assertEqual(destination.read_bytes(), b"synthetic-existing")

    def test_input_symlink_and_output_symlink_are_refused(self):
        source = self.root / "source.xml"
        source.write_bytes(fixture())
        link = self.root / "input-link"
        link.symlink_to(source)
        self.error("SYMLINK_FORBIDDEN", tool.read_xml, link)
        target = self.root / "target"
        target.mkdir()
        out_link = self.root / "output-link"
        out_link.symlink_to(target, target_is_directory=True)
        self.error("OUTPUT_EXISTS", tool.write_outputs, out_link, {"modules_summary.json": b"[]"})
        self.assertEqual(list(target.iterdir()), [])

    def test_output_parent_symlink_is_refused(self):
        target = self.root / "target"
        target.mkdir()
        link = self.root / "parent-link"
        link.symlink_to(target, target_is_directory=True)
        self.error("SYMLINK_FORBIDDEN", tool.write_outputs, link / "new", {"modules_summary.json": b"[]"})
        self.assertEqual(list(target.iterdir()), [])

    def test_fifo_is_refused_without_blocking(self):
        fifo = self.root / "synthetic-fifo"
        os.mkfifo(fifo)
        self.error("INPUT_NOT_REGULAR", tool.read_xml, fifo)

    def test_output_name_traversal_is_refused(self):
        destination = self.root / "new"
        self.error("INVALID_OUTPUT", tool.write_outputs, destination, {"../outside": b"synthetic"})
        self.assertFalse(destination.exists())

    def test_cli_prints_counts_and_fixed_error_codes(self):
        source = self.root / "synthetic.xml"
        source.write_bytes(fixture())
        destination = self.root / "new"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tool.main([str(source), "--out-dir", str(destination)]), 0)
        self.assertEqual(json.loads(out.getvalue())["overlay_rows"], 1)
        self.assertNotIn("synthetic-measurement", out.getvalue())
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            self.assertEqual(tool.main([str(source), "--out-dir", str(destination)]), 2)
        self.assertEqual(json.loads(error.getvalue()), {"status": "error", "code": "OUTPUT_EXISTS"})


    def test_unknown_argument_does_not_echo_private_value(self):
        canary = "/private/CLI-ARGUMENT-CANARY"
        out, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(error):
            self.assertEqual(tool.main(["input.xml", "--out-dir", "new", "--unknown", canary]), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(json.loads(error.getvalue()), {"status": "error", "code": "ARGUMENTS_INVALID"})
        self.assertNotIn(canary, error.getvalue())

    def test_missing_input_does_not_echo_output_path(self):
        canary = "/private/CLI-OUTPUT-CANARY"
        out, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(error):
            self.assertEqual(tool.main(["--out-dir", canary]), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(json.loads(error.getvalue()), {"status": "error", "code": "ARGUMENTS_INVALID"})
        self.assertNotIn(canary, error.getvalue())

    def test_missing_output_does_not_echo_input_path(self):
        canary = "/private/CLI-INPUT-CANARY"
        out, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(error):
            self.assertEqual(tool.main([canary, "--out-dir"]), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(json.loads(error.getvalue()), {"status": "error", "code": "ARGUMENTS_INVALID"})
        self.assertNotIn(canary, error.getvalue())

    def test_help_uses_static_program_name(self):
        canary = "/private/CLI-PROGRAM-CANARY"
        out, error = io.StringIO(), io.StringIO()
        with mock.patch.object(tool.sys, "argv", [canary]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(error):
                with self.assertRaises(SystemExit) as stopped:
                    tool.main(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn("usage: xml_recipe_inspector.py", out.getvalue())
        self.assertIn("no vendor measurement validation", out.getvalue())
        self.assertNotIn(canary, out.getvalue())
        self.assertEqual(error.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
