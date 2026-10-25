"""Fictional captured reports; never opens a real inventoried source body."""

import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/source-inventory-diff/inventory_diff.py"
spec = importlib.util.spec_from_file_location("fictional_inventory_diff", SCRIPT)
diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diff)
STAMP = "2030-01-01T00:00:00+00:00"


def record(
    path="sample.txt",
    body=b"Fictional sample\n",
    *,
    stamp=STAMP,
    size=None,
    digest=None,
):
    return dict(
        path=path,
        bytes=len(body) if size is None else size,
        modified_utc=stamp,
        sha256=digest or hashlib.sha256(body).hexdigest(),
    )


def report(rows=(), **changes):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(diff.HEADERS)
    top = {}
    for row in rows:
        encoded, escaped = diff._csv_path(row["path"])
        writer.writerow(
            [encoded, escaped, row["bytes"], row["modified_utc"], row["sha256"], "ok"]
        )
        head = row["path"].split("/", 1)[0]
        top[head] = top.get(head, 0) + 1
    raw = output.getvalue().encode("utf-8")
    summary = dict(
        schema_version="outlands.source_inventory.v1",
        label="fictional",
        created_at_utc=STAMP,
        coverage="selected_regular_files_only",
        file_count=len(rows),
        hashed_file_count=len(rows),
        total_bytes=sum(row["bytes"] for row in rows),
        top_level_counts=top,
        skipped=dict(directories=0, files=0, links=0, nonregular=0),
        files_csv_sha256=hashlib.sha256(raw).hexdigest().upper(),
        path_encoding=diff.ENCODING,
        limits=dict(
            max_files=10000,
            max_file_bytes=67108864,
            max_total_bytes=268435456,
            max_entries=10000,
        ),
        default_excluded_directories=[".git"],
        default_excluded_suffixes=[".log"],
    )
    summary.update(changes)
    return raw, json.dumps(summary, ensure_ascii=True).encode()


def alter_csv(value, transform):
    raw, summary = value
    rows = list(csv.reader(io.StringIO(raw.decode(), newline="")))
    transform(rows)
    out = io.StringIO(newline="")
    csv.writer(out).writerows(rows)
    raw = out.getvalue().encode()
    data = json.loads(summary)
    data["files_csv_sha256"] = hashlib.sha256(raw).hexdigest()
    return raw, json.dumps(data).encode()


class Fixture(unittest.TestCase):
    def setUp(self):
        base = Path(
            os.environ.get("OUTLANDS_TEST_TEMP", tempfile.gettempdir())
        ).resolve()
        self.temporary = tempfile.TemporaryDirectory(dir=base)
        self.parent = Path(self.temporary.name)

        def cleanup():
            target = self.parent.resolve()
            if target == base or not target.is_relative_to(base):
                raise RuntimeError("UNEXPECTED_CLEANUP_TARGET")
            self.temporary.cleanup()

        self.addCleanup(cleanup)

    def write_run(self, name, value):
        path = self.parent / name
        path.mkdir()
        for filename, raw in zip(("files.csv", "summary.json"), value):
            (path / filename).write_bytes(raw)
        return path

    def compare(self, left, right):
        return diff.compare_reports(*left, *right)

    def rejected(self, value, code=None):
        with self.assertRaises(diff.DiffError) as caught:
            diff.parse_inventory(*value)
        if code:
            self.assertEqual(str(caught.exception), code)

    def invoke(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = diff.main(list(map(str, args)))
        return code, output.getvalue(), errors.getvalue()


class ReportParserTests(Fixture):
    def test_compatible_public_generator_output(self):
        spec = importlib.util.spec_from_file_location(
            "fictional_inventory_generator",
            ROOT / "tools/source-inventory/source_inventory.py",
        )
        inventory = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inventory)
        source, parent = self.parent / "fictional-source", self.parent / "reports"
        source.mkdir()
        parent.mkdir()
        (source / "sample.txt").write_bytes(b"Fictional source only\n")
        run, _ = inventory.snapshot(source, parent, "fictional")
        result = diff.read_and_compare(run, run)
        self.assertEqual(result["status"], "MATCHING_SELECTED_RECORDS")
        self.assertEqual(result["counts"]["unchanged"], 1)

    def test_empty_reports_are_supported(self):
        value = report()
        self.assertEqual(diff.parse_inventory(*value)[0], [])
        result = self.compare(value, value)
        self.assertEqual(result["status"], "MATCHING_SELECTED_RECORDS")
        self.assertEqual(result["rows"], [])

    def test_input_bytes_and_csv_hash_are_required(self):
        value = report([record()])
        for pair in (("fictional", value[1]), (value[0], {})):
            self.rejected(pair, "REPORT_BYTES_REQUIRED")
        self.rejected((value[0] + b" ", value[1]), "CSV_HASH_MISMATCH")

    def test_summary_fields_schema_coverage_and_encoding_are_exact(self):
        base = json.loads(report()[1])
        for key in diff.SUMMARY_REQUIRED:
            data = {k: v for k, v in base.items() if k != key}
            self.rejected(
                (report()[0], json.dumps(data).encode()), "JSON_FIELDS_INVALID"
            )
        for changes in (
            dict(private_path="fictional-canary"),
            dict(schema_version="other"),
            dict(coverage="all_files"),
            dict(path_encoding="other"),
        ):
            self.rejected(report(**changes))

    def test_summary_integer_bounds_types_and_totals(self):
        for value in (True, "0", -1, 10001):
            self.rejected(report(file_count=value), "INVENTORY_TOTALS_INVALID")
        self.rejected(report(file_count=0.0), "JSON_INTEGER_REQUIRED")
        self.rejected(report([record()], total_bytes=0), "INVENTORY_TOTALS_MISMATCH")
        self.rejected(
            report([record()], top_level_counts={}), "INVENTORY_TOTALS_MISMATCH"
        )
        self.rejected(report(hashed_file_count=True), "INVENTORY_TOTALS_INVALID")
        self.rejected(
            report(
                limits=dict(
                    max_files=0, max_file_bytes=1, max_total_bytes=1, max_entries=1
                )
            ),
            "INVENTORY_METADATA_INVALID",
        )

    def test_summary_metadata_and_optional_fields(self):
        for changes in (
            dict(label="Invalid Label"),
            dict(created_at_utc="2030-01-01"),
            dict(skipped={}),
            dict(default_excluded_suffixes=[""]),
            dict(tree=[]),
        ):
            self.rejected(report(**changes))
        value = report(
            [record()],
            tree={"uninterpreted": "fictional"},
            additional_excluded_directories=["scratch"],
        )
        self.assertEqual(len(diff.parse_inventory(*value)[0]), 1)

    def test_json_duplicates_nonstandard_numbers_depth_and_utf8_are_refused(self):
        for raw in (
            b'{"x":1,"x":2}',
            b'{"x":NaN}',
            b'{"x":1.5}',
            b"[" * 1200,
            b"\xff",
            b'{"x":"\\ud800"}',
            b"{",
        ):
            self.rejected((report()[0], raw))

    def test_exact_csv_header_column_counts_and_status(self):
        value = report([record()])
        self.rejected(
            alter_csv(value, lambda rows: rows[0].reverse()), "CSV_HEADER_INVALID"
        )
        self.rejected(
            alter_csv(value, lambda rows: rows[1].append("fictional")),
            "CSV_ROWS_INVALID",
        )
        self.rejected(
            alter_csv(value, lambda rows: rows[1].__setitem__(5, "incomplete")),
            "CSV_ROW_INVALID",
        )

    def test_duplicate_decoded_paths_fail(self):
        value = report([record(), record()])
        self.rejected(value, "CSV_PATH_DUPLICATE")

    def test_unsupported_paths_and_canonical_spreadsheet_encoding(self):
        for path in (
            "",
            "/fictional",
            "../sample",
            "a/./sample",
            "a//sample",
            "C:/fictional",
            "\\fictional",
            "nul\x00name",
        ):
            self.rejected(report([record(path)]), "CSV_PATH_INVALID")
        value = report([record("=fictional.txt")])
        self.rejected(
            alter_csv(value, lambda rows: rows[1].__setitem__(1, "false")),
            "CSV_ESCAPE_INVALID",
        )
        self.rejected(
            alter_csv(value, lambda rows: rows[1].__setitem__(1, "yes")),
            "CSV_PATH_INVALID",
        )

    def test_literal_formula_apostrophe_controls_and_backslashes_remain_data(self):
        paths = [
            "=fictional.txt",
            "'sample.txt",
            "\tsample.txt",
            "sample\nname.txt",
            "nested\\literal.txt",
            "échantillon.txt",
        ]
        parsed, _ = diff.parse_inventory(
            *report([record(path, body=path.encode()) for path in paths])
        )
        self.assertEqual({row["path"] for row in parsed}, set(paths))
        rendered = diff.render_report(
            self.compare(
                report(), report([record(path, body=path.encode()) for path in paths])
            )
        )
        self.assertNotIn("\t", rendered)
        self.assertNotIn("\n", rendered)
        self.assertTrue(rendered.isascii())

    def test_csv_sizes_digests_and_utc_timestamps(self):
        value = report([record()])
        for size in ("01", "-1", "1.5", "true", "9999999999"):
            self.rejected(
                alter_csv(value, lambda rows: rows[1].__setitem__(2, size)),
                "CSV_BYTES_INVALID",
            )
        for index, text in (
            (4, "not-a-hash"),
            (3, "2030-01-01"),
            (3, "2030-01-01T00:00:00+01:00"),
        ):
            self.rejected(
                alter_csv(value, lambda rows: rows[1].__setitem__(index, text)),
                "CSV_ROW_INVALID",
            )

    def test_row_and_byte_limits(self):
        with patch.object(diff, "MAX_ROWS", 1):
            self.rejected(report([record("a"), record("b")]))
        value = report([record()])
        with patch.object(diff, "MAX_CSV_BYTES", len(value[0]) - 1):
            self.rejected(value, "INPUT_BYTE_LIMIT")
        with patch.object(diff, "MAX_JSON_BYTES", len(value[1]) - 1):
            self.rejected(value, "INPUT_BYTE_LIMIT")


class ComparisonTests(Fixture):
    def test_matching_selected_records_ignore_run_label_and_creation_time(self):
        a = report([record()])
        b = report([record()], label="other", created_at_utc="2031-01-01T00:00:00Z")
        result = self.compare(a, b)
        self.assertEqual(result["status"], "MATCHING_SELECTED_RECORDS")
        self.assertEqual(result["counts"]["unchanged"], 1)
        self.assertNotEqual(
            result["input_hashes"]["before"]["summary_json_sha256"],
            result["input_hashes"]["after"]["summary_json_sha256"],
        )

    def test_only_in_before_and_after_are_observations(self):
        result = self.compare(
            report([record("old.txt", b"Old fictional\n")]),
            report([record("new.txt", b"New fictional\n")]),
        )
        self.assertEqual(result["status"], "DIFFERENCES_REPORTED")
        self.assertEqual(
            {row["classification"] for row in result["rows"]},
            {"ONLY_IN_BEFORE", "ONLY_IN_AFTER"},
        )
        self.assertEqual(result["hash_size_groups"], [])

    def test_hash_or_size_change_precedes_timestamp_only(self):
        result = self.compare(
            report([record()]),
            report(
                [record(body=b"Different fictional\n", stamp="2031-01-01T00:00:00Z")]
            ),
        )
        self.assertEqual(result["rows"][0]["classification"], "HASH_OR_SIZE_CHANGED")
        self.assertEqual(result["counts"]["mtime_only_changed"], 0)

    def test_timestamp_only_changes_and_equivalent_utc_spellings(self):
        a = report([record()])
        b = report(
            [record(stamp="2030-01-01T00:00:00Z", digest=record()["sha256"].upper())]
        )
        self.assertEqual(self.compare(a, b)["status"], "MATCHING_SELECTED_RECORDS")
        c = report([record(stamp="2030-01-02T00:00:00Z")])
        self.assertEqual(
            self.compare(a, c)["rows"][0]["classification"], "MTIME_ONLY_CHANGED"
        )

    def test_coverage_exclusions_and_limits_are_compared(self):
        a = report([record()])
        base = json.loads(a[1])
        b = report(
            [record()],
            additional_excluded_directories=["scratch"],
            default_excluded_suffixes=[".tmp"],
            limits={**base["limits"], "max_files": 9999},
        )
        result = self.compare(a, b)
        self.assertEqual(
            result["coverage"]["issues"],
            [
                "DIRECTORY_EXCLUSIONS_DIFFER",
                "SUFFIX_EXCLUSIONS_DIFFER",
                "LIMITS_DIFFER",
            ],
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["counts"]["unchanged"], 1)

    def test_effective_exclusion_sets_ignore_order_case_and_default_vs_additional_split(
        self,
    ):
        a = report(
            [record()],
            default_excluded_directories=[".git", "Scratch"],
            default_excluded_suffixes=[".LOG", ".tmp"],
        )
        b = report(
            [record()],
            default_excluded_directories=[".GIT"],
            additional_excluded_directories=["scratch", "SCRATCH"],
            default_excluded_suffixes=[".TMP", ".log"],
        )
        self.assertTrue(self.compare(a, b)["coverage"]["declarations_match"])

    def test_skip_counts_require_review_even_if_identical(self):
        skipped = dict(directories=1, files=0, links=0, nonregular=0)
        value = report([record()], skipped=skipped)
        result = self.compare(value, value)
        self.assertEqual(result["issues"], ["SKIPPED_ENTRIES_PRESENT"])
        self.assertTrue(result["coverage"]["declarations_match"])
        self.assertFalse(result["scope_equivalence_verified"])

    def test_optional_tree_is_ignored_and_not_opened(self):
        a = report([record()], tree={"sha256": "fictional-a"})
        b = report([record()], tree={"sha256": "fictional-b"})
        result = self.compare(a, b)
        self.assertEqual(result["status"], "MATCHING_SELECTED_RECORDS")
        self.assertFalse(result["tree_metadata_compared"])

    def test_cross_run_casefold_names_are_ambiguous_not_conflated(self):
        result = self.compare(
            report([record("Sample.txt", b"Fictional A")]),
            report([record("sample.txt", b"Fictional B")]),
        )
        self.assertIn("CASEFOLD_PATH_AMBIGUITY", result["issues"])
        self.assertEqual(result["counts"]["only_in_before"], 1)
        self.assertEqual(result["counts"]["only_in_after"], 1)

    def test_unicode_casefold_and_no_unicode_normalization(self):
        a = report([record("Straße.txt", b"Fictional A")])
        b = report([record("STRASSE.txt", b"Fictional B")])
        self.assertTrue(self.compare(a, b)["casefold_ambiguities"])
        a = report([record("é.txt", b"Fictional A")])
        b = report([record("e\u0301.txt", b"Fictional B")])
        self.assertEqual(self.compare(a, b)["casefold_ambiguities"], [])

    def test_hash_size_group_hints_do_not_verify_renames(self):
        result = self.compare(report([record("old.txt")]), report([record("new.txt")]))
        self.assertEqual(
            result["hash_size_groups"],
            [
                dict(
                    sha256=record()["sha256"],
                    bytes=record()["bytes"],
                    before_paths=["old.txt"],
                    after_paths=["new.txt"],
                )
            ],
        )
        self.assertIn("HASH_SIZE_GROUP_HINTS_PRESENT", result["issues"])
        self.assertFalse(result["renames_verified"])
        self.assertFalse(result["canonical_copy_selected"])

    def test_one_to_many_and_one_sided_duplicates_stay_grouped(self):
        a = report([record("a.txt")])
        b = report([record("b.txt"), record("c.txt")])
        result = self.compare(a, b)
        self.assertEqual(len(result["hash_size_groups"]), 1)
        self.assertEqual(
            result["hash_size_groups"][0]["after_paths"], ["b.txt", "c.txt"]
        )
        self.assertEqual(len(self.compare(report(), b)["hash_size_groups"]), 1)
        self.assertEqual(self.compare(b, b)["status"], "REVIEW_REQUIRED")

    def test_same_digest_different_sizes_is_separate_review_not_a_group_match(self):
        result = self.compare(
            report([record()]), report([record(size=record()["bytes"] + 1)])
        )
        self.assertIn("DIGEST_SIZE_CONFLICT", result["issues"])
        self.assertEqual(result["hash_size_groups"], [])
        self.assertEqual(
            result["digest_size_conflicts"][0]["reported_sizes"],
            [record()["bytes"], record()["bytes"] + 1],
        )

    def test_counts_status_flags_and_sorted_rows_are_fixed(self):
        result = self.compare(report([record("b", b"B"), record("A", b"A")]), report())
        self.assertEqual([r["path"] for r in result["rows"]], ["A", "b"])
        self.assertTrue(all(result[key] is False for key in diff._flags()))
        self.assertEqual(
            result["counts"],
            dict(
                before=2,
                after=0,
                only_in_before=2,
                only_in_after=0,
                hash_or_size_changed=0,
                mtime_only_changed=0,
                unchanged=0,
            ),
        )

    def test_reverse_comparison_swaps_sides_without_losing_evidence(self):
        a, b = (
            report([record("a.txt"), record("keep.txt", b"K")]),
            report([record("b.txt"), record("keep.txt", b"K2")]),
        )
        forward, reverse = self.compare(a, b), self.compare(b, a)
        self.assertEqual(
            forward["counts"]["only_in_before"], reverse["counts"]["only_in_after"]
        )
        for one, two in zip(forward["rows"], reverse["rows"]):
            self.assertEqual(one["path"], two["path"])
            self.assertEqual(one["before"], two["after"])
            self.assertEqual(one["after"], two["before"])

    def test_row_permutations_leave_observations_unchanged_except_snapshot_hashes(self):
        rows = [record("a", b"A"), record("b", b"B"), record("c", b"C")]
        one = self.compare(report(rows), report(rows[1:]))
        two = self.compare(
            report(list(reversed(rows))), report(list(reversed(rows[1:])))
        )
        one.pop("input_hashes")
        two.pop("input_hashes")
        self.assertEqual(one, two)

    def test_200_seeded_pairs_match_independent_list_search_and_group_oracle(self):
        rng = random.Random(1702)
        for _ in range(200):
            sides = []
            for side in range(2):
                rows = []
                for index in range(8):
                    if rng.randrange(3):
                        rows.append(
                            record(
                                f"sample_{index}.txt",
                                f"Fictional body {rng.randrange(4)}".encode(),
                                stamp=f"2030-01-0{rng.randrange(1, 3)}T00:00:00Z",
                            )
                        )
                sides.append(rows)
            result = self.compare(report(sides[0]), report(sides[1]))
            for row in result["rows"]:
                a = next(
                    (item for item in sides[0] if item["path"] == row["path"]), None
                )
                b = next(
                    (item for item in sides[1] if item["path"] == row["path"]), None
                )
                expected = (
                    "ONLY_IN_AFTER"
                    if a is None
                    else "ONLY_IN_BEFORE"
                    if b is None
                    else "HASH_OR_SIZE_CHANGED"
                    if a["sha256"] != b["sha256"] or a["bytes"] != b["bytes"]
                    else "MTIME_ONLY_CHANGED"
                    if a["modified_utc"] != b["modified_utc"]
                    else "UNCHANGED"
                )
                self.assertEqual(row["classification"], expected)
            pairs = {(row["sha256"], row["bytes"]) for side in sides for row in side}
            expected = []
            for digest, size in sorted(pairs):
                left = sorted(
                    row["path"]
                    for row in sides[0]
                    if row["sha256"] == digest and row["bytes"] == size
                )
                right = sorted(
                    row["path"]
                    for row in sides[1]
                    if row["sha256"] == digest and row["bytes"] == size
                )
                if (
                    len(left) > 1
                    or len(right) > 1
                    or (left and right and left != right)
                ):
                    expected.append(
                        dict(
                            sha256=digest,
                            bytes=size,
                            before_paths=left,
                            after_paths=right,
                        )
                    )
            self.assertEqual(result["hash_size_groups"], expected)


class ReaderAndCliTests(Fixture):
    def test_maximum_rows_are_grouped_without_quadratic_pairs(self):
        rows = [record(f"sample_{index:05}.txt", body=b"") for index in range(10000)]
        result = self.compare(report(rows), report())
        self.assertEqual(result["counts"]["only_in_before"], 10000)
        self.assertEqual(len(result["hash_size_groups"]), 1)
        self.assertEqual(len(result["hash_size_groups"][0]["before_paths"]), 10000)
        self.assertLess(len(diff.render_report(result)), diff.MAX_OUTPUT_BYTES)

    def test_descriptor_identity_change_is_refused_before_read(self):
        run = self.write_run("before", report())
        real = (run / "files.csv").lstat()
        fake = SimpleNamespace(
            **{key: getattr(real, key) for key in dir(real) if key.startswith("st_")}
        )
        fake.st_ino += 1
        with patch.object(os, "fstat", return_value=fake):
            code, output, _ = self.invoke("--before", run, "--after", run)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["code"], "INPUT_CHANGED")

    def test_reads_exactly_four_control_files_and_preserves_bytes(self):
        a = self.write_run("before", report([record()]))
        b = self.write_run("after", report([record()]))
        (a / "tree.txt").write_text("fictional tree must not be read", encoding="utf-8")
        original = diff._read_bytes
        opened = []

        def track(path, maximum):
            opened.append(path)
            return original(path, maximum)

        with (
            patch.object(diff, "_read_bytes", side_effect=track),
            patch.object(os, "scandir", side_effect=AssertionError("NO_SCAN")),
            patch.object(socket, "socket", side_effect=AssertionError("NO_NETWORK")),
        ):
            result = diff.read_and_compare(a, b)
        self.assertEqual(
            opened,
            [a / "files.csv", a / "summary.json", b / "files.csv", b / "summary.json"],
        )
        self.assertEqual(result["status"], "MATCHING_SELECTED_RECORDS")

    def test_pure_compare_has_no_filesystem_network_clock_or_process_access(self):
        value = report([record()])
        with contextlib.ExitStack() as stack:
            for name in (
                "builtins.open",
                "os.open",
                "os.scandir",
                "socket.socket",
                "subprocess.Popen",
                "time.time",
                "pathlib.Path.stat",
                "pathlib.Path.unlink",
            ):
                stack.enter_context(
                    patch(name, side_effect=AssertionError("NO_SIDE_EFFECT"))
                )
            self.assertEqual(
                self.compare(value, value)["status"], "MATCHING_SELECTED_RECORDS"
            )

    def test_oversized_control_file_refused_before_open(self):
        run = self.write_run("before", report())
        with (
            patch.object(diff, "MAX_CSV_BYTES", 1),
            patch.object(diff.os, "open", side_effect=AssertionError("NO_OPEN")),
        ):
            code, out, _ = self.invoke("--before", run, "--after", run)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["code"], "INPUT_BYTE_LIMIT")

    def test_ambiguous_paths_refused_before_metadata(self):
        for value in (
            "../fictional",
            "//fictional-host/share",
            "C:fictional",
            "nul",
            "fictional. ",
            "fictional:stream",
        ):
            with patch.object(Path, "lstat", side_effect=AssertionError("NO_STAT")):
                self.assertEqual(self.invoke("--before", value, "--after", value)[0], 2)

    def test_missing_native_error_and_private_values_are_not_echoed(self):
        missing = self.parent / "fictional-private-canary"
        code, out, err = self.invoke("--before", missing, "--after", missing)
        self.assertEqual(code, 2)
        self.assertNotIn(str(missing), out + err)
        self.assertNotIn("fictional-private-canary", out + err)
        try:
            diff.read_and_compare(missing, missing)
        except diff.DiffError as error:
            self.assertNotIn(str(missing), "".join(traceback.format_exception(error)))
            self.assertTrue(error.__suppress_context__)
        else:
            self.fail("EXPECTED_ERROR")

    def test_changed_across_sequential_snapshots_is_refused(self):
        run = self.write_run("before", report())
        with patch.object(diff, "_fingerprint", return_value=("fictional-change",)):
            code, out, _ = self.invoke("--before", run, "--after", run)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["code"], "INPUT_CHANGED")

    def test_hardlinked_control_file_is_refused(self):
        run = self.write_run("before", report())
        try:
            os.link(run / "files.csv", self.parent / "fictional-hardlink.csv")
        except OSError:
            self.skipTest("Native hardlink creation unavailable")
        self.assertEqual(self.invoke("--before", run, "--after", run)[0], 2)

    def test_symlink_run_or_leaf_is_refused(self):
        run = self.write_run("before", report())
        linked = self.parent / "linked"
        try:
            linked.symlink_to(run, target_is_directory=True)
        except OSError:
            self.skipTest("Native symlink creation unavailable")
        self.assertEqual(self.invoke("--before", linked, "--after", run)[0], 2)
        (run / "files.csv").rename(run / "fictional-real.csv")
        (run / "files.csv").symlink_to(run / "fictional-real.csv")
        self.assertEqual(self.invoke("--before", run, "--after", run)[0], 2)

    def test_reparse_and_missing_identity_are_refused_synthetically(self):
        run = self.write_run("before", report())
        real = (run / "files.csv").lstat()
        for changes in (dict(st_ino=0), dict(st_file_attributes=0x400)):
            fake = SimpleNamespace(
                **{
                    key: getattr(real, key)
                    for key in dir(real)
                    if key.startswith("st_")
                }
            )
            for key, value in changes.items():
                setattr(fake, key, value)
            with patch.object(Path, "lstat", return_value=fake):
                self.assertEqual(self.invoke("--before", run, "--after", run)[0], 2)

    def test_output_bound_has_no_partial_report(self):
        run = self.write_run("before", report([record()]))
        with patch.object(diff, "MAX_OUTPUT_BYTES", 10):
            code, out, err = self.invoke("--before", run, "--after", run)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["code"], "OUTPUT_BYTE_LIMIT")
        self.assertNotIn('"rows"', out)
        self.assertEqual(err, "")

    def test_cli_statuses_arguments_and_interrupt(self):
        a = self.write_run("before", report())
        b = self.write_run("after", report([record()]))
        self.assertEqual(self.invoke("--before", a, "--after", a)[0], 0)
        self.assertEqual(self.invoke("--before", a, "--after", b)[0], 1)
        for args in (
            (),
            ("--before", a),
            ("--bef", a, "--after", b),
            ("--unknown", "fictional-private-canary"),
        ):
            code, out, err = self.invoke(*args)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out)["code"], "ARGUMENTS_INVALID")
            self.assertNotIn("fictional-private-canary", out + err)
        with patch.object(diff, "read_and_compare", side_effect=KeyboardInterrupt):
            code, out, _ = self.invoke("--before", a, "--after", a)
        self.assertEqual(code, 130)
        self.assertEqual(json.loads(out)["code"], "INTERRUPTED")

    def test_standalone_copy_of_single_script_works(self):
        run = self.write_run("before", report([record()]))
        script = self.parent / "inventory_diff.py"
        shutil.copyfile(SCRIPT, script)
        original = (run / "files.csv").read_bytes(), (run / "summary.json").read_bytes()
        done = subprocess.run(
            [
                sys.executable,
                "-B",
                str(script),
                "--before",
                str(run),
                "--after",
                str(run),
            ],
            cwd=self.parent,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["status"], "MATCHING_SELECTED_RECORDS")
        self.assertEqual(done.stderr, "")
        self.assertEqual(
            original,
            ((run / "files.csv").read_bytes(), (run / "summary.json").read_bytes()),
        )

    def test_shipped_reports_have_fictional_expected_results(self):
        base = SCRIPT.parent / "examples"
        self.assertEqual(
            diff.read_and_compare(base / "before", base / "before")["status"],
            "MATCHING_SELECTED_RECORDS",
        )
        result = diff.read_and_compare(base / "before", base / "after")
        self.assertEqual(
            result["counts"],
            dict(
                before=4,
                after=5,
                only_in_before=1,
                only_in_after=2,
                hash_or_size_changed=1,
                mtime_only_changed=1,
                unchanged=1,
            ),
        )
        self.assertEqual(result["issues"], ["HASH_SIZE_GROUP_HINTS_PRESENT"])
        coverage = diff.read_and_compare(base / "before", base / "coverage-changed")
        self.assertEqual(
            coverage["issues"],
            ["DIRECTORY_EXCLUSIONS_DIFFER", "SKIPPED_ENTRIES_PRESENT"],
        )


if __name__ == "__main__":
    unittest.main()
