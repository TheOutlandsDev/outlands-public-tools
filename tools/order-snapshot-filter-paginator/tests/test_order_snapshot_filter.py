from datetime import date
from pathlib import Path

import pytest

from order_snapshot_filter import SavedSnapshot, filter_order_snapshot


def fictional_snapshot():
    example = Path(__file__).resolve().parents[1] / "examples" / "fictional-orders.json"
    return SavedSnapshot.model_validate_json(example.read_bytes())


def test_date_range_filter_supports_governed_date_fields() -> None:
    grid = filter_order_snapshot(
        fictional_snapshot(),
        date_field="commit_date",
        date_from=date(2026, 8, 21),
        date_to=date(2026, 8, 21),
        page=1,
        page_size=10,
    )
    assert grid.filtered_rows == 1
    assert grid.rows[0].part_number == "DEMO-1"
    assert set(fictional_snapshot().available_modalities).issubset(set(grid.available_modalities))

    with pytest.raises(ValueError):
        filter_order_snapshot(
            fictional_snapshot(),
            date_from=date(2026, 8, 22),
            date_to=date(2026, 8, 21),
            page=1,
            page_size=10,
        )


def test_snapshot_preserves_revision_search_and_row_version() -> None:
    grid = filter_order_snapshot(
        fictional_snapshot(), search="watch", sheet="P", page=1, page_size=10
    )

    assert grid.revision_sha256 == "a" * 64
    assert grid.total_rows == 3
    assert grid.filtered_rows == 1
    assert grid.rows[0].row_version == 1
