"""Input models for saved planning configuration."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanningValidationError(ValueError):
    """Raised when planning input cannot be evaluated safely."""


class ReviewStatus(str, Enum):
    """Manufacturing-authority status for a controlled planning value."""

    DRAFT_LEGACY_SOURCE = "DRAFT_LEGACY_SOURCE"


class ParameterProvenance(BaseModel):
    """Traceability attached to one reviewed group of planning values."""

    source: str = Field(min_length=1, max_length=256)
    review_status: ReviewStatus
    reviewed_by: str = Field(min_length=1, max_length=120)
    reviewed_on: date

    model_config = ConfigDict(frozen=True)


class PriorityRuleConfiguration(BaseModel):
    """Explicit replacement for the legacy priority thresholds."""

    severe_schedule_lateness_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_min_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_max_days: int = Field(gt=0, le=365)
    future_shipment_rank_limit: int = Field(ge=2, le=8)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "PriorityRuleConfiguration":
        if (
            self.moderate_schedule_lateness_min_days
            > self.moderate_schedule_lateness_max_days
        ):
            raise ValueError("moderate schedule-lateness thresholds are reversed")
        if (
            self.severe_schedule_lateness_days
            <= self.moderate_schedule_lateness_max_days
        ):
            raise ValueError("severe lateness must exceed the moderate range")
        return self


class TimingException(BaseModel):
    """One explicit product/operation timing override, if later approved."""

    exception_id: str = Field(min_length=1, max_length=100)
    operation: str | None = Field(default=None, min_length=1, max_length=256)
    lot_prefix: str | None = Field(default=None, min_length=1, max_length=40)
    days_remaining_override: int = Field(ge=0, le=365)
    provenance: ParameterProvenance

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_selector(self) -> "TimingException":
        if self.operation is None and self.lot_prefix is None:
            raise ValueError("timing exception requires an operation or lot prefix")
        return self


class ProductPlanningConfiguration(BaseModel):
    """Reviewed planning constants for one supported Flex product."""

    modality: str = Field(min_length=1, max_length=40)
    part_number: str = Field(min_length=1, max_length=40)
    flow_name: str = Field(min_length=1, max_length=256)
    route_version: int = Field(gt=0)
    expected_lot_start_quantity: int = Field(gt=0)
    uncovered_demand_start_factor: Decimal = Field(ge=Decimal("1"), le=Decimal("2"))
    operation_to_kanban: dict[str, int] = Field(min_length=1)
    kanban_days_remaining: dict[int, int]
    priority_rules: PriorityRuleConfiguration
    timing_exceptions: tuple[TimingException, ...]
    parameter_provenance: dict[str, ParameterProvenance]

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_controlled_mappings(self) -> "ProductPlanningConfiguration":
        if set(self.kanban_days_remaining) != set(range(1, 8)):
            raise ValueError("kanban_days_remaining must define Kanbans 1 through 7")
        if any(value < 0 for value in self.kanban_days_remaining.values()):
            raise ValueError("kanban days remaining must not be negative")
        if any(value not in range(1, 8) for value in self.operation_to_kanban.values()):
            raise ValueError("every operation must map to Kanban 1 through 7")
        required_provenance = {
            "expected_lot_start_quantity",
            "uncovered_demand_start_factor",
            "operation_to_kanban",
            "kanban_days_remaining",
            "priority_rules",
            "timing_exceptions",
        }
        if set(self.parameter_provenance) != required_provenance:
            raise ValueError("parameter provenance keys are incomplete or unexpected")
        exception_ids = [item.exception_id for item in self.timing_exceptions]
        if len(exception_ids) != len(set(exception_ids)):
            raise ValueError("timing exception IDs must be unique")
        return self


class PlanningConfiguration(BaseModel):
    """Versioned collection of reviewed product configurations."""

    configuration_id: str = Field(min_length=1, max_length=100)
    configuration_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    effective_date: date
    source_set: str = Field(min_length=1, max_length=256)
    status: str = Field(pattern=r"^APPROVED_MANUAL_GATE_1$")
    products: tuple[ProductPlanningConfiguration, ...] = Field(min_length=1)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_unique_products(self) -> "PlanningConfiguration":
        modalities = [product.modality for product in self.products]
        part_numbers = [product.part_number for product in self.products]
        if len(modalities) != len(set(modalities)):
            raise ValueError("product modalities must be unique")
        if len(part_numbers) != len(set(part_numbers)):
            raise ValueError("product part numbers must be unique")
        return self

    def product(self, modality: str, part_number: str) -> ProductPlanningConfiguration:
        matches = [
            product
            for product in self.products
            if product.modality == modality and product.part_number == part_number
        ]
        if len(matches) != 1:
            raise PlanningValidationError(
                f"unsupported product identity: modality={modality!r}, part_number={part_number!r}"
            )
        return matches[0]
