"""Classify incidents from explicitly supplied server runtime observations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import chain
from typing import Any


_TEXT_FIELDS = (
    "id",
    "name",
    "status",
    "runtime_status",
    "observed_runtime_status",
    "expected_state",
    "notes",
    "expected_state_reason",
)


@dataclass(frozen=True, slots=True)
class IncidentCandidate:
    source: str
    code: str
    severity: str
    summary: str
    evidence: dict[str, Any]

    @property
    def fingerprint(self) -> str:
        raw = f"{self.source}|{self.code}|{self.summary}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _candidate(
    source: str,
    code: str,
    severity: str,
    summary: str,
    evidence: dict[str, Any],
) -> IncidentCandidate:
    return IncidentCandidate(source, code, severity, summary[:500], evidence)


def _validate_server(server: Any) -> tuple[list[str], list[str]]:
    if not isinstance(server, dict):
        raise ValueError("each server must be an object")
    text = [server.get(field, "") for field in _TEXT_FIELDS]
    if any(not isinstance(value, str) for value in text):
        raise ValueError("server text fields must be strings")
    if not server.get("id", "").strip() or not server.get("name", "").strip():
        raise ValueError("each server needs a nonempty id and name")

    issues = server.get("issues", [])
    automation_issues = server.get("automation_issues", [])
    for values in (issues, automation_issues):
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError("server issues must be arrays of strings")
    try:
        for value in chain(text, issues, automation_issues):
            value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("server text must be valid Unicode") from None
    return list(issues), list(automation_issues)


def classify_servers(servers: list[dict[str, Any]]) -> list[IncidentCandidate]:
    """Return the advisory incidents generated for the supplied server rows."""
    if not isinstance(servers, list):
        raise ValueError("servers must be an array")
    incidents: list[IncidentCandidate] = []
    for server in servers:
        issues, automation_issues = _validate_server(server)
        if server.get("status") == "healthy":
            continue
        expected_state = str(server.get("expected_state", "online")).casefold()
        observed_runtime_status = str(
            server.get("observed_runtime_status", "")
        ).casefold()
        runtime_status = str(server.get("runtime_status", "")).casefold()
        if not runtime_status:
            runtime_status = "down" if server.get("status") == "down" else "online"
        if runtime_status == "planned_off":
            if not automation_issues:
                continue
            severity = "warning"
            summary = (
                f"{server.get('name')} runtime is PLANNED OFF; automation needs attention: "
                + "; ".join(automation_issues[:4])
            )
            impact = "NO OUTAGE - runtime is intentionally stopped"
            suggested_action = (
                "Keep the runtime off; inspect only the listed automation warning."
            )
        elif expected_state == "planned_off" and observed_runtime_status == "online":
            severity = "warning"
            summary = f"{server.get('name')} is ONLINE but configured PLANNED OFF"
            impact = "STATE MISMATCH - runtime is active during a planned-off window"
            suggested_action = (
                "Confirm intent before using approved controls to stop the runtime."
            )
        elif runtime_status == "maintenance":
            severity = "warning"
            summary = (
                f"{server.get('name')} is in SCHEDULED MAINTENANCE: "
                + ("; ".join(issues[:4]) or "approved restart controller is running")
            )
            impact = "SCHEDULED MAINTENANCE - bounded restart window, not a crash"
            suggested_action = (
                "Allow the scheduled controller to finish; investigate only if the "
                "maintenance window exceeds its bound."
            )
        elif runtime_status == "down":
            severity = "critical"
            summary = (
                f"{server.get('name')} runtime is DOWN: "
                + ("; ".join(issues[:4]) or "runtime proof is incomplete")
            )
            impact = "OUTAGE - process, listener, or endpoint proof is incomplete"
            suggested_action = (
                "Verify the missing runtime evidence, then use approved server controls."
            )
        else:
            severity = "warning"
            issue_type = "automation" if automation_issues else "support state"
            summary = (
                f"{server.get('name')} runtime is ONLINE; {issue_type} needs attention: "
                + ("; ".join(issues[:4]) or "support health is incomplete")
            )
            impact = "NO OUTAGE - runtime is online"
            suggested_action = (
                "Inspect the listed warning after the active soak; no restart is required."
            )
        incidents.append(
            _candidate(
                f"server:{server.get('id')}",
                "health",
                severity,
                summary,
                {
                    "issues": issues,
                    "automation_issues": automation_issues,
                    "notes": server.get("notes", ""),
                    "runtime_status": runtime_status,
                    "observed_runtime_status": observed_runtime_status,
                    "expected_state": expected_state,
                    "expected_state_reason": server.get("expected_state_reason", ""),
                    "impact": impact,
                    "suggested_action": suggested_action,
                },
            )
        )
    return incidents
