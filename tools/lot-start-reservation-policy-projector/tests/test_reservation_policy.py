import json
from pathlib import Path

from reference_lot_calculator import recommend_lot_start
from reservation_policy import PolicyProjectionInput, project_lot_start_policy


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_reservation_projection_makes_legacy_factor_comparison_only() -> None:
    policy = PolicyProjectionInput.model_validate_json((EXAMPLES / "candidate-policy.json").read_bytes())
    projected = project_lot_start_policy(policy)
    legacy = json.loads((EXAMPLES / "legacy-comparison.json").read_bytes())
    observed = ["DEMO-01-AAAA"]

    authoritative = recommend_lot_start(
        modality="GROUP01",
        uncovered_demand=300,
        observed_lot_ids=observed,
        policy=projected,
    )
    comparison_only = recommend_lot_start(
        modality="GROUP01",
        uncovered_demand=300,
        observed_lot_ids=observed,
        policy=legacy,
    )

    assert len(projected["configured_products"]) == 12
    assert authoritative.start_factor == "1.00"
    assert authoritative.allowance_demand == 300
    assert authoritative.recommended_lot_count == 1
    assert comparison_only.start_factor == "1.10"
    assert comparison_only.allowance_demand == 330
    assert comparison_only.recommended_lot_count == 2
