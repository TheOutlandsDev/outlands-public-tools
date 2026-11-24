from datetime import date

import pytest
from pydantic import ValidationError

from new_order_request import NewOrderRequest


def test_new_order_contract_defaults_to_no_lots_and_rejects_unknown_fields() -> None:
    created = NewOrderRequest(
        source_sheet="C",
        order_date=date(2030, 8, 17),
        part_number="DEMO-PART-1",
        quantity=300,
        commit_date=date(2030, 8, 28),
    )
    assert created.lot_count == 0
    assert created.lot_allocations == ()
    with pytest.raises(ValidationError):
        NewOrderRequest(
            source_sheet="C",
            order_date=date(2030, 8, 17),
            part_number="DEMO-PART-1",
            quantity=300,
            commit_date=date(2030, 8, 28),
            unexpected="rejected",
        )
