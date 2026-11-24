"""Validate a saved request to create an order."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class LotAllocation(BaseModel):
    lot_id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )
    circuits: int = Field(gt=0, le=100000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class _LotAllocationContract(BaseModel):
    lot_count: int | None = Field(default=None, ge=0, le=20)
    lot_allocations: tuple[LotAllocation, ...] | None = Field(
        default=None, max_length=20
    )

    @model_validator(mode="after")
    def validate_lot_allocations(self):
        if (self.lot_count is None) != (self.lot_allocations is None):
            raise ValueError("Lot count and lot allocations must be supplied together.")
        if self.lot_count is None:
            return self
        assert self.lot_allocations is not None
        if len(self.lot_allocations) != self.lot_count:
            raise ValueError("The number of lot allocations must match the selected lot count.")
        identities = [allocation.lot_id.casefold() for allocation in self.lot_allocations]
        if len(identities) != len(set(identities)):
            raise ValueError("Lot IDs must be unique within an order.")
        return self


class NewOrderRequest(_LotAllocationContract):
    lot_count: int = Field(default=0, ge=0, le=20)
    lot_allocations: tuple[LotAllocation, ...] = Field(default=(), max_length=20)
    source_sheet: str = Field(pattern=r"^[CP]$")
    order_date: date
    part_number: str = Field(min_length=1, max_length=40)
    purchase_order: str | None = Field(default=None, max_length=80)
    po_line: str | None = Field(default=None, max_length=30)
    quantity: int = Field(gt=0)
    requested_ship_date: date | None = None
    organization: str | None = Field(default=None, max_length=20)
    commit_date: date
    ship_quantity: int | None = Field(default=None, ge=0)
    ship_date: date | None = None
    dock_date: date | None = None
    work_request_flow: str | None = Field(default=None, max_length=256)
    customer_notes: str | None = Field(default=None, max_length=4000)
    planning_notes: str | None = Field(default=None, max_length=4000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InvalidAllocationTotal(ValueError):
    """The lot quantities disagree with the saved order or ship quantity."""


def _lot_allocation_values(
    *,
    lot_count: int | None,
    allocations: tuple[LotAllocation, ...] | None,
    order_quantity: int,
    ship_quantity: int | None,
) -> dict[str, str | None]:
    if lot_count is None:
        return {}
    assert allocations is not None
    total = sum(allocation.circuits for allocation in allocations)
    if total > order_quantity:
        raise InvalidAllocationTotal("Allocated circuits cannot exceed the order quantity.")
    if ship_quantity not in (None, 0) and total != ship_quantity:
        raise InvalidAllocationTotal(
            "Allocated circuits must equal the ship quantity when a ship quantity is present."
        )
    return {
        "lot_ids": " ".join(allocation.lot_id for allocation in allocations) or None,
        "lot_quantities": " ".join(str(allocation.circuits) for allocation in allocations) or None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="Path to a saved order request in JSON")
    args = parser.parse_args()
    try:
        data = args.request.read_bytes()
    except OSError:
        print("New order request could not be read.", file=sys.stderr)
        return 2
    try:
        order = NewOrderRequest.model_validate_json(data)
        _lot_allocation_values(
            lot_count=order.lot_count,
            allocations=order.lot_allocations,
            order_quantity=order.quantity,
            ship_quantity=order.ship_quantity,
        )
    except (ValidationError, InvalidAllocationTotal):
        print("Invalid new order request.", file=sys.stderr)
        return 2
    print(json.dumps({"valid": True, "lot_count": order.lot_count}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
