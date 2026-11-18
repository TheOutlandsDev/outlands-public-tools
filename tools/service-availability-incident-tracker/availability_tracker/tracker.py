"""Offline state transitions and JSON persistence for supplied check results."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return default


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(value, indent=2))
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def determine_overall(checks: list[dict[str, Any]]) -> str:
    required = [item for item in checks if item.get("required", True)]
    if required and all(bool(item.get("ok")) for item in required):
        return "online"
    if checks and any(bool(item.get("ok")) for item in checks):
        return "degraded"
    return "offline"


def apply_transition(
    state: dict[str, Any], overall: str, observed_at: datetime
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    previous = str(state.get("previousOverall") or "unknown")
    active = state.get("activeIncident")
    completed = None
    if overall != "online" and not isinstance(active, dict):
        active = {
            "startedAt": iso(observed_at),
            "initialState": overall,
            "worstState": overall,
        }
    elif overall == "offline" and isinstance(active, dict):
        active["worstState"] = "offline"
    if overall == "online" and isinstance(active, dict):
        started = datetime.fromisoformat(str(active["startedAt"]).replace("Z", "+00:00"))
        completed = {
            **active,
            "recoveredAt": iso(observed_at),
            "durationSeconds": max(0, round((observed_at - started).total_seconds())),
        }
        active = None
    state.update(
        {
            "schemaVersion": 1,
            "previousOverall": overall,
            "previousObservedAt": iso(observed_at),
            "activeIncident": active,
            "lastTransition": (
                {"from": previous, "to": overall, "at": iso(observed_at)}
                if previous != overall
                else state.get("lastTransition")
            ),
        }
    )
    return state, completed
