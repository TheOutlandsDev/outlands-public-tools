"""Classify the saved Ollama endpoint health and expected runtime state."""

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


def classify_ollama_runtime(snapshot: dict[str, Any]) -> list[IncidentCandidate]:
    """Apply the original Ollama runtime incident rule."""
    incidents: list[IncidentCandidate] = []
    ai = snapshot.get("ai", {})
    ollama = ai.get("ollama", {})
    ollama_expected_state = str(
        ollama.get("expected_state", "online")
    ).casefold()
    if ollama_expected_state == "planned_off":
        if ollama.get("healthy", False):
            incidents.append(
                _candidate(
                    "ai:ollama",
                    "unexpected_state",
                    "warning",
                    "Ollama is running during a planned-off window",
                    {
                        **ollama,
                        "impact": "AI compute is active despite the planned hardware hold",
                        "suggested_action": (
                            "Confirm intent before stopping Ollama with approved controls."
                        ),
                    },
                )
            )
    elif not ollama.get("healthy", False):
        incidents.append(
            _candidate(
                "ai:ollama",
                "endpoint",
                "warning",
                "Ollama local endpoint is unavailable",
                {
                    **ollama,
                    "impact": "Game servers unaffected; AI assistant unavailable",
                    "suggested_action": "Restore Ollama only after hardware approval.",
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
    ollama = ai.get("ollama", {})
    if not isinstance(ollama, dict):
        raise ValueError("Ollama telemetry must be an object.")
    if "healthy" in ollama and type(ollama["healthy"]) is not bool:
        raise ValueError("Ollama healthy must be Boolean.")
    if "expected_state" in ollama and not isinstance(ollama["expected_state"], str):
        raise ValueError("Ollama expected_state must be text.")
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
            for item in classify_ollama_runtime(snapshot)
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
