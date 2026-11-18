"""Summarize saved crash telemetry and print the report."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .report import summarize


def _reference_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            return parsed.astimezone(UTC)
    except (ValueError, OverflowError):
        pass
    raise argparse.ArgumentTypeError("use an ISO 8601 timestamp with a time zone")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path, help="closed SQLite snapshot export")
    parser.add_argument("--sensors", required=True, type=Path, help="saved temperatures JSON")
    parser.add_argument("--thermal-guard", required=True, type=Path, help="saved thermal guard JSON")
    parser.add_argument("--quarantine", required=True, type=Path, help="saved quarantine JSON")
    parser.add_argument("--now-utc", type=_reference_time, help="reference time for a reproducible report")
    args = parser.parse_args()

    report = summarize(
        args.database,
        args.sensors,
        args.thermal_guard,
        args.quarantine,
        args.now_utc if args.now_utc is not None else datetime.now(UTC),
    )
    print(json.dumps(report, indent=2, allow_nan=False))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
