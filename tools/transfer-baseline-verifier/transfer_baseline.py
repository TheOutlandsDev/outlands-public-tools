"""Validate a saved transfer baseline and summarize its observed events."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
import stat
import sys
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationInfo, model_validator


MAX_BASELINE_BYTES = 256 * 1024
Assembly = Annotated[str, Field(pattern=r"^[0-9]{7}$")]


class ApprovedAssemblies(BaseModel):
    assemblies: tuple[Assembly, ...] = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_unique(self) -> "ApprovedAssemblies":
        if len(set(self.assemblies)) != len(self.assemblies):
            raise ValueError("The approved assembly list has duplicate entries.")
        return self


class InternalPanelFlexBaselineError(ValueError):
    """Raised when the controlled validation fixture cannot be trusted."""


class InternalPanelFlexTransferRecord(BaseModel):
    source_row_number: int = Field(strict=True, gt=0, le=10_000)
    assembly: str = Field(pattern=r"^[0-9]{7}$")
    lot_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_]+$")
    quantity: int = Field(strict=True, gt=0, le=1_000_000)
    status: Literal["CLOSED"]
    occurred_at: datetime

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def require_explicit_timezone(self):
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("Every transfer timestamp must include its UTC offset.")
        return self


class InternalPanelFlexTransferBaseline(BaseModel):
    schema_version: Literal["0.1.0"]
    status: Literal["DEVELOPMENT_VALIDATION_FIXTURE"]
    source_identity: str = Field(min_length=1, max_length=100)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    declared_window_start: date
    declared_window_end: date
    event_type: Literal["FLEX_TO_HLA_TRANSFER"]
    expected_records: int = Field(strict=True, gt=0, le=10_000)
    expected_quantity: int = Field(strict=True, gt=0, le=10_000_000_000)
    proves_hla_consumption: StrictBool
    database_ingestion_authorized: StrictBool
    records: tuple[InternalPanelFlexTransferRecord, ...] = Field(min_length=1, max_length=10_000)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_baseline(self, info: ValidationInfo):
        if self.proves_hla_consumption or self.database_ingestion_authorized:
            raise ValueError("The baseline cannot authorize ingestion or claim consumption.")
        approved = info.context
        if not isinstance(approved, frozenset) or not approved:
            raise ValueError("A separately approved assembly list is required.")
        if self.declared_window_start > self.declared_window_end:
            raise ValueError("The baseline window is reversed.")
        if len(self.records) != self.expected_records:
            raise ValueError("The baseline record count drifted.")
        if sum(record.quantity for record in self.records) != self.expected_quantity:
            raise ValueError("The baseline quantity drifted.")

        row_numbers = [record.source_row_number for record in self.records]
        if row_numbers != list(range(1, self.expected_records + 1)):
            raise ValueError("Baseline row identities must be consecutive and ordered.")

        unknown = sorted(
            {record.assembly for record in self.records} - approved
        )
        if unknown:
            raise ValueError("The baseline includes an unknown internal Flex product.")

        for record in self.records:
            local_date = record.occurred_at.date()
            if not self.declared_window_start <= local_date <= self.declared_window_end:
                raise ValueError("A baseline event falls outside the declared window.")

        canonical_records = [
            record.model_dump(mode="json") for record in self.records
        ]
        calculated_source_sha256 = sha256(
            json.dumps(
                canonical_records,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        if calculated_source_sha256 != self.source_sha256:
            raise ValueError("The baseline source checksum gate failed.")

        identities = [
            transfer_event_identity(
                self.source_sha256,
                record.source_row_number,
                self.event_type,
            )
            for record in self.records
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("The baseline contains a duplicate event identity.")
        return self


class InternalPanelFlexBaselineSummary(BaseModel):
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_count: int = Field(gt=0)
    total_quantity: int = Field(gt=0)
    totals_by_assembly: dict[str, int]
    first_observed_event: datetime
    last_observed_event: datetime
    database_writes: Literal[False] = False
    proves_hla_consumption: Literal[False] = False

    model_config = ConfigDict(frozen=True)


def transfer_event_identity(
    source_sha256: str,
    source_row_number: int,
    event_type: str = "FLEX_TO_HLA_TRANSFER",
) -> str:
    """Return the contract-defined identity for one immutable transfer event."""

    if len(source_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in source_sha256
    ):
        raise InternalPanelFlexBaselineError("The source checksum is invalid.")
    if source_row_number <= 0:
        raise InternalPanelFlexBaselineError("The source row number is invalid.")
    if event_type != "FLEX_TO_HLA_TRANSFER":
        raise InternalPanelFlexBaselineError("The event type is not authorized.")
    identity = {
        "event_type": event_type,
        "source_row_number": source_row_number,
        "source_sha256": source_sha256,
    }
    return sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise InternalPanelFlexBaselineError("The JSON contains duplicate fields.")
    return fields


def _invalid_constant(_value: str) -> None:
    raise InternalPanelFlexBaselineError("The JSON contains a non-finite number.")


def _load_json(path: Path) -> Any:
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise InternalPanelFlexBaselineError("A saved input must be an ordinary file.")
    with path.open("rb") as stream:
        data = stream.read(MAX_BASELINE_BYTES + 1)
    if not 0 < len(data) <= MAX_BASELINE_BYTES:
        raise InternalPanelFlexBaselineError("A saved input size is invalid.")
    return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_fields, parse_constant=_invalid_constant)


def load_internal_panel_flex_transfer_baseline(
    path: Path, *, assembly_path: Path,
) -> InternalPanelFlexTransferBaseline:
    """Validate the baseline against a separate, trusted assembly list."""
    try:
        approved = ApprovedAssemblies.model_validate(_load_json(assembly_path))
        payload = _load_json(path)
        return InternalPanelFlexTransferBaseline.model_validate(payload, context=frozenset(approved.assemblies))
    except InternalPanelFlexBaselineError:
        raise
    except (OSError, ValueError, RecursionError) as exc:
        raise InternalPanelFlexBaselineError("The transfer baseline or approved assembly list failed validation.") from exc


def summarize_internal_panel_flex_transfer_baseline(
    baseline: InternalPanelFlexTransferBaseline,
) -> InternalPanelFlexBaselineSummary:
    """Create bounded evidence without writing to PostgreSQL or ClickHouse."""

    source = baseline
    totals = Counter[str]()
    for record in source.records:
        totals[record.assembly] += record.quantity
    timestamps = [record.occurred_at for record in source.records]
    return InternalPanelFlexBaselineSummary(
        source_sha256=source.source_sha256,
        record_count=len(source.records),
        total_quantity=sum(record.quantity for record in source.records),
        totals_by_assembly=dict(sorted(totals.items())),
        first_observed_event=min(timestamps),
        last_observed_event=max(timestamps),
    )

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="Saved transfer baseline JSON")
    parser.add_argument("--assemblies", type=Path, required=True, help="Trusted approved assembly list JSON")
    parser.add_argument("--include-event-ids", action="store_true", help="Include each verified source row and event ID")
    args = parser.parse_args()
    try:
        baseline = load_internal_panel_flex_transfer_baseline(args.baseline, assembly_path=args.assemblies)
        summary = summarize_internal_panel_flex_transfer_baseline(baseline)
    except InternalPanelFlexBaselineError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    output = summary.model_dump(mode="json")
    if args.include_event_ids:
        output["event_ids"] = [
            {"source_row_number": record.source_row_number,
             "event_id": transfer_event_identity(baseline.source_sha256, record.source_row_number, baseline.event_type)}
            for record in baseline.records
        ]
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
