"""Stdlib process fixtures using only two copied runtime files and invented docs."""

import ctypes
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("docs_check.py", "docs_windows.py")
LIMITS = "Common Markdown links only; no anchor validation, external fetch, or source execution"
MAX_BYTES = 2 * 1024 * 1024


class Download(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="documentation-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied runtime"
        self.runtime.mkdir()
        self.runtime_bytes = {}
        for name in RUNTIME:
            data = (ROOT / name).read_bytes()
            self.runtime_bytes[name] = data
            (self.runtime / name).write_bytes(data)
        self.docs = self.work / "fictional documentation"
        self.docs.mkdir()
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def file(self, name, data=b"# Fictional document\n"):
        path = self.docs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        return path

    def wrapper(self, code):
        self.serial += 1
        path = self.work / ("controlled-child-" + str(self.serial) + ".py")
        path.write_text("import sys\nsys.path.insert(0, " + repr(str(self.runtime)) + ")\n"
                        "import docs_check as tool\n" + code + "\nraise SystemExit(tool.main(sys.argv[1:]))\n",
                        encoding="utf-8", newline="\n")
        return path

    def process(self, *arguments, expected=0, script=None, json_output=True):
        # These are owned regular fixture paths. Never probe arbitrary CLI roots
        # or link targets when recording the read-only assertion.
        retained = {path: path.read_bytes() for path in self.work.rglob("*")
                    if not path.is_symlink() and not path.is_junction() and path.is_file()}
        inventory = {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")}
        result = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8",
                                 str(script or self.runtime / "docs_check.py"), *map(str, arguments)],
                                cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=35)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        for path, data in retained.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertEqual(inventory, {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")})
        self.assertEqual({p.name for p in self.runtime.iterdir()}, set(RUNTIME))
        for name, data in self.runtime_bytes.items():
            self.assertEqual((self.runtime / name).read_bytes(), data)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
        text = result.stdout.replace("\\\\", "\\")
        self.assertNotIn(str(self.work), text)
        self.assertNotIn(str(ROOT), text)
        if not json_output:
            return result.stdout
        self.assertEqual(len(result.stdout.splitlines()), 1)
        response = json.loads(result.stdout)
        if expected in (2, 130):
            self.assertEqual(response, dict(status="ERROR", code="DOCUMENTATION_CHECK_INTERRUPTED"
                                            if expected == 130 else "DOCUMENTATION_CHECK_FAILED"))
        else:
            self.assertEqual(set(response), {"status", "checked_documents", "findings", "limits"})
            self.assertEqual(response["status"], "PASS" if expected == 0 else "FAIL")
            self.assertEqual(response["limits"], LIMITS)
            self.assertIs(type(response["checked_documents"]), int)
            self.assertEqual(bool(response["findings"]), expected == 1)
        return response

    def check(self, expected=0, root=None, script=None):
        return self.process("--root", self.docs if root is None else root, expected=expected, script=script)

    def symlink(self, path, target, directory=False):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as failure:
            if (os.name == "nt" and getattr(failure, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_DOCS_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_minimal_pass_uses_only_copied_runtime_and_selected_scope(self):
        self.file("README.md", "# Fictional\n[local](target.txt)\n")
        self.file("target.txt", b"FICTIONAL_TARGET_BODY_NOT_A_REPORT")
        self.file("settings.json", b'{"fictional":true}\n')
        self.assertEqual(self.check(), dict(status="PASS", checked_documents=2, findings=[], limits=LIMITS))

    def test_help_no_default_root_and_private_arguments_do_not_echo(self):
        text = self.process("--help", json_output=False)
        self.assertIn("--root", text)
        self.assertIn("offline", text)
        self.process(expected=2)
        self.process("--FICTIONAL_PRIVATE_ARGUMENT", "FICTIONAL_PRIVATE_VALUE", expected=2)
        self.process("--root", expected=2)

    def test_missing_and_file_roots_return_fixed_error_not_false_findings(self):
        private = self.work / "FICTIONAL_PRIVATE_MISSING_ROOT"
        self.check(root=private, expected=2)
        self.assertFalse(private.exists())
        regular = self.file("FICTIONAL_PRIVATE_FILE.txt", b"Fictional")
        self.check(root=regular, expected=2)

    def test_findings_exit_one_have_relative_path_rule_and_line_fields(self):
        self.file("relative-document.md", "# Fictional\n\n[missing](absent.txt)\n")
        report = self.check(expected=1)
        self.assertEqual(report["checked_documents"], 1)
        self.assertEqual(report["findings"], [dict(path="relative-document.md", line=3, rule="MISSING_OR_LINKED_TARGET")])
        self.assertNotIn("absent.txt", json.dumps(report))

    def test_finding_order_is_exact_name_then_document_line_and_stack_order(self):
        for name in ("b.md", "Z.md", "A.md", "a-folder/one.md", "z-folder/one.md"):
            self.file(name, "[one](missing-one.txt)\n[two](missing-two.txt)\n")
        report = self.check(expected=1)
        self.assertEqual([(row["path"], row["line"]) for row in report["findings"]],
                         [(path, line) for path in ("A.md", "Z.md", "b.md", "z-folder/one.md", "a-folder/one.md")
                          for line in (1, 2)])
        self.assertEqual(self.check(expected=1), report)

    def test_inline_image_and_reference_definition_links_are_checked(self):
        self.file("README.md", "[inline](missing.txt)\n![image](missing.bin)\n[reference]: missing.dat\n")
        report = self.check(expected=1)
        self.assertEqual(report["findings"], [dict(path="README.md", line=line, rule="MISSING_OR_LINKED_TARGET")
                                             for line in (1, 2, 3)])
        self.assertEqual(report["checked_documents"], 1)

    def test_fenced_and_simple_inline_code_are_skipped_without_execution(self):
        self.file("README.md", "```python\n[ignored](missing.txt)\nraise Exception('FICTIONAL_EXECUTION_TRAP')\n```\n"
                  "~~~text\n[ignored](also-missing.txt)\n~~~\n`[inline code](absent.txt)`\n")
        self.file("not-executed.py", "raise Exception('FICTIONAL_EXECUTION_TRAP')\n")
        self.assertEqual(self.check()["checked_documents"], 1)

    def test_percent_encoded_angle_and_title_links_resolve_local_metadata(self):
        self.file("folder/target file.txt", b"Fictional target")
        self.file("README.md", '[one](folder/target%20file.txt)\n[two](<folder/target%20file.txt> "Title")\n'
                  '[three](folder%2Ftarget%20file.txt "Title")\n[reference]: folder/target%20file.txt "Title"\n')
        self.assertEqual(self.check()["checked_documents"], 1)

    def test_anchor_and_reference_use_validation_are_explicitly_outside_scope(self):
        self.file("README.md", "# Fictional\n[fragment](#definitely-no-such-heading)\n"
                  "[local](README.md#also-not-a-heading)\n[unresolved-reference][missing-definition]\n")
        self.assertEqual(self.check()["findings"], [])

    def test_controlled_child_never_fetches_http_https_or_mail_links(self):
        self.file("README.md", "[http](http://fictional.invalid/not-requested)\n"
                  "[https](https://fictional.invalid/not-requested)\n[mail](mailto:fictional@example.invalid)\n")
        wrapper = self.wrapper("import socket, urllib.request, subprocess, os\n"
                               "def forbidden(*args, **kwargs):\n    raise AssertionError('EXTERNAL_ACTION_ATTEMPTED')\n"
                               "socket.socket = forbidden\nsocket.create_connection = forbidden\n"
                               "urllib.request.urlopen = forbidden\nsubprocess.run = forbidden\nos.system = forbidden\n")
        self.assertEqual(self.check(script=wrapper)["checked_documents"], 1)

    def test_other_schemes_protocol_relative_and_malformed_urls_are_findings(self):
        self.file("README.md", "[file](file:///fictional.txt)\n[ftp](ftp://fictional.invalid/a)\n"
                  "[data](data:text/plain,fictional)\n[network](//fictional.invalid/a)\n[bad](http://[)\n")
        report = self.check(expected=1)
        self.assertEqual([row["rule"] for row in report["findings"]],
                         ["UNSUPPORTED_LINK_SCHEME"] * 4 + ["INVALID_LINK"])
        self.assertEqual([row["line"] for row in report["findings"]], [1, 2, 3, 4, 5])

    def test_parent_and_encoded_root_escapes_fail_without_reading_target_bodies(self):
        outside = self.work / "outside.txt"
        outside.write_bytes(b"FICTIONAL_OUTSIDE_BODY_NOT_REPORT")
        self.file("README.md", "[escape](../outside.txt)\n[encoded](%2e%2e%2foutside.txt)\n")
        report = self.check(expected=1)
        self.assertEqual(report["findings"], [dict(path="README.md", line=line, rule="LINK_ESCAPES_ROOT") for line in (1, 2)])
        self.assertNotIn("FICTIONAL_OUTSIDE_BODY_NOT_REPORT", json.dumps(report))

    def test_json_bom_duplicate_keys_arbitrary_values_and_universal_newlines_pass(self):
        self.file("duplicate.json", b'\xef\xbb\xbf{"fictional":1,"fictional":2}\r\n')
        self.file("array.JSON", b'[1, true, null]\r')
        self.file("null.json", b'null\n')
        self.file("not-a-validated-schema.json", b'{"schema_version":"fictional-unknown","extra":42}\n')
        self.assertEqual(self.check()["checked_documents"], 4)

    def test_nonstandard_json_constants_and_invalid_syntax_are_findings(self):
        for index, value in enumerate((b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{broken')):
            self.file(str(index) + ".json", value)
        report = self.check(expected=1)
        self.assertEqual(report["checked_documents"], 4)
        self.assertEqual(report["findings"], [dict(path=str(index) + ".json", rule="INVALID_JSON") for index in range(4)])

    def test_invalid_utf8_is_read_error_without_content_or_exception_disclosure(self):
        self.file("bad.md", b"\xffFICTIONAL_PRIVATE_DOCUMENT_BODY")
        self.file("bad.json", b"\xfeFICTIONAL_PRIVATE_JSON_BODY")
        report = self.check(expected=1)
        self.assertEqual(report["checked_documents"], 0)
        self.assertEqual(report["findings"], [dict(path=name, rule="READ_ERROR") for name in ("bad.json", "bad.md")])
        self.assertNotIn("FICTIONAL_PRIVATE_", json.dumps(report))

    def test_bom_crlf_and_cr_are_normalized_before_line_findings(self):
        self.file("README.md", b'\xef\xbb\xbf# Fictional\r\n\r[x](missing.txt)\n[y](other.txt)\r')
        report = self.check(expected=1)
        self.assertEqual(report["findings"], [dict(path="README.md", line=line, rule="MISSING_OR_LINKED_TARGET") for line in (3, 4)])

    def test_exclusions_and_selected_extensions_do_not_expand_scope(self):
        for name in (".git", ".hidden", "node_modules", "runtime", "private", "__pycache__"):
            self.file(name + "/invalid.json", b"{fictional")
        self.file("ignored.txt", b"{fictional")
        self.file("ignored.py", b"raise Exception('DO_NOT_EXECUTE')\n")
        self.file("upper.MD", b"# Fictional\n")
        self.file("upper.JSON", b"{}\n")
        self.assertEqual(self.check()["checked_documents"], 2)

    def test_selected_file_byte_bound_and_large_binary_target_metadata(self):
        exact = b"# Fictional\n"
        self.file("exact.md", exact + b" " * (MAX_BYTES - len(exact)))
        self.file("oversize.json", b" " * (MAX_BYTES + 1))
        binary = self.file("target.bin", b"\xff" * (MAX_BYTES + 1))
        self.file("README.md", "[binary metadata only](target.bin)\n")
        report = self.check(expected=1)
        self.assertEqual(report["checked_documents"], 2)
        self.assertEqual(report["findings"], [dict(path="oversize.json", rule="SIZE_OR_TYPE")])
        self.assertEqual(binary.stat().st_size, MAX_BYTES + 1)

    def test_controlled_child_entry_budget_counts_ignored_entries_and_returns_two(self):
        for name in ("one.txt", "two.txt", "three.txt"):
            self.file(name, b"Fictional ignored file")
        wrapper = self.wrapper("tool.MAX_FILES = 2\n")
        self.check(script=wrapper, expected=2)

    def test_controlled_child_read_failure_is_a_finding_and_omits_private_detail(self):
        self.file("README.md")
        wrapper = self.wrapper("def fail_read(*args):\n    raise OSError('FICTIONAL_PRIVATE_EXCEPTION_DETAIL')\n"
                               "tool._read_text = fail_read\n")
        report = self.check(script=wrapper, expected=1)
        self.assertEqual(report["checked_documents"], 0)
        self.assertEqual(report["findings"], [dict(path="README.md", rule="READ_ERROR")])
        self.assertNotIn("FICTIONAL_PRIVATE_EXCEPTION_DETAIL", json.dumps(report))

    def test_explicit_relative_root_works_from_unrelated_owned_working_directory(self):
        self.file("README.md")
        self.assertEqual(self.check(root=self.docs.relative_to(self.work)), self.check())
        self.assertEqual(self.runtime.parent, self.work)
        self.assertNotEqual(self.work, ROOT)

    def test_native_symlink_root_is_refused(self):
        self.file("README.md")
        link = self.work / "linked root"
        self.symlink(link, self.docs, directory=True)
        self.check(root=link, expected=2)

    def test_native_symlink_source_is_a_finding(self):
        outside = self.work / "outside.json"
        outside.write_bytes(b"{fictional invalid, never parsed")
        self.symlink(self.docs / "linked.json", outside)
        report = self.check(expected=1)
        self.assertEqual(report["checked_documents"], 0)
        self.assertEqual(report["findings"], [dict(path="linked.json", rule="LINK_OR_REPARSE")])

    def test_native_symlink_target_is_refused(self):
        outside = self.work / "outside.bin"
        outside.write_bytes(b"Fictional target, metadata only")
        private = self.docs / "private"
        private.mkdir()
        self.symlink(private / "linked.bin", outside)
        self.file("README.md", "[linked target](private/linked.bin)\n")
        report = self.check(expected=1)
        self.assertEqual(report["findings"], [dict(path="README.md", line=1, rule="MISSING_OR_LINKED_TARGET")])

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_boundaries_and_findings(self):
        from ctypes import wintypes

        target = self.work / "junction target"
        target.mkdir()
        (target / "target.bin").write_bytes(b"Fictional metadata-only target")
        link = self.docs / "junction entry"
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
        self.check(root=link, expected=2)
        self.file("README.md", "[target](junction%20entry/target.bin)\n")
        report = self.check(expected=1)
        self.assertEqual(report["findings"], [dict(path="README.md", line=1, rule="MISSING_OR_LINKED_TARGET"),
                                             dict(path="junction entry", rule="LINK_OR_REPARSE")])
        self.assertEqual(report["checked_documents"], 1)

    @unittest.skipUnless(os.name == "nt", "Native Windows interruption fixture")
    def test_native_windows_interrupt_has_exit_130_and_fixed_status(self):
        self.file("README.md")
        wrapper = self.wrapper("def interrupt(*args):\n    raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT_DETAIL')\n"
                               "tool.check = interrupt\n")
        self.check(script=wrapper, expected=130)


if __name__ == "__main__":
    unittest.main()
