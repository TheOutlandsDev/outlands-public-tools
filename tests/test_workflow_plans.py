"""Fictional task declarations in disposable owned temporary directories."""

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
SCRIPT = ROOT / "tools/workflow-plan-checker/workflow_check.py"
spec = importlib.util.spec_from_file_location("fictional_workflow_plan_checker", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def task(identifier="sample_prepare", *, requires=(), state="pending"):
    return dict(id=identifier, requires=list(requires), state=state)


def plan(*tasks):
    return dict(schema_version=1, tasks=list(tasks))


def valid_plan():
    return plan(
        task(state="completed"),
        task("sample_check", requires=["sample_prepare"]),
        task("sample_package", requires=["sample_check", "sample_prepare"]),
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

    def rejected(self, value, expected):
        with self.assertRaises(checker.ContractError) as caught:
            checker.check_plan(value)
        self.assertEqual(str(caught.exception), expected)

    def issues_for(self, result, identifier):
        return next(row["issues"] for row in result["tasks"] if row["id"] == identifier)

    def withheld(self, result):
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        for key in ("declared_order", "eligible_next_ids", "waiting_ids"):
            self.assertEqual(result[key], [])


class SchemaTests(Fixture):
    def test_root_fields_and_integer_version_are_exact(self):
        data = valid_plan()
        for value in (
            None,
            [],
            True,
            "fictional",
            {},
            {**data, "path": "fictional-canary"},
        ):
            self.rejected(value, "PLAN_SCHEMA_INVALID")
        for field in data:
            self.rejected(
                {key: value for key, value in data.items() if key != field},
                "PLAN_SCHEMA_INVALID",
            )
        for version in (True, False, 1.0, "1", None, 0, 2):
            self.rejected({**data, "schema_version": version}, "PLAN_SCHEMA_INVALID")

    def test_task_fields_exclude_commands_paths_identities_and_private_payloads(self):
        for field in (
            "command",
            "path",
            "endpoint",
            "credential",
            "operator",
            "evidence",
            "log",
            "timestamp",
            "duration",
            "resource",
        ):
            self.rejected(
                plan({**task(), field: "fictional-canary"}), "TASK_SCHEMA_INVALID"
            )
        for field in task():
            self.rejected(
                plan({key: value for key, value in task().items() if key != field}),
                "TASK_SCHEMA_INVALID",
            )
        for row in (None, [], "fictional", False):
            self.rejected(plan(row), "TASK_SCHEMA_INVALID")

    def test_ids_are_bounded_ascii_tokens_without_coercion(self):
        for value in (
            None,
            True,
            1,
            [],
            {},
            "",
            "Sample",
            "1sample",
            "sample/path",
            "sample.name",
            "sample space",
            "échantillon",
            "a" * 41,
        ):
            self.rejected(plan({**task(), "id": value}), "TASK_ID_INVALID")
            self.rejected(
                plan({**task(), "requires": [value]}), "PREREQUISITE_ID_INVALID"
            )
        self.assertEqual(
            checker.check_plan(plan(task("a" * 40)))["status"],
            "DECLARED_PLAN_CONSISTENT",
        )

    def test_duplicate_task_and_prerequisite_ids_are_errors(self):
        self.rejected(plan(task(), task()), "DUPLICATE_TASK_ID")
        self.rejected(
            plan(task(requires=["sample_other", "sample_other"])),
            "DUPLICATE_PREREQUISITE_ID",
        )

    def test_requires_is_a_bounded_list(self):
        for value in (None, {}, "sample_other", False, 1, ["sample_other"] * 33):
            self.rejected(plan({**task(), "requires": value}), "PREREQUISITES_INVALID")
        roots = [task(f"sample_{i}", state="completed") for i in range(32)]
        data = plan(*roots, task(requires=[row["id"] for row in roots]))
        result = checker.check_plan(data)
        self.assertEqual(result["eligible_next_ids"], ["sample_prepare"])
        self.assertEqual(result["counts"]["dependency_edges"], 32)

    def test_states_are_only_exact_declared_values(self):
        for value in (
            None,
            True,
            1,
            [],
            {},
            "PENDING",
            "complete",
            "failed",
            "skipped",
            "pending ",
        ):
            self.rejected(plan({**task(), "state": value}), "TASK_STATE_INVALID")
        for state in checker.STATES:
            self.assertEqual(
                checker.check_plan(plan(task(state=state)))["status"],
                "DECLARED_PLAN_CONSISTENT",
            )

    def test_task_list_bounds(self):
        for value in (None, {}, "fictional", [], [task()] * 129):
            self.rejected(dict(schema_version=1, tasks=value), "PLAN_SCHEMA_INVALID")
        result = checker.check_plan(plan(*(task(f"sample_{i}") for i in range(128))))
        self.assertEqual(len(result["eligible_next_ids"]), 128)

    def test_parse_and_check_do_not_mutate_or_alias_inputs(self):
        data, before = valid_plan(), valid_plan()
        parsed = checker.parse_plan(data)
        self.assertEqual(parsed, data)
        self.assertIsNot(parsed, data)
        self.assertIsNot(parsed["tasks"], data["tasks"])
        self.assertIsNot(parsed["tasks"][1], data["tasks"][1])
        self.assertIsNot(parsed["tasks"][1]["requires"], data["tasks"][1]["requires"])
        parsed["tasks"][1]["requires"].clear()
        checker.check_plan(data)
        self.assertEqual(data, before)


class DependencyTests(Fixture):
    def test_valid_plan_order_eligibility_and_waiting(self):
        result = checker.check_plan(valid_plan())
        self.assertEqual(result["status"], "DECLARED_PLAN_CONSISTENT")
        self.assertEqual(
            result["declared_order"],
            ["sample_prepare", "sample_check", "sample_package"],
        )
        self.assertEqual(result["eligible_next_ids"], ["sample_check"])
        self.assertEqual(result["waiting_ids"], ["sample_package"])
        self.assertEqual(
            result["counts"],
            dict(
                tasks=3,
                dependency_edges=3,
                pending=2,
                in_progress=0,
                completed=1,
                tasks_with_issues=0,
                cycle_members=0,
            ),
        )

    def test_pending_prerequisites_are_normal_waiting_not_an_issue(self):
        result = checker.check_plan(
            plan(task(), task("sample_child", requires=["sample_prepare"]))
        )
        self.assertEqual(result["status"], "DECLARED_PLAN_CONSISTENT")
        self.assertEqual(result["eligible_next_ids"], ["sample_prepare"])
        self.assertEqual(result["waiting_ids"], ["sample_child"])

    def test_multiple_prerequisites_all_must_be_completed(self):
        for state in ("pending", "in_progress", "completed"):
            result = checker.check_plan(
                plan(
                    task("sample_a", state="completed"),
                    task("sample_b", state=state),
                    task("sample_c", requires=["sample_a", "sample_b"]),
                )
            )
            self.assertEqual(result["status"], "DECLARED_PLAN_CONSISTENT")
            self.assertEqual(
                "sample_c" in result["eligible_next_ids"], state == "completed"
            )

    def test_completed_and_active_tasks_are_never_eligible_again(self):
        result = checker.check_plan(
            plan(
                task("sample_a", state="completed"),
                task("sample_b", requires=["sample_a"], state="in_progress"),
                task("sample_c", requires=["sample_b"]),
            )
        )
        self.assertEqual(result["eligible_next_ids"], [])
        self.assertEqual(result["waiting_ids"], ["sample_c"])

    def test_all_completed_plan_is_consistent_without_next_steps(self):
        data = valid_plan()
        for row in data["tasks"]:
            row["state"] = "completed"
        result = checker.check_plan(data)
        self.assertEqual(result["status"], "DECLARED_PLAN_CONSISTENT")
        self.assertEqual(result["eligible_next_ids"], [])
        self.assertEqual(result["waiting_ids"], [])

    def test_missing_prerequisite_blocks_every_plan_list(self):
        result = checker.check_plan(plan(task(requires=["sample_missing"])))
        self.withheld(result)
        self.assertEqual(
            self.issues_for(result, "sample_prepare"), ["PREREQUISITE_NOT_FOUND"]
        )

    def test_self_dependency_is_a_cycle(self):
        result = checker.check_plan(plan(task(requires=["sample_prepare"])))
        self.withheld(result)
        self.assertEqual(
            self.issues_for(result, "sample_prepare"),
            ["SELF_DEPENDENCY", "DEPENDENCY_CYCLE"],
        )
        self.assertEqual(result["counts"]["cycle_members"], 1)

    def test_cycle_members_exclude_tail_and_include_multiparent_cycle_edge(self):
        result = checker.check_plan(
            plan(
                task("sample_a", requires=["sample_b", "sample_root"]),
                task("sample_b", requires=["sample_a"]),
                task("sample_tail", requires=["sample_a"]),
                task("sample_root"),
            )
        )
        self.withheld(result)
        self.assertEqual(self.issues_for(result, "sample_a"), ["DEPENDENCY_CYCLE"])
        self.assertEqual(self.issues_for(result, "sample_b"), ["DEPENDENCY_CYCLE"])
        self.assertEqual(self.issues_for(result, "sample_tail"), [])
        self.assertEqual(result["counts"]["cycle_members"], 2)

    def test_multiple_disconnected_cycles_all_marked(self):
        rows = [
            task("sample_a", requires=["sample_b"]),
            task("sample_b", requires=["sample_a"]),
            task("sample_c", requires=["sample_c"]),
            task("sample_root"),
        ]
        result = checker.check_plan(plan(*rows))
        self.withheld(result)
        self.assertEqual(result["counts"]["cycle_members"], 3)

    def test_completed_claim_requires_completed_prerequisites(self):
        for state in ("pending", "in_progress"):
            result = checker.check_plan(
                plan(
                    task(state=state),
                    task(
                        "sample_child", requires=["sample_prepare"], state="completed"
                    ),
                )
            )
            self.withheld(result)
            self.assertEqual(
                self.issues_for(result, "sample_child"),
                ["COMPLETED_PREREQUISITES_UNSATISFIED"],
            )

    def test_active_claim_requires_completed_prerequisites(self):
        result = checker.check_plan(
            plan(
                task(),
                task("sample_child", requires=["sample_prepare"], state="in_progress"),
            )
        )
        self.withheld(result)
        self.assertEqual(
            self.issues_for(result, "sample_child"),
            ["ACTIVE_PREREQUISITES_UNSATISFIED"],
        )

    def test_unknown_prerequisite_does_not_satisfy_completion_or_active_claim(self):
        for state, code in (
            ("completed", "COMPLETED_PREREQUISITES_UNSATISFIED"),
            ("in_progress", "ACTIVE_PREREQUISITES_UNSATISFIED"),
        ):
            result = checker.check_plan(
                plan(task(requires=["sample_missing"], state=state))
            )
            self.withheld(result)
            self.assertEqual(
                self.issues_for(result, "sample_prepare"),
                ["PREREQUISITE_NOT_FOUND", code],
            )

    def test_invalid_ancestor_claim_cannot_unlock_descendant(self):
        result = checker.check_plan(
            plan(
                task(),
                task("sample_middle", requires=["sample_prepare"], state="completed"),
                task("sample_child", requires=["sample_middle"]),
            )
        )
        self.withheld(result)
        self.assertEqual(self.issues_for(result, "sample_child"), [])

    def test_unrelated_broken_branch_withholds_global_lists(self):
        result = checker.check_plan(
            plan(task(), task("sample_other", requires=["sample_missing"]))
        )
        self.withheld(result)
        self.assertEqual(self.issues_for(result, "sample_prepare"), [])

    def test_fixed_issue_order_with_multiple_problems(self):
        result = checker.check_plan(
            plan(task(requires=["sample_prepare", "sample_missing"], state="completed"))
        )
        actual = self.issues_for(result, "sample_prepare")
        self.assertEqual(
            actual, [code for code in checker.ISSUE_ORDER if code in actual]
        )
        self.assertEqual(
            actual,
            [
                "PREREQUISITE_NOT_FOUND",
                "SELF_DEPENDENCY",
                "DEPENDENCY_CYCLE",
                "COMPLETED_PREREQUISITES_UNSATISFIED",
            ],
        )

    def test_input_task_and_prerequisite_permutations_do_not_change_output(self):
        data = valid_plan()
        expected = checker.check_plan(data)
        for rows in itertools.permutations(data["tasks"]):
            copied = copy.deepcopy(list(rows))
            for row in copied:
                row["requires"].reverse()
            self.assertEqual(checker.check_plan(plan(*copied)), expected)

    def test_order_is_lexical_among_currently_ready_tasks(self):
        result = checker.check_plan(
            plan(
                task("sample_z"),
                task("sample_a", requires=["sample_z"]),
                task("sample_b"),
            )
        )
        self.assertEqual(result["declared_order"], ["sample_b", "sample_z", "sample_a"])

    def test_maximum_depth_without_recursion_and_bounded_result(self):
        rows = [task("sample_000")]
        rows += [
            task(f"sample_{i:03}", requires=[f"sample_{i - 1:03}"])
            for i in range(1, 128)
        ]
        result = checker.check_plan(plan(*reversed(rows)))
        self.assertEqual(result["declared_order"], [row["id"] for row in rows])
        self.assertEqual(result["eligible_next_ids"], ["sample_000"])
        self.assertEqual(len(result["waiting_ids"]), 127)
        self.assertLess(len(json.dumps(result)), 65536)


class OracleTests(Fixture):
    def test_all_512_three_node_graphs_match_independent_path_cycle_oracle(self):
        ids = ["sample_a", "sample_b", "sample_c"]
        for mask in range(512):
            deps = {
                key: [ids[j] for j in range(3) if mask & (1 << (i * 3 + j))]
                for i, key in enumerate(ids)
            }
            result = checker.check_plan(
                plan(*(task(key, requires=deps[key]) for key in ids))
            )
            expected = set()
            for start in ids:
                stack, seen = list(deps[start]), set()
                while stack:
                    key = stack.pop()
                    if key == start:
                        expected.add(start)
                        break
                    if key not in seen:
                        seen.add(key)
                        stack.extend(deps[key])
            actual = {
                row["id"]
                for row in result["tasks"]
                if "DEPENDENCY_CYCLE" in row["issues"]
            }
            self.assertEqual(actual, expected, mask)
            self.assertEqual(result["counts"]["cycle_members"], len(expected))
            if expected:
                self.withheld(result)
            else:
                orders = [
                    order
                    for order in itertools.permutations(ids)
                    if all(
                        order.index(dep) < order.index(key)
                        for key in ids
                        for dep in deps[key]
                    )
                ]
                self.assertEqual(result["declared_order"], list(min(orders)))

    def test_all_216_three_node_dag_state_combinations_match_literal_rules(self):
        ids = ["sample_a", "sample_b", "sample_c"]
        edges = [(1, 0), (2, 0), (2, 1)]
        for mask, states in itertools.product(
            range(8), itertools.product(checker.STATES, repeat=3)
        ):
            deps = {key: [] for key in ids}
            for bit, (child, parent) in enumerate(edges):
                if mask & (1 << bit):
                    deps[ids[child]].append(ids[parent])
            data = plan(
                *(
                    task(key, requires=deps[key], state=states[i])
                    for i, key in enumerate(ids)
                )
            )
            result = checker.check_plan(data)
            invalid = [
                key
                for i, key in enumerate(ids)
                if states[i] != "pending"
                and any(states[ids.index(dep)] != "completed" for dep in deps[key])
            ]
            self.assertEqual(result["counts"]["tasks_with_issues"], len(invalid))
            if invalid:
                self.withheld(result)
            else:
                expected = [
                    key
                    for i, key in enumerate(ids)
                    if states[i] == "pending"
                    and all(states[ids.index(dep)] == "completed" for dep in deps[key])
                ]
                self.assertEqual(result["eligible_next_ids"], expected)
                self.assertEqual(result["status"], "DECLARED_PLAN_CONSISTENT")

    def test_300_seeded_valid_dags_and_100_bruteforce_order_oracles(self):
        rng = random.Random(1601)
        for scenario in range(300):
            count = 4 if scenario < 100 else rng.randrange(1, 25)
            rows = []
            for index in range(count):
                dependencies = [row for row in rows if rng.randrange(3) == 0][-4:]
                state = (
                    rng.choice(checker.STATES)
                    if all(row["state"] == "completed" for row in dependencies)
                    else "pending"
                )
                rows.append(
                    task(
                        f"sample_{index:02}",
                        requires=[row["id"] for row in dependencies],
                        state=state,
                    )
                )
            expected_eligible = sorted(
                row["id"]
                for row in rows
                if row["state"] == "pending"
                and all(
                    next(other["state"] for other in rows if other["id"] == dep)
                    == "completed"
                    for dep in row["requires"]
                )
            )
            rng.shuffle(rows)
            result = checker.check_plan(plan(*rows))
            self.assertEqual(result["status"], "DECLARED_PLAN_CONSISTENT")
            self.assertEqual(result["eligible_next_ids"], expected_eligible)
            if scenario < 100:
                orders = [
                    order
                    for order in itertools.permutations(row["id"] for row in rows)
                    if all(
                        order.index(dep) < order.index(row["id"])
                        for row in rows
                        for dep in row["requires"]
                    )
                ]
                self.assertEqual(result["declared_order"], list(min(orders)))


class ReaderAndCliTests(Fixture):
    def test_bom_and_selected_input_bytes_are_preserved(self):
        source = self.file(raw=b"\xef\xbb\xbf" + json.dumps(valid_plan()).encode())
        before = source.read_bytes()
        self.assertEqual(checker.read_input_json(source), valid_plan())
        self.assertEqual(source.read_bytes(), before)

    def test_duplicate_keys_constants_encoding_and_deep_json_are_refused(self):
        for raw in (
            b'{"schema_version":1,"schema_version":1}',
            b'{"x":NaN}',
            b'{"x":Infinity}',
            b'{"x":-Infinity}',
            b"\xff",
            b"{",
            b"[" * 1200,
        ):
            source = self.file(raw=raw)
            code, output, errors = self.invoke("--plan", source)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output)["status"], "ERROR")
            self.assertEqual(errors, "")

    def test_byte_boundary_and_oversize_refusal_before_open(self):
        source = self.file(raw=b" " * 65537)
        with patch.object(
            checker.os, "open", side_effect=AssertionError("MUST_NOT_OPEN")
        ):
            code, output, _ = self.invoke("--plan", source)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["code"], "INPUT_SIZE_LIMIT")
        source.write_bytes(json.dumps(valid_plan()).encode().ljust(65536))
        self.assertEqual(self.invoke("--plan", source)[0], 0)

    def test_ambiguous_paths_refused_before_metadata_or_open(self):
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
            "COM" + chr(0xB9) + ".json",
            "fictional. ",
            "fictional\nname",
            "x" * 4097,
        )
        for value in values:
            with self.subTest(value=value[:60]):
                with (
                    patch.object(
                        Path, "lstat", side_effect=AssertionError("MUST_NOT_STAT")
                    ),
                    patch.object(
                        checker.os, "open", side_effect=AssertionError("MUST_NOT_OPEN")
                    ),
                ):
                    self.assertEqual(self.invoke("--plan", value)[0], 2)

    def test_missing_input_and_native_details_have_fixed_errors(self):
        source = self.parent / "fictional-private-canary.json"
        code, output, errors = self.invoke("--plan", source)
        self.assertEqual(code, 2)
        self.assertNotIn(str(source), output + errors)
        self.assertNotIn("fictional-private-canary", output + errors)
        try:
            checker.read_input_json(source)
        except checker.ContractError as error:
            self.assertNotIn(str(source), "".join(traceback.format_exception(error)))
            self.assertTrue(error.__suppress_context__)
        else:
            self.fail("EXPECTED_FIXED_ERROR")

    def test_directory_and_hardlinks_are_refused(self):
        self.assertEqual(self.invoke("--plan", self.parent)[0], 2)
        source = self.file(valid_plan())
        link = self.parent / "fictional-hardlink.json"
        try:
            os.link(source, link)
        except OSError:
            self.skipTest("Native hardlink creation unavailable")
        before = source.read_bytes()
        self.assertEqual(self.invoke("--plan", link)[0], 2)
        self.assertEqual(source.read_bytes(), before)

    def test_symlink_leaf_and_ancestor_are_refused(self):
        source = self.file(valid_plan())
        leaf = self.parent / "fictional-link.json"
        folder = self.parent / "fictional-folder-link"
        try:
            leaf.symlink_to(source)
            folder.symlink_to(self.parent, target_is_directory=True)
        except OSError:
            self.skipTest("Native symlink creation unavailable")
        self.assertEqual(self.invoke("--plan", leaf)[0], 2)
        self.assertEqual(self.invoke("--plan", folder / source.name)[0], 2)

    def test_reparse_or_missing_identity_is_refused_synthetically(self):
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

    def test_changed_sampled_identity_is_refused(self):
        source = self.file(valid_plan())
        original, calls = checker._snapshot, 0

        def changed(path):
            nonlocal calls
            ancestors, info = original(path)
            calls += 1
            return (
                ancestors + (("fictional-change",),) if calls == 2 else ancestors
            ), info

        with patch.object(checker, "_snapshot", side_effect=changed):
            code, output, _ = self.invoke("--plan", source)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["code"], "INPUT_CHANGED")

    def test_exit_codes_and_arguments_never_echo_private_canary(self):
        source = self.file(valid_plan())
        self.assertEqual(self.invoke("--plan", source)[0], 0)
        source.write_text(
            json.dumps(plan(task(requires=["sample_missing"]))), encoding="utf-8"
        )
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

    def test_unknown_private_fields_are_not_echoed(self):
        source = self.file({**valid_plan(), "credential": "fictional-private-canary"})
        code, output, errors = self.invoke("--plan", source)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["code"], "PLAN_SCHEMA_INVALID")
        self.assertNotIn("fictional-private-canary", output + errors)

    def test_result_shape_flags_and_no_raw_states_or_requires_echo(self):
        result = checker.check_plan(valid_plan())
        self.assertEqual(
            set(result),
            {
                "schema_version",
                "status",
                "scope",
                "counts",
                "tasks",
                "declared_order",
                "eligible_next_ids",
                "waiting_ids",
                *checker._flags(),
            },
        )
        self.assertTrue(all(result[name] is False for name in checker._flags()))
        self.assertEqual(set(result["tasks"][0]), {"id", "issues"})
        self.assertNotIn('"requires"', json.dumps(result))
        self.assertNotIn('"state"', json.dumps(result))

    def test_pure_check_has_no_file_network_process_or_clock_side_effects(self):
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
                checker.check_plan(valid_plan())["status"], "DECLARED_PLAN_CONSISTENT"
            )

    def test_cli_reads_only_control_file_and_creates_nothing(self):
        source = self.file(valid_plan())
        before = {p.name: p.read_bytes() for p in self.parent.iterdir()}
        with (
            patch.object(checker.os, "scandir", side_effect=AssertionError("NO_SCAN")),
            patch.object(socket, "socket", side_effect=AssertionError("NO_NETWORK")),
            patch.object(
                subprocess, "Popen", side_effect=AssertionError("NO_EXECUTION")
            ),
        ):
            self.assertEqual(self.invoke("--plan", source)[0], 0)
        self.assertEqual(
            {p.name: p.read_bytes() for p in self.parent.iterdir()}, before
        )

    def test_interruption_has_fixed_error_and_exit_130(self):
        with patch.object(checker, "read_input_json", side_effect=KeyboardInterrupt):
            code, output, errors = self.invoke("--plan", "fictional.json")
        self.assertEqual(code, 130)
        self.assertEqual(json.loads(output)["code"], "INTERRUPTED")
        self.assertEqual(errors, "")

    def test_single_script_standalone_child_works_without_collection_files(self):
        script = self.parent / "workflow_check.py"
        shutil.copyfile(SCRIPT, script)
        source = self.file(valid_plan())
        before = {p.name: p.read_bytes() for p in self.parent.iterdir()}
        run = subprocess.run(
            [sys.executable, "-B", str(script), "--plan", str(source)],
            cwd=self.parent,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), checker.check_plan(valid_plan()))
        self.assertEqual(run.stderr, "")
        self.assertEqual(
            {p.name: p.read_bytes() for p in self.parent.iterdir()}, before
        )

    def test_shipped_examples_match_documented_outcomes_and_keep_bytes(self):
        for name, status, eligible in (
            ("valid-plan", "DECLARED_PLAN_CONSISTENT", ["sample_check"]),
            ("missing-prerequisite", "REVIEW_REQUIRED", []),
            ("cycle", "REVIEW_REQUIRED", []),
            ("invalid-completion", "REVIEW_REQUIRED", []),
        ):
            source = SCRIPT.parent / "examples" / (name + ".json")
            before = source.read_bytes()
            code, output, errors = self.invoke("--plan", source)
            result = json.loads(output)
            self.assertEqual(result["status"], status)
            self.assertEqual(result["eligible_next_ids"], eligible)
            self.assertEqual(code, 0 if status == "DECLARED_PLAN_CONSISTENT" else 1)
            self.assertEqual(errors, "")
            self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
