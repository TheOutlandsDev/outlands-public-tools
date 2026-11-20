"""Calculate order status, modality and lead-time dates from saved rows."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path
import stat
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OSBusinessRules(BaseModel):
    """Caller-supplied part IDs, aliases, lead times and modalities."""

    part_aliases: dict[str, str] = Field(default_factory=dict, max_length=1000)
    part_lead_time_weeks: dict[str, int] = Field(max_length=1000)
    part_modalities: dict[str, str] = Field(default_factory=dict, max_length=1000)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_contract(self) -> "OSBusinessRules":
        if any(weeks < 1 or weeks > 52 for weeks in self.part_lead_time_weeks.values()):
            raise ValueError("lead-time weeks must remain between 1 and 52")
        if any(target not in self.part_lead_time_weeks for target in self.part_aliases.values()):
            raise ValueError("every part alias must target a governed lead-time part")
        parts = self.part_lead_time_weeks.keys() | self.part_aliases.keys() | self.part_modalities.keys()
        if any(not part or part != "".join(part.upper().split()) for part in parts):
            raise ValueError("Rule table part IDs must be uppercase and contain no whitespace")
        return self


def canonical_part_number(value: str, rules: OSBusinessRules) -> str:
    normalized = "".join(value.upper().split())
    return rules.part_aliases.get(normalized, normalized)


def modality_for_part(value: str, rules: OSBusinessRules) -> str:
    return rules.part_modalities.get(canonical_part_number(value, rules), "UNMAPPED")


def calculated_lead_time_date(part_number: str, order_date: date | None, rules: OSBusinessRules) -> date | None:
    if order_date is None:
        return None
    weeks = rules.part_lead_time_weeks.get(canonical_part_number(part_number, rules))
    return order_date + timedelta(weeks=weeks) if weeks is not None else None


def calculated_order_status(
    *,
    carrier: str | None,
    tracking_number: str | None,
    ship_date: date | None,
    ship_quantity: int | None,
    shipment_number: str | None,
    dock_date: date | None,
) -> str:
    carrier_tracking = bool((carrier or "").strip() and (tracking_number or "").strip())
    if carrier_tracking:
        return "Shipped"
    if ship_date is not None or ship_quantity is not None or (shipment_number or "").strip():
        return "Shipped"
    if dock_date is not None:
        return "Docked"
    return "Open"


class OrderInput(BaseModel):
    part_number: str = Field(min_length=1, max_length=120)
    order_date: date | None = None
    carrier: str | None = Field(default=None, max_length=120)
    tracking_number: str | None = Field(default=None, max_length=120)
    ship_date: date | None = None
    ship_quantity: int | None = Field(default=None, ge=0)
    shipment_number: str | None = Field(default=None, max_length=120)
    dock_date: date | None = None

    model_config = ConfigDict(extra="forbid")


class SavedInput(BaseModel):
    rules: OSBusinessRules
    orders: tuple[OrderInput, ...] = Field(max_length=1000)

    model_config = ConfigDict(extra="forbid")


class OrderStatusRow(BaseModel):
    part_number: str
    canonical_part_number: str
    modality: str
    status: Literal["Open", "Docked", "Shipped"]
    lead_time_date: date | None


def evaluate_order(order: OrderInput, rules: OSBusinessRules) -> OrderStatusRow:
    status = calculated_order_status(
        carrier=order.carrier, tracking_number=order.tracking_number,
        ship_date=order.ship_date, ship_quantity=order.ship_quantity,
        shipment_number=order.shipment_number, dock_date=order.dock_date,
    )
    return OrderStatusRow(
        part_number=order.part_number,
        canonical_part_number=canonical_part_number(order.part_number, rules),
        modality=modality_for_part(order.part_number, rules),
        status=status,
        lead_time_date=calculated_lead_time_date(order.part_number, order.order_date, rules),
    )


_MAX_FILE_BYTES = 1024 * 1024


def _ordinary_file(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Saved input contains duplicate JSON fields.")
    return result


def _reject_constant(_value: str) -> object:
    raise ValueError("Saved input contains an invalid JSON number.")


def _read_json(path: Path) -> object:
    try:
        selected = path.lstat()
        if not _ordinary_file(selected):
            raise ValueError("Saved input must be an ordinary file.")
        if selected.st_size > _MAX_FILE_BYTES:
            raise ValueError("Saved input exceeds the 1 MiB limit.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _ordinary_file(opened) or not os.path.samestat(selected, opened):
                raise ValueError("Saved input changed while opening.")
            content = stream.read(_MAX_FILE_BYTES + 1)
    except ValueError:
        raise
    except (OSError, ValueError):
        raise ValueError("Unable to read the saved input.") from None
    if len(content) > _MAX_FILE_BYTES:
        raise ValueError("Saved input exceeds the 1 MiB limit.")

    try:
        return json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique_fields,
            parse_constant=_reject_constant,
        )
    except ValueError:
        raise
    except (ArithmeticError, ValueError, RecursionError):
        raise ValueError("Saved input must contain valid UTF-8 JSON.") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Saved JSON with rule tables and order evidence")
    args = parser.parse_args()
    try:
        saved = SavedInput.model_validate(_read_json(args.input))
        rows = [evaluate_order(order, saved.rules).model_dump(mode="json") for order in saved.orders]
    except (ValueError, OverflowError):
        print("Invalid order input. Check rule tables, dates and order evidence.", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((json.dumps({"orders": rows}, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
