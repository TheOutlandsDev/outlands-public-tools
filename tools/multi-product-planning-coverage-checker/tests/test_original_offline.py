"""Original coverage assertions with fictional input and golden results."""

from pathlib import Path

from multi_product_preflight import SavedCoverageInput


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "coverage.json"


def _saved():
    return SavedCoverageInput.model_validate_json(EXAMPLE.read_bytes())


def _result():
    return _saved().evaluate()


def test_fictional_multi_product_preflight_fails_closed_without_partial_plans() -> None:
    result = _result()

    assert result.status == "FAIL"
    assert result.plans_generated == 0
    assert result.open_order_count == 7
    assert result.open_order_quantity == 127
    assert result.open_order_part_numbers == (
        "DEMO-01",
        "DEMO-02",
        "DEMO-03",
        "DEMO-04",
        "DEMO-05",
        "DEMO-06",
    )
    assert result.unsupported_open_order_part_numbers == ()
    assert result.missing_planning_part_numbers == (
        "DEMO-05",
        "DEMO-06",
    )
    assert result.wip_input_count == 2
    assert result.wip_assignable_count == 1
    assert result.wip_rejected_count == 1
    assert any(issue.code == "PREFIX_PRODUCT_MISMATCH" for issue in result.issues)
    assert set(result.planning_configured_part_numbers) == {
        "DEMO-01",
        "DEMO-02",
        "DEMO-03",
        "DEMO-04",
    }
    assert result.missing_planning_part_numbers


def test_fictional_multi_product_preflight_is_deterministic_and_auditable() -> None:
    first = _result()
    second = _result()

    assert first == second
    assert first.result_sha256 == (
        "5c70852fa674282392f49e6588d60605ff5ec88e47d7171494bbeddeaee4b8f7"
    )
    assert first.result_sha256 == second.result_sha256
    assert first.open_order_count > 0
    assert first.open_order_quantity > 0
    assert tuple(sorted(first.open_order_part_numbers)) == first.open_order_part_numbers
    assert tuple(sorted(first.issues, key=lambda item: (item.code, item.subject, item.detail))) == first.issues


def test_every_missing_planning_part_is_still_mapped() -> None:
    result = _result()

    assert set(result.missing_planning_part_numbers) <= set(
        result.mapped_open_order_part_numbers
    )
    assert not (
        set(result.missing_planning_part_numbers)
        & set(result.unsupported_open_order_part_numbers)
    )


def test_reviewed_route_quantity_timing_and_operation_mapping() -> None:
    configuration = _saved().planning_configuration
    product = configuration.product(modality="DEMO-FAMILY-04", part_number="DEMO-04")

    assert product.flow_name == "Fictional assembly route"
    assert product.route_version == 2
    assert product.expected_lot_start_quantity == 120
    assert str(product.uncovered_demand_start_factor) == "1.25"
    assert product.operation_to_kanban["STATION-5-01"] == 5
    assert product.operation_to_kanban["STATION-6-01"] == 6
    assert product.kanban_days_remaining[5] == 3


def test_products_remain_fail_closed_until_quantities_are_reviewed() -> None:
    result = _result()

    assert result.missing_planning_part_numbers == ("DEMO-05", "DEMO-06")
    assert result.status == "FAIL"
    assert result.plans_generated == 0
