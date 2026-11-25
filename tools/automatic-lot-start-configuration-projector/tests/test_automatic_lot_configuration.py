"""Original shadow-projection parity assertions with fictional local rules and an order."""

from datetime import date
from pathlib import Path

from automatic_lot_configuration import (
    AutomaticLotStartConfiguration,
    project_automatic_lot_start_configuration,
    read_policy,
)
from reference_ledger import AutomaticLotStartLedger, OSOrderState


ROOT = Path(__file__).resolve().parents[1]


def test_automatic_shadow_projection_preserves_exact_calculation_behavior() -> None:
    policy = read_policy(ROOT / "examples/policy.json")
    legacy = AutomaticLotStartConfiguration.model_validate_json(
        (ROOT / "examples/reference-configuration.json").read_bytes()
    )
    projected = project_automatic_lot_start_configuration(policy)

    legacy_products = {
        item.modality: (
            item.part_number,
            item.lot_prefix,
            item.start_quantity,
            item.lead_time_days,
        )
        for item in legacy.configured_products
    }
    projected_products = {
        item.modality: (
            item.part_number,
            item.lot_prefix,
            item.start_quantity,
            item.lead_time_days,
        )
        for item in projected.configured_products
    }
    assert projected_products == legacy_products
    assert projected.replenishment_factor == legacy.replenishment_factor == "1.00"

    order = OSOrderState(
        order_id="demo-order-001",
        row_version=1,
        source_revision_sha256="a" * 64,
        part_number="DEMO-PART-01",
        ordered_quantity=36,
        accepted_ship_quantity=0,
        requested_ship_date=date(2030, 9, 30),
    )
    legacy_result = AutomaticLotStartLedger(legacy).ingest(order)
    projected_result = AutomaticLotStartLedger(projected).ingest(order)
    assert projected_result == legacy_result
    assert projected_result.event is not None
    assert projected_result.event.current_recommended_lots == 1
