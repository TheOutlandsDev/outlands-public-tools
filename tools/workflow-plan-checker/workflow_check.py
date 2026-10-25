#!/usr/bin/env python3
"""Check declared workflow dependencies and states without executing tasks."""

from __future__ import annotations

import argparse
import heapq
import json
import os
from pathlib import Path
import re
import stat
import sys

VERSION = "0.1.0"
MAX_INPUT_BYTES = 65536
MAX_TASKS = 128
MAX_REQUIRES = 32
ID = re.compile(r"[a-z][a-z0-9_-]{0,39}")
STATES = ("pending", "in_progress", "completed")
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit
    for prefix in ("com", "lpt")
    for digit in "123456789\u00b9\u00b2\u00b3"
}
ISSUE_ORDER = (
    "PREREQUISITE_NOT_FOUND",
    "SELF_DEPENDENCY",
    "DEPENDENCY_CYCLE",
    "COMPLETED_PREREQUISITES_UNSATISFIED",
    "ACTIVE_PREREQUISITES_UNSATISFIED",
)


class ContractError(ValueError):
    """A fixed error code without selected input values or native details."""


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
    """Validate the exact JSON-shaped contract, without coercion or repair."""
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "tasks"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["tasks"], list)
        or not 1 <= len(data["tasks"]) <= MAX_TASKS
    ):
        _fail("PLAN_SCHEMA_INVALID")
    identifiers, tasks = set(), []
    for row in data["tasks"]:
        if not isinstance(row, dict) or set(row) != {"id", "requires", "state"}:
            _fail("TASK_SCHEMA_INVALID")
        _identifier(row["id"], "TASK_ID_INVALID")
        if row["id"] in identifiers:
            _fail("DUPLICATE_TASK_ID")
        identifiers.add(row["id"])
        if row["state"] not in STATES:
            _fail("TASK_STATE_INVALID")
        requires = row["requires"]
        if not isinstance(requires, list) or len(requires) > MAX_REQUIRES:
            _fail("PREREQUISITES_INVALID")
        seen = set()
        for dependency in requires:
            _identifier(dependency, "PREREQUISITE_ID_INVALID")
            if dependency in seen:
                _fail("DUPLICATE_PREREQUISITE_ID")
            seen.add(dependency)
        tasks.append(dict(id=row["id"], state=row["state"], requires=list(requires)))
    return dict(schema_version=1, tasks=tasks)


def _cycle_members(rows):
    """Bounded bitset transitive closure; mark cycle members, not descendants."""
    identifiers = sorted(rows)
    positions = {key: index for index, key in enumerate(identifiers)}
    reach = [
        sum(
            1 << positions[dependency]
            for dependency in rows[key]["requires"]
            if dependency in rows
        )
        for key in identifiers
    ]
    for middle in range(len(identifiers)):
        bit = 1 << middle
        for start in range(len(identifiers)):
            if reach[start] & bit:
                reach[start] |= reach[middle]
    return {key for index, key in enumerate(identifiers) if reach[index] & (1 << index)}


def _topological_order(rows):
    """Lexicographically smallest topological order of an already valid graph."""
    incoming = {key: len(row["requires"]) for key, row in rows.items()}
    children = {key: [] for key in rows}
    for key, row in rows.items():
        for dependency in row["requires"]:
            children[dependency].append(key)
    ready = [key for key in rows if incoming[key] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        key = heapq.heappop(ready)
        order.append(key)
        for child in children[key]:
            incoming[child] -= 1
            if incoming[child] == 0:
                heapq.heappush(ready, child)
    if len(order) != len(rows):
        _fail("DEPENDENCY_ANALYSIS_FAILED")
    return order


def _flags():
    return dict(
        filesystem_scanned=False,
        states_verified=False,
        execution_performed=False,
        execution_authorized=False,
        commands_generated=False,
        plan_changed=False,
        network_probed=False,
    )


def check_plan(data):
    """Return declared consistency only; any issue withholds all next-step lists."""
    plan = parse_plan(data)
    rows = {row["id"]: row for row in plan["tasks"]}
    cycles, problems = _cycle_members(rows), {}
    for key in sorted(rows):
        row = rows[key]
        issues = []
        if any(dependency not in rows for dependency in row["requires"]):
            issues.append("PREREQUISITE_NOT_FOUND")
        if key in row["requires"]:
            issues.append("SELF_DEPENDENCY")
        if key in cycles:
            issues.append("DEPENDENCY_CYCLE")
        prerequisites_completed = all(
            dependency in rows and rows[dependency]["state"] == "completed"
            for dependency in row["requires"]
        )
        if row["state"] == "completed" and not prerequisites_completed:
            issues.append("COMPLETED_PREREQUISITES_UNSATISFIED")
        if row["state"] == "in_progress" and not prerequisites_completed:
            issues.append("ACTIVE_PREREQUISITES_UNSATISFIED")
        problems[key] = issues
    review = any(problems.values())
    order, eligible, waiting = [], [], []
    if not review:
        order = _topological_order(rows)
        for key in sorted(rows):
            row = rows[key]
            if row["state"] == "pending":
                if all(
                    rows[dependency]["state"] == "completed"
                    for dependency in row["requires"]
                ):
                    eligible.append(key)
                else:
                    waiting.append(key)
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED" if review else "DECLARED_PLAN_CONSISTENT",
        scope="DECLARED_TASK_DEPENDENCIES_AND_STATES_ONLY",
        **_flags(),
        counts=dict(
            tasks=len(rows),
            dependency_edges=sum(len(row["requires"]) for row in rows.values()),
            pending=sum(row["state"] == "pending" for row in rows.values()),
            in_progress=sum(row["state"] == "in_progress" for row in rows.values()),
            completed=sum(row["state"] == "completed" for row in rows.values()),
            tasks_with_issues=sum(bool(issues) for issues in problems.values()),
            cycle_members=len(cycles),
        ),
        tasks=[dict(id=key, issues=problems[key]) for key in sorted(rows)],
        declared_order=order,
        eligible_next_ids=eligible,
        waiting_ids=waiting,
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
        prog="workflow-plan-checker", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--plan", required=True)
    exit_code = 2
    try:
        args = parser.parse_args(argv)
        result = check_plan(read_input_json(args.plan))
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0 if result["status"] == "DECLARED_PLAN_CONSISTENT" else 1
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
