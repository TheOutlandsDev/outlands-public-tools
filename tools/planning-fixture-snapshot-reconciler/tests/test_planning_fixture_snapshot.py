import json
from copy import deepcopy
from pathlib import Path

import pytest

from planning_fixture_snapshot import FlexFixtureLoadError, _canonical_rows, reconcile_fixture_snapshot


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def approved_fixture():
    return json.loads((EXAMPLES / "approved-fixture.json").read_bytes())


def empty_snapshot():
    return json.loads((EXAMPLES / "empty-snapshot.json").read_bytes())


def test_approved_fixture_loads_exactly_once_and_is_idempotent() -> None:
    expected = approved_fixture()
    empty = reconcile_fixture_snapshot(expected, empty_snapshot())
    assert empty["status"] == "empty"
    assert empty["expected_row_count"] == 7 and empty["stored_row_count"] == 0
    assert [item["expected"] for item in empty["tables"].values()] == [1, 2, 4]

    stored = deepcopy(expected)
    accepted = reconcile_fixture_snapshot(expected, stored)
    assert accepted["status"] == "match" and accepted["stored_row_count"] == 7
    assert reconcile_fixture_snapshot(expected, stored) == accepted
    assert stored == expected


def test_partial_database_state_fails_closed_without_more_inserts() -> None:
    expected = approved_fixture()
    stored = empty_snapshot()
    stored["flex_planning_orders"] = expected["flex_planning_orders"][:1]
    before = deepcopy(stored)
    with pytest.raises(FlexFixtureLoadError, match="incomplete or differs"):
        reconcile_fixture_snapshot(expected, stored)
    assert stored == before


def test_changed_database_value_fails_closed() -> None:
    expected = approved_fixture()
    stored = deepcopy(expected)
    stored["flex_planning_wip"][0]["quantity"] += 1
    before = deepcopy(stored)
    with pytest.raises(FlexFixtureLoadError, match="incomplete or differs"):
        reconcile_fixture_snapshot(expected, stored)
    assert stored == before


def test_clickhouse_fixed_strings_and_row_order_are_normalized() -> None:
    rows = [
        {"case_id": "case", "lot_id": "B", "fixture_sha256": b"abc"},
        {"case_id": "case", "lot_id": "A", "fixture_sha256": b"def"},
    ]

    assert _canonical_rows("flex_planning_wip", rows) == [
        {"case_id": "case", "lot_id": "A", "fixture_sha256": "def"},
        {"case_id": "case", "lot_id": "B", "fixture_sha256": "abc"},
    ]
