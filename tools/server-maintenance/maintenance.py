#!/usr/bin/env python3
"""Pure calendar, maintenance-plan, and readiness rules; no server control."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path
import stat
import sys


INPUT_LIMIT = 64 * 1024


class PlanError(ValueError):
    """Invalid or incomplete operator-supplied planning input."""


def integer(value: object, low: int, high: int) -> int:
    """Require an actual integer in the inclusive range."""
    if type(value) is not int or not low <= value <= high:
        raise PlanError("INVALID_INTEGER")
    return value


def first_weekday(year: int, month: int, weekday: int) -> date:
    """Return the first selected weekday in a month (Monday is zero)."""
    integer(year, 1, 9999)
    integer(month, 1, 12)
    integer(weekday, 0, 6)
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7)


def schedule_window(year: int, month: int, weekday: int, offset_days: int) -> dict:
    """Plan two dates without selecting a time zone or performing an action."""
    integer(year, 1, 9998)
    integer(offset_days, 1, 27)
    anchor = first_weekday(year, month, weekday)
    next_month = 1 if month == 12 else month + 1
    next_year = year + 1 if month == 12 else year
    next_anchor = first_weekday(next_year, next_month, weekday)
    followup = anchor + timedelta(days=offset_days)
    if followup >= next_anchor:
        raise PlanError("FOLLOWUP_OVERLAPS_NEXT_WINDOW")
    return {
        "anchor": anchor.isoformat(),
        "followup": followup.isoformat(),
        "next_anchor": next_anchor.isoformat(),
        "weekday": weekday,
        "time_of_day": "operator_selected",
        "timezone": "operator_selected",
        "execution_performed": False,
    }


def maintenance_plan(value: object) -> dict:
    """Return a conservative ordered plan from caller-supplied observations."""
    keys = {
        "action",
        "state",
        "players",
        "observation_age_seconds",
        "maximum_age_seconds",
        "cooldown_remaining_seconds",
        "previous_attempt",
        "target_verified",
        "backup_verified",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise PlanError("INVALID_REQUEST_FIELDS")

    action = value["action"]
    state = value["state"]
    previous = value["previous_attempt"]
    if any(type(item) is not str for item in (action, state, previous)):
        raise PlanError("INVALID_REQUEST_VALUE")
    if action not in {"start", "stop", "restart", "update", "backup"}:
        raise PlanError("INVALID_REQUEST_VALUE")
    if state not in {"running", "stopped", "unknown"}:
        raise PlanError("INVALID_REQUEST_VALUE")
    if previous not in {"none", "completed", "incomplete", "unknown"}:
        raise PlanError("INVALID_REQUEST_VALUE")

    for key in ("target_verified", "backup_verified"):
        if type(value[key]) is not bool:
            raise PlanError("BOOLEAN_REQUIRED")

    players = value["players"]
    age = value["observation_age_seconds"]
    if players is not None:
        integer(players, 0, 100_000)
    if age is not None:
        integer(age, 0, 86_400)
    maximum_age = integer(value["maximum_age_seconds"], 1, 3_600)
    cooldown = integer(value["cooldown_remaining_seconds"], 0, 86_400)

    def result(status: str, steps: tuple[str, ...] = ()) -> dict:
        return {
            "status": status,
            "action": action,
            "steps": list(steps),
            "execution_performed": False,
        }

    if previous in {"incomplete", "unknown"}:
        return result("REVIEW_PREVIOUS_ATTEMPT")
    if not value["target_verified"]:
        return result("TARGET_NOT_VERIFIED")
    if state == "unknown":
        return result("STATE_NOT_ESTABLISHED")
    if age is None or age > maximum_age:
        return result("OBSERVATION_STALE_OR_MISSING")
    if players is None:
        return result("PLAYER_COUNT_UNKNOWN")
    if state == "stopped" and players:
        return result("OBSERVATION_INCONSISTENT")
    if cooldown:
        return result("COOLDOWN_PENDING")
    if players:
        return result("PLAYERS_PRESENT")

    if action == "start":
        if state == "running":
            return result("NO_ACTION")
        return result(
            "PLAN_READY", ("start", "verify_new_instance", "verify_fresh_readiness")
        )
    if action == "stop":
        if state == "stopped":
            return result("NO_ACTION")
        return result(
            "PLAN_READY", ("notify", "request_save", "request_stop", "verify_stopped")
        )
    if action in {"backup", "update"} and state != "stopped":
        return result("STOP_REQUIRED")
    if action in {"restart", "update"} and not value["backup_verified"]:
        return result("VERIFIED_BACKUP_REQUIRED")
    if action == "backup":
        return result("PLAN_READY", ("snapshot_private_state", "verify_snapshot"))
    if action == "update":
        return result(
            "PLAN_READY",
            (
                "verify_backup_pin",
                "apply_reviewed_update",
                "verify_updated_files",
                "record_result",
            ),
        )

    if state == "running":
        steps = (
            "notify",
            "request_save",
            "request_stop",
            "verify_stopped",
            "refresh_backup",
            "verify_backup_pin",
            "start",
            "verify_new_instance",
            "verify_fresh_readiness",
        )
    else:
        steps = (
            "verify_backup_pin",
            "start",
            "verify_new_instance",
            "verify_fresh_readiness",
        )
    return result("PLAN_READY", steps)


def readiness_rule(value: object) -> dict:
    """Summarize caller-supplied readiness observations; do not probe services."""
    keys = {"target_verified", "new_instance", "fresh_log_markers", "probe_succeeded"}
    if not isinstance(value, dict) or set(value) != keys:
        raise PlanError("INVALID_READINESS_FIELDS")
    if any(type(value[key]) is not bool for key in keys):
        raise PlanError("INVALID_READINESS_FIELDS")
    missing = sorted(key for key in keys if not value[key])
    return {
        "status": "OBSERVATIONS_COMPLETE" if not missing else "NOT_ESTABLISHED",
        "missing": missing,
        "execution_performed": False,
    }


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject repeated keys instead of silently accepting the last value."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise PlanError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def load_request(path: str | Path) -> object:
    """Read one bounded JSON request without following a linked path."""
    selected = Path(path)
    if ".." in selected.parts:
        raise PlanError("PARENT_TRAVERSAL")
    selected = selected.absolute()
    for item in [*reversed(selected.parents), selected]:
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise PlanError("LINKED_INPUT")

    before = selected.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > INPUT_LIMIT:
        raise PlanError("INPUT_LIMIT")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(os.open(selected, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(before):
            raise PlanError("INPUT_CHANGED")
        data = stream.read(INPUT_LIMIT + 1)
        if len(data) > INPUT_LIMIT or _identity(os.fstat(stream.fileno())) != _identity(
            before
        ):
            raise PlanError("INPUT_CHANGED")
    if _identity(selected.lstat()) != _identity(before):
        raise PlanError("INPUT_CHANGED")
    return json.loads(
        data.decode("utf-8-sig"),
        object_pairs_hook=unique_object,
        parse_constant=lambda _: (_ for _ in ()).throw(PlanError("NONSTANDARD_JSON")),
    )


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


class Parser(argparse.ArgumentParser):
    """Use fixed errors so input paths do not appear in console diagnostics."""

    def error(self, message: str) -> None:
        raise PlanError("INVALID_ARGUMENTS")


def main(argv: list[str] | None = None) -> int:
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    calendar = commands.add_parser("calendar")
    calendar.add_argument("--year", required=True, type=int)
    calendar.add_argument("--month", required=True, type=int)
    calendar.add_argument(
        "--weekday", required=True, type=int, help="Monday=0 through Sunday=6"
    )
    calendar.add_argument("--offset-days", required=True, type=int)
    for name in ("plan", "readiness"):
        command = commands.add_parser(name)
        command.add_argument("--input", required=True)

    try:
        args = parser.parse_args(argv)
        if args.command == "calendar":
            result = schedule_window(
                args.year, args.month, args.weekday, args.offset_days
            )
        else:
            request = load_request(args.input)
            result = (
                maintenance_plan(request)
                if args.command == "plan"
                else readiness_rule(request)
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, UnicodeError, TypeError, KeyError, RecursionError):
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "code": "PLAN_INPUT_INVALID",
                    "execution_performed": False,
                }
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
