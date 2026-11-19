from dataclasses import dataclass, replace
from datetime import date

import pytest

from lot_identity import (
    LastLotMapping,
    AutomaticLotIdentityError,
    build_automatic_lot_identity_rows,
)


@dataclass(frozen=True)
class QueueState:
    modality: str = "DEMO-A"
    part_number: str = "DEMO-PART-A"
    lot_prefix: str = "FIC-A"
    recommended_lot_count: int = 2
    recommended_start_by: date | None = None
    queue_status: str = "ACTIVE"


def queue_state(**updates) -> QueueState:
    return replace(QueueState(), **updates)


def mapping(**updates) -> LastLotMapping:
    values = {
        "product": "DEMO-PART-A",
        "material_template": "DEMO-TEMPLATE-A",
        "prefix": "FIC-A",
        "last_lot_started": "FIC-AAABX",
        "next_lot_to_start": "FIC-AAABY",
    }
    values.update(updates)
    return LastLotMapping.model_validate(values)


def test_queue_is_joined_to_product_and_sequential_lot_identities() -> None:
    rows = build_automatic_lot_identity_rows((queue_state(),), (mapping(),))

    assert rows[0].modality == "DEMO-A"
    assert rows[0].product_group == "DEMO-PART-A"
    assert rows[0].material_template == "DEMO-TEMPLATE-A"
    assert rows[0].next_lot_to_start == "FIC-AAABY"
    assert rows[0].recommended_lot_ids == ("FIC-AAABY", "FIC-AAABZ")


def test_product_mismatch_fails_closed() -> None:
    with pytest.raises(AutomaticLotIdentityError):
        build_automatic_lot_identity_rows(
            (queue_state(part_number="DEMO-OTHER-PART"),),
            (mapping(),),
        )


def test_workbook_next_lot_mismatch_fails_closed() -> None:
    with pytest.raises(AutomaticLotIdentityError):
        build_automatic_lot_identity_rows(
            (queue_state(),),
            (mapping(next_lot_to_start="FIC-AAACB"),),
        )


def test_unqueued_mapping_remains_a_reference_row() -> None:
    rows = build_automatic_lot_identity_rows((), (mapping(),))

    assert rows[0].queue_status == "REFERENCE_ONLY"
    assert rows[0].recommended_lot_ids == ()
