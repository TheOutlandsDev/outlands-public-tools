"""Validate a fictional production workflow contract offline."""

from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


CONTRACT_RELATIVE_PATH = Path(
    "data/internal_panel_flex/internal_panel_flex_contract_v1.json"
)
MAX_CONTRACT_BYTES = 128 * 1024

EXPECTED_PRODUCTS = {
    "DMO01": ("PDMO01", "9100001", "PDMO01"),
    "LAB01": ("PLAB01", "9100002", "PLAB01"),
    "LAB02": ("PLAB02", "9100003", "PLAB02"),
    "SIM01": ("PSIM01", "9100004", "PSIM01"),
    "SIM02": ("PSIM02", "9100005", "PSIM02"),
}

EXPECTED_STATES = (
    "IN_PRODUCTION",
    "COMPLETE_AWAITING_DESTINATION_TRANSFER",
    "TRANSFERRED_TO_DESTINATION",
    "CONSUMED_AT_DESTINATION",
)

EXPECTED_TRANSITIONS = {
    (
        "COMPLETE",
        "IN_PRODUCTION",
        "COMPLETE_AWAITING_DESTINATION_TRANSFER",
    ),
    (
        "TRANSFER_TO_DESTINATION",
        "COMPLETE_AWAITING_DESTINATION_TRANSFER",
        "TRANSFERRED_TO_DESTINATION",
    ),
    (
        "RECORD_DESTINATION_CONSUMPTION",
        "TRANSFERRED_TO_DESTINATION",
        "CONSUMED_AT_DESTINATION",
    ),
}

EXPECTED_EVENT_IDENTITIES = {
    "MANUAL_INTERNAL_DEMAND": ("demand_id", "revision"),
    "COMPLETION_ACTION": ("lot_id", "completion_revision"),
    "TRANSFER_TO_DESTINATION_EVENT": (
        "source_sha256",
        "source_row_number",
        "event_type",
    ),
    "DESTINATION_CONSUMPTION": (
        "source_sha256",
        "source_row_number",
        "event_type",
    ),
}


class InternalPanelFlexContractError(ValueError):
    """Raised when the development contract cannot be trusted."""


class ActivationBoundary(BaseModel):
    runtime_wiring_authorized: Literal[True]
    database_migration_authorized: Literal[True]
    historical_ingestion_authorized: Literal[True]
    user_interface_authorized: Literal[True]
    production_included: Literal[False]

    model_config = ConfigDict(frozen=True, extra="forbid")


class Authorities(BaseModel):
    manual_internal_demand: Literal[
        "DEVELOPMENT_POSTGRESQL_EDITABLE_TRANSACTION"
    ]
    completion_and_transfer_actions: Literal[
        "DEVELOPMENT_POSTGRESQL_CONTROLLED_STATE_TRANSITION"
    ]
    wip_and_inventory_history: Literal[
        "DEVELOPMENT_CLICKHOUSE_IMMUTABLE_SNAPSHOT"
    ]
    flex_to_hla_transfer_history: Literal[
        "DEVELOPMENT_CLICKHOUSE_APPEND_ONLY_EVENT"
    ]
    hla_receipt_and_consumption: Literal[
        "PENDING_AUTHORITATIVE_SOURCE_FAIL_CLOSED"
    ]
    external_os_orders: Literal[
        "EXCLUDED_FOR_FICTIONAL_WORKFLOW_SCOPE"
    ]

    model_config = ConfigDict(frozen=True, extra="forbid")


class InternalPanelFlexProduct(BaseModel):
    canonical_modality: str = Field(pattern=r"^(?:DMO|LAB|SIM)[0-9]{2}$")
    display_modality: str = Field(pattern=r"^P(?:DMO|LAB|SIM)[0-9]{2}$")
    assembly: str = Field(pattern=r"^[0-9]{7}$")
    lot_prefix: str = Field(pattern=r"^P(?:DMO|LAB|SIM)[0-9]{2}$")
    manual_demand_required: Literal[True]
    external_os_order_expected: Literal[False]

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class StateTransition(BaseModel):
    action: str = Field(pattern=r"^[A-Z0-9_]+$")
    from_state: str = Field(pattern=r"^[A-Z0-9_]+$")
    to_state: str = Field(pattern=r"^[A-Z0-9_]+$")

    model_config = ConfigDict(frozen=True, extra="forbid")


class StateModel(BaseModel):
    states: tuple[str, ...]
    transitions: tuple[StateTransition, ...]
    hla_consumption_transition_executable: Literal[False]
    completed_work_remains_in_active_priorities: Literal[False]

    model_config = ConfigDict(frozen=True, extra="forbid")


class EventIdentity(BaseModel):
    event_type: str = Field(pattern=r"^[A-Z0-9_]+$")
    identity_fields: tuple[str, ...]

    model_config = ConfigDict(frozen=True, extra="forbid")


class HistoricalBaseline(BaseModel):
    source_identity: Literal["DEMO-BASELINE-001"]
    declared_window_start: date
    declared_window_end: date
    first_observed_event: datetime
    last_observed_event: datetime
    expected_records: Literal[18]
    expected_quantity: Literal[1724]
    status_scope: Literal["CLOSED"]
    proves_hla_consumption: Literal[False]

    model_config = ConfigDict(frozen=True, extra="forbid")


class ContractControls(BaseModel):
    monthly_average_is_demand_standard: Literal[False]
    transfer_is_hla_consumption: Literal[False]
    source_values_may_be_silently_renamed: Literal[False]
    duplicate_event_behavior: Literal["FAIL_CLOSED"]
    unknown_product_behavior: Literal["FAIL_CLOSED"]
    database_writes_permitted_by_this_contract: Literal[True]
    mes_reads_permitted_by_this_contract: Literal[False]
    mes_writes_permitted: Literal[False]

    model_config = ConfigDict(frozen=True, extra="forbid")


class InternalPanelFlexContract(BaseModel):
    contract_id: Literal["demo-production-workflow-v1"]
    contract_version: Literal["0.2.0"]
    status: Literal["DEVELOPMENT_ACTIVATED"]
    environment: Literal["development-only"]
    prepared_on: date
    technical_owner: str = Field(min_length=1, max_length=160)
    production_included: Literal[False]
    activation: ActivationBoundary
    authorities: Authorities
    products: tuple[InternalPanelFlexProduct, ...]
    state_model: StateModel
    event_identities: tuple[EventIdentity, ...]
    historical_baseline: HistoricalBaseline
    controls: ContractControls

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_semantic_contract(self):
        products = {
            product.canonical_modality: (
                product.display_modality,
                product.assembly,
                product.lot_prefix,
            )
            for product in self.products
        }
        if len(products) != len(self.products):
            raise ValueError("Every fictional production workflow modality must be unique.")
        if products != EXPECTED_PRODUCTS:
            raise ValueError("The five-product fictional production workflow scope drifted.")

        for label, values in (
            ("display modality", [item.display_modality for item in self.products]),
            ("assembly", [item.assembly for item in self.products]),
            ("lot prefix", [item.lot_prefix for item in self.products]),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"Every {label} must be unique.")

        if self.state_model.states != EXPECTED_STATES:
            raise ValueError("The fictional production workflow state order drifted.")
        transitions = {
            (item.action, item.from_state, item.to_state)
            for item in self.state_model.transitions
        }
        if len(transitions) != len(self.state_model.transitions):
            raise ValueError("Every state transition must be unique.")
        if transitions != EXPECTED_TRANSITIONS:
            raise ValueError("The fictional production workflow transition set drifted.")

        event_identities = {
            item.event_type: item.identity_fields for item in self.event_identities
        }
        if len(event_identities) != len(self.event_identities):
            raise ValueError("Every event identity type must be unique.")
        if event_identities != EXPECTED_EVENT_IDENTITIES:
            raise ValueError("The fictional production workflow event identities drifted.")

        baseline = self.historical_baseline
        if baseline.declared_window_start > baseline.declared_window_end:
            raise ValueError("The declared baseline window is reversed.")
        if baseline.first_observed_event > baseline.last_observed_event:
            raise ValueError("The observed baseline window is reversed.")
        return self


def find_project_root() -> Path:
    """Locate the project root without assuming one deployment layout."""

    for parent in Path(__file__).resolve().parents:
        if (parent / "data" / "internal_panel_flex").is_dir():
            return parent
    raise InternalPanelFlexContractError("The project root is unavailable.")


def load_internal_panel_flex_contract(
    path: Path | None = None,
) -> InternalPanelFlexContract:
    """Load the candidate without enabling migrations, writes, or runtime use."""

    contract_path = path or (find_project_root() / CONTRACT_RELATIVE_PATH)
    try:
        size = contract_path.stat().st_size
        if size <= 0 or size > MAX_CONTRACT_BYTES:
            raise InternalPanelFlexContractError(
                "The fictional production workflow contract size is invalid."
            )
        payload = json.loads(contract_path.read_text(encoding="utf-8"))
        return InternalPanelFlexContract.model_validate(payload)
    except InternalPanelFlexContractError:
        raise
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise InternalPanelFlexContractError(
            "The fictional production workflow contract failed validation."
        ) from exc


def internal_panel_flex_contract_sha256(path: Path | None = None) -> str:
    """Return the checksum of the validated contract source."""

    contract_path = path or (find_project_root() / CONTRACT_RELATIVE_PATH)
    load_internal_panel_flex_contract(contract_path)
    return sha256(contract_path.read_bytes()).hexdigest()
