"""Read saved Windows hardware event JSON and write normalized events to stdout."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .event_payload import parse_event_payload


MAX_INPUT_BYTES = 4 * 1024 * 1024


def _read(path: Path) -> str:
    if not path.is_file():
        raise ValueError("input must be a regular file")
    with path.open("rb") as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 4 MiB")
    return raw.decode("utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="saved hardware event JSON")
    args = parser.parse_args()

    try:
        payload = _read(args.input)
    except UnicodeDecodeError:
        parser.exit(2, "error: expected UTF-8 input\n")
    except OSError:
        parser.exit(2, "error: could not read input\n")
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    try:
        events = parse_event_payload(payload)
    except (ValueError, RecursionError):
        parser.exit(2, "error: invalid or overly nested JSON\n")

    rows = []
    for event in events:
        row = asdict(event)
        row["timestamp"] = event.timestamp.isoformat()
        rows.append(row)
    print(json.dumps({"events": rows}, indent=2))


if __name__ == "__main__":
    main()
