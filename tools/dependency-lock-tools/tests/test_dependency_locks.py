"""Synthetic reports/locks only; no package artifact, resolver or installer."""
import contextlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import lock_common as common
import report_to_lock as converter
import verify_locks as verifier


HASH_A, HASH_B = "a" * 64, "b" * 64


def item(name="demo-package", version="1.2.3", digest=HASH_A):
    return {"metadata": {"name": name, "version": version},
            "download_info": {"archive_info": {"hashes": {"sha256": digest}}}}


def report(*items):
    return {"version": "1", "install": list(items or (item(),))}


def pin(name="demo-package", version="1.2.3", digest=HASH_A):
    return (name + "==" + version + " \\\n    --hash=sha256:" + digest + "\n").encode()


class DependencyLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def error(self, code, function, *args):
        with self.assertRaises(common.LockError) as caught:
            function(*args)
        self.assertEqual(str(caught.exception), code)

    def source(self, payload=None):
        path = self.root / "synthetic-report.json"
        path.write_text(json.dumps(payload if payload is not None else report()))
        return path

    def test_conversion_normalizes_sorts_and_omits_report_metadata(self):
        first = item("Demo_Zeta", "2.0rc1.post2.dev3+local.4", HASH_B.upper())
        first["metadata"]["summary"] = "synthetic-unexported-marker"
        first["download_info"]["url"] = "synthetic-unexported-marker"
        second = item("demo-alpha", "1!3.0", HASH_A)
        a = converter.render_lock(converter.records_from_report(report(first, second)))
        b = converter.render_lock(converter.records_from_report(report(second, first)))
        self.assertEqual(a, b)
        self.assertLess(a.index(b"demo-alpha=="), a.index(b"demo-zeta=="))
        self.assertIn(HASH_B.encode(), a)
        self.assertNotIn(b"synthetic-unexported-marker", a)
        self.assertEqual(verifier.validate_lock(a), 2)

    def test_legacy_sha256_is_supported(self):
        record = item()
        record["download_info"]["archive_info"] = {"hash": "sha256=" + HASH_A}
        self.assertEqual(converter.records_from_report(report(record))["demo-package"], ("1.2.3", HASH_A))

    def test_equal_modern_and_legacy_hashes_are_supported(self):
        record = item()
        record["download_info"]["archive_info"]["hash"] = "sha256=" + HASH_A.upper()
        self.assertEqual(len(converter.records_from_report(report(record))), 1)

    def test_conflicting_hash_representations_are_rejected(self):
        record = item()
        record["download_info"]["archive_info"]["hash"] = "sha256=" + HASH_B
        self.error("ARCHIVE_HASH_CONFLICT", converter.records_from_report, report(record))

    def test_missing_or_non_sha256_artifact_is_rejected(self):
        for archive in ({}, {"hash": "sha1=synthetic"}, {"hashes": {"sha512": "synthetic"}}):
            record = item()
            record["download_info"]["archive_info"] = archive
            self.error("ARCHIVE_HASH_REQUIRED", converter.records_from_report, report(record))

    def test_malformed_sha256_is_rejected(self):
        for digest in (HASH_A[:-1], "x" * 64, HASH_A + "\n", 123):
            self.error("SHA256_INVALID", converter.records_from_report, report(item(digest=digest)))

    def test_identical_normalized_duplicate_is_deduplicated(self):
        records = converter.records_from_report(report(item("Demo_Package"), item("demo.package")))
        self.assertEqual(len(records), 1)

    def test_conflicting_artifacts_or_versions_are_rejected(self):
        for other in (item(version="2.0"), item(digest=HASH_B)):
            self.error("PACKAGE_ARTIFACT_CONFLICT", converter.records_from_report, report(item(), other))

    def test_unsafe_package_names_are_rejected(self):
        for name in ("-option", "demo[extra]", "demo @ synthetic", "demo\ninjected", "", None):
            self.error("PACKAGE_NAME_INVALID", converter.records_from_report, report(item(name=name)))

    def test_unsupported_version_syntax_is_rejected(self):
        for version in ("1.*", "1.0;marker", "1.0\n--option", "synthetic", "v1.0", "1.0RC1", "", None):
            self.error("VERSION_UNSUPPORTED", converter.records_from_report, report(item(version=version)))

    def test_supported_fixed_version_subset(self):
        for version in ("1", "1.2.3", "2!1.0rc2.post3.dev4+local.5", "1.0a1", "1.0b2", "1.0.dev1"):
            self.assertEqual(common.checked_version(version), version)

    def test_record_schema_and_count_are_required(self):
        self.error("REPORT_VERSION_UNSUPPORTED", converter.records_from_report, {"version": "2", "install": [item()]})
        self.error("REPORT_RECORD_LIMIT", converter.records_from_report, {"version": "1", "install": []})
        self.error("REPORT_RECORD_INVALID", converter.records_from_report, report({"metadata": None}))
        with mock.patch.object(converter, "MAX_PACKAGES", 1):
            self.error("REPORT_RECORD_LIMIT", converter.records_from_report, report(item(), item()))

    def test_strict_json_rejects_duplicates_and_nonfinite(self):
        self.error("JSON_DUPLICATE_KEY", common.strict_json, b'{"version":"1","version":"1"}')
        self.error("JSON_NONFINITE", common.strict_json, b'{"synthetic":NaN}')
        self.error("JSON_NONFINITE", common.strict_json, b'{"synthetic":1e999}')

    def test_invalid_json_and_utf8_have_fixed_codes(self):
        for data in (b"{synthetic}", b"\xff"):
            self.error("JSON_INVALID", common.strict_json, data)

    def test_json_depth_is_bounded(self):
        self.error("JSON_STRUCTURE_LIMIT", common.strict_json, b"[" * 65 + b"0" + b"]" * 65)

    def test_input_bound_precedes_json_decoder(self):
        source = self.root / "oversized-synthetic.json"
        source.write_bytes(b"x" * (common.MAX_REPORT_BYTES + 1))
        with mock.patch.object(common.json, "loads", side_effect=AssertionError("Decoder must not run")):
            self.error("INPUT_SIZE_LIMIT", converter.convert, source, self.root / "never.lock")
        self.assertFalse((self.root / "never.lock").exists())

    def test_converter_output_is_new_private_and_source_unchanged(self):
        source = self.source()
        before = source.read_bytes()
        output = self.root / "synthetic.lock"
        self.assertEqual(converter.convert(source, output), 1)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertEqual(verifier.verify([output]), 1)
        original = output.read_bytes()
        self.error("OUTPUT_EXISTS", converter.convert, source, output)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(source.read_bytes(), before)

    def test_invalid_report_creates_no_output(self):
        source = self.source(report(item(version="unsupported")))
        output = self.root / "never.lock"
        self.error("VERSION_UNSUPPORTED", converter.convert, source, output)
        self.assertFalse(output.exists())

    def test_output_parent_is_not_created(self):
        source = self.source()
        with self.assertRaises(FileNotFoundError):
            converter.convert(source, self.root / "missing" / "synthetic.lock")
        self.assertFalse((self.root / "missing").exists())

    def test_input_link_and_linked_parent_are_rejected(self):
        source = self.source()
        link = self.root / "input-link"
        link.symlink_to(source)
        self.error("SYMLINK_PATH", converter.convert, link, self.root / "never.lock")
        parent = self.root / "parent-link"
        parent.symlink_to(self.root, target_is_directory=True)
        self.error("SYMLINK_PATH", converter.convert, parent / source.name, self.root / "never.lock")

    def test_output_link_is_preserved(self):
        target = self.root / "existing.lock"
        target.write_bytes(b"synthetic-existing")
        link = self.root / "output-link"
        link.symlink_to(target)
        self.error("OUTPUT_EXISTS", converter.convert, self.source(), link)
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_bytes(), b"synthetic-existing")

    def test_output_parent_link_is_rejected(self):
        link = self.root / "output-parent"
        link.symlink_to(self.root, target_is_directory=True)
        self.error("SYMLINK_PATH", converter.convert, self.source(), link / "never.lock")
        self.assertFalse((self.root / "never.lock").exists())

    def test_fifo_and_traversal_are_rejected(self):
        fifo = self.root / "synthetic-fifo"
        os.mkfifo(fifo)
        self.error("INPUT_NOT_REGULAR", common.read_bounded, fifo, 100)
        self.error("PATH_TRAVERSAL", common.read_bounded, self.root / "sub" / ".." / "anything", 100)

    def test_unknown_active_lock_lines_are_rejected(self):
        for line in (b"--index-url synthetic-index\n", b"-r synthetic.txt\n", b"demo @ synthetic:artifact\n",
                     b"--find-links synthetic\n", b"demo==1.0;synthetic\n"):
            self.error("LOCK_LINE_INVALID", verifier.validate_lock, pin() + line)

    def test_hash_must_be_immediately_adjacent(self):
        self.error("ADJACENT_SHA256_REQUIRED", verifier.validate_lock, b"demo==1.0 \\\n")
        self.error("ADJACENT_SHA256_REQUIRED", verifier.validate_lock,
                   b"demo==1.0 \\\n# intervening comment\n    --hash=sha256:" + HASH_A.encode() + b"\n")
        self.error("LOCK_LINE_INVALID", verifier.validate_lock, b"    --hash=sha256:" + HASH_A.encode() + b"\n")

    def test_lock_duplicates_noncanonical_names_and_order_are_rejected(self):
        self.error("DUPLICATE_PACKAGE", verifier.validate_lock, pin() + pin())
        self.error("PACKAGE_NAME_NONCANONICAL", verifier.validate_lock, pin("Demo_Package"))
        self.error("PACKAGE_ORDER_INVALID", verifier.validate_lock, pin("demo-zeta") + pin("demo-alpha"))

    def test_comments_are_ignored_but_cannot_form_an_empty_lock(self):
        self.assertEqual(verifier.validate_lock(b"# synthetic comment\n\n" + pin()), 1)
        self.error("EMPTY_LOCK", verifier.validate_lock, b"# synthetic comment\n")

    def test_control_characters_and_invalid_encoding_are_rejected(self):
        self.error("LOCK_CONTROL_CHARACTER", verifier.validate_lock, b"\t" + pin())
        self.error("LOCK_ENCODING_INVALID", verifier.validate_lock, b"\xff")

    def test_lock_line_count_length_and_byte_bounds(self):
        with mock.patch.object(verifier, "MAX_LINES", 1):
            self.error("LOCK_STRUCTURE_LIMIT", verifier.validate_lock, pin())
        with mock.patch.object(verifier, "MAX_LINE_CHARS", 10):
            self.error("LOCK_STRUCTURE_LIMIT", verifier.validate_lock, pin())
        self.error("INPUT_SIZE_LIMIT", verifier.validate_lock, b"x" * (common.MAX_LOCK_BYTES + 1))

    def test_multiple_locks_count_records_without_claiming_uniqueness(self):
        a, b = self.root / "a.lock", self.root / "b.lock"
        a.write_bytes(pin())
        b.write_bytes(pin())
        self.assertEqual(verifier.verify([a, b]), 2)

    def test_total_input_and_file_count_limits(self):
        a = self.root / "a.lock"
        a.write_bytes(pin())
        with mock.patch.object(verifier, "MAX_TOTAL_LOCK_BYTES", len(pin()) * 2 - 1):
            self.error("TOTAL_INPUT_SIZE_LIMIT", verifier.verify, [a, a])
        with mock.patch.object(verifier, "read_bounded", side_effect=AssertionError("No read expected")):
            self.error("LOCK_FILE_COUNT_LIMIT", verifier.verify, [a] * (common.MAX_LOCKS + 1))

    def test_cli_success_is_counts_only_and_failure_hides_arguments(self):
        source, output = self.source(), self.root / "synthetic.lock"
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            self.assertEqual(converter.main(["--report", str(source), "--output", str(output)]), 0)
        self.assertEqual(json.loads(result.getvalue()), {"result": "LOCK_WRITTEN", "packages": 1})
        self.assertNotIn(str(self.root), result.getvalue())
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            self.assertEqual(verifier.main([str(output)]), 0)
        self.assertEqual(json.loads(result.getvalue()), {"result": "PASS", "locks": 1, "package_records": 1})
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            self.assertEqual(converter.main(["--unexpected", "synthetic-marker"]), 2)
        self.assertNotIn("synthetic-marker", result.getvalue())


if __name__ == "__main__":
    unittest.main()
