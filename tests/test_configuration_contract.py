"""Fictional flat settings; no private configuration or live targets."""

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
    "configuration_contract_checker",
    "tools/configuration-contract-checker/config_check.py",
)
LOWEST = -(2**63)
HIGHEST = 2**63 - 1


def field(
    identifier="fictional_field",
    *,
    key="FictionalSetting",
    kind="integer",
    required=True,
    **constraints,
):
    return {
        "id": identifier,
        "key": key,
        "type": kind,
        "required": required,
        **constraints,
    }


def rule(identifier="fictional_rule", *, left="lower", right="upper"):
    return {"id": identifier, "op": "less_or_equal", "left": left, "right": right}


def contract(*fields, rules=()):
    return {"schema_version": 1, "fields": list(fields), "rules": list(rules)}


def changed_stat(info, **values):
    fields = {
        name: getattr(info, name)
        for name in dir(info)
        if name.startswith("st_") and not callable(getattr(info, name))
    }
    fields.update(values)
    return SimpleNamespace(**fields)


class ContractFixture(Fixture):
    def metadata(self, value=None, *, raw=None, name="fictional-control.json"):
        source = self.parent / name
        source.write_bytes(json.dumps(value).encode("utf-8") if raw is None else raw)
        return source

    def invoke(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = checker.main(list(map(str, args)))
        return code, output.getvalue(), errors.getvalue()

    def ordered_contract(self, *, required=True):
        return contract(
            field(
                "lower", key="FictionalLower", required=required, minimum=0, maximum=10
            ),
            field(
                "upper", key="FictionalUpper", required=required, minimum=0, maximum=10
            ),
            rules=[rule()],
        )

    def by_id(self, result):
        return {row["id"]: row for row in result["checks"]}

    def reader_failure_traceback(self, source):
        try:
            checker.read_input_json(source)
        except checker.ContractError as error:
            self.assertTrue(error.__suppress_context__)
            return "".join(traceback.format_exception(error))
        self.fail("Expected a fixed input error")


class ContractSchemaTests(ContractFixture):
    def test_parsing_copies_contract_rows_and_choices_without_mutation(self):
        data = contract(field(kind="string", choices=["fictional", "example"]))
        before = copy.deepcopy(data)
        parsed = checker.parse_contract(data)
        self.assertEqual(parsed, data)
        self.assertIsNot(parsed, data)
        self.assertIsNot(parsed["fields"], data["fields"])
        self.assertIsNot(parsed["fields"][0], data["fields"][0])
        self.assertIsNot(parsed["fields"][0]["choices"], data["fields"][0]["choices"])
        parsed["fields"][0]["choices"].append("another")
        self.assertEqual(data, before)

    def test_contract_root_shape_and_schema_are_exact(self):
        valid = contract(field())
        invalid = [None, [], "fictional", {}, {**valid, "private_value": "fictional"}]
        invalid.extend(
            {**valid, "schema_version": version}
            for version in (True, 1.0, "1", 0, 2, None)
        )
        invalid.extend(
            {key: value for key, value in valid.items() if key != removed}
            for removed in valid
        )
        for name in ("fields", "rules"):
            invalid.extend(
                {**valid, name: value} for value in (None, {}, "fictional", ())
            )
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(checker.ContractError):
                checker.parse_contract(data)

    def test_field_shapes_types_and_required_boolean_are_strict(self):
        invalid = [
            None,
            [],
            {},
            {**field(), "default": 4},
            {**field(), "pattern": "fictional"},
        ]
        invalid.extend(
            {key: value for key, value in field().items() if key != removed}
            for removed in field()
        )
        invalid.extend(
            field(kind=value) for value in (None, True, 1, [], {}, "Integer", "float")
        )
        invalid.extend(field(required=value) for value in (None, 0, 1, "true", [], {}))
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(checker.ContractError):
                checker.parse_contract(contract(row))

    def test_ids_are_neutral_bounded_and_globally_unique(self):
        for identifier in (
            None,
            True,
            1,
            [],
            {},
            "",
            "A",
            "1field",
            "a b",
            "a/b",
            "a" * 41,
            "café",
        ):
            with (
                self.subTest(identifier=identifier),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_contract(contract(field(identifier)))
        for identifier in ("a", "a" * 40, "fictional_field-1"):
            self.assertEqual(
                checker.parse_contract(contract(field(identifier)))["fields"][0]["id"],
                identifier,
            )
        for data in (
            contract(field("same"), field("same", key="Other")),
            contract(
                field("lower"), field("upper", key="Other"), rules=[rule("lower")]
            ),
            contract(
                field("lower"),
                field("upper", key="Other"),
                rules=[rule("same"), rule("same", left="upper", right="lower")],
            ),
        ):
            with self.subTest(data=data), self.assertRaises(checker.ContractError):
                checker.parse_contract(data)

    def test_keys_are_bounded_unique_and_case_sensitive(self):
        for key in (
            None,
            True,
            1,
            [],
            {},
            "",
            "1setting",
            "a b",
            "a/b",
            "a.b",
            "a" * 65,
            "café",
        ):
            with self.subTest(key=key), self.assertRaises(checker.ContractError):
                checker.parse_contract(contract(field(key=key)))
        with self.assertRaises(checker.ContractError):
            checker.parse_contract(contract(field("one"), field("two")))
        data = contract(field("one", key="Mode"), field("two", key="mode"))
        result = checker.check_configuration(data, {"Mode": 1, "mode": 2})
        self.assertEqual(result["status"], "NO_DECLARED_VIOLATIONS")
        for key in ("_", "Fictional-Key_1", "a" * 64):
            self.assertEqual(
                checker.parse_contract(contract(field(key=key)))["fields"][0]["key"],
                key,
            )

    def test_constraints_are_supported_only_for_their_field_type(self):
        invalid = (
            field(kind="boolean", minimum=0),
            field(kind="boolean", choices=["true"]),
            field(kind="boolean", min_length=0),
            field(kind="integer", choices=["1"]),
            field(kind="integer", max_length=2),
            field(kind="string", minimum=0),
            field(kind="string", maximum=2),
        )
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(checker.ContractError):
                checker.parse_contract(contract(row))

    def test_integer_constraints_are_ordered_signed_64_bit_integers(self):
        invalid = (True, False, 0.0, "0", None, [], {}, LOWEST - 1, HIGHEST + 1)
        for name in ("minimum", "maximum"):
            for value in invalid:
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises(checker.ContractError),
                ):
                    checker.parse_contract(contract(field(**{name: value})))
        with self.assertRaises(checker.ContractError):
            checker.parse_contract(contract(field(minimum=2, maximum=1)))
        self.assertEqual(
            checker.parse_contract(contract(field(minimum=LOWEST, maximum=HIGHEST)))[
                "fields"
            ][0]["minimum"],
            LOWEST,
        )

    def test_string_lengths_are_ordered_bounded_integers(self):
        for name in ("min_length", "max_length"):
            for value in (True, False, 1.0, "1", None, [], {}, -1, 4097):
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises(checker.ContractError),
                ):
                    checker.parse_contract(
                        contract(field(kind="string", **{name: value}))
                    )
        with self.assertRaises(checker.ContractError):
            checker.parse_contract(
                contract(field(kind="string", min_length=2, max_length=1))
            )
        self.assertEqual(
            checker.parse_contract(
                contract(field(kind="string", min_length=0, max_length=4096))
            )["fields"][0]["max_length"],
            4096,
        )

    def test_choices_are_unique_bounded_strings_consistent_with_lengths(self):
        invalid = (
            None,
            {},
            "fictional",
            (),
            [],
            ["a", "a"],
            [True],
            [1],
            [[]],
            ["a" * 129],
            [str(index) for index in range(33)],
        )
        for choices in invalid:
            with (
                self.subTest(choices=choices),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_contract(contract(field(kind="string", choices=choices)))
        for row in (
            field(kind="string", min_length=2, choices=["a"]),
            field(kind="string", max_length=1, choices=["ab"]),
        ):
            with self.subTest(row=row), self.assertRaises(checker.ContractError):
                checker.parse_contract(contract(row))
        for choices in (
            [""],
            ["a" * 128],
            [str(index) for index in range(32)],
            ["é", "e\u0301"],
        ):
            self.assertEqual(
                checker.parse_contract(contract(field(kind="string", choices=choices)))[
                    "fields"
                ][0]["choices"],
                choices,
            )

    def test_rules_have_exact_shape_distinct_integer_references_and_unique_pairs(self):
        base = [field("lower"), field("upper", key="Other")]
        invalid = (
            None,
            [],
            {},
            {**rule(), "expression": "fictional"},
            {**rule(), "op": "eval"},
            {**rule(), "op": []},
            rule(left="unknown"),
            rule(left="lower", right="lower"),
            rule(left=[]),
            {key: value for key, value in rule().items() if key != "right"},
        )
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(checker.ContractError):
                checker.parse_contract(contract(*base, rules=[row]))
        with self.assertRaises(checker.ContractError):
            checker.parse_contract(
                contract(field("lower", kind="boolean"), base[1], rules=[rule()])
            )
        with self.assertRaises(checker.ContractError):
            checker.parse_contract(contract(*base, rules=[rule("one"), rule("two")]))
        self.assertEqual(
            len(
                checker.parse_contract(
                    contract(
                        *base,
                        rules=[rule("one"), rule("two", left="upper", right="lower")],
                    )
                )["rules"]
            ),
            2,
        )

    def test_full_supported_contract_and_count_limits(self):
        fields = [
            field("field_" + str(index), key="Setting_" + str(index))
            for index in range(128)
        ]
        rules = [
            rule("rule_" + str(index), left="field_0", right="field_" + str(index + 1))
            for index in range(127)
        ]
        rules.append(rule("rule_127", left="field_1", right="field_0"))
        result = checker.check_configuration(
            contract(*fields, rules=rules), {row["key"]: 0 for row in fields}
        )
        self.assertEqual(result["counts"]["passed"], 256)
        self.assertEqual(result["status"], "NO_DECLARED_VIOLATIONS")
        for data in (
            contract(),
            contract(*fields, field("extra", key="Extra")),
            contract(
                *fields, rules=[*rules, rule("extra", left="field_2", right="field_0")]
            ),
        ):
            with (
                self.subTest(
                    field_count=len(data["fields"]), rule_count=len(data["rules"])
                ),
                self.assertRaises(checker.ContractError),
            ):
                checker.parse_contract(data)


class ConfigurationSemanticsTests(ContractFixture):
    def test_boolean_integer_and_string_fields_accept_exact_matching_types(self):
        data = contract(
            field("flag", key="Flag", kind="boolean"),
            field("count", key="Count"),
            field("label", key="Label", kind="string"),
        )
        settings = {"Flag": False, "Count": 0, "Label": ""}
        before = copy.deepcopy((data, settings))
        result = checker.check_configuration(data, settings)
        self.assertEqual(result["status"], "NO_DECLARED_VIOLATIONS")
        self.assertEqual(
            result["counts"],
            {
                "passed": 3,
                "failed": 0,
                "not_supplied": 0,
                "blocked": 0,
                "unexpected_settings": 0,
            },
        )
        self.assertTrue(
            all(row["evidence"] == "PRESENT_VALID" for row in result["checks"])
        )
        self.assertEqual((data, settings), before)

    def test_scalar_type_mismatches_are_failures_without_coercion(self):
        cases = (
            ("boolean", 0),
            ("boolean", "false"),
            ("integer", True),
            ("integer", "5"),
            ("string", False),
            ("string", 5),
        )
        for kind, value in cases:
            with self.subTest(kind=kind, value=value):
                result = checker.check_configuration(
                    contract(field(kind=kind)), {"FictionalSetting": value}
                )
                self.assertEqual(result["checks"][0]["status"], "FAIL")
                self.assertEqual(result["checks"][0]["evidence"], "TYPE_MISMATCH")
                self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_settings_are_flat_bounded_and_use_supported_exact_scalars(self):
        for settings in (
            None,
            [],
            "fictional",
            {1: "fictional"},
            {"invalid key": 1},
            {"a" * 65: 1},
            {"FictionalSetting": None},
            {"FictionalSetting": 1.0},
            {"FictionalSetting": []},
            {"FictionalSetting": {}},
            {"FictionalSetting": LOWEST - 1},
            {"FictionalSetting": HIGHEST + 1},
            {"FictionalSetting": "a" * 4097},
            {"Unknown": []},
        ):
            with (
                self.subTest(settings=settings),
                self.assertRaises(checker.ContractError),
            ):
                checker.check_configuration(contract(field()), settings)
        with self.assertRaises(checker.ContractError):
            checker.check_configuration(
                contract(field()), {"Setting_" + str(index): 0 for index in range(129)}
            )

    def test_required_missing_fails_and_optional_missing_is_not_supplied(self):
        data = contract(
            field("required"), field("optional", key="Optional", required=False)
        )
        result = checker.check_configuration(data, {})
        self.assertEqual(
            result["checks"],
            [
                {
                    "id": "required",
                    "kind": "field",
                    "status": "FAIL",
                    "evidence": "REQUIRED_SETTING_MISSING",
                },
                {
                    "id": "optional",
                    "kind": "field",
                    "status": "NOT_SUPPLIED",
                    "evidence": "OPTIONAL_SETTING_NOT_SUPPLIED",
                },
            ],
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        optional = checker.check_configuration(contract(field(required=False)), {})
        self.assertEqual(optional["status"], "NO_DECLARED_VIOLATIONS")
        self.assertEqual(optional["counts"]["not_supplied"], 1)

    def test_integer_bounds_are_inclusive_and_unbounded_extremes_are_supported(self):
        data = contract(field(minimum=-2, maximum=2))
        for value, evidence in (
            (-3, "BELOW_MINIMUM"),
            (-2, "PRESENT_VALID"),
            (2, "PRESENT_VALID"),
            (3, "ABOVE_MAXIMUM"),
        ):
            self.assertEqual(
                checker.check_configuration(data, {"FictionalSetting": value})[
                    "checks"
                ][0]["evidence"],
                evidence,
            )
        for value in (LOWEST, HIGHEST):
            self.assertEqual(
                checker.check_configuration(
                    contract(field()), {"FictionalSetting": value}
                )["checks"][0]["status"],
                "PASS",
            )

    def test_string_length_bounds_use_unicode_codepoints_without_normalization(self):
        data = contract(field(kind="string", min_length=1, max_length=1))
        for value, evidence in (
            ("", "STRING_TOO_SHORT"),
            ("é", "PRESENT_VALID"),
            ("🐢", "PRESENT_VALID"),
            ("e\u0301", "STRING_TOO_LONG"),
            ("ab", "STRING_TOO_LONG"),
        ):
            self.assertEqual(
                checker.check_configuration(data, {"FictionalSetting": value})[
                    "checks"
                ][0]["evidence"],
                evidence,
            )
        self.assertEqual(
            checker.check_configuration(
                contract(field(kind="string")), {"FictionalSetting": "a" * 4096}
            )["checks"][0]["status"],
            "PASS",
        )

    def test_string_choices_are_exact_and_no_expansion_or_trimming_occurs(self):
        data = contract(
            field(
                kind="string",
                choices=[
                    "Fictional",
                    "é",
                    "${FICTIONAL_SETTING}",
                    "%FICTIONAL_SETTING%",
                    "fictional/script()",
                    " padded ",
                ],
            )
        )
        for value in data["fields"][0]["choices"]:
            self.assertEqual(
                checker.check_configuration(data, {"FictionalSetting": value})[
                    "checks"
                ][0]["status"],
                "PASS",
            )
        for value in ("fictional", "e\u0301", "padded", "expanded"):
            self.assertEqual(
                checker.check_configuration(data, {"FictionalSetting": value})[
                    "checks"
                ][0]["evidence"],
                "CHOICE_NOT_ALLOWED",
            )

    def test_cross_field_integer_order_includes_equality(self):
        data = self.ordered_contract()
        for lower, upper, status, evidence in (
            (1, 2, "PASS", "INTEGER_ORDER_SATISFIED"),
            (2, 2, "PASS", "INTEGER_ORDER_SATISFIED"),
            (3, 2, "FAIL", "INTEGER_ORDER_VIOLATED"),
        ):
            result = checker.check_configuration(
                data, {"FictionalLower": lower, "FictionalUpper": upper}
            )
            self.assertEqual(self.by_id(result)["fictional_rule"]["status"], status)
            self.assertEqual(self.by_id(result)["fictional_rule"]["evidence"], evidence)

    def test_any_missing_rule_operand_blocks_instead_of_passing(self):
        for required in (True, False):
            data = self.ordered_contract(required=required)
            for settings in (
                {},
                {"FictionalLower": 1},
                {"FictionalUpper": 2},
                {"FictionalUpper": "invalid"},
            ):
                with self.subTest(required=required, settings=settings):
                    result = checker.check_configuration(data, settings)
                    self.assertEqual(
                        self.by_id(result)["fictional_rule"],
                        {
                            "id": "fictional_rule",
                            "kind": "rule",
                            "status": "BLOCKED",
                            "evidence": "DEPENDENCY_NOT_SUPPLIED",
                        },
                    )
                    self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_invalid_present_rule_operand_blocks_instead_of_comparing(self):
        for settings in (
            {"FictionalLower": True, "FictionalUpper": 2},
            {"FictionalLower": 1, "FictionalUpper": "invalid"},
            {"FictionalLower": -1, "FictionalUpper": 2},
            {"FictionalLower": 1, "FictionalUpper": 11},
        ):
            result = checker.check_configuration(self.ordered_contract(), settings)
            self.assertEqual(
                self.by_id(result)["fictional_rule"],
                {
                    "id": "fictional_rule",
                    "kind": "rule",
                    "status": "BLOCKED",
                    "evidence": "DEPENDENCY_INVALID",
                },
            )
            self.assertEqual(result["counts"]["blocked"], 1)
            self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_unknown_keys_fail_without_echoing_setting_keys_or_values(self):
        key, value = "FictionalSensitiveKey", "fictional-sensitive-value-canary"
        result = checker.check_configuration(
            contract(field()), {"FictionalSetting": 1, key: value}
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["issues"], ["SETTINGS_KEYS_UNDECLARED"])
        self.assertEqual(result["counts"]["unexpected_settings"], 1)
        self.assertNotIn(key, json.dumps(result))
        self.assertNotIn(value, json.dumps(result))

    def test_setting_lookup_is_exact_case_and_does_not_fill_missing_fields(self):
        result = checker.check_configuration(
            contract(field(key="FictionalMode")), {"fictionalmode": 1}
        )
        self.assertEqual(result["checks"][0]["evidence"], "REQUIRED_SETTING_MISSING")
        self.assertEqual(result["counts"]["failed"], 1)
        self.assertEqual(result["counts"]["unexpected_settings"], 1)
        self.assertEqual(result["issues"], ["SETTINGS_KEYS_UNDECLARED"])
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertNotIn("FictionalMode", json.dumps(result))
        self.assertNotIn("fictionalmode", json.dumps(result))

    def test_mixed_status_counts_cover_every_check_without_false_rule_pass(self):
        data = contract(
            field("flag", key="Flag", kind="boolean"),
            field("lower", key="Lower", minimum=0),
            field("upper", key="Upper", required=False),
            rules=[rule()],
        )
        result = checker.check_configuration(
            data, {"Flag": False, "Lower": -1, "FictionalUnexpected": "fictional"}
        )
        self.assertEqual(
            result["counts"],
            {
                "passed": 1,
                "failed": 1,
                "not_supplied": 1,
                "blocked": 1,
                "unexpected_settings": 1,
            },
        )
        self.assertEqual(
            [row["status"] for row in result["checks"]],
            ["PASS", "FAIL", "NOT_SUPPLIED", "BLOCKED"],
        )
        self.assertEqual(
            self.by_id(result)["fictional_rule"]["evidence"], "DEPENDENCY_NOT_SUPPLIED"
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_report_is_fixed_metadata_with_only_declared_ids(self):
        data = self.ordered_contract()
        result = checker.check_configuration(
            data, {"FictionalLower": 1, "FictionalUpper": 2}
        )
        self.assertEqual(
            set(result),
            {
                "schema_version",
                "status",
                "scope",
                "network_probed",
                "programs_executed",
                "configuration_modified",
                "runtime_verified",
                "counts",
                "checks",
                "issues",
            },
        )
        self.assertEqual(result["scope"], "DECLARED_FLAT_SETTINGS_ONLY")
        self.assertEqual(result["schema_version"], 1)
        for flag in (
            "network_probed",
            "programs_executed",
            "configuration_modified",
            "runtime_verified",
        ):
            self.assertIs(result[flag], False)
        self.assertEqual(
            result["counts"],
            {
                "passed": 3,
                "failed": 0,
                "not_supplied": 0,
                "blocked": 0,
                "unexpected_settings": 0,
            },
        )
        self.assertEqual(
            [row["id"] for row in result["checks"]],
            ["lower", "upper", "fictional_rule"],
        )
        for row in result["checks"]:
            self.assertEqual(set(row), {"id", "kind", "status", "evidence"})
        self.assertEqual(result["issues"], [])
        for value in (
            "FictionalLower",
            "FictionalUpper",
            str(self.parent),
            '"key"',
            '"value"',
        ):
            self.assertNotIn(value, json.dumps(result))

    def test_evaluation_has_no_network_process_environment_or_target_file_activity(
        self,
    ):
        data = contract(field(kind="string", choices=["${FICTIONAL_SETTING}"]))
        settings = {"FictionalSetting": "${FICTIONAL_SETTING}"}
        before = copy.deepcopy((data, settings))
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
            patch.object(
                os, "getenv", side_effect=AssertionError("No environment reads")
            ),
            patch("builtins.open", side_effect=AssertionError("No target reads")),
            patch("io.open", side_effect=AssertionError("No target reads")),
            patch.object(os, "open", side_effect=AssertionError("No target reads")),
            patch.object(os, "stat", side_effect=AssertionError("No target metadata")),
            patch.object(os, "lstat", side_effect=AssertionError("No target metadata")),
            patch.object(os, "listdir", side_effect=AssertionError("No inventories")),
            patch.object(os, "scandir", side_effect=AssertionError("No inventories")),
        ):
            result = checker.check_configuration(data, settings)
        self.assertEqual(result["status"], "NO_DECLARED_VIOLATIONS")
        self.assertEqual((data, settings), before)


class GuardedJsonTests(ContractFixture):
    def test_bom_and_bounded_json_read_preserves_original_bytes(self):
        data = contract(field())
        raw = b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8")
        raw += b" " * (65536 - len(raw))
        source = self.metadata(raw=raw)
        self.assertEqual(checker.read_input_json(source), data)
        self.assertEqual(source.read_bytes(), raw)
        source.write_bytes(raw + b" ")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(source)

    def test_duplicate_keys_nonfinite_json_and_invalid_encoding_are_refused(self):
        samples = [
            b'{"schema_version":1,"schema_version":1}',
            b'{"Fictional":1,"Fictional":2}',
            b'{"fields":[{"id":"first","id":"second"}]}',
            b"{",
            b"\xff",
            b"{} trailing",
        ]
        samples.extend(
            b'{"Fictional":' + value + b"}"
            for value in (b"NaN", b"Infinity", b"-Infinity")
        )
        for raw in samples:
            source = self.metadata(raw=raw)
            with self.subTest(raw=raw), self.assertRaises(checker.ContractError):
                checker.read_input_json(source)

    def test_missing_nonfile_root_and_unsafe_paths_are_refused(self):
        paths = (
            self.parent / "missing.json",
            self.root,
            Path(self.parent.anchor),
            str(self.parent / "fictional/../control.json"),
            r"\\fictional-host\share\control.json",
            "//fictional-host/share/control.json",
            "Q:fictional-control.json",
            "NUL",
            "CON",
        )
        for path in paths:
            with self.subTest(path=str(path)), self.assertRaises(checker.ContractError):
                checker.read_input_json(path)

    def test_reader_does_not_enumerate_directories(self):
        source = self.metadata(contract(field()))
        with (
            patch.object(os, "scandir", side_effect=AssertionError("No inventory")),
            patch.object(os, "listdir", side_effect=AssertionError("No inventory")),
        ):
            self.assertEqual(checker.read_input_json(source), contract(field()))

    def test_link_special_and_unavailable_identity_metadata_are_refused_before_open(
        self,
    ):
        source = self.metadata(contract(field()))
        original = Path.lstat
        for values in (
            {"st_file_attributes": 0x400},
            {"st_nlink": 2},
            {"st_mode": stat.S_IFIFO | 0o600},
            {"st_ino": 0},
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
                    with self.assertRaises(checker.ContractError):
                        checker.read_input_json(source)

    def test_unsafe_or_unidentified_ancestor_is_refused_before_open(self):
        source = self.metadata(contract(field()))
        original = Path.lstat
        for values in ({"st_file_attributes": 0x400}, {"st_ino": 0}):

            def unsafe(path):
                info = original(path)
                return changed_stat(info, **values) if path == self.parent else info

            with self.subTest(values=values):
                with (
                    patch.object(Path, "lstat", unsafe),
                    patch.object(
                        os,
                        "open",
                        side_effect=AssertionError("Unsafe ancestor followed"),
                    ),
                ):
                    with self.assertRaises(checker.ContractError):
                        checker.read_input_json(source)

    def test_opened_and_post_read_metadata_changes_are_refused(self):
        source = self.metadata(contract(field()))
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

    def test_input_or_parent_replacement_after_read_is_refused(self):
        source = self.metadata(contract(field()))
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

    def test_missing_input_and_native_permission_tracebacks_hide_canaries(self):
        source = self.parent / "fictional-missing-path-canary.json"
        formatted = self.reader_failure_traceback(source)
        for value in (str(source), source.name, "FileNotFoundError"):
            self.assertNotIn(value, formatted)
        source = self.metadata(
            contract(field()), name="fictional-input-path-canary.json"
        )
        message = "fictional-sensitive-native-message"
        original = Path.lstat

        def denied(path):
            if path == source:
                raise PermissionError(13, message, str(source))
            return original(path)

        with patch.object(Path, "lstat", denied):
            formatted = self.reader_failure_traceback(source)
        for value in (str(source), source.name, message, "PermissionError"):
            self.assertNotIn(value, formatted)

    def test_unicode_json_and_recursion_exception_tracebacks_hide_messages(self):
        source = self.metadata(
            contract(field()), name="fictional-decoder-path-canary.json"
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
        source = self.metadata(contract(field()))
        alias = self.parent / "fictional-alias.json"
        try:
            alias.symlink_to(source)
        except OSError:
            self.skipTest("Native symlink creation is unavailable")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(alias)

    def test_native_hardlink_input_is_refused(self):
        source = self.metadata(contract(field()))
        alias = self.parent / "fictional-alias.json"
        try:
            os.link(source, alias)
        except OSError:
            self.skipTest("Native hardlink creation is unavailable")
        with self.assertRaises(checker.ContractError):
            checker.read_input_json(source)


class ConfigurationCliTests(ContractFixture):
    def test_cli_success_and_review_exit_codes_preserve_both_inputs(self):
        source = self.metadata(contract(field()), name="fictional-contract.json")
        for value, expected in ((1, 0), ("fictional-sensitive-value-canary", 1)):
            settings = self.metadata(
                {"FictionalSetting": value}, name="fictional-settings.json"
            )
            before = {path: path.read_bytes() for path in (source, settings)}
            code, output, errors = self.invoke(
                "--contract", source, "--settings", settings
            )
            self.assertEqual(code, expected, output + errors)
            self.assertEqual(errors, "")
            for path, raw in before.items():
                self.assertEqual(path.read_bytes(), raw)
                self.assertNotIn(str(path), output)
            self.assertNotIn("FictionalSetting", output)
            self.assertNotIn("fictional-sensitive-value-canary", output)

    def test_cli_errors_have_fixed_schema_and_no_private_values(self):
        source = self.metadata(contract(field()), name="fictional-contract.json")
        canary = "fictional-sensitive-value-canary"
        settings = self.metadata(
            {"FictionalPrivateKey": [canary]}, name="fictional-settings.json"
        )
        for args in (
            ("--contract", source, "--settings", settings),
            (
                "--contract",
                source,
                "--settings",
                self.parent / "missing-settings-canary.json",
            ),
            ("--unknown", canary),
            (
                "--contract",
                source,
                "--settings",
                settings,
                "--report",
                self.parent / "must-not-create.json",
            ),
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
                        "configuration_modified",
                        "runtime_verified",
                    },
                )
                self.assertEqual(result["status"], "ERROR")
                for flag in (
                    "network_probed",
                    "programs_executed",
                    "configuration_modified",
                    "runtime_verified",
                ):
                    self.assertIs(result[flag], False)
                for value in (
                    canary,
                    "FictionalPrivateKey",
                    str(self.parent),
                    "missing-settings-canary.json",
                    "Traceback",
                ):
                    self.assertNotIn(value, output + errors)
        self.assertFalse((self.parent / "must-not-create.json").exists())

    def test_cli_abbreviations_are_refused_before_input_reading(self):
        source = self.metadata(contract(field()))
        for args in (
            ("--contr", source, "--settings", source),
            ("--contract", source, "--sett", source),
        ):
            with patch.object(
                checker,
                "read_input_json",
                side_effect=AssertionError("Unexpected input read"),
            ):
                code, output, errors = self.invoke(*args)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output)["status"], "ERROR")
            self.assertNotIn(str(source), output + errors)

    def test_interruption_uses_fixed_false_flags_and_exit_130(self):
        source = self.metadata(contract(field()))
        with patch.object(checker, "read_input_json", side_effect=KeyboardInterrupt):
            code, output, errors = self.invoke(
                "--contract", source, "--settings", source
            )
        self.assertEqual(code, 130)
        self.assertEqual(
            json.loads(output),
            {
                "status": "ERROR",
                "code": "INTERRUPTED",
                "network_probed": False,
                "programs_executed": False,
                "configuration_modified": False,
                "runtime_verified": False,
            },
        )
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

    def test_actual_cli_is_stdout_only_and_does_not_modify_inputs(self):
        source = self.metadata(
            self.ordered_contract(required=False), name="fictional-contract.json"
        )
        settings = self.metadata({"FictionalLower": 1}, name="fictional-settings.json")
        before = {path: path.read_bytes() for path in (source, settings)}
        names_before = {path.name for path in self.parent.iterdir()}
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/configuration-contract-checker/config_check.py"),
                "--contract",
                str(source),
                "--settings",
                str(settings),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(self.by_id(result)["fictional_rule"]["status"], "BLOCKED")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(process.stderr, "")
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)
            self.assertNotIn(str(path), process.stdout)
        self.assertEqual({path.name for path in self.parent.iterdir()}, names_before)


if __name__ == "__main__":
    unittest.main()
