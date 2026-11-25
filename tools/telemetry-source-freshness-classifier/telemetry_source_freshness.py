"""Classify collector freshness in a saved telemetry snapshot."""

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


def classify_source_freshness(snapshot: dict[str, Any]) -> list[IncidentCandidate]:
    """Report stale and unavailable collector states."""
    incidents: list[IncidentCandidate] = []
    for source_name, health in snapshot.get("source_health", {}).items():
        if not isinstance(health, dict):
            continue
        state = str(health.get("state", "unavailable")).casefold()
        if state not in {"stale", "unavailable"}:
            continue
        label = str(source_name).replace("_", " ")
        if state == "stale":
            summary = f"{label} data is stale; the last valid value is cached"
            impact = "Dependent views may be delayed, but unrelated collectors remain current"
        else:
            summary = f"{label} data is unavailable; no valid fallback exists"
            impact = "Dependent views have no current or cached source data"
        incidents.append(
            _candidate(
                f"collector:{source_name}",
                "freshness",
                "warning",
                summary,
                {
                    **health,
                    "impact": impact,
                    "suggested_action": (
                        "Inspect the isolated collector error; do not infer failure "
                        "of unrelated sources or game runtimes."
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
    sources = data.get("source_health", {})
    if not isinstance(sources, dict):
        raise ValueError("Source health must be an object.")
    if len(sources) > 1000:
        raise ValueError("Source health exceeds 1000 collectors.")
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
            for item in classify_source_freshness(snapshot)
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
