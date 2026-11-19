"""Command-line entry point for a saved player activity history."""

import argparse
import json
from pathlib import Path
import sys

from .history import ReportError, build_report, read_history


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "Invalid arguments. See --help for usage.\n")


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser(
        prog="python -m player_activity_history",
        description="Report activity history from saved daily totals and state observations.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Saved activity history JSON")
    parser.add_argument("--as-of", required=True, help="Report date (YYYY-MM-DD)")
    parser.add_argument("--display-offset", default="+00:00", help="Fixed UTC offset (default +00:00)")
    args = parser.parse_args(argv)
    try:
        report = build_report(read_history(args.input), args.as_of, args.display_offset)
    except (OSError, ReportError):
        print("Could not report the supplied player activity history.", file=sys.stderr)
        return 2
    print(json.dumps(report, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
