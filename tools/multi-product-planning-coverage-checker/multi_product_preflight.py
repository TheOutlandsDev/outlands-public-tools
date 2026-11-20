"""Fail-closed coverage gate for saved multi-product planning inputs."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from planning_configuration import PlanningConfiguration
from kanban_assignment import (
    KanbanAssignmentConfiguration,
    preflight_wip_assignment,
)
from wip_supply import FPCWIPRecord, WIPNormalizationConfiguration, _read_json, prepare_wip_supply


class OrderRecord(BaseModel):
    part_number: str = Field(min_length=1, max_length=40)
    quantity: int = Field(gt=0)
    ship_quantity: int | None = Field(default=None, ge=0)
    dock_date: date | None = None

    model_config = ConfigDict(frozen=True, extra="forbid")


class InputDataset(BaseModel):
    customer_orders: tuple[OrderRecord, ...] = Field(max_length=10_000)
    panel_orders: tuple[OrderRecord, ...] = Field(max_length=10_000)
    wip_records: tuple[FPCWIPRecord, ...] = Field(max_length=10_000)

    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonical_part_number(value: Any) -> str:
    """Normalize Excel-style numeric identifiers without hiding malformed values."""

    if isinstance(value, bool):
        raise ValueError("part number cannot be boolean")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("numeric part number must be a whole number")
        return str(int(value))
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise ValueError("part number cannot be blank")
        return normalized
    raise ValueError("part number must be a string or whole number")


class PartModalityConfiguration(BaseModel):
    part_to_modality: dict[str, str] = Field(min_length=1, max_length=100)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_mapping(self) -> "PartModalityConfiguration":
        canonical: dict[str, str] = {}
        for raw_part, raw_modality in self.part_to_modality.items():
            part = _canonical_part_number(raw_part)
            modality = raw_modality.strip()
            if not modality:
                raise ValueError("modality cannot be blank")
            if part in canonical:
                raise ValueError("duplicate normalized part number mapping")
            canonical[part] = modality
        object.__setattr__(self, "part_to_modality", canonical)
        return self


class MultiProductCoverageIssue(BaseModel):
    """One deterministic reason the complete input set cannot yet be planned."""

    code: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=120)
    record_count: int = Field(ge=1)
    detail: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True)


class MultiProductCoverageResult(BaseModel):
    """Coverage evidence only; this object intentionally contains no plans."""

    status: str = Field(pattern=r"^(PASS|FAIL)$")
    open_order_count: int = Field(ge=0)
    open_order_quantity: int = Field(ge=0)
    open_order_part_numbers: tuple[str, ...]
    mapped_open_order_part_numbers: tuple[str, ...]
    planning_configured_part_numbers: tuple[str, ...]
    missing_planning_part_numbers: tuple[str, ...]
    unsupported_open_order_part_numbers: tuple[str, ...]
    wip_input_count: int = Field(ge=0)
    wip_assignable_count: int = Field(ge=0)
    wip_rejected_count: int = Field(ge=0)
    issues: tuple[MultiProductCoverageIssue, ...]
    plans_generated: int = Field(ge=0, le=0)
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True)


def _result_hash(values: dict[str, object]) -> str:
    canonical = json.dumps(
        values,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def preflight_multi_product_coverage(
    *,
    dataset: InputDataset,
    part_mapping: PartModalityConfiguration,
    planning_configuration: PlanningConfiguration,
    wip_configuration: WIPNormalizationConfiguration,
    assignment_configuration: KanbanAssignmentConfiguration,
) -> MultiProductCoverageResult:
    """Prove coverage before any multi-product plan is permitted to run."""

    orders = tuple(
        record
        for record in (*dataset.customer_orders, *dataset.panel_orders)
        if record.quantity > 0
        and record.ship_quantity is None
        and record.dock_date is None
    )
    part_counts = Counter(record.part_number for record in orders)
    open_parts = tuple(sorted(part_counts))
    mapped_parts = tuple(
        part for part in open_parts if part in part_mapping.part_to_modality
    )
    unsupported_parts = tuple(
        part for part in open_parts if part not in part_mapping.part_to_modality
    )
    configured_parts = tuple(
        sorted(product.part_number for product in planning_configuration.products)
    )
    configured_set = set(configured_parts)
    missing_planning = tuple(
        part for part in mapped_parts if part not in configured_set
    )

    issues: list[MultiProductCoverageIssue] = []
    for part in unsupported_parts:
        issues.append(
            MultiProductCoverageIssue(
                code="UNSUPPORTED_OPEN_ORDER_PART",
                subject=part,
                record_count=part_counts[part],
                detail="Open demand has no reviewed part-to-modality mapping.",
            )
        )
    for part in missing_planning:
        issues.append(
            MultiProductCoverageIssue(
                code="MISSING_PRODUCT_PLANNING_CONFIGURATION",
                subject=part,
                record_count=part_counts[part],
                detail=(
                    "Open demand is mapped but lacks a complete reviewed planning "
                    "configuration; no partial schedule is allowed."
                ),
            )
        )

    prepared = prepare_wip_supply(dataset.wip_records, wip_configuration)
    wip_preflight = preflight_wip_assignment(
        prepared.records, assignment_configuration
    )
    for issue in wip_preflight.issues:
        issues.append(
            MultiProductCoverageIssue(
                code=issue.code,
                subject=issue.lot_id,
                record_count=1,
                detail=f"WIP source row {issue.source_row}: {issue.detail}",
            )
        )

    ordered_issues = tuple(
        sorted(issues, key=lambda item: (item.code, item.subject, item.detail))
    )
    values: dict[str, object] = {
        "status": "PASS" if not ordered_issues else "FAIL",
        "open_order_count": len(orders),
        "open_order_quantity": sum(record.quantity for record in orders),
        "open_order_part_numbers": open_parts,
        "mapped_open_order_part_numbers": mapped_parts,
        "planning_configured_part_numbers": configured_parts,
        "missing_planning_part_numbers": missing_planning,
        "unsupported_open_order_part_numbers": unsupported_parts,
        "wip_input_count": wip_preflight.input_record_count,
        "wip_assignable_count": wip_preflight.assignable_record_count,
        "wip_rejected_count": wip_preflight.rejected_record_count,
        "issues": ordered_issues,
        "plans_generated": 0,
    }
    return MultiProductCoverageResult(
        **values,
        result_sha256=_result_hash(
            {
                **values,
                "issues": [item.model_dump(mode="json") for item in ordered_issues],
            }
        ),
    )


class SavedCoverageInput(BaseModel):
    dataset: InputDataset
    part_mapping: PartModalityConfiguration
    planning_configuration: PlanningConfiguration
    wip_configuration: WIPNormalizationConfiguration
    assignment_configuration: KanbanAssignmentConfiguration

    model_config = ConfigDict(frozen=True, extra="forbid")

    def evaluate(self) -> MultiProductCoverageResult:
        return preflight_multi_product_coverage(
            dataset=self.dataset,
            part_mapping=self.part_mapping,
            planning_configuration=self.planning_configuration,
            wip_configuration=self.wip_configuration,
            assignment_configuration=self.assignment_configuration,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local JSON containing the orders, WIP and rules")
    args = parser.parse_args()
    try:
        saved = SavedCoverageInput.model_validate(_read_json(args.input))
        result = saved.evaluate()
    except (OSError, ValueError):
        print("Invalid or unreadable coverage input", file=sys.stderr)
        return 2
    print(result.model_dump_json())
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
