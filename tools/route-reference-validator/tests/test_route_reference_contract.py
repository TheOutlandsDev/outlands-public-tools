import csv
from hashlib import sha256
import json
from pathlib import Path

import pytest

from production_planning.route_reference import (
    EXPECTED_HEADERS,
    EXPECTED_ROUTE_COUNTS,
    RouteValidationError,
    validate_route_dataset,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIRECTORY = PROJECT_ROOT / "data" / "route_reference"
CSV_PATH = DATA_DIRECTORY / "demo_routes.csv"
METADATA_PATH = DATA_DIRECTORY / "metadata.json"


def _source_rows() -> list[dict[str, str]]:
    with CSV_PATH.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _candidate(
    tmp_path: Path,
    rows: list[dict[str, str]],
    headers: tuple[str, ...] = EXPECTED_HEADERS,
) -> tuple[Path, Path]:
    csv_path = tmp_path / "candidate.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(headers))
        writer.writeheader()
        writer.writerows(rows)

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    metadata["controlled_csv_file"] = csv_path.name
    metadata["controlled_csv_sha256"] = sha256(csv_path.read_bytes()).hexdigest()
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return csv_path, metadata_path


def test_accepted_route_source_contract_passes_exactly() -> None:
    dataset = validate_route_dataset(CSV_PATH, METADATA_PATH)

    assert len(EXPECTED_HEADERS) == 22
    assert len(dataset.rows) == 239
    assert dataset.metadata.source_file == "fictional-route-export.xlsx"
    assert dataset.metadata.accepted_revision == "3"
    assert dataset.metadata.controlled_csv_sha256 == (
        "85b0d027b07ff1eac1119e593504bc40c509b03afb2c88c8de7b6504257e4183"
    )


def test_flow_versions_counts_and_identifier_prefixes_are_preserved() -> None:
    dataset = validate_route_dataset(CSV_PATH, METADATA_PATH)
    counts: dict[tuple[str, str], int] = {}
    for row in dataset.rows:
        key = (row["RequestedFlowName"], row["RequestedVersion"])
        counts[key] = counts.get(key, 0) + 1
        assert isinstance(row["RequestedVersion"], str)
        assert row["StepId"].startswith("ID:")
        assert row["StepCorrelationId"].startswith("CID:")
        assert row["RouteOrderKey"].startswith("R:")

    assert counts == EXPECTED_ROUTE_COUNTS


def test_repeated_step_preserves_all_three_occurrences() -> None:
    dataset = validate_route_dataset(CSV_PATH, METADATA_PATH)
    records = [
        row
        for row in dataset.rows
        if row["RequestedFlowName"] == "Demo Circuit"
        and row["RequestedVersion"] == "6"
        and row["StepName"] == "Repeated_Check"
    ]

    assert [row["StepPosition"] for row in records] == ["15", "26", "28"]
    assert {row["StepId"] for row in records} == {"ID:DEMO-STEP-REPEAT"}
    assert [row["StepCorrelationId"] for row in records] == [
        "CID:15",
        "CID:20",
        "CID:22",
    ]


def test_validator_rejects_header_drift(tmp_path: Path) -> None:
    rows = _source_rows()
    bad_headers = (*EXPECTED_HEADERS[:-1], "UnexpectedHeader")
    rows = [
        {
            **{key: value for key, value in row.items() if key != "LayerName"},
            "UnexpectedHeader": row["LayerName"],
        }
        for row in rows
    ]
    csv_path, metadata_path = _candidate(tmp_path, rows, bad_headers)

    with pytest.raises(RouteValidationError, match="headers"):
        validate_route_dataset(csv_path, metadata_path)


def test_validator_rejects_blank_required_value(tmp_path: Path) -> None:
    rows = _source_rows()
    rows[0]["StepId"] = ""
    csv_path, metadata_path = _candidate(tmp_path, rows)

    with pytest.raises(RouteValidationError, match="StepId must not be blank"):
        validate_route_dataset(csv_path, metadata_path)


def test_validator_rejects_missing_identifier_prefix(tmp_path: Path) -> None:
    rows = _source_rows()
    rows[0]["StepId"] = "DEMO-MISSING-PREFIX"
    csv_path, metadata_path = _candidate(tmp_path, rows)

    with pytest.raises(RouteValidationError, match="StepId must begin with ID:"):
        validate_route_dataset(csv_path, metadata_path)


def test_validator_rejects_duplicate_position(tmp_path: Path) -> None:
    rows = _source_rows()
    rows[1]["StepPosition"] = rows[0]["StepPosition"]
    csv_path, metadata_path = _candidate(tmp_path, rows)

    with pytest.raises(RouteValidationError, match="duplicate step position"):
        validate_route_dataset(csv_path, metadata_path)
