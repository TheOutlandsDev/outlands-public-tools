from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from production_planning.internal_panel_flex_contract import (
    CONTRACT_RELATIVE_PATH,
    EXPECTED_EVENT_IDENTITIES,
    EXPECTED_PRODUCTS,
    EXPECTED_STATES,
    InternalPanelFlexContractError,
    internal_panel_flex_contract_sha256,
    load_internal_panel_flex_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / CONTRACT_RELATIVE_PATH


def _payload() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _write_candidate(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_contract_accepts_only_the_five_internal_panel_flex_products() -> None:
    contract = load_internal_panel_flex_contract()

    actual = {
        product.canonical_modality: (
            product.display_modality,
            product.assembly,
            product.lot_prefix,
        )
        for product in contract.products
    }
    assert actual == EXPECTED_PRODUCTS
    assert all(product.manual_demand_required for product in contract.products)
    assert not any(product.external_os_order_expected for product in contract.products)


def test_contract_keeps_database_authority_separated_by_behavior() -> None:
    contract = load_internal_panel_flex_contract()

    assert "POSTGRESQL" in contract.authorities.manual_internal_demand
    assert "POSTGRESQL" in contract.authorities.completion_and_transfer_actions
    assert "CLICKHOUSE" in contract.authorities.wip_and_inventory_history
    assert "CLICKHOUSE" in contract.authorities.flex_to_hla_transfer_history
    assert contract.authorities.external_os_orders.startswith("EXCLUDED")


def test_contract_keeps_consumption_fail_closed() -> None:
    contract = load_internal_panel_flex_contract()

    assert contract.authorities.hla_receipt_and_consumption.endswith("FAIL_CLOSED")
    assert contract.state_model.hla_consumption_transition_executable is False
    assert contract.historical_baseline.proves_hla_consumption is False
    assert contract.controls.transfer_is_hla_consumption is False
    assert contract.controls.monthly_average_is_demand_standard is False


def test_contract_records_the_reviewed_state_and_identity_models() -> None:
    contract = load_internal_panel_flex_contract()

    assert contract.state_model.states == EXPECTED_STATES
    assert contract.state_model.completed_work_remains_in_active_priorities is False
    assert {
        identity.event_type: identity.identity_fields
        for identity in contract.event_identities
    } == EXPECTED_EVENT_IDENTITIES


def test_contract_records_the_supplied_and_ingested_baseline() -> None:
    contract = load_internal_panel_flex_contract()

    assert contract.historical_baseline.expected_records == 18
    assert contract.historical_baseline.expected_quantity == 1724
    assert contract.historical_baseline.status_scope == "CLOSED"
    assert contract.activation.historical_ingestion_authorized is True


def test_contract_authorizes_only_the_completed_development_scope() -> None:
    contract = load_internal_panel_flex_contract()

    assert contract.activation.runtime_wiring_authorized is True
    assert contract.activation.database_migration_authorized is True
    assert contract.activation.historical_ingestion_authorized is True
    assert contract.activation.user_interface_authorized is True
    assert contract.activation.production_included is False
    assert contract.production_included is False
    assert contract.controls.database_writes_permitted_by_this_contract is True
    assert contract.controls.mes_reads_permitted_by_this_contract is False
    assert contract.controls.mes_writes_permitted is False


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("production_included",), True),
        (("activation", "database_migration_authorized"), False),
        (("controls", "transfer_is_hla_consumption"), True),
        (("controls", "monthly_average_is_demand_standard"), True),
        (("historical_baseline", "proves_hla_consumption"), True),
    ),
)
def test_contract_rejects_authority_expansion(
    tmp_path: Path,
    path: tuple[str, ...],
    value: object,
) -> None:
    payload = deepcopy(_payload())
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(InternalPanelFlexContractError):
        load_internal_panel_flex_contract(_write_candidate(tmp_path, payload))


def test_contract_rejects_product_mapping_drift(tmp_path: Path) -> None:
    payload = _payload()
    payload["products"][0]["assembly"] = "9199999"

    with pytest.raises(InternalPanelFlexContractError):
        load_internal_panel_flex_contract(_write_candidate(tmp_path, payload))


def test_contract_rejects_duplicate_event_identity(tmp_path: Path) -> None:
    payload = _payload()
    payload["event_identities"].append(payload["event_identities"][0])

    with pytest.raises(InternalPanelFlexContractError):
        load_internal_panel_flex_contract(_write_candidate(tmp_path, payload))


def test_contract_checksum_is_stable_and_bounded() -> None:
    digest = internal_panel_flex_contract_sha256()

    assert len(digest) == 64
    assert digest == internal_panel_flex_contract_sha256(CONTRACT_PATH)


def test_oversized_contract_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "oversized.json"
    path.write_bytes(b"{" + b" " * (128 * 1024))

    with pytest.raises(InternalPanelFlexContractError):
        load_internal_panel_flex_contract(path)
