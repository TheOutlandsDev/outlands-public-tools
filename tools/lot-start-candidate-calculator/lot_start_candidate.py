"""Calculate development lot-start candidates from a saved policy and request."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_CEILING, localcontext
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_DEMAND = 1_000_000_000
PREFIX = re.compile(r"[A-Z0-9-]{3,20}")
FACTOR = re.compile(r"[0-9]{1,12}(?:\.[0-9]{1,12})?")


class LotStartPolicyError(ValueError):
    """Raised when a lot-start candidate cannot be produced safely."""


class UnavailableLotRule(LotStartPolicyError):
    """The selected modality lacks a configured rule."""


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
    planned_capacity_circuits: int
    capacity_above_uncovered: int
    proposed_lot_ids: tuple[str, ...]
    authority: str = "DEVELOPMENT_CANDIDATE_NOT_RESERVED"

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
    policy: dict[str, Any],
) -> LotStartRecommendation:
    """Calculate a candidate without reserving or writing any identity."""

    if uncovered_demand < 0:
        raise LotStartPolicyError("Uncovered demand cannot be negative.")
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
        raise UnavailableLotRule(f"The {modality} lot-start rule is unavailable: {reason}.")

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
        planned_capacity_circuits=planned_capacity,
        capacity_above_uncovered=max(0, planned_capacity - uncovered_demand),
        proposed_lot_ids=proposed_lot_ids,
    )


def unique_fields(pairs):
    result = dict(pairs)
    if len(pairs) != len(result):
        raise LotStartPolicyError("Duplicate JSON field")
    return result


def read_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise LotStartPolicyError(f"Expected a saved {label} file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise LotStartPolicyError(f"{label.capitalize()} exceeds the 4 MiB limit")
    try:
        result = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_fields)
    except (ValueError, RecursionError) as exc:
        raise LotStartPolicyError(f"Invalid {label} JSON") from exc
    if not isinstance(result, dict):
        raise LotStartPolicyError(f"Expected a JSON object for the {label}")
    return result


def text_field(value: object, maximum: int) -> bool:
    return isinstance(value, str) and 0 < len(value) <= maximum and value.isprintable() and bool(value.strip())


def load_lot_start_policy(path: Path) -> dict[str, Any]:
    policy = read_object(path, "lot-start policy")
    if policy.get("policy_version") != "1.0.0":
        raise LotStartPolicyError("The lot-start policy version is unsupported")
    modalities = set()
    prefixes = set()
    for list_name in ("configured_products", "fail_closed_products"):
        products = policy.get(list_name)
        if not isinstance(products, list) or len(products) > 1000:
            raise LotStartPolicyError("The policy requires bounded configured and fail-closed product arrays")
        for product in products:
            if not isinstance(product, dict) or not text_field(product.get("modality"), 120):
                raise LotStartPolicyError("Invalid product modality in the policy")
            modality = product["modality"]
            if modality in modalities:
                raise LotStartPolicyError("Duplicate product modality in the policy")
            modalities.add(modality)
            if list_name == "fail_closed_products":
                if not text_field(product.get("reason"), 300):
                    raise LotStartPolicyError("A fail-closed product needs a reason")
                continue
            part, prefix, size, factor = (product.get(name) for name in
                                         ("part_number", "lot_prefix", "lot_size", "start_factor"))
            if not text_field(part, 120) or not isinstance(prefix, str) or not PREFIX.fullmatch(prefix):
                raise LotStartPolicyError("Invalid configured part number or lot prefix")
            if prefix in prefixes:
                raise LotStartPolicyError("Duplicate configured lot prefix")
            prefixes.add(prefix)
            if type(size) is not int or not 1 <= size <= MAX_DEMAND:
                raise LotStartPolicyError("Configured lot size must be a positive bounded integer")
            if not isinstance(factor, str) or not FACTOR.fullmatch(factor) or Decimal(factor) <= 0:
                raise LotStartPolicyError("Configured start factor must be a positive decimal string")
    return policy


def read_request(path: Path) -> dict:
    request = read_object(path, "lot-start request")
    if set(request) != {"modality", "uncovered_demand", "observed_lot_ids"}:
        raise LotStartPolicyError("The request requires modality, uncovered demand, and observed lot IDs")
    modality, demand, history = (request[key] for key in ("modality", "uncovered_demand", "observed_lot_ids"))
    if not text_field(modality, 120) or type(demand) is not int or not 0 <= demand <= MAX_DEMAND:
        raise LotStartPolicyError("The request requires a modality and bounded nonnegative integer demand")
    if (not isinstance(history, list) or len(history) > 20_000
            or any(not text_field(value, 128) for value in history)):
        raise LotStartPolicyError("The request requires bounded observed lot IDs")
    return request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", type=Path)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        policy = load_lot_start_policy(args.policy)
        request = read_request(args.request)
        with localcontext() as context:
            context.prec = 40
            result = recommend_lot_start(policy=policy, **request)
    except UnavailableLotRule:
        print("Lot-start candidate: No configured lot-start rule for the requested modality", file=sys.stderr)
        return 2
    except LotStartPolicyError as exc:
        print(f"Lot-start candidate: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("Lot-start candidate: Cannot read the saved inputs", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
