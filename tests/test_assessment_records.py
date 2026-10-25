"""Fictional assessment workflow metadata; no assessments or target activity."""

import contextlib
import copy
import io
import json
import os
from pathlib import Path
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
    "assessment_record_checker",
    "tools/assessment-record-checker/assessment_check.py",
)


def submission(
    identifier="original", *, series_id="fictional_series", revision=1, **extra
):
    return {"id": identifier, "series_id": series_id, "revision": revision, **extra}


def finding(
    identifier="fictional_finding",
    *,
    submission_id="original",
    state="open",
    selected_retest_id=None,
    **extra,
):
    return {
        "id": identifier,
        "submission_id": submission_id,
        "state": state,
        "selected_retest_id": selected_retest_id,
        **extra,
    }


def retest(
    identifier="fictional_retest",
    *,
    finding_id="fictional_finding",
    submission_id="replacement",
    outcome="not_run",
    **extra,
):
    return {
        "id": identifier,
        "finding_id": finding_id,
        "submission_id": submission_id,
        "outcome": outcome,
        **extra,
    }


def records(*submissions, findings=(), retests=()):
    return {
        "schema_version": 1,
        "submissions": list(submissions),
        "findings": list(findings),
        "retests": list(retests),
    }


def changed_stat(info, **values):
    fields = {
        name: getattr(info, name)
        for name in dir(info)
        if name.startswith("st_") and not callable(getattr(info, name))
    }
    fields.update(values)
    return SimpleNamespace(**fields)


class RecordFixture(Fixture):
    def metadata(self, value=None, *, raw=None, name="fictional-records.json"):
        source = self.parent / name
        source.write_bytes(json.dumps(value).encode("utf-8") if raw is None else raw)
        return source

    def selected_records(self, *, state="closure_claimed", outcome="not_observed"):
        return records(
            submission(),
            submission("replacement", revision=2),
            findings=[finding(state=state, selected_retest_id="fictional_retest")],
            retests=[retest(outcome=outcome)],
        )

    def by_id(self, result):
        return {row["id"]: row for row in result["checks"]}

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


class RecordSchemaTests(RecordFixture):
    def test_parse_copies_all_collection_rows_and_preserves_input(self):
        data = self.selected_records()
        before = copy.deepcopy(data)
        parsed = checker.parse_records(data)
        self.assertEqual(parsed, data)
        self.assertIsNot(parsed, data)
        for name in ("submissions", "findings", "retests"):
            self.assertIsNot(parsed[name], data[name])
            for actual, original in zip(parsed[name], data[name]):
                self.assertIsNot(actual, original)
        parsed["submissions"][0]["revision"] = 5
        parsed["findings"][0]["state"] = "open"
        parsed["retests"][0]["outcome"] = "still_present"
        self.assertEqual(data, before)
        checker.check_records(data)
        self.assertEqual(data, before)

    def test_root_schema_is_exact_and_collections_are_lists(self):
        valid = records(submission())
        invalid = [
            None,
            [],
            "fictional",
            {},
            {**valid, "narrative": "fictional-sensitive-canary"},
        ]
        invalid.extend(
            {key: value for key, value in valid.items() if key != removed}
            for removed in valid
        )
        invalid.extend(
            {**valid, "schema_version": value} for value in (None, True, 1.0, "1", 0, 2)
        )
        for name in ("submissions", "findings", "retests"):
            invalid.extend(
                {**valid, name: value} for value in (None, {}, "fictional", ())
            )
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(checker.ContractError):
                checker.parse_records(data)

    def test_entity_shapes_reject_missing_extra_and_untyped_rows(self):
        for name, sample in (
            ("submissions", submission()),
            ("findings", finding()),
            ("retests", retest()),
        ):
            invalid = [
                None,
                [],
                {},
                "fictional",
                {**sample, "evidence_path": "fictional/private/evidence"},
            ]
            invalid.extend(
                {key: value for key, value in sample.items() if key != removed}
                for removed in sample
            )
            for row in invalid:
                data = records(submission())
                data[name] = [row]
                with (
                    self.subTest(collection=name, row=row),
                    self.assertRaises(checker.ContractError),
                ):
                    checker.parse_records(data)

    def test_entity_ids_link_tokens_and_series_labels_use_neutral_id_syntax(self):
        invalid = (
            None,
            True,
            1,
            [],
            {},
            "",
            "A",
            "1record",
            "a b",
            "a/b",
            "a" * 41,
            "café",
        )
        for name, token in (
            ("submissions", "id"),
            ("submissions", "series_id"),
            ("findings", "id"),
            ("findings", "submission_id"),
            ("retests", "id"),
            ("retests", "finding_id"),
            ("retests", "submission_id"),
            ("findings", "selected_retest_id"),
        ):
            for value in invalid:
                if token == "selected_retest_id" and value is None:
                    continue
                data = self.selected_records()
                data[name][0][token] = value
                with (
                    self.subTest(collection=name, token=token, value=value),
                    self.assertRaises(checker.ContractError),
                ):
                    checker.parse_records(data)
        for identifier in ("a", "a" * 40, "fictional_record-1"):
            self.assertEqual(
                checker.parse_records(records(submission(identifier)))["submissions"][
                    0
                ]["id"],
                identifier,
            )

    def test_ids_are_global_but_series_labels_are_a_separate_namespace(self):
        invalid = (
            records(submission("same"), submission("same", revision=2)),
            records(submission("same"), findings=[finding("same")]),
            records(submission(), findings=[finding("same"), finding("same")]),
            records(submission(), findings=[finding("same")], retests=[retest("same")]),
            records(
                submission(),
                retests=[retest("same"), retest("same", submission_id="another")],
            ),
        )
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(checker.ContractError):
                checker.parse_records(data)
        data = records(
            submission("shared_label", series_id="shared_label"),
            submission("replacement", series_id="shared_label", revision=2),
        )
        self.assertEqual(
            checker.check_records(data)["status"], "DECLARED_RECORDS_CONSISTENT"
        )

    def test_revisions_are_plain_bounded_integers_and_series_revision_pairs_unique(
        self,
    ):
        for revision in (None, True, False, 1.0, "1", [], {}, 0, -1, 1000000001):
            with (
                self.subTest(revision=revision),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_records(records(submission(revision=revision)))
        for revision in (1, 1000000000):
            self.assertEqual(
                checker.parse_records(records(submission(revision=revision)))[
                    "submissions"
                ][0]["revision"],
                revision,
            )
        with self.assertRaises(checker.ContractError):
            checker.parse_records(records(submission(), submission("duplicate")))
        self.assertEqual(
            len(
                checker.parse_records(
                    records(
                        submission(), submission("other", series_id="another_series")
                    )
                )["submissions"]
            ),
            2,
        )

    def test_states_outcomes_and_selected_tokens_are_exact(self):
        for state in (
            None,
            True,
            1,
            [],
            {},
            "Open",
            "closed",
            "pending",
            "closure_claimed ",
        ):
            with self.subTest(state=state), self.assertRaises(checker.ContractError):
                checker.parse_records(
                    records(submission(), findings=[finding(state=state)])
                )
        for outcome in (None, True, 1, [], {}, "pass", "Not_Observed", "not_observed "):
            with (
                self.subTest(outcome=outcome),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_records(
                    records(submission(), retests=[retest(outcome=outcome)])
                )
        for outcome in ("not_run", "still_present", "not_observed", "inconclusive"):
            self.assertEqual(
                checker.parse_records(
                    records(submission(), retests=[retest(outcome=outcome)])
                )["retests"][0]["outcome"],
                outcome,
            )

    def test_one_retest_summary_per_finding_and_submission_pair(self):
        with self.assertRaises(checker.ContractError):
            checker.parse_records(
                records(
                    submission(),
                    retests=[retest("one"), retest("two", outcome="not_observed")],
                )
            )
        data = records(
            submission(),
            retests=[
                retest("one"),
                retest("two", finding_id="another_finding"),
                retest("three", submission_id="another_submission"),
            ],
        )
        self.assertEqual(len(checker.parse_records(data)["retests"]), 3)

    def test_collection_and_total_bounds_accept_full_supported_ledgers(self):
        submissions = [
            submission("submission_" + str(index), revision=index + 1)
            for index in range(128)
        ]
        findings = [
            finding("finding_" + str(index), submission_id="submission_" + str(index))
            for index in range(128)
        ]
        result = checker.check_records(records(*submissions, findings=findings))
        self.assertEqual(
            result["counts"],
            {
                "passed": 256,
                "failed": 0,
                "blocked": 0,
                "submissions": 128,
                "findings": 128,
                "retests": 0,
            },
        )
        retests = [
            retest("retest_" + str(index), finding_id="missing_" + str(index))
            for index in range(128)
        ]
        self.assertEqual(
            len(
                checker.parse_records(records(submission(), retests=retests))["retests"]
            ),
            128,
        )
        invalid = (
            records(),
            records(*submissions, submission("extra", revision=129)),
            records(submission(), findings=[*findings, finding("extra")]),
            records(
                submission(),
                retests=[*retests, retest("extra", finding_id="extra_finding")],
            ),
            records(*submissions, findings=findings, retests=[retest()]),
        )
        for data in invalid:
            with (
                self.subTest(
                    counts=tuple(
                        len(data[name])
                        for name in ("submissions", "findings", "retests")
                    )
                ),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_records(data)


class RelationshipTests(RecordFixture):
    def test_submission_only_ledger_is_consistent(self):
        result = checker.check_records(records(submission()))
        self.assertEqual(result["status"], "DECLARED_RECORDS_CONSISTENT")
        self.assertEqual(
            result["checks"],
            [
                {
                    "id": "original",
                    "kind": "submission",
                    "status": "PASS",
                    "evidence": "SUBMISSION_DECLARATION_VALID",
                }
            ],
        )

    def test_open_null_selection_can_have_historical_retests_without_closing(self):
        data = records(
            submission(),
            submission("replacement", revision=2),
            findings=[finding()],
            retests=[retest(outcome="not_observed")],
        )
        result = checker.check_records(data)
        self.assertEqual(result["status"], "DECLARED_RECORDS_CONSISTENT")
        self.assertEqual(
            self.by_id(result)["fictional_finding"]["evidence"],
            "OPEN_RECORD_CONSISTENT",
        )
        self.assertEqual(
            self.by_id(result)["fictional_retest"]["evidence"],
            "RETEST_RELATIONSHIPS_CONSISTENT",
        )
        self.assertIs(result["outcomes_verified"], False)

    def test_open_record_with_any_selected_retest_is_inconsistent(self):
        for selected in ("fictional_retest", "missing_retest"):
            data = self.selected_records(state="open")
            data["findings"][0]["selected_retest_id"] = selected
            row = self.by_id(checker.check_records(data))["fictional_finding"]
            self.assertEqual(
                (row["status"], row["evidence"]), ("FAIL", "OPEN_HAS_SELECTED_RETEST")
            )

    def test_pending_and_closure_require_explicit_declared_selection(self):
        for state in ("retest_pending", "closure_claimed"):
            for selected, evidence in (
                (None, "SELECTED_RETEST_NOT_SUPPLIED"),
                ("missing_retest", "SELECTED_RETEST_NOT_DECLARED"),
                ("original", "SELECTED_RETEST_NOT_DECLARED"),
            ):
                data = self.selected_records(state=state)
                data["findings"][0]["selected_retest_id"] = selected
                row = self.by_id(checker.check_records(data))["fictional_finding"]
                self.assertEqual(
                    (row["status"], row["evidence"]), ("BLOCKED", evidence)
                )

    def test_finding_original_reference_is_typed_and_required(self):
        for original in ("missing_original", "fictional_finding", "fictional_retest"):
            data = self.selected_records()
            data["findings"][0]["submission_id"] = original
            result = checker.check_records(data)
            self.assertEqual(
                self.by_id(result)["fictional_finding"]["evidence"],
                "ORIGINAL_SUBMISSION_NOT_DECLARED",
            )
            self.assertEqual(
                self.by_id(result)["fictional_finding"]["status"], "BLOCKED"
            )
            self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_retest_missing_typed_references_are_blocked_with_fixed_precedence(self):
        cases = (
            ("finding_id", "missing_finding", "FINDING_NOT_DECLARED"),
            ("finding_id", "original", "FINDING_NOT_DECLARED"),
            (
                "submission_id",
                "missing_replacement",
                "REPLACEMENT_SUBMISSION_NOT_DECLARED",
            ),
            (
                "submission_id",
                "fictional_finding",
                "REPLACEMENT_SUBMISSION_NOT_DECLARED",
            ),
        )
        for key, value, evidence in cases:
            data = self.selected_records()
            data["retests"][0][key] = value
            result = checker.check_records(data)
            row = self.by_id(result)["fictional_retest"]
            self.assertEqual((row["status"], row["evidence"]), ("BLOCKED", evidence))
            self.assertEqual(result["status"], "REVIEW_REQUIRED")
        data = self.selected_records()
        data["findings"][0]["submission_id"] = "missing_original"
        data["retests"][0]["submission_id"] = "missing_replacement"
        row = self.by_id(checker.check_records(data))["fictional_retest"]
        self.assertEqual(
            (row["status"], row["evidence"]),
            ("BLOCKED", "ORIGINAL_SUBMISSION_NOT_DECLARED"),
        )

    def test_cross_series_and_nonlater_replacements_fail_relationship_checks(self):
        cross_series = self.selected_records()
        cross_series["submissions"][1]["series_id"] = "another_series"
        same_submission = self.selected_records()
        same_submission["retests"][0]["submission_id"] = "original"
        older = self.selected_records()
        older["submissions"][0]["revision"] = 3
        for data, evidence in (
            (cross_series, "SERIES_MISMATCH"),
            (same_submission, "REPLACEMENT_NOT_LATER"),
            (older, "REPLACEMENT_NOT_LATER"),
        ):
            result = checker.check_records(data)
            self.assertEqual(self.by_id(result)["fictional_retest"]["status"], "FAIL")
            self.assertEqual(
                self.by_id(result)["fictional_retest"]["evidence"], evidence
            )
            self.assertEqual(
                self.by_id(result)["fictional_finding"]["evidence"],
                "SELECTED_RETEST_INVALID",
            )
            self.assertEqual(
                self.by_id(result)["fictional_finding"]["status"], "BLOCKED"
            )

    def test_selected_retest_must_belong_to_the_finding(self):
        data = records(
            submission(),
            submission("replacement", revision=2),
            findings=[
                finding("one", state="closure_claimed", selected_retest_id="selected"),
                finding("two"),
            ],
            retests=[retest("selected", finding_id="two", outcome="not_observed")],
        )
        result = checker.check_records(data)
        self.assertEqual(
            (
                self.by_id(result)["one"]["status"],
                self.by_id(result)["one"]["evidence"],
            ),
            ("FAIL", "SELECTED_RETEST_FINDING_MISMATCH"),
        )
        self.assertEqual(self.by_id(result)["two"]["status"], "PASS")
        self.assertEqual(self.by_id(result)["selected"]["status"], "PASS")

    def test_selected_invalid_relationship_blocks_before_outcome_or_latest_checks(self):
        data = self.selected_records(outcome="not_observed")
        data["retests"][0]["submission_id"] = "missing_replacement"
        result = checker.check_records(data)
        row = self.by_id(result)["fictional_finding"]
        self.assertEqual(
            (row["status"], row["evidence"]), ("BLOCKED", "SELECTED_RETEST_INVALID")
        )

    def test_pending_and_closure_require_latest_declared_revision_in_original_series(
        self,
    ):
        for state, outcome in (
            ("retest_pending", "not_run"),
            ("closure_claimed", "not_observed"),
        ):
            data = self.selected_records(state=state, outcome=outcome)
            data["submissions"].insert(
                0, submission("latest_without_retest", revision=3)
            )
            result = checker.check_records(data)
            row = self.by_id(result)["fictional_finding"]
            self.assertEqual(
                (row["status"], row["evidence"]),
                ("FAIL", "SELECTED_SUBMISSION_NOT_LATEST_DECLARED"),
            )
            self.assertEqual(self.by_id(result)["fictional_retest"]["status"], "PASS")

    def test_latest_is_numeric_within_series_and_independent_of_array_order(self):
        data = records(
            submission("latest", revision=3),
            submission("unrelated", series_id="another_series", revision=1000000000),
            submission(),
            submission("historical", revision=2),
            findings=[finding(state="closure_claimed", selected_retest_id="selected")],
            retests=[
                retest("selected", submission_id="latest", outcome="not_observed"),
                retest("history", submission_id="historical", outcome="still_present"),
            ],
        )
        for reverse in (False, True):
            candidate = copy.deepcopy(data)
            if reverse:
                candidate["submissions"].reverse()
                candidate["retests"].reverse()
            result = checker.check_records(candidate)
            self.assertEqual(result["status"], "DECLARED_RECORDS_CONSISTENT")
            self.assertEqual(
                self.by_id(result)["fictional_finding"]["evidence"],
                "CLOSURE_CLAIM_CONSISTENT",
            )
            self.assertEqual(result["counts"]["passed"], 7)

    def test_pending_outcome_matrix_requires_not_run(self):
        for outcome in ("not_run", "still_present", "not_observed", "inconclusive"):
            result = checker.check_records(
                self.selected_records(state="retest_pending", outcome=outcome)
            )
            row = self.by_id(result)["fictional_finding"]
            self.assertEqual(
                (row["status"], row["evidence"]),
                ("PASS", "PENDING_RECORD_CONSISTENT")
                if outcome == "not_run"
                else ("FAIL", "PENDING_OUTCOME_INCONSISTENT"),
            )
            self.assertEqual(self.by_id(result)["fictional_retest"]["status"], "PASS")
            self.assertIs(result["outcomes_verified"], False)

    def test_closure_outcome_matrix_requires_not_observed(self):
        for outcome in ("not_run", "still_present", "not_observed", "inconclusive"):
            result = checker.check_records(self.selected_records(outcome=outcome))
            row = self.by_id(result)["fictional_finding"]
            self.assertEqual(
                (row["status"], row["evidence"]),
                ("PASS", "CLOSURE_CLAIM_CONSISTENT")
                if outcome == "not_observed"
                else ("FAIL", "CLOSURE_OUTCOME_NOT_SUPPORTING"),
            )
            self.assertEqual(self.by_id(result)["fictional_retest"]["status"], "PASS")
            self.assertIs(result["outcomes_verified"], False)

    def test_unselected_invalid_retests_still_require_review(self):
        data = records(
            submission(),
            findings=[finding()],
            retests=[retest(submission_id="missing_replacement")],
        )
        result = checker.check_records(data)
        self.assertEqual(self.by_id(result)["fictional_finding"]["status"], "PASS")
        self.assertEqual(self.by_id(result)["fictional_retest"]["status"], "BLOCKED")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")


class RecordPrivacyTests(RecordFixture):
    def test_report_is_fixed_id_only_metadata_in_declaration_order(self):
        data = self.selected_records()
        result = checker.check_records(data)
        self.assertEqual(
            set(result),
            {
                "schema_version",
                "status",
                "scope",
                "execution_performed",
                "network_probed",
                "records_modified",
                "authorization_verified",
                "isolation_verified",
                "outcomes_verified",
                "counts",
                "checks",
            },
        )
        self.assertEqual(result["scope"], "DECLARED_ASSESSMENT_RECORDS_ONLY")
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(
            result["counts"],
            {
                "passed": 4,
                "failed": 0,
                "blocked": 0,
                "submissions": 2,
                "findings": 1,
                "retests": 1,
            },
        )
        self.assertEqual(
            [row["id"] for row in result["checks"]],
            ["original", "replacement", "fictional_finding", "fictional_retest"],
        )
        self.assertEqual(
            [row["kind"] for row in result["checks"]],
            ["submission", "submission", "finding", "retest"],
        )
        for row in result["checks"]:
            self.assertEqual(set(row), {"id", "kind", "status", "evidence"})
        for flag in (
            "execution_performed",
            "network_probed",
            "records_modified",
            "authorization_verified",
            "isolation_verified",
            "outcomes_verified",
        ):
            self.assertIs(result[flag], False)

    def test_report_does_not_echo_series_revision_link_tokens_or_workflow_values(self):
        data = self.selected_records()
        data["submissions"][0].update(
            series_id="fictional_sensitive_series", revision=987654321
        )
        data["submissions"][1].update(
            series_id="fictional_sensitive_series", revision=987654322
        )
        data["findings"].append(
            finding(
                "missing_link_finding", submission_id="fictional_sensitive_missing_link"
            )
        )
        raw = json.dumps(checker.check_records(data))
        for value in (
            "fictional_sensitive_series",
            "987654321",
            "987654322",
            "fictional_sensitive_missing_link",
            str(self.parent),
            '"series_id"',
            '"revision"',
            '"submission_id"',
            '"finding_id"',
            '"selected_retest_id"',
            '"state"',
            '"outcome"',
            '"closure_claimed"',
            '"not_observed"',
        ):
            self.assertNotIn(value, raw)

    def test_mixed_relationship_statuses_have_consistent_counts(self):
        data = records(
            submission(),
            submission("replacement", revision=2),
            findings=[
                finding(
                    "closed", state="closure_claimed", selected_retest_id="bad_outcome"
                ),
                finding("missing", submission_id="absent_submission"),
                finding("open"),
            ],
            retests=[
                retest("bad_outcome", finding_id="closed", outcome="still_present"),
                retest("orphan", finding_id="absent_finding"),
            ],
        )
        result = checker.check_records(data)
        self.assertEqual(
            result["counts"],
            {
                "passed": 4,
                "failed": 1,
                "blocked": 2,
                "submissions": 2,
                "findings": 3,
                "retests": 2,
            },
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_evaluation_has_no_target_network_process_clock_or_file_activity(self):
        data = self.selected_records()
        before = copy.deepcopy(data)
        guards = (
            patch.object(socket, "socket", side_effect=AssertionError("No sockets")),
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("No connections"),
            ),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("No DNS")),
            patch("subprocess.Popen", side_effect=AssertionError("No execution")),
            patch("subprocess.run", side_effect=AssertionError("No execution")),
            patch.object(os, "system", side_effect=AssertionError("No shell")),
            patch.object(os, "execv", side_effect=AssertionError("No exec")),
            patch("builtins.open", side_effect=AssertionError("No target reads")),
            patch("io.open", side_effect=AssertionError("No target reads")),
            patch.object(os, "open", side_effect=AssertionError("No target reads")),
            patch.object(os, "stat", side_effect=AssertionError("No target metadata")),
            patch.object(os, "lstat", side_effect=AssertionError("No target metadata")),
            patch.object(os, "listdir", side_effect=AssertionError("No scanning")),
            patch.object(os, "scandir", side_effect=AssertionError("No scanning")),
            patch.object(os, "remove", side_effect=AssertionError("No deletion")),
            patch.object(os, "unlink", side_effect=AssertionError("No deletion")),
            patch.object(os, "rename", side_effect=AssertionError("No mutation")),
            patch.object(os, "replace", side_effect=AssertionError("No mutation")),
            patch.object(
                os, "getenv", side_effect=AssertionError("No environment reads")
            ),
            patch.object(time, "time", side_effect=AssertionError("No clock")),
            patch.object(
                time, "localtime", side_effect=AssertionError("No local clock")
            ),
            patch.object(time, "gmtime", side_effect=AssertionError("No UTC clock")),
        )
        with contextlib.ExitStack() as stack:
            for guard in guards:
                stack.enter_context(guard)
            result = checker.check_records(data)
        self.assertEqual(result["status"], "DECLARED_RECORDS_CONSISTENT")
        self.assertEqual(data, before)


class GuardedInputTests(RecordFixture):
    def test_utf8_bom_size_limit_and_original_bytes(self):
        data = self.selected_records()
        raw = b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8")
        raw += b" " * (65536 - len(raw))
        source = self.metadata(raw=raw)
        self.assertEqual(checker.read_input_json(source), data)
        self.assertEqual(source.read_bytes(), raw)
        source.write_bytes(raw + b" ")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(source)

    def test_duplicate_json_keys_nonfinite_values_and_invalid_encoding(self):
        samples = [
            b'{"submissions":[],"submissions":[]}',
            b'{"findings":[{"id":"one","id":"two"}]}',
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
            str(self.parent / "fictional/../records.json"),
            r"\\fictional-host\share\records.json",
            "//fictional-host/share/records.json",
            "Q:fictional-records.json",
            "NUL",
            "CON",
        ):
            with self.subTest(path=str(path)), self.assertRaises(checker.ContractError):
                checker.read_input_json(path)

    def test_reader_does_not_enumerate_directories(self):
        source = self.metadata(records(submission()))
        with (
            patch.object(os, "listdir", side_effect=AssertionError("No inventory")),
            patch.object(os, "scandir", side_effect=AssertionError("No inventory")),
        ):
            self.assertEqual(checker.read_input_json(source), records(submission()))

    def test_unsafe_input_and_ancestor_metadata_are_refused_before_open(self):
        source = self.metadata(records(submission()))
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

    def test_opened_and_post_read_metadata_changes_are_refused(self):
        source = self.metadata(records(submission()))
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
        source = self.metadata(records(submission()))
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

    def test_missing_path_and_permission_tracebacks_hide_native_canaries(self):
        source = self.parent / "fictional-missing-path-canary.json"
        formatted = self.reader_failure_traceback(source)
        for value in (str(source), source.name, "FileNotFoundError"):
            self.assertNotIn(value, formatted)
        source = self.metadata(
            records(submission()), name="fictional-input-path-canary.json"
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
            records(submission()), name="fictional-decoder-path-canary.json"
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
        source = self.metadata(records(submission()))
        alias = self.parent / "fictional-alias.json"
        try:
            alias.symlink_to(source)
        except OSError:
            self.skipTest("Native symlink creation is unavailable")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(alias)

    def test_native_hardlink_input_is_refused(self):
        source = self.metadata(records(submission()))
        alias = self.parent / "fictional-alias.json"
        try:
            os.link(source, alias)
        except OSError:
            self.skipTest("Native hardlink creation is unavailable")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(source)


class RecordCliTests(RecordFixture):
    def test_cli_consistent_and_review_exit_codes_preserve_input(self):
        for data, expected in (
            (self.selected_records(), 0),
            (self.selected_records(outcome="still_present"), 1),
        ):
            source = self.metadata(data)
            before = source.read_bytes()
            code, output, errors = self.invoke("--records", source)
            self.assertEqual(code, expected, output + errors)
            self.assertEqual(errors, "")
            self.assertEqual(source.read_bytes(), before)
            self.assertNotIn(str(source), output)
            self.assertNotIn("fictional_series", output)

    def test_cli_errors_are_fixed_and_do_not_echo_values_or_paths(self):
        canary = "fictional-sensitive-narrative-canary"
        source = self.metadata({**records(submission()), "narrative": canary})
        for args in (
            ("--records", source),
            ("--records", self.parent / "fictional-missing-path-canary.json"),
            ("--unknown", canary),
            ("--records", source, "--report", self.parent / "must-not-create.json"),
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
                        "execution_performed",
                        "network_probed",
                        "records_modified",
                        "authorization_verified",
                        "isolation_verified",
                        "outcomes_verified",
                    },
                )
                self.assertEqual(result["status"], "ERROR")
                for flag in (
                    "execution_performed",
                    "network_probed",
                    "records_modified",
                    "authorization_verified",
                    "isolation_verified",
                    "outcomes_verified",
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

    def test_abbreviations_are_refused_before_input_reading(self):
        source = self.metadata(records(submission()))
        for argument in ("--rec", "--record"):
            with patch.object(
                checker,
                "read_input_json",
                side_effect=AssertionError("Unexpected input read"),
            ):
                code, output, errors = self.invoke(argument, source)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output)["status"], "ERROR")
            self.assertNotIn(str(source), output + errors)

    def test_interrupt_has_six_false_flags_and_exit_130(self):
        source = self.metadata(records(submission()))
        with patch.object(checker, "read_input_json", side_effect=KeyboardInterrupt):
            code, output, errors = self.invoke("--records", source)
        self.assertEqual(code, 130)
        result = json.loads(output)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["code"], "INTERRUPTED")
        self.assertEqual(
            set(result),
            {
                "status",
                "code",
                "execution_performed",
                "network_probed",
                "records_modified",
                "authorization_verified",
                "isolation_verified",
                "outcomes_verified",
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

    def test_actual_cli_is_stdout_only_and_preserves_all_fictional_files(self):
        source = self.metadata(self.selected_records(outcome="inconclusive"))
        canary_file = self.write(
            "fictional-record-not-an-input.txt", "Fictional bytes remain unchanged.\n"
        )
        preserved = {path: path.read_bytes() for path in (source, canary_file)}
        names_before = {path.name for path in self.parent.iterdir()}
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/assessment-record-checker/assessment_check.py"),
                "--records",
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
