"""Fictional, offline checks for declared loopback binding plans."""

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
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_public_additions import Fixture, load, ROOT


checker = load(
    "connection_plan_checker", "tools/connection-plan-checker/connection_check.py"
)


def binding(
    identifier="fictional_listener", *, transport="tcp", address="127.0.0.1", port=54321
):
    return {"id": identifier, "transport": transport, "address": address, "port": port}


def plan(*bindings):
    return {"schema_version": 1, "bindings": list(bindings)}


def changed_stat(info, **values):
    fields = {
        name: getattr(info, name)
        for name in dir(info)
        if name.startswith("st_") and not callable(getattr(info, name))
    }
    fields.update(values)
    return SimpleNamespace(**fields)


class PlanFixture(Fixture):
    def metadata(self, value=None, *, raw=None, name="fictional-plan.json"):
        source = self.parent / name
        source.write_bytes(json.dumps(value).encode("utf-8") if raw is None else raw)
        return source

    def invoke(self, *args):
        output = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = checker.main(list(map(str, args)))
        return code, output.getvalue(), errors.getvalue()

    def reader_failure_traceback(self, source):
        try:
            checker.read_input_json(source)
        except checker.PlanError as error:
            self.assertTrue(error.__suppress_context__)
            return "".join(traceback.format_exception(error))
        self.fail("Expected a fixed input error")


class PlanSchemaTests(PlanFixture):
    def test_parse_copies_rows_and_does_not_mutate_input(self):
        data = plan(
            binding(), binding("second", transport="udp", address="::1", port=65535)
        )
        before = copy.deepcopy(data)
        rows = checker.parse_plan(data)
        self.assertEqual(rows, data["bindings"])
        self.assertIsNot(rows, data["bindings"])
        for actual, original in zip(rows, data["bindings"]):
            self.assertIsNot(actual, original)
        rows[0]["port"] = 1
        self.assertEqual(data, before)
        checker.check_plan(data)
        self.assertEqual(data, before)

    def test_top_level_shape_and_schema_are_exact(self):
        valid = plan(binding())
        invalid = [None, [], "fictional", {}, {**valid, "extra": "fictional"}]
        invalid.extend(
            {**valid, "schema_version": version}
            for version in (None, True, 1.0, 0, 2, "1")
        )
        invalid.extend(
            {"schema_version": 1, "bindings": rows}
            for rows in (None, {}, "fictional", (binding(),))
        )
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(checker.PlanError):
                checker.parse_plan(data)

    def test_rows_reject_unknown_missing_and_untyped_fields(self):
        invalid = [None, [], "fictional", {}, {**binding(), "command": "fictional"}]
        invalid.extend(
            {key: value for key, value in binding().items() if key != removed}
            for removed in binding()
        )
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(checker.PlanError):
                checker.parse_plan(plan(row))

    def test_ids_are_unique_and_bounded_neutral_tokens(self):
        for identifier in (
            None,
            True,
            1,
            [],
            {},
            "",
            "A",
            "1listener",
            "fictional/name",
            "fictional name",
            "a" * 41,
            "café",
        ):
            with (
                self.subTest(identifier=identifier),
                self.assertRaises(checker.PlanError),
            ):
                checker.parse_plan(plan(binding(identifier)))
        for identifier in ("a", "a" * 40, "fictional_listener-1"):
            with self.subTest(identifier=identifier):
                self.assertEqual(
                    checker.parse_plan(plan(binding(identifier)))[0]["id"], identifier
                )
        with self.assertRaises(checker.PlanError):
            checker.parse_plan(plan(binding("same"), binding("same", port=54322)))

    def test_transport_is_exact_tcp_or_udp(self):
        for transport in (None, True, 1, [], {}, "TCP", " udp", "udp ", "http", "tcp6"):
            with (
                self.subTest(transport=transport),
                self.assertRaises(checker.PlanError),
            ):
                checker.parse_plan(plan(binding(transport=transport)))

    def test_only_exact_loopback_addresses_are_accepted(self):
        invalid = (
            None,
            True,
            1,
            [],
            {},
            "",
            "localhost",
            "0.0.0.0",
            "::",
            "192.0.2.10",
            "127.0.0.2",
            "127.1",
            "127.000.000.001",
            "2130706433",
            "[::1]",
            "::1%fictional",
            "::ffff:127.0.0.1",
            "0:0:0:0:0:0:0:1",
            "127.0.0.1 ",
            " ::1",
            "127.0.0.1\n",
            "127．0．0．1",
        )
        for address in invalid:
            with self.subTest(address=address), self.assertRaises(checker.PlanError):
                checker.parse_plan(plan(binding(address=address)))

    def test_ports_are_plain_bounded_integers(self):
        for port in (None, True, False, 1.0, "54321", [], {}, 0, -1, 65536):
            with self.subTest(port=port), self.assertRaises(checker.PlanError):
                checker.parse_plan(plan(binding(port=port)))
        for port in (1, 65535):
            self.assertEqual(
                checker.parse_plan(plan(binding(port=port)))[0]["port"], port
            )

    def test_binding_count_bounds_include_full_supported_plan(self):
        for rows in (
            [],
            [
                binding("item_" + str(index))
                for index in range(checker.MAX_BINDINGS + 1)
            ],
        ):
            with self.subTest(count=len(rows)), self.assertRaises(checker.PlanError):
                checker.parse_plan(plan(*rows))
        rows = [
            binding("item_" + str(index), port=index + 1)
            for index in range(checker.MAX_BINDINGS)
        ]
        report = checker.check_plan(plan(*rows))
        self.assertEqual(report["counts"]["bindings"], checker.MAX_BINDINGS)
        self.assertEqual(report["status"], "NO_DECLARED_CONFLICTS")


class DeclarationAndPrivacyTests(PlanFixture):
    def test_one_declaration_is_distinct_without_runtime_claims(self):
        report = checker.check_plan(plan(binding()))
        self.assertEqual(report["status"], "NO_DECLARED_CONFLICTS")
        self.assertEqual(
            report["checks"],
            [
                {
                    "id": "fictional_listener",
                    "status": "DISTINCT",
                    "evidence": "UNIQUE_DECLARED_BINDING",
                }
            ],
        )
        self.assertEqual(
            report["counts"],
            {"bindings": 1, "conflict_groups": 0, "conflicting_bindings": 0},
        )
        self.assertEqual(report["conflict_groups"], [])

    def test_all_members_of_repeated_binding_are_conflicts(self):
        report = checker.check_plan(
            plan(binding("first"), binding("second"), binding("third"))
        )
        self.assertEqual(report["status"], "DECLARED_CONFLICTS")
        self.assertEqual(
            report["conflict_groups"], [{"ids": ["first", "second", "third"]}]
        )
        self.assertEqual(
            report["counts"],
            {"bindings": 3, "conflict_groups": 1, "conflicting_bindings": 3},
        )
        for row in report["checks"]:
            self.assertEqual(row["status"], "CONFLICT")
            self.assertEqual(row["evidence"], "REPEATED_DECLARED_BINDING")

    def test_groups_and_members_follow_declaration_order(self):
        data = plan(
            binding("group_a_first", port=54322),
            binding("group_b_first", transport="udp"),
            binding("group_b_second", transport="udp"),
            binding("unique", address="::1"),
            binding("group_a_second", port=54322),
        )
        report = checker.check_plan(data)
        self.assertEqual(
            report["conflict_groups"],
            [
                {"ids": ["group_a_first", "group_a_second"]},
                {"ids": ["group_b_first", "group_b_second"]},
            ],
        )
        self.assertEqual(
            [row["id"] for row in report["checks"]],
            [row["id"] for row in data["bindings"]],
        )
        self.assertEqual(
            [row["status"] for row in report["checks"]],
            ["CONFLICT", "CONFLICT", "CONFLICT", "DISTINCT", "CONFLICT"],
        )
        self.assertEqual(
            report["counts"],
            {"bindings": 5, "conflict_groups": 2, "conflicting_bindings": 4},
        )

    def test_transport_address_and_port_each_separate_declared_groups(self):
        report = checker.check_plan(
            plan(
                binding("tcp_v4"),
                binding("udp_v4", transport="udp"),
                binding("tcp_v6", address="::1"),
                binding("udp_v6", transport="udp", address="::1"),
                binding("another_port", port=54322),
            )
        )
        self.assertEqual(report["status"], "NO_DECLARED_CONFLICTS")
        self.assertTrue(all(row["status"] == "DISTINCT" for row in report["checks"]))
        self.assertIs(report["runtime_verified"], False)
        self.assertIs(report["availability_verified"], False)

    def test_report_has_only_fixed_metadata_and_operator_ids(self):
        report = checker.check_plan(plan(binding("first"), binding("second")))
        self.assertEqual(
            set(report),
            {
                "schema_version",
                "status",
                "scope",
                "network_probed",
                "programs_executed",
                "runtime_verified",
                "availability_verified",
                "counts",
                "checks",
                "conflict_groups",
            },
        )
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["scope"], "DECLARED_LOOPBACK_BINDINGS_ONLY")
        for flag in (
            "network_probed",
            "programs_executed",
            "runtime_verified",
            "availability_verified",
        ):
            self.assertIs(report[flag], False)
        for row in report["checks"]:
            self.assertEqual(set(row), {"id", "status", "evidence"})
        raw = json.dumps(report)
        for value in (
            "127.0.0.1",
            "54321",
            '"tcp"',
            '"address"',
            '"port"',
            str(self.parent),
        ):
            self.assertNotIn(value, raw)

    def test_planner_does_not_probe_network_run_processes_or_read_targets(self):
        data = plan(binding("first"), binding("second"))
        with (
            patch.object(socket, "socket", side_effect=AssertionError("No sockets")),
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("No connections"),
            ),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("No DNS")),
            patch("subprocess.Popen", side_effect=AssertionError("No processes")),
            patch("subprocess.run", side_effect=AssertionError("No processes")),
            patch.object(os, "system", side_effect=AssertionError("No shell")),
            patch.object(os, "execv", side_effect=AssertionError("No exec")),
            patch("builtins.open", side_effect=AssertionError("No target reads")),
            patch("io.open", side_effect=AssertionError("No target reads")),
            patch.object(os, "open", side_effect=AssertionError("No target reads")),
            patch.object(os, "stat", side_effect=AssertionError("No target metadata")),
            patch.object(os, "lstat", side_effect=AssertionError("No target metadata")),
            patch.object(
                os, "listdir", side_effect=AssertionError("No directory enumeration")
            ),
            patch.object(
                os, "scandir", side_effect=AssertionError("No directory enumeration")
            ),
        ):
            report = checker.check_plan(data)
        self.assertEqual(report["status"], "DECLARED_CONFLICTS")


class GuardedInputTests(PlanFixture):
    def test_utf8_bom_is_accepted_and_input_bytes_are_preserved(self):
        data = plan(binding())
        raw = b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8")
        source = self.metadata(raw=raw)
        self.assertEqual(checker.read_input_json(source), data)
        self.assertEqual(source.read_bytes(), raw)

    def test_duplicate_json_keys_at_top_or_row_are_refused(self):
        samples = (
            b'{"schema_version":1,"schema_version":1,"bindings":[]}',
            b'{"schema_version":1,"bindings":[{"id":"fictional","id":"fictional","transport":"tcp","address":"127.0.0.1","port":54321}]}',
        )
        for raw in samples:
            source = self.metadata(raw=raw)
            with self.subTest(raw=raw), self.assertRaises(checker.PlanError):
                checker.read_input_json(source)
            self.assertEqual(source.read_bytes(), raw)

    def test_nonfinite_numbers_bad_json_and_non_utf8_are_refused(self):
        samples = [b"{", b"\xff", b'{"schema_version":1,"bindings":[]} trailing']
        samples.extend(
            (b'{"fictional":' + value + b"}")
            for value in (b"NaN", b"Infinity", b"-Infinity")
        )
        for raw in samples:
            source = self.metadata(raw=raw)
            with self.subTest(raw=raw), self.assertRaises(checker.PlanError):
                checker.read_input_json(source)

    def test_input_byte_boundary_is_enforced_without_truncation(self):
        raw = json.dumps(plan(binding())).encode("utf-8")
        exact = raw + b" " * (checker.MAX_INPUT_BYTES - len(raw))
        source = self.metadata(raw=exact)
        self.assertEqual(checker.read_input_json(source), plan(binding()))
        source.write_bytes(exact + b" ")
        with self.assertRaises(checker.PlanError):
            checker.read_input_json(source)
        self.assertEqual(source.stat().st_size, checker.MAX_INPUT_BYTES + 1)

    def test_input_read_does_not_enumerate_directories(self):
        source = self.metadata(plan(binding()))
        with (
            patch.object(os, "listdir", side_effect=AssertionError("No inventory")),
            patch.object(os, "scandir", side_effect=AssertionError("No inventory")),
        ):
            self.assertEqual(checker.read_input_json(source), plan(binding()))

    def test_missing_directory_root_and_unsafe_lexical_inputs_are_refused(self):
        paths = (
            self.parent / "missing.json",
            self.root,
            Path(self.parent.anchor),
            str(self.parent / "fictional/../plan.json"),
            r"\\fictional-host\share\plan.json",
            "//fictional-host/share/plan.json",
            "Q:fictional-plan.json",
            "NUL",
            "CON",
        )
        for path in paths:
            with self.subTest(path=str(path)), self.assertRaises(checker.PlanError):
                checker.read_input_json(path)

    def test_permission_errors_are_fixed_without_path_or_message_echo(self):
        source = self.metadata(plan(binding()))
        original = Path.lstat

        def denied(path):
            if path == source:
                raise PermissionError("fictional-sensitive-error-canary")
            return original(path)

        with patch.object(Path, "lstat", denied):
            with self.assertRaises(checker.PlanError) as caught:
                checker.read_input_json(source)
        self.assertNotIn("fictional-sensitive-error-canary", str(caught.exception))
        self.assertNotIn(str(self.parent), str(caught.exception))

    def test_missing_input_traceback_suppresses_native_selected_path(self):
        source = self.parent / "fictional-missing-path-canary.json"
        formatted = self.reader_failure_traceback(source)
        self.assertIn("INPUT_OR_PLAN_FAILED", formatted)
        self.assertNotIn(str(source), formatted)
        self.assertNotIn(source.name, formatted)
        self.assertNotIn("FileNotFoundError", formatted)

    def test_permission_traceback_suppresses_native_path_and_message(self):
        source = self.metadata(plan(binding()), name="fictional-input-path-canary.json")
        message = "fictional-sensitive-permission-canary"
        original = Path.lstat

        def denied(path):
            if path == source:
                raise PermissionError(13, message, str(source))
            return original(path)

        with patch.object(Path, "lstat", denied):
            formatted = self.reader_failure_traceback(source)
        for value in (str(source), source.name, message, "PermissionError"):
            self.assertNotIn(value, formatted)

    def test_invalid_unicode_and_json_tracebacks_suppress_input_values(self):
        canary = "fictional-sensitive-document-canary"
        for raw in (
            json.dumps({"fictional": canary}).encode("utf-8") + b"\xff",
            (json.dumps({"fictional": canary}) + ",").encode("utf-8"),
        ):
            source = self.metadata(raw=raw, name="fictional-invalid-path-canary.json")
            with self.subTest(raw=raw):
                formatted = self.reader_failure_traceback(source)
                for value in (
                    str(source),
                    source.name,
                    canary,
                    "UnicodeDecodeError",
                    "JSONDecodeError",
                ):
                    self.assertNotIn(value, formatted)

    def test_injected_decoder_tracebacks_suppress_native_error_messages(self):
        source = self.metadata(
            plan(binding()), name="fictional-decoder-path-canary.json"
        )
        canary = "fictional-sensitive-decoder-canary"
        errors = (
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, canary),
            json.JSONDecodeError(canary, "{}", 0),
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

    def test_input_reparse_hardlink_and_special_metadata_are_refused_before_open(self):
        source = self.metadata(plan(binding()))
        original = Path.lstat
        for values in (
            {"st_file_attributes": 0x400},
            {"st_nlink": 2},
            {"st_mode": stat.S_IFIFO | 0o600},
        ):

            def unsafe(path):
                info = original(path)
                return changed_stat(info, **values) if path == source else info

            with self.subTest(values=values):
                with (
                    patch.object(Path, "lstat", unsafe),
                    patch.object(
                        os, "open", side_effect=AssertionError("Unsafe input opened")
                    ),
                ):
                    with self.assertRaises(checker.PlanError):
                        checker.read_input_json(source)

    def test_reparse_ancestor_is_refused_before_open(self):
        source = self.metadata(plan(binding()))
        original = Path.lstat

        def reparse(path):
            info = original(path)
            return (
                changed_stat(info, st_file_attributes=0x400)
                if path == self.parent
                else info
            )

        with (
            patch.object(Path, "lstat", reparse),
            patch.object(
                os, "open", side_effect=AssertionError("Unsafe ancestor followed")
            ),
        ):
            with self.assertRaises(checker.PlanError):
                checker.read_input_json(source)

    def test_changed_open_file_identity_is_refused(self):
        source = self.metadata(plan(binding()))
        original = os.fstat

        def changed(descriptor):
            info = original(descriptor)
            return changed_stat(info, st_ino=info.st_ino + 1)

        with patch.object(os, "fstat", changed), self.assertRaises(checker.PlanError):
            checker.read_input_json(source)

    def test_metadata_changed_after_read_is_refused(self):
        source = self.metadata(plan(binding()))
        original = os.fstat
        observations = 0

        def changed_after_read(descriptor):
            nonlocal observations
            observations += 1
            info = original(descriptor)
            return (
                changed_stat(info, st_mtime_ns=info.st_mtime_ns + 1)
                if observations > 1
                else info
            )

        with (
            patch.object(os, "fstat", changed_after_read),
            self.assertRaises(checker.PlanError),
        ):
            checker.read_input_json(source)

    def test_replaced_input_or_ancestor_after_read_is_refused(self):
        source = self.metadata(plan(binding()))
        original = Path.lstat
        for selected in (source, self.parent):
            observations = 0

            def replaced(path):
                nonlocal observations
                info = original(path)
                if path == selected:
                    observations += 1
                    if observations > 1:
                        return changed_stat(info, st_ino=info.st_ino + 1)
                return info

            with self.subTest(selected=selected.name):
                with (
                    patch.object(Path, "lstat", replaced),
                    self.assertRaises(checker.PlanError),
                ):
                    checker.read_input_json(source)

    def test_unavailable_input_or_ancestor_identity_is_refused_before_open(self):
        source = self.metadata(plan(binding()))
        original = Path.lstat
        for selected in (source, self.parent):

            def unidentified(path):
                info = original(path)
                return changed_stat(info, st_ino=0) if path == selected else info

            with self.subTest(selected=selected.name):
                with (
                    patch.object(Path, "lstat", unidentified),
                    patch.object(
                        os,
                        "open",
                        side_effect=AssertionError("Unknown identity opened"),
                    ),
                ):
                    with self.assertRaises(checker.PlanError):
                        checker.read_input_json(source)

    def test_deep_invalid_plan_has_fixed_cli_error(self):
        source = self.metadata(raw=b"[" * 2000 + b"0" + b"]" * 2000)
        code, output, errors = self.invoke("--plan", source)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["status"], "ERROR")
        self.assertNotIn(str(self.parent), output + errors)
        self.assertNotIn("Traceback", output + errors)

    def test_decoder_recursion_error_has_fixed_public_code(self):
        source = self.metadata(plan(binding()))
        with patch.object(
            checker.json,
            "loads",
            side_effect=RecursionError("fictional-sensitive-error-canary"),
        ):
            with self.assertRaises(checker.PlanError) as caught:
                checker.read_input_json(source)
        self.assertNotIn(str(self.parent), str(caught.exception))
        self.assertNotIn("fictional-sensitive-error-canary", str(caught.exception))
        self.assertNotIn("recursion", str(caught.exception).lower())

    def test_native_symlink_input_is_refused(self):
        source = self.metadata(plan(binding()))
        alias = self.parent / "fictional-alias.json"
        try:
            alias.symlink_to(source)
        except OSError:
            self.skipTest("Native symlink creation is unavailable")
        with self.assertRaises(checker.PlanError):
            checker.read_input_json(alias)

    def test_native_hardlink_input_is_refused(self):
        source = self.metadata(plan(binding()))
        alias = self.parent / "fictional-alias.json"
        try:
            os.link(source, alias)
        except OSError:
            self.skipTest("Native hardlink creation is unavailable")
        with self.assertRaises(checker.PlanError):
            checker.read_input_json(source)


class PlanCliTests(PlanFixture):
    def test_abbreviated_plan_flag_is_refused_before_reading(self):
        source = self.metadata(plan(binding()))
        for argument in ("--pl", "--pla"):
            with self.subTest(argument=argument):
                with patch.object(
                    checker,
                    "read_input_json",
                    side_effect=AssertionError("Unexpected plan read"),
                ):
                    code, output, errors = self.invoke(argument, source)
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(output)["status"], "ERROR")
                self.assertNotIn(str(source), output + errors)

    def test_interruption_has_fixed_metadata_and_exit_130(self):
        source = self.metadata(plan(binding()))
        with patch.object(checker, "read_input_json", side_effect=KeyboardInterrupt):
            code, output, errors = self.invoke("--plan", source)
        self.assertEqual(code, 130)
        self.assertEqual(
            json.loads(output),
            {
                "status": "ERROR",
                "code": "INTERRUPTED",
                "network_probed": False,
                "programs_executed": False,
                "runtime_verified": False,
                "availability_verified": False,
            },
        )
        self.assertEqual(errors, "")

    def test_cli_distinct_and_conflict_results_have_expected_exit_codes(self):
        for data, expected, status in (
            (plan(binding()), 0, "NO_DECLARED_CONFLICTS"),
            (plan(binding("first"), binding("second")), 1, "DECLARED_CONFLICTS"),
        ):
            source = self.metadata(data)
            before = source.read_bytes()
            code, output, errors = self.invoke("--plan", source)
            self.assertEqual(code, expected, output + errors)
            self.assertEqual(json.loads(output)["status"], status)
            self.assertEqual(errors, "")
            self.assertNotIn(str(source), output)
            self.assertEqual(source.read_bytes(), before)

    def test_cli_errors_have_fixed_schema_and_do_not_echo_paths_or_values(self):
        canary = "fictional-sensitive-input-canary"
        invalid = self.metadata({**plan(binding()), "private_value": canary})
        for args in (
            ("--plan", invalid),
            ("--plan", self.parent / "fictional-missing-input.json"),
            ("--unknown", canary),
            ("--plan", invalid, "--report", self.parent / "must-not-create.json"),
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
                        "network_probed",
                        "programs_executed",
                        "runtime_verified",
                        "availability_verified",
                    },
                )
                self.assertEqual(result["status"], "ERROR")
                for flag in (
                    "network_probed",
                    "programs_executed",
                    "runtime_verified",
                    "availability_verified",
                ):
                    self.assertIs(result[flag], False)
                for value in (
                    canary,
                    str(self.parent),
                    "fictional-missing-input.json",
                    "Traceback",
                ):
                    self.assertNotIn(value, output + errors)
        self.assertFalse((self.parent / "must-not-create.json").exists())

    def test_static_help_and_version_do_not_reveal_source_path(self):
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

    def test_actual_cli_with_fictional_input_is_stdout_only_and_preserves_input(self):
        source = self.metadata(plan(binding("first"), binding("second")))
        before = source.read_bytes()
        files_before = {path.name for path in self.parent.iterdir()}
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/connection-plan-checker/connection_check.py"),
                "--plan",
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        self.assertEqual(json.loads(process.stdout)["status"], "DECLARED_CONFLICTS")
        self.assertEqual(process.stderr, "")
        self.assertNotIn(str(self.parent), process.stdout)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual({path.name for path in self.parent.iterdir()}, files_before)


if __name__ == "__main__":
    unittest.main()
