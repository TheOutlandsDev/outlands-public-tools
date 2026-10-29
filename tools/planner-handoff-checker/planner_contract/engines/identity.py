"""Explicit local lot proposals; no production execution or reservation."""

from __future__ import annotations

from dataclasses import asdict,dataclass

from decimal import Decimal,ROUND_CEILING

import re

from typing import Any,Iterable

class LotStartPolicyError(ValueError):
    """Raised when a lot-start candidate cannot be produced safely."""


@dataclass(frozen=True)
class LotStartRecommendation:
    modality: str
    part_number: str
    lot_prefix: str
    uncovered_demand: int
    start_factor: str
    allowance_demand: int
    lot_size: int
    recommended_lot_count: int
    planned_capacity_units: int
    capacity_above_uncovered: int
    proposed_lot_ids: tuple[str, ...]
    authority: str = "LOCAL_CANDIDATE_NOT_RESERVED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _letters_to_number(value: str) -> int:
    result = 0
    for character in value:
        result = result * 26 + (ord(character) - ord("A"))
    return result


def _number_to_letters(value: int, *, width: int = 4) -> str:
    if value < 0 or value >= 26**width:
        raise LotStartPolicyError("The standard lot sequence is exhausted.")
    characters = ["A"] * width
    for index in range(width - 1, -1, -1):
        characters[index] = chr(ord("A") + value % 26)
        value //= 26
    return "".join(characters)


def propose_standard_lot_ids(
    *,
    lot_prefix: str,
    observed_lot_ids: Iterable[str],
    count: int,
) -> tuple[str, ...]:
    """Propose identities after all observed and non-reusable reservations."""

    if not re.fullmatch(r"[A-Z0-9-]{3,20}", lot_prefix):
        raise LotStartPolicyError("The lot prefix is invalid.")
    if count < 0 or count > 100:
        raise LotStartPolicyError("The proposed lot count is outside the bounded limit.")
    if count == 0:
        return ()
    pattern = re.compile(rf"^{re.escape(lot_prefix)}([A-Z]{{4}})$")
    standard_sequences: list[int] = []
    for raw_lot_id in observed_lot_ids:
        lot_id = str(raw_lot_id).strip().upper()
        match = pattern.fullmatch(lot_id)
        if match:
            standard_sequences.append(_letters_to_number(match.group(1)))
    if not standard_sequences:
        raise LotStartPolicyError(
            "No standard historical lot identity is available for safe sequencing."
        )
    next_sequence = max(standard_sequences) + 1
    return tuple(
        f"{lot_prefix}{_number_to_letters(next_sequence + offset)}"
        for offset in range(count)
    )


def recommend_lot_start(
    *,
    modality: str,
    uncovered_demand: int,
    observed_lot_ids: Iterable[str],
    policy: dict[str, Any] | None = None,
) -> LotStartRecommendation:
    """Calculate a candidate without reserving or writing any identity."""

    if uncovered_demand < 0:
        raise LotStartPolicyError("Uncovered demand cannot be negative.")
    if policy is None:
        raise LotStartPolicyError("Explicit policy required.")
    active_policy = policy
    product = next(
        (
            item
            for item in active_policy["configured_products"]
            if item["modality"] == modality
        ),
        None,
    )
    if product is None:
        pending = next(
            (
                item
                for item in active_policy["fail_closed_products"]
                if item["modality"] == modality
            ),
            None,
        )
        reason = pending["reason"] if pending else "No product-specific rule is configured"
        raise LotStartPolicyError(f"The {modality} lot-start rule is unavailable: {reason}.")

    factor = Decimal(product["start_factor"])
    lot_size = int(product["lot_size"])
    allowance_demand = int(
        (Decimal(uncovered_demand) * factor).to_integral_value(rounding=ROUND_CEILING)
    )
    lot_count = (
        (allowance_demand + lot_size - 1) // lot_size if allowance_demand else 0
    )
    proposed_lot_ids = propose_standard_lot_ids(
        lot_prefix=product["lot_prefix"],
        observed_lot_ids=observed_lot_ids,
        count=lot_count,
    )
    planned_capacity = lot_count * lot_size
    return LotStartRecommendation(
        modality=modality,
        part_number=product["part_number"],
        lot_prefix=product["lot_prefix"],
        uncovered_demand=uncovered_demand,
        start_factor=str(factor),
        allowance_demand=allowance_demand,
        lot_size=lot_size,
        recommended_lot_count=lot_count,
        planned_capacity_units=planned_capacity,
        capacity_above_uncovered=max(0, planned_capacity - uncovered_demand),
        proposed_lot_ids=proposed_lot_ids,
    )
