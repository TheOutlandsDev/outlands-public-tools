#!/usr/bin/env python3
"""Check declared assessment record relationships without testing targets."""

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
MAX_COLLECTION = 128
MAX_RECORDS = 256
MAX_REVISION = 1000000000
ID = re.compile(r"[a-z][a-z0-9_-]{0,39}")
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit for prefix in ("com", "lpt") for digit in "123456789¹²³"
}


class ContractError(ValueError):
    """Only a fixed public code; never record content or a native exception."""


def _fail(code):
    raise ContractError(code) from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _token(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        _fail("RECORD_TOKEN_INVALID")
    return value


def _record_id(row, seen):
    identifier = _token(row["id"])
    if identifier in seen:
        _fail("DUPLICATE_RECORD_ID")
    seen.add(identifier)


def parse_records(data):
    collections = ("submissions", "findings", "retests")
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", *collections}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or any(not isinstance(data[name], list) for name in collections)
    ):
        _fail("RECORDS_SCHEMA_INVALID")
    if (
        not data["submissions"]
        or any(len(data[name]) > MAX_COLLECTION for name in collections)
        or sum(len(data[name]) for name in collections) > MAX_RECORDS
    ):
        _fail("RECORD_COUNT_INVALID")
    seen = set()
    revisions = set()
    submissions = []
    for row in data["submissions"]:
        if not isinstance(row, dict) or set(row) != {"id", "series_id", "revision"}:
            _fail("SUBMISSION_SCHEMA_INVALID")
        _record_id(row, seen)
        _token(row["series_id"])
        if type(row["revision"]) is not int or not 1 <= row["revision"] <= MAX_REVISION:
            _fail("REVISION_INVALID")
        revision = row["series_id"], row["revision"]
        if revision in revisions:
            _fail("DUPLICATE_SERIES_REVISION")
        revisions.add(revision)
        submissions.append(dict(row))
    findings = []
    for row in data["findings"]:
        if not isinstance(row, dict) or set(row) != {
            "id",
            "submission_id",
            "state",
            "selected_retest_id",
        }:
            _fail("FINDING_SCHEMA_INVALID")
        _record_id(row, seen)
        _token(row["submission_id"])
        if row["state"] not in ("open", "retest_pending", "closure_claimed"):
            _fail("FINDING_STATE_INVALID")
        if row["selected_retest_id"] is not None:
            _token(row["selected_retest_id"])
        findings.append(dict(row))
    pairs = set()
    retests = []
    for row in data["retests"]:
        if not isinstance(row, dict) or set(row) != {
            "id",
            "finding_id",
            "submission_id",
            "outcome",
        }:
            _fail("RETEST_SCHEMA_INVALID")
        _record_id(row, seen)
        _token(row["finding_id"])
        _token(row["submission_id"])
        if row["outcome"] not in (
            "not_run",
            "still_present",
            "not_observed",
            "inconclusive",
        ):
            _fail("RETEST_OUTCOME_INVALID")
        pair = row["finding_id"], row["submission_id"]
        if pair in pairs:
            _fail("DUPLICATE_RETEST_PAIR")
        pairs.add(pair)
        retests.append(dict(row))
    return dict(
        schema_version=1, submissions=submissions, findings=findings, retests=retests
    )


def _retest_result(row, submissions, findings):
    finding = findings.get(row["finding_id"])
    if finding is None:
        return "BLOCKED", "FINDING_NOT_DECLARED"
    original = submissions.get(finding["submission_id"])
    if original is None:
        return "BLOCKED", "ORIGINAL_SUBMISSION_NOT_DECLARED"
    replacement = submissions.get(row["submission_id"])
    if replacement is None:
        return "BLOCKED", "REPLACEMENT_SUBMISSION_NOT_DECLARED"
    if original["series_id"] != replacement["series_id"]:
        return "FAIL", "SERIES_MISMATCH"
    if replacement["revision"] <= original["revision"]:
        return "FAIL", "REPLACEMENT_NOT_LATER"
    return "PASS", "RETEST_RELATIONSHIPS_CONSISTENT"


def _finding_result(row, submissions, retests, retest_states, highest):
    original = submissions.get(row["submission_id"])
    if original is None:
        return "BLOCKED", "ORIGINAL_SUBMISSION_NOT_DECLARED"
    selected_id = row["selected_retest_id"]
    if row["state"] == "open":
        return (
            ("PASS", "OPEN_RECORD_CONSISTENT")
            if selected_id is None
            else ("FAIL", "OPEN_HAS_SELECTED_RETEST")
        )
    if selected_id is None:
        return "BLOCKED", "SELECTED_RETEST_NOT_SUPPLIED"
    selected = retests.get(selected_id)
    if selected is None:
        return "BLOCKED", "SELECTED_RETEST_NOT_DECLARED"
    if selected["finding_id"] != row["id"]:
        return "FAIL", "SELECTED_RETEST_FINDING_MISMATCH"
    if retest_states[selected_id][0] != "PASS":
        return "BLOCKED", "SELECTED_RETEST_INVALID"
    replacement = submissions[selected["submission_id"]]
    if replacement["revision"] != highest[original["series_id"]]:
        return "FAIL", "SELECTED_SUBMISSION_NOT_LATEST_DECLARED"
    if row["state"] == "retest_pending":
        return (
            ("PASS", "PENDING_RECORD_CONSISTENT")
            if selected["outcome"] == "not_run"
            else ("FAIL", "PENDING_OUTCOME_INCONSISTENT")
        )
    return (
        ("PASS", "CLOSURE_CLAIM_CONSISTENT")
        if selected["outcome"] == "not_observed"
        else ("FAIL", "CLOSURE_OUTCOME_NOT_SUPPORTING")
    )


def check_records(data):
    """Check declarations only; outcomes and actual testing remain unverified."""
    data = parse_records(data)
    submissions = {row["id"]: row for row in data["submissions"]}
    findings = {row["id"]: row for row in data["findings"]}
    retests = {row["id"]: row for row in data["retests"]}
    highest = {}
    for row in data["submissions"]:
        highest[row["series_id"]] = max(
            highest.get(row["series_id"], 0), row["revision"]
        )
    # Finding base links inform retests; final finding states depend on retests.
    # Evaluating those phases avoids treating the intentional cross-reference
    # as a recursive graph or allowing a broken dependency to pass closure.
    retest_states = {
        row["id"]: _retest_result(row, submissions, findings) for row in data["retests"]
    }
    finding_states = {
        row["id"]: _finding_result(row, submissions, retests, retest_states, highest)
        for row in data["findings"]
    }
    checks = [
        dict(
            id=row["id"],
            kind="submission",
            status="PASS",
            evidence="SUBMISSION_DECLARATION_VALID",
        )
        for row in data["submissions"]
    ]
    for kind, collection, states in (
        ("finding", data["findings"], finding_states),
        ("retest", data["retests"], retest_states),
    ):
        for row in collection:
            status, evidence = states[row["id"]]
            checks.append(
                dict(id=row["id"], kind=kind, status=status, evidence=evidence)
            )
    counts = Counter(row["status"] for row in checks)
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED"
        if counts["FAIL"] or counts["BLOCKED"]
        else "DECLARED_RECORDS_CONSISTENT",
        scope="DECLARED_ASSESSMENT_RECORDS_ONLY",
        execution_performed=False,
        network_probed=False,
        records_modified=False,
        authorization_verified=False,
        isolation_verified=False,
        outcomes_verified=False,
        counts=dict(
            passed=counts["PASS"],
            failed=counts["FAIL"],
            blocked=counts["BLOCKED"],
            submissions=len(submissions),
            findings=len(findings),
            retests=len(retests),
        ),
        checks=checks,
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
        _fail("INPUT_OR_RECORDS_FAILED")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        _fail("ARGUMENTS_INVALID")


def main(argv=None):
    parser = _Parser(
        prog="assessment-record-checker", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--records", required=True)
    exit_code = 2
    try:
        args = parser.parse_args(argv)
        result = check_records(read_input_json(args.records))
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0 if result["status"] == "DECLARED_RECORDS_CONSISTENT" else 1
    except ContractError as error:
        code = str(error)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        code = "INPUT_OR_RECORDS_FAILED"
    except KeyboardInterrupt:
        code, exit_code = "INTERRUPTED", 130
    print(
        json.dumps(
            dict(
                status="ERROR",
                code=code,
                execution_performed=False,
                network_probed=False,
                records_modified=False,
                authorization_verified=False,
                isolation_verified=False,
                outcomes_verified=False,
            ),
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
