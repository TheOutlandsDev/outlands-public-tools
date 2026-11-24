"""Check whether two saved planning policies preserve their product rules."""

import argparse
import json
from math import isfinite
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


MAX_POLICY_BYTES = 1024 * 1024


class AutomaticLotStartError(ValueError):
    """A part has no executable lot-start rule."""


class PolicyParityError(ValueError):
    """The snapshots are invalid or differ on governed product rules."""


class ProductRule(BaseModel):
    modality: str = Field(pattern=r"^[A-Z0-9]{3,12}$")
    part_number: str = Field(min_length=1, max_length=40)
    lot_prefix: str = Field(pattern=r"^[A-Z0-9-]{3,20}$")
    start_quantity: int = Field(gt=0, le=10000)
    lead_time_days: int = Field(gt=0, le=365)
    status: str

    model_config = ConfigDict(frozen=True, extra="forbid")


class FailClosedProduct(BaseModel):
    modality: str
    part_number: str
    lot_prefix: str | None
    reason: str

    model_config = ConfigDict(frozen=True, extra="forbid")


class PolicySnapshot(BaseModel):
    configured_products: tuple[ProductRule, ...]
    fail_closed_products: tuple[FailClosedProduct, ...]

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_unique_product_contract(self):
        for attribute in ("modality", "part_number", "lot_prefix"):
            values = [getattr(item, attribute) for item in self.configured_products]
            if len(values) != len(set(values)):
                raise ValueError(f"Configured {attribute} values must be unique.")
        configured_parts = {item.part_number for item in self.configured_products}
        failed_parts = {item.part_number for item in self.fail_closed_products}
        if len(failed_parts) != len(self.fail_closed_products):
            raise ValueError("Blocked part numbers must be unique.")
        if configured_parts & failed_parts:
            raise ValueError("A product cannot be both configured and fail closed.")
        return self

    def product_for_part(self, part_number: str) -> ProductRule:
        normalized = part_number.strip().upper()
        for product in self.configured_products:
            if product.part_number.upper() == normalized:
                return product
        for product in self.fail_closed_products:
            if product.part_number.upper() == normalized:
                raise AutomaticLotStartError(
                    f"The {product.modality} lot-start rule is fail closed: "
                    f"{product.reason}."
                )
        raise AutomaticLotStartError("The part number has no configured rule.")


def _validate_configured_products(
    legacy: PolicySnapshot,
    authoritative: PolicySnapshot,
) -> None:
    def values(configuration: PolicySnapshot):
        return {
            product.modality: (
                product.part_number,
                product.lot_prefix,
                product.start_quantity,
                product.lead_time_days,
            )
            for product in configuration.configured_products
        }

    if values(legacy) != values(authoritative):
        raise PolicyParityError(
            "The configured product semantics differ between policies."
        )


def _verify_fail_closed(
    legacy: PolicySnapshot,
    authoritative: PolicySnapshot,
) -> int:
    legacy_products = {item.part_number for item in legacy.fail_closed_products}
    candidate_products = {
        item.part_number for item in authoritative.fail_closed_products
    }
    if legacy_products != candidate_products or len(legacy_products) != 11:
        raise PolicyParityError("The fail-closed product set has drifted.")
    for part_number in sorted(legacy_products):
        for configuration in (legacy, authoritative):
            try:
                configuration.product_for_part(part_number)
            except AutomaticLotStartError:
                continue
            raise PolicyParityError(
                "An unapproved product unexpectedly resolved to a planning rule."
            )
    return len(legacy_products)


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyParityError("The policy contains a duplicate JSON field.")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise PolicyParityError("The policy contains a nonfinite JSON value.")


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        _invalid_constant(value)
    return number


def _load_policy(path: Path) -> PolicySnapshot:
    try:
        if not path.is_file():
            raise PolicyParityError("The policy must be a readable file.")
        with path.open("rb") as stream:
            raw = stream.read(MAX_POLICY_BYTES + 1)
    except OSError as exc:
        raise PolicyParityError("The policy could not be read.") from exc
    if len(raw) > MAX_POLICY_BYTES:
        raise PolicyParityError("The policy exceeds the 1 MiB input limit.")
    try:
        content = json.loads(
            raw.decode("utf-8-sig"), object_pairs_hook=_unique_fields,
            parse_constant=_invalid_constant, parse_float=_finite_float,
        )
    except PolicyParityError:
        raise
    except (ValueError, RecursionError) as exc:
        raise PolicyParityError("The policy is not valid JSON.") from exc
    try:
        return PolicySnapshot.model_validate(content)
    except ValidationError as exc:
        raise PolicyParityError("The policy does not match the product snapshot schema.") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args(argv)
    try:
        baseline = _load_policy(args.baseline)
        candidate = _load_policy(args.candidate)
        _validate_configured_products(baseline, candidate)
        blocked_count = _verify_fail_closed(baseline, candidate)
    except PolicyParityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "status": "equivalent",
        "configured_products": len(baseline.configured_products),
        "fail_closed_products": blocked_count,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
