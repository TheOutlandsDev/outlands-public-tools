from copy import deepcopy
from datetime import date
import json
from pathlib import Path

from planning_overlay import load_authoritative_flex_policy, project_detailed_planning_configuration
from reference_planner import FlexOrder, FlexWipLot, build_flex_plan, comparison_result, load_planning_configuration


ROOT = Path(__file__).resolve().parents[1] / "examples"


def test_detailed_planning_projection_preserves_all_non_factor_results() -> None:
    policy = load_authoritative_flex_policy(ROOT / "candidate-policy.json")
    legacy = load_planning_configuration(
        ROOT / "data" / "flex_planning" / "configuration_v1.json"
    )
    projected = project_detailed_planning_configuration(policy, project_root=ROOT)
    assert all(
        "example-review-1 factor 1.00" in str(
            item.parameter_provenance["uncovered_demand_start_factor"].source
        )
        for item in projected.products
    )
    fixture_path = ROOT / "orders-and-wip.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    orders = [
        FlexOrder(
            **item,
            modality=fixture["modality"],
            part_number=fixture["part_number"],
        )
        for item in fixture["orders"]
    ]
    wip = [
        FlexWipLot(
            **item,
            modality=fixture["modality"],
            part_number=fixture["part_number"],
            quantity_basis="available_after_legacy_import_normalization",
        )
        for item in fixture["wip"]
    ]
    arguments = {
        "planning_date": date.fromisoformat(fixture["planning_date"]),
        "modality": fixture["modality"],
        "part_number": fixture["part_number"],
        "orders": orders,
        "wip": wip,
    }
    legacy_result = comparison_result(
        build_flex_plan(configuration=legacy, **arguments)
    )
    authoritative_result = comparison_result(
        build_flex_plan(configuration=projected, **arguments)
    )

    assert legacy_result["recommended_start_by_order"] == [0, 220]
    assert authoritative_result["recommended_start_by_order"] == [0, 200]
    legacy_without_factor = deepcopy(legacy_result)
    authoritative_without_factor = deepcopy(authoritative_result)
    legacy_without_factor.pop("recommended_start_by_order")
    authoritative_without_factor.pop("recommended_start_by_order")
    assert authoritative_without_factor == legacy_without_factor
