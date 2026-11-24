"""Verify reviewed differences between two saved planning-policy results."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import sys
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

MAX_BYTES = 2 * 1024 * 1024
DETAILED = "reviewed-difference-detailed-planning"
RESERVATION = "reviewed-difference-reservation-boundary"
Quantity = Annotated[StrictInt, Field(ge=0)]


class AuthoritativeFlexShadowError(ValueError):
    """Raised when A2 cannot prove the shadow comparison safely."""


class ReviewedDifference(BaseModel):
    legacy_result: tuple[Quantity, ...]
    authoritative_result: tuple[Quantity, ...]
    reason: str = Field(min_length=40, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class ShadowCaseResult(BaseModel):
    case_id: str
    classification: Literal[
        "MATCH", "REVIEWED_DIFFERENCE", "DEFERRED_MIGRATION"
    ]
    legacy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authoritative_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    legacy_result: tuple[int, ...] | None = None
    authoritative_result: tuple[int, ...] | None = None
    database_writes: Literal[False] = False
    reservation_created: Literal[False] = False

    model_config = ConfigDict(frozen=True, extra="forbid")


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _case(
    case_id: str,
    legacy: Any,
    authoritative: Any,
    *,
    reviewed: ReviewedDifference | None = None,
) -> ShadowCaseResult:
    legacy_bytes = _canonical(legacy)
    authoritative_bytes = _canonical(authoritative)
    if reviewed is None:
        if legacy_bytes != authoritative_bytes:
            raise AuthoritativeFlexShadowError(
                f"The {case_id} shadow comparison produced an unexpected difference."
            )
        classification = "MATCH"
        legacy_result = authoritative_result = None
    else:
        legacy_result = tuple(legacy)
        authoritative_result = tuple(authoritative)
        if legacy_result != reviewed.legacy_result:
            raise AuthoritativeFlexShadowError(
                f"The {case_id} legacy result differs from its reviewed evidence."
            )
        if authoritative_result != reviewed.authoritative_result:
            raise AuthoritativeFlexShadowError(
                f"The {case_id} authoritative result differs from its reviewed evidence."
            )
        if legacy_result == authoritative_result:
            raise AuthoritativeFlexShadowError(
                f"The {case_id} reviewed difference unexpectedly disappeared."
            )
        classification = "REVIEWED_DIFFERENCE"
    return ShadowCaseResult(
        case_id=case_id,
        classification=classification,
        legacy_sha256=sha256(legacy_bytes).hexdigest(),
        authoritative_sha256=sha256(authoritative_bytes).hexdigest(),
        legacy_result=legacy_result,
        authoritative_result=authoritative_result,
    )


class ReservationResult(BaseModel):
    recommended_lot_count: Quantity
    allowance_demand: Quantity

    model_config = ConfigDict(extra="forbid", frozen=True)

    def comparison_vector(self) -> tuple[int, int]:
        return self.recommended_lot_count, self.allowance_demand


class PlanningSnapshot(BaseModel):
    detailed_planning: dict[str, Any]
    reservation_boundary: ReservationResult

    model_config = ConfigDict(extra="forbid", frozen=True)


class ReviewEvidence(BaseModel):
    detailed_planning: ReviewedDifference
    reservation_boundary: ReviewedDifference

    model_config = ConfigDict(extra="forbid", frozen=True)


class VerificationResult(BaseModel):
    cases: tuple[ShadowCaseResult, ShadowCaseResult]

    model_config = ConfigDict(frozen=True)


def _start_quantities(value: object) -> tuple[int, ...]:
    if not isinstance(value, list) or not value or any(
        type(item) is not int or item < 0 for item in value
    ):
        raise AuthoritativeFlexShadowError("Detailed planning requires a nonempty start quantity list.")
    return tuple(value)


def verify_policy_differences(
    legacy: PlanningSnapshot, authoritative: PlanningSnapshot, reviewed: ReviewEvidence
) -> VerificationResult:
    legacy_result = dict(legacy.detailed_planning)
    authoritative_result = dict(authoritative.detailed_planning)
    legacy_starts = _start_quantities(legacy_result.pop("recommended_start_by_order", None))
    authoritative_starts = _start_quantities(authoritative_result.pop("recommended_start_by_order", None))
    # Canonical comparison preserves JSON types that Python equality can conflate.
    if _canonical(legacy_result) != _canonical(authoritative_result):
        raise AuthoritativeFlexShadowError(
            "Detailed planning changed outside the reviewed factor result."
        )
    return VerificationResult(cases=(
        _case(DETAILED, legacy_starts, authoritative_starts, reviewed=reviewed.detailed_planning),
        _case(
            RESERVATION, legacy.reservation_boundary.comparison_vector(),
            authoritative.reservation_boundary.comparison_vector(),
            reviewed=reviewed.reservation_boundary,
        ),
    ))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuthoritativeFlexShadowError("A saved input contains duplicate JSON fields.")
        result[key] = value
    return result


def _reject_nonfinite(_value):
    raise AuthoritativeFlexShadowError("A saved input contains a nonfinite number.")


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        _reject_nonfinite(value)
    return number


def read_input(path: Path, model: type[BaseModel]):
    if not path.is_file():
        raise AuthoritativeFlexShadowError("A saved input must be a regular file.")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise AuthoritativeFlexShadowError("A saved input is empty or exceeds its size limit.")
    payload = json.loads(
        data.decode("utf-8"), object_pairs_hook=_unique_object,
        parse_constant=_reject_nonfinite, parse_float=_finite_float,
    )
    return model.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("authoritative", type=Path)
    parser.add_argument("review", type=Path)
    args = parser.parse_args(argv)
    try:
        legacy = read_input(args.legacy, PlanningSnapshot)
        authoritative = read_input(args.authoritative, PlanningSnapshot)
        reviewed = read_input(args.review, ReviewEvidence)
        report = verify_policy_differences(legacy, authoritative, reviewed)
        output = report.model_dump_json(indent=2)
    except AuthoritativeFlexShadowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: A saved input is unreadable or invalid.", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
