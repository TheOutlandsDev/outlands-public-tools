"""Project a saved planning policy for the offline lot-start calculator."""

import argparse
import json
from math import isfinite
from pathlib import Path
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


MAX_POLICY_BYTES = 1024 * 1024


class PolicyProjectionError(ValueError):
    """The saved policy cannot produce an offline reservation policy."""


class CalculationRules(BaseModel):
    recommendation_factor: Literal["1.00"]
    legacy_comparison_factor: Literal["1.10"]
    legacy_comparison_factor_status: Literal["COMPARISON_ONLY_NOT_EXECUTABLE"]
    verification_lots_advance_standard_sequence: Literal[False]

    model_config = ConfigDict(frozen=True, extra="forbid")


class IdentityRules(BaseModel):
    identity_sources_required: tuple[str, ...] = Field(min_length=1)
    verification_lots_remain_linked_to_standard_base: Literal[True]

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_sources(self):
        if not all(self.identity_sources_required) or len(set(self.identity_sources_required)) != len(
            self.identity_sources_required
        ):
            raise ValueError("Identity sources must be nonempty and unique.")
        return self


class ConfiguredProduct(BaseModel):
    modality: str = Field(pattern=r"^[A-Z0-9]{3,12}$")
    part_number: str = Field(min_length=1, max_length=40)
    lot_prefix: str = Field(pattern=r"^[A-Z0-9-]{3,20}$")
    lot_size: int = Field(gt=0, le=10_000)
    recommendation_status: Literal["CONFIGURED"]

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class FailClosedProduct(BaseModel):
    modality: str = Field(min_length=3, max_length=12)
    part_number: str = Field(min_length=1, max_length=40)
    lot_prefix: str | None = Field(default=None, max_length=20)
    reason: str = Field(min_length=10, max_length=300)

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class PolicyProjectionInput(BaseModel):
    policy_id: str = Field(min_length=1, max_length=120)
    technical_owner: str = Field(min_length=1, max_length=120)
    calculation_rules: CalculationRules
    event_and_identity_rules: IdentityRules
    configured_products: tuple[ConfiguredProduct, ...] = Field(min_length=1)
    fail_closed_products: tuple[FailClosedProduct, ...]

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_product_identities(self):
        all_products = (*self.configured_products, *self.fail_closed_products)
        for key in ("modality", "part_number"):
            values = [getattr(product, key).casefold() for product in all_products]
            if len(values) != len(set(values)):
                raise ValueError("Product modalities and part numbers must be unique across both lists.")
        prefixes = {product.lot_prefix for product in self.configured_products}
        if len(prefixes) != len(self.configured_products):
            raise ValueError("Configured product prefixes must be unique.")
        return self


def project_lot_start_policy(
    policy: PolicyProjectionInput,
) -> dict[str, Any]:
    """Project a candidate into the reservation calculator's policy dictionary."""

    return {
        "policy_id": policy.policy_id,
        "policy_version": "1.0.0",
        "status": "CANDIDATE_SHADOW_ONLY",
        "technical_owner": policy.technical_owner,
        "rule_resolution": {
            "mode": "AUTHORITATIVE_PRODUCT_SPECIFIC",
            "active_uncovered_demand_factor": (
                policy.calculation_rules.recommendation_factor
            ),
            "legacy_uncovered_demand_factor": (
                policy.calculation_rules.legacy_comparison_factor
            ),
            "legacy_factor_status": (
                policy.calculation_rules.legacy_comparison_factor_status
            ),
            "production_authority": False,
        },
        "configured_products": [
            {
                "modality": item.modality,
                "part_number": item.part_number,
                "lot_prefix": item.lot_prefix,
                "lot_size": item.lot_size,
                "start_factor": policy.calculation_rules.recommendation_factor,
                "status": item.recommendation_status,
            }
            for item in policy.configured_products
        ],
        "fail_closed_products": [item.model_dump() for item in policy.fail_closed_products],
        "identity_sources_required": list(
            policy.event_and_identity_rules.identity_sources_required
        ),
        "verification_policy": {
            "verification_lots_advance_standard_sequence": (
                policy.calculation_rules.verification_lots_advance_standard_sequence
            ),
            "verification_lots_remain_linked_to_standard_base": (
                policy.event_and_identity_rules.verification_lots_remain_linked_to_standard_base
            ),
        },
        "activation_gate": {
            "policy_reviewed": True,
            "shadow_projection_validated": True,
            "development_cutover_authorized": False,
            "production_included": False,
        },
    }


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyProjectionError("The policy contains a duplicate JSON field.")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise PolicyProjectionError("The policy contains a nonfinite JSON value.")


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        _invalid_constant(value)
    return number


def _load_policy(path: Path) -> PolicyProjectionInput:
    try:
        if not path.is_file():
            raise PolicyProjectionError("The policy must be a readable file.")
        with path.open("rb") as stream:
            raw = stream.read(MAX_POLICY_BYTES + 1)
    except OSError as exc:
        raise PolicyProjectionError("The policy could not be read.") from exc
    if len(raw) > MAX_POLICY_BYTES:
        raise PolicyProjectionError("The policy exceeds the 1 MiB input limit.")
    try:
        content = json.loads(
            raw.decode("utf-8-sig"), object_pairs_hook=_unique_fields,
            parse_constant=_invalid_constant, parse_float=_finite_float,
        )
    except PolicyProjectionError:
        raise
    except (ValueError, RecursionError) as exc:
        raise PolicyProjectionError("The policy is not valid JSON.") from exc
    try:
        return PolicyProjectionInput.model_validate(content)
    except ValidationError as exc:
        raise PolicyProjectionError("The policy does not match the reservation projection schema.") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("policy", type=Path)
    args = parser.parse_args(argv)
    try:
        report = project_lot_start_policy(_load_policy(args.policy))
    except PolicyProjectionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
