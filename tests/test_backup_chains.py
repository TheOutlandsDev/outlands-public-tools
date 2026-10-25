"""Disposable fictional declarations; never reads actual backups or inventory."""

import contextlib
import copy
import importlib.util
import io
import itertools
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
SCRIPT = ROOT / "tools/backup-chain-checker/chain_check.py"
spec = importlib.util.spec_from_file_location("fictional_backup_chain_checker", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def snapshot(
    identifier="sample_full",
    *,
    parent=None,
    sequence=0,
    series="sample_series",
    kind=None,
):
    return dict(
        id=identifier,
        series_id=series,
        kind=kind or ("full" if parent is None else "incremental"),
        parent_id=parent,
        sequence=sequence,
    )


def plan(*rows, target="sample_full"):
    return dict(schema_version=1, restore_point_id=target, snapshots=list(rows))


def valid_plan():
    return plan(
        snapshot(),
        snapshot("sample_first", parent="sample_full", sequence=1),
        snapshot("sample_second", parent="sample_first", sequence=2),
        target="sample_second",
    )


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

    def file(self, value=None, *, raw=None, name="fictional-plan.json"):
        path = self.parent / name
        path.write_bytes(json.dumps(value).encode() if raw is None else raw)
        return path

    def invoke(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = checker.main(list(map(str, args)))
        return code, output.getvalue(), errors.getvalue()

    def rejected(self, value, expected=None):
        with self.assertRaises(checker.ContractError) as caught:
            checker.check_chain(value)
        if expected:
            self.assertEqual(str(caught.exception), expected)

    def local(self, result, identifier):
        return next(
            row["issues"] for row in result["snapshots"] if row["id"] == identifier
        )


class SchemaTests(Fixture):
    def test_root_schema_is_exact_and_version_has_no_coercion(self):
        data = valid_plan()
        for value in (
            None,
            [],
            True,
            1,
            "fictional",
            {},
            {**data, "private_path": "fictional"},
        ):
            self.rejected(value, "PLAN_SCHEMA_INVALID")
        for key in data:
            self.rejected(
                {k: v for k, v in data.items() if k != key}, "PLAN_SCHEMA_INVALID"
            )
        for value in (True, 1.0, "1", None, 0, 2):
            self.rejected({**data, "schema_version": value}, "PLAN_SCHEMA_INVALID")

    def test_snapshot_fields_are_exact_and_private_fields_refused(self):
        for extra in (
            "path",
            "endpoint",
            "credential",
            "player",
            "evidence",
            "hash",
            "timestamp",
            "size",
            "command",
        ):
            self.rejected(
                plan({**snapshot(), extra: "fictional-private-canary"}),
                "SNAPSHOT_SCHEMA_INVALID",
            )
        for key in snapshot():
            self.rejected(
                plan({k: v for k, v in snapshot().items() if k != key}),
                "SNAPSHOT_SCHEMA_INVALID",
            )
        for row in (None, [], "fictional", False):
            self.rejected(plan(row), "SNAPSHOT_SCHEMA_INVALID")

    def test_identifiers_are_bounded_neutral_ascii_tokens(self):
        invalid = (
            None,
            True,
            1,
            [],
            "",
            "Sample",
            "1sample",
            "sample/path",
            "sample.name",
            "sample space",
            "échantillon",
            "a" * 41,
        )
        for value in invalid:
            self.rejected(plan({**snapshot(), "id": value}), "SNAPSHOT_ID_INVALID")
            self.rejected(plan({**snapshot(), "series_id": value}), "SERIES_ID_INVALID")
            self.rejected(plan(snapshot(), target=value), "RESTORE_POINT_ID_INVALID")
            if value is not None:
                self.rejected(
                    plan({**snapshot(), "parent_id": value}), "PARENT_ID_INVALID"
                )
        row = snapshot("a" * 40, series="s_1-valid")
        self.assertEqual(
            checker.check_chain(plan(row, target=row["id"]))["status"],
            "DECLARED_CHAIN_CONSISTENT",
        )

    def test_duplicate_ids_are_rejected_before_graph_construction(self):
        self.rejected(plan(snapshot(), snapshot(sequence=3)), "DUPLICATE_SNAPSHOT_ID")

    def test_sequence_requires_bounded_non_boolean_integer(self):
        for value in (True, False, None, 0.0, "0", -1, 1000001, [], {}):
            self.rejected(plan({**snapshot(), "sequence": value}), "SEQUENCE_INVALID")
        for value in (0, 1000000):
            self.assertEqual(
                checker.check_chain(plan(snapshot(sequence=value)))["status"],
                "DECLARED_CHAIN_CONSISTENT",
            )

    def test_only_documented_kinds_are_accepted(self):
        for value in (
            None,
            True,
            1,
            [],
            {},
            "FULL",
            "differential",
            "deduplicated",
            "incremental ",
        ):
            self.rejected(plan({**snapshot(), "kind": value}), "SNAPSHOT_KIND_INVALID")

    def test_snapshot_count_bounds_and_list_type(self):
        for value in ([], None, {}, "fictional", [snapshot()] * 257):
            self.rejected({**valid_plan(), "snapshots": value}, "PLAN_SCHEMA_INVALID")
        rows = [snapshot(f"sample_{i}", sequence=i) for i in range(256)]
        self.assertEqual(
            checker.check_chain(plan(*rows, target="sample_255"))["counts"][
                "snapshots"
            ],
            256,
        )

    def test_parse_and_check_copy_without_mutating_input(self):
        data = valid_plan()
        before = copy.deepcopy(data)
        parsed = checker.parse_plan(data)
        self.assertEqual(parsed, data)
        self.assertIsNot(parsed, data)
        self.assertIsNot(parsed["snapshots"], data["snapshots"])
        self.assertIsNot(parsed["snapshots"][0], data["snapshots"][0])
        checker.check_chain(data)
        self.assertEqual(data, before)


class RelationshipTests(Fixture):
    def test_full_root_and_incremental_order(self):
        result = checker.check_chain(valid_plan())
        self.assertEqual(result["status"], "DECLARED_CHAIN_CONSISTENT")
        self.assertEqual(
            result["target"]["declared_order"],
            ["sample_full", "sample_first", "sample_second"],
        )
        self.assertEqual(
            result["counts"],
            dict(snapshots=3, series=1, snapshots_with_issues=0, cycle_members=0),
        )
        self.assertTrue(all(not row["issues"] for row in result["snapshots"]))

    def test_selected_root_omits_descendants_and_unrelated_roots(self):
        data = valid_plan()
        data["restore_point_id"] = "sample_full"
        data["snapshots"].append(snapshot("sample_other", sequence=10))
        result = checker.check_chain(data)
        self.assertEqual(result["status"], "DECLARED_CHAIN_CONSISTENT")
        self.assertEqual(result["target"]["declared_order"], ["sample_full"])

    def test_branching_gaps_and_multiple_series_are_supported(self):
        data = plan(
            snapshot(),
            snapshot("sample_left", parent="sample_full", sequence=8),
            snapshot("sample_right", parent="sample_full", sequence=12),
            snapshot("other_full", series="other_series"),
            target="sample_right",
        )
        result = checker.check_chain(data)
        self.assertEqual(result["status"], "DECLARED_CHAIN_CONSISTENT")
        self.assertEqual(result["counts"]["series"], 2)
        self.assertEqual(
            result["target"]["declared_order"], ["sample_full", "sample_right"]
        )

    def test_missing_selected_restore_point_is_explicit(self):
        result = checker.check_chain(plan(snapshot(), target="sample_absent"))
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            result["target"],
            dict(
                id="sample_absent",
                status="REVIEW_REQUIRED",
                issues=["RESTORE_POINT_NOT_FOUND"],
                declared_order=[],
            ),
        )

    def test_missing_parent_blocks_entire_order(self):
        result = checker.check_chain(
            plan(
                snapshot("sample_child", parent="sample_absent", sequence=1),
                target="sample_child",
            )
        )
        self.assertEqual(self.local(result, "sample_child"), ["PARENT_NOT_FOUND"])
        self.assertEqual(result["target"]["issues"], ["TARGET_CHAIN_BLOCKED"])
        self.assertEqual(result["target"]["declared_order"], [])

    def test_full_parent_and_incremental_null_are_issues_not_repaired(self):
        rows = [
            snapshot(),
            snapshot("sample_bad_full", parent="sample_full", sequence=1, kind="full"),
            snapshot("sample_bad_inc", sequence=2, kind="incremental"),
        ]
        result = checker.check_chain(plan(*rows))
        self.assertEqual(
            self.local(result, "sample_bad_full"), ["FULL_PARENT_NOT_NULL"]
        )
        self.assertEqual(
            self.local(result, "sample_bad_inc"), ["INCREMENTAL_PARENT_NOT_SUPPLIED"]
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_cross_series_parent_is_blocked(self):
        result = checker.check_chain(
            plan(
                snapshot(),
                snapshot(
                    "sample_child",
                    parent="sample_full",
                    sequence=1,
                    series="other_series",
                ),
                target="sample_child",
            )
        )
        self.assertEqual(self.local(result, "sample_child"), ["PARENT_SERIES_MISMATCH"])
        self.assertEqual(result["target"]["declared_order"], [])

    def test_equal_or_later_parent_sequence_is_flagged(self):
        for parent_sequence in (4, 5):
            result = checker.check_chain(
                plan(
                    snapshot(sequence=parent_sequence),
                    snapshot("sample_child", parent="sample_full", sequence=4),
                    target="sample_child",
                )
            )
            self.assertIn(
                "PARENT_SEQUENCE_NOT_EARLIER", self.local(result, "sample_child")
            )
            self.assertEqual(result["target"]["declared_order"], [])

    def test_reused_sequence_marks_every_row_in_its_series_only(self):
        result = checker.check_chain(
            plan(
                snapshot(),
                snapshot("sample_duplicate"),
                snapshot("other_full", series="other_series"),
            )
        )
        self.assertEqual(
            self.local(result, "sample_full"), ["SEQUENCE_REUSED_IN_SERIES"]
        )
        self.assertEqual(
            self.local(result, "sample_duplicate"), ["SEQUENCE_REUSED_IN_SERIES"]
        )
        self.assertEqual(self.local(result, "other_full"), [])

    def test_self_reference_and_cycle_members_are_distinct_issues(self):
        result = checker.check_chain(plan(snapshot(parent="sample_full", sequence=1)))
        self.assertEqual(
            self.local(result, "sample_full"),
            [
                "PARENT_SELF_REFERENCE",
                "PARENT_SEQUENCE_NOT_EARLIER",
                "DEPENDENCY_CYCLE",
            ],
        )
        self.assertEqual(result["counts"]["cycle_members"], 1)

    def test_multinode_cycle_marks_members_without_marking_descendant_as_member(self):
        result = checker.check_chain(
            plan(
                snapshot("sample_a", parent="sample_b", sequence=1),
                snapshot("sample_b", parent="sample_a", sequence=2),
                snapshot("sample_child", parent="sample_b", sequence=3),
                target="sample_child",
            )
        )
        self.assertIn("DEPENDENCY_CYCLE", self.local(result, "sample_a"))
        self.assertIn("DEPENDENCY_CYCLE", self.local(result, "sample_b"))
        self.assertEqual(self.local(result, "sample_child"), [])
        self.assertEqual(result["counts"]["cycle_members"], 2)
        self.assertEqual(result["target"]["declared_order"], [])

    def test_unrelated_bad_branch_requires_global_review_but_keeps_clean_target_order(
        self,
    ):
        data = valid_plan()
        data["snapshots"].append(
            snapshot(
                "sample_broken",
                parent="sample_absent",
                sequence=9,
                series="other_series",
            )
        )
        result = checker.check_chain(data)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["target"]["status"], "DECLARED_CHAIN_CONSISTENT")
        self.assertEqual(
            result["target"]["declared_order"],
            ["sample_full", "sample_first", "sample_second"],
        )

    def test_bad_ancestor_blocks_target_without_inventing_local_issue(self):
        result = checker.check_chain(
            plan(
                snapshot(kind="incremental"),
                snapshot("sample_child", parent="sample_full", sequence=1),
                target="sample_child",
            )
        )
        self.assertEqual(self.local(result, "sample_child"), [])
        self.assertEqual(result["target"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["target"]["declared_order"], [])

    def test_all_input_permutations_have_identical_results(self):
        data = valid_plan()
        data["snapshots"].append(snapshot("other_full", series="other_series"))
        expected = checker.check_chain(data)
        for rows in itertools.permutations(data["snapshots"]):
            self.assertEqual(
                checker.check_chain(plan(*rows, target=data["restore_point_id"])),
                expected,
            )

    def test_maximum_depth_uses_no_recursion_and_output_is_bounded(self):
        rows = [snapshot("sample_0")]
        rows += [
            snapshot(f"sample_{i}", parent=f"sample_{i - 1}", sequence=i)
            for i in range(1, 256)
        ]
        result = checker.check_chain(plan(*reversed(rows), target="sample_255"))
        self.assertEqual(
            result["target"]["declared_order"], [row["id"] for row in rows]
        )
        self.assertLess(len(json.dumps(result)), 131072)

    def test_issue_order_is_fixed_for_multiple_local_failures(self):
        result = checker.check_chain(
            plan(snapshot(parent="sample_full", kind="full"), snapshot("sample_other"))
        )
        issues = self.local(result, "sample_full")
        self.assertEqual(
            issues, [code for code in checker.ISSUE_ORDER if code in issues]
        )
        self.assertEqual(
            issues,
            [
                "FULL_PARENT_NOT_NULL",
                "PARENT_SELF_REFERENCE",
                "PARENT_SEQUENCE_NOT_EARLIER",
                "SEQUENCE_REUSED_IN_SERIES",
                "DEPENDENCY_CYCLE",
            ],
        )


class OracleTests(Fixture):
    def test_all_1296_four_node_parent_graphs_match_independent_reachability_oracle(
        self,
    ):
        ids = ["sample_a", "sample_b", "sample_c", "sample_d"]
        choices = [None, "sample_missing", *ids]
        for parents in itertools.product(choices, repeat=4):
            rows = [
                snapshot(key, parent=parent, sequence=i)
                for i, (key, parent) in enumerate(zip(ids, parents))
            ]
            result = checker.check_chain(plan(*rows, target=ids[-1]))
            # Independent transitive closure, rather than the implementation's path walk.
            reach = [[parents[i] == ids[j] for j in range(4)] for i in range(4)]
            for middle in range(4):
                for left in range(4):
                    for right in range(4):
                        reach[left][right] |= (
                            reach[left][middle] and reach[middle][right]
                        )
            expected = {ids[i] for i in range(4) if reach[i][i]}
            actual = {
                row["id"]
                for row in result["snapshots"]
                if "DEPENDENCY_CYCLE" in row["issues"]
            }
            self.assertEqual(actual, expected, parents)
            self.assertEqual(result["counts"]["cycle_members"], len(expected))
            route, seen, current = [], set(), ids[-1]
            while current in ids and current not in seen:
                seen.add(current)
                index = ids.index(current)
                route.append(current)
                parent = parents[index]
                if parent is not None and (
                    parent not in ids or ids.index(parent) >= index
                ):
                    route = []
                    break
                current = parent
            order = list(reversed(route)) if current is None else []
            self.assertEqual(result["target"]["declared_order"], order, parents)

    def test_300_seeded_forests_match_independent_selected_ancestor_oracle(self):
        rng = random.Random(1701)
        for _ in range(300):
            count = rng.randrange(1, 80)
            rows = []
            parents = []
            for index in range(count):
                parent = rng.randrange(index) if index and rng.randrange(3) else None
                parents.append(parent)
                rows.append(
                    snapshot(
                        f"sample_{index}",
                        parent=None if parent is None else f"sample_{parent}",
                        sequence=index * 3,
                    )
                )
            target = rng.randrange(count)
            # Reverse generation order selects exactly target and its known ancestors.
            required = {target}
            for index in range(target, -1, -1):
                if index in required and parents[index] is not None:
                    required.add(parents[index])
            rng.shuffle(rows)
            result = checker.check_chain(plan(*rows, target=f"sample_{target}"))
            self.assertEqual(result["status"], "DECLARED_CHAIN_CONSISTENT")
            self.assertEqual(
                result["target"]["declared_order"],
                [f"sample_{i}" for i in sorted(required)],
            )


class ReaderAndCliTests(Fixture):
    def test_json_reader_accepts_utf8_bom_and_preserves_input(self):
        source = self.file(raw=b"\xef\xbb\xbf" + json.dumps(valid_plan()).encode())
        before = source.read_bytes()
        self.assertEqual(checker.read_input_json(source), valid_plan())
        self.assertEqual(source.read_bytes(), before)

    def test_duplicate_json_keys_nonstandard_numbers_and_bad_encoding_are_refused(self):
        for raw in (
            b'{"schema_version":1,"schema_version":1}',
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":-Infinity}',
            b"\xff",
            b"{",
            b"[" * 1200,
        ):
            source = self.file(raw=raw)
            code, output, errors = self.invoke("--plan", source)
            self.assertEqual(code, 2)
            self.assertEqual(errors, "")
            self.assertEqual(json.loads(output)["status"], "ERROR")

    def test_byte_size_limit_is_enforced_before_read(self):
        source = self.file(raw=b" " * 65537)
        with patch.object(
            checker.os, "open", side_effect=AssertionError("MUST_NOT_OPEN")
        ):
            code, output, _ = self.invoke("--plan", source)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["code"], "INPUT_SIZE_LIMIT")
        source.write_bytes(json.dumps(valid_plan()).encode().ljust(65536))
        self.assertEqual(self.invoke("--plan", source)[0], 0)

    def test_invalid_paths_are_refused_before_metadata_or_open(self):
        values = (
            "",
            "../fictional",
            "fictional/../plan.json",
            "//fictional-host/share/plan.json",
            "\\\\fictional-host\\share\\plan.json",
            "C:fictional",
            "fictional:stream",
            "nul",
            "COM1.json",
            "fictional. ",
            "fictional\nname",
            "x" * 4097,
        )
        for value in values:
            with (
                self.subTest(fictional_value=value[:60]),
                patch.object(
                    Path, "lstat", side_effect=AssertionError("MUST_NOT_STAT")
                ),
                patch.object(
                    checker.os, "open", side_effect=AssertionError("MUST_NOT_OPEN")
                ),
            ):
                self.assertEqual(self.invoke("--plan", value)[0], 2)

    def test_missing_directory_and_native_error_details_are_fixed(self):
        source = self.parent / "fictional-private-canary.json"
        code, output, errors = self.invoke("--plan", source)
        self.assertEqual(code, 2)
        self.assertNotIn(str(source), output + errors)
        self.assertNotIn("fictional-private-canary", output + errors)
        try:
            checker.read_input_json(source)
        except checker.ContractError as error:
            formatted = "".join(traceback.format_exception(error))
            self.assertNotIn(str(source), formatted)
            self.assertTrue(error.__suppress_context__)
        else:
            self.fail("EXPECTED_FIXED_ERROR")

    def test_directory_and_hardlinked_input_are_refused(self):
        self.assertEqual(self.invoke("--plan", self.parent)[0], 2)
        source = self.file(valid_plan())
        linked = self.parent / "fictional-hardlink.json"
        try:
            os.link(source, linked)
        except OSError:
            self.skipTest("Native hardlink creation unavailable")
        before = source.read_bytes()
        self.assertEqual(self.invoke("--plan", linked)[0], 2)
        self.assertEqual(source.read_bytes(), before)

    def test_symlink_leaf_and_linked_ancestor_are_refused(self):
        source = self.file(valid_plan())
        link = self.parent / "fictional-link.json"
        folder = self.parent / "fictional-folder-link"
        try:
            link.symlink_to(source)
            folder.symlink_to(self.parent, target_is_directory=True)
        except OSError:
            self.skipTest("Native symlink creation unavailable")
        self.assertEqual(self.invoke("--plan", link)[0], 2)
        self.assertEqual(self.invoke("--plan", folder / source.name)[0], 2)

    def test_reparse_and_missing_identity_are_refused_synthetically(self):
        source = self.file(valid_plan())
        real = source.lstat()
        for values in (dict(st_ino=0), dict(st_file_attributes=0x400)):
            fake = SimpleNamespace(
                **{
                    name: getattr(real, name)
                    for name in dir(real)
                    if name.startswith("st_")
                }
            )
            for key, value in values.items():
                setattr(fake, key, value)
            with patch.object(Path, "lstat", return_value=fake):
                self.assertEqual(self.invoke("--plan", source)[0], 2)

    def test_sampled_identity_change_is_refused_without_echoing_path(self):
        source = self.file(valid_plan())
        original = checker._snapshot
        calls = 0

        def changed(path):
            nonlocal calls
            ancestors, info = original(path)
            calls += 1
            if calls == 2:
                ancestors += (("fictional-change",),)
            return ancestors, info

        with patch.object(checker, "_snapshot", side_effect=changed):
            code, output, _ = self.invoke("--plan", source)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["code"], "INPUT_CHANGED")

    def test_cli_exit_codes_and_invalid_arguments_have_no_raw_echo(self):
        source = self.file(valid_plan())
        self.assertEqual(self.invoke("--plan", source)[0], 0)
        source.write_text(json.dumps(plan(snapshot(), target="sample_absent")))
        self.assertEqual(self.invoke("--plan", source)[0], 1)
        for args in (
            (),
            ("--plan",),
            ("--unknown", "fictional-private-canary"),
            ("--pl", source),
            ("--plan", source, "fictional-private-canary"),
        ):
            code, output, errors = self.invoke(*args)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output)["code"], "ARGUMENTS_INVALID")
            self.assertNotIn("fictional-private-canary", output + errors)

    def test_output_is_fixed_shape_with_unverified_flags_and_no_sequence_or_series_echo(
        self,
    ):
        result = checker.check_chain(valid_plan())
        self.assertEqual(
            set(result),
            {
                "schema_version",
                "status",
                "scope",
                "counts",
                "snapshots",
                "target",
                *checker._flags(),
            },
        )
        self.assertTrue(all(result[name] is False for name in checker._flags()))
        self.assertNotIn("sample_series", json.dumps(result))
        self.assertNotIn('"sequence"', json.dumps(result))
        self.assertEqual(set(result["snapshots"][0]), {"id", "issues"})

    def test_pure_check_does_not_access_files_network_processes_or_wall_clock(self):
        with contextlib.ExitStack() as stack:
            for target in (
                "builtins.open",
                "os.open",
                "os.scandir",
                "os.system",
                "subprocess.Popen",
                "socket.socket",
                "time.time",
                "pathlib.Path.write_text",
                "pathlib.Path.unlink",
            ):
                stack.enter_context(
                    patch(target, side_effect=AssertionError("UNEXPECTED_SIDE_EFFECT"))
                )
            self.assertEqual(
                checker.check_chain(valid_plan())["status"], "DECLARED_CHAIN_CONSISTENT"
            )

    def test_cli_reads_only_selected_control_file_and_creates_nothing(self):
        source = self.file(valid_plan())
        before = {p.name: p.read_bytes() for p in self.parent.iterdir()}
        with (
            patch.object(checker.os, "scandir", side_effect=AssertionError("NO_SCAN")),
            patch.object(socket, "socket", side_effect=AssertionError("NO_NETWORK")),
            patch.object(
                subprocess, "Popen", side_effect=AssertionError("NO_EXECUTION")
            ),
        ):
            code, _, _ = self.invoke("--plan", source)
        self.assertEqual(code, 0)
        self.assertEqual(
            {p.name: p.read_bytes() for p in self.parent.iterdir()}, before
        )

    def test_private_unknown_input_fields_are_not_echoed_by_cli(self):
        source = self.file({**valid_plan(), "credential": "fictional-private-canary"})
        code, output, errors = self.invoke("--plan", source)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["code"], "PLAN_SCHEMA_INVALID")
        self.assertNotIn("fictional-private-canary", output + errors)

    def test_interrupt_is_fixed_exit_130(self):
        with patch.object(checker, "read_input_json", side_effect=KeyboardInterrupt):
            code, output, errors = self.invoke("--plan", "fictional.json")
        self.assertEqual(code, 130)
        self.assertEqual(json.loads(output)["code"], "INTERRUPTED")
        self.assertEqual(errors, "")

    def test_script_runs_standalone_in_fresh_child_with_only_fictional_input(self):
        script = self.parent / "chain_check.py"
        shutil.copyfile(SCRIPT, script)
        source = self.file(valid_plan())
        before = {p.name: p.read_bytes() for p in self.parent.iterdir()}
        process = subprocess.run(
            [sys.executable, "-B", str(script), "--plan", str(source)],
            cwd=self.parent,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), checker.check_chain(valid_plan()))
        self.assertEqual(process.stderr, "")
        self.assertEqual(
            {p.name: p.read_bytes() for p in self.parent.iterdir()}, before
        )

    def test_shipped_examples_match_documented_outcomes_without_changes(self):
        examples = SCRIPT.parent / "examples"
        for name, status, order in (
            (
                "valid-chain.json",
                "DECLARED_CHAIN_CONSISTENT",
                ["sample_full", "sample_first", "sample_second"],
            ),
            ("missing-parent.json", "REVIEW_REQUIRED", []),
            ("cycle.json", "REVIEW_REQUIRED", []),
            (
                "unrelated-broken.json",
                "REVIEW_REQUIRED",
                ["sample_full", "sample_first", "sample_second"],
            ),
        ):
            source = examples / name
            before = source.read_bytes()
            code, output, errors = self.invoke("--plan", source)
            result = json.loads(output)
            self.assertEqual(result["status"], status)
            self.assertEqual(result["target"]["declared_order"], order)
            self.assertEqual(code, 0 if status == "DECLARED_CHAIN_CONSISTENT" else 1)
            self.assertEqual(errors, "")
            self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
