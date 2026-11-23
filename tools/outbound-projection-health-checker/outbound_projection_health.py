"""Check whether a saved worker status records a fresh successful projection."""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


STATUS_SCHEMA_VERSION = 1
MAX_STATUS_BYTES = 65_536


class HealthStateError(RuntimeError):
    """A saved worker status file is unavailable or invalid."""


def _read_status(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_STATUS_BYTES + 1)
        if len(raw) > MAX_STATUS_BYTES:
            raise HealthStateError("Worker health state is oversized.")
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, RecursionError) as exc:
        raise HealthStateError("Worker health state is unavailable.") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != STATUS_SCHEMA_VERSION:
        raise HealthStateError("Worker health state is invalid.")
    return payload


def worker_is_healthy(
    path: Path,
    *,
    now: datetime,
    max_age_seconds: int,
) -> bool:
    """Return true only while a validated successful cycle remains fresh."""

    try:
        payload = _read_status(path)
        raw_success = payload.get("last_success_at")
        if not isinstance(raw_success, str):
            return False
        successful_at = datetime.fromisoformat(raw_success.replace("Z", "+00:00"))
        if successful_at.tzinfo is None:
            return False
        age = (now.astimezone(UTC) - successful_at.astimezone(UTC)).total_seconds()
        return -60 <= age <= max_age_seconds
    except (HealthStateError, ValueError, TypeError, OverflowError):
        return False


def timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is not None:
            return parsed
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("expected an ISO 8601 timestamp with a UTC offset")


def nonnegative_seconds(value: str) -> int:
    try:
        seconds = int(value)
        if seconds >= 0:
            return seconds
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("expected a nonnegative number of whole seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("status_file", type=Path, help="Saved worker status in JSON")
    parser.add_argument("--at", required=True, type=timestamp, help="Time at which to evaluate freshness")
    parser.add_argument("--max-age-seconds", required=True, type=nonnegative_seconds)
    args = parser.parse_args()

    healthy = worker_is_healthy(args.status_file, now=args.at, max_age_seconds=args.max_age_seconds)
    print(json.dumps({"healthy": healthy}))
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
