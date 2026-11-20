"""Original comparison assertions from the candidate review test."""

from pathlib import Path

import pytest

from order_revisions import SavedSnapshot, compare_orders


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def snapshot(name):
    return SavedSnapshot.model_validate_json((EXAMPLES / f"{name}.json").read_bytes()).orders


def test_identical_candidate_has_no_changes():
    active = snapshot("active")
    comparison = compare_orders(active, active)
    assert comparison.added_count == 0
    assert comparison.removed_count == 0
    assert comparison.changed_count == 0


def test_additions_removals_changes_and_row_moves():
    result = compare_orders(snapshot("active"), snapshot("candidate"))
    assert (result.added_count, result.removed_count, result.changed_count) == (2, 2, 2)
    assert [row.key.split("|")[1] for row in result.added] == ["DEMO-06", "DEMO-07"]
    assert [row.key.split("|")[1] for row in result.removed] == ["DEMO-04", "DEMO-05"]
    assert [(row.key.split("|")[1], row.changed_fields) for row in result.changed] == [
        ("DEMO-01", ("carrier", "quantity")),
        ("DEMO-02", ("ship_quantity",)),
    ]
    active = snapshot("active")
    moved = tuple(row.model_copy(update={"source_row": row.source_row + 80}) for row in active)
    assert compare_orders(active, moved).changed_count == 0


def test_duplicate_identity_is_refused_on_both_sides():
    active = snapshot("active")
    duplicate = active[0].model_copy(update={"source_row": 77})
    for left, right in ((active + (duplicate,), active), (active, active + (duplicate,))):
        with pytest.raises(ValueError, match="Duplicate order identity"):
            compare_orders(left, right)


def test_limit_preserves_full_counts():
    active, candidate = snapshot("active"), snapshot("candidate")
    complete = compare_orders(active, candidate)
    limited = compare_orders(active, candidate, limit=1)
    assert (limited.added_count, limited.removed_count, limited.changed_count) == (2, 2, 2)
    assert limited.added == complete.added[:1]
    assert limited.removed == complete.removed[:1]
    assert limited.changed == complete.changed[:1]
    assert limited.truncated
