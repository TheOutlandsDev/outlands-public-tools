"""Classify one service from saved remote probe evidence."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any, TextIO


_MAX_BYTES = 256 * 1024
_INPUT_FIELDS = {"service_id", "as_of", "maximum_age_seconds", "evidence"}
_REPORTED_STATES = {
    "reachable": "reachable",
    "healthy": "reachable",
    "passed": "reachable",
    "unreachable": "unreachable",
    "failed": "unreachable",
    "down": "unreachable",
}


class ReachabilityEvidenceError(ValueError):
    """An invalid saved check, with a fixed diagnostic."""


def _evaluation_time(value: object) -> datetime:
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if isinstance(value, datetime) and value.utcoffset() is not None:
            return value.astimezone(UTC)
    except (ValueError, OverflowError):
        pass
    raise ReachabilityEvidenceError("Evaluation time must be a timezone-aware ISO timestamp.")


def _fresh(
    payload: dict[str, Any],
    maximum_age_seconds: float,
    *,
    as_of: datetime,
) -> tuple[bool, float | None]:
    timestamp = payload.get("generated")
    if not isinstance(timestamp, str):
        return False, None
    try:
        generated = datetime.fromisoformat(timestamp)
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=UTC)
        age = (as_of - generated.astimezone(UTC)).total_seconds()
    except (ValueError, OverflowError):
        return False, None
    return -5.0 <= age <= maximum_age_seconds, age


def _service_entries(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ReachabilityEvidenceError("Saved evidence must be an object.")
    entries = payload.get("services", [])
    if not isinstance(entries, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not item["id"].strip()
        for item in entries
    ):
        raise ReachabilityEvidenceError("Saved services must be a list of records with IDs.")
    return entries


def _reported_state(status: object) -> str:
    return _REPORTED_STATES.get(status.casefold(), "pending") if isinstance(status, str) else "pending"


def _external_state(
    service_id: str,
    payload: dict[str, Any],
    maximum_age_seconds: float,
    *,
    as_of: datetime | str,
) -> tuple[str, str]:
    if not isinstance(service_id, str) or not service_id.strip():
        raise ReachabilityEvidenceError("Expected service ID must be nonempty text.")
    if (
        type(maximum_age_seconds) not in (int, float)
        or maximum_age_seconds < 0
        or (type(maximum_age_seconds) is float and not math.isfinite(maximum_age_seconds))
    ):
        raise ReachabilityEvidenceError("Maximum evidence age must be a finite nonnegative number.")
    evaluation_time = _evaluation_time(as_of)
    entries = _service_entries(payload)
    fresh, age = _fresh(payload, maximum_age_seconds, as_of=evaluation_time)
    if not fresh:
        if age is None:
            return "pending", "no remote probe evidence"
        return "stale", "remote probe evidence is outside the freshness window"

    states = {_reported_state(item.get("status")) for item in entries if item["id"] == service_id}
    if not states:
        return "pending", "no saved result for the service"
    if len(states) != 1:
        return "pending", "conflicting remote probe results"
    state = states.pop()
    if state == "pending":
        return state, "remote probe status is unrecognized or pending"
    return state, f"fresh remote probe evidence reports {state}"


def _ordinary_file(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ReachabilityEvidenceError("Saved input contains duplicate JSON fields.")
    return result


def _reject_constant(value: str) -> object:
    raise ReachabilityEvidenceError("Saved input contains an invalid JSON number.")


def _read_input(path: Path) -> dict[str, Any]:
    try:
        selected = path.lstat()
        if not _ordinary_file(selected):
            raise ReachabilityEvidenceError("Saved input must be an ordinary file.")
        if selected.st_size > _MAX_BYTES:
            raise ReachabilityEvidenceError("Saved input exceeds the 256 KiB limit.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _ordinary_file(opened) or not os.path.samestat(selected, opened):
                raise ReachabilityEvidenceError("Saved input changed while opening.")
            payload = stream.read(_MAX_BYTES + 1)
    except ReachabilityEvidenceError:
        raise
    except (OSError, ValueError):
        raise ReachabilityEvidenceError("Unable to read the saved input.") from None
    if len(payload) > _MAX_BYTES:
        raise ReachabilityEvidenceError("Saved input exceeds the 256 KiB limit.")

    try:
        raw = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_fields, parse_constant=_reject_constant)
    except ReachabilityEvidenceError:
        raise
    except (ValueError, RecursionError):
        raise ReachabilityEvidenceError("Saved input must contain valid UTF-8 JSON.") from None
    if not isinstance(raw, dict) or raw.keys() != _INPUT_FIELDS:
        raise ReachabilityEvidenceError("Saved input has an invalid shape.")
    return raw


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ReachabilityEvidenceError("Invalid arguments. Use --help for usage.")


def main(
    argv: list[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    parser = _ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 evaluation and evidence JSON.")
    try:
        args = parser.parse_args(argv)
        saved = _read_input(args.input)
        status, reason = _external_state(
            saved["service_id"],
            saved["evidence"],
            saved["maximum_age_seconds"],
            as_of=saved["as_of"],
        )
    except ReachabilityEvidenceError as error:
        errors.write(f"ERROR: {error}\n")
        return 2

    json.dump({"status": status, "reason": reason}, output)
    output.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
