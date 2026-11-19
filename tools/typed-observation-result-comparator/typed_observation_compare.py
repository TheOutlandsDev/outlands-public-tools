"""Compare two saved results as exact typed row multisets."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import TextIO


COLUMN_COUNT = 5
MAX_ROWS = 10_000
MAX_INPUT_BYTES = 16 * 1024 * 1024
TIMESTAMP_COLUMNS = (3, 4)
TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?"
)
ERRORS = {
    "arguments": "Invalid arguments. Use --help for usage.",
    "input_file": "Unable to read an ordinary observation result file.",
    "input_size": "Observation result file exceeds the 16 MiB limit.",
    "input_json": "Observation result file must contain valid UTF-8 JSON.",
    "result_shape": "Invalid observation result rows.",
}


class ValidationError(Exception):
    """Collect a fixed error category without storing input data."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


def validate_rows(rows: Sequence[Sequence[object]]) -> list[tuple[object, ...]]:
    """Preserve exact strings and nulls, with naive timestamps in both fields."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) > MAX_ROWS:
        raise ValidationError("result_shape")
    validated = []
    for raw in rows:
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) != COLUMN_COUNT:
            raise ValidationError("result_shape")
        row = tuple(raw)
        for index, value in enumerate(row):
            if value is None:
                continue
            if index in TIMESTAMP_COLUMNS:
                if type(value) is not datetime or value.tzinfo is not None:
                    raise ValidationError("result_shape")
            elif type(value) is not str:
                raise ValidationError("result_shape")
        validated.append(row)
    return validated


def compare_rows(expected: Sequence[Sequence[object]], actual: Sequence[Sequence[object]]) -> dict[str, object]:
    """Compare every typed value and duplicate count without emitting raw values."""
    left, right = Counter(validate_rows(expected)), Counter(validate_rows(actual))
    left_only, right_only = left - right, right - left
    matched = not left_only and not right_only
    return {
        "status": "match" if matched else "mismatch",
        "all_values_match": matched,
        "columns_compared": COLUMN_COUNT,
        "expected_rows": sum(left.values()),
        "actual_rows": sum(right.values()),
        "matched_rows": sum((left & right).values()),
        "expected_only_rows": sum(left_only.values()),
        "actual_only_rows": sum(right_only.values()),
        "expected_only_distinct_rows": len(left_only),
        "actual_only_distinct_rows": len(right_only),
        "comparison_basis": "Exact typed five-field multiset with nulls and duplicates.",
    }


def _timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or TIMESTAMP.fullmatch(value) is None:
        raise ValidationError("result_shape")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValidationError("result_shape") from None


def _decode_rows(raw: object) -> list[tuple[object, ...]]:
    if not isinstance(raw, list) or len(raw) > MAX_ROWS:
        raise ValidationError("result_shape")
    rows = []
    for row in raw:
        if not isinstance(row, list) or len(row) != COLUMN_COUNT:
            raise ValidationError("result_shape")
        rows.append(tuple(_timestamp(value) if index in TIMESTAMP_COLUMNS else value
                          for index, value in enumerate(row)))
    return rows


def _is_regular(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _read_json(path: Path) -> object:
    try:
        selected = path.lstat()
        if not _is_regular(selected):
            raise ValidationError("input_file")
        if selected.st_size > MAX_INPUT_BYTES:
            raise ValidationError("input_size")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _is_regular(opened) or not os.path.samestat(selected, opened):
                raise ValidationError("input_file")
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except (OSError, ValueError):
        raise ValidationError("input_file") from None
    if len(payload) > MAX_INPUT_BYTES:
        raise ValidationError("input_size")
    try:
        return json.loads(payload.decode("utf-8"))
    except (ValueError, RecursionError):
        raise ValidationError("input_json") from None


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValidationError("arguments")


def main(
    argv: Sequence[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    parser = _ArgumentParser(
        description="Compare exact text, timestamps, nulls, and duplicate counts in two saved results.",
        allow_abbrev=False,
    )
    parser.add_argument("--expected", required=True, type=Path, help="Expected UTF-8 JSON result file.")
    parser.add_argument("--actual", required=True, type=Path, help="Actual UTF-8 JSON result file.")
    try:
        args = parser.parse_args(argv)
        expected = _decode_rows(_read_json(args.expected))
        actual = _decode_rows(_read_json(args.actual))
        report = compare_rows(expected, actual)
    except ValidationError as error:
        errors.write(f"ERROR: {ERRORS[error.category]}\n")
        return 2

    json.dump(report, output)
    output.write("\n")
    return 0 if report["all_values_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
