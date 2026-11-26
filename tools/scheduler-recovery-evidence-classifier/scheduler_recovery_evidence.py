"""Classify saved scheduler recovery evidence without inspecting live tasks."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 2_000_000
RUNTIME_STATES = {"online", "down", "maintenance", "planned_off"}
INPUT_FIELDS = {"runtime_status", "state_healthy", "expected_tasks", "tasks"}


class EvidenceInputError(ValueError):
    """A saved scheduler record violates the input contract."""


def _task_healthy(task: dict[str, Any]) -> bool:
    if not task.get("enabled"):
        return False
    if str(task.get("state", "")).casefold() == "running":
        return True
    return str(task.get("last_result", "")).upper() in {
        "0X00000000",
        "0X00041300",
        "0X00041301",
        "0X00041303",  # Registered and not yet run.
    }


def _task_last_run(task: dict[str, Any]) -> datetime | None:
    value = str(task.get("last_run") or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    try:
        return parsed.astimezone(UTC)
    except OverflowError:
        return None


def _validate_evidence(
    runtime_status: str, state_healthy: bool | None, expected_tasks: list[str],
    observed_tasks: list[dict[str, Any]],
) -> None:
    if not isinstance(runtime_status, str) or runtime_status not in RUNTIME_STATES:
        raise EvidenceInputError("Unsupported runtime status.")
    if state_healthy is not None and type(state_healthy) is not bool:
        raise EvidenceInputError("state_healthy must be a JSON boolean or null.")
    if not isinstance(expected_tasks, list) or any(
        not isinstance(name, str) or not name.strip() for name in expected_tasks
    ):
        raise EvidenceInputError("expected_tasks must be an array of nonempty names.")
    if len({name.casefold() for name in expected_tasks}) != len(expected_tasks):
        raise EvidenceInputError("Duplicate expected task name.")
    if not isinstance(observed_tasks, list):
        raise EvidenceInputError("tasks must be an array of task objects.")
    names: set[str] = set()
    for task in observed_tasks:
        name = task.get("name") if isinstance(task, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise EvidenceInputError("Each observed task needs a nonempty name.")
        canonical = name.casefold()
        if canonical in names:
            raise EvidenceInputError("Duplicate observed task name.")
        names.add(canonical)
        if "enabled" in task and type(task["enabled"]) is not bool:
            raise EvidenceInputError("Task enabled must be a JSON boolean.")
        for key in ("state", "last_run", "next_run", "last_result"):
            value = task.get(key)
            if value is not None and not isinstance(value, str) and not (
                key == "last_result" and type(value) is int
            ):
                raise EvidenceInputError(f"Invalid task {key} value.")


def classify_recovery(
    runtime_status: str, state_healthy: bool | None, expected_tasks: list[str],
    observed_tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate observed scheduler evidence for one saved program profile."""
    _validate_evidence(runtime_status, state_healthy, expected_tasks, observed_tasks)
    tasks_by_name = {
        str(task.get("name", "")).casefold(): task for task in observed_tasks
    }
    tasks: list[dict[str, Any]] = []
    task_issues: list[str] = []
    for task_name in expected_tasks:
        task = tasks_by_name.get(task_name.casefold())
        if task is None:
            task_issues.append(f"{task_name}: not installed")
            tasks.append({"name": task_name, "installed": False})
            continue
        healthy = _task_healthy(task)
        tasks.append(
            {
                "name": task_name,
                "installed": True,
                "enabled": task.get("enabled"),
                "state": task.get("state"),
                "last_run": task.get("last_run"),
                "last_result": task.get("last_result"),
                "next_run": task.get("next_run"),
                "healthy": healthy,
            }
        )
        if not healthy:
            task_issues.append(
                f"{task_name}: state={task.get('state')} "
                f"result={task.get('last_result')}"
            )

    automation_notices: list[str] = []
    if runtime_status == "online" and state_healthy is True:
        successful_runs = [
            (run_time, str(task.get("name") or "scheduled task"))
            for task in tasks
            if task.get("installed")
            and task.get("healthy")
            and (run_time := _task_last_run(task)) is not None
        ]
        for task in tasks:
            task_name = str(task.get("name") or "")
            if (
                not task.get("installed")
                or task.get("healthy")
                or "recoveratlogon" not in task_name.casefold()
            ):
                continue
            failed_at = _task_last_run(task)
            if failed_at is None:
                continue
            newer_runs = [item for item in successful_runs if item[0] > failed_at]
            if not newer_runs:
                continue
            succeeded_at, succeeded_name = max(newer_runs, key=lambda item: item[0])
            issue = (
                f"{task_name}: state={task.get('state')} "
                f"result={task.get('last_result')}"
            )
            if issue not in task_issues:
                continue
            task_issues.remove(issue)
            automation_notices.append(
                "scheduler advisory: "
                f"{task_name} last result={task.get('last_result')} at "
                f"{failed_at.isoformat(timespec='seconds')} was superseded by "
                f"{succeeded_name} at {succeeded_at.isoformat(timespec='seconds')}; "
                "runtime and ready-state are healthy"
            )

    automation_issues = [f"scheduler: {issue}" for issue in task_issues]
    if automation_issues:
        automation_status = "attention"
    elif automation_notices:
        automation_status = "advisory"
    else:
        automation_status = "ready" if expected_tasks else "not configured"

    if runtime_status == "down":
        status = "down"
    elif runtime_status == "maintenance" or automation_issues:
        status = "warning"
    elif runtime_status == "planned_off":
        status = "planned_off"
    else:
        status = "warning" if state_healthy is False else "healthy"

    return {
        "status": status,
        "runtime_status": runtime_status,
        "state_healthy": state_healthy,
        "automation_status": automation_status,
        "automation_issues": automation_issues,
        "automation_notices": automation_notices,
        "tasks": tasks,
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
        raise EvidenceInputError("Evidence must contain runtime_status, state_healthy, expected_tasks, and tasks.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 scheduler evidence")
    args = parser.parse_args()
    try:
        saved = _read_evidence(args.input)
        report = classify_recovery(
            saved["runtime_status"], saved["state_healthy"], saved["expected_tasks"], saved["tasks"],
        )
    except EvidenceInputError as error:
        parser.exit(2, f"{error}\n")
    except OSError:
        parser.exit(2, "Could not read the saved evidence.\n")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
