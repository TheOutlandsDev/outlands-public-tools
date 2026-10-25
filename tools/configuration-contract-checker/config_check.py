#!/usr/bin/env python3
"""Validate declared flat settings without executing or changing configuration."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import stat
import sys

VERSION = "0.1.0"
MAX_INPUT_BYTES = 65536
MAX_FIELDS = 128
MAX_RULES = 128
MAX_SETTINGS = 128
MAX_STRING_LENGTH = 4096
MAX_CHOICES = 32
MAX_CHOICE_LENGTH = 128
MIN_INTEGER = -(2**63)
MAX_INTEGER = 2**63 - 1
ID = re.compile(r"[a-z][a-z0-9_-]{0,39}")
KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_-]{0,63}")
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit for prefix in ("com", "lpt") for digit in "123456789¹²³"
}


class ContractError(ValueError):
    """Only a fixed public code; never an input value or native exception."""


def _fail(code):
    raise ContractError(code) from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _integer(value):
    return type(value) is int and MIN_INTEGER <= value <= MAX_INTEGER


def _identifier(value, used):
    if not isinstance(value, str) or not ID.fullmatch(value):
        _fail("CONTRACT_ID_INVALID")
    if value in used:
        _fail("DUPLICATE_CONTRACT_ID")
    used.add(value)


def parse_contract(data):
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "fields", "rules"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["fields"], list)
        or not 0 < len(data["fields"]) <= MAX_FIELDS
        or not isinstance(data["rules"], list)
        or len(data["rules"]) > MAX_RULES
    ):
        _fail("CONTRACT_SCHEMA_INVALID")
    ids = set()
    keys = set()
    fields = []
    for row in data["fields"]:
        required = {"id", "key", "type", "required"}
        if not isinstance(row, dict) or not required.issubset(row):
            _fail("FIELD_SCHEMA_INVALID")
        _identifier(row["id"], ids)
        key = row["key"]
        if not isinstance(key, str) or not KEY.fullmatch(key):
            _fail("FIELD_KEY_INVALID")
        if key in keys:
            _fail("DUPLICATE_FIELD_KEY")
        keys.add(key)
        if type(row["required"]) is not bool:
            _fail("REQUIRED_FLAG_INVALID")
        kind = row["type"]
        if not isinstance(kind, str) or kind not in ("boolean", "integer", "string"):
            _fail("FIELD_TYPE_INVALID")
        optional = (
            {"minimum", "maximum"}
            if kind == "integer"
            else {"min_length", "max_length", "choices"}
            if kind == "string"
            else set()
        )
        if set(row) - required - optional:
            _fail("FIELD_SCHEMA_INVALID")
        if kind == "integer":
            for name in ("minimum", "maximum"):
                if name in row and not _integer(row[name]):
                    _fail("INTEGER_BOUND_INVALID")
            if row.get("minimum", MIN_INTEGER) > row.get("maximum", MAX_INTEGER):
                _fail("INTEGER_BOUNDS_CONTRADICT")
        if kind == "string":
            for name in ("min_length", "max_length"):
                if name in row and (
                    type(row[name]) is not int
                    or not 0 <= row[name] <= MAX_STRING_LENGTH
                ):
                    _fail("STRING_BOUND_INVALID")
            minimum = row.get("min_length", 0)
            maximum = row.get("max_length", MAX_STRING_LENGTH)
            if minimum > maximum:
                _fail("STRING_BOUNDS_CONTRADICT")
            if "choices" in row:
                choices = row["choices"]
                if (
                    not isinstance(choices, list)
                    or not 0 < len(choices) <= MAX_CHOICES
                    or any(
                        not isinstance(choice, str)
                        or len(choice) > MAX_CHOICE_LENGTH
                        or not minimum <= len(choice) <= maximum
                        for choice in choices
                    )
                ):
                    _fail("STRING_CHOICES_INVALID")
                if len(set(choices)) != len(choices):
                    _fail("STRING_CHOICES_INVALID")
        field = dict(row)
        if "choices" in field:
            field["choices"] = list(field["choices"])
        fields.append(field)
    by_id = {row["id"]: row for row in fields}
    pairs = set()
    rules = []
    for row in data["rules"]:
        if not isinstance(row, dict) or set(row) != {"id", "op", "left", "right"}:
            _fail("RULE_SCHEMA_INVALID")
        _identifier(row["id"], ids)
        if row["op"] != "less_or_equal":
            _fail("RULE_OPERATION_INVALID")
        left, right = row["left"], row["right"]
        if (
            not isinstance(left, str)
            or not isinstance(right, str)
            or left not in by_id
            or right not in by_id
            or left == right
            or by_id[left]["type"] != "integer"
            or by_id[right]["type"] != "integer"
        ):
            _fail("RULE_REFERENCE_INVALID")
        pair = (left, right)
        if pair in pairs:
            _fail("DUPLICATE_RULE_PAIR")
        pairs.add(pair)
        rules.append(dict(row))
    return dict(schema_version=1, fields=fields, rules=rules)


def _settings(data):
    if not isinstance(data, dict) or len(data) > MAX_SETTINGS:
        _fail("SETTINGS_SCHEMA_INVALID")
    for key, value in data.items():
        if not isinstance(key, str) or not KEY.fullmatch(key):
            _fail("SETTINGS_KEY_INVALID")
        if type(value) is bool or _integer(value):
            continue
        if isinstance(value, str) and len(value) <= MAX_STRING_LENGTH:
            continue
        _fail("SETTINGS_VALUE_UNSUPPORTED")
    return dict(data)


def _field_result(row, settings):
    if row["key"] not in settings:
        return (
            ("FAIL", "REQUIRED_SETTING_MISSING")
            if row["required"]
            else ("NOT_SUPPLIED", "OPTIONAL_SETTING_NOT_SUPPLIED")
        )
    value = settings[row["key"]]
    kind = row["type"]
    valid_type = (
        type(value) is bool
        if kind == "boolean"
        else _integer(value)
        if kind == "integer"
        else isinstance(value, str)
    )
    if not valid_type:
        return "FAIL", "TYPE_MISMATCH"
    if kind == "integer":
        if value < row.get("minimum", MIN_INTEGER):
            return "FAIL", "BELOW_MINIMUM"
        if value > row.get("maximum", MAX_INTEGER):
            return "FAIL", "ABOVE_MAXIMUM"
    if kind == "string":
        if len(value) < row.get("min_length", 0):
            return "FAIL", "STRING_TOO_SHORT"
        if len(value) > row.get("max_length", MAX_STRING_LENGTH):
            return "FAIL", "STRING_TOO_LONG"
        if "choices" in row and value not in row["choices"]:
            return "FAIL", "CHOICE_NOT_ALLOWED"
    return "PASS", "PRESENT_VALID"


def check_configuration(contract, settings):
    """Check the declared contract only; results never include setting values."""
    contract = parse_contract(contract)
    settings = _settings(settings)
    fields = {row["id"]: row for row in contract["fields"]}
    expected_keys = {row["key"] for row in contract["fields"]}
    unexpected = len(set(settings) - expected_keys)
    checks = []
    states = {}
    for row in contract["fields"]:
        status, evidence = _field_result(row, settings)
        states[row["id"]] = status
        checks.append(
            dict(id=row["id"], kind="field", status=status, evidence=evidence)
        )
    for row in contract["rules"]:
        left = fields[row["left"]]
        right = fields[row["right"]]
        if left["key"] not in settings or right["key"] not in settings:
            status, evidence = "BLOCKED", "DEPENDENCY_NOT_SUPPLIED"
        elif states[row["left"]] != "PASS" or states[row["right"]] != "PASS":
            status, evidence = "BLOCKED", "DEPENDENCY_INVALID"
        elif settings[left["key"]] <= settings[right["key"]]:
            status, evidence = "PASS", "INTEGER_ORDER_SATISFIED"
        else:
            status, evidence = "FAIL", "INTEGER_ORDER_VIOLATED"
        checks.append(dict(id=row["id"], kind="rule", status=status, evidence=evidence))
    counts = Counter(row["status"] for row in checks)
    review = counts["FAIL"] or counts["BLOCKED"] or unexpected
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED" if review else "NO_DECLARED_VIOLATIONS",
        scope="DECLARED_FLAT_SETTINGS_ONLY",
        network_probed=False,
        programs_executed=False,
        configuration_modified=False,
        runtime_verified=False,
        counts=dict(
            passed=counts["PASS"],
            failed=counts["FAIL"],
            not_supplied=counts["NOT_SUPPLIED"],
            blocked=counts["BLOCKED"],
            unexpected_settings=unexpected,
        ),
        checks=checks,
        issues=["SETTINGS_KEYS_UNDECLARED"] if unexpected else [],
    )


def _selected_path(value):
    try:
        raw = os.fspath(value)
        if (
            not isinstance(raw, str)
            or not 0 < len(raw) <= 4096
            or raw.startswith(("\\\\", "//"))
            or any(ord(c) < 32 or ord(c) == 127 for c in raw)
        ):
            _fail("INPUT_PATH_INVALID")
        original = Path(raw)
        if ".." in original.parts or (original.drive and not original.is_absolute()):
            _fail("INPUT_PATH_INVALID")
        path = Path(os.path.abspath(original))
        if path.parent == path or len(path.parts) > 64 or len(str(path)) > 4096:
            _fail("INPUT_PATH_INVALID")
        for part in path.parts:
            if part == path.anchor:
                continue
            if (
                part.endswith((".", " "))
                or part.split(".")[0].casefold() in RESERVED
                or any(c in '\\:<>"|?*' for c in part)
            ):
                _fail("INPUT_PATH_INVALID")
        return path
    except (OSError, TypeError, ValueError):
        _fail("INPUT_PATH_INVALID")


def _linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


def _identity(info, *, directory=False):
    base = (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        getattr(info, "st_file_attributes", 0) & 0x400,
    )
    return base if directory else (*base, info.st_nlink, info.st_size, info.st_mtime_ns)


def _regular_input(info):
    if _linked(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _fail("INPUT_UNAVAILABLE_OR_UNSAFE")
    if not info.st_ino:
        _fail("INPUT_IDENTITY_UNAVAILABLE")


def _snapshot(path):
    ancestors = []
    for ancestor in reversed(path.parents):
        info = ancestor.lstat()
        if _linked(info) or not stat.S_ISDIR(info.st_mode):
            _fail("INPUT_UNAVAILABLE_OR_UNSAFE")
        if not info.st_ino:
            _fail("INPUT_IDENTITY_UNAVAILABLE")
        ancestors.append(_identity(info, directory=True))
    leaf = path.lstat()
    _regular_input(leaf)
    return tuple(ancestors), leaf


def _read_input_json(value):
    path = _selected_path(value)
    ancestors, before = _snapshot(path)
    if before.st_size > MAX_INPUT_BYTES:
        _fail("INPUT_SIZE_LIMIT")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        _regular_input(opened)
        if _identity(opened) != _identity(before):
            _fail("INPUT_CHANGED")
        raw = stream.read(MAX_INPUT_BYTES + 1)
        after = os.fstat(stream.fileno())
    current_ancestors, current = _snapshot(path)
    if (
        ancestors != current_ancestors
        or _identity(after) != _identity(before)
        or _identity(current) != _identity(before)
        or len(raw) != before.st_size
    ):
        _fail("INPUT_CHANGED")
    if len(raw) > MAX_INPUT_BYTES:
        _fail("INPUT_SIZE_LIMIT")
    return json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=_unique_object,
        parse_constant=lambda _: _fail("NONSTANDARD_JSON"),
    )


def read_input_json(value):
    """Read selected bounded JSON; formatted errors suppress native input details."""
    try:
        return _read_input_json(value)
    except ContractError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        _fail("INPUT_OR_CONTRACT_FAILED")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        _fail("ARGUMENTS_INVALID")


def main(argv=None):
    parser = _Parser(
        prog="configuration-contract-checker", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--settings", required=True)
    exit_code = 2
    try:
        args = parser.parse_args(argv)
        result = check_configuration(
            read_input_json(args.contract), read_input_json(args.settings)
        )
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0 if result["status"] == "NO_DECLARED_VIOLATIONS" else 1
    except ContractError as error:
        code = str(error)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        code = "INPUT_OR_CONTRACT_FAILED"
    except KeyboardInterrupt:
        code, exit_code = "INTERRUPTED", 130
    print(
        json.dumps(
            dict(
                status="ERROR",
                code=code,
                network_probed=False,
                programs_executed=False,
                configuration_modified=False,
                runtime_verified=False,
            ),
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
