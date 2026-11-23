"""Build the next worker status from an offline projection outcome."""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from uuid import UUID


STATUS_SCHEMA_VERSION = 1
MAX_STATUS_BYTES = 65_536
COUNTS = ("source_event_count", "inserted_event_count", "replayed_event_count")


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _timestamp(value: object) -> datetime:
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is not None:
            return parsed
    raise ValueError("Expected a timestamp with a UTC offset.")


def _read_record(path: Path) -> dict:
    with path.open("rb") as stream:
        raw = stream.read(MAX_STATUS_BYTES + 1)
    if len(raw) > MAX_STATUS_BYTES:
        raise ValueError("The record exceeds the byte limit.")
    record = json.loads(raw.decode("utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Expected a JSON object.")
    return record


def _load_prior(path: Path | None) -> dict:
    if path is None:
        return {}
    try:
        record = _read_record(path)
        return record if record.get("schema_version") == STATUS_SCHEMA_VERSION else {}
    except (OSError, ValueError, RecursionError):
        return {}


def _previous_success(previous: dict) -> tuple[str | None, int]:
    last_success = previous.get("last_success_at")
    failures = previous.get("consecutive_failures", 0)
    try:
        last_success = _iso(_timestamp(last_success))
    except (ValueError, OverflowError):
        last_success = None
    return last_success, failures if type(failures) is int and failures >= 0 else 0


def next_status(outcome: dict, previous: dict) -> dict:
    attempted_at = _iso(_timestamp(outcome.get("attempted_at")))
    result = outcome.get("last_result")
    common = {
        "schema_version": STATUS_SCHEMA_VERSION,
        "scope": "development-only",
        "authority": "postgresql",
        "last_result": result,
        "last_attempt_at": attempted_at,
    }
    if result == "failed":
        category = outcome.get("failure_category")
        if category not in ("projection", "unexpected"):
            raise ValueError("Unknown failure category.")
        last_success, prior_failures = _previous_success(previous)
        return {
            **common,
            "last_success_at": last_success,
            "consecutive_failures": prior_failures + 1,
            "failure_category": category,
        }

    if result != "accepted":
        raise ValueError("Unknown projection result.")
    run_id = outcome.get("projection_run_id")
    if not isinstance(run_id, str):
        raise ValueError("Expected a projection run UUID.")
    counts = {key: outcome.get(key) for key in COUNTS}
    if any(type(count) is not int or count < 0 for count in counts.values()):
        raise ValueError("Expected nonnegative integer event counts.")
    return {
        **common,
        "last_success_at": _iso(_timestamp(outcome.get("projected_at"))),
        "consecutive_failures": 0,
        "projection_run_id": str(UUID(run_id)),
        **counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outcome", type=Path, help="Recorded result of one attempted projection")
    parser.add_argument("--prior-status", type=Path, help="Previous worker status JSON")
    args = parser.parse_args()
    try:
        status = next_status(_read_record(args.outcome), _load_prior(args.prior_status))
        report = json.dumps(status, indent=2)
        if len(report.encode("utf-8")) > MAX_STATUS_BYTES:
            raise ValueError("The status exceeds the byte limit.")
    except (OSError, ValueError, OverflowError, RecursionError):
        print("The projection outcome is unreadable or invalid.", file=sys.stderr)
        return 2
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
