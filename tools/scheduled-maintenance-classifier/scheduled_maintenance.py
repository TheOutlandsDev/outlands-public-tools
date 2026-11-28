"""Classify scheduled maintenance from a saved runtime and task observation."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 2_000_000
INPUT_FIELDS = {"observed_at", "expected_state", "observed_runtime_issues", "tasks"}


class EvidenceInputError(ValueError):
    """A saved maintenance observation violates the input contract."""


def _maintenance_controller(task: dict[str, Any], observed_at: datetime) -> bool:
    name = str(task.get("name", "")).casefold()
    if not task.get("enabled"):
        return False
    if str(task.get("state", "")).casefold() != "running":
        return False
    if not any(token in name for token in ("restart", "rollover", "wipe")):
        return False
    try:
        started = datetime.fromisoformat(str(task.get("last_run", "")))
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        age = observed_at - started.astimezone(UTC)
    except (TypeError, ValueError, OverflowError):
        return False
    return timedelta(minutes=-1) <= age <= timedelta(minutes=45)


def classify_maintenance(
    observed_at: datetime, expected_state: str,
    observed_runtime_issues: list[str], tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply the original runtime and maintenance decision to saved evidence."""
    if not isinstance(observed_at, datetime) or observed_at.utcoffset() is None:
        raise EvidenceInputError("observed_at must be an ISO 8601 timestamp with a UTC offset.")
    try:
        observed_at = observed_at.astimezone(UTC)
    except (ValueError, OverflowError) as error:
        raise EvidenceInputError("observed_at must be an ISO 8601 timestamp with a UTC offset.") from error
    if not isinstance(expected_state, str) or expected_state.casefold() not in {"online", "planned_off"}:
        raise EvidenceInputError("expected_state must be online or planned_off.")
    expected_state = expected_state.casefold()
    if not isinstance(observed_runtime_issues, list) or any(
        not isinstance(issue, str) or not issue.strip() for issue in observed_runtime_issues
    ):
        raise EvidenceInputError("observed_runtime_issues must be an array of nonempty strings.")
    observed_runtime_issues = list(observed_runtime_issues)
    if not isinstance(tasks, list):
        raise EvidenceInputError("tasks must be an array of task objects.")
    names: set[str] = set()
    for task in tasks:
        name = task.get("name") if isinstance(task, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise EvidenceInputError("Each task needs a nonempty name.")
        canonical = name.casefold()
        if canonical in names:
            raise EvidenceInputError("Duplicate task name.")
        names.add(canonical)
        if "enabled" in task and type(task["enabled"]) is not bool:
            raise EvidenceInputError("Task enabled must be a JSON boolean.")
        for field in ("state", "last_run"):
            value = task.get(field)
            if value is not None and not isinstance(value, str):
                raise EvidenceInputError(f"Task {field} must be a string or null.")

    observed_runtime_status = (
        "down" if observed_runtime_issues else "online"
    )
    maintenance_tasks = [
        str(task.get("name", "scheduled controller"))
        for task in tasks
        if _maintenance_controller(task, observed_at)
    ]
    maintenance_issues: list[str] = []
    planned_off = expected_state == "planned_off"
    if planned_off and observed_runtime_status == "down":
        runtime_status = "planned_off"
        runtime_issues: list[str] = []
        expectation_issues: list[str] = []
    elif planned_off:
        runtime_status = "online"
        runtime_issues = []
        expectation_issues = [
            "runtime unexpectedly online while configured planned off"
        ]
    elif maintenance_tasks and observed_runtime_status == "down":
        runtime_status = "maintenance"
        runtime_issues = []
        expectation_issues = []
        maintenance_issues = [
            f"scheduled maintenance: {', '.join(maintenance_tasks)}"
        ]
    else:
        runtime_status = observed_runtime_status
        runtime_issues = observed_runtime_issues
        expectation_issues = []

    issues = runtime_issues + expectation_issues + maintenance_issues
    if runtime_status in {"down", "planned_off"}:
        status = runtime_status
    else:
        status = "warning" if issues else "healthy"

    return {
        "status": status,
        "observed_at": observed_at.isoformat(),
        "observed_runtime_status": observed_runtime_status,
        "expected_state": expected_state,
        "runtime_status": runtime_status,
        "maintenance_in_progress": runtime_status == "maintenance",
        "maintenance_tasks": maintenance_tasks,
        "runtime_issues": runtime_issues,
        "issues": issues,
    }


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, value in pairs:
        if key in values:
            raise EvidenceInputError("Duplicate JSON key.")
        values[key] = value
    return values


def _reject_nonfinite(_: str) -> None:
    raise EvidenceInputError("Use standard JSON numbers.")


def _read_evidence(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceInputError("Evidence input must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise EvidenceInputError("Evidence input exceeds 2,000,000 bytes.")
    try:
        value = json.loads(
            raw.decode("utf-8-sig"), object_pairs_hook=_unique_fields, parse_constant=_reject_nonfinite,
        )
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except EvidenceInputError:
        raise
    except (ValueError, RecursionError) as error:
        raise EvidenceInputError("Invalid UTF-8 JSON evidence.") from error
    if not isinstance(value, dict) or value.keys() != INPUT_FIELDS:
        raise EvidenceInputError("Evidence must contain observed_at, expected_state, observed_runtime_issues, and tasks.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 maintenance observation")
    args = parser.parse_args()
    try:
        saved = _read_evidence(args.input)
        try:
            observed_at = datetime.fromisoformat(saved["observed_at"])
        except (TypeError, ValueError) as error:
            raise EvidenceInputError("observed_at must be an ISO 8601 timestamp with a UTC offset.") from error
        output = classify_maintenance(
            observed_at, saved["expected_state"], saved["observed_runtime_issues"], saved["tasks"],
        )
    except EvidenceInputError as error:
        parser.exit(2, f"{error}\n")
    except OSError:
        parser.exit(2, "Could not read the saved evidence.\n")
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
