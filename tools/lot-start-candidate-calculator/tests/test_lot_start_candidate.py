from pathlib import Path

import pytest

from lot_start_candidate import LotStartPolicyError, load_lot_start_policy, recommend_lot_start

def test_product_specific_factor_is_separate_from_lot_capacity():
    policy = load_lot_start_policy(Path(__file__).with_name("fictional-comparison-policy.json"))
    recommendation = recommend_lot_start(
        modality="GROUP01",
        uncovered_demand=100,
        observed_lot_ids=["DEMO-01-AAAA"],
        policy=policy,
    )

    assert recommendation.start_factor == "1.10"
    assert recommendation.lot_prefix == "DEMO-01-"
    assert recommendation.allowance_demand == 110
    assert recommendation.lot_size == 300
    assert recommendation.recommended_lot_count == 1
    assert recommendation.planned_capacity_circuits == 300
    assert recommendation.proposed_lot_ids == ("DEMO-01-AAAB",)
    assert recommendation.authority == "DEVELOPMENT_CANDIDATE_NOT_RESERVED"


def test_unknown_sizes_and_absent_identity_history_fail_closed():
    policy = load_lot_start_policy(Path(__file__).with_name("fictional-comparison-policy.json"))
    with pytest.raises(LotStartPolicyError, match="Lot size pending"):
        recommend_lot_start(
            modality="HOLD01",
            uncovered_demand=100,
            observed_lot_ids=["DEMO-HOLD-AAAA"],
            policy=policy,
        )
    with pytest.raises(LotStartPolicyError, match="No standard historical"):
        recommend_lot_start(
            modality="GROUP04",
            uncovered_demand=100,
            observed_lot_ids=[],
            policy=policy,
        )
