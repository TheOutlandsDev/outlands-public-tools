#!/usr/bin/env python3
"""Check declared full/incremental relationships without inspecting backups."""

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
MAX_SNAPSHOTS = 256
MAX_SEQUENCE = 1000000
ID = re.compile(r"[a-z][a-z0-9_-]{0,39}")
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit for prefix in ("com", "lpt") for digit in "123456789Â¹Â²Â³"
}
ISSUE_ORDER = (
    "FULL_PARENT_NOT_NULL",
    "INCREMENTAL_PARENT_NOT_SUPPLIED",
    "PARENT_NOT_FOUND",
    "PARENT_SELF_REFERENCE",
    "PARENT_SERIES_MISMATCH",
    "PARENT_SEQUENCE_NOT_EARLIER",
    "SEQUENCE_REUSED_IN_SERIES",
    "DEPENDENCY_CYCLE",
)


class ContractError(ValueError):
    """A fixed code without selected paths, metadata or native exception text."""


def _fail(code):
    raise ContractError(code) from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _identifier(value, code):
    if not isinstance(value, str) or not ID.fullmatch(value):
        _fail(code)


def parse_plan(data):
    """Validate JSON-shaped input and copy its declarations without repair."""
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "restore_point_id", "snapshots"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["snapshots"], list)
        or not 1 <= len(data["snapshots"]) <= MAX_SNAPSHOTS
    ):
        _fail("PLAN_SCHEMA_INVALID")
    _identifier(data["restore_point_id"], "RESTORE_POINT_ID_INVALID")
    seen, rows = set(), []
    for row in data["snapshots"]:
        if not isinstance(row, dict) or set(row) != {
            "id",
            "series_id",
            "kind",
            "parent_id",
            "sequence",
        }:
            _fail("SNAPSHOT_SCHEMA_INVALID")
        _identifier(row["id"], "SNAPSHOT_ID_INVALID")
        _identifier(row["series_id"], "SERIES_ID_INVALID")
        if row["id"] in seen:
            _fail("DUPLICATE_SNAPSHOT_ID")
        seen.add(row["id"])
        if row["kind"] not in ("full", "incremental"):
            _fail("SNAPSHOT_KIND_INVALID")
        if row["parent_id"] is not None:
            _identifier(row["parent_id"], "PARENT_ID_INVALID")
        if type(row["sequence"]) is not int or not 0 <= row["sequence"] <= MAX_SEQUENCE:
            _fail("SEQUENCE_INVALID")
        rows.append(dict(row))
    return dict(
        schema_version=1, restore_point_id=data["restore_point_id"], snapshots=rows
    )


def _cycle_members(rows):
    """Find all cycle members in a bounded one-parent graph without recursion."""
    finished, members = set(), set()
    for start in sorted(rows):
        trail, positions = [], {}
        current = start
        while current in rows and current not in finished:
            if current in positions:
                members.update(trail[positions[current] :])
                break
            positions[current] = len(trail)
            trail.append(current)
            current = rows[current]["parent_id"]
        finished.update(trail)
    return members


def _flags():
    return dict(
        filesystem_scanned=False,
        backup_contents_read=False,
        metadata_verified=False,
        restore_performed=False,
        deletion_performed=False,
        deletion_authorized=False,
        commands_generated=False,
        network_probed=False,
    )


def check_chain(data):
    """Return local issues and a selected order derived only from declarations."""
    plan = parse_plan(data)
    rows = {row["id"]: row for row in plan["snapshots"]}
    cycles = _cycle_members(rows)
    generations = {}
    for row in rows.values():
        key = row["series_id"], row["sequence"]
        generations[key] = generations.get(key, 0) + 1
    problems = {}
    for identifier, row in rows.items():
        issues = []
        parent = row["parent_id"]
        if row["kind"] == "full" and parent is not None:
            issues.append("FULL_PARENT_NOT_NULL")
        if row["kind"] == "incremental" and parent is None:
            issues.append("INCREMENTAL_PARENT_NOT_SUPPLIED")
        if parent is not None:
            if parent not in rows:
                issues.append("PARENT_NOT_FOUND")
            else:
                other = rows[parent]
                if parent == identifier:
                    issues.append("PARENT_SELF_REFERENCE")
                if other["series_id"] != row["series_id"]:
                    issues.append("PARENT_SERIES_MISMATCH")
                if other["sequence"] >= row["sequence"]:
                    issues.append("PARENT_SEQUENCE_NOT_EARLIER")
        if generations[row["series_id"], row["sequence"]] > 1:
            issues.append("SEQUENCE_REUSED_IN_SERIES")
        if identifier in cycles:
            issues.append("DEPENDENCY_CYCLE")
        problems[identifier] = issues

    target = plan["restore_point_id"]
    order, target_issues = [], []
    if target not in rows:
        target_issues.append("RESTORE_POINT_NOT_FOUND")
    else:
        current = target
        while current is not None:
            # Any unsupported relationship blocks the whole selected order.
            if current not in rows or problems[current]:
                target_issues.append("TARGET_CHAIN_BLOCKED")
                order = []
                break
            order.append(current)
            current = rows[current]["parent_id"]
        order.reverse()
    review = any(problems.values()) or bool(target_issues)
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED" if review else "DECLARED_CHAIN_CONSISTENT",
        scope="DECLARED_FULL_INCREMENTAL_METADATA_ONLY",
        **_flags(),
        counts=dict(
            snapshots=len(rows),
            series=len({row["series_id"] for row in rows.values()}),
            snapshots_with_issues=sum(bool(value) for value in problems.values()),
            cycle_members=len(cycles),
        ),
        snapshots=[dict(id=key, issues=problems[key]) for key in sorted(rows)],
        target=dict(
            id=target,
            status="REVIEW_REQUIRED" if target_issues else "DECLARED_CHAIN_CONSISTENT",
            issues=target_issues,
            declared_order=order,
        ),
    )


def _validate_path_parts(path):
    for part in path.parts:
        if part == path.anchor:
            continue
        if (
            part.endswith((".", " "))
            or part.split(".")[0].casefold() in RESERVED
            or any(c in '\\:<>"|?*' for c in part)
        ):
            _fail("INPUT_PATH_INVALID")


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
        # Windows absolute-path normalization can erase trailing dots/spaces.
        _validate_path_parts(original)
        path = Path(os.path.abspath(original))
        if path.parent == path or len(path.parts) > 64 or len(str(path)) > 4096:
            _fail("INPUT_PATH_INVALID")
        _validate_path_parts(path)
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
    """Read selected bounded JSON; formatted errors suppress native input detail."""
    try:
        return _read_input_json(value)
    except ContractError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        _fail("INPUT_OR_PLAN_FAILED")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        _fail("ARGUMENTS_INVALID")


def main(argv=None):
    parser = _Parser(
        prog="backup-chain-checker", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--plan", required=True)
    exit_code = 2
    try:
        args = parser.parse_args(argv)
        result = check_chain(read_input_json(args.plan))
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0 if result["status"] == "DECLARED_CHAIN_CONSISTENT" else 1
    except ContractError as error:
        code = str(error)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        code = "INPUT_OR_PLAN_FAILED"
    except KeyboardInterrupt:
        code, exit_code = "INTERRUPTED", 130
    print(json.dumps(dict(status="ERROR", code=code, **_flags()), sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
