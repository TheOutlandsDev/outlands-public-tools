"""Stdlib-only process tests of copied CLI output and authored fixture DLLs.

OUTLANDS_DOTNET selects an absolute host. OUTLANDS_API_APP_DIR selects its
matching compiled app output; OUTLANDS_API_BEFORE and OUTLANDS_API_AFTER select
the two compiled fictional Example.Plugin fixtures. This suite never builds,
loads a fixture as Python/.NET code, restores packages, or accesses a network.
"""

from collections import Counter
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest


REPORT_FIELDS = {
    "schemaVersion", "scope", "beforeAssembly", "afterAssembly", "beforeSha256",
    "afterSha256", "beforeDeclarations", "afterDeclarations", "changes",
}
MAX_INPUT_BYTES = 32 * 1024 * 1024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Download(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dotnet = Path(os.environ["OUTLANDS_DOTNET"])
        cls.app_source = Path(os.environ["OUTLANDS_API_APP_DIR"])
        cls.before_source = Path(os.environ["OUTLANDS_API_BEFORE"])
        cls.after_source = Path(os.environ["OUTLANDS_API_AFTER"])
        for path in (cls.dotnet, cls.before_source, cls.after_source):
            if not path.is_absolute() or not path.is_file():
                raise RuntimeError("Select existing absolute host and fictional fixture paths")
        if not cls.app_source.is_absolute() or not cls.app_source.is_dir():
            raise RuntimeError("OUTLANDS_API_APP_DIR must select complete absolute app output")
        for name in ("ApiDiff.dll", "ApiDiff.deps.json", "ApiDiff.runtimeconfig.json"):
            if not (cls.app_source / name).is_file():
                raise RuntimeError("The selected compiled application output is incomplete")
        cls.temp_parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT")
                               or os.environ.get("TEMP") or tempfile.gettempdir())
        if not cls.temp_parent.is_absolute() or not cls.temp_parent.is_dir():
            raise RuntimeError("The test temporary parent must already exist and be absolute")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="api-diff-cli-", dir=self.temp_parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied application output"
        shutil.copytree(self.app_source, self.runtime)
        self.assembly = self.runtime / "ApiDiff.dll"
        self.fixtures = self.work / "copied fictional fixtures"
        self.fixtures.mkdir()
        self.before = self.fixtures / "FICTIONAL_PRIVATE_BEFORE.dll"
        self.after = self.fixtures / "FICTIONAL_PRIVATE_AFTER.dll"
        shutil.copyfile(self.before_source, self.before)
        shutil.copyfile(self.after_source, self.after)
        self.retained_before = self.before.read_bytes()
        self.retained_after = self.after.read_bytes()
        self.trap = self.work / "FICTIONAL_PRIVATE_INITIALIZER_TRAP.txt"
        self.environment = os.environ.copy()
        self.environment.update(DOTNET_ROOT=str(self.dotnet.parent), DOTNET_MULTILEVEL_LOOKUP="0",
                                DOTNET_NOLOGO="1", DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1",
                                DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_ADD_GLOBAL_TOOLS_TO_PATH="false",
                                DOTNET_CLI_USE_MSBUILD_SERVER="0", MSBUILDDISABLENODEREUSE="1",
                                OUTLANDS_API_EXECUTION_TRAP=str(self.trap))
        for name in ("DOTNET_ADDITIONAL_DEPS", "DOTNET_SHARED_STORE", "DOTNET_STARTUP_HOOKS"):
            self.environment.pop(name, None)
        self.serial = 0

    def fresh(self, label="fictional", suffix=".json"):
        self.serial += 1
        return self.work / (str(self.serial) + "-" + label + suffix)

    def assert_inputs_preserved(self):
        self.assertEqual(self.before.read_bytes(), self.retained_before)
        self.assertEqual(self.after.read_bytes(), self.retained_after)
        self.assertFalse(self.trap.exists(), "A fictional fixture initializer executed")

    def process(self, *arguments):
        result = subprocess.run([str(self.dotnet), str(self.assembly), *map(str, arguments)],
                                cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=30)
        self.assert_inputs_preserved()
        for private in (str(self.work), str(self.app_source), str(self.before_source), str(self.after_source),
                        "FICTIONAL_PRIVATE_", "OUTLANDS_API_EXECUTION_TRAP", "ExecutionTrap"):
            self.assertNotIn(private, result.stdout + result.stderr)
        return result

    def compare(self, before=None, after=None, output=None, expected=1):
        arguments = ["compare", "--before", self.before if before is None else before,
                     "--after", self.after if after is None else after]
        if output is not None:
            arguments += ["--output", output]
        result = self.process(*arguments)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        if expected == 2:
            self.assertEqual(result.stdout, "")
            self.assertTrue(result.stderr.startswith("Error: "), result.stderr)
            self.assertEqual(len(result.stderr.splitlines()), 1)
            self.assertNotIn('"changes"', result.stderr)
            self.assertNotIn('"schemaVersion"', result.stderr)
            return None
        self.assertEqual(result.stderr, "")
        if output is not None:
            self.assertEqual(result.stdout, "")
            return json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(result.stdout.endswith("\n"))
        return json.loads(result.stdout)

    def symlink(self, path, target, directory=False):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as failure:
            if (os.name == "nt" and getattr(failure, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_API_REQUIRE_NATIVE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_golden_six_changes_have_expected_kinds_and_identities(self):
        report = self.compare()
        self.assertEqual(len(report["changes"]), 6)
        self.assertEqual(Counter(row["kind"] for row in report["changes"]),
                         {"added": 1, "removed": 2, "changed": 3})
        expected = {
            ("field", "Example.Plugin", "Level"): "changed",
            ("method", "Example.Plugin", "Added", 0, ()): "added",
            ("method", "Example.Plugin", "Convert", 0, ("System.Int32",)): "changed",
            ("method", "Example.Plugin", "Removed", 0, ()): "removed",
            ("method", "Example.Plugin", "set_Name", 0, ("System.String",)): "removed",
            ("property", "Example.Plugin", "Name", ()): "changed",
        }
        actual = {}
        for row in report["changes"]:
            parts = json.loads(row["id"])
            identity = tuple(tuple(part) if isinstance(part, list) else part for part in parts)
            actual[identity] = row["kind"]
        self.assertEqual(actual, expected)
        self.assertEqual((report["beforeDeclarations"], report["afterDeclarations"]), (31, 30))
        changes = {json.loads(row["id"])[2]: row for row in report["changes"]}
        self.assertEqual(json.loads(changes["Level"]["before"]), ["System.Int32", 6])
        self.assertEqual(json.loads(changes["Level"]["after"]), ["System.Int64", 6])
        self.assertEqual(json.loads(changes["Convert"]["before"]), ["System.Int32", 32, 1, 134, "[]"])
        self.assertEqual(json.loads(changes["Convert"]["after"]), ["System.Int64", 32, 1, 134, "[]"])
        self.assertEqual(json.loads(changes["Name"]["before"]), ["System.String", 40, 0, True, True])
        self.assertEqual(json.loads(changes["Name"]["after"]), ["System.String", 40, 0, True, False])

    def test_equal_fixture_returns_zero_and_empty_changes(self):
        for path, declarations in ((self.before, 31), (self.after, 30)):
            with self.subTest(fixture=path.name):
                report = self.compare(path, path, expected=0)
                self.assertEqual(report["changes"], [])
                self.assertEqual(report["beforeDeclarations"], declarations)
                self.assertEqual(report["afterDeclarations"], declarations)
                self.assertEqual(report["beforeSha256"], report["afterSha256"])

    def test_reverse_comparison_swaps_sides_and_change_kinds(self):
        forward, reverse = self.compare(), self.compare(self.after, self.before)
        inverse = {"added": "removed", "removed": "added", "changed": "changed"}
        self.assertEqual(reverse["changes"], [dict(kind=inverse[row["kind"]], id=row["id"],
                                                   before=row["after"], after=row["before"])
                                              for row in forward["changes"]])
        self.assertEqual(reverse["beforeSha256"], forward["afterSha256"])
        self.assertEqual(reverse["afterSha256"], forward["beforeSha256"])
        self.assertEqual(reverse["beforeDeclarations"], forward["afterDeclarations"])
        self.assertEqual(reverse["afterDeclarations"], forward["beforeDeclarations"])

    def test_report_version_scope_and_fields_are_explicit(self):
        report = self.compare()
        self.assertEqual(set(report), REPORT_FIELDS)
        self.assertIs(type(report["schemaVersion"]), int)
        self.assertEqual(report["schemaVersion"], 1)
        self.assertEqual(report["scope"], "public-declarations-only")
        self.assertEqual((report["beforeAssembly"], report["afterAssembly"]),
                         ("Example.Plugin", "Example.Plugin"))
        for row in report["changes"]:
            self.assertEqual(set(row), {"kind", "id", "before", "after"})

    def test_report_uses_ordinal_order_and_nested_json_values(self):
        report = self.compare()
        ids = [row["id"] for row in report["changes"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(set(ids)), 6)
        for row in report["changes"]:
            self.assertIsInstance(json.loads(row["id"]), list)
            for side in ("before", "after"):
                if row[side] is not None:
                    self.assertIsInstance(row[side], str)
                    self.assertIsInstance(json.loads(row[side]), list)
            self.assertEqual(row["before"] is None, row["kind"] == "added")
            self.assertEqual(row["after"] is None, row["kind"] == "removed")

    def test_hashes_cover_exact_copied_input_bytes_without_private_paths(self):
        report = self.compare()
        self.assertEqual(report["beforeSha256"], hashlib.sha256(self.retained_before).hexdigest())
        self.assertEqual(report["afterSha256"], hashlib.sha256(self.retained_after).hexdigest())
        for field in ("beforeSha256", "afterSha256"):
            self.assertRegex(report[field], r"^[0-9a-f]{64}$")
        text = json.dumps(report)
        self.assertNotIn("timestamp", text.lower())
        self.assertNotIn(str(self.work), text)

    def test_new_report_is_utf8_without_bom_and_has_final_newline(self):
        output = self.fresh()
        expected = self.compare()
        self.assertEqual(self.compare(output=output), expected)
        data = output.read_bytes()
        self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(data.endswith(b"\n"))
        self.assertEqual(json.loads(data.decode("utf-8", errors="strict")), expected)

    def test_equal_report_file_returns_zero(self):
        output = self.fresh()
        report = self.compare(self.before, self.before, output=output, expected=0)
        self.assertEqual(report["changes"], [])
        self.assertEqual(report["beforeSha256"], digest(self.before))

    def test_repeated_comparisons_are_byte_deterministic(self):
        one = self.process("compare", "--before", self.before, "--after", self.after)
        two = self.process("compare", "--before", self.before, "--after", self.after)
        self.assertEqual((one.returncode, two.returncode), (1, 1))
        self.assertEqual(one.stdout, two.stdout)
        self.assertEqual(one.stderr, two.stderr)

    def test_fictional_module_initializers_never_run_in_actual_cli(self):
        self.assertFalse(self.trap.exists())
        self.compare()
        self.compare(self.after, self.before)
        self.compare(self.before, self.before, expected=0)
        bad = self.fresh("invalid", ".dll")
        bad.write_bytes(b"Fictional invalid assembly, never executable.\n")
        self.compare(bad, self.after, expected=2)
        self.assertFalse(self.trap.exists())

    def test_copied_app_and_fixture_outputs_have_no_intermediate_dependency(self):
        first_runtime, first_fixtures = self.runtime, self.fixtures
        second_runtime = self.work / "independent second application copy"
        second_fixtures = self.work / "independent second fixture copy"
        inventory = {p.relative_to(first_runtime): digest(p) for p in first_runtime.rglob("*") if p.is_file()}
        shutil.copytree(first_runtime, second_runtime)
        shutil.copytree(first_fixtures, second_fixtures)
        shutil.rmtree(first_runtime)
        shutil.rmtree(first_fixtures)
        self.runtime, self.fixtures = second_runtime, second_fixtures
        self.assembly = second_runtime / "ApiDiff.dll"
        self.before = second_fixtures / self.before.name
        self.after = second_fixtures / self.after.name
        self.environment.update(OUTLANDS_API_APP_DIR=str(first_runtime),
                                OUTLANDS_API_BEFORE=str(first_fixtures / "absent-before.dll"),
                                OUTLANDS_API_AFTER=str(first_fixtures / "absent-after.dll"))
        self.assertFalse(first_runtime.exists() or first_fixtures.exists())
        self.assertEqual(inventory, {p.relative_to(second_runtime): digest(p)
                                     for p in second_runtime.rglob("*") if p.is_file()})
        self.assertEqual(len(self.compare()["changes"]), 6)
        self.assertEqual(sorted(p.name for p in second_fixtures.iterdir()),
                         ["FICTIONAL_PRIVATE_AFTER.dll", "FICTIONAL_PRIVATE_BEFORE.dll"])

    def test_selected_inputs_are_unchanged_after_stdout_and_file_reports(self):
        self.compare()
        self.compare(output=self.fresh())
        self.compare(self.after, self.before)
        self.assert_inputs_preserved()

    def test_existing_report_is_never_overwritten(self):
        output = self.fresh()
        retained = b"Fictional retained report bytes.\n"
        output.write_bytes(retained)
        self.compare(output=output, expected=2)
        self.assertEqual(output.read_bytes(), retained)

    def test_neither_selected_input_can_be_used_as_output(self):
        for output in (self.before, self.after):
            with self.subTest(output=output.name):
                self.compare(output=output, expected=2)
                self.assert_inputs_preserved()

    def test_invalid_input_emits_no_comparison_or_report_file(self):
        invalid = self.fresh("invalid", ".dll")
        invalid.write_bytes(b"Fictional invalid binary.\n")
        for before, after in ((invalid, self.after), (self.before, invalid)):
            with self.subTest(side="before" if before == invalid else "after"):
                output = self.fresh()
                self.compare(before, after, output=output, expected=2)
                self.assertFalse(output.exists())
                self.assertEqual(invalid.read_bytes(), b"Fictional invalid binary.\n")

    def test_empty_malformed_and_native_looking_invalid_bytes_are_refused(self):
        cases = [b"", b"Fictional plain text, not a managed image.\n",
                 b"MZ\x90\x00Fictional malformed native-looking image.\x00",
                 self.retained_before[:64], b"\xff\xfe\x00\x01"]
        for data in cases:
            with self.subTest(size=len(data), prefix=data[:4]):
                invalid = self.fresh("invalid", ".dll")
                invalid.write_bytes(data)
                self.compare(invalid, self.after, expected=2)
                self.assertEqual(invalid.read_bytes(), data)

    def test_oversized_fictional_file_is_refused_before_parsing(self):
        invalid = self.fresh("too-large", ".dll")
        with invalid.open("xb") as stream:
            stream.truncate(MAX_INPUT_BYTES + 1)
        before = invalid.stat()
        output = self.fresh()
        self.compare(invalid, self.after, output=output, expected=2)
        self.assertEqual(invalid.stat().st_size, before.st_size)
        self.assertEqual(invalid.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertFalse(output.exists())

    def test_unknown_duplicate_incomplete_and_missing_arguments_return_two(self):
        for arguments in (("fictional-command",), ("compare", "--unknown", "fictional"),
                          ("compare", "--before", self.before, "--before", self.after),
                          ("compare", "--before"), ("compare", "--after", self.after),
                          ("compare", "--before", self.before), ("compare",)):
            with self.subTest(arguments=arguments):
                result = self.process(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr.startswith("Error: "))
                self.assertNotIn('"changes"', result.stderr)

    def test_missing_and_directory_inputs_are_refused(self):
        for invalid in (self.fresh("missing", ".dll"), self.work):
            with self.subTest(kind="directory" if invalid == self.work else "missing"):
                self.compare(invalid, self.after, expected=2)
                self.compare(self.before, invalid, expected=2)

    def test_output_parent_must_exist_and_directory_output_is_refused(self):
        parent = self.work / "missing fictional report parent"
        self.compare(output=parent / "report.json", expected=2)
        self.assertFalse(parent.exists())
        self.compare(output=self.fixtures, expected=2)
        self.assert_inputs_preserved()

    def test_control_network_and_windows_stream_paths_are_refused_by_cli(self):
        # Literal path strings reach only the CLI; the fixture code never probes
        # these nonexistent network/device paths with stat(), exists(), or open().
        paths = [str(self.work) + os.sep + "FICTIONAL_PRIVATE_\ninvalid.dll",
                 r"\\fictional.invalid\authored\not-an-input.dll", "//fictional.invalid/authored/not-an-input.dll"]
        if os.name == "nt":
            paths += [r"\\?\C:\fictional\not-an-input.dll", str(self.before) + ":fictional-stream"]
        for invalid in paths:
            with self.subTest(path=repr(invalid)):
                self.compare(invalid, self.after, expected=2)
        output = str(self.work) + os.sep + "FICTIONAL_PRIVATE_\ninvalid.json"
        self.compare(output=output, expected=2)

    def test_help_has_no_input_defaults_and_writes_no_files(self):
        before = sorted(p.relative_to(self.work).as_posix() for p in self.work.rglob("*"))
        for arguments in ((), ("--help",)):
            with self.subTest(arguments=arguments):
                result = self.process(*arguments)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, "")
                self.assertIn("trusted build artifacts only", result.stdout)
                self.assertIn("Exit 0 equal; 1 declarations differ; 2", result.stdout)
        self.assertEqual(before, sorted(p.relative_to(self.work).as_posix() for p in self.work.rglob("*")))

    def test_option_order_and_selected_relative_paths_preserve_report(self):
        expected = self.compare()
        result = self.process("compare", "--after", self.after.relative_to(self.work),
                              "--before", self.before.relative_to(self.work))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), expected)

    def test_equal_declarations_can_have_different_exact_input_hashes(self):
        # A harmless authored overlay is outside the PE metadata declaration
        # surface. This checks the stated comparison boundary through the CLI.
        overlay = self.fresh("fictional-overlay", ".dll")
        overlay.write_bytes(self.retained_before + b"\nFictional non-metadata overlay.\n")
        report = self.compare(self.before, overlay, expected=0)
        self.assertEqual(report["changes"], [])
        self.assertEqual(report["beforeDeclarations"], report["afterDeclarations"])
        self.assertEqual(report["beforeSha256"], digest(self.before))
        self.assertEqual(report["afterSha256"], digest(overlay))
        self.assertNotEqual(report["beforeSha256"], report["afterSha256"])

    def test_native_symlink_leaf_input_is_refused(self):
        link = self.fresh("input-link", ".dll")
        self.symlink(link, self.before)
        self.compare(link, self.after, expected=2)

    def test_native_symlink_input_parent_is_refused(self):
        link = self.work / "linked fixture parent"
        self.symlink(link, self.fixtures, directory=True)
        self.compare(link / self.before.name, self.after, expected=2)

    def test_native_symlink_output_parent_is_refused(self):
        target = self.work / "real output parent"
        target.mkdir()
        link = self.work / "linked output parent"
        self.symlink(link, target, directory=True)
        self.compare(output=link / "fictional-report.json", expected=2)
        self.assertEqual(list(target.iterdir()), [])

    def test_native_symlink_leaf_output_preserves_targets(self):
        retained = self.fresh("retained")
        retained.write_bytes(b"Fictional retained target.\n")
        dangling_target = self.fresh("absent-target")
        # Fixture creation stays outside subTest so an unavailable Windows
        # privilege skips this one test exactly once, with a stable test ID.
        link = self.fresh("existing-output-link")
        self.symlink(link, retained)
        self.compare(output=link, expected=2)
        self.assertTrue(link.is_symlink())
        dangling_link = self.fresh("dangling-output-link")
        self.symlink(dangling_link, dangling_target)
        self.compare(output=dangling_link, expected=2)
        self.assertTrue(dangling_link.is_symlink())
        self.assertEqual(retained.read_bytes(), b"Fictional retained target.\n")
        self.assertFalse(dangling_target.exists())

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_input_and_output_parent_are_refused(self):
        from ctypes import wintypes

        target = self.work / "real junction parent"
        target.mkdir()
        fixture = target / "fictional.dll"
        fixture.write_bytes(self.retained_before)
        link = self.work / "junction parent"
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
        self.compare(link / fixture.name, self.after, expected=2)
        self.compare(output=link / "new-report.json", expected=2)
        self.assertEqual(sorted(path.name for path in target.iterdir()), [fixture.name])
        self.assertEqual(fixture.read_bytes(), self.retained_before)


if __name__ == "__main__":
    unittest.main()
