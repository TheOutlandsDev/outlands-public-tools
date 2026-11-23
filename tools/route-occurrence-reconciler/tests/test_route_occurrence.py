from pathlib import Path

import pytest

from route_occurrence import RouteReconciliationError, reconcile_occurrences
from route_reference import validate_route_dataset


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def dataset():
    return validate_route_dataset(EXAMPLES / "demo_routes.csv", EXAMPLES / "metadata.json")


def inventory(report):
    return {
        row["route_occurrence_key"]: row["source_row_sha256"]
        for row in report["missing_occurrences"]
    }


def test_route_loader_is_idempotent_and_preserves_239_occurrences() -> None:
    source = dataset()
    fingerprint = source.metadata.source_workbook_sha256

    initial = reconcile_occurrences(source, fingerprint, {})
    assert initial["missing_count"] == 239
    completed = inventory(initial)
    assert len(completed) == 239
    repeated = reconcile_occurrences(source, fingerprint, completed)
    assert repeated["missing_count"] == 0
    assert repeated["matched_count"] == 239


def test_route_loader_rejects_existing_row_that_differs_from_source() -> None:
    source = dataset()
    fingerprint = source.metadata.source_workbook_sha256
    completed = inventory(reconcile_occurrences(source, fingerprint, {}))
    first_key = next(iter(completed))
    completed[first_key] = "0" * 64

    with pytest.raises(RouteReconciliationError, match="does not match source"):
        reconcile_occurrences(source, fingerprint, completed)
