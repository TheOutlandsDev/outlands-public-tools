"""Render saved task observations and advisory runtime status."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any


_RUNTIME_STATES = {"online", "down", "maintenance", "planned_off"}
_UNTIMED_LABELS = {"Manual launcher", "Logon console", "Logon recovery", "Logon lock"}
_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def _display_zone(value: str) -> timezone:
    if value == "Z":
        return timezone.utc
    match = re.fullmatch(r"([+-])([0-9]{2}):([0-9]{2})", value) if isinstance(value, str) else None
    if match is not None:
        sign, hours_text, minutes_text = match.groups()
        hours, minutes = int(hours_text), int(minutes_text)
        if hours <= 23 and minutes <= 59:
            amount = timedelta(hours=hours, minutes=minutes)
            return timezone(-amount if sign == "-" else amount)
    raise ValueError("display_offset must be Z or a fixed UTC offset (+/-HH:MM)")


def _text(value: Any, field: str) -> str:
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            pass
        else:
            return value
    raise ValueError(f"{field} must be valid text")


def _runtime_status(server: dict[str, Any]) -> str:
    explicit = _text(server.get("runtime_status", ""), "runtime_status").casefold()
    if explicit in _RUNTIME_STATES:
        return explicit
    status = _text(server.get("status", ""), "status").casefold()
    if status in {"down", "planned_off"}:
        return status
    return "online"


def _automation_status(server: dict[str, Any], issues: list[str], tasks: list[Any]) -> str:
    explicit = _text(server.get("automation_status", ""), "automation_status").casefold()
    if explicit:
        return explicit
    if any(issue.casefold().startswith("scheduler:") for issue in issues):
        return "attention"
    return "ready" if tasks else "not configured"


def _server_next_action(runtime: str, automation: str, issues: list[str]) -> str:
    if runtime == "down":
        return "Verify the missing process/listener first; use approved controls only."
    if runtime == "maintenance":
        return "No outage: a scheduled controller is running; allow its bounded restart window."
    if runtime == "planned_off":
        return "No outage: runtime is intentionally stopped; leave it off."
    if automation == "attention":
        return "No outage: inspect and repair the restart task after the active soak."
    if any(not issue.casefold().startswith("scheduler:") for issue in issues):
        return "Runtime is online; review the listed support-state warning."
    return "No action required."


def _saved_time(value: Any) -> datetime:
    try:
        if isinstance(value, str):
            when = datetime.fromisoformat(value)
            if when.utcoffset() is not None:
                return when
    except (OverflowError, ValueError):
        pass
    raise ValueError("next_run must be an ISO 8601 timestamp with a UTC offset")


def _format_time(when: datetime, zone: timezone) -> str:
    display = when.astimezone(zone)
    hour = display.hour % 12 or 12
    half = "AM" if display.hour < 12 else "PM"
    return f"{_MONTHS[display.month - 1]} {display.day} {hour}:{display.minute:02d} {half}"


def _server_schedule(tasks: list[Any], zone: timezone) -> str:
    details: list[str] = []
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("each task must be an object")
        installed = task.get("installed", False)
        enabled = task.get("enabled", False)
        if type(installed) is not bool or type(enabled) is not bool:
            raise ValueError("task installed and enabled must be booleans")
        if not installed or not enabled:
            continue

        name = _text(task.get("name"), "task name")
        label = _text(task.get("label", name), "task label")
        if not name.strip() or not label.strip():
            raise ValueError("task name and label must be nonempty")
        state = _text(task.get("state", ""), "task state")
        warning_minutes = task.get("warning_minutes", 0)
        if type(warning_minutes) is not int or warning_minutes < 0:
            raise ValueError("warning_minutes must be a nonnegative integer")
        if state.casefold() == "running":
            details.append(f"{label}: RUNNING")
            continue

        next_run = task.get("next_run")
        if next_run is None or next_run == "":
            if label not in _UNTIMED_LABELS:
                details.append(label)
            continue

        when = _saved_time(next_run)
        try:
            warning_time = _format_time(when, zone)
            if warning_minutes:
                restart_time = _format_time(when + timedelta(minutes=warning_minutes), zone)
                details.append(f"{label} {restart_time} (warnings {warning_time})")
            else:
                details.append(f"{label} {warning_time}")
        except (OverflowError, ValueError):
            raise ValueError("task schedule is outside the supported timestamp range") from None
    return " | ".join(details) if details else "No timed controller"


def build_preview(server: dict[str, Any], *, display_offset: str) -> dict[str, str]:
    """Return runtime advice and formatted task timings from a saved server record."""
    if not isinstance(server, dict):
        raise ValueError("server must be an object")
    zone = _display_zone(display_offset)
    tasks = server.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("tasks must be an array")
    issues = server.get("issues", [])
    if not isinstance(issues, list) or any(not isinstance(issue, str) for issue in issues):
        raise ValueError("issues must be an array of text")
    issues = [_text(issue, "issue") for issue in issues]
    runtime = _runtime_status(server)
    automation = _automation_status(server, issues, tasks)
    return {
        "runtime_status": runtime,
        "next_action": _server_next_action(runtime, automation, issues),
        "schedule": _server_schedule(tasks, zone),
    }
