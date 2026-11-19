"""Select the latest recorded calendar day from a saved timestamp window."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import TextIO


ROW_CAP = 100
MAX_INPUT_BYTES = 16 * 1024
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,3})?")
ERRORS = {
    "arguments": "Invalid arguments. Use --help for usage.",
    "bounds": "Bounds must be ascending local date-times at millisecond precision.",
    "input_file": "Unable to read an ordinary observation file.",
    "input_size": "Observation file exceeds the 16 KiB limit.",
    "input_json": "Observation file must contain valid UTF-8 JSON.",
    "result_shape": "Invalid timestamp rows.",
    "window_overflow": "The next midnight is outside the supported calendar.",
}


class ValidationError(Exception):
    """A fixed error category suitable for reporting without source data."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


def _validate_bounds(start: datetime, end: datetime) -> None:
    if (type(start) is not datetime or type(end) is not datetime
            or start.tzinfo is not None or end.tzinfo is not None
            or start.microsecond % 1000 or end.microsecond % 1000 or not start < end):
        raise ValidationError("bounds")


def validate_rows(
    rows: Sequence[Sequence[object]], *, start: datetime, end: datetime,
) -> list[tuple[datetime]]:
    """Validate the one-column, descending millisecond timestamp rows."""
    _validate_bounds(start, end)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) > ROW_CAP:
        raise ValidationError("result_shape")
    previous = None
    validated = []
    for raw in rows:
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) != 1:
            raise ValidationError("result_shape")
        timestamp = raw[0]
        if (type(timestamp) is not datetime or timestamp.tzinfo is not None
                or timestamp.microsecond % 1000 or not start <= timestamp < end
                or (previous is not None and timestamp > previous)):
            raise ValidationError("result_shape")
        validated.append((timestamp,))
        previous = timestamp
    return validated


def _latest_window(rows: list[tuple[datetime]]) -> tuple[str, str] | None:
    if not rows:
        return None
    start = rows[0][0].replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        end = start + timedelta(days=1)
    except OverflowError:
        raise ValidationError("window_overflow") from None
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


def select_case(
    rows: Sequence[Sequence[object]], *, start: datetime, end: datetime,
) -> tuple[str, str] | None:
    """Choose the midnight-to-midnight window for the latest recorded day."""
    return _latest_window(validate_rows(rows, start=start, end=end))


def _timestamp(value: object, category: str) -> datetime:
    if not isinstance(value, str) or TIMESTAMP.fullmatch(value) is None:
        raise ValidationError(category)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValidationError(category) from None


def _decode_rows(raw: object) -> list[tuple[datetime]]:
    if not isinstance(raw, list) or len(raw) > ROW_CAP:
        raise ValidationError("result_shape")
    rows = []
    for row in raw:
        if not isinstance(row, list) or len(row) != 1:
            raise ValidationError("result_shape")
        rows.append((_timestamp(row[0], "result_shape"),))
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
        description="Select the latest recorded day from saved timestamp rows.",
        allow_abbrev=False,
    )
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 JSON observation file.")
    parser.add_argument("--start", required=True, help="Inclusive date-time bound.")
    parser.add_argument("--end", required=True, help="Exclusive date-time bound.")
    try:
        args = parser.parse_args(argv)
        start = _timestamp(args.start, "bounds")
        end = _timestamp(args.end, "bounds")
        rows = validate_rows(_decode_rows(_read_json(args.input)), start=start, end=end)
        window = _latest_window(rows)
    except ValidationError as error:
        errors.write(f"ERROR: {ERRORS[error.category]}\n")
        return 2

    report = {
        "count": len(rows),
        "window": None if window is None else {"start": window[0], "end": window[1]},
    }
    json.dump(report, output)
    output.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
