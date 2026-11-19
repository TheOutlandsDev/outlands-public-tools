"""Command-line entry point for offline snapshot normalization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .normalizer import SnapshotError, _load_json, normalize_snapshot


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "Invalid arguments. See --help for usage.\n")


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser(
        prog="python -m player_telemetry_normalizer",
        description="Normalize a saved player telemetry JSON snapshot.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Saved snapshot JSON file")
    parser.add_argument("--mapping", required=True, type=Path, help="Server mapping JSON file")
    parser.add_argument("--format", required=True, choices=("portal", "collector"))
    args = parser.parse_args(argv)
    try:
        report = normalize_snapshot(_load_json(args.input), _load_json(args.mapping), args.format)
    except (OSError, SnapshotError):
        print("Could not normalize the supplied snapshot and mapping.", file=sys.stderr)
        return 2
    print(json.dumps(report, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
