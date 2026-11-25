from pathlib import Path

from fulfillment_wip_eligibility import AssignmentReport, OverrideConfiguration, project_eligibility, read_model

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_verification_supply_is_excluded_from_standard_production_allocation():
    assignment = read_model(EXAMPLES / "assigned-wip.json", AssignmentReport, "assignment report")
    overrides = read_model(EXAMPLES / "overrides.json", OverrideConfiguration, "override configuration")
    result = project_eligibility(assignment, overrides)

    assert result["verification_supply"]
    assert all(row["policy"] == "Excluded from standard production allocation"
               for row in result["verification_supply"])
