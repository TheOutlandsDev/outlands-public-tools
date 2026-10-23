"""Synthetic layout-checker regression tests; no original project is read."""
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("layout_checker_under_test", HERE / "layout_check.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@unittest.skipUnless(checker.platform_supported(), "POSIX no-follow descriptor support required")
class LayoutCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="layout-checker-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "package"
        self.root.mkdir()
        (self.root / "src").mkdir()
        (self.root / "README.md").write_text("Fictional sample package\n")
        (self.root / "src/demo.py").write_text("def add(a, b):\n    return a + b\n")
        self.manifest = self.home / "layout.json"
        self.entries = [{"path":"README.md"},{"path":"src/demo.py","python_syntax":True,"forbidden_literals":["DO_NOT_SHIP_EXAMPLE"]}]
        self.write_manifest()

    def write_manifest(self, entries=None):
        self.manifest.write_text(json.dumps({"schema_version":1,"files":self.entries if entries is None else entries}))

    def invoke(self, root=None, manifest=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = checker.main(["--root",str(root or self.root),"--manifest",str(manifest or self.manifest)])
        output = stdout.getvalue()
        self.assertNotIn(str(self.home), output + stderr.getvalue())
        self.assertEqual(stderr.getvalue(), "")
        return code, json.loads(output), output

    def test_fictional_layout_passes(self):
        code, report, _ = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(report["checked_files"], 2)
        self.assertEqual(report["failed_files"], 0)

    def test_missing_file_fails(self):
        (self.root / "README.md").unlink()
        code, report, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("MISSING", report["results"][0]["codes"])

    def test_syntax_error_without_source_exposure(self):
        marker = "SYNTHETIC_PRIVATE_CANARY"
        (self.root / "src/demo.py").write_text("def " + marker + "(\n")
        code, report, output = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("PYTHON_SYNTAX", report["results"][1]["codes"])
        self.assertNotIn(marker, output)

    def test_forbidden_literal_casefold_without_value(self):
        marker = "DO_NOT_SHIP_EXAMPLE"
        (self.root / "src/demo.py").write_text("# " + marker.lower() + "\n")
        code, report, output = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("FORBIDDEN_LITERAL", report["results"][1]["codes"])
        self.assertNotIn(marker, output)
        self.assertNotIn(marker.lower(), output)

    def test_source_is_not_executed(self):
        (self.root / "src/demo.py").write_text('raise RuntimeError("not executed")\n')
        self.assertEqual(self.invoke()[0], 0)

    def test_presence_only_binary_not_decoded(self):
        (self.root / "README.md").write_bytes(b"\xff\x00")
        self.assertEqual(self.invoke()[0], 0)

    def test_invalid_utf8_text_fails(self):
        (self.root / "src/demo.py").write_bytes(b"\xff")
        code, report, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("TEXT_INVALID", report["results"][1]["codes"])

    def test_duplicate_json_keys_rejected(self):
        self.manifest.write_text('{"schema_version":1,"schema_version":1,"files":[]}')
        self.assertEqual(self.invoke()[0], 2)

    def test_nonfinite_json_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                self.manifest.write_text('{"schema_version":'+value+',"files":[]}')
                self.assertEqual(self.invoke()[0], 2)

    def test_unknown_fields_rejected(self):
        self.entries[0]["unknown"] = True
        self.write_manifest()
        self.assertEqual(self.invoke()[0], 2)

    def test_bool_schema_version_rejected(self):
        self.manifest.write_text('{"schema_version":true,"files":[{"path":"README.md"}]}')
        self.assertEqual(self.invoke()[0], 2)

    def test_empty_manifest_rejected(self):
        self.write_manifest([])
        self.assertEqual(self.invoke()[0], 2)

    def test_manifest_size_bound(self):
        self.manifest.write_bytes(b" " * (checker.MAX_MANIFEST_BYTES + 1))
        self.assertEqual(self.invoke()[0], 2)

    def test_file_size_bound(self):
        (self.root / "README.md").write_bytes(b"x" * (checker.MAX_FILE_BYTES + 1))
        code, report, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("BYTE_LIMIT", report["results"][0]["codes"])

    def test_file_count_bound(self):
        self.write_manifest([{"path":str(n)+".py"} for n in range(101)])
        self.assertEqual(self.invoke()[0], 2)

    def test_bad_manifest_paths(self):
        for path in ("../escape.py","/absolute.py","a//b.py","a/./b.py","C:/file.py","a\\b.py","bad\x00name"):
            with self.subTest(path=path):
                self.write_manifest([{"path":path}])
                self.assertEqual(self.invoke()[0], 2)

    def test_case_collision_rejected(self):
        self.write_manifest([{"path":"README.md"},{"path":"readme.md"}])
        self.assertEqual(self.invoke()[0], 2)

    def test_root_symlink_rejected(self):
        link = self.home / "root-link";link.symlink_to(self.root,target_is_directory=True)
        self.assertEqual(self.invoke(root=link)[0], 2)

    def test_manifest_symlink_rejected(self):
        link = self.home / "manifest-link.json";link.symlink_to(self.manifest)
        self.assertEqual(self.invoke(manifest=link)[0], 2)

    def test_expected_file_symlink_rejected(self):
        target = self.home / "outside.md";target.write_text("fictional external content")
        (self.root / "README.md").unlink();(self.root / "README.md").symlink_to(target)
        self.assertEqual(self.invoke()[0], 1)

    def test_intermediate_symlink_rejected(self):
        (self.root / "src/demo.py").unlink();(self.root / "src").rmdir()
        target = self.home / "outside";target.mkdir();(target / "demo.py").write_text("pass\n")
        (self.root / "src").symlink_to(target,target_is_directory=True)
        self.assertEqual(self.invoke()[0], 1)

    def test_hardlink_rejected(self):
        os.link(self.root / "README.md", self.home / "second-link.md")
        self.assertEqual(self.invoke()[0], 1)

    def test_fifo_nonblocking_rejection(self):
        (self.root / "README.md").unlink();os.mkfifo(self.root / "README.md")
        self.assertEqual(self.invoke()[0], 1)

    def test_selected_directory_rejected(self):
        (self.root / "README.md").unlink();(self.root / "README.md").mkdir()
        self.assertEqual(self.invoke()[0], 1)

    def test_total_text_budget(self):
        entries = []
        for n in range(9):
            name = str(n)+".py";(self.root/name).write_bytes(b" "*checker.MAX_FILE_BYTES)
            entries.append({"path":name,"python_syntax":True})
        self.write_manifest(entries)
        code, report, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("TOTAL_BYTE_LIMIT",report["results"][-1]["codes"])

    def test_unlisted_file_not_checked(self):
        (self.root / "unlisted.py").write_text("not valid python @@\n")
        code, report, output = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(report["checked_files"],2)
        self.assertNotIn("unlisted.py",output)

    def test_package_bytes_unchanged(self):
        paths = [self.root/"README.md",self.root/"src/demo.py",self.manifest]
        before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        self.assertEqual(self.invoke()[0],0)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})

    def test_missing_manifest_and_root_fail(self):
        self.assertEqual(self.invoke(manifest=self.home/"missing.json")[0],2)
        self.assertEqual(self.invoke(root=self.home/"missing-root")[0],2)

    def test_read_error_nonzero(self):
        fd = checker.open_directory(self.root)
        try:
            with mock.patch.object(checker,"open_regular",side_effect=PermissionError()):
                result, used = checker.inspect_entry(fd,{"path":"README.md"},0)
            self.assertEqual(result["status"],"FAIL")
            self.assertIn("READ_ERROR",result["codes"])
        finally:os.close(fd)

    def test_unsupported_platform_rejected(self):
        with mock.patch.object(checker,"platform_supported",return_value=False):
            self.assertEqual(self.invoke()[0],2)

    def test_cli_errors_do_not_echo_arguments(self):
        marker = "FICTIONAL_PRIVATE_ARGUMENT"
        for args in (["--unknown", marker], ["--root"], []):
            with self.subTest(args=args):
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = checker.main(args)
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(stdout.getvalue()), {"status":"REJECTED","code":"ARGUMENTS_INVALID"})
                self.assertNotIn(marker, stdout.getvalue() + stderr.getvalue())
                self.assertEqual(stderr.getvalue(), "")

    def test_help_keeps_static_usage(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as result:
            checker.main(["--help"])
        self.assertEqual(result.exception.code, 0)
        self.assertIn("--manifest", stdout.getvalue())

    def test_root_manifest_rejected_without_trace(self):
        code, report, output = self.invoke(manifest=Path("/"))
        self.assertEqual(code, 2)
        self.assertEqual(report["code"], "MANIFEST_INVALID")
        self.assertNotIn("Traceback", output)
        with self.assertRaises(checker.EntryFailure):
            checker.open_regular(-1, "")


if __name__ == "__main__":unittest.main()
