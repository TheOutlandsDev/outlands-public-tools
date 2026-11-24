"""Reconcile saved operator work-in-progress with authoritative Order Needs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator


MAX_INPUT_BYTES = 16 * 1024 * 1024
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Part = Annotated[str, Field(min_length=1, max_length=80)]
Quantity = Annotated[StrictInt, Field(ge=0)]


class OperatorWorkCenterError(ValueError):
    """The saved inputs cannot be reconciled."""


class OrderNeedsSource(BaseModel):
    revision_sha256: Digest
    wip_source_sha256: Digest


class OrderRow(BaseModel):
    part_number: Part


class ProductSummary(OrderRow):
    eligible_wip: Quantity
    configured: StrictBool


class OrderNeedsSnapshot(BaseModel):
    source: OrderNeedsSource
    rows: tuple[OrderRow, ...]
    products: tuple[ProductSummary, ...]

    @model_validator(mode="after")
    def validate_product_keys(self):
        if len({product.part_number for product in self.products}) != len(self.products):
            raise ValueError("The Order Needs snapshot contains duplicate product summaries.")
        return self


class ActiveRevision(BaseModel):
    sha256: Digest


class AssignedWIPRecord(BaseModel):
    lot_id: str = Field(min_length=1, max_length=80)
    source_product: Part
    canonical_product: Part
    total_parts: Quantity


class OperationsSnapshot(BaseModel):
    active_revision: ActiveRevision
    wip_source_sha256: Digest
    wip_rows: tuple[AssignedWIPRecord, ...]


class VerifiedSource(BaseModel):
    sha256: Digest
    wip_sha256: Digest


class ReconciliationResult(BaseModel):
    status: Literal["PASS"] = "PASS"
    source: VerifiedSource
    eligible_wip_by_product: dict[str, int]

    model_config = ConfigDict(frozen=True)


def _is_verification(row: AssignedWIPRecord) -> bool:
    product = row.source_product.upper()
    return (
        row.source_product != row.canonical_product
        or row.lot_id.upper().startswith("V")
        or product.endswith("V")
        or product.endswith("-V")
    )


def reconcile_wip(
    order_needs: OrderNeedsSnapshot, operations: OperationsSnapshot
) -> ReconciliationResult:
    source_sha256 = operations.active_revision.sha256
    wip_sha256 = operations.wip_source_sha256
    if source_sha256 != order_needs.source.revision_sha256:
        raise OperatorWorkCenterError(
            "The operator O&S revision does not match authoritative Order Needs."
        )
    if wip_sha256 != order_needs.source.wip_source_sha256:
        raise OperatorWorkCenterError(
            "The operator WIP revision does not match authoritative Order Needs."
        )

    current_products = tuple(sorted({row.part_number for row in order_needs.rows}))
    eligible_wip = tuple(
        row
        for row in operations.wip_rows
        if row.canonical_product in current_products and not _is_verification(row)
    )
    expected_wip_by_product = {
        row.part_number: row.eligible_wip
        for row in order_needs.products
        if row.part_number in current_products and row.configured
    }
    actual_wip_by_product = {
        part_number: sum(
            row.total_parts
            for row in eligible_wip
            if row.canonical_product == part_number
        )
        for part_number in expected_wip_by_product
    }
    if actual_wip_by_product != expected_wip_by_product:
        raise OperatorWorkCenterError(
            "Current lot-level WIP does not reconcile with authoritative coverage."
        )
    return ReconciliationResult(
        source=VerifiedSource(sha256=source_sha256, wip_sha256=wip_sha256),
        eligible_wip_by_product=actual_wip_by_product,
    )


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise OperatorWorkCenterError("A snapshot contains duplicate JSON fields.")
        fields[key] = value
    return fields


def _nonfinite(_value):
    raise OperatorWorkCenterError("A snapshot contains a nonfinite JSON number.")


def read_snapshot(path: Path, model: type[BaseModel]):
    if not path.is_file():
        raise OperatorWorkCenterError("A snapshot must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise OperatorWorkCenterError("A snapshot is empty or exceeds its size limit.")
    payload = json.loads(
        raw.decode("utf-8"), object_pairs_hook=_unique_fields, parse_constant=_nonfinite,
    )
    return model.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("order_needs", type=Path)
    parser.add_argument("operations", type=Path)
    args = parser.parse_args(argv)
    try:
        result = reconcile_wip(
            read_snapshot(args.order_needs, OrderNeedsSnapshot),
            read_snapshot(args.operations, OperationsSnapshot),
        )
    except OperatorWorkCenterError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: A saved snapshot is unreadable or invalid.", file=sys.stderr)
        return 2
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
