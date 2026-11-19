"""Summarize game server status from a saved A2S_INFO or Quake 3 response."""

import argparse
import json
from pathlib import Path

from .parser import parse_a2s_info, parse_quake3_status


MAX_RESPONSE_BYTES = 64 * 1024
PARSERS = {"a2s-info": parse_a2s_info, "quake3-status": parse_quake3_status}


def _read_response(path: Path) -> bytes:
    if not path.is_file():
        raise ValueError("input must be a regular file")
    with path.open("rb") as source:
        data = source.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("response exceeds 64 KiB")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", required=True, choices=PARSERS, help="saved response format")
    parser.add_argument("--input", required=True, type=Path, help="saved response file")
    args = parser.parse_args()

    try:
        report = PARSERS[args.format](_read_response(args.input))
    except OSError:
        parser.exit(2, "error: could not read input\n")
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
