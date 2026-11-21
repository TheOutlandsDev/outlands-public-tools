from pathlib import Path

from raw_material_contract import load_raw_material_source_contract

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "pending-source.json"


def test_raw_material_contract_is_explicitly_fail_closed() -> None:
    contract = load_raw_material_source_contract(EXAMPLE)
    assert contract.status == "PENDING_AUTHORITATIVE_SOURCE"
    assert contract.authoritative_owner == "PENDING_SITE_DECISION"
    assert contract.authoritative_system == "PENDING_SITE_DECISION"
    assert contract.ingestion_enabled is False
    assert contract.database_writes is False
    assert "material_id" in contract.required_fields
    assert "quantity_on_hand" in contract.required_fields
