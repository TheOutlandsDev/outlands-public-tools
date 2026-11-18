"""Classify saved server observations and print the incidents as JSON."""

import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path

from .classifier import classify_servers


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
    parser.add_argument("--input", required=True, type=Path, help="saved server observations JSON")
    args = parser.parse_args()

    try:
        payload = _read_input(args.input)
        if not isinstance(payload, dict) or "servers" not in payload:
            raise ValueError("input must include a servers array")
        incidents = [
            {**asdict(incident), "fingerprint": incident.fingerprint}
            for incident in classify_servers(payload["servers"])
        ]
        report = json.dumps({"incidents": incidents}, indent=2, allow_nan=False)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        parser.exit(2, "error: expected valid UTF-8 JSON\n")
    except OSError:
        parser.exit(2, "error: could not read input\n")
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
