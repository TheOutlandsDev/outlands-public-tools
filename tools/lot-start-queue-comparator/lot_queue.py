"""Compare two saved lot-start recommendation queues by modality."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import stat
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MAX_INPUT_BYTES = 2 * 1024 * 1024


class AuthoritativeFlexA4Error(ValueError):
    """A saved queue cannot be compared safely."""


class QueueComparisonRow(BaseModel):
    modality: str = Field(min_length=1, max_length=80)
    part_number: str = Field(min_length=1, max_length=80)
    lot_size: int = Field(gt=0)
    remaining_demand: int = Field(ge=0)
    eligible_wip: int = Field(ge=0)
    uncovered_after_wip: int = Field(ge=0)
    recommended_lots: int = Field(ge=0)
    recommended_start_quantity: int = Field(ge=0)
    recommended_start_by: date | None

    model_config = ConfigDict(frozen=True, extra="forbid")


class QueueTotals(BaseModel):
    queue_rows: int = Field(ge=0)
    open_order_demand: int = Field(ge=0)
    eligible_wip: int = Field(ge=0)
    covered_by_wip: int = Field(ge=0)
    wip_surplus_after_demand: int = Field(ge=0)
    uncovered_after_wip: int = Field(ge=0)
    recommended_lots: int = Field(ge=0)
    recommended_start_quantity: int = Field(ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class QueueComparisonResult(BaseModel):
    status: Literal["PASS"] = "PASS"
    before_totals: QueueTotals
    after_totals: QueueTotals
    changed_recommendations: tuple[dict[str, Any], ...]
    changed_recommendation_count: int = Field(ge=0)
    timing_or_start_date_changes: tuple[dict[str, Any], ...]
    timing_or_start_date_change_count: int = Field(ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_difference_counts(self):
        if self.changed_recommendation_count != len(self.changed_recommendations):
            raise ValueError("The recommendation difference count is inconsistent.")
        if self.timing_or_start_date_change_count != len(
            self.timing_or_start_date_changes
        ):
            raise ValueError("The timing difference count is inconsistent.")
        return self


def _totals(rows: tuple[QueueComparisonRow, ...]) -> QueueTotals:
    return QueueTotals(
        queue_rows=len(rows),
        open_order_demand=sum(row.remaining_demand for row in rows),
        eligible_wip=sum(row.eligible_wip for row in rows),
        covered_by_wip=sum(
            min(row.remaining_demand, row.eligible_wip) for row in rows
        ),
        wip_surplus_after_demand=sum(
            max(0, row.eligible_wip - row.remaining_demand) for row in rows
        ),
        uncovered_after_wip=sum(row.uncovered_after_wip for row in rows),
        recommended_lots=sum(row.recommended_lots for row in rows),
        recommended_start_quantity=sum(
            row.recommended_start_quantity for row in rows
        ),
    )


def _differences(
    before: tuple[QueueComparisonRow, ...],
    after: tuple[QueueComparisonRow, ...],
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    before_by_modality = {row.modality: row for row in before}
    after_by_modality = {row.modality: row for row in after}
    if len(before_by_modality) != len(before) or len(after_by_modality) != len(after):
        raise AuthoritativeFlexA4Error("Duplicate modalities are not allowed in a queue.")
    if set(before_by_modality) != set(after_by_modality):
        raise AuthoritativeFlexA4Error("The compared modality sets differ.")
    recommendations: list[dict[str, Any]] = []
    timing: list[dict[str, Any]] = []
    for modality in sorted(before_by_modality):
        legacy = before_by_modality[modality]
        candidate = after_by_modality[modality]
        if (
            legacy.recommended_lots != candidate.recommended_lots
            or legacy.recommended_start_quantity
            != candidate.recommended_start_quantity
        ):
            recommendations.append(
                {
                    "modality": modality,
                    "before_lots": legacy.recommended_lots,
                    "after_lots": candidate.recommended_lots,
                    "before_start_quantity": legacy.recommended_start_quantity,
                    "after_start_quantity": candidate.recommended_start_quantity,
                }
            )
        if legacy.recommended_start_by != candidate.recommended_start_by:
            timing.append(
                {
                    "modality": modality,
                    "before_start_by": (
                        legacy.recommended_start_by.isoformat()
                        if legacy.recommended_start_by else None
                    ),
                    "after_start_by": (
                        candidate.recommended_start_by.isoformat()
                        if candidate.recommended_start_by else None
                    ),
                }
            )
    return tuple(recommendations), tuple(timing)


class SavedQueue(BaseModel):
    rows: tuple[QueueComparisonRow, ...] = Field(max_length=1000)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_uncovered(self) -> "SavedQueue":
        if any(row.uncovered_after_wip != max(0, row.remaining_demand - row.eligible_wip) for row in self.rows):
            raise ValueError("Uncovered demand does not reconcile with eligible WIP.")
        return self


def compare_queues(
    before: tuple[QueueComparisonRow, ...],
    after: tuple[QueueComparisonRow, ...],
) -> QueueComparisonResult:
    recommendations, timing = _differences(before, after)
    return QueueComparisonResult(
        before_totals=_totals(before),
        after_totals=_totals(after),
        changed_recommendations=recommendations,
        changed_recommendation_count=len(recommendations),
        timing_or_start_date_changes=timing,
        timing_or_start_date_change_count=len(timing),
    )


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise AuthoritativeFlexA4Error("A saved queue has duplicate JSON fields.")
    return fields


def _invalid_constant(_value: str) -> None:
    raise AuthoritativeFlexA4Error("A saved queue contains a non-finite number.")


def load_saved_queue(path: Path) -> SavedQueue:
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise AuthoritativeFlexA4Error("A saved queue must be an ordinary file.")
        with path.open("rb") as stream:
            content = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as exc:
        raise AuthoritativeFlexA4Error("A saved queue is unavailable.") from exc
    if not 0 < len(content) <= MAX_INPUT_BYTES:
        raise AuthoritativeFlexA4Error("A saved queue is empty or exceeds its size limit.")
    try:
        payload = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields,
                             parse_constant=_invalid_constant)
        return SavedQueue.model_validate(payload)
    except AuthoritativeFlexA4Error:
        raise
    except (ValueError, RecursionError) as exc:
        raise AuthoritativeFlexA4Error("A saved queue's schema or uncovered demand is invalid.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path, help="Baseline queue JSON")
    parser.add_argument("after", type=Path, help="Candidate queue JSON")
    args = parser.parse_args()
    try:
        result = compare_queues(load_saved_queue(args.before).rows, load_saved_queue(args.after).rows)
    except AuthoritativeFlexA4Error as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
