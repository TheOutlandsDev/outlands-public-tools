"""Fail-closed validation for a route-reference CSV and its metadata."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re


EXPECTED_HEADERS = (
    "RecordStatus",
    "RequestedFlowName",
    "RequestedVersion",
    "RootResolvedName",
    "RootResolvedVersion",
    "HierarchyDepth",
    "ParentFlowName",
    "ParentFlowVersion",
    "ParentSubflowPosition",
    "ComponentFlowName",
    "ComponentFlowVersion",
    "ComponentFlowType",
    "ComponentIsAlternate",
    "LogicalFlowPath",
    "RouteOrderKey",
    "StepPosition",
    "StepCorrelationId",
    "StepId",
    "StepName",
    "StepDisplayOrder",
    "AreaNames",
    "LayerName",
)

NULLABLE_HEADERS = {
    "ParentFlowName",
    "ParentFlowVersion",
    "ParentSubflowPosition",
    "LayerName",
}

METADATA_KEYS = {
    "accepted_revision",
    "controlled_csv_file",
    "controlled_csv_sha256",
    "expected_data_row_count",
    "expected_header_count",
    "source_extracted_on",
    "source_file",
    "source_query_file",
    "source_query_sha256",
    "source_workbook_sha256",
}


class RouteValidationError(ValueError):
    """A bounded source-contract failure with no secret-bearing details."""


@dataclass(frozen=True)
class RouteSourceMetadata:
    accepted_revision: str
    controlled_csv_file: str
    controlled_csv_sha256: str
    expected_data_row_count: int
    expected_header_count: int
    source_extracted_on: date
    source_file: str
    source_query_file: str
    source_query_sha256: str
    source_workbook_sha256: str


@dataclass(frozen=True)
class ValidatedRouteDataset:
    metadata: RouteSourceMetadata
    rows: tuple[dict[str, str], ...]


def route_occurrence_key(row: dict[str, str]) -> str:
    return "|".join(
        (
            row["RequestedFlowName"],
            row["RequestedVersion"],
            row["RouteOrderKey"],
        )
    )


def source_row_sha256(row: dict[str, str]) -> str:
    canonical = "\x1f".join(row[header] for header in EXPECTED_HEADERS)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _positive_integer(value: str, *, row_number: int, field: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RouteValidationError(
            f"row {row_number}: {field} must be an integer"
        ) from exc
    if parsed <= 0:
        raise RouteValidationError(
            f"row {row_number}: {field} must be positive"
        )
    return parsed


def _nonnegative_integer(value: str, *, row_number: int, field: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RouteValidationError(
            f"row {row_number}: {field} must be an integer"
        ) from exc
    if parsed < 0:
        raise RouteValidationError(
            f"row {row_number}: {field} must not be negative"
        )
    return parsed


def _load_metadata(metadata_path: Path) -> RouteSourceMetadata:
    try:
        raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RouteValidationError("route source metadata is unreadable") from exc

    if not isinstance(raw, dict) or set(raw) != METADATA_KEYS:
        raise RouteValidationError("route source metadata keys do not match the contract")
    for key in ("accepted_revision", "controlled_csv_file", "source_file", "source_query_file"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise RouteValidationError(f"metadata {key} must be nonblank text")
    if raw["expected_header_count"] != len(EXPECTED_HEADERS):
        raise RouteValidationError("metadata header count does not match the contract")
    if type(raw["expected_data_row_count"]) is not int or raw["expected_data_row_count"] < 0:
        raise RouteValidationError("metadata row count must be a nonnegative integer")

    for key in (
        "controlled_csv_sha256",
        "source_query_sha256",
        "source_workbook_sha256",
    ):
        value = raw[key]
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise RouteValidationError(f"metadata {key} must be a SHA-256 value")

    try:
        extracted_on = date.fromisoformat(raw["source_extracted_on"])
    except (TypeError, ValueError) as exc:
        raise RouteValidationError("source extraction date is invalid") from exc

    return RouteSourceMetadata(
        accepted_revision=raw["accepted_revision"],
        controlled_csv_file=raw["controlled_csv_file"],
        controlled_csv_sha256=raw["controlled_csv_sha256"].lower(),
        expected_data_row_count=raw["expected_data_row_count"],
        expected_header_count=raw["expected_header_count"],
        source_extracted_on=extracted_on,
        source_file=raw["source_file"],
        source_query_file=raw["source_query_file"],
        source_query_sha256=raw["source_query_sha256"].lower(),
        source_workbook_sha256=raw["source_workbook_sha256"].lower(),
    )


def validate_route_dataset(
    csv_path: Path,
    metadata_path: Path,
) -> ValidatedRouteDataset:
    metadata = _load_metadata(metadata_path)
    if csv_path.name != metadata.controlled_csv_file:
        raise RouteValidationError("controlled CSV filename does not match metadata")
    try:
        content = csv_path.read_bytes()
        if sha256(content).hexdigest() != metadata.controlled_csv_sha256:
            raise RouteValidationError("controlled CSV checksum does not match metadata")
        with StringIO(content.decode("utf-8"), newline="") as source:
            reader = csv.DictReader(source)
            if tuple(reader.fieldnames or ()) != EXPECTED_HEADERS:
                raise RouteValidationError("controlled CSV headers do not match exactly")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise RouteValidationError("controlled CSV is unreadable") from exc

    if len(rows) != metadata.expected_data_row_count:
        raise RouteValidationError(
            f"controlled CSV must contain {metadata.expected_data_row_count} data rows"
        )

    route_order_keys: set[tuple[str, str, str]] = set()
    route_positions: set[tuple[str, str, int]] = set()

    for row_number, row in enumerate(rows, start=2):
        if None in row:
            raise RouteValidationError(f"row {row_number}: extra CSV columns")
        for header in EXPECTED_HEADERS:
            value = row.get(header)
            if value is None or value == "":
                raise RouteValidationError(
                    f"row {row_number}: {header} must not be blank"
                )
            if "\x1f" in value:
                raise RouteValidationError(f"row {row_number}: a field contains the row hash separator")
            if value == "NULL" and header not in NULLABLE_HEADERS:
                raise RouteValidationError(
                    f"row {row_number}: {header} is not nullable"
                )

        if row["RecordStatus"] != "ROUTE_STEP":
            raise RouteValidationError(
                f"row {row_number}: RecordStatus must be ROUTE_STEP"
            )
        for field, prefix in (
            ("RouteOrderKey", "R:"),
            ("StepCorrelationId", "CID:"),
            ("StepId", "ID:"),
        ):
            if not row[field].startswith(prefix):
                raise RouteValidationError(
                    f"row {row_number}: {field} must begin with {prefix}"
                )

        flow_key = (row["RequestedFlowName"], row["RequestedVersion"])
        if any("|" in row[field] for field in ("RequestedFlowName", "RequestedVersion", "RouteOrderKey")):
            raise RouteValidationError(f"row {row_number}: an occurrence-key field contains a separator")

        order_key = (*flow_key, row["RouteOrderKey"])
        if order_key in route_order_keys:
            raise RouteValidationError(
                f"row {row_number}: duplicate route-order key within flow/version"
            )
        route_order_keys.add(order_key)

        step_position = _positive_integer(
            row["StepPosition"], row_number=row_number, field="StepPosition"
        )
        position_key = (*flow_key, step_position)
        if position_key in route_positions:
            raise RouteValidationError(
                f"row {row_number}: duplicate step position within flow/version"
            )
        route_positions.add(position_key)

        _nonnegative_integer(
            row["HierarchyDepth"], row_number=row_number, field="HierarchyDepth"
        )
        alternate = _nonnegative_integer(
            row["ComponentIsAlternate"],
            row_number=row_number,
            field="ComponentIsAlternate",
        )
        if alternate not in (0, 1):
            raise RouteValidationError(
                f"row {row_number}: ComponentIsAlternate must be 0 or 1"
            )
        _nonnegative_integer(
            row["StepDisplayOrder"],
            row_number=row_number,
            field="StepDisplayOrder",
        )
        if row["ParentSubflowPosition"] != "NULL":
            _positive_integer(
                row["ParentSubflowPosition"],
                row_number=row_number,
                field="ParentSubflowPosition",
            )

    return ValidatedRouteDataset(metadata=metadata, rows=tuple(rows))
