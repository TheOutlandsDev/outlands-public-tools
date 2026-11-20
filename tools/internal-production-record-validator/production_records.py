"""Validate saved internal demand, completion, transfer, and event records."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from datetime import date
from pathlib import Path
import stat
import sys
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator


MAX_INPUT_BYTES = 2 * 1024 * 1024
Modality = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]{4,7}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ProductionRecordError(ValueError):
    """A saved production record is invalid."""


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InternalPanelFlexProduct(InputModel):
    canonical_modality: Modality
    display_modality: Modality
    assembly: Annotated[str, Field(pattern=r"^[0-9]{7}$")]
    lot_prefix: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]{2,19}$")]


class ApprovedProducts(InputModel):
    products: tuple[InternalPanelFlexProduct, ...] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def check_identities(self) -> "ApprovedProducts":
        aliases: set[str] = set()
        prefixes: set[str] = set()
        assemblies: set[str] = set()
        for product in self.products:
            names = {product.canonical_modality, product.display_modality}
            if (aliases & names or product.assembly in assemblies
                    or any(product.lot_prefix.startswith(prefix) or prefix.startswith(product.lot_prefix)
                           for prefix in prefixes)):
                raise ValueError("Approved product aliases, assemblies, and lot prefixes must be unambiguous.")
            aliases.update(names)
            prefixes.add(product.lot_prefix)
            assemblies.add(product.assembly)
        return self


def _approved_products(info: ValidationInfo) -> ApprovedProducts:
    if not isinstance(info.context, ApprovedProducts):
        raise ValueError("A separately approved product map is required.")
    return info.context


def operational_event_identity(
    event_type: Literal["MANUAL_INTERNAL_DEMAND", "COMPLETION_ACTION"],
    target_id: str,
    revision: int,
) -> str:
    """Return the contract-defined exact-once event identity."""

    if revision <= 0:
        raise ValueError("The event revision must be positive.")
    normalized_target = target_id.strip().lower()
    if not normalized_target or len(normalized_target) > 80:
        raise ValueError("The event target identity is invalid.")
    return sha256(
        json.dumps(
            {
                "event_type": event_type,
                "target_id": normalized_target,
                "revision": revision,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def resolve_internal_product(modality: str, approved: ApprovedProducts) -> InternalPanelFlexProduct:
    normalized = modality.strip().upper()
    for product in approved.products:
        if normalized in {product.canonical_modality, product.display_modality}:
            return product
    raise ValueError("The internal Panel Flex modality is not configured.")


class InternalDemandCreateCommand(BaseModel):
    demand_id: UUID
    modality: str = Field(min_length=5, max_length=8)
    requested_quantity: int = Field(gt=0, le=1_000_000)
    needed_by: date
    demand_status: Literal["DRAFT", "ACTIVE"] = "DRAFT"
    revision_comment: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_modality(self, info: ValidationInfo):
        resolve_internal_product(self.modality, _approved_products(info))
        return self


class InternalDemandRevisionCommand(BaseModel):
    expected_revision: int = Field(gt=0)
    requested_quantity: int = Field(gt=0, le=1_000_000)
    needed_by: date
    demand_status: Literal["DRAFT", "ACTIVE", "FULFILLED", "CANCELLED"]
    revision_comment: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InternalPanelFlexLotEvidence(BaseModel):
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_row_number: int = Field(gt=0)
    lot_id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Z][A-Z0-9._/-]*$",
    )
    canonical_modality: str
    display_modality: str
    assembly: str
    quantity: int = Field(gt=0, le=1_000_000)
    step_name: str = Field(min_length=1, max_length=256)

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_product_identity(self, info: ValidationInfo):
        product = resolve_internal_product(self.canonical_modality, _approved_products(info))
        if (
            self.display_modality != product.display_modality
            or self.assembly != product.assembly
            or not self.lot_id.startswith(product.lot_prefix)
        ):
            raise ValueError("The lot evidence does not match the product contract.")
        return self


class InternalLotCompletionCommand(BaseModel):
    completion_revision: int = Field(default=1, gt=0)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    completion_comment: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InternalLotTransferCommand(BaseModel):
    expected_row_version: int = Field(gt=0)
    transfer_comment: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InternalLotTransferSelection(BaseModel):
    lot_id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Z][A-Z0-9._/-]*$",
    )
    expected_row_version: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InternalLotBulkTransferCommand(BaseModel):
    lots: tuple[InternalLotTransferSelection, ...] = Field(
        min_length=1,
        max_length=100,
    )
    transfer_comment: str = Field(min_length=3, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_unique_lots(self, info: ValidationInfo):
        identities = [lot.lot_id.upper() for lot in self.lots]
        if len(identities) != len(set(identities)):
            raise ValueError("Each selected lot may appear only once per batch.")
        prefixes = tuple(product.lot_prefix for product in _approved_products(info).products)
        if any(not lot.lot_id.startswith(prefixes) for lot in self.lots):
            raise ValueError("A selected lot is outside the approved product map.")
        return self


class DemandCreateRecord(InternalDemandCreateCommand):
    kind: Literal["demand-create"]


class DemandRevisionRecord(InternalDemandRevisionCommand):
    kind: Literal["demand-revision"]


class CompletionRecord(InputModel):
    kind: Literal["completion"]
    evidence: InternalPanelFlexLotEvidence
    command: InternalLotCompletionCommand

    @model_validator(mode="after")
    def validate_snapshot(self) -> "CompletionRecord":
        if self.command.source_sha256 != self.evidence.source_sha256:
            raise ValueError("The completion source snapshot does not match the saved evidence.")
        return self


class TransferRecord(InternalLotTransferCommand):
    kind: Literal["transfer"]


class BulkTransferRecord(InternalLotBulkTransferCommand):
    kind: Literal["bulk-transfer"]


class EventRecord(InputModel):
    kind: Literal["event-identity"]
    event_type: Literal["MANUAL_INTERNAL_DEMAND", "COMPLETION_ACTION"]
    target_id: str = Field(min_length=1, max_length=80)
    revision: int = Field(strict=True, gt=0)
    event_id: Digest


Record = Annotated[
    DemandCreateRecord | DemandRevisionRecord | CompletionRecord | TransferRecord | BulkTransferRecord | EventRecord,
    Field(discriminator="kind"),
]


class SavedRecords(InputModel):
    records: tuple[Record, ...] = Field(min_length=1, max_length=1000)


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ProductionRecordError("A saved JSON input has duplicate fields.")
    return fields


def _invalid_constant(_value: str) -> None:
    raise ProductionRecordError("A saved JSON input has a non-finite number.")


def _read_json(path: Path) -> Any:
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise ProductionRecordError("Saved inputs must be ordinary files.")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if not 0 < len(data) <= MAX_INPUT_BYTES:
        raise ProductionRecordError("A saved input is empty or exceeds its size limit.")
    return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_fields, parse_constant=_invalid_constant)


def validate_records(records: SavedRecords) -> dict[str, Any]:
    verified = []
    for number, record in enumerate(records.records, start=1):
        row: dict[str, int | str] = {"record": number, "kind": record.kind}
        if isinstance(record, EventRecord):
            actual = operational_event_identity(record.event_type, record.target_id, record.revision)
            if actual != record.event_id:
                raise ProductionRecordError(f"Event ID mismatch in record {number}.")
            row["event_id"] = actual
        elif isinstance(record, CompletionRecord):
            row["event_id"] = operational_event_identity(
                "COMPLETION_ACTION", record.evidence.lot_id, record.command.completion_revision,
            )
        elif isinstance(record, BulkTransferRecord):
            row["lot_count"] = len(record.lots)
        verified.append(row)
    return {"status": "PASS", "record_count": len(verified), "records": verified}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Saved production record batch JSON")
    parser.add_argument("--products", required=True, type=Path, help="Separately approved product map JSON")
    args = parser.parse_args()
    try:
        approved = ApprovedProducts.model_validate(_read_json(args.products))
        records = SavedRecords.model_validate(_read_json(args.input), context=approved)
        result = validate_records(records)
    except ProductionRecordError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("The saved records or approved product map failed validation.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
