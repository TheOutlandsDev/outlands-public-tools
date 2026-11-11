"""Stdlib-only process qualification of an explicitly selected compiled app.

Set OUTLANDS_DOTNET to an absolute dotnet host and OUTLANDS_HASH_APP_DIR to
the complete compiled application output. No build, package restore, network,
repository assembly, real journal, or in-process CLI substitute is used here.
"""

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


ROOT = Path(__file__).resolve().parents[1]
ZERO = "0" * 64
FIRST_TEXT = "Fictional build prepared."
SECOND_TEXT = "Fictional checks passed."
FIRST_HEAD = "66a82dd6cfc9760a7b9d754525fe693e9d63ca60e427e3d1d2bd25a4c61c398e"
SECOND_HEAD = "ec91f00284e1d0faccd7f3301ae23ae7af1c8eed6121cab890dd1648d9f33d36"
MAX_BYTES = 1_048_576
MAX_LINE_BYTES = 65_536
MAX_TEXT_BYTES = 8_192


def record(sequence, previous, text):
    """Independent implementation of the published version-one hash message."""
    material = ("outlands-hash-journal-v1\n" + str(sequence) + "\n" + previous + "\n" + text)
    return dict(schema=1, sequence=sequence, previous=previous, text=text,
                hash=hashlib.sha256(material.encode("utf-8", errors="strict")).hexdigest())


def encode(records):
    return b"".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
                    for item in records)


def fictional_chain(count=2, text=None):
    records = []
    previous = ZERO
    for sequence in range(1, count + 1):
        value = text if text is not None else (FIRST_TEXT if sequence == 1 else SECOND_TEXT)
        item = record(sequence, previous, value)
        records.append(item)
        previous = item["hash"]
    return records


class Download(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dotnet = Path(os.environ["OUTLANDS_DOTNET"])
        cls.app_source = Path(os.environ["OUTLANDS_HASH_APP_DIR"])
        if not cls.dotnet.is_absolute() or not cls.dotnet.is_file():
            raise RuntimeError("OUTLANDS_DOTNET must select an existing absolute dotnet host")
        if not cls.app_source.is_absolute() or not cls.app_source.is_dir():
            raise RuntimeError("OUTLANDS_HASH_APP_DIR must select an existing absolute output directory")
        for name in ("Outlands.HashJournal.dll", "Outlands.HashJournal.deps.json",
                     "Outlands.HashJournal.runtimeconfig.json"):
            if not (cls.app_source / name).is_file():
                raise RuntimeError("Selected application output is incomplete")
        cls.temp_parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT")
                               or os.environ.get("TEMP") or tempfile.gettempdir())
        if not cls.temp_parent.is_absolute() or not cls.temp_parent.is_dir():
            raise RuntimeError("The selected test temporary parent must already exist and be absolute")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hash-journal-cli-", dir=self.temp_parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied application output"
        shutil.copytree(self.app_source, self.runtime)
        self.assembly = self.runtime / "Outlands.HashJournal.dll"
        self.environment = os.environ.copy()
        self.environment.update(DOTNET_ROOT=str(self.dotnet.parent),
                                DOTNET_MULTILEVEL_LOOKUP="0", DOTNET_NOLOGO="1",
                                DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1",
                                DOTNET_CLI_TELEMETRY_OPTOUT="1",
                                DOTNET_ADD_GLOBAL_TOOLS_TO_PATH="false",
                                DOTNET_CLI_USE_MSBUILD_SERVER="0",
                                MSBUILDDISABLENODEREUSE="1")
        # External injection settings are irrelevant to this isolated copied app.
        for name in ("DOTNET_ADDITIONAL_DEPS", "DOTNET_SHARED_STORE", "DOTNET_STARTUP_HOOKS"):
            self.environment.pop(name, None)
        self.serial = 0

    def fresh(self, label="fictional"):
        self.serial += 1
        return self.work / (str(self.serial) + "-" + label + ".jsonl")

    def fixture(self, data=None):
        path = self.fresh()
        path.write_bytes(encode(fictional_chain()) if data is None else data)
        return path

    def process(self, *arguments):
        return subprocess.run([str(self.dotnet), str(self.assembly), *map(str, arguments)],
                              cwd=self.work, env=self.environment, capture_output=True,
                              text=True, encoding="utf-8", errors="strict", timeout=30)

    def cli(self, *arguments, error=None):
        result = self.process(*arguments)
        self.assertEqual(result.returncode, 0 if error is None else 2,
                         result.stdout + result.stderr)
        # Metadata and fixed error codes must not disclose either selected path.
        for selected in (str(self.work), str(self.app_source), str(self.assembly)):
            self.assertNotIn(selected, result.stdout)
            self.assertNotIn(selected, result.stderr)
        if error is not None:
            self.assertEqual(result.stdout, "")
            self.assertEqual(len(result.stderr.splitlines()), 1)
            response = json.loads(result.stderr)
            self.assertEqual(response, {"status": "ERROR", "code": error})
        else:
            self.assertEqual(result.stderr, "")
            self.assertEqual(len(result.stdout.splitlines()), 1)
            response = json.loads(result.stdout)
        return response

    def verify(self, path, error=None, head=None, count=None):
        before = path.read_bytes() if path.is_file() else None
        arguments = ["verify", "--input", path]
        if head is not None:
            arguments += ["--expected-head", head]
        if count is not None:
            arguments += ["--expected-count", str(count)]
        response = self.cli(*arguments, error=error)
        if before is not None:
            self.assertEqual(path.read_bytes(), before)
        return response

    def assert_report(self, response, command, count, head, anchored=False, expected_count=False):
        self.assertEqual(response, dict(status="VALID_HEAD_MATCHED" if anchored else "VALID_UNANCHORED",
                                        command=command, count=count, head=head,
                                        anchor="HEAD_MATCHED" if anchored else "UNANCHORED",
                                        expectedCountMatched=True if expected_count else None,
                                        outputWritten=command != "verify"))

    def symlink(self, path, target, directory=False):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as failure:
            if (os.name == "nt" and getattr(failure, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_HASH_REQUIRE_NATIVE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_create_append_verify_golden_and_preserves_input(self):
        first, second = self.fresh(), self.fresh()
        self.assertEqual(record(1, ZERO, FIRST_TEXT)["hash"], FIRST_HEAD)
        self.assertEqual(record(2, FIRST_HEAD, SECOND_TEXT)["hash"], SECOND_HEAD)
        self.assert_report(self.cli("create", "--output", first, "--text", FIRST_TEXT),
                           "create", 1, FIRST_HEAD)
        self.assertEqual(first.read_bytes(), encode(fictional_chain(1)))
        retained = first.read_bytes()
        self.assert_report(self.cli("append", "--input", first, "--output", second,
                                    "--text", SECOND_TEXT), "append", 2, SECOND_HEAD)
        self.assertEqual(first.read_bytes(), retained)
        self.assertEqual(second.read_bytes(), encode(fictional_chain()))
        self.assert_report(self.verify(second, head=SECOND_HEAD, count=2),
                           "verify", 2, SECOND_HEAD, anchored=True, expected_count=True)

    def test_public_example_matches_independent_golden(self):
        example = (ROOT / "examples" / "two-record.jsonl").read_bytes()
        self.assertEqual(example, encode(fictional_chain()))
        self.assert_report(self.verify(self.fixture(example), head=SECOND_HEAD, count=2),
                           "verify", 2, SECOND_HEAD, anchored=True, expected_count=True)

    def test_success_and_error_redact_paths_and_text(self):
        marker = "FICTIONAL_PRIVATE_TEXT_7f2d"
        selected = self.work / "FICTIONAL_PRIVATE_PATH_7f2d.jsonl"
        result = self.process("create", "--output", selected, "--text", marker)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["head"], record(1, ZERO, marker)["hash"])
        for args in (("create", "--output", selected, "--text", marker),
                     ("verify", "--input", self.work / "FICTIONAL_PRIVATE_MISSING_7f2d"),
                     ("FICTIONAL_PRIVATE_COMMAND_7f2d", "--text", marker)):
            failed = self.process(*args)
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(failed.stdout, "")
            self.assertEqual(set(json.loads(failed.stderr)), {"status", "code"})
            for secret in (marker, "FICTIONAL_PRIVATE_", str(self.work)):
                self.assertNotIn(secret, failed.stdout + failed.stderr)
        self.assertEqual(result.stderr, "")
        self.assertNotIn(marker, result.stdout)
        self.assertNotIn("FICTIONAL_PRIVATE_", result.stdout)
        self.assertNotIn(str(self.work), result.stdout)

    def test_demo_and_help_are_explicit_and_write_nothing(self):
        before = sorted(p.relative_to(self.work).as_posix() for p in self.work.rglob("*"))
        for args in ((), ("--help",), ("help",)):
            with self.subTest(args=args):
                result = self.process(*args)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, "")
                self.assertIn("No input/output defaults. Fresh output files only.", result.stdout)
                self.assertNotIn(str(self.work), result.stdout)
        response = self.cli("demo")
        self.assertIs(response["simulated"], True)
        self.assertIs(response["writes"], False)
        self.assertEqual(response["records"], fictional_chain())
        self.assertEqual((response["count"], response["head"], response["anchor"]),
                         (2, SECOND_HEAD, "UNANCHORED"))
        self.assertEqual(before, sorted(p.relative_to(self.work).as_posix() for p in self.work.rglob("*")))

    def test_copied_output_runs_independently_of_removed_intermediate(self):
        original_copy = self.runtime
        moved_copy = self.work / "independent second copy"
        expected = {p.relative_to(original_copy): hashlib.sha256(p.read_bytes()).digest()
                    for p in original_copy.rglob("*") if p.is_file()}
        shutil.copytree(original_copy, moved_copy)
        shutil.rmtree(original_copy)
        self.runtime = moved_copy
        self.assembly = moved_copy / "Outlands.HashJournal.dll"
        self.environment["OUTLANDS_HASH_APP_DIR"] = str(original_copy)
        self.assertFalse(original_copy.exists())
        self.assertEqual(expected, {p.relative_to(moved_copy): hashlib.sha256(p.read_bytes()).digest()
                                    for p in moved_copy.rglob("*") if p.is_file()})
        output = self.fresh()
        self.assert_report(self.cli("create", "--output", output, "--text", FIRST_TEXT),
                           "create", 1, FIRST_HEAD)
        self.assert_report(self.verify(output, head=FIRST_HEAD), "verify", 1, FIRST_HEAD, anchored=True)

    def test_text_mutation_is_refused_with_and_without_anchors(self):
        records = fictional_chain()
        records[0]["text"] = "Fictional changed event."
        path = self.fixture(encode(records))
        for options in ({}, {"head": SECOND_HEAD}, {"count": 2}, {"head": SECOND_HEAD, "count": 2}):
            with self.subTest(options=options):
                self.verify(path, error="HASH_MISMATCH", **options)

    def test_reordering_is_refused_with_and_without_anchors(self):
        path = self.fixture(encode(list(reversed(fictional_chain()))))
        for options in ({}, {"head": SECOND_HEAD}, {"count": 2}, {"head": SECOND_HEAD, "count": 2}):
            with self.subTest(options=options):
                self.verify(path, error="SEQUENCE_MISMATCH", **options)

    def test_valid_prefix_truncation_needs_separately_retained_head_or_count(self):
        # These anchors are retained constants, never taken from the truncated input.
        path = self.fixture(encode(fictional_chain(1)))
        self.assert_report(self.verify(path), "verify", 1, FIRST_HEAD)
        self.verify(path, head=SECOND_HEAD, error="EXPECTED_HEAD_MISMATCH")
        self.verify(path, count=2, error="EXPECTED_COUNT_MISMATCH")
        self.verify(path, head=SECOND_HEAD, count=2, error="EXPECTED_HEAD_MISMATCH")

    def test_complete_rewrite_needs_external_head_even_with_same_count(self):
        replacement = fictional_chain(text="Different fictional events.")
        path = self.fixture(encode(replacement))
        self.assert_report(self.verify(path, count=2), "verify", 2, replacement[-1]["hash"],
                           expected_count=True)
        self.verify(path, head=SECOND_HEAD, count=2, error="EXPECTED_HEAD_MISMATCH")

    def test_strict_jsonl_framing(self):
        good = encode(fictional_chain(1))
        for data, code in ((good[:-1], "FINAL_LF_REQUIRED"),
                           (good.replace(b"\n", b"\r\n"), "CRLF_UNSUPPORTED"),
                           (good + b"\n", "LINE_BYTE_LIMIT"),
                           (b"\n" + good, "LINE_BYTE_LIMIT"),
                           (b"\xef\xbb\xbf" + good, "BOM_UNSUPPORTED")):
            with self.subTest(code=code, prefix=data[:3]):
                self.verify(self.fixture(data), error=code)

    def test_strict_utf8_and_escaped_surrogates(self):
        for data, code in ((b"\xff\n", "INVALID_UTF8"), (b"\xc0\xaf\n", "INVALID_UTF8"),
                           (b"\xed\xa0\x80\n", "INVALID_UTF8")):
            with self.subTest(data=data):
                self.verify(self.fixture(data), error=code)
        invalid = encode(fictional_chain(1)).replace(FIRST_TEXT.encode(), b"\\ud800")
        self.verify(self.fixture(invalid), error="INVALID_JSON_TEXT")

    def test_strict_json_objects_properties_and_depth(self):
        good = encode(fictional_chain(1))
        for data, code in ((b"{broken\n", "INVALID_JSON"), (b"[]\n", "RECORD_OBJECT_REQUIRED"),
                           (good.replace(b'"schema":1', b'"schema":1,"schema":1'), "DUPLICATE_PROPERTY"),
                           (good.replace(b'"schema":1', b'"schema":1,"extra":1'), "UNKNOWN_PROPERTY"),
                           (good.replace(b'"schema":1,', b""), "MISSING_PROPERTY"),
                           (b'{"extra":' + b"[" * 9 + b"0" + b"]" * 9 + b"}\n", "INVALID_JSON"),
                           (good[:-2] + b",}\n", "INVALID_JSON"),
                           (b"//comment\n" + good, "INVALID_JSON")):
            with self.subTest(code=code, data=data[:50]):
                self.verify(self.fixture(data), error=code)

    def test_strict_schema_sequence_hash_and_property_types(self):
        good = encode(fictional_chain(1))
        cases = [(b'"schema":1', b'"schema":' + token, "UNSUPPORTED_SCHEMA")
                 for token in (b"2", b"1.0", b"1e0", b"true")]
        cases += [(b'"sequence":1', b'"sequence":' + token, "INVALID_SEQUENCE")
                  for token in (b"1.0", b"1e0", b"true", b"2147483648")]
        cases += [(b'"sequence":1', b'"sequence":2', "SEQUENCE_MISMATCH"),
                  (b'"sequence":1', b'"sequence":NaN', "INVALID_JSON"),
                  (b'"previous":"' + ZERO.encode() + b'"', b'"previous":null', "STRING_PROPERTY_REQUIRED"),
                  (FIRST_HEAD.encode(), FIRST_HEAD.upper().encode(), "INVALID_HASH"),
                  (ZERO.encode(), b"f" * 64, "PREVIOUS_MISMATCH")]
        for old, new, code in cases:
            with self.subTest(new=new, code=code):
                self.verify(self.fixture(good.replace(old, new)), error=code)

    def test_text_utf8_byte_boundary_is_independent_of_character_count(self):
        text = "\u00e9" * (MAX_TEXT_BYTES // 2)
        output = self.fresh()
        response = self.cli("create", "--output", output, "--text", text)
        self.assertEqual(response["head"], record(1, ZERO, text)["hash"])
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["text"], text)
        self.assert_report(self.verify(output), "verify", 1, response["head"])
        refused = self.fresh()
        self.cli("create", "--output", refused, "--text", text + "\u00e9", error="TEXT_BYTE_LIMIT")
        self.assertFalse(refused.exists())
        oversized = self.fixture(encode([record(1, ZERO, text + "\u00e9")]))
        self.verify(oversized, error="TEXT_BYTE_LIMIT")

    def test_input_and_line_byte_boundaries(self):
        line = encode(fictional_chain(1))[:-1]
        exact_line = line + b" " * (MAX_LINE_BYTES - len(line)) + b"\n"
        self.assert_report(self.verify(self.fixture(exact_line)), "verify", 1, FIRST_HEAD)
        self.verify(self.fixture(exact_line[:-1] + b" \n"), error="LINE_BYTE_LIMIT")
        records = fictional_chain(16)
        lines = encode(records).splitlines()
        exact_file = b"".join(line + b" " * (65_535 - len(line)) + b"\n" for line in lines)
        self.assertEqual(len(exact_file), MAX_BYTES)
        self.assert_report(self.verify(self.fixture(exact_file)), "verify", 16, records[-1]["hash"])
        self.verify(self.fixture(exact_file + b"\n"), error="INPUT_BYTE_LIMIT")
        self.verify(self.fixture(b""), error="INPUT_BYTE_LIMIT")

    def test_output_byte_bound_is_checked_before_new_file_creation(self):
        text = "x" * MAX_TEXT_BYTES
        records = []
        previous = ZERO
        while True:
            candidate = record(len(records) + 1, previous, text)
            if len(encode(records + [candidate])) > MAX_BYTES:
                break
            records.append(candidate)
            previous = candidate["hash"]
        source = self.fixture(encode(records))
        before = source.read_bytes()
        output = self.fresh()
        self.cli("append", "--input", source, "--output", output, "--text", text,
                 error="OUTPUT_BYTE_LIMIT")
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse(output.exists())

    def test_expected_head_and_count_arguments_are_strict(self):
        path = self.fixture()
        for head in ("not-a-hash", SECOND_HEAD.upper(), ZERO[:-1]):
            with self.subTest(head=head):
                self.verify(path, head=head, error="INVALID_EXPECTED_HEAD")
        for count in ("0", "10001", "+2", " 2", "2.0", "2e0", "-1", "2147483648"):
            with self.subTest(count=count):
                self.verify(path, count=count, error="INVALID_EXPECTED_COUNT")

    def test_existing_output_and_input_as_output_are_never_overwritten(self):
        source = self.fixture()
        existing = self.fixture(b"Fictional retained output.\n")
        for path in (source, existing):
            with self.subTest(output=path.name):
                retained = path.read_bytes()
                self.cli("create", "--output", path, "--text", FIRST_TEXT, error="OUTPUT_EXISTS")
                self.cli("append", "--input", source, "--output", path,
                         "--text", FIRST_TEXT, error="OUTPUT_EXISTS")
                self.assertEqual(path.read_bytes(), retained)

    def test_corrupt_append_creates_no_output(self):
        source = self.fixture(b"Fictional invalid JSON.\n")
        output = self.fresh()
        retained = source.read_bytes()
        self.cli("append", "--input", source, "--output", output, "--text", SECOND_TEXT,
                 error="INVALID_JSON")
        self.assertFalse(output.exists())
        self.assertEqual(source.read_bytes(), retained)

    def test_relative_ambiguous_and_missing_parent_paths_are_refused(self):
        self.cli("verify", "--input", "relative-fictional.jsonl", error="ABSOLUTE_PATH_REQUIRED")
        self.cli("create", "--output", "relative-fictional.jsonl", "--text", FIRST_TEXT,
                 error="ABSOLUTE_PATH_REQUIRED")
        ambiguous = str(self.work) + os.sep + "." + os.sep + "fictional.jsonl"
        self.cli("create", "--output", ambiguous, "--text", FIRST_TEXT, error="AMBIGUOUS_PATH")
        missing = self.work / "missing fictional parent"
        self.cli("create", "--output", missing / "fictional.jsonl", "--text", FIRST_TEXT,
                 error="PARENT_DIRECTORY_REQUIRED")
        self.assertFalse(missing.exists())
        self.assertFalse((self.work / "relative-fictional.jsonl").exists())

    def test_selected_inputs_are_regular_files_and_windows_paths_are_local(self):
        self.verify(self.work, error="REGULAR_FILE_REQUIRED")
        self.verify(self.fresh(), error="INPUT_UNAVAILABLE")
        self.cli("create", "--output", self.work, "--text", FIRST_TEXT,
                 error="REGULAR_FILE_REQUIRED")
        if os.name == "nt":
            for path in (r"\\fictional.invalid\fictional\journal.jsonl",
                         r"\\?\C:\fictional\journal.jsonl"):
                with self.subTest(path=path):
                    self.cli("verify", "--input", path, error="NETWORK_OR_DEVICE_PATH")
            self.cli("verify", "--input", str(self.fresh()) + ":fictional",
                     error="ALTERNATE_STREAM_UNSUPPORTED")

    def test_unknown_duplicate_missing_arguments_are_refused(self):
        for arguments, code in ((("fictional-unknown-command",), "UNKNOWN_COMMAND"),
                                (("verify", "--unknown", "fictional"), "INVALID_ARGUMENTS"),
                                (("verify", "--input", "a", "--input", "b"), "INVALID_ARGUMENTS"),
                                (("create", "--output"), "INVALID_ARGUMENTS"),
                                (("create", "--text", FIRST_TEXT), "MISSING_ARGUMENT"),
                                (("verify",), "MISSING_ARGUMENT")):
            with self.subTest(arguments=arguments):
                self.cli(*arguments, error=code)

    def test_verify_and_append_preserve_selected_input_bytes(self):
        records = fictional_chain()
        # Noncanonical whitespace and member order are retained in the old version.
        data = b"".join(json.dumps(dict(reversed(list(item.items()))), ensure_ascii=True,
                                  separators=(", ", ": ")).encode() + b"\n" for item in records)
        source = self.fixture(data)
        self.assert_report(self.verify(source), "verify", 2, SECOND_HEAD)
        output = self.fresh()
        text = "Fictional third event."
        expected = record(3, SECOND_HEAD, text)
        self.assert_report(self.cli("append", "--input", source, "--output", output, "--text", text),
                           "append", 3, expected["hash"])
        self.assertEqual(source.read_bytes(), data)
        self.assertEqual(output.read_bytes(), encode(records + [expected]))

    def test_unicode_escaping_member_order_and_exact_text_hash_semantics(self):
        text = "Fictional\nline \"quoted\"\rreturn \u00e9"
        output = self.fresh()
        self.cli("create", "--output", output, "--text", text)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), record(1, ZERO, text))
        self.assertNotIn(b"\r", output.read_bytes())
        self.assertEqual(output.read_bytes().count(b"\n"), 1)
        escaped = json.dumps(dict(reversed(list(record(1, ZERO, text).items()))), ensure_ascii=True)
        self.assert_report(self.verify(self.fixture((escaped + "\n").encode())),
                           "verify", 1, record(1, ZERO, text)["hash"])
        heads = []
        for value in ("\u00e9", "e\u0301"):
            selected = self.fresh()
            heads.append(self.cli("create", "--output", selected, "--text", value)["head"])
            self.assertEqual(heads[-1], record(1, ZERO, value)["hash"])
        self.assertNotEqual(*heads)

    def test_expected_count_alone_remains_unanchored(self):
        self.assert_report(self.verify(self.fixture(), count=2), "verify", 2, SECOND_HEAD,
                           expected_count=True)

    def test_empty_and_blank_text_create_no_output(self):
        for text in ("", " \t\n", "\u2003"):
            with self.subTest(text=repr(text)):
                output = self.fresh()
                self.cli("create", "--output", output, "--text", text, error="EMPTY_TEXT")
                self.assertFalse(output.exists())

    def test_native_symlink_leaf_input_is_refused(self):
        source = self.fixture()
        retained = source.read_bytes()
        link = self.fresh("symlink")
        self.symlink(link, source)
        self.verify(link, error="LINKED_PATH")
        self.assertEqual(source.read_bytes(), retained)

    def test_native_symlink_input_parent_is_refused(self):
        target = self.work / "real input parent"
        target.mkdir()
        source = target / "fictional.jsonl"
        source.write_bytes(encode(fictional_chain()))
        link = self.work / "linked input parent"
        self.symlink(link, target, directory=True)
        self.verify(link / source.name, error="LINKED_PATH")
        self.assertEqual(source.read_bytes(), encode(fictional_chain()))

    def test_native_symlink_output_parent_is_refused(self):
        target = self.work / "real output parent"
        target.mkdir()
        link = self.work / "linked output parent"
        self.symlink(link, target, directory=True)
        self.cli("create", "--output", link / "fictional.jsonl", "--text", FIRST_TEXT,
                 error="LINKED_PATH")
        self.assertEqual(list(target.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_input_and_output_parent_are_refused(self):
        # Native mount-point reparse data avoids a shell, administrative changes,
        # external fixture tools, and interpretation of parent-directory text.
        from ctypes import wintypes

        target = self.work / "real junction parent"
        target.mkdir()
        source = target / "fictional.jsonl"
        source.write_bytes(encode(fictional_chain()))
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
        self.verify(link / source.name, error="LINKED_PATH")
        self.cli("create", "--output", link / "new-fictional.jsonl", "--text", FIRST_TEXT,
                 error="LINKED_PATH")
        self.assertEqual(sorted(path.name for path in target.iterdir()), [source.name])
        self.assertEqual(source.read_bytes(), encode(fictional_chain()))


if __name__ == "__main__":
    unittest.main()
