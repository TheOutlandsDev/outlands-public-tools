"""Original direct order-rule tests using a fictional rule table."""

from datetime import date
from pathlib import Path

from order_status import SavedInput, calculated_lead_time_date, calculated_order_status, modality_for_part


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "orders.json"
RULES = SavedInput.model_validate_json(EXAMPLE.read_bytes()).rules


def test_shipping_evidence_precedes_dock_date() -> None:
    status = calculated_order_status(
        carrier="Fictional carrier",
        tracking_number="FICT-TRACK-01",
        ship_date=date(2030, 1, 27),
        ship_quantity=300,
        shipment_number="FICT-TRACK-01",
        dock_date=date(2030, 1, 21),
    )

    assert status == "Shipped"


def test_lead_time_is_recomputed_from_governed_part_rules() -> None:
    assert calculated_lead_time_date("DEMO-01", date(2030, 1, 1), RULES) == date(
        2030, 3, 5
    )
    assert calculated_lead_time_date(
        "DEMO-ALT", date(2030, 1, 1), RULES
    ) == date(2030, 3, 26)
    assert modality_for_part("DEMO-ALT", RULES) == "FAMILY-02"
