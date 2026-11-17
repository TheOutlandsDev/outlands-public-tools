"""Streaming readers and non-destructive schema inference for tabular inputs."""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from program_data.ingest.common import normalize_json_value

INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")


def data_format_for_path(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix == "csv":
        return "csv"
    if suffix == "json":
        return "json"
    if suffix in {"jsonl", "ndjson"}:
        return suffix
    raise ValueError(
        f"Unsupported tabular format {path.suffix!r}; use CSV, JSON, JSONL, or NDJSON"
    )


def declared_columns(path: Path) -> list[str]:
    """Return columns available before row iteration, when the format has them."""

    if data_format_for_path(path) != "csv":
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            headers = next(reader)
        except StopIteration:
            raise ValueError("CSV input is empty") from None
    _validate_headers(headers)
    return headers


def _validate_headers(headers: list[str]) -> None:
    if not headers:
        raise ValueError("Tabular input has no columns")
    if any(not header.strip() for header in headers):
        raise ValueError("Tabular input contains a blank column name")
    if len(set(headers)) != len(headers):
        raise ValueError("Tabular input contains duplicate column names")


def iter_tabular_records(path: Path) -> Iterator[dict[str, Any]]:
    data_format = data_format_for_path(path)
    if data_format == "csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(
                handle,
                restkey="__extra_columns__",
                restval=None,
            )
            headers = list(reader.fieldnames or [])
            _validate_headers(headers)
            for row_number, row in enumerate(reader, start=1):
                if row.get("__extra_columns__") is not None:
                    raise ValueError(
                        f"CSV row {row_number} contains more values than headers"
                    )
                row.pop("__extra_columns__", None)
                yield {
                    str(key): normalize_json_value(value)
                    for key, value in row.items()
                }
        return

    if data_format == "json":
        with path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        if isinstance(payload, Mapping) and isinstance(payload.get("records"), list):
            payload = payload["records"]
        elif isinstance(payload, Mapping):
            payload = [payload]
        if not isinstance(payload, list):
            raise ValueError("JSON input must be an object or an array of objects")
        for row_number, row in enumerate(payload, start=1):
            if not isinstance(row, Mapping):
                raise ValueError(f"JSON row {row_number} is not an object")
            yield {
                str(key): normalize_json_value(value)
                for key, value in row.items()
            }
        return

    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, Mapping):
                raise ValueError(f"JSONL line {line_number} is not an object")
            yield {
                str(key): normalize_json_value(value)
                for key, value in row.items()
            }


def inferred_value_type(value: Any) -> str:
    if value is None or value == "":
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "real"
    if isinstance(value, (dict, list)):
        return "json"
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.lower() in {"true", "false"}:
            return "boolean"
        if INTEGER_PATTERN.fullmatch(normalized):
            return "integer"
        try:
            float(normalized)
        except ValueError:
            return "text"
        return "real"
    return "text"


def update_type_profile(
    profile: dict[str, set[str]],
    row: Mapping[str, Any],
) -> None:
    for column in row:
        profile.setdefault(column, set())
    for column in profile:
        profile[column].add(inferred_value_type(row.get(column)))


def schema_from_profile(profile: Mapping[str, set[str]]) -> dict[str, Any]:
    columns: list[dict[str, Any]] = []
    for name, observed_types in profile.items():
        non_null_types = observed_types - {"null"}
        if not non_null_types:
            inferred = "null"
        elif non_null_types <= {"integer", "real"}:
            inferred = "real" if "real" in non_null_types else "integer"
        elif len(non_null_types) == 1:
            inferred = next(iter(non_null_types))
        else:
            inferred = "mixed"
        columns.append(
            {
                "name": name,
                "inferred_type": inferred,
                "nullable": not observed_types or "null" in observed_types,
                "observed_types": sorted(observed_types),
            }
        )
    return {"columns": columns}
