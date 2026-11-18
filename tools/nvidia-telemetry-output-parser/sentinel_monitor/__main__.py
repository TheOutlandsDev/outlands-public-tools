"""Read saved GPU output and write a JSON report to stdout."""

import argparse
import csv
import json
import math
from dataclasses import asdict
from pathlib import Path

from .collectors.nvidia import parse_gpu_output


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
    parser.add_argument("--csv", required=True, type=Path, help="saved headerless GPU query CSV")
    parser.add_argument("--replay", type=Path, help="optional saved PCIe query text")
    args = parser.parse_args()
    try:
        csv_output = _read(args.csv)
        replay_output = _read(args.replay) if args.replay is not None else ""
        readings, status = parse_gpu_output(csv_output, replay_output)
    except UnicodeDecodeError:
        parser.exit(2, "error: expected UTF-8 input\n")
    except csv.Error:
        parser.exit(2, 'error: invalid or oversized CSV field\n')
    except OSError:
        parser.exit(2, "error: could not read input\n")
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    report = []
    for reading in readings:
        row = asdict(reading)
        for field, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                row[field] = None
        report.append(row)
    print(json.dumps({"readings": report, "status": status}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
