"""Compare two saved CSV result sets without a database connection.

Rows are compared as multisets after aligning columns by name or by a complete
left-to-right mapping. Reports contain counts and row digests, never row values.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Sequence


_DEFAULT_MAX_EXAMPLES = 5
_MAX_EXAMPLES_LIMIT = 20


def _read_csv(path: Path) -> tuple[list[str], Counter[tuple[str, ...]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader, None)
        if not header or any(not name for name in header):
            raise ValueError("CSV header is missing or contains an empty column name")
        if len(header) != len(set(header)):
            raise ValueError("CSV header contains duplicate column names")

        rows: Counter[tuple[str, ...]] = Counter()
        for row_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(f"CSV row {row_number} has a different column count")
            rows[tuple(row)] += 1
    return header, rows


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Column mapping JSON contains a duplicate key")
        result[key] = value
    return result


def _load_mapping(path: Path) -> dict[str, str]:
    mapping = json.loads(
        path.read_text(encoding="utf-8-sig"),
        object_pairs_hook=_reject_duplicate_json_keys,
    )
    if not isinstance(mapping, dict) or any(
        not isinstance(key, str) or not isinstance(value, str) or not key or not value
        for key, value in mapping.items()
    ):
        raise ValueError("Column mapping must be a JSON object of nonempty string names")
    return mapping


def _right_indices(
    left_header: list[str], right_header: list[str], mapping: dict[str, str] | None
) -> list[int]:
    if mapping is None:
        if set(left_header) != set(right_header):
            raise ValueError("CSV columns differ; provide a complete column mapping JSON")
        right_names = left_header
    else:
        if set(mapping) != set(left_header) or set(mapping.values()) != set(right_header):
            raise ValueError("Column mapping must cover every column on both sides exactly once")
        if len(set(mapping.values())) != len(mapping):
            raise ValueError("Column mapping must use each right column exactly once")
        right_names = [mapping[name] for name in left_header]
    return [right_header.index(name) for name in right_names]


def _row_digest(row: tuple[str, ...]) -> str:
    canonical = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"rdl-query-lab-row-v1\x00" + canonical).hexdigest()


def _examples(rows: Counter[tuple[str, ...]], limit: int) -> list[dict[str, str | int]]:
    digests = [(_row_digest(row), count) for row, count in rows.items()]
    digests.sort(key=lambda item: (-item[1], item[0]))
    return [{"sha256": digest, "count": count} for digest, count in digests[:limit]]


def compare_csvs(
    left_path: Path | str,
    right_path: Path | str,
    *,
    mapping_path: Path | str | None = None,
    max_examples: int = _DEFAULT_MAX_EXAMPLES,
) -> dict[str, object]:
    """Compare saved CSVs exactly, ignoring only row and column order.

    A mapping file may rename columns, but it must be a complete one-to-one
    mapping from left column names to right column names. CSV values remain
    strings; no whitespace, date, or numeric normalization is applied.
    """

    if not isinstance(max_examples, int) or not 0 <= max_examples <= _MAX_EXAMPLES_LIMIT:
        raise ValueError(f"max_examples must be an integer from 0 to {_MAX_EXAMPLES_LIMIT}")

    left_header, left_rows = _read_csv(Path(left_path))
    right_header, right_rows = _read_csv(Path(right_path))
    mapping = _load_mapping(Path(mapping_path)) if mapping_path is not None else None
    indices = _right_indices(left_header, right_header, mapping)
    aligned_right: Counter[tuple[str, ...]] = Counter()
    for row, count in right_rows.items():
        aligned_right[tuple(row[index] for index in indices)] += count

    left_only = left_rows - aligned_right
    right_only = aligned_right - left_rows
    matched_rows = sum((left_rows & aligned_right).values())
    return {
        "status": "match" if not left_only and not right_only else "mismatch",
        "columns_compared": len(left_header),
        "column_mapping_used": mapping is not None,
        "left_rows": sum(left_rows.values()),
        "right_rows": sum(right_rows.values()),
        "matched_rows": matched_rows,
        "left_only_rows": sum(left_only.values()),
        "right_only_rows": sum(right_only.values()),
        "left_only_distinct_rows": len(left_only),
        "right_only_distinct_rows": len(right_only),
        "left_only_examples": _examples(left_only, max_examples),
        "right_only_examples": _examples(right_only, max_examples),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path, help="First saved CSV result")
    parser.add_argument("right", type=Path, help="Second saved CSV result")
    parser.add_argument("--mapping", type=Path, help="Complete left-to-right column mapping JSON")
    parser.add_argument(
        "--max-examples", type=int, default=_DEFAULT_MAX_EXAMPLES,
        help=f"Digest examples per side, from 0 to {_MAX_EXAMPLES_LIMIT} (default: {_DEFAULT_MAX_EXAMPLES})",
    )
    args = parser.parse_args(argv)
    try:
        report = compare_csvs(
            args.left, args.right, mapping_path=args.mapping, max_examples=args.max_examples
        )
    except (OSError, UnicodeError, csv.Error, json.JSONDecodeError, ValueError) as exc:
        print(f"Comparison input error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
