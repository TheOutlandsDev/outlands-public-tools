from datetime import date
import json
from pathlib import Path

import pytest

from allocation_engine import comparison_result
from planning_fixture_replay import FlexFixtureLoadError, validate_fixture


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
FIXTURE = EXAMPLES / "fictional-fixture.json"
CONFIGURATION = EXAMPLES / "fictional-configuration.json"


def test_approved_frozen_case_matches_manual_gate_1_result() -> None:
    fixture, plan = validate_fixture(FIXTURE, CONFIGURATION)

    assert plan.planning_date == date(2030, 1, 10)
    assert plan.modality == "DEMO-A"
    assert plan.part_number == "DEMO-PART-1"
    assert plan.flow_name == "Fictional Assembly Route"
    assert plan.route_version == 6
    assert plan.expected_lot_start_quantity == 120
    assert plan.configuration_version == "1.0.0"
    assert plan.configuration_effective_date == date(2030, 1, 10)
    assert [order.covered_quantity for order in plan.orders] == fixture["expected"]["covered_by_order"]
    assert [order.uncovered_quantity for order in plan.orders] == fixture["expected"]["uncovered_by_order"]
    assert [order.recommended_start_quantity for order in plan.orders] == fixture["expected"]["recommended_start_by_order"]
    assert [allocation.lot_id for allocation in plan.orders[0].allocations] == [
        "DEMO-K6-A", "DEMO-K4-A", "DEMO-K2-A",
    ]
    assert [allocation.lot_id for allocation in plan.orders[1].allocations] == ["DEMO-K2-B"]
    assert plan.conservation.model_dump() == {
        key: fixture["expected"][key]
        for key in ("demand_input", "covered", "uncovered", "wip_input", "wip_allocated", "wip_remaining")
    }
    assert comparison_result(plan) == fixture["expected"]


def test_fixture_expected_result_is_validated_before_accepting_a_report(tmp_path: Path) -> None:
    fixture = json.loads(FIXTURE.read_bytes())
    fixture["expected"]["recommended_start_by_order"][1] += 1
    altered = tmp_path / "fixture.json"
    altered.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(FlexFixtureLoadError, match="does not match"):
        validate_fixture(altered, CONFIGURATION)
