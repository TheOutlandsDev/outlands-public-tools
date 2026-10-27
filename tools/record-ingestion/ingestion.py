"""Bounded in-memory CSV/JSONL ingestion; no filesystem or external services."""
from dataclasses import dataclass
import csv
import io
import json
import math
import re

MAX_BYTES = 65536
MAX_ROWS = 256
MAX_SERIES = 32
MAX_PERIOD = 1000000
MAX_VALUE = 1000000000
SERIES = re.compile(r"[a-z][a-z0-9_-]{0,31}")
FIELDS = {"series", "period", "value"}


class ReferenceError(ValueError):
    """Fixed codes only; no payload, field value or native exception message."""


@dataclass(frozen=True)
class Point:
    series: str
    period: int
    value: float

    def __post_init__(self):
        if type(self.series) is not str or SERIES.fullmatch(self.series) is None:
            raise ReferenceError("SERIES_INVALID")
        if type(self.period) is not int or not 0 <= self.period <= MAX_PERIOD:
            raise ReferenceError("PERIOD_INVALID")
        if type(self.value) not in (int, float):
            raise ReferenceError("VALUE_INVALID")
        if not -MAX_VALUE <= self.value <= MAX_VALUE or not math.isfinite(self.value):
            raise ReferenceError("VALUE_INVALID")
        value = float(self.value)
        object.__setattr__(self, "value", 0.0 if value == 0 else value)


@dataclass(frozen=True)
class Issue:
    record: int
    code: str


@dataclass(frozen=True)
class Batch:
    records: tuple[Point, ...]
    issues: tuple[Issue, ...]
    duplicates: int

    @property
    def ok(self):
        return bool(self.records) and not self.issues

    def require_clean(self):
        if not self.ok:
            raise ReferenceError("BATCH_REVIEW_REQUIRED")
        return self.records


def _text(value):
    if type(value) is not str or "\x00" in value:
        raise ReferenceError("INPUT_TEXT_INVALID")
    if len(value) > MAX_BYTES:
        raise ReferenceError("INPUT_BYTE_LIMIT")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        raise ReferenceError("INPUT_TEXT_INVALID") from None
    if size > MAX_BYTES:
        raise ReferenceError("INPUT_BYTE_LIMIT")
    return value.removeprefix("\ufeff")


def _point(value, csv_values=False):
    if type(value) is not dict or set(value) != FIELDS:
        raise ReferenceError("ROW_SCHEMA_INVALID")
    series = value["series"]
    if type(series) is not str or not series.isascii():
        raise ReferenceError("SERIES_INVALID")
    series = series.strip().lower()
    period, number = value["period"], value["value"]
    if csv_values:
        if type(period) is not str or re.fullmatch(r"[0-9]{1,7}", period.strip()) is None:
            raise ReferenceError("PERIOD_INVALID")
        period = int(period.strip())
        try:
            number = float(number)
        except (ValueError, TypeError, OverflowError):
            raise ReferenceError("VALUE_INVALID") from None
    return Point(series, period, number)


def _collect(rows, csv_values=False, offset=0):
    records, issues, series = {}, [], set()
    duplicates = 0
    for index, value in enumerate(rows, 1):
        if index > MAX_ROWS:
            raise ReferenceError("INPUT_RECORD_LIMIT")
        try:
            if isinstance(value, ReferenceError):
                raise value
            point = _point(value, csv_values)
            if point.series not in series and len(series) >= MAX_SERIES:
                raise ReferenceError("SERIES_COUNT_LIMIT")
            key = point.series, point.period
            if key in records:
                if records[key] != point:
                    raise ReferenceError("RECORD_CONFLICT")
                duplicates += 1
            else:
                records[key] = point
                series.add(point.series)
        except ReferenceError as error:
            issues.append(Issue(index + offset, str(error)))
    if not records and not issues:
        issues.append(Issue(0, "EMPTY_INPUT"))
    return Batch(tuple(records[key] for key in sorted(records)), tuple(issues), duplicates)


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReferenceError("JSON_DUPLICATE_KEY")
        value[key] = item
    return value


def _constant(value):
    raise ReferenceError("JSON_NONSTANDARD_NUMBER")


def ingest_jsonl(text):
    """Return typed valid records and fixed diagnostics; require_clean gates use."""
    text = _text(text)
    def rows():
        lines = text.split("\n")
        if lines[-1] == "":
            lines.pop()
        for line in lines:
            try:
                if not line.strip():
                    raise ReferenceError("EMPTY_RECORD")
                yield json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
            except ReferenceError as error:
                yield ReferenceError(str(error))
            except (ValueError, RecursionError):
                yield ReferenceError("JSON_RECORD_INVALID")
    return _collect(rows())


def ingest_csv(text):
    """Require exact header order; numeric conversion is explicit for CSV."""
    text = _text(text)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        if next(reader, None) != ["series", "period", "value"]:
            raise ReferenceError("CSV_HEADER_INVALID")
        rows = (dict(zip(("series", "period", "value"), row)) if len(row) == 3
                else ReferenceError("ROW_SCHEMA_INVALID") for row in reader)
        return _collect(rows, csv_values=True, offset=1)
    except csv.Error:
        raise ReferenceError("CSV_SYNTAX_INVALID") from None
