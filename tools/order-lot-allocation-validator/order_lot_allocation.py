"""Validate one saved order's lot allocations and print the paired fields."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class AllocationError(ValueError):
    """The per-order allocation quantities do not reconcile."""


class LotAllocation(BaseModel):
    lot_id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )
    circuits: int = Field(gt=0, le=100000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OrderLotAllocation(BaseModel):
    lot_count: int | None = Field(default=None, ge=0, le=20)
    lot_allocations: tuple[LotAllocation, ...] | None = Field(
        default=None, max_length=20
    )

    order_quantity: int = Field(gt=0)
    ship_quantity: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")

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
        raise AllocationError("Allocated circuits cannot exceed the order quantity.")
    if ship_quantity not in (None, 0) and total != ship_quantity:
        raise AllocationError(
            "Allocated circuits must equal the ship quantity when a ship quantity is present."
        )
    return {
        "lot_ids": " ".join(allocation.lot_id for allocation in allocations) or None,
        "lot_quantities": " ".join(str(allocation.circuits) for allocation in allocations) or None,
    }


def allocation_fields(request: OrderLotAllocation) -> dict[str, str | None]:
    return _lot_allocation_values(
        lot_count=request.lot_count,
        allocations=request.lot_allocations,
        order_quantity=request.order_quantity,
        ship_quantity=request.ship_quantity,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("order", type=Path, help="Saved order and lot allocation JSON")
    args = parser.parse_args()
    try:
        order = OrderLotAllocation.model_validate_json(args.order.read_bytes())
        fields = allocation_fields(order)
    except ValidationError as error:
        message = error.errors(include_input=False, include_url=False, include_context=False)[0]["msg"]
        print(f"Invalid order lot allocation. {message}", file=sys.stderr)
        return 2
    except AllocationError as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError:
        print("The saved order could not be read.", file=sys.stderr)
        return 2
    print(json.dumps(fields, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
