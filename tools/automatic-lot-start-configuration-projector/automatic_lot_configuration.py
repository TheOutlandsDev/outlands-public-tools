"""Project a saved policy into offline automatic lot-start calculator rules."""

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MAX_POLICY_BYTES = 1024 * 1024
LOT_PREFIX_PATTERN = r"^LOT[A-Z0-9]{2,8}$"


class AutomaticLotStartError(ValueError):
    """Raised when automatic replenishment cannot be calculated safely."""


class ProductRule(BaseModel):
    modality: str = Field(pattern=r"^[A-Z0-9]{3,12}$")
    part_number: str = Field(min_length=1, max_length=40)
    lot_prefix: str = Field(pattern=LOT_PREFIX_PATTERN)
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


class AutomaticLotStartConfiguration(BaseModel):
    contract_id: Literal["offline-automatic-lot-start-v1"]
    contract_version: str = Field(pattern=r"^0\.[0-9]+\.[0-9]+$")
    status: Literal["DEVELOPMENT_BACKEND_CONTRACT_NO_UI"]
    technical_owner: str
    demand_authority: Literal["SAVED_ORDER_SNAPSHOT"]
    calculation_mode: Literal["AGGREGATED_MODALITY_BACKFILL"]
    remaining_demand_rule: str
    replenishment_factor: Literal["1.00"]
    early_wip_loss_rate: Literal["0.20"]
    rule_boundaries: dict[str, str]
    event_identity: tuple[str, ...]
    configured_products: tuple[ProductRule, ...]
    fail_closed_products: tuple[FailClosedProduct, ...]
    legacy_conflicts: tuple[dict[str, Any], ...]

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_unique_product_contract(self):
        for attribute in ("modality", "part_number", "lot_prefix"):
            values = [getattr(item, attribute) for item in self.configured_products]
            if len(values) != len(set(values)):
                raise ValueError(f"Configured {attribute} values must be unique.")
        configured_parts = {item.part_number for item in self.configured_products}
        failed_parts = {item.part_number for item in self.fail_closed_products}
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
                    f"The {product.modality} automatic lot-start rule is fail closed: "
                    f"{product.reason}."
                )
        raise AutomaticLotStartError("The O&S part number has no controlled Flex rule.")


class PolicyAuthorities(BaseModel):
    demand: Literal["SAVED_ORDER_SNAPSHOT"]
    model_config = ConfigDict(frozen=True, extra="forbid")


class CalculationRules(BaseModel):
    recommendation_factor: Literal["1.00"]
    recommendation_factor_reason: str = Field(min_length=20, max_length=500)
    early_wip_loss_rate: Literal["0.20"]
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class ConfiguredProduct(BaseModel):
    modality: str = Field(pattern=r"^[A-Z0-9]{3,12}$")
    part_number: str = Field(min_length=1, max_length=40)
    lot_prefix: str = Field(pattern=LOT_PREFIX_PATTERN)
    lot_size: int = Field(strict=True, gt=0, le=10000)
    lot_size_status: str = Field(min_length=1, max_length=120)
    lead_time_days: int = Field(strict=True, gt=0, le=365)
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class UnapprovedProduct(FailClosedProduct):
    modality: str = Field(min_length=3, max_length=12)
    part_number: str = Field(min_length=1, max_length=40)
    lot_prefix: str | None = Field(default=None, pattern=LOT_PREFIX_PATTERN)
    reason: str = Field(min_length=10, max_length=300)
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class PolicyProjectionInput(BaseModel):
    technical_owner: str = Field(min_length=1, max_length=160)
    authorities: PolicyAuthorities
    calculation_rules: CalculationRules
    configured_products: tuple[ConfiguredProduct, ...] = Field(min_length=1, max_length=100)
    fail_closed_products: tuple[UnapprovedProduct, ...] = Field(max_length=100)
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_product_identities(self):
        products = (*self.configured_products, *self.fail_closed_products)
        for attribute in ("modality", "part_number", "lot_prefix"):
            values = [
                value.casefold()
                for product in products
                if (value := getattr(product, attribute)) is not None
            ]
            if len(values) != len(set(values)):
                raise ValueError(f"Product {attribute} values must be unique.")
        return self


def project_automatic_lot_start_configuration(
    policy: PolicyProjectionInput,
) -> AutomaticLotStartConfiguration:
    """Project a saved policy into the automatic calculator's input model."""

    return AutomaticLotStartConfiguration.model_validate(
        {
            "contract_id": "offline-automatic-lot-start-v1",
            "contract_version": "0.1.0",
            "status": "DEVELOPMENT_BACKEND_CONTRACT_NO_UI",
            "technical_owner": policy.technical_owner,
            "demand_authority": policy.authorities.demand,
            "calculation_mode": "AGGREGATED_MODALITY_BACKFILL",
            "remaining_demand_rule": (
                "MAX_ZERO_ORDERED_QUANTITY_MINUS_ACCEPTED_SHIP_QUANTITY"
            ),
            "replenishment_factor": policy.calculation_rules.recommendation_factor,
            "early_wip_loss_rate": policy.calculation_rules.early_wip_loss_rate,
            "rule_boundaries": {
                "replenishment_factor": (
                    policy.calculation_rules.recommendation_factor_reason
                ),
                "early_wip_loss_rate": (
                    "Apply only when valuing WIP at controlled early-stage "
                    "operations; never change physical lot-start quantity."
                ),
                "priority": "No manual priority field is permitted.",
                "mes": "No MES write, release, or lot creation is permitted.",
                "ui": "Shadow projection only; no runtime reader is activated.",
            },
            # Preserve the current event fingerprint namespace during shadow proof.
            # A policy-revision migration requires its own database compatibility gate.
            "event_identity": (
                "contract_version",
                "os_order_id",
                "os_row_version",
                "canonical_order_state",
            ),
            "configured_products": [
                {
                    "modality": item.modality,
                    "part_number": item.part_number,
                    "lot_prefix": item.lot_prefix,
                    "start_quantity": item.lot_size,
                    "lead_time_days": item.lead_time_days,
                    "status": item.lot_size_status,
                }
                for item in policy.configured_products
            ],
            "fail_closed_products": [item.model_dump() for item in policy.fail_closed_products],
            "legacy_conflicts": [],
        }
    )


def replay_rules(configuration: AutomaticLotStartConfiguration) -> dict:
    fields = {"contract_version", "configured_products", "fail_closed_products"}
    return configuration.model_dump(mode="json", include=fields)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-JSON constant")


def read_policy(path: Path) -> PolicyProjectionInput:
    try:
        with path.open("rb") as stream:
            payload = stream.read(MAX_POLICY_BYTES + 1)
    except OSError:
        raise ValueError("Unable to read the policy JSON.") from None

    if len(payload) > MAX_POLICY_BYTES:
        raise ValueError("The policy JSON exceeds the 1 MiB limit.")

    try:
        data = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_object,
                           parse_constant=reject_constant)
        return PolicyProjectionInput.model_validate(data)
    except (ValueError, RecursionError):
        raise ValueError("Invalid policy JSON.") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", type=Path, help="Saved offline policy JSON")
    parser.add_argument("--format", choices=("configuration", "replay"), default="configuration",
                        help="Export the full configuration or the published replay reporter's rules")
    args = parser.parse_args()
    try:
        configuration = project_automatic_lot_start_configuration(read_policy(args.policy))
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")

    report = replay_rules(configuration) if args.format == "replay" else configuration.model_dump(mode="json")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
