"""Real SQLite workflows with disposable fictional neutral records only."""

import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch


WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH))
import workbench_core as core  # noqa: E402


REPOSITORY = core.REPOSITORY
PINNED_CONTRACT_SHA256 = (
    "5c81fb4c74aa7126fc7c4e81b30aca138353c8e79ac6edcd5b9d488e72f0439d"
)


def one_submission(revision=1):
    return {
        "schema_version": 1,
        "submissions": [
            {
                "id": "fictional_original",
                "series_id": "fictional_series",
                "revision": revision,
            }
        ],
        "findings": [],
        "retests": [],
    }


def inconsistent_records():
    data = one_submission()
    data["findings"] = [
        {
            "id": "fictional_finding",
            "submission_id": "fictional_original",
            "state": "closure_claimed",
            "selected_retest_id": None,
        }
    ]
    return data


def short_path_alias(path):
    import ctypes

    function = ctypes.windll.kernel32.GetShortPathNameW
    function.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint)
    function.restype = ctypes.c_uint
    output = ctypes.create_unicode_buffer(32768)
    size = function(str(path), output, len(output))
    if not size or size >= len(output):
        return None
    alias = Path(output.value)
    return alias if str(alias).casefold() != str(path).casefold() else None


def changed_stat(info, **values):
    result = {
        name: getattr(info, name)
        for name in dir(info)
        if name.startswith("st_") and not callable(getattr(info, name))
    }
    result.update(values)
    return SimpleNamespace(**result)


class StoreFixture(unittest.TestCase):
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
        self.path = self.parent / "fictional-workspace.db"

    def json_file(self, data, name="fictional-input.json"):
        path = self.parent / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def fixed_failure(self, operation, *forbidden):
        try:
            operation()
        except core.WorkbenchError as error:
            self.assertRegex(str(error), r"\A[A-Z][A-Z0-9_]*\Z")
            self.assertTrue(error.__suppress_context__)
            formatted = "".join(traceback.format_exception(error))
            for value in forbidden:
                self.assertNotIn(str(value), str(error))
                self.assertNotIn(str(value), formatted)
            return str(error)
        self.fail("Expected a fixed workbench error")

    def raw_edit(self, path, statement, parameters=()):
        with contextlib.closing(sqlite3.connect(path)) as connection:
            connection.execute(statement, parameters)
            connection.commit()

    def populated(self):
        core.create_store(self.path)
        return core.save_records(self.path, one_submission(), expected_revision=0)


class ValidationTests(StoreFixture):
    def test_empty_workspace_is_explicit_and_never_claims_contract_success(self):
        empty = core.empty_records()
        self.assertEqual(
            empty,
            {"schema_version": 1, "submissions": [], "findings": [], "retests": []},
        )
        self.assertEqual(
            core.validate_records(empty),
            {
                "status": "REVIEW_REQUIRED",
                "empty": True,
                "issues": ["EMPTY_WORKSPACE"],
                "report": None,
            },
        )
        empty["submissions"].append({"fictional": "changed"})
        self.assertEqual(core.empty_records()["submissions"], [])

    def test_nonempty_validation_matches_pinned_bundled_contract_and_fixtures(self):
        self.assertEqual(
            hashlib.sha256((WORKBENCH / "record_contract.py").read_bytes()).hexdigest(),
            PINNED_CONTRACT_SHA256,
        )
        fixtures = (
            (
                one_submission(),
                "DECLARED_RECORDS_CONSISTENT",
                ["SUBMISSION_DECLARATION_VALID"],
            ),
            (
                inconsistent_records(),
                "REVIEW_REQUIRED",
                ["SUBMISSION_DECLARATION_VALID", "SELECTED_RETEST_NOT_SUPPLIED"],
            ),
            (
                core.demo_records(),
                "DECLARED_RECORDS_CONSISTENT",
                [
                    "SUBMISSION_DECLARATION_VALID",
                    "SUBMISSION_DECLARATION_VALID",
                    "CLOSURE_CLAIM_CONSISTENT",
                    "RETEST_RELATIONSHIPS_CONSISTENT",
                ],
            ),
        )
        for data, status, evidence in fixtures:
            before = copy.deepcopy(data)
            result = core.validate_records(data)
            expected = core.contract.check_records(data)
            self.assertEqual(set(result), {"status", "empty", "issues", "report"})
            self.assertIs(result["empty"], False)
            self.assertEqual(result["status"], status)
            self.assertEqual(result["report"], expected)
            self.assertEqual(
                [row["evidence"] for row in result["report"]["checks"]], evidence
            )
            self.assertEqual(
                [row["status"] for row in result["report"]["checks"]],
                ["PASS", "BLOCKED"]
                if status == "REVIEW_REQUIRED"
                else ["PASS"] * len(evidence),
            )
            self.assertEqual(data, before)

    def test_partial_empty_or_schema_invalid_records_are_not_silently_repaired(self):
        invalid = core.empty_records()
        invalid["findings"] = inconsistent_records()["findings"]
        canary = "fictional-sensitive-narrative-canary"
        for data in (invalid, {**one_submission(), "narrative": canary}):
            before = copy.deepcopy(data)
            self.fixed_failure(lambda: core.validate_records(data), canary)
            self.assertEqual(data, before)


class StoreHistoryTests(StoreFixture):
    def test_new_store_reopens_empty_at_revision_zero_with_init_history(self):
        created = core.create_store(self.path)
        self.assertEqual(set(created), {"revision", "records", "validation", "head"})
        self.assertEqual(created["revision"], 0)
        self.assertEqual(created["records"], core.empty_records())
        self.assertRegex(created["head"], r"\A[0-9a-f]{64}\Z")
        self.assertEqual(core.load_store(self.path), created)
        self.assertEqual(core.load_revision(self.path, 0), created)
        self.assertEqual(
            core.list_history(self.path),
            [
                {
                    "revision": 0,
                    "operation": "INIT",
                    "status": "REVIEW_REQUIRED",
                    "empty": True,
                }
            ],
        )

    def test_demo_is_explicit_new_only_and_preserves_fixture_records(self):
        expected = core.demo_records()
        snapshot = core.create_demo(self.path)
        self.assertEqual(snapshot["records"], expected)
        self.assertEqual(core.list_history(self.path)[0]["operation"], "DEMO")
        before = self.path.read_bytes()
        self.fixed_failure(lambda: core.create_demo(self.path), self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_saves_append_full_snapshots_and_old_revisions_remain_unchanged(self):
        initial = core.create_store(self.path)
        first_data, second_data = one_submission(), inconsistent_records()
        first = core.save_records(self.path, first_data, expected_revision=0)
        second = core.save_records(self.path, second_data, expected_revision=1)
        self.assertEqual((first["revision"], second["revision"]), (1, 2))
        self.assertEqual(first["records"], first_data)
        self.assertEqual(second["records"], second_data)
        self.assertNotEqual(first["head"], second["head"])
        self.assertEqual(core.load_revision(self.path, 0), initial)
        self.assertEqual(core.load_revision(self.path, 1), first)
        self.assertEqual(core.load_store(self.path), second)
        self.assertEqual(
            [row["operation"] for row in core.list_history(self.path)],
            ["INIT", "SAVE", "SAVE"],
        )
        second["records"]["findings"].clear()
        self.assertEqual(core.load_store(self.path)["records"], second_data)

    def test_review_drafts_are_saved_without_state_or_link_repairs(self):
        core.create_store(self.path)
        data = inconsistent_records()
        before = copy.deepcopy(data)
        result = core.save_records(self.path, data, expected_revision=0)
        self.assertEqual(result["records"], before)
        self.assertEqual(result["validation"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(core.load_store(self.path)["records"], before)
        self.assertEqual(data, before)
        self.assertEqual(core.list_history(self.path)[-1]["status"], "REVIEW_REQUIRED")

    def test_later_empty_snapshot_keeps_previous_plaintext_records_in_history(self):
        saved = self.populated()
        empty = core.save_records(self.path, core.empty_records(), expected_revision=1)
        self.assertEqual(empty["revision"], 2)
        self.assertEqual(empty["records"], core.empty_records())
        self.assertEqual(empty["validation"]["issues"], ["EMPTY_WORKSPACE"])
        self.assertEqual(core.load_revision(self.path, 1), saved)
        self.assertEqual(len(core.list_history(self.path)), 3)

    def test_stale_clients_cannot_overwrite_a_newer_revision(self):
        left = core.create_store(self.path)
        right = core.load_store(self.path)
        saved = core.save_records(
            self.path, one_submission(), expected_revision=left["revision"]
        )
        before = self.path.read_bytes()
        self.fixed_failure(
            lambda: core.save_records(
                self.path, inconsistent_records(), expected_revision=right["revision"]
            ),
            self.path,
        )
        self.assertEqual(core.load_store(self.path), saved)
        self.assertEqual(len(core.list_history(self.path)), 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_expected_revisions_or_payloads_leave_store_unchanged(self):
        self.populated()
        before = self.path.read_bytes()
        for revision in (None, True, False, "1", 1.0, -1, 999):
            with self.subTest(revision=revision):
                self.fixed_failure(
                    lambda: core.save_records(
                        self.path, one_submission(2), expected_revision=revision
                    )
                )
                self.assertEqual(self.path.read_bytes(), before)
        invalid = {**one_submission(), "private_value": "fictional-sensitive-canary"}
        self.fixed_failure(
            lambda: core.save_records(self.path, invalid, expected_revision=1),
            "fictional-sensitive-canary",
        )
        self.assertEqual(self.path.read_bytes(), before)

    def test_sqlite_failure_rolls_back_history_and_metadata_together(self):
        saved = self.populated()
        history = core.list_history(self.path)
        original_connect = sqlite3.connect

        def controlled_connect(*args, **kwargs):
            connection = original_connect(*args, **kwargs)

            def deny_metadata_write(action, table, column, database, trigger):
                if table == "metadata" and action in (
                    sqlite3.SQLITE_INSERT,
                    sqlite3.SQLITE_UPDATE,
                    sqlite3.SQLITE_DELETE,
                ):
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            connection.set_authorizer(deny_metadata_write)
            return connection

        with patch.object(core.sqlite3, "connect", side_effect=controlled_connect):
            self.fixed_failure(
                lambda: core.save_records(
                    self.path, one_submission(2), expected_revision=1
                ),
                self.path,
            )
        self.assertEqual(core.load_store(self.path), saved)
        self.assertEqual(core.list_history(self.path), history)

    def test_busy_writer_fails_within_bound_and_commits_nothing(self):
        initial = core.create_store(self.path)
        history = core.list_history(self.path)
        before = self.path.read_bytes()
        script = """
import sqlite3
import sys

connection = None
try:
    connection = sqlite3.connect(sys.argv[1], timeout=0, isolation_level=None)
    connection.execute("BEGIN IMMEDIATE")
    print("LOCKED", flush=True)
    sys.stdin.readline()
    connection.rollback()
except Exception:
    print("LOCK_FAILED", flush=True)
    raise SystemExit(2) from None
finally:
    if connection is not None:
        connection.close()
"""
        child = subprocess.Popen(
            [sys.executable, "-B", "-u", "-c", script, str(self.path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        readiness, signal = [], threading.Event()

        def read_ready():
            readiness.append(child.stdout.readline().strip())
            signal.set()

        reader = threading.Thread(target=read_ready, daemon=True)

        def release_child():
            if child.poll() is None:
                try:
                    child.stdin.write("RELEASE\n")
                    child.stdin.flush()
                except (OSError, ValueError):
                    pass
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            if reader.ident is not None:
                reader.join(1)
            for stream in (child.stdin, child.stdout, child.stderr):
                stream.close()

        self.addCleanup(release_child)
        reader.start()
        try:
            self.assertTrue(signal.wait(5), "CHILD_LOCK_NOT_READY")
            reader.join(1)
            self.assertEqual(readiness, ["LOCKED"])
            started = time.monotonic()
            code = self.fixed_failure(
                lambda: core.save_records(
                    self.path, one_submission(), expected_revision=0
                ),
                self.path,
            )
            elapsed = time.monotonic() - started
            self.assertEqual(code, "STORE_BUSY")
        finally:
            release_child()
        self.assertEqual(child.returncode, 0)
        self.assertLess(elapsed, 8.0)
        self.assertEqual(core.load_store(self.path), initial)
        self.assertEqual(core.list_history(self.path), history)
        self.assertEqual(self.path.read_bytes(), before)

    def test_history_limit_does_not_prune_or_partially_append(self):
        core.create_store(self.path)
        for revision in range(1, 128):
            snapshot = core.save_records(
                self.path, one_submission(revision), expected_revision=revision - 1
            )
            self.assertEqual(snapshot["revision"], revision)
        before = self.path.read_bytes()
        self.fixed_failure(
            lambda: core.save_records(
                self.path, one_submission(128), expected_revision=127
            )
        )
        self.assertEqual(self.path.read_bytes(), before)
        history = core.list_history(self.path)
        self.assertEqual([row["revision"] for row in history], list(range(128)))
        self.assertEqual(
            core.load_revision(self.path, 0)["records"], core.empty_records()
        )

    def test_revision_lookup_rejects_invalid_or_absent_sequence(self):
        self.populated()
        for revision in (None, True, False, "1", 1.0, -1, 2, 999):
            with self.subTest(revision=revision):
                self.fixed_failure(
                    lambda: core.load_revision(self.path, revision), self.path
                )


class NewOnlyHandoffTests(StoreFixture):
    def test_maximum_control_file_import_exports_a_bounded_roundtrip(self):
        data = one_submission()
        raw = b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8")
        raw += b" " * (65536 - len(raw))
        source = self.parent / "maximum-fictional-input.json"
        source.write_bytes(raw)
        core.import_to_new_store(source, self.path)
        output = self.parent / "fictional-roundtrip.json"
        core.export_records(self.path, output)
        self.assertEqual(json.loads(output.read_bytes()), data)
        self.assertLessEqual(output.stat().st_size, 65536)
        imported = core.import_to_new_store(
            output, self.parent / "fictional-roundtrip.db"
        )
        self.assertEqual(imported["records"], data)
        self.assertEqual(source.read_bytes(), raw)

    def test_import_creates_a_new_store_without_modifying_control_json(self):
        data = inconsistent_records()
        source = self.json_file(data)
        before = source.read_bytes()
        result = core.import_to_new_store(source, self.path)
        self.assertEqual(result["revision"], 0)
        self.assertEqual(result["records"], data)
        self.assertEqual(result["validation"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(core.list_history(self.path)[0]["operation"], "IMPORT")
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(core.load_store(self.path), result)

    def test_import_accepts_explicit_relative_json_without_relative_output(self):
        source = self.json_file(one_submission())
        previous = Path.cwd()
        try:
            os.chdir(self.parent)
            result = core.import_to_new_store(Path(source.name), self.path)
        finally:
            os.chdir(previous)
        self.assertEqual(result["records"], one_submission())

    def test_import_never_merges_or_replaces_an_existing_store(self):
        saved = self.populated()
        source = self.json_file(inconsistent_records())
        before_store, before_json = self.path.read_bytes(), source.read_bytes()
        self.fixed_failure(
            lambda: core.import_to_new_store(source, self.path), self.path
        )
        self.assertEqual(self.path.read_bytes(), before_store)
        self.assertEqual(source.read_bytes(), before_json)
        self.assertEqual(core.load_store(self.path), saved)

    def test_export_is_new_only_and_contains_exact_ledger_even_for_review(self):
        core.create_store(self.path)
        snapshot = core.save_records(
            self.path, inconsistent_records(), expected_revision=0
        )
        output = self.parent / "fictional-export.json"
        before = self.path.read_bytes()
        result = core.export_records(self.path, output)
        self.assertEqual(set(result), {"status", "revision", "validation"})
        self.assertEqual(result["revision"], snapshot["revision"])
        self.assertEqual(result["validation"], snapshot["validation"])
        self.assertEqual(
            json.loads(output.read_text(encoding="utf-8")), snapshot["records"]
        )
        original_export = output.read_bytes()
        self.fixed_failure(lambda: core.export_records(self.path, output), output)
        self.assertEqual(output.read_bytes(), original_export)
        self.assertEqual(self.path.read_bytes(), before)

    def test_clone_preserves_history_through_selected_revision_and_forks_independently(
        self,
    ):
        core.create_store(self.path)
        first = core.save_records(self.path, one_submission(), expected_revision=0)
        latest = core.save_records(
            self.path, inconsistent_records(), expected_revision=1
        )
        source_history = core.list_history(self.path)
        output = self.parent / "fictional-recovery.db"
        clone = core.clone_store(self.path, output, revision=1)
        self.assertEqual(clone, first)
        self.assertEqual(core.list_history(output), source_history[:2])
        core.save_records(output, one_submission(3), expected_revision=1)
        self.assertEqual(core.load_store(self.path), latest)
        self.assertEqual(core.list_history(self.path), source_history)
        self.assertNotEqual(core.load_store(output)["head"], latest["head"])

    def test_latest_clone_is_new_only_and_never_overwrites_source_or_destination(self):
        saved = self.populated()
        output = self.parent / "fictional-clone.db"
        self.assertEqual(core.clone_store(self.path, output), saved)
        before_source, before_output = self.path.read_bytes(), output.read_bytes()
        for destination in (self.path, output):
            with self.subTest(destination=destination.name):
                self.fixed_failure(
                    lambda: core.clone_store(self.path, destination), destination
                )
        self.assertEqual(self.path.read_bytes(), before_source)
        self.assertEqual(output.read_bytes(), before_output)

    def test_failed_import_does_not_create_destination_or_rewrite_source(self):
        canary = "fictional-sensitive-input-canary"
        source = self.json_file({**one_submission(), "narrative": canary})
        before = source.read_bytes()
        self.fixed_failure(
            lambda: core.import_to_new_store(source, self.path), canary, source
        )
        self.assertFalse(self.path.exists())
        self.assertEqual(source.read_bytes(), before)


class RecordMutationTests(StoreFixture):
    def test_put_adds_or_updates_only_the_explicit_immutable_record_id(self):
        self.populated()
        added = {"id": "fictional_added", "series_id": "another_series", "revision": 1}
        saved = core.put_record(self.path, "submissions", added, expected_revision=1)
        self.assertEqual(saved["revision"], 2)
        self.assertEqual(
            saved["records"]["submissions"], [one_submission()["submissions"][0], added]
        )
        updated = {**one_submission()["submissions"][0], "revision": 3}
        result = core.put_record(
            self.path,
            "submissions",
            updated,
            expected_revision=2,
            identifier="fictional_original",
        )
        self.assertEqual(result["records"]["submissions"], [updated, added])
        before = self.path.read_bytes()
        self.fixed_failure(
            lambda: core.put_record(
                self.path,
                "submissions",
                {**updated, "id": "changed"},
                expected_revision=3,
                identifier="fictional_original",
            )
        )
        self.fixed_failure(
            lambda: core.put_record(
                self.path,
                "submissions",
                {**updated, "id": "missing"},
                expected_revision=3,
                identifier="missing",
            )
        )
        self.assertEqual(self.path.read_bytes(), before)

    def test_remove_keeps_dependent_declarations_and_records_the_review_snapshot(self):
        data = one_submission()
        data["submissions"].append(
            {
                "id": "fictional_replacement",
                "series_id": "fictional_series",
                "revision": 2,
            }
        )
        data["findings"] = [
            {
                "id": "fictional_finding",
                "submission_id": "fictional_original",
                "state": "open",
                "selected_retest_id": None,
            }
        ]
        data["retests"] = [
            {
                "id": "fictional_retest",
                "finding_id": "fictional_finding",
                "submission_id": "fictional_replacement",
                "outcome": "not_run",
            }
        ]
        core.create_store(self.path)
        core.save_records(self.path, data, expected_revision=0)
        result = core.remove_record(
            self.path, "submissions", "fictional_original", expected_revision=1
        )
        self.assertEqual(result["records"]["findings"], data["findings"])
        self.assertEqual(result["records"]["retests"], data["retests"])
        self.assertEqual(result["validation"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["revision"], 2)
        before = self.path.read_bytes()
        self.fixed_failure(
            lambda: core.remove_record(
                self.path, "submissions", "missing", expected_revision=2
            )
        )
        self.assertEqual(self.path.read_bytes(), before)

    def test_put_and_remove_reject_invalid_expected_revision_types(self):
        self.populated()
        before = self.path.read_bytes()
        added = {"id": "fictional_added", "series_id": "another_series", "revision": 1}
        for expected in (True, False, None, "1", 1.0, -1, 999):
            with self.subTest(expected=expected):
                self.fixed_failure(
                    lambda: core.put_record(
                        self.path, "submissions", added, expected_revision=expected
                    )
                )
                self.fixed_failure(
                    lambda: core.remove_record(
                        self.path,
                        "submissions",
                        "fictional_original",
                        expected_revision=expected,
                    )
                )
                self.assertEqual(self.path.read_bytes(), before)

    def test_ahead_and_stale_materialization_cannot_drop_newer_records(self):
        old = self.populated()
        current = core.save_records(self.path, one_submission(2), expected_revision=1)
        added = {"id": "fictional_added", "series_id": "another_series", "revision": 1}
        for expected in (2, 1):
            for kind in ("put", "remove"):
                materialized = copy.deepcopy(old)
                with self.subTest(expected=expected, operation=kind):
                    with patch.object(core, "load_store", return_value=materialized):
                        if kind == "put":
                            self.fixed_failure(
                                lambda: core.put_record(
                                    self.path,
                                    "submissions",
                                    added,
                                    expected_revision=expected,
                                )
                            )
                        else:
                            self.fixed_failure(
                                lambda: core.remove_record(
                                    self.path,
                                    "submissions",
                                    "fictional_original",
                                    expected_revision=expected,
                                )
                            )
                    self.assertEqual(core.load_store(self.path), current)
                    self.assertEqual(len(core.list_history(self.path)), 3)
                    if expected == 2:
                        self.assertEqual(materialized, old)


class CliTests(StoreFixture):
    def cli(self, *arguments, expected=0):
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(WORKBENCH / "workbench.py"),
                *map(str, arguments),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
        self.assertEqual(process.stderr, "")
        self.assertNotIn(str(self.parent), process.stdout)
        return json.loads(process.stdout)

    def test_actual_cli_init_put_update_remove_and_reopen_persist_explicit_versions(
        self,
    ):
        initialized = self.cli("init", "--store", self.path)
        self.assertEqual(initialized["revision"], 0)
        self.assertEqual(
            self.cli("check", "--store", self.path, expected=1)["issues"],
            ["EMPTY_WORKSPACE"],
        )
        record = self.json_file(
            one_submission()["submissions"][0], name="fictional-record.json"
        )
        preserved = record.read_bytes()
        put = self.cli(
            "put",
            "--store",
            self.path,
            "--kind",
            "submissions",
            "--record",
            record,
            "--expected-revision",
            0,
        )
        self.assertEqual(put["revision"], 1)
        self.assertEqual(record.read_bytes(), preserved)
        summary = self.cli("show", "--store", self.path)
        self.assertEqual(set(summary), {"revision", "validation"})
        explicit = self.cli("show", "--store", self.path, "--records")
        self.assertEqual(explicit["records"], one_submission())
        record.write_text(
            json.dumps(one_submission(2)["submissions"][0]), encoding="utf-8"
        )
        updated = self.cli(
            "put",
            "--store",
            self.path,
            "--kind",
            "submissions",
            "--record",
            record,
            "--id",
            "fictional_original",
            "--expected-revision",
            1,
        )
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(
            self.cli("revision", "--store", self.path, "--revision", 1, "--records")[
                "records"
            ],
            one_submission(),
        )
        self.assertEqual(
            [
                entry["revision"]
                for entry in self.cli("history", "--store", self.path)["history"]
            ],
            [0, 1, 2],
        )
        removed = self.cli(
            "remove",
            "--store",
            self.path,
            "--kind",
            "submissions",
            "--id",
            "fictional_original",
            "--expected-revision",
            2,
        )
        self.assertEqual(removed["revision"], 3)
        self.assertEqual(core.load_store(self.path)["records"], core.empty_records())

    def test_actual_cli_import_save_export_clone_and_recover_are_new_only(self):
        source = self.json_file(one_submission())
        original_json = source.read_bytes()
        imported = self.cli("import", "--store", self.path, "--input", source)
        self.assertEqual(imported["revision"], 0)
        draft = self.json_file(inconsistent_records(), name="fictional-draft.json")
        self.assertEqual(
            self.cli(
                "save", "--store", self.path, "--input", draft, "--expected-revision", 0
            )["revision"],
            1,
        )
        current = core.load_store(self.path)
        before = self.path.read_bytes()
        output = self.parent / "fictional-export.json"
        self.cli("export", "--store", self.path, "--output", output)
        self.assertEqual(json.loads(output.read_bytes()), inconsistent_records())
        recovered = self.parent / "fictional-recovered.db"
        self.cli(
            "recover", "--store", self.path, "--output", recovered, "--revision", 0
        )
        self.assertEqual(core.load_store(recovered)["records"], one_submission())
        clone = self.parent / "fictional-clone.db"
        self.cli("clone", "--store", self.path, "--output", clone)
        self.assertEqual(core.load_store(clone), current)
        recovered_bytes = recovered.read_bytes()
        self.cli("recover", "--store", self.path, "--output", recovered, expected=2)
        self.cli(
            "save",
            "--store",
            self.path,
            "--input",
            source,
            "--expected-revision",
            0,
            expected=2,
        )
        self.assertEqual(recovered.read_bytes(), recovered_bytes)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(source.read_bytes(), original_json)

    def test_actual_cli_fixed_errors_and_abbreviations_do_not_create_files(self):
        missing = self.parent / "fictional-missing-path-canary.db"
        for arguments in (
            ("show", "--store", missing),
            ("init", "--sto", missing),
            ("run", "fictional-sensitive-argument-canary"),
        ):
            result = self.cli(*arguments, expected=2)
            self.assertEqual(set(result), {"status", "code"})
            self.assertEqual(result["status"], "ERROR")
            self.assertNotIn("fictional-sensitive-argument-canary", json.dumps(result))
            self.assertNotIn(missing.name, json.dumps(result))
        self.assertFalse(missing.exists())

    def test_actual_cli_help_and_version_are_static(self):
        for argument in ("--help", "--version"):
            process = subprocess.run(
                [sys.executable, "-B", str(WORKBENCH / "workbench.py"), argument],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(process.returncode, 0)
            self.assertEqual(process.stderr, "")
            self.assertNotIn(str(REPOSITORY), process.stdout)


class IntegrityAndBoundaryTests(StoreFixture):
    def test_cleanly_closed_wal_store_is_rejected_before_sqlite_without_new_sidecars(
        self,
    ):
        self.populated()
        with contextlib.closing(sqlite3.connect(self.path)) as connection:
            mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            self.assertEqual(mode, "wal")
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        for suffix in ("-journal", "-wal", "-shm"):
            self.assertFalse(Path(str(self.path) + suffix).exists())
        before = self.path.read_bytes()
        self.assertEqual(before[18:20], b"\x02\x02")
        files_before = {path.name for path in self.parent.iterdir()}
        clone = self.parent / "must-not-clone-wal.db"
        with patch.object(
            core, "_connect", side_effect=AssertionError("WAL reached SQLite")
        ):
            for operation in (
                lambda: core.load_store(self.path),
                lambda: core.list_history(self.path),
                lambda: core.load_revision(self.path, 1),
                lambda: core.save_records(
                    self.path, one_submission(2), expected_revision=1
                ),
                lambda: core.clone_store(self.path, clone),
            ):
                self.fixed_failure(operation, self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual({path.name for path in self.parent.iterdir()}, files_before)
        self.assertFalse(clone.exists())

    def test_wrong_header_magic_page_size_or_versions_are_refused_before_sqlite(self):
        core.create_store(self.path)
        original = self.path.read_bytes()
        mutations = (
            (0, b"fictional" + b"\x00" * 7),
            (16, b"\x20\x00"),
            (16, b"\x00\x01"),
            (18, b"\x02\x01"),
            (18, b"\x01\x02"),
            (18, b"\x00\x01"),
            (18, b"\x01\x00"),
        )
        for index, (offset, replacement) in enumerate(mutations):
            altered = bytearray(original)
            altered[offset : offset + len(replacement)] = replacement
            path = self.parent / ("fictional-header-" + str(index) + ".db")
            path.write_bytes(altered)
            files_before = {entry.name for entry in self.parent.iterdir()}
            with self.subTest(index=index):
                with patch.object(
                    core,
                    "_connect",
                    side_effect=AssertionError("Invalid header reached SQLite"),
                ):
                    self.fixed_failure(lambda: core.load_store(path), path)
                self.assertEqual(path.read_bytes(), bytes(altered))
                self.assertEqual(
                    {entry.name for entry in self.parent.iterdir()}, files_before
                )

    def test_reentrant_store_open_never_opens_raw_file_while_sqlite_lock_is_live(self):
        saved = self.populated()
        with core.STORE_LOCK:
            with core._opened(self.path, write=True) as (_, connection, _rows):
                self.assertTrue(connection.in_transaction)
                with patch.object(
                    core.os,
                    "open",
                    side_effect=AssertionError("Reentrant raw file open"),
                ):
                    code = self.fixed_failure(lambda: core.load_store(self.path))
                self.assertEqual(code, "REENTRANT_STORE_OPERATION")
                with contextlib.closing(
                    sqlite3.connect(self.path, timeout=0)
                ) as competitor:
                    with self.assertRaises(sqlite3.OperationalError):
                        competitor.execute("BEGIN IMMEDIATE")
                self.assertTrue(connection.in_transaction)
        self.assertEqual(core.load_store(self.path), saved)

    def test_reentrant_json_readers_cannot_open_live_store_but_pure_validation_is_allowed(
        self,
    ):
        saved = self.populated()
        destination = self.parent / "must-not-import-live-store.db"
        with core.STORE_LOCK:
            with core._opened(self.path, write=True) as (_, connection, _rows):
                with patch.object(
                    core.os,
                    "open",
                    side_effect=AssertionError("Reentrant JSON raw file open"),
                ):
                    operations = (
                        lambda: core.read_records_file(self.path),
                        lambda: core.read_record_file(self.path),
                        lambda: core.import_to_new_store(self.path, destination),
                    )
                    for operation in operations:
                        self.assertEqual(
                            self.fixed_failure(operation), "REENTRANT_STORE_OPERATION"
                        )
                    self.assertEqual(
                        core.validate_records(one_submission())["status"],
                        "DECLARED_RECORDS_CONSISTENT",
                    )
                self.assertTrue(connection.in_transaction)
        self.assertFalse(destination.exists())
        self.assertEqual(core.load_store(self.path), saved)

    def test_safe_api_waits_for_same_process_live_connection_before_preflight(self):
        saved = self.populated()
        started, done = threading.Event(), threading.Event()
        outcomes = []

        def read_store():
            started.set()
            try:
                outcomes.append(core.load_store(self.path))
            except core.WorkbenchError as error:
                outcomes.append(str(error))
            except Exception as error:
                outcomes.append(type(error).__name__)
            finally:
                done.set()

        reader = threading.Thread(target=read_store, daemon=True)
        self.addCleanup(lambda: reader.join(5) if reader.ident is not None else None)
        with core.STORE_LOCK:
            with core._opened(self.path, write=True):
                reader.start()
                self.assertTrue(started.wait(1))
                self.assertFalse(done.wait(0.05))
        reader.join(5)
        self.assertFalse(reader.is_alive())
        self.assertEqual(outcomes, [saved])

    def test_all_history_tampering_is_rejected_without_repair(self):
        mutations = (
            ("UPDATE history SET ledger = ledger || ' ' WHERE sequence = 0", ()),
            ("UPDATE history SET digest = ? WHERE sequence = 0", ("0" * 64,)),
            ("UPDATE history SET previous = ? WHERE sequence = 1", ("0" * 64,)),
            ("UPDATE metadata SET head = ? WHERE id = 1", ("0" * 64,)),
            ("UPDATE metadata SET revision = 9 WHERE id = 1", ()),
            ("DELETE FROM history WHERE sequence = 0", ()),
        )
        for index, (statement, parameters) in enumerate(mutations):
            path = self.parent / ("tampered-" + str(index) + ".db")
            core.create_store(path)
            core.save_records(path, one_submission(), expected_revision=0)
            self.raw_edit(path, statement, parameters)
            before = path.read_bytes()
            with self.subTest(index=index):
                for operation in (
                    lambda: core.load_store(path),
                    lambda: core.list_history(path),
                    lambda: core.load_revision(path, 1),
                ):
                    self.fixed_failure(operation, path)
                    self.assertEqual(path.read_bytes(), before)

    def test_unknown_schema_objects_and_version_changes_are_not_migrated(self):
        mutations = (
            "CREATE TABLE unapproved (fictional TEXT)",
            "CREATE VIEW unapproved AS SELECT revision FROM metadata",
            "CREATE INDEX unapproved ON history(operation)",
            "CREATE TRIGGER unapproved AFTER INSERT ON history BEGIN SELECT RAISE(ABORT, 'fictional-native-schema-canary'); END",
            "PRAGMA application_id = 7",
            "PRAGMA user_version = 7",
            "ALTER TABLE metadata ADD COLUMN unapproved TEXT",
        )
        for index, statement in enumerate(mutations):
            path = self.parent / ("schema-" + str(index) + ".db")
            core.create_store(path)
            self.raw_edit(path, statement)
            before = path.read_bytes()
            with self.subTest(index=index):
                self.fixed_failure(
                    lambda: core.load_store(path),
                    path,
                    "fictional-native-schema-canary",
                )
                self.assertEqual(path.read_bytes(), before)

    def test_damaged_or_oversized_store_cannot_be_recovered_by_silent_repair(self):
        self.path.write_bytes(b"fictional-sensitive-not-a-sqlite-store")
        before = self.path.read_bytes()
        output = self.parent / "must-not-recover.db"
        self.fixed_failure(
            lambda: core.load_store(self.path),
            self.path,
            "fictional-sensitive-not-a-sqlite-store",
        )
        self.fixed_failure(lambda: core.clone_store(self.path, output), self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse(output.exists())
        self.path.unlink()
        core.create_store(self.path)
        with self.path.open("r+b") as stream:
            stream.truncate(16 * 1024 * 1024 + 1)
        self.fixed_failure(lambda: core.load_store(self.path), self.path)
        self.assertEqual(self.path.stat().st_size, 16 * 1024 * 1024 + 1)

    def test_reserved_sidecar_artifacts_are_preserved_and_block_new_or_existing_store(
        self,
    ):
        for suffix in ("-journal", "-wal", "-shm"):
            path = self.parent / ("artifact" + suffix.replace("-", "_") + ".db")
            artifact = Path(str(path) + suffix)
            artifact.write_bytes(b"Fictional preserved sidecar bytes")
            with self.subTest(suffix=suffix):
                self.fixed_failure(lambda: core.create_store(path), path)
                self.assertFalse(path.exists())
                self.assertEqual(
                    artifact.read_bytes(), b"Fictional preserved sidecar bytes"
                )
        core.create_store(self.path)
        artifact = Path(str(self.path) + "-journal")
        artifact.write_bytes(b"Fictional hot-journal canary")
        before = self.path.read_bytes()
        self.fixed_failure(lambda: core.load_store(self.path), self.path)
        self.fixed_failure(
            lambda: core.clone_store(self.path, self.parent / "must-not-clone.db"),
            self.path,
        )
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(artifact.read_bytes(), b"Fictional hot-journal canary")

    def test_new_outputs_cannot_use_reserved_sidecar_names(self):
        self.populated()
        before = self.path.read_bytes()
        for suffix in ("-journal", "-wal", "-shm"):
            destination = self.parent / ("fictional-new-output" + suffix)
            with self.subTest(suffix=suffix):
                self.fixed_failure(lambda: core.create_store(destination))
                self.fixed_failure(lambda: core.export_records(self.path, destination))
                self.fixed_failure(lambda: core.clone_store(self.path, destination))
                self.assertFalse(destination.exists())
        self.assertEqual(self.path.read_bytes(), before)

    def test_relative_or_repository_store_destinations_are_refused_before_creation(
        self,
    ):
        for destination in (
            Path("fictional-must-not-create.db"),
            REPOSITORY / "fictional-must-not-create.db",
        ):
            with self.subTest(destination=str(destination)):
                with patch.object(
                    core.os,
                    "open",
                    side_effect=AssertionError("Forbidden output opened"),
                ):
                    self.fixed_failure(lambda: core.create_store(destination))
                self.assertFalse((REPOSITORY / destination.name).exists())

    @unittest.skipUnless(os.name == "nt", "Native Windows short-path alias")
    def test_repository_short_path_alias_is_refused_before_store_creation(self):
        alias = short_path_alias(REPOSITORY)
        if alias is None:
            self.skipTest("Filesystem did not supply an alternate short spelling")
        destination = alias / "short-alias-must-not-create.db"
        with patch.object(
            core.os, "open", side_effect=AssertionError("Alias output opened")
        ):
            self.fixed_failure(lambda: core.create_store(destination))
        self.assertFalse((REPOSITORY / destination.name).exists())

    @unittest.skipUnless(os.name == "nt", "Native Windows short-path alias")
    def test_selected_database_short_name_cannot_bypass_sidecar_family_guard(self):
        saved = self.populated()
        alias = short_path_alias(self.path)
        if alias is None:
            self.skipTest("Filesystem did not supply an alternate short spelling")
        self.assertEqual(core.load_store(alias), saved)
        artifact = Path(str(self.path) + "-journal")
        artifact.write_bytes(b"Fictional preserved canonical journal canary")
        before = self.path.read_bytes()
        output = self.parent / "must-not-export.json"
        clone = self.parent / "must-not-clone.db"
        self.fixed_failure(lambda: core.load_store(alias), alias)
        self.fixed_failure(
            lambda: core.save_records(alias, one_submission(2), expected_revision=1),
            alias,
        )
        self.fixed_failure(lambda: core.export_records(alias, output), alias)
        self.fixed_failure(lambda: core.clone_store(alias, clone), alias)
        self.assertFalse(output.exists())
        self.assertFalse(clone.exists())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(
            artifact.read_bytes(), b"Fictional preserved canonical journal canary"
        )

    def test_missing_parent_is_not_created_implicitly(self):
        destination = self.parent / "missing-parent/fictional.db"
        self.fixed_failure(lambda: core.create_store(destination), destination)
        self.assertFalse(destination.parent.exists())

    def test_selected_store_hardlinks_and_symlinks_are_refused(self):
        core.create_store(self.path)
        alias = self.parent / "fictional-alias.db"
        try:
            os.link(self.path, alias)
        except OSError:
            self.skipTest("Native hardlink creation is unavailable")
        self.fixed_failure(lambda: core.load_store(self.path), self.path)

    def test_native_symlink_store_is_refused(self):
        core.create_store(self.path)
        alias = self.parent / "fictional-alias.db"
        try:
            alias.symlink_to(self.path)
        except OSError:
            self.skipTest("Native symlink creation is unavailable")
        self.fixed_failure(lambda: core.load_store(alias), alias)

    def test_import_json_guards_size_duplicate_keys_and_encoding(self):
        source = self.parent / "fictional-control.json"
        for raw in (
            b'{"schema_version":1,"schema_version":1}',
            b"\xff",
            b"{" + b" " * 65536,
        ):
            source.write_bytes(raw)
            with self.subTest(size=len(raw)):
                self.fixed_failure(
                    lambda: core.import_to_new_store(source, self.path), source
                )
                self.assertEqual(source.read_bytes(), raw)
                self.assertFalse(self.path.exists())

    def test_store_and_control_json_reject_link_metadata_before_open(self):
        self.populated()
        source = self.json_file(one_submission())
        original = Path.lstat
        for selected in (self.path, source):

            def linked(path):
                info = original(path)
                return changed_stat(info, st_nlink=2) if path == selected else info

            with (
                self.subTest(selected=selected.name),
                patch.object(Path, "lstat", linked),
            ):
                if selected == self.path:
                    self.fixed_failure(lambda: core.load_store(selected), selected)
                else:
                    self.fixed_failure(
                        lambda: core.import_to_new_store(
                            selected, self.parent / "must-not-import.db"
                        ),
                        selected,
                    )
        self.assertFalse((self.parent / "must-not-import.db").exists())

    def test_missing_and_native_errors_do_not_leak_selected_paths_in_tracebacks(self):
        missing = self.parent / "fictional-missing-path-canary.db"
        self.fixed_failure(lambda: core.load_store(missing), missing, missing.name)
        source = self.parent / "fictional-input-path-canary.json"
        source.write_text("{}", encoding="utf-8")
        original = Path.lstat
        canary = "fictional-sensitive-native-message"

        def denied(path):
            if path == source:
                raise PermissionError(13, canary, str(source))
            return original(path)

        with patch.object(Path, "lstat", denied):
            self.fixed_failure(
                lambda: core.import_to_new_store(source, self.path),
                source,
                source.name,
                canary,
                "PermissionError",
            )

    def test_workflow_does_not_contact_hosts_or_execute_programs(self):
        with (
            patch.object(socket, "socket", side_effect=AssertionError("No sockets")),
            patch.object(
                socket, "create_connection", side_effect=AssertionError("No connection")
            ),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("No DNS")),
            patch("subprocess.Popen", side_effect=AssertionError("No execution")),
            patch("subprocess.run", side_effect=AssertionError("No execution")),
            patch.object(os, "system", side_effect=AssertionError("No shell")),
            patch.object(os, "execv", side_effect=AssertionError("No exec")),
        ):
            core.create_store(self.path)
            saved = core.save_records(self.path, one_submission(), expected_revision=0)
            core.export_records(self.path, self.parent / "fictional-export.json")
            clone = core.clone_store(self.path, self.parent / "fictional-clone.db")
        self.assertEqual(saved, clone)


if __name__ == "__main__":
    unittest.main()
