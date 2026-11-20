"""Validate saved shipment event identities and lot handoff records."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import stat
import sys
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ROW_ID_PATTERN = re.compile(r"^[0-9a-f]{24}$")
MAX_INPUT_BYTES = 1024 * 1024
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
RowID = Annotated[str, Field(pattern=r"^[0-9a-f]{24}$")]
Version = Annotated[int, Field(strict=True, gt=0)]
LotID = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")]


class SavedRecordError(ValueError):
    """A saved shipment record could not be verified."""


class FlexHandoffLotCommand(BaseModel):
    lot_id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )
    quantity: int = Field(gt=0, le=100000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FlexReadyForLogisticsCommand(BaseModel):
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_order_version: int = Field(gt=0)
    lots: tuple[FlexHandoffLotCommand, ...] = Field(min_length=1, max_length=20)
    comment: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_unique_lots(self) -> "FlexReadyForLogisticsCommand":
        identities = [lot.lot_id.casefold() for lot in self.lots]
        if len(identities) != len(set(identities)):
            raise ValueError("Each selected lot may appear only once.")
        return self


class FlexReturnLotCommand(BaseModel):
    lot_id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )
    expected_state_version: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FlexReturnToFlexCommand(BaseModel):
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_order_version: int = Field(gt=0)
    lots: tuple[FlexReturnLotCommand, ...] = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=3, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_unique_lots(self) -> "FlexReturnToFlexCommand":
        identities = [lot.lot_id.casefold() for lot in self.lots]
        if len(identities) != len(set(identities)):
            raise ValueError("Each returned lot may appear only once.")
        return self


def outbound_event_identity(
    revision_sha256: str,
    row_id: str,
    order_row_version: int,
) -> str:
    """Return a deterministic identity for one accepted O&S dock transaction."""

    if not re.fullmatch(r"[0-9a-f]{64}", revision_sha256):
        raise ValueError("The outbound source revision is invalid.")
    if not ROW_ID_PATTERN.fullmatch(row_id):
        raise ValueError("The outbound order identity is invalid.")
    if order_row_version <= 0:
        raise ValueError("The outbound order version is invalid.")
    payload = {
        "event_type": "FLEX_OUTBOUND_TRANSACTION",
        "order_row_version": order_row_version,
        "revision_sha256": revision_sha256,
        "row_id": row_id,
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def flex_handoff_event_identity(
    *,
    revision_sha256: str,
    row_id: str,
    lot_id: str,
    quantity: int,
    action: str,
    state_version: int,
) -> str:
    """Return a stable identity for one lot lifecycle transition."""

    payload = {
        "action": action,
        "event_type": "FLEX_LOGISTICS_HANDOFF",
        "lot_id": lot_id,
        "quantity": quantity,
        "revision_sha256": revision_sha256,
        "row_id": row_id,
        "state_version": state_version,
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class InputRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DockEvent(InputRecord):
    kind: Literal["dock-event"]
    revision_sha256: Digest
    row_id: RowID
    order_row_version: Version
    event_id: Digest


class HandoffEvent(InputRecord):
    kind: Literal["handoff-event"]
    revision_sha256: Digest
    row_id: RowID
    lot_id: LotID
    quantity: int = Field(strict=True, gt=0, le=100_000)
    action: Literal["READY_FOR_LOGISTICS", "RETURN_TO_FLEX"]
    state_version: Version
    event_id: Digest


class ReadyRecord(FlexReadyForLogisticsCommand):
    kind: Literal["ready-record"]


class ReturnRecord(FlexReturnToFlexCommand):
    kind: Literal["return-record"]


Record = Annotated[DockEvent | HandoffEvent | ReadyRecord | ReturnRecord, Field(discriminator="kind")]


class SavedRecords(InputRecord):
    records: list[Record] = Field(min_length=1, max_length=500)


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise SavedRecordError("The JSON contains duplicate fields.")
    return result


def _invalid_constant(_value: str) -> None:
    raise SavedRecordError("The JSON contains a non-finite number.")


def _read_records(path: Path) -> SavedRecords:
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise SavedRecordError("The input must be an ordinary file.")
    with path.open("rb") as stream:
        content = stream.read(MAX_INPUT_BYTES + 1)
    if len(content) > MAX_INPUT_BYTES:
        raise SavedRecordError("The input exceeds its size limit.")
    try:
        value = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields,
                           parse_constant=_invalid_constant)
        return SavedRecords.model_validate(value)
    except (ValueError, RecursionError) as exc:
        raise SavedRecordError("The saved record schema is invalid.") from exc


def validate_saved_records(path: Path) -> dict[str, object]:
    """Validate every record before returning a report."""
    rows = []
    for number, record in enumerate(_read_records(path).records, start=1):
        summary: dict[str, str | int] = {"record": number, "kind": record.kind}
        if isinstance(record, DockEvent):
            actual = outbound_event_identity(record.revision_sha256, record.row_id, record.order_row_version)
        elif isinstance(record, HandoffEvent):
            actual = flex_handoff_event_identity(
                revision_sha256=record.revision_sha256,
                row_id=record.row_id, lot_id=record.lot_id, quantity=record.quantity,
                action=record.action, state_version=record.state_version,
            )
        else:
            summary["lot_count"] = len(record.lots)
            rows.append(summary)
            continue
        if actual != record.event_id:
            raise SavedRecordError(f"Event ID mismatch in record {number}.")
        summary["event_id"] = actual
        rows.append(summary)
    return {"status": "PASS", "record_count": len(rows), "records": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Saved JSON records file")
    args = parser.parse_args()
    try:
        result = validate_saved_records(args.input)
    except SavedRecordError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError:
        print("The saved records could not be read.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
