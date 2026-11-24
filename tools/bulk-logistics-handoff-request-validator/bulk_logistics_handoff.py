"""Validate a saved bulk logistics handoff request and report its counts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class HandoffLotCommand(BaseModel):
    lot_id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )
    quantity: int = Field(gt=0, le=100000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReadyOrderCommand(BaseModel):
    row_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_order_version: int = Field(gt=0)
    lots: tuple[HandoffLotCommand, ...] = Field(min_length=1, max_length=20)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_unique_lots(self) -> "ReadyOrderCommand":
        identities = [lot.lot_id.casefold() for lot in self.lots]
        if len(identities) != len(set(identities)):
            raise ValueError("Each selected lot may appear only once per order.")
        return self


class BulkReadyCommand(BaseModel):
    orders: tuple[ReadyOrderCommand, ...] = Field(min_length=1, max_length=25)
    comment: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_batch(self) -> "BulkReadyCommand":
        row_ids = [order.row_id for order in self.orders]
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("Each selected order may appear only once.")
        if sum(len(order.lots) for order in self.orders) > 100:
            raise ValueError("A handoff batch may contain at most 100 lots.")
        return self


class ReturnLotCommand(BaseModel):
    lot_id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )
    expected_state_version: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReturnOrderCommand(BaseModel):
    row_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_order_version: int = Field(gt=0)
    lots: tuple[ReturnLotCommand, ...] = Field(min_length=1, max_length=20)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_unique_lots(self) -> "ReturnOrderCommand":
        identities = [lot.lot_id.casefold() for lot in self.lots]
        if len(identities) != len(set(identities)):
            raise ValueError("Each returned lot may appear only once per order.")
        return self


class BulkReturnCommand(BaseModel):
    orders: tuple[ReturnOrderCommand, ...] = Field(min_length=1, max_length=25)
    reason: str = Field(min_length=3, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_batch(self) -> "BulkReturnCommand":
        row_ids = [order.row_id for order in self.orders]
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("Each selected order may appear only once.")
        if sum(len(order.lots) for order in self.orders) > 100:
            raise ValueError("A handoff batch may contain at most 100 lots.")
        return self


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("ready", "return"), help="Type of saved request")
    parser.add_argument("request", type=Path, help="Saved request in JSON")
    args = parser.parse_args()
    request_type = BulkReadyCommand if args.action == "ready" else BulkReturnCommand
    try:
        request = request_type.model_validate_json(args.request.read_bytes())
    except ValidationError as error:
        message = error.errors(include_input=False, include_context=False, include_url=False)[0]["msg"]
        print(f"Invalid bulk handoff request. {message}", file=sys.stderr)
        return 2
    except OSError:
        print("The saved request could not be read.", file=sys.stderr)
        return 2

    print(json.dumps({
        "action": args.action,
        "order_count": len(request.orders),
        "lot_count": sum(len(order.lots) for order in request.orders),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
