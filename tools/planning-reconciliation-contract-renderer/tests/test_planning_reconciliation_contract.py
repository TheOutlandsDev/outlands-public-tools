from pathlib import Path

from planning_reconciliation_contract import SAFE_STATUS, SavedMetrics, load_contract, render_contract_text


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_logic_contract_is_complete_safe_and_plain_text() -> None:
    contract = load_contract(EXAMPLES / "fictional-contract.json")
    metrics = SavedMetrics.model_validate_json((EXAMPLES / "fictional-metrics.json").read_bytes())
    rendered = render_contract_text(contract, metrics)

    assert contract.contract_version == "1.7.0"
    assert contract.effective_date == "2030-01-10"
    assert contract.change_history[-1].version == contract.contract_version
    assert contract.change_history[-1].date == contract.effective_date
    assert contract.status == SAFE_STATUS
    assert contract.database_writes is False
    assert contract.reconciliation_active is False
    assert len(contract.authority_matrix) == 5
    assert len(contract.data_freshness_matrix) == 5
    assert len(contract.metric_authority_matrix) == 7
    assert "DATA FRESHNESS POLICY" in rendered
    assert "Accepted WIP snapshot [accepted-wip] \u2014 ACCEPTED_SNAPSHOT" in rendered
    assert "Reviewers receive a freshness notice" in rendered
    assert "Effective WIP = Current observed live WIP" in rendered
    assert "METRIC AUTHORITY MATRIX" in rendered
    assert "Completed-state WIP" in rendered
    assert "Voided order row -> zero demand" in rendered
    assert "Eligible allocation = active order revision with voided rows excluded" in rendered
    assert "Frozen sample allocation remains a comparison reference" in rendered
    assert "A void carries into a replacement order revision only when" in rendered
    assert "quantity, and required date all match exactly" in rendered
    assert "Role-owned review queues are isolated projections" in rendered
    assert "BLOCKED_MISMATCH" in rendered
    assert "Observed assembly lots: 1" in rendered
    assert "Reconciliation active: false" in rendered
