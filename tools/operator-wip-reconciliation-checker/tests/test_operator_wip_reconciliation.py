from pathlib import Path

from operator_wip_reconciliation import (
    OperationsSnapshot,
    OrderNeedsSnapshot,
    read_snapshot,
    reconcile_wip,
)


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
OS_SHA = "a" * 64
WIP_SHA = "b" * 64


def test_authoritative_operator_projection_uses_current_os_and_matching_wip() -> None:
    order_needs = read_snapshot(EXAMPLES / "order-needs.json", OrderNeedsSnapshot)
    operations = read_snapshot(EXAMPLES / "operations.json", OperationsSnapshot)
    result = reconcile_wip(order_needs, operations)

    assert result.source.sha256 == OS_SHA
    assert result.source.wip_sha256 == WIP_SHA
    assert sum(result.eligible_wip_by_product.values()) == 360
    assert result.eligible_wip_by_product == {"DEMO-A": 240, "DEMO-B": 120, "DEMO-ZERO": 0}
