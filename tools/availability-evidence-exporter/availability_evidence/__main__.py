"""Export a fixed-field safety summary from saved availability evidence."""

import argparse
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from .exporter import build_safety, build_signal


MAX_INPUT_BYTES = 4 * 1024 * 1024
SIGNAL_FIELDS = {"state", "method", "observedAtUtc", "result"}


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


def _signal_from_input(value: object) -> dict:
    if not isinstance(value, dict) or not SIGNAL_FIELDS <= value.keys():
        raise ValueError("each signal needs state, method, observedAtUtc, and result")
    observed = value["observedAtUtc"]
    try:
        valid_time = (
            isinstance(observed, str)
            and datetime.fromisoformat(observed).utcoffset() == timedelta(0)
        )
    except (OverflowError, ValueError):
        valid_time = False
    if not valid_time:
        raise ValueError("observedAtUtc must be an ISO 8601 UTC timestamp")
    return build_signal(value["state"], value["method"], observed, value["result"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="saved availability evidence JSON")
    args = parser.parse_args()

    try:
        payload = _read_input(args.input)
        if not isinstance(payload, dict) or not isinstance(payload.get("snapshot"), dict):
            raise ValueError("input must include a snapshot object")
        if not isinstance(payload.get("signals"), list):
            raise ValueError("input must include a signals array")
        safety = build_safety(payload["snapshot"])
        signals = [_signal_from_input(item) for item in payload["signals"]]
        report = json.dumps({"safety": safety, "signals": signals}, indent=2, allow_nan=False)
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
