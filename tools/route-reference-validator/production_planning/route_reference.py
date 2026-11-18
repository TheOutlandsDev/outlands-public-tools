"""Fail-closed validation for the accepted demo route-reference dataset."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
from pathlib import Path


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

EXPECTED_ROUTE_COUNTS = {
    ("Demo Panel", "7"): 38,
    ("Demo Panel Extended", "9"): 40,
    ("Demo Circuit", "6"): 42,
    ("Demo Assembly", "17"): 111,
    ("Demo Inspection", "7"): 8,
}

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


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def nullable_value(value: str) -> str | None:
    return None if value == "NULL" else value


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

    if set(raw) != METADATA_KEYS:
        raise RouteValidationError("route source metadata keys do not match the contract")
    if raw["accepted_revision"] != "3":
        raise RouteValidationError("accepted route source revision must be 3")
    if raw["expected_header_count"] != len(EXPECTED_HEADERS):
        raise RouteValidationError("metadata header count does not match the contract")
    if raw["expected_data_row_count"] != 239:
        raise RouteValidationError("metadata row count does not match the contract")

    for key in (
        "controlled_csv_sha256",
        "source_query_sha256",
        "source_workbook_sha256",
    ):
        value = raw[key]
        if not isinstance(value, str) or len(value) != 64:
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
    if file_sha256(csv_path) != metadata.controlled_csv_sha256:
        raise RouteValidationError("controlled CSV checksum does not match metadata")

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if tuple(reader.fieldnames or ()) != EXPECTED_HEADERS:
                raise RouteValidationError("controlled CSV headers do not match exactly")
            rows = list(reader)
    except (OSError, csv.Error) as exc:
        raise RouteValidationError("controlled CSV is unreadable") from exc

    if len(rows) != metadata.expected_data_row_count:
        raise RouteValidationError(
            f"controlled CSV must contain {metadata.expected_data_row_count} data rows"
        )

    route_counts: dict[tuple[str, str], int] = {}
    route_order_keys: set[tuple[str, str, str]] = set()
    route_positions: set[tuple[str, str, int]] = set()

    for row_number, row in enumerate(rows, start=2):
        for header in EXPECTED_HEADERS:
            value = row.get(header)
            if value is None or value == "":
                raise RouteValidationError(
                    f"row {row_number}: {header} must not be blank"
                )
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
        route_counts[flow_key] = route_counts.get(flow_key, 0) + 1

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

    if route_counts != EXPECTED_ROUTE_COUNTS:
        raise RouteValidationError("flow/version occurrence counts do not match")

    mr_rows = [
        row
        for row in rows
        if row["RequestedFlowName"] == "Demo Circuit"
        and row["RequestedVersion"] == "6"
        and row["StepName"] == "Repeated_Check"
    ]
    mr_actual = {
        (row["StepPosition"], row["StepId"], row["StepCorrelationId"])
        for row in mr_rows
    }
    mr_expected = {
        ("15", "ID:DEMO-STEP-REPEAT", "CID:15"),
        ("26", "ID:DEMO-STEP-REPEAT", "CID:20"),
        ("28", "ID:DEMO-STEP-REPEAT", "CID:22"),
    }
    if mr_actual != mr_expected:
        raise RouteValidationError("Demo repeated-occurrence contract failed")

    return ValidatedRouteDataset(metadata=metadata, rows=tuple(rows))
