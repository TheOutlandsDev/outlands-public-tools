"""Check whether a saved prior order void applies to a candidate order."""

import argparse
import json
from pathlib import Path
import sys
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, ValidationError


class OrderIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    row_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    source_sheet: Literal["C", "P"]
    source_row: int = Field(ge=4, le=500)
    part_number: str
    purchase_order: str | None
    po_line: str | None
    quantity: int = Field(gt=0)
    commit_date: date


class PreviousOrder(OrderIdentity):
    revision_sha256: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9a-f]{64}$")]
    row_version: int = Field(ge=1)
    voided_at: AwareDatetime | None
    voided_by: str | None
    void_reason: str | None


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    candidate: OrderIdentity
    previous: PreviousOrder | None = None


def _exact_void_carryover(
    previous: dict[str, Any] | None,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Carry a void only when the complete governed order identity is unchanged."""

    if previous is None or previous.get("voided_at") is None:
        return {}
    identity_fields = (
        "row_id",
        "source_sheet",
        "source_row",
        "part_number",
        "purchase_order",
        "po_line",
        "quantity",
        "commit_date",
    )
    if any(previous.get(field) != candidate.get(field) for field in identity_fields):
        return {}
    return {
        "row_version": int(previous["row_version"]),
        "voided_at": previous["voided_at"],
        "voided_by": previous["voided_by"],
        "void_reason": previous["void_reason"],
        "previous_revision_sha256": str(previous["revision_sha256"]).strip(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="Path to a saved JSON request")
    args = parser.parse_args()
    try:
        data = args.request.read_bytes()
    except OSError:
        print("Order void carryover request could not be read.", file=sys.stderr)
        return 2
    try:
        request = Request.model_validate_json(data)
    except ValidationError:
        print("Invalid order void carryover request.", file=sys.stderr)
        return 2

    previous = request.previous.model_dump(mode="json") if request.previous is not None else None
    carryover = _exact_void_carryover(previous, request.candidate.model_dump(mode="json"))
    print(json.dumps({"eligible": bool(carryover), "carryover": carryover}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
