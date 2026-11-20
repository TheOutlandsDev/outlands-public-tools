"""Cross-bucket quantity and rejection safeguards."""

from pathlib import Path

import pytest

from kanban_assignment import KanbanAssignmentError, SavedAssignment, assign_wip_to_kanbans, preflight_wip_assignment


def test_conservation_and_order_independence():
    saved = example()
    result = assign_wip_to_kanbans(saved.records, saved.configuration)
    reversed_result = assign_wip_to_kanbans(saved.records[::-1], saved.configuration)
    assert result == reversed_result
    assert result.kanban_counts == {1: 1, 5: 1}
    assert result.raw_wip_total == 200
    assert result.normalized_wip_total == 160
    assert result.completed_total == 20
    assert result.total_parts == 180


def test_duplicate_rows_fail_without_partial_assignment():
    saved = example()
    records = saved.records + (saved.records[0],)
    result = preflight_wip_assignment(records, saved.configuration)
    assert result.status == "FAIL"
    assert result.rejected_record_count == 2
    assert result.assignable_record_count == 1
    assert {issue.code for issue in result.issues} == {"DUPLICATE_SOURCE_ROW", "DUPLICATE_LOT_ID"}
    with pytest.raises(KanbanAssignmentError, match="DUPLICATE_SOURCE_ROW"):
        assign_wip_to_kanbans(records, saved.configuration)


def example():
    path = Path(__file__).resolve().parents[1] / "examples" / "assignment.json"
    return SavedAssignment.model_validate_json(path.read_bytes())
