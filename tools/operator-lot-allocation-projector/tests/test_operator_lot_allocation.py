from pathlib import Path

from operator_lot_allocation import (
    OperationsSnapshot,
    OrderNeedsSnapshot,
    PlanningRules,
    project_allocations,
    read_snapshot,
)


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
OS_SHA = "a" * 64
WIP_SHA = "b" * 64


def test_authoritative_operator_projection_uses_current_os_and_matching_wip() -> None:
    result = project_allocations(
        read_snapshot(EXAMPLES / "order-needs.json", OrderNeedsSnapshot),
        read_snapshot(EXAMPLES / "operations.json", OperationsSnapshot),
        read_snapshot(EXAMPLES / "planning-rules.json", PlanningRules),
    )

    assert result.source_mode == "Authoritative current O&S and accepted WIP"
    assert result.source.sha256 == OS_SHA
    assert result.source.wip_sha256 == WIP_SHA
    assert result.current_inputs.open_orders == 3
    assert result.current_inputs.open_demand == 550
    assert result.planning.demand == 550
    assert result.planning.covered == 360
    assert result.planning.uncovered == 190
    assert result.planning.recommended_starts == 140
    assert len(result.orders) == 3
    assert len(result.actions) == 2
    assert sum(row.allocated_quantity for row in result.actions) == 360
    assert all(row.part_number != "DEMO-EXCLUDED" for row in result.orders)
    assert "Outside configured ranking horizon" not in result.available_risks
    assert result.warnings == ()
