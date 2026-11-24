import pytest
from pydantic import ValidationError

from order_lot_allocation import (
    AllocationError,
    LotAllocation,
    OrderLotAllocation,
    _lot_allocation_values,
)


def test_lot_allocation_requires_exact_unique_positive_rows() -> None:
    valid = OrderLotAllocation(
        order_quantity=300,
        lot_count=2,
        lot_allocations=(
            LotAllocation(lot_id="DEMO-LOT-01", circuits=160),
            LotAllocation(lot_id="DEMO-LOT-02", circuits=140),
        ),
    )
    assert valid.lot_count == 2

    with pytest.raises(ValidationError):
        OrderLotAllocation(
            order_quantity=300,
            lot_count=2,
            lot_allocations=(LotAllocation(lot_id="DEMO-LOT-01", circuits=300),),
        )
    with pytest.raises(ValidationError):
        OrderLotAllocation(
            order_quantity=300,
            lot_count=2,
            lot_allocations=(
                LotAllocation(lot_id="DEMO-LOT-01", circuits=150),
                LotAllocation(lot_id="demo-lot-01", circuits=150),
            ),
        )


def test_lot_allocation_conserves_order_and_ship_quantities() -> None:
    allocations = (
        LotAllocation(lot_id="DEMO-LOT-01", circuits=160),
        LotAllocation(lot_id="DEMO-LOT-02", circuits=140),
    )
    assert _lot_allocation_values(
        lot_count=2,
        allocations=allocations,
        order_quantity=300,
        ship_quantity=300,
    ) == {
        "lot_ids": "DEMO-LOT-01 DEMO-LOT-02",
        "lot_quantities": "160 140",
    }
    with pytest.raises(AllocationError):
        _lot_allocation_values(
            lot_count=2,
            allocations=allocations,
            order_quantity=299,
            ship_quantity=None,
        )
    with pytest.raises(AllocationError):
        _lot_allocation_values(
            lot_count=2,
            allocations=allocations,
            order_quantity=300,
            ship_quantity=299,
        )
