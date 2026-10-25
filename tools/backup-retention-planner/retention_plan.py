#!/usr/bin/env python3
"""Plan declared independent snapshot retention without scanning or deleting."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import stat
import sys

VERSION = "0.1.0"
MAX_INPUT_BYTES = 65536
MAX_SNAPSHOTS = 256
MAX_KEEP_DAYS = 36500
ID = re.compile(r"[a-z][a-z0-9_-]{0,39}")
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit for prefix in ("com", "lpt") for digit in "123456789¹²³"
}


class ContractError(ValueError):
    """Only a fixed public code; never supplied metadata or a native exception."""


def _fail(code):
    raise ContractError(code) from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _timestamp(value):
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        _fail("TIMESTAMP_INVALID")
    try:
        # Exact Z-only syntax above makes both naive values explicit UTC.
        return datetime.fromisoformat(value[:-1])
    except ValueError:
        _fail("TIMESTAMP_INVALID")


def parse_plan(data):
    if (
        not isinstance(data, dict)
        or set(data)
        != {"schema_version", "snapshot_kind", "as_of", "policy", "snapshots"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["snapshots"], list)
        or not 0 < len(data["snapshots"]) <= MAX_SNAPSHOTS
    ):
        _fail("PLAN_SCHEMA_INVALID")
    if data["snapshot_kind"] != "independent_full":
        _fail("INDEPENDENT_FULL_DECLARATION_REQUIRED")
    _timestamp(data["as_of"])
    policy = data["policy"]
    if not isinstance(policy, dict) or set(policy) != {"keep_latest", "keep_days"}:
        _fail("POLICY_SCHEMA_INVALID")
    if (
        type(policy["keep_latest"]) is not int
        or not 1 <= policy["keep_latest"] <= MAX_SNAPSHOTS
        or type(policy["keep_days"]) is not int
        or not 0 <= policy["keep_days"] <= MAX_KEEP_DAYS
    ):
        _fail("POLICY_VALUE_INVALID")
    ids = set()
    snapshots = []
    for row in data["snapshots"]:
        if not isinstance(row, dict) or set(row) != {"id", "created_at", "pinned"}:
            _fail("SNAPSHOT_SCHEMA_INVALID")
        identifier = row["id"]
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            _fail("SNAPSHOT_ID_INVALID")
        if identifier in ids:
            _fail("DUPLICATE_SNAPSHOT_ID")
        ids.add(identifier)
        _timestamp(row["created_at"])
        if type(row["pinned"]) is not bool:
            _fail("PIN_FLAG_INVALID")
        snapshots.append(dict(row))
    return dict(
        schema_version=1,
        snapshot_kind="independent_full",
        as_of=data["as_of"],
        policy=dict(policy),
        snapshots=snapshots,
    )


def plan_retention(data):
    """Return advisory ID decisions using supplied metadata, never a local clock."""
    plan = parse_plan(data)
    as_of = _timestamp(plan["as_of"])
    policy = plan["policy"]
    times = {row["id"]: _timestamp(row["created_at"]) for row in plan["snapshots"]}
    eligible = sorted(
        (value for value in times.values() if value <= as_of), reverse=True
    )
    cutoff = (
        eligible[min(policy["keep_latest"], len(eligible)) - 1] if eligible else None
    )
    latest = {
        identifier
        for identifier, value in times.items()
        if cutoff is not None and cutoff <= value <= as_of
    }
    results = []
    future_count = 0
    for row in plan["snapshots"]:
        created = times[row["id"]]
        future = created > as_of
        reasons = []
        if row["pinned"]:
            reasons.append("PINNED")
        if future:
            future_count += 1
            reasons.append("FUTURE_TIMESTAMP_UNVERIFIED")
        if row["id"] in latest:
            reasons.append("LATEST_COUNT")
        if not future and policy["keep_days"]:
            age = as_of - created
            seconds = age.days * 86400 + age.seconds
            if seconds <= policy["keep_days"] * 86400:
                reasons.append("WITHIN_AGE_WINDOW")
        decision = "KEEP" if reasons else "REVIEW"
        results.append(
            dict(
                id=row["id"],
                decision=decision,
                reasons=reasons or ["OUTSIDE_DECLARED_PROTECTIONS"],
            )
        )
    issues = []
    if future_count:
        issues.append("FUTURE_TIMESTAMPS_PRESENT")
    if len(eligible) < policy["keep_latest"]:
        issues.append("LATEST_COUNT_NOT_MET")
    review = sum(row["decision"] == "REVIEW" for row in results)
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED" if review or issues else "KEEP_ONLY_PLAN",
        scope="DECLARED_INDEPENDENT_FULL_METADATA_ONLY",
        filesystem_scanned=False,
        backup_contents_verified=False,
        metadata_verified=False,
        deletion_performed=False,
        deletion_authorized=False,
        network_probed=False,
        counts=dict(
            keep=len(results) - review,
            review=review,
            future=future_count,
            nonfuture=len(eligible),
            latest_protected=len(latest),
        ),
        snapshots=results,
        issues=issues,
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
        prog="backup-retention-planner", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--plan", required=True)
    exit_code = 2
    try:
        args = parser.parse_args(argv)
        result = plan_retention(read_input_json(args.plan))
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0 if result["status"] == "KEEP_ONLY_PLAN" else 1
    except ContractError as error:
        code = str(error)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        code = "INPUT_OR_PLAN_FAILED"
    except KeyboardInterrupt:
        code, exit_code = "INTERRUPTED", 130
    print(
        json.dumps(
            dict(
                status="ERROR",
                code=code,
                filesystem_scanned=False,
                backup_contents_verified=False,
                metadata_verified=False,
                deletion_performed=False,
                deletion_authorized=False,
                network_probed=False,
            ),
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
