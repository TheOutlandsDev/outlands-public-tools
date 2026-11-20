"""Deterministic, fail-closed K1-K6 assignment for prepared work-in-progress records."""

from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_MAX_RECORDS = 10_000
_MAX_INPUT_BYTES = 8 * 1024 * 1024


class PreparedWIPRecord(BaseModel):
    """One immutable prepared supply row."""

    source_row: int = Field(ge=5, le=_MAX_RECORDS)
    product: str = Field(min_length=1, max_length=120)
    lot_id: str = Field(min_length=1, max_length=120)
    current_step: str = Field(min_length=1, max_length=256)
    quantity_in_process_raw: int = Field(ge=0)
    normalization_applied: bool
    yield_loss_quantity: int = Field(ge=0)
    quantity_in_process: int = Field(ge=0)
    parts_completed: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class KanbanAssignmentError(ValueError):
    """Raised before assignment when the controlled contract cannot be proven."""


class ProductStartRule(BaseModel):
    lot_prefix: str = Field(pattern=r"^[A-Z0-9]{5}$")
    product: str = Field(min_length=1, max_length=120)
    passivation_family: Literal["Soldermask", "Coverlay", "Dryfilm"]
    expected_start: int = Field(gt=0, le=10_000)

    model_config = ConfigDict(frozen=True)


class KanbanAssignmentConfiguration(BaseModel):
    configuration_id: str = Field(min_length=1, max_length=100)
    configuration_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    product_start_rules: tuple[ProductStartRule, ...] = Field(
        min_length=1, max_length=100
    )
    product_aliases: dict[str, str] = Field(default_factory=dict, max_length=100)
    direct_kanbans: dict[int, tuple[str, ...]]
    alternate_operations: tuple[str, ...] = Field(min_length=1, max_length=20)
    alternate_product_kanban: dict[str, int] = Field(min_length=1, max_length=100)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_contract(self) -> "KanbanAssignmentConfiguration":
        if set(self.direct_kanbans) != set(range(1, 7)):
            raise ValueError("direct Kanban keys must be exactly K1 through K6")
        direct_steps = [
            step.strip()
            for kanban in range(1, 7)
            for step in self.direct_kanbans[kanban]
        ]
        if len(direct_steps) != 66 or len(set(direct_steps)) != 66:
            raise ValueError("direct operations must contain 66 unique values")
        if any(not step for step in direct_steps):
            raise ValueError("direct operation cannot be blank")
        if len(self.alternate_operations) != 3:
            raise ValueError("alternate operation contract must contain three values")
        if len(set(self.alternate_operations)) != 3:
            raise ValueError("alternate operations must be unique")
        if set(direct_steps) & set(self.alternate_operations):
            raise ValueError("direct and alternate operations must not overlap")
        prefixes = [rule.lot_prefix for rule in self.product_start_rules]
        if len(prefixes) != 24 or len(set(prefixes)) != 24:
            raise ValueError("start rules must contain 24 unique prefixes")
        for source, target in self.product_aliases.items():
            if not source.strip() or not target.strip() or source == target:
                raise ValueError("product aliases must be explicit and non-circular")
        if any(value not in range(1, 7) for value in self.alternate_product_kanban.values()):
            raise ValueError("alternate destination must be K1 through K6")
        return self


class AssignmentIssue(BaseModel):
    code: Literal[
        "DUPLICATE_SOURCE_ROW",
        "DUPLICATE_LOT_ID",
        "UNKNOWN_LOT_PREFIX",
        "PREFIX_PRODUCT_MISMATCH",
        "UNMAPPED_OPERATION",
        "UNRESOLVED_ALTERNATE_PRODUCT",
    ]
    source_row: int
    lot_id: str
    detail: str

    model_config = ConfigDict(frozen=True)


class AssignmentPreflight(BaseModel):
    status: Literal["PASS", "FAIL"]
    input_record_count: int = Field(ge=0, le=10_000)
    assignable_record_count: int = Field(ge=0, le=10_000)
    rejected_record_count: int = Field(ge=0, le=10_000)
    issues: tuple[AssignmentIssue, ...]
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True)


class AssignedWIPRecord(BaseModel):
    source_row: int
    lot_id: str
    lot_prefix: str
    source_product: str
    canonical_product: str
    passivation_family: str
    current_step: str
    kanban: int = Field(ge=1, le=6)
    assignment_rule: Literal["DIRECT_OPERATION", "ALTERNATE_PRODUCT"]
    quantity_in_process_raw: int = Field(ge=0)
    quantity_in_process: int = Field(ge=0)
    parts_completed: int = Field(ge=0)
    total_parts: int = Field(ge=0)
    expected_start: int = Field(gt=0)
    yield_percent: Decimal = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class KanbanAssignmentResult(BaseModel):
    records: tuple[AssignedWIPRecord, ...]
    input_record_count: int
    kanban_counts: dict[int, int]
    raw_wip_total: int
    normalized_wip_total: int
    completed_total: int
    total_parts: int
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True)


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def load_assignment_configuration(path: Path) -> KanbanAssignmentConfiguration:
    try:
        return KanbanAssignmentConfiguration.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise KanbanAssignmentError("Kanban assignment configuration is invalid") from exc


def _configuration_sha256(configuration: KanbanAssignmentConfiguration) -> str:
    return _canonical_sha256(configuration.model_dump(mode="json"))


def _prefix(record: PreparedWIPRecord) -> str:
    return record.lot_id[1:6] if len(record.lot_id) >= 6 else ""


def preflight_wip_assignment(
    records: tuple[PreparedWIPRecord, ...],
    configuration: KanbanAssignmentConfiguration,
) -> AssignmentPreflight:
    """Evaluate every input row without returning a partial assignment."""

    start_by_prefix = {
        rule.lot_prefix: rule for rule in configuration.product_start_rules
    }
    direct = {
        step: kanban
        for kanban, steps in configuration.direct_kanbans.items()
        for step in steps
    }
    source_rows = Counter(record.source_row for record in records)
    lots = Counter(record.lot_id for record in records)
    issues: list[AssignmentIssue] = []
    rejected_rows: set[int] = set()

    def add(index: int, record: PreparedWIPRecord, code: str, detail: str) -> None:
        issues.append(
            AssignmentIssue(
                code=code,
                source_row=record.source_row,
                lot_id=record.lot_id,
                detail=detail,
            )
        )
        rejected_rows.add(index)

    for index, record in enumerate(records):
        if source_rows[record.source_row] > 1:
            add(index, record, "DUPLICATE_SOURCE_ROW", "source row is not unique")
        if lots[record.lot_id] > 1:
            add(index, record, "DUPLICATE_LOT_ID", "lot identity is not unique")
        prefix = _prefix(record)
        start_rule = start_by_prefix.get(prefix)
        if start_rule is None:
            add(index, record, "UNKNOWN_LOT_PREFIX", f"unsupported lot prefix {prefix!r}")
        else:
            canonical = configuration.product_aliases.get(
                record.product, record.product
            )
            if canonical != start_rule.product:
                add(
                    index,
                    record,
                    "PREFIX_PRODUCT_MISMATCH",
                    f"prefix expects {start_rule.product!r}; product resolves to {canonical!r}",
                )
        if record.current_step in direct:
            continue
        if record.current_step not in configuration.alternate_operations:
            add(index, record, "UNMAPPED_OPERATION", "operation is not in K1-K6 or alternate rules")
            continue
        canonical = configuration.product_aliases.get(record.product, record.product)
        destination = configuration.alternate_product_kanban.get(record.product)
        if destination is None:
            destination = configuration.alternate_product_kanban.get(canonical)
        if destination is None:
            add(
                index,
                record,
                "UNRESOLVED_ALTERNATE_PRODUCT",
                "alternate operation has no reviewed product destination",
            )

    ordered = tuple(sorted(issues, key=lambda item: (item.source_row, item.code)))
    return AssignmentPreflight(
        status="FAIL" if ordered else "PASS",
        input_record_count=len(records),
        assignable_record_count=len(records) - len(rejected_rows),
        rejected_record_count=len(rejected_rows),
        issues=ordered,
        configuration_sha256=_configuration_sha256(configuration),
    )


def assign_wip_to_kanbans(
    records: tuple[PreparedWIPRecord, ...],
    configuration: KanbanAssignmentConfiguration,
) -> KanbanAssignmentResult:
    """Assign every input or fail before returning any assignment result."""

    preflight = preflight_wip_assignment(records, configuration)
    if preflight.status != "PASS":
        codes = ",".join(issue.code for issue in preflight.issues)
        raise KanbanAssignmentError(f"Kanban assignment preflight failed: {codes}")
    start_by_prefix = {
        rule.lot_prefix: rule for rule in configuration.product_start_rules
    }
    direct = {
        step: kanban
        for kanban, steps in configuration.direct_kanbans.items()
        for step in steps
    }
    assigned: list[AssignedWIPRecord] = []
    for record in records:
        prefix = _prefix(record)
        start = start_by_prefix[prefix]
        canonical = configuration.product_aliases.get(record.product, record.product)
        if record.current_step in direct:
            kanban = direct[record.current_step]
            assignment_rule = "DIRECT_OPERATION"
        else:
            kanban = configuration.alternate_product_kanban.get(record.product)
            if kanban is None:
                kanban = configuration.alternate_product_kanban[canonical]
            assignment_rule = "ALTERNATE_PRODUCT"
        total = record.quantity_in_process + record.parts_completed
        yield_percent = (
            (Decimal(total) / Decimal(start.expected_start)) * Decimal("100")
        ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        assigned.append(
            AssignedWIPRecord(
                source_row=record.source_row,
                lot_id=record.lot_id,
                lot_prefix=prefix,
                source_product=record.product,
                canonical_product=canonical,
                passivation_family=start.passivation_family,
                current_step=record.current_step,
                kanban=kanban,
                assignment_rule=assignment_rule,
                quantity_in_process_raw=record.quantity_in_process_raw,
                quantity_in_process=record.quantity_in_process,
                parts_completed=record.parts_completed,
                total_parts=total,
                expected_start=start.expected_start,
                yield_percent=yield_percent,
            )
        )
    ordered = tuple(
        sorted(
            assigned,
            key=lambda row: (
                row.kanban,
                row.canonical_product,
                row.total_parts,
                row.lot_id,
                row.source_row,
            ),
        )
    )
    payload = [row.model_dump(mode="json") for row in ordered]
    return KanbanAssignmentResult(
        records=ordered,
        input_record_count=len(records),
        kanban_counts=dict(sorted(Counter(row.kanban for row in ordered).items())),
        raw_wip_total=sum(row.quantity_in_process_raw for row in ordered),
        normalized_wip_total=sum(row.quantity_in_process for row in ordered),
        completed_total=sum(row.parts_completed for row in ordered),
        total_parts=sum(row.total_parts for row in ordered),
        configuration_sha256=preflight.configuration_sha256,
        result_sha256=_canonical_sha256(payload),
    )


class SavedAssignment(BaseModel):
    configuration: KanbanAssignmentConfiguration
    records: tuple[PreparedWIPRecord, ...] = Field(max_length=_MAX_RECORDS)

    model_config = ConfigDict(extra="forbid")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local JSON with configuration and prepared records")
    parser.add_argument("--preflight", action="store_true", help="Return row diagnostics and counts")
    args = parser.parse_args()
    try:
        if not args.input.is_file():
            raise ValueError("Expected a regular input file")
        with args.input.open("rb") as stream:
            data = stream.read(_MAX_INPUT_BYTES + 1)
        if len(data) > _MAX_INPUT_BYTES:
            raise ValueError("Input exceeds the size limit")
        saved = SavedAssignment.model_validate_json(data)
        if args.preflight:
            result = preflight_wip_assignment(saved.records, saved.configuration)
            print(result.model_dump_json())
            return 0 if result.status == "PASS" else 1
        result = assign_wip_to_kanbans(saved.records, saved.configuration)
    except KanbanAssignmentError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print("Invalid or unreadable assignment input", file=sys.stderr)
        return 2
    print(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
