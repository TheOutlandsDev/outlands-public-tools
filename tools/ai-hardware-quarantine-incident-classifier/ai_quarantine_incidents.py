"""Classify the AI hardware quarantine in a saved telemetry snapshot."""

import argparse
from dataclasses import dataclass
import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Any


MAX_SNAPSHOT_BYTES = 1024 * 1024


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


def classify_hardware_quarantine(snapshot: dict[str, Any]) -> list[IncidentCandidate]:
    """Preserve the AI quarantine rule for a saved snapshot."""
    incidents: list[IncidentCandidate] = []
    ai = snapshot.get("ai", {})
    quarantine = ai.get("hardware_quarantine", {})
    if quarantine.get("latched") is True:
        reason_text = "; ".join(
            str(item.get("detail", item)) if isinstance(item, dict) else str(item)
            for item in quarantine.get("reasons", [])
        )
        incidents.append(
            _candidate(
                "safety:hardware_quarantine",
                "ai_latched",
                "critical",
                "Hardware degraded / AI quarantined"
                + (f": {reason_text[:320]}" if reason_text else ""),
                {
                    **quarantine,
                    "impact": "AI compute blocked; game servers remain online",
                    "suggested_action": (
                        "Keep AI disabled. Clear only through the approval-gated "
                        "hardware recovery validation."
                    ),
                },
            )
        )
    return incidents


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-JSON constant")


def finite_float(raw):
    value = float(raw)
    if not isfinite(value):
        raise ValueError("Nonfinite JSON number")
    return value


def read_snapshot(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise OSError
        with path.open("rb") as stream:
            payload = stream.read(MAX_SNAPSHOT_BYTES + 1)
    except OSError:
        raise ValueError("Unable to read the telemetry snapshot.") from None

    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise ValueError("The telemetry snapshot exceeds the 1 MiB limit.")

    try:
        data = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant, parse_float=finite_float)
    except (ValueError, RecursionError):
        raise ValueError("Invalid telemetry JSON.") from None

    if not isinstance(data, dict):
        raise ValueError("The telemetry snapshot must be an object.")
    ai = data.get("ai", {})
    if not isinstance(ai, dict):
        raise ValueError("The AI telemetry must be an object.")
    quarantine = ai.get("hardware_quarantine", {})
    if not isinstance(quarantine, dict):
        raise ValueError("The hardware quarantine must be an object.")
    if quarantine.get("latched") is True and not isinstance(quarantine.get("reasons", []), list):
        raise ValueError("Latched quarantine reasons must be an array.")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Saved telemetry snapshot JSON")
    args = parser.parse_args()
    try:
        snapshot = read_snapshot(args.snapshot)
        incidents = [
            {
                "code": item.code,
                "evidence": item.evidence,
                "fingerprint": item.fingerprint,
                "severity": item.severity,
                "source": item.source,
                "summary": item.summary,
            }
            for item in classify_hardware_quarantine(snapshot)
        ]
        report = json.dumps({"incidents": incidents}, indent=2, sort_keys=True, allow_nan=False)
    except (UnicodeError, RecursionError):
        parser.exit(2, "Invalid telemetry text or nesting.\n")
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
