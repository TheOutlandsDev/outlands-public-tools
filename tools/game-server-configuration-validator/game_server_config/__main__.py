"""Validate saved game server declarations and print a configuration count."""

import argparse
import json
import math
import sys
from pathlib import Path

from .validator import validate_config


MAX_INPUT_BYTES = 4 * 1024 * 1024


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(file=sys.stderr)
        self.exit(2, "error: invalid command arguments\n")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("JSON object keys must be unique")
    return result


def _finite_number(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON numbers must be finite")
    return number


def _read_input(path: Path) -> object:
    if not path.is_file():
        raise ValueError("input must be a regular file")
    with path.open("rb") as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 4 MiB")
    return json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=_unique_object,
        parse_float=_finite_number,
        parse_constant=_finite_number,
    )


def main() -> int:
    parser = _SafeParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="saved JSON configuration")
    args = parser.parse_args()

    try:
        count = validate_config(_read_input(args.input))
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        parser.exit(2, "error: expected valid UTF-8 JSON\n")
    except OSError:
        parser.exit(2, "error: could not read input\n")
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(json.dumps({"status": "valid", "server_count": count}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
