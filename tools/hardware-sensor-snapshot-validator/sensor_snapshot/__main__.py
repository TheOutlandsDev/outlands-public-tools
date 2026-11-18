"""Validate a saved hardware temperature snapshot and print the result."""

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from .validator import validate_snapshot


MAX_INPUT_BYTES = 4 * 1024 * 1024


def _read(path: Path) -> object:
    if not path.is_file():
        raise ValueError("input must be a regular file")
    with path.open("rb") as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 4 MiB")
    return json.loads(raw.decode("utf-8-sig"))


def _now(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            return parsed.astimezone(UTC)
    except (OverflowError, ValueError):
        pass
    raise argparse.ArgumentTypeError("use an ISO 8601 timestamp with a time zone")


def _maximum_age(value: str) -> float:
    try:
        limit = float(value)
    except ValueError:
        limit = math.nan
    if not math.isfinite(limit) or limit < 0:
        raise argparse.ArgumentTypeError("use a finite nonnegative number of seconds")
    return limit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="saved snapshot JSON")
    parser.add_argument("--now", type=_now, help="reference time for reproducible checks")
    parser.add_argument("--max-age-seconds", type=_maximum_age, default=20.0)
    args = parser.parse_args()

    try:
        payload = _read(args.input)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        parser.exit(2, "error: expected valid UTF-8 JSON\n")
    except OSError:
        parser.exit(2, "error: could not read input\n")
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    readings, status = validate_snapshot(
        payload, now=args.now or datetime.now(UTC), maximum_age_seconds=args.max_age_seconds
    )
    print(json.dumps({"readings": readings, "status": status}, indent=2, allow_nan=False))
    return 0 if readings else 1


if __name__ == "__main__":
    raise SystemExit(main())
