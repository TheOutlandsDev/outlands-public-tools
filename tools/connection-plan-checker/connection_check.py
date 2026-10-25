#!/usr/bin/env python3
"""Check declared loopback binding plans without contacting or configuring hosts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

VERSION = "0.1.0"
MAX_INPUT_BYTES = 65536
MAX_BINDINGS = 128
ID = re.compile(r"[a-z][a-z0-9_-]{0,39}")
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit for prefix in ("com", "lpt") for digit in "123456789¹²³"
}


class PlanError(ValueError):
    """A fixed public code, never an operator input or native exception."""


def _fail(code):
    raise PlanError(code) from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def parse_plan(data):
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "bindings"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["bindings"], list)
        or not 0 < len(data["bindings"]) <= MAX_BINDINGS
    ):
        _fail("PLAN_SCHEMA_INVALID")
    rows = []
    seen = set()
    for row in data["bindings"]:
        if not isinstance(row, dict) or set(row) != {
            "id",
            "transport",
            "address",
            "port",
        }:
            _fail("BINDING_SCHEMA_INVALID")
        identifier = row["id"]
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            _fail("BINDING_ID_INVALID")
        if identifier in seen:
            _fail("DUPLICATE_BINDING_ID")
        seen.add(identifier)
        if not isinstance(row["transport"], str) or row["transport"] not in (
            "tcp",
            "udp",
        ):
            _fail("TRANSPORT_INVALID")
        if not isinstance(row["address"], str) or row["address"] not in (
            "127.0.0.1",
            "::1",
        ):
            _fail("LOOPBACK_LITERAL_REQUIRED")
        if type(row["port"]) is not int or not 1 <= row["port"] <= 65535:
            _fail("PORT_INVALID")
        rows.append(dict(row))
    return rows


def check_plan(data):
    """Compare only the supplied declaration tuples; never inspect listeners."""
    bindings = parse_plan(data)
    groups = {}
    for row in bindings:
        key = (row["transport"], row["address"], row["port"])
        groups.setdefault(key, []).append(row["id"])
    conflicts = [dict(ids=list(ids)) for ids in groups.values() if len(ids) > 1]
    conflicting = {identifier for group in conflicts for identifier in group["ids"]}
    checks = [
        dict(
            id=row["id"],
            status="CONFLICT" if row["id"] in conflicting else "DISTINCT",
            evidence="REPEATED_DECLARED_BINDING"
            if row["id"] in conflicting
            else "UNIQUE_DECLARED_BINDING",
        )
        for row in bindings
    ]
    return dict(
        schema_version=1,
        status="DECLARED_CONFLICTS" if conflicts else "NO_DECLARED_CONFLICTS",
        scope="DECLARED_LOOPBACK_BINDINGS_ONLY",
        network_probed=False,
        programs_executed=False,
        runtime_verified=False,
        availability_verified=False,
        counts=dict(
            bindings=len(bindings),
            conflict_groups=len(conflicts),
            conflicting_bindings=len(conflicting),
        ),
        checks=checks,
        conflict_groups=conflicts,
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
    """Read the selected bounded JSON; errors contain only fixed public codes."""
    try:
        return _read_input_json(value)
    except PlanError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        _fail("INPUT_OR_PLAN_FAILED")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        _fail("ARGUMENTS_INVALID")


def main(argv=None):
    parser = _Parser(
        prog="connection-plan-checker", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--plan", required=True)
    exit_code = 2
    try:
        args = parser.parse_args(argv)
        result = check_plan(read_input_json(args.plan))
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 1 if result["status"] == "DECLARED_CONFLICTS" else 0
    except PlanError as error:
        code = str(error)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        code = "INPUT_OR_PLAN_FAILED"
    except KeyboardInterrupt:
        code = "INTERRUPTED"
        exit_code = 130
    print(
        json.dumps(
            dict(
                status="ERROR",
                code=code,
                network_probed=False,
                programs_executed=False,
                runtime_verified=False,
                availability_verified=False,
            ),
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
