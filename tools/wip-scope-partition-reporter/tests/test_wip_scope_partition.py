from pathlib import Path

from wip_scope_partition import read_assignment, report_partition


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "assigned-wip.json"


def test_operations_center_separates_panel_wip_from_current_wip() -> None:
    panel_flex_prefixes = ("DEMO-PANEL-",)
    context = report_partition(read_assignment(EXAMPLE), panel_flex_prefixes).model_dump()

    assert context["wip_total"] >= 0
    assert context["panel_flex_excluded_lot_count"] > 0
    assert context["panel_flex_excluded_quantity"] > 0
    assert all(
        not row["lot_id"].upper().startswith(panel_flex_prefixes)
        for row in context["wip_rows"]
    )
