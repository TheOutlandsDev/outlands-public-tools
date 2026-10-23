"""Synthetic regression tests; no existing documents or remote services used."""
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("markdown_docx_under_test", ROOT / "markdown_docx.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class DocumentBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="document-builder-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "fictional.md"
        self.source.write_bytes((ROOT / "examples/fictional_request.md").read_bytes())
        self.output = self.root / "example.docx"

    def invoke(self, source=None, output=None, title="OUTLANDS Synthetic Example"):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = builder.main(["--input", str(source or self.source), "--output", str(output or self.output), "--title", title])
        self.assertNotIn(str(self.root), stdout.getvalue() + stderr.getvalue())
        return status, stdout.getvalue(), stderr.getvalue()

    def rejected(self, source=None, output=None, title="OUTLANDS Synthetic Example"):
        target = output or self.output
        status, stdout, stderr = self.invoke(source, target, title)
        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("DOCUMENT_BUILD_FAILED:"))
        self.assertFalse(target.exists())

    def test_fictional_content_table_and_neutral_properties(self):
        self.assertEqual(self.invoke()[0], 0)
        with zipfile.ZipFile(self.output) as archive:
            xml = archive.read("word/document.xml")
            self.assertIn(b"Fictional Parts Request", xml)
            self.assertIn(b"DEMO-A", xml)
            self.assertIn(b"<w:tbl>", xml)
            self.assertFalse(any(name.startswith("word/media/") for name in archive.namelist()))
            combined = b"\n".join(archive.read(name) for name in archive.namelist() if name.endswith(".xml"))
            self.assertNotIn(str(self.root).encode(), combined)
            core = ET.fromstring(archive.read("docProps/core.xml"))
            ns = {"dc":"http://purl.org/dc/elements/1.1/", "cp":"http://schemas.openxmlformats.org/package/2006/metadata/core-properties", "dcterms":"http://purl.org/dc/terms/"}
            self.assertEqual(core.findtext("dc:creator", namespaces=ns), "OUTLANDS")
            self.assertEqual(core.findtext("cp:lastModifiedBy", namespaces=ns), "OUTLANDS")
            self.assertEqual(core.findtext("dcterms:created", namespaces=ns), "2000-01-01T00:00:00Z")
            self.assertEqual(core.findtext("dcterms:modified", namespaces=ns), "2000-01-01T00:00:00Z")
            self.assertEqual(core.findtext("dc:title", namespaces=ns), "OUTLANDS Synthetic Example")
            self.assertEqual(core.findtext("dc:subject", namespaces=ns), "Local Markdown document")
            self.assertEqual(core.findtext("cp:revision", namespaces=ns), "1")
            for field in ("dc:description", "cp:keywords", "cp:category", "dc:identifier"):
                self.assertFalse(core.findtext(field, namespaces=ns))
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o600)

    def test_existing_output_preserved(self):
        self.output.write_bytes(b"fictional existing output")
        before = self.output.read_bytes()
        self.assertEqual(self.invoke()[0], 2)
        self.assertEqual(self.output.read_bytes(), before)

    def test_missing_input(self):
        self.rejected(self.root / "missing.md")

    def test_directory_input(self):
        self.rejected(self.root)

    def test_invalid_utf8(self):
        self.source.write_bytes(b"\xff\xfe")
        self.rejected()

    def test_oversized_input(self):
        self.source.write_bytes(b"x" * (builder.MAX_INPUT_BYTES + 1))
        self.rejected()

    def test_too_many_lines(self):
        self.source.write_text("\n" * (builder.MAX_LINES + 1))
        self.rejected()

    def test_long_line(self):
        self.source.write_text("x" * (builder.MAX_LINE_CHARS + 1))
        self.rejected()

    def test_control_character(self):
        self.source.write_bytes(b"text\x00text")
        self.rejected()

    def test_ragged_table(self):
        self.source.write_text("| A | B |\n| --- | --- |\n| one |\n")
        self.rejected()

    def test_wide_table(self):
        self.source.write_text("|" + " x |" * 17 + "\n|" + " --- |" * 17 + "\n")
        self.rejected()

    def test_table_row_limit(self):
        self.source.write_text("| A | B |\n| --- | --- |\n" + "| x | y |\n" * 1001)
        self.rejected()

    def test_missing_parent_not_created(self):
        self.rejected(output=self.root / "missing" / "new.docx")
        self.assertFalse((self.root / "missing").exists())

    def test_output_extension(self):
        self.rejected(output=self.root / "wrong.txt")

    def test_title_limit(self):
        self.rejected(title="x" * 161)

    def test_traversal_rejected(self):
        with self.assertRaises(builder.BuildError):
            builder.checked_path(str(self.root) + "/../not-used.docx")

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError):
            self.skipTest("This environment does not permit synthetic symlinks")

    def test_input_symlink(self):
        link = self.root / "linked.md"
        self.symlink(link, self.source)
        self.rejected(source=link)

    def test_parent_symlink(self):
        link = self.root / "linked-parent"
        self.symlink(link, self.root, directory=True)
        self.rejected(source=link / "fictional.md")

    def test_output_symlink_preserved(self):
        target = self.root / "target.docx"
        target.write_bytes(b"fictional existing document")
        self.symlink(self.output, target)
        self.assertEqual(self.invoke()[0], 2)
        self.assertTrue(self.output.is_symlink())
        self.assertEqual(target.read_bytes(), b"fictional existing document")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO creation is not available")
    def test_fifo_input_rejected(self):
        fifo = self.root / "pipe.md"
        os.mkfifo(fifo)
        self.rejected(source=fifo)


    def rejected_arguments(self, arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = builder.main(arguments)
        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "DOCUMENT_BUILD_FAILED:ARGUMENTS_INVALID\n")
        self.assertFalse(self.output.exists())

    def test_unknown_argument_does_not_echo_private_values(self):
        self.rejected_arguments(["--input", str(self.source), "--output", str(self.output),
                                 "--unknown", "PRIVATE-ARGUMENT-CANARY"])

    def test_missing_input_does_not_echo_output_path(self):
        self.rejected_arguments(["--output", str(self.output)])

    def test_missing_output_value_does_not_echo_input_path(self):
        self.rejected_arguments(["--input", str(self.source), "--output"])

    def test_missing_title_value_does_not_echo_paths(self):
        self.rejected_arguments(["--input", str(self.source), "--output", str(self.output), "--title"])

    def test_help_uses_static_program_name(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(builder.sys, "argv", ["/private/PROGRAM-NAME-CANARY"]):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as stopped:
                    builder.main(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn("usage: markdown_docx.py", stdout.getvalue())
        self.assertNotIn("PROGRAM-NAME-CANARY", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_missing_dependency_cli_has_no_traceback_and_help_works(self):
        bootstrap = '''import runpy, sys
class MissingDependency:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "docx" or fullname.startswith("docx."):
            raise ModuleNotFoundError("PRIVATE-DEPENDENCY-CANARY")
sys.meta_path.insert(0, MissingDependency())
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
'''
        base = [sys.executable, "-I", "-B", "-c", bootstrap, str(ROOT / "markdown_docx.py")]
        rejected = subprocess.run(base + ["--input", str(self.source), "--output", str(self.output)],
                                  capture_output=True, timeout=10, cwd=self.root)
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(rejected.stdout, b"")
        self.assertEqual(rejected.stderr, b"DOCUMENT_BUILD_FAILED:DEPENDENCY_UNAVAILABLE\n")
        self.assertFalse(self.output.exists())
        help_result = subprocess.run(base + ["--help"], capture_output=True, timeout=10, cwd=self.root)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn(b"usage: markdown_docx.py", help_result.stdout)
        self.assertNotIn(str(ROOT).encode(), help_result.stdout)
        self.assertEqual(help_result.stderr, b"")

    def test_literal_markup_creates_no_media_or_external_relationships(self):
        self.source.write_text("# Fictional links\n![demo](https://example.invalid/image.png)\n"
                               "[demo](https://example.invalid/)\n<script>fictional()</script>\n")
        self.assertEqual(self.invoke()[0], 0)
        with zipfile.ZipFile(self.output) as archive:
            self.assertFalse(any(name.startswith("word/media/") for name in archive.namelist()))
            for name in archive.namelist():
                if name.endswith(".rels"):
                    relationships = ET.fromstring(archive.read(name))
                    self.assertFalse(any(node.get("TargetMode") == "External" for node in relationships))
            self.assertIn(b"https://example.invalid/", archive.read("word/document.xml"))


if __name__ == "__main__":
    unittest.main()
