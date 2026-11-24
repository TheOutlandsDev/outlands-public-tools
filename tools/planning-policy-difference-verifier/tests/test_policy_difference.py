from pathlib import Path

from policy_difference import PlanningSnapshot, ReviewEvidence, read_input, verify_policy_differences


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_only_two_reviewed_factor_differences_are_permitted() -> None:
    result = verify_policy_differences(
        read_input(EXAMPLES / "before.json", PlanningSnapshot),
        read_input(EXAMPLES / "after.json", PlanningSnapshot),
        read_input(EXAMPLES / "review.json", ReviewEvidence),
    )
    differences = {
        case.case_id: (case.legacy_result, case.authoritative_result)
        for case in result.cases
        if case.classification == "REVIEWED_DIFFERENCE"
    }
    assert differences == {
        "reviewed-difference-detailed-planning": ((0, 220), (0, 200)),
        "reviewed-difference-reservation-boundary": ((2, 330), (1, 300)),
    }
