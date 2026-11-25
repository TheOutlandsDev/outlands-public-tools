"""Separate verification lots from eligible fulfillment WIP."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MAX_INPUT_BYTES = 4 * 1024 * 1024
Identifier = Annotated[str, StringConstraints(min_length=1, max_length=256)]
Kanban = Annotated[int, Field(strict=True, ge=1, le=6)]


class EligibilityError(ValueError):
    """A saved WIP or override input cannot be validated."""


class AssignedWIPRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    lot_id: Identifier
    source_product: Identifier
    canonical_product: Identifier
    current_step: Identifier
    kanban: Kanban
    total_parts: int = Field(strict=True, ge=0)


class AssignmentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    records: tuple[AssignedWIPRecord, ...] = Field(max_length=10_000)

    @model_validator(mode="after")
    def unique_lots(self):
        if len({row.lot_id.casefold() for row in self.records}) != len(self.records):
            raise ValueError("Assigned lot identities must be unique")
        return self


class KanbanOverride(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    part_number: Identifier
    operation: Identifier
    kanban: Kanban


class OverrideConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contextual_kanban_overrides: tuple[KanbanOverride, ...] = Field(max_length=1000)

    @model_validator(mode="after")
    def unique_keys(self):
        rules = self.contextual_kanban_overrides
        if len({(row.part_number, row.operation) for row in rules}) != len(rules):
            raise ValueError("Each part and operation can have one override")
        return self


class VerificationSupply(BaseModel):
    lot_id: str
    source_product: str
    canonical_product: str
    kanban: int = Field(ge=1, le=6)
    quantity: int = Field(ge=0)
    policy: Literal["Excluded from standard production allocation"] = (
        "Excluded from standard production allocation"
    )

    model_config = ConfigDict(frozen=True)


def _is_verification(row: AssignedWIPRecord) -> bool:
    product = row.source_product.upper()
    return (
        row.source_product != row.canonical_product
        or row.lot_id.upper().startswith("V")
        or product.endswith("V")
        or product.endswith("-V")
    )


def project_eligibility(report: AssignmentReport, configuration: OverrideConfiguration) -> dict:
    verification: list[VerificationSupply] = []
    eligible = []
    totals: dict[str, int] = defaultdict(int)
    overrides = {(row.part_number, row.operation): row.kanban
                 for row in configuration.contextual_kanban_overrides}
    for row in report.records:
        if _is_verification(row):
            verification.append(VerificationSupply(
                lot_id=row.lot_id,
                source_product=row.source_product,
                canonical_product=row.canonical_product,
                kanban=row.kanban,
                quantity=row.total_parts,
            ))
            continue
        eligible.append({
            "part_number": row.canonical_product,
            "lot_id": row.lot_id,
            "kanban": overrides.get((row.canonical_product, row.current_step), row.kanban),
            "operation": row.current_step,
            "quantity": row.total_parts,
        })
        totals[row.canonical_product] += row.total_parts

    return {
        "status": "PASS",
        "input_parts": sum(row.total_parts for row in report.records),
        "eligible_parts": sum(totals.values()),
        "verification_parts": sum(row.quantity for row in verification),
        "eligible_by_product": dict(sorted(totals.items())),
        "eligible_supply": eligible,
        "verification_supply": [row.model_dump() for row in sorted(verification, key=lambda item: item.lot_id)],
    }


def unique_fields(pairs):
    result = dict(pairs)
    if len(pairs) != len(result):
        raise ValueError("Duplicate JSON field")
    return result


def read_model(path: Path, model, label: str):
    if not path.is_file():
        raise EligibilityError(f"Expected a saved {label} file")
    with path.open("rb") as stream:
        content = stream.read(MAX_INPUT_BYTES + 1)
    if len(content) > MAX_INPUT_BYTES:
        raise EligibilityError(f"{label.capitalize()} exceeds the 4 MiB limit")
    try:
        data = json.loads(content.decode("utf-8-sig"), object_pairs_hook=unique_fields)
        return model.model_validate(data)
    except (ValueError, RecursionError) as exc:
        raise EligibilityError(f"Invalid {label} JSON") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assignment", type=Path)
    parser.add_argument("--overrides", type=Path)
    args = parser.parse_args()
    try:
        report = read_model(args.assignment, AssignmentReport, "assignment report")
        configuration = (read_model(args.overrides, OverrideConfiguration, "override configuration")
                         if args.overrides else OverrideConfiguration(contextual_kanban_overrides=()))
    except EligibilityError as exc:
        print(f"WIP eligibility: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("WIP eligibility: cannot read the saved inputs", file=sys.stderr)
        return 2
    print(json.dumps(project_eligibility(report, configuration), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
