"""Run the checker on supplied saved JSON evidence."""

import argparse
import json
from pathlib import Path
import sys

from .evidence import EvidenceError, check_evidence, read_evidence


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "Invalid arguments. See --help for usage.\n")


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser(
        prog="python -m process_listener_evidence",
        description="Check saved process identity and listener ownership evidence.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Saved evidence JSON")
    args = parser.parse_args(argv)
    try:
        report = check_evidence(read_evidence(args.input))
    except (OSError, EvidenceError):
        print("Could not check the supplied process and listener evidence.", file=sys.stderr)
        return 2
    print(json.dumps(report, allow_nan=False))
    return 0 if report["status"] == "proven" else 1


if __name__ == "__main__":
    raise SystemExit(main())
