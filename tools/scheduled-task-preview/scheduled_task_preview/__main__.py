"""Preview scheduled tasks from saved records using a fixed display offset."""

import argparse
import json
import math
from pathlib import Path

from .preview import build_preview


MAX_INPUT_BYTES = 4 * 1024 * 1024


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="saved server and task JSON")
    parser.add_argument(
        "--display-offset", required=True, help="Z or UTC offset, for example --display-offset=-04:00"
    )
    args = parser.parse_args()

    try:
        payload = _read_input(args.input)
        report = build_preview(payload, display_offset=args.display_offset)
        output = json.dumps(report, indent=2, allow_nan=False)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        parser.exit(2, "error: expected valid UTF-8 JSON\n")
    except OSError:
        parser.exit(2, "error: could not read input\n")
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
