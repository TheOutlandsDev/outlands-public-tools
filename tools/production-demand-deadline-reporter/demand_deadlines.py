"""Summarize overdue and upcoming production demand from a saved allocation report."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict, Field, model_validator

from order_needs import OrderNeedsResult, _read_json


class PTLProductionExceptionMetrics(BaseModel):
    """Production-owned exceptions after shipping and PTL clearance are removed."""

    generated_on: date
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    production_order_lines: int = Field(ge=0)
    production_quantity: int = Field(ge=0)
    late_order_lines: int = Field(ge=0)
    late_quantity: int = Field(ge=0)
    due_within_seven_days_order_lines: int = Field(ge=0)
    due_within_seven_days_quantity: int = Field(ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_bounded_exceptions(self) -> "PTLProductionExceptionMetrics":
        exception_lines = (
            self.late_order_lines + self.due_within_seven_days_order_lines
        )
        exception_quantity = self.late_quantity + self.due_within_seven_days_quantity
        if exception_lines > self.production_order_lines:
            raise ValueError("PTL exception lines exceed current production demand.")
        if exception_quantity > self.production_quantity:
            raise ValueError("PTL exception quantity exceeds current production demand.")
        return self


def build_ptl_production_exception_metrics(
    order_needs: OrderNeedsResult,
    *,
    generated_on: date | None = None,
) -> PTLProductionExceptionMetrics:
    """Count only authoritative demand that still belongs to Flex production."""

    current_date = generated_on or order_needs.generated_at.date()
    due_through = current_date + timedelta(days=7)
    late_rows = tuple(row for row in order_needs.rows if row.due_date < current_date)
    due_soon_rows = tuple(
        row
        for row in order_needs.rows
        if current_date <= row.due_date <= due_through
    )
    return PTLProductionExceptionMetrics(
        generated_on=current_date,
        source_revision_sha256=order_needs.source.revision_sha256,
        production_order_lines=sum(
            row.order_line_count for row in order_needs.rows
        ),
        production_quantity=sum(row.remaining_demand for row in order_needs.rows),
        late_order_lines=sum(row.order_line_count for row in late_rows),
        late_quantity=sum(row.remaining_demand for row in late_rows),
        due_within_seven_days_order_lines=sum(
            row.order_line_count for row in due_soon_rows
        ),
        due_within_seven_days_quantity=sum(
            row.remaining_demand for row in due_soon_rows
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Saved Order Demand and WIP Allocation report")
    parser.add_argument("--as-of", type=date.fromisoformat)
    args = parser.parse_args()
    try:
        report = OrderNeedsResult.model_validate(_read_json(args.input))
        metrics = build_ptl_production_exception_metrics(report, generated_on=args.as_of)
    except (ValueError, OverflowError):
        print("Invalid deadline input. Check the allocation report and report date.", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((metrics.model_dump_json() + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
