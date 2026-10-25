"""Fictional independent-full snapshot metadata; no backup contents or actions."""

import contextlib
import copy
import datetime as calendar
import io
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_public_additions import Fixture, load, ROOT


checker = load(
    "backup_retention_planner", "tools/backup-retention-planner/retention_plan.py"
)


def snapshot(
    identifier="fictional_snapshot",
    *,
    created_at="2030-01-10T00:00:00Z",
    pinned=False,
    **extra,
):
    return {"id": identifier, "created_at": created_at, "pinned": pinned, **extra}


def plan(*snapshots, as_of="2030-01-10T00:00:00Z", keep_latest=1, keep_days=0):
    return {
        "schema_version": 1,
        "snapshot_kind": "independent_full",
        "as_of": as_of,
        "policy": {"keep_latest": keep_latest, "keep_days": keep_days},
        "snapshots": list(snapshots),
    }


def changed_stat(info, **values):
    fields = {
        name: getattr(info, name)
        for name in dir(info)
        if name.startswith("st_") and not callable(getattr(info, name))
    }
    fields.update(values)
    return SimpleNamespace(**fields)


class RetentionFixture(Fixture):
    def metadata(self, value=None, *, raw=None, name="fictional-retention.json"):
        source = self.parent / name
        source.write_bytes(json.dumps(value).encode("utf-8") if raw is None else raw)
        return source

    def by_id(self, result):
        return {row["id"]: row for row in result["snapshots"]}

    def invoke(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = checker.main(list(map(str, args)))
        return code, output.getvalue(), errors.getvalue()

    def reader_failure_traceback(self, source):
        try:
            checker.read_input_json(source)
        except checker.ContractError as error:
            self.assertTrue(error.__suppress_context__)
            return "".join(traceback.format_exception(error))
        self.fail("Expected a fixed input error")


class RetentionSchemaTests(RetentionFixture):
    def test_parse_copies_rows_and_policy_without_mutating_input(self):
        data = plan(snapshot())
        before = copy.deepcopy(data)
        parsed = checker.parse_plan(data)
        self.assertEqual(parsed, data)
        self.assertIsNot(parsed, data)
        self.assertIsNot(parsed["policy"], data["policy"])
        self.assertIsNot(parsed["snapshots"], data["snapshots"])
        self.assertIsNot(parsed["snapshots"][0], data["snapshots"][0])
        parsed["policy"]["keep_days"] = 1
        parsed["snapshots"][0]["pinned"] = True
        self.assertEqual(data, before)
        checker.plan_retention(data)
        self.assertEqual(data, before)

    def test_root_and_snapshot_kind_schema_are_exact(self):
        valid = plan(snapshot())
        invalid = [None, [], "fictional", {}, {**valid, "private_path": "fictional"}]
        invalid.extend(
            {key: value for key, value in valid.items() if key != removed}
            for removed in valid
        )
        invalid.extend(
            {**valid, "schema_version": value} for value in (True, 1.0, "1", 0, 2, None)
        )
        invalid.extend(
            {**valid, "snapshot_kind": value}
            for value in (
                None,
                True,
                [],
                {},
                "incremental",
                "differential",
                "Independent_Full",
            )
        )
        invalid.extend(
            {**valid, "snapshots": value}
            for value in (None, {}, "fictional", (snapshot(),))
        )
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(checker.ContractError):
                checker.parse_plan(data)

    def test_policy_is_exact_plain_bounded_integers(self):
        valid = plan(snapshot())
        invalid = (
            None,
            [],
            {},
            {"keep_latest": 1},
            {"keep_days": 1},
            {"keep_latest": 1, "keep_days": 0, "delete": True},
        )
        for policy in invalid:
            with self.subTest(policy=policy), self.assertRaises(checker.ContractError):
                checker.parse_plan({**valid, "policy": policy})
        for name, values in (
            ("keep_latest", (None, True, False, 1.0, "1", [], {}, 0, -1, 257)),
            ("keep_days", (None, True, False, 1.0, "1", [], {}, -1, 36501)),
        ):
            for value in values:
                policy = {**valid["policy"], name: value}
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises(checker.ContractError),
                ):
                    checker.parse_plan({**valid, "policy": policy})
        self.assertEqual(
            checker.parse_plan(plan(snapshot(), keep_latest=256, keep_days=36500))[
                "policy"
            ],
            {"keep_latest": 256, "keep_days": 36500},
        )

    def test_snapshot_rows_are_exact_and_no_paths_sizes_or_chains_are_supported(self):
        invalid = [
            None,
            [],
            {},
            "fictional",
            snapshot(path="fictional/private/backup"),
            snapshot(size=1),
            snapshot(requires=["other"]),
            snapshot(dependencies=[]),
        ]
        invalid.extend(
            {key: value for key, value in snapshot().items() if key != removed}
            for removed in snapshot()
        )
        invalid.extend(
            snapshot(pinned=value) for value in (None, 0, 1, "false", [], {})
        )
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(checker.ContractError):
                checker.parse_plan(plan(row))

    def test_ids_are_unique_bounded_neutral_tokens(self):
        for identifier in (
            None,
            True,
            1,
            [],
            {},
            "",
            "A",
            "1snapshot",
            "a b",
            "a/b",
            "a" * 41,
            "café",
        ):
            with (
                self.subTest(identifier=identifier),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_plan(plan(snapshot(identifier)))
        for identifier in ("a", "a" * 40, "fictional_snapshot-1"):
            self.assertEqual(
                checker.parse_plan(plan(snapshot(identifier)))["snapshots"][0]["id"],
                identifier,
            )
        with self.assertRaises(checker.ContractError):
            checker.parse_plan(
                plan(
                    snapshot("same"),
                    snapshot("same", created_at="2030-01-09T00:00:00Z"),
                )
            )

    def test_timestamps_require_canonical_whole_second_utc_gregorian_dates(self):
        invalid = (
            None,
            True,
            1,
            [],
            {},
            "",
            "2030-01-10",
            "2030-01-10t00:00:00Z",
            "2030-01-10T00:00:00z",
            "2030-01-10T00:00:00+00:00",
            "2030-01-10T00:00:00.000Z",
            "2030-01-10T00:00:00Z ",
            " 2030-01-10T00:00:00Z",
            "0000-01-01T00:00:00Z",
            "10000-01-01T00:00:00Z",
            "1900-02-29T00:00:00Z",
            "2023-02-29T00:00:00Z",
            "2030-00-01T00:00:00Z",
            "2030-13-01T00:00:00Z",
            "2030-01-00T00:00:00Z",
            "2030-04-31T00:00:00Z",
            "2030-01-10T24:00:00Z",
            "2030-01-10T00:60:00Z",
            "2030-01-10T00:00:60Z",
            "2030-1-10T00:00:00Z",
        )
        for value in invalid:
            for location in ("as_of", "created_at"):
                data = (
                    plan(snapshot(), as_of=value)
                    if location == "as_of"
                    else plan(snapshot(created_at=value))
                )
                with (
                    self.subTest(location=location, value=value),
                    self.assertRaises(checker.ContractError),
                ):
                    checker.parse_plan(data)
        for value in (
            "0001-01-01T00:00:00Z",
            "2000-02-29T23:59:59Z",
            "2024-02-29T00:00:00Z",
            "9999-12-31T23:59:59Z",
        ):
            self.assertEqual(
                checker.parse_plan(plan(snapshot(created_at=value), as_of=value))[
                    "as_of"
                ],
                value,
            )

    def test_record_count_bounds_accept_the_full_supported_plan(self):
        rows = [snapshot("snapshot_" + str(index)) for index in range(256)]
        result = checker.plan_retention(plan(*rows, keep_latest=256))
        self.assertEqual(result["counts"]["keep"], 256)
        self.assertEqual(result["counts"]["latest_protected"], 256)
        for data in (plan(), plan(*rows, snapshot("extra"))):
            with (
                self.subTest(count=len(data["snapshots"])),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_plan(data)


class RetentionPolicyTests(RetentionFixture):
    def test_single_snapshot_is_kept_without_runtime_or_deletion_claims(self):
        result = checker.plan_retention(plan(snapshot()))
        self.assertEqual(result["status"], "KEEP_ONLY_PLAN")
        self.assertEqual(
            result["snapshots"],
            [
                {
                    "id": "fictional_snapshot",
                    "decision": "KEEP",
                    "reasons": ["LATEST_COUNT"],
                }
            ],
        )
        self.assertEqual(
            result["counts"],
            {
                "keep": 1,
                "review": 0,
                "future": 0,
                "nonfuture": 1,
                "latest_protected": 1,
            },
        )
        self.assertEqual(result["issues"], [])

    def test_latest_count_protects_all_ties_at_the_nth_record(self):
        data = plan(
            snapshot("old", created_at="2030-01-07T00:00:00Z"),
            snapshot("tie_a", created_at="2030-01-08T00:00:00Z"),
            snapshot("latest", created_at="2030-01-09T00:00:00Z"),
            snapshot("tie_b", created_at="2030-01-08T00:00:00Z"),
            keep_latest=2,
        )
        result = checker.plan_retention(data)
        self.assertEqual(
            [row["id"] for row in result["snapshots"]],
            [row["id"] for row in data["snapshots"]],
        )
        self.assertEqual(
            [row["decision"] for row in result["snapshots"]],
            ["REVIEW", "KEEP", "KEEP", "KEEP"],
        )
        self.assertEqual(
            result["counts"],
            {
                "keep": 3,
                "review": 1,
                "future": 0,
                "nonfuture": 4,
                "latest_protected": 3,
            },
        )
        self.assertEqual(
            self.by_id(result)["old"]["reasons"], ["OUTSIDE_DECLARED_PROTECTIONS"]
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_equal_timestamps_can_keep_more_than_the_requested_latest_count(self):
        result = checker.plan_retention(
            plan(snapshot("one"), snapshot("two"), snapshot("three"))
        )
        self.assertEqual(result["counts"]["latest_protected"], 3)
        self.assertEqual(result["status"], "KEEP_ONLY_PLAN")

    def test_pins_age_and_latest_are_a_union_with_fixed_reason_order(self):
        data = plan(
            snapshot("pinned_latest", pinned=True),
            snapshot("age_only", created_at="2030-01-09T00:00:00Z"),
            snapshot("pinned_old", created_at="2020-01-01T00:00:00Z", pinned=True),
            snapshot("unprotected", created_at="2020-01-02T00:00:00Z"),
            keep_days=2,
        )
        rows = self.by_id(checker.plan_retention(data))
        self.assertEqual(
            rows["pinned_latest"]["reasons"],
            ["PINNED", "LATEST_COUNT", "WITHIN_AGE_WINDOW"],
        )
        self.assertEqual(rows["age_only"]["reasons"], ["WITHIN_AGE_WINDOW"])
        self.assertEqual(rows["pinned_old"]["reasons"], ["PINNED"])
        self.assertEqual(
            rows["unprotected"],
            {
                "id": "unprotected",
                "decision": "REVIEW",
                "reasons": ["OUTSIDE_DECLARED_PROTECTIONS"],
            },
        )

    def test_zero_days_disables_age_even_for_as_of_timestamp(self):
        result = checker.plan_retention(
            plan(
                snapshot("latest"),
                snapshot("older", created_at="2030-01-09T23:59:59Z"),
                keep_days=0,
            )
        )
        self.assertEqual(self.by_id(result)["latest"]["reasons"], ["LATEST_COUNT"])
        self.assertEqual(self.by_id(result)["older"]["decision"], "REVIEW")

    def test_age_window_uses_rolling_24_hours_with_inclusive_cutoff(self):
        data = plan(
            snapshot("latest", created_at="2030-01-10T12:34:56Z"),
            snapshot("cutoff", created_at="2030-01-09T12:34:56Z"),
            snapshot("inside", created_at="2030-01-09T12:34:57Z"),
            snapshot("outside", created_at="2030-01-09T12:34:55Z"),
            as_of="2030-01-10T12:34:56Z",
            keep_days=1,
        )
        rows = self.by_id(checker.plan_retention(data))
        self.assertEqual(rows["cutoff"]["reasons"], ["WITHIN_AGE_WINDOW"])
        self.assertEqual(rows["inside"]["decision"], "KEEP")
        self.assertEqual(rows["outside"]["decision"], "REVIEW")

    def test_age_window_spans_leap_day_and_year_boundary(self):
        for as_of, cutoff, outside in (
            ("2024-03-01T00:00:00Z", "2024-02-29T00:00:00Z", "2024-02-28T23:59:59Z"),
            ("2030-01-01T00:00:00Z", "2029-12-31T00:00:00Z", "2029-12-30T23:59:59Z"),
        ):
            result = checker.plan_retention(
                plan(
                    snapshot("latest", created_at=as_of),
                    snapshot("cutoff", created_at=cutoff),
                    snapshot("outside", created_at=outside),
                    as_of=as_of,
                    keep_days=1,
                )
            )
            self.assertEqual(self.by_id(result)["cutoff"]["decision"], "KEEP")
            self.assertEqual(self.by_id(result)["outside"]["decision"], "REVIEW")

    def test_calendar_minimum_and_maximum_do_not_overflow_age_arithmetic(self):
        for value in ("0001-01-01T00:00:00Z", "9999-12-31T23:59:59Z"):
            result = checker.plan_retention(
                plan(snapshot(created_at=value), as_of=value, keep_days=36500)
            )
            self.assertEqual(
                result["snapshots"][0]["reasons"], ["LATEST_COUNT", "WITHIN_AGE_WINDOW"]
            )
            self.assertEqual(result["status"], "KEEP_ONLY_PLAN")

    def test_future_records_are_kept_without_consuming_latest_or_age_slots(self):
        data = plan(
            snapshot("future", created_at="2030-01-11T00:00:00Z"),
            snapshot("newer", created_at="2030-01-09T00:00:00Z"),
            snapshot("older", created_at="2030-01-08T00:00:00Z"),
            snapshot("oldest", created_at="2030-01-07T00:00:00Z"),
            keep_latest=2,
            keep_days=1,
        )
        result = checker.plan_retention(data)
        rows = self.by_id(result)
        self.assertEqual(rows["future"]["reasons"], ["FUTURE_TIMESTAMP_UNVERIFIED"])
        self.assertEqual(
            rows["newer"]["reasons"], ["LATEST_COUNT", "WITHIN_AGE_WINDOW"]
        )
        self.assertEqual(rows["older"]["reasons"], ["LATEST_COUNT"])
        self.assertEqual(rows["oldest"]["decision"], "REVIEW")
        self.assertEqual(
            result["counts"],
            {
                "keep": 3,
                "review": 1,
                "future": 1,
                "nonfuture": 3,
                "latest_protected": 2,
            },
        )
        self.assertEqual(result["issues"], ["FUTURE_TIMESTAMPS_PRESENT"])
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_all_future_records_require_review_and_do_not_satisfy_baseline(self):
        result = checker.plan_retention(
            plan(
                snapshot("future", created_at="2030-01-10T00:00:01Z", pinned=True),
                keep_days=36500,
            )
        )
        self.assertEqual(
            result["snapshots"],
            [
                {
                    "id": "future",
                    "decision": "KEEP",
                    "reasons": ["PINNED", "FUTURE_TIMESTAMP_UNVERIFIED"],
                }
            ],
        )
        self.assertEqual(
            result["counts"],
            {
                "keep": 1,
                "review": 0,
                "future": 1,
                "nonfuture": 0,
                "latest_protected": 0,
            },
        )
        self.assertEqual(
            result["issues"], ["FUTURE_TIMESTAMPS_PRESENT", "LATEST_COUNT_NOT_MET"]
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_insufficient_nonfuture_records_require_review_even_when_all_kept(self):
        result = checker.plan_retention(
            plan(snapshot("one"), snapshot("two"), keep_latest=3)
        )
        self.assertEqual(result["counts"]["keep"], 2)
        self.assertEqual(result["counts"]["review"], 0)
        self.assertEqual(result["issues"], ["LATEST_COUNT_NOT_MET"])
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_equal_as_of_is_nonfuture_and_pinned_rows_participate_in_latest(self):
        result = checker.plan_retention(
            plan(
                snapshot("pinned_latest", pinned=True),
                snapshot("older", created_at="2030-01-09T00:00:00Z"),
            )
        )
        self.assertEqual(
            self.by_id(result)["pinned_latest"]["reasons"], ["PINNED", "LATEST_COUNT"]
        )
        self.assertEqual(self.by_id(result)["older"]["decision"], "REVIEW")
        self.assertEqual(result["counts"]["future"], 0)
        self.assertEqual(result["issues"], [])


class RetentionPrivacyTests(RetentionFixture):
    def test_report_contains_only_ids_fixed_metadata_and_counts(self):
        data = plan(
            snapshot("first"),
            snapshot("second", pinned=True),
            keep_latest=187,
            keep_days=197,
        )
        result = checker.plan_retention(data)
        self.assertEqual(
            set(result),
            {
                "schema_version",
                "status",
                "scope",
                "filesystem_scanned",
                "backup_contents_verified",
                "metadata_verified",
                "deletion_performed",
                "deletion_authorized",
                "network_probed",
                "counts",
                "snapshots",
                "issues",
            },
        )
        self.assertEqual(result["scope"], "DECLARED_INDEPENDENT_FULL_METADATA_ONLY")
        for flag in (
            "filesystem_scanned",
            "backup_contents_verified",
            "metadata_verified",
            "deletion_performed",
            "deletion_authorized",
            "network_probed",
        ):
            self.assertIs(result[flag], False)
        for row in result["snapshots"]:
            self.assertEqual(set(row), {"id", "decision", "reasons"})
        raw = json.dumps(result)
        for value in (
            data["as_of"],
            "187",
            "197",
            str(self.parent),
            '"as_of"',
            '"created_at"',
            '"policy"',
            '"keep_days"',
            '"keep_latest"',
        ):
            self.assertNotIn(value, raw)

    def test_planner_has_no_filesystem_network_process_or_mutation_activity(self):
        data = plan(snapshot(), snapshot("older", created_at="2020-01-01T00:00:00Z"))
        before = copy.deepcopy(data)
        guards = (
            patch.object(socket, "socket", side_effect=AssertionError("No sockets")),
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("No connections"),
            ),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("No DNS")),
            patch("subprocess.Popen", side_effect=AssertionError("No process")),
            patch("subprocess.run", side_effect=AssertionError("No process")),
            patch.object(os, "system", side_effect=AssertionError("No shell")),
            patch.object(os, "execv", side_effect=AssertionError("No exec")),
            patch("builtins.open", side_effect=AssertionError("No backup reads")),
            patch("io.open", side_effect=AssertionError("No backup reads")),
            patch.object(os, "open", side_effect=AssertionError("No backup reads")),
            patch.object(os, "stat", side_effect=AssertionError("No backup metadata")),
            patch.object(os, "lstat", side_effect=AssertionError("No backup metadata")),
            patch.object(os, "listdir", side_effect=AssertionError("No inventory")),
            patch.object(os, "scandir", side_effect=AssertionError("No inventory")),
            patch.object(os, "remove", side_effect=AssertionError("No deletion")),
            patch.object(os, "unlink", side_effect=AssertionError("No deletion")),
            patch.object(os, "rmdir", side_effect=AssertionError("No deletion")),
            patch.object(os, "rename", side_effect=AssertionError("No moving")),
            patch.object(os, "replace", side_effect=AssertionError("No replacement")),
            patch.object(shutil, "copyfile", side_effect=AssertionError("No copying")),
            patch.object(shutil, "copy2", side_effect=AssertionError("No copying")),
            patch.object(shutil, "rmtree", side_effect=AssertionError("No deletion")),
        )
        with contextlib.ExitStack() as stack:
            for guard in guards:
                stack.enter_context(guard)
            result = checker.plan_retention(data)
        self.assertEqual(result["counts"]["review"], 1)
        self.assertEqual(data, before)

    def test_age_decisions_use_explicit_metadata_instead_of_current_time(self):
        data = plan(
            snapshot("latest", created_at="1980-01-02T00:00:00Z"),
            snapshot("cutoff", created_at="1980-01-01T00:00:00Z"),
            as_of="1980-01-02T00:00:00Z",
            keep_days=1,
        )

        class NoClock(calendar.datetime):
            @classmethod
            def now(cls, *args, **kwargs):
                raise AssertionError("No datetime clock")

            @classmethod
            def utcnow(cls, *args, **kwargs):
                raise AssertionError("No UTC datetime clock")

            @classmethod
            def today(cls, *args, **kwargs):
                raise AssertionError("No date clock")

        with (
            patch.object(checker, "datetime", NoClock),
            patch.object(time, "time", side_effect=AssertionError("No clock")),
            patch.object(
                time, "localtime", side_effect=AssertionError("No local clock")
            ),
            patch.object(time, "gmtime", side_effect=AssertionError("No UTC clock")),
        ):
            result = checker.plan_retention(data)
        self.assertEqual(self.by_id(result)["cutoff"]["reasons"], ["WITHIN_AGE_WINDOW"])


class GuardedInputTests(RetentionFixture):
    def test_utf8_bom_exact_size_input_and_original_bytes_are_preserved(self):
        data = plan(snapshot())
        raw = b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8")
        raw += b" " * (65536 - len(raw))
        source = self.metadata(raw=raw)
        self.assertEqual(checker.read_input_json(source), data)
        self.assertEqual(source.read_bytes(), raw)
        source.write_bytes(raw + b" ")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(source)

    def test_duplicate_keys_nonfinite_bad_json_and_encoding_are_refused(self):
        samples = [
            b'{"policy":{},"policy":{}}',
            b'{"snapshots":[{"id":"one","id":"two"}]}',
            b"{",
            b"\xff",
            b"{} trailing",
        ]
        samples.extend(
            b'{"fictional":' + value + b"}"
            for value in (b"NaN", b"Infinity", b"-Infinity")
        )
        for raw in samples:
            source = self.metadata(raw=raw)
            with self.subTest(raw=raw), self.assertRaises(checker.ContractError):
                checker.read_input_json(source)

    def test_missing_nonfile_root_and_unsafe_paths_are_refused(self):
        for path in (
            self.parent / "missing.json",
            self.root,
            Path(self.parent.anchor),
            str(self.parent / "fictional/../plan.json"),
            r"\\fictional-host\share\plan.json",
            "//fictional-host/share/plan.json",
            "Q:fictional-plan.json",
            "CON",
            "NUL",
        ):
            with self.subTest(path=str(path)), self.assertRaises(checker.ContractError):
                checker.read_input_json(path)

    def test_reader_does_not_enumerate_directories(self):
        source = self.metadata(plan(snapshot()))
        with (
            patch.object(os, "listdir", side_effect=AssertionError("No inventory")),
            patch.object(os, "scandir", side_effect=AssertionError("No inventory")),
        ):
            self.assertEqual(checker.read_input_json(source), plan(snapshot()))

    def test_unsafe_input_and_ancestor_metadata_are_refused_before_open(self):
        source = self.metadata(plan(snapshot()))
        original = Path.lstat
        for selected, values in (
            (source, {"st_file_attributes": 0x400}),
            (source, {"st_nlink": 2}),
            (source, {"st_mode": stat.S_IFIFO | 0o600}),
            (source, {"st_ino": 0}),
            (self.parent, {"st_file_attributes": 0x400}),
            (self.parent, {"st_ino": 0}),
        ):

            def unsafe(path):
                info = original(path)
                return changed_stat(info, **values) if path == selected else info

            with self.subTest(selected=selected.name, values=values):
                with (
                    patch.object(Path, "lstat", unsafe),
                    patch.object(
                        os, "open", side_effect=AssertionError("Unsafe input opened")
                    ),
                ):
                    with self.assertRaises(checker.ContractError):
                        checker.read_input_json(source)

    def test_open_and_post_read_metadata_changes_are_refused(self):
        source = self.metadata(plan(snapshot()))
        original = os.fstat
        for after_only in (False, True):
            observations = 0

            def changed(descriptor):
                nonlocal observations
                observations += 1
                info = original(descriptor)
                return (
                    changed_stat(info, st_mtime_ns=info.st_mtime_ns + 1)
                    if not after_only or observations > 1
                    else info
                )

            with (
                self.subTest(after_only=after_only),
                patch.object(os, "fstat", changed),
                self.assertRaises(checker.ContractError),
            ):
                checker.read_input_json(source)

    def test_path_or_ancestor_replacement_after_read_is_refused(self):
        source = self.metadata(plan(snapshot()))
        original = Path.lstat
        for selected in (source, self.parent):
            observations = 0

            def changed(path):
                nonlocal observations
                info = original(path)
                if path == selected:
                    observations += 1
                    if observations > 1:
                        return changed_stat(info, st_ino=info.st_ino + 1)
                return info

            with (
                self.subTest(selected=selected.name),
                patch.object(Path, "lstat", changed),
                self.assertRaises(checker.ContractError),
            ):
                checker.read_input_json(source)

    def test_missing_path_and_native_permission_tracebacks_hide_canaries(self):
        source = self.parent / "fictional-missing-path-canary.json"
        formatted = self.reader_failure_traceback(source)
        for value in (str(source), source.name, "FileNotFoundError"):
            self.assertNotIn(value, formatted)
        source = self.metadata(
            plan(snapshot()), name="fictional-input-path-canary.json"
        )
        message = "fictional-sensitive-native-canary"
        original = Path.lstat

        def denied(path):
            if path == source:
                raise PermissionError(13, message, str(source))
            return original(path)

        with patch.object(Path, "lstat", denied):
            formatted = self.reader_failure_traceback(source)
        for value in (str(source), source.name, message, "PermissionError"):
            self.assertNotIn(value, formatted)

    def test_unicode_json_and_recursion_tracebacks_hide_native_messages(self):
        source = self.metadata(
            plan(snapshot()), name="fictional-decoder-path-canary.json"
        )
        canary = "fictional-sensitive-decoder-canary"
        errors = (
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, canary),
            json.JSONDecodeError(canary, "{}", 0),
            RecursionError(canary),
        )
        for native_error in errors:
            with self.subTest(error_type=type(native_error).__name__):
                with patch.object(checker.json, "loads", side_effect=native_error):
                    formatted = self.reader_failure_traceback(source)
                for value in (
                    str(source),
                    source.name,
                    canary,
                    type(native_error).__name__,
                ):
                    self.assertNotIn(value, formatted)

    def test_native_symlink_input_is_refused(self):
        source = self.metadata(plan(snapshot()))
        alias = self.parent / "fictional-alias.json"
        try:
            alias.symlink_to(source)
        except OSError:
            self.skipTest("Native symlink creation is unavailable")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(alias)

    def test_native_hardlink_input_is_refused(self):
        source = self.metadata(plan(snapshot()))
        alias = self.parent / "fictional-alias.json"
        try:
            os.link(source, alias)
        except OSError:
            self.skipTest("Native hardlink creation is unavailable")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(source)


class RetentionCliTests(RetentionFixture):
    def test_cli_keep_and_review_exit_codes_preserve_metadata(self):
        cases = (
            (plan(snapshot()), 0),
            (plan(snapshot(), snapshot("old", created_at="2020-01-01T00:00:00Z")), 1),
            (plan(snapshot(), keep_latest=2), 1),
        )
        for data, expected in cases:
            source = self.metadata(data)
            before = source.read_bytes()
            code, output, errors = self.invoke("--plan", source)
            self.assertEqual(code, expected, output + errors)
            self.assertEqual(errors, "")
            self.assertEqual(source.read_bytes(), before)
            self.assertNotIn(str(source), output)
            self.assertNotIn(data["as_of"], output)

    def test_cli_invalid_input_has_fixed_schema_without_raw_values(self):
        canary = "fictional-sensitive-input-canary"
        source = self.metadata({**plan(snapshot()), "private_value": canary})
        for args in (
            ("--plan", source),
            ("--plan", self.parent / "fictional-missing-path-canary.json"),
            ("--unknown", canary),
            ("--plan", source, "--report", self.parent / "must-not-create.json"),
            ("--plan", source, "--delete"),
        ):
            with self.subTest(args=args):
                code, output, errors = self.invoke(*args)
                self.assertEqual(code, 2, output + errors)
                result = json.loads(output)
                self.assertEqual(
                    set(result),
                    {
                        "status",
                        "code",
                        "filesystem_scanned",
                        "backup_contents_verified",
                        "metadata_verified",
                        "deletion_performed",
                        "deletion_authorized",
                        "network_probed",
                    },
                )
                self.assertEqual(result["status"], "ERROR")
                for flag in (
                    "filesystem_scanned",
                    "backup_contents_verified",
                    "metadata_verified",
                    "deletion_performed",
                    "deletion_authorized",
                    "network_probed",
                ):
                    self.assertIs(result[flag], False)
                for value in (
                    str(self.parent),
                    "fictional-missing-path-canary.json",
                    canary,
                    "Traceback",
                ):
                    self.assertNotIn(value, output + errors)
        self.assertFalse((self.parent / "must-not-create.json").exists())

    def test_abbreviated_flags_are_refused_before_input_reading(self):
        source = self.metadata(plan(snapshot()))
        for argument in ("--pl", "--pla"):
            with patch.object(
                checker,
                "read_input_json",
                side_effect=AssertionError("Unexpected input read"),
            ):
                code, output, errors = self.invoke(argument, source)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output)["status"], "ERROR")
            self.assertNotIn(str(source), output + errors)

    def test_interrupt_keeps_all_six_action_verification_flags_false(self):
        source = self.metadata(plan(snapshot()))
        with patch.object(checker, "read_input_json", side_effect=KeyboardInterrupt):
            code, output, errors = self.invoke("--plan", source)
        self.assertEqual(code, 130)
        result = json.loads(output)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["code"], "INTERRUPTED")
        self.assertEqual(
            set(result),
            {
                "status",
                "code",
                "filesystem_scanned",
                "backup_contents_verified",
                "metadata_verified",
                "deletion_performed",
                "deletion_authorized",
                "network_probed",
            },
        )
        for key, value in result.items():
            if key not in ("status", "code"):
                self.assertIs(value, False)
        self.assertEqual(errors, "")

    def test_help_and_version_are_static(self):
        for argument in ("--help", "--version"):
            output, errors = io.StringIO(), io.StringIO()
            with (
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(errors),
                self.assertRaises(SystemExit) as stopped,
            ):
                checker.main([argument])
            self.assertEqual(stopped.exception.code, 0)
            self.assertNotIn(str(ROOT), output.getvalue() + errors.getvalue())

    def test_actual_cli_is_stdout_only_and_leaves_all_fixture_files_unchanged(self):
        source = self.metadata(
            plan(snapshot(), snapshot("older", created_at="2020-01-01T00:00:00Z"))
        )
        backup_canary = self.write(
            "fictional-backup.txt", "Fictional backup bytes must remain unchanged.\n"
        )
        preserved = {path: path.read_bytes() for path in (source, backup_canary)}
        names_before = {path.name for path in self.parent.iterdir()}
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/backup-retention-planner/retention_plan.py"),
                "--plan",
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        self.assertEqual(json.loads(process.stdout)["status"], "REVIEW_REQUIRED")
        self.assertEqual(process.stderr, "")
        for path, raw in preserved.items():
            self.assertEqual(path.read_bytes(), raw)
            self.assertNotIn(str(path), process.stdout)
        self.assertEqual({path.name for path in self.parent.iterdir()}, names_before)


if __name__ == "__main__":
    unittest.main()
