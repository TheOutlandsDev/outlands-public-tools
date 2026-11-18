from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from production_planning.what_is_needed import (
    DueProductInput,
    ShipmentNeedInput,
    WhatIsNeededValidationError,
    determine_parts_to_ship,
    evaluate_comparison_case,
    load_part_modality_configuration,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "flex_planning"
CASE_PATH = (
    DATA_ROOT
    / "comparison_cases"
    / "demo_shipment_needs.json"
)
MAPPING_PATH = DATA_ROOT / "demo_part_modality.json"


def _inputs():
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    shipments = tuple(
        ShipmentNeedInput.model_validate(item)
        for item in case["input_contract"]["shipment_records"]
    )
    due_products = tuple(
        DueProductInput.model_validate(item)
        for item in case["input_contract"]["due_products"]
    )
    return shipments, due_products, load_part_modality_configuration(MAPPING_PATH)


def test_fixed_case_matches_every_approved_expected_field() -> None:
    evaluated = evaluate_comparison_case(
        case_path=CASE_PATH,
        mapping_path=MAPPING_PATH,
    )

    assert evaluated.status == "APPROVED_DEVELOPMENT_REFERENCE"
    assert evaluated.review_status == "APPROVED_BY_OWNER"
    assert evaluated.matlab_execution_status == "NOT_RUN"
    assert [item.source_id for item in evaluated.result.parts_to_ship] == [
        "DEMO-SHIP-001",
        "DEMO-SHIP-002",
    ]
    assert evaluated.result.active_cutoff_date == date(2000, 8, 17)
    assert evaluated.result.active_products == ("7000011-DEMO",)
    assert evaluated.result.retained_demand_quantity == 325
    assert evaluated.result.excluded_shipped_count == 1
    assert evaluated.result.excluded_docked_count == 1


def test_pure_function_does_not_mutate_inputs() -> None:
    shipments, due_products, mapping = _inputs()
    before = deepcopy(
        {
            "shipments": [item.model_dump() for item in shipments],
            "due_products": [item.model_dump() for item in due_products],
            "mapping": mapping.model_dump(),
        }
    )

    determine_parts_to_ship(
        shipment_records=shipments,
        due_products=due_products,
        mapping=mapping,
    )

    assert [item.model_dump() for item in shipments] == before["shipments"]
    assert [item.model_dump() for item in due_products] == before["due_products"]
    assert mapping.model_dump() == before["mapping"]


def test_empty_and_nonpositive_inputs_return_a_bounded_empty_result() -> None:
    _, _, mapping = _inputs()
    zero = ShipmentNeedInput(
        source_id="ZERO",
        date_to_ship=date(2000, 8, 17),
        quantity_due=0,
        part_number="7000011-DEMO",
    )

    result = determine_parts_to_ship(
        shipment_records=(zero,),
        due_products=(),
        mapping=mapping,
    )

    assert result.parts_to_ship == ()
    assert result.active_products == ()
    assert result.active_cutoff_date is None
    assert result.excluded_nonpositive_count == 1


def test_equal_dates_use_source_id_as_stable_tie_breaker() -> None:
    _, _, mapping = _inputs()
    records = tuple(
        ShipmentNeedInput(
            source_id=source_id,
            date_to_ship=date(2000, 8, 17),
            quantity_due=10,
            part_number="7000011-DEMO",
        )
        for source_id in ("B", "A")
    )

    result = determine_parts_to_ship(
        shipment_records=records,
        due_products=(),
        mapping=mapping,
    )

    assert [item.source_id for item in result.parts_to_ship] == ["A", "B"]


def test_numeric_excel_part_number_is_normalized_before_mapping() -> None:
    _, _, mapping = _inputs()
    record = ShipmentNeedInput.model_validate(
        {
            "source_id": "NUMERIC-PART",
            "date_to_ship": "2000-08-17",
            "quantity_due": 12,
            "part_number": 8400021,
        }
    )

    result = determine_parts_to_ship(
        shipment_records=(record,),
        due_products=(),
        mapping=mapping,
    )

    assert result.parts_to_ship[0].part_number == "8400021"
    assert result.parts_to_ship[0].modality == "DEMO-B"


def test_active_cutoff_is_inclusive_and_products_are_unique_sorted() -> None:
    _, _, mapping = _inputs()
    shipment = ShipmentNeedInput(
        source_id="OPEN",
        date_to_ship=date(2000, 8, 17),
        quantity_due=10,
        part_number="7000011-DEMO",
    )
    due_products = (
        DueProductInput(source_id="BEFORE", due_date=date(2000, 8, 16), part_number="8400021"),
        DueProductInput(source_id="AT", due_date=date(2000, 8, 17), part_number="7000011-DEMO"),
        DueProductInput(source_id="AFTER", due_date=date(2000, 8, 18), part_number="8400021"),
        DueProductInput(source_id="DUP", due_date=date(2000, 8, 19), part_number="7000011-DEMO"),
    )

    result = determine_parts_to_ship(
        shipment_records=(shipment,),
        due_products=due_products,
        mapping=mapping,
    )

    assert result.active_products == ("7000011-DEMO", "8400021")


def test_any_present_ship_quantity_excludes_the_entire_row_for_v5p3_parity() -> None:
    _, _, mapping = _inputs()
    partial = ShipmentNeedInput(
        source_id="PARTIAL",
        date_to_ship=date(2000, 8, 17),
        quantity_due=300,
        ship_quantity=1,
        part_number="7000011-DEMO",
    )

    result = determine_parts_to_ship(
        shipment_records=(partial,),
        due_products=(),
        mapping=mapping,
    )

    assert result.open_need_count == 0
    assert result.excluded_shipped_count == 1


def test_unknown_retained_part_fails_closed() -> None:
    _, _, mapping = _inputs()
    unknown = ShipmentNeedInput(
        source_id="UNKNOWN",
        date_to_ship=date(2000, 8, 17),
        quantity_due=10,
        part_number="NOT-CONFIGURED",
    )

    with pytest.raises(WhatIsNeededValidationError, match="unsupported retained part"):
        determine_parts_to_ship(
            shipment_records=(unknown,),
            due_products=(),
            mapping=mapping,
        )


@pytest.mark.parametrize("collection", ["shipments", "due_products"])
def test_duplicate_source_identity_fails_closed(collection: str) -> None:
    shipments, due_products, mapping = _inputs()
    if collection == "shipments":
        shipments = (shipments[0], shipments[0])
        message = "duplicate shipment source ID"
    else:
        due_products = (due_products[0], due_products[0])
        message = "duplicate due/product source ID"

    with pytest.raises(WhatIsNeededValidationError, match=message):
        determine_parts_to_ship(
            shipment_records=shipments,
            due_products=due_products,
            mapping=mapping,
        )


def test_nonwhole_quantity_and_part_number_fail_schema_validation() -> None:
    with pytest.raises(ValidationError):
        ShipmentNeedInput.model_validate(
            {
                "source_id": "BAD-QTY",
                "date_to_ship": "2000-08-17",
                "quantity_due": 1.5,
                "part_number": "7000011-DEMO",
            }
        )
    with pytest.raises(ValidationError):
        ShipmentNeedInput.model_validate(
            {
                "source_id": "BAD-PART",
                "date_to_ship": "2000-08-17",
                "quantity_due": 1,
                "part_number": 8400021.5,
            }
        )


def test_changed_expected_result_fails_closed(tmp_path: Path) -> None:
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    case["expected"]["retained_demand_quantity"] = 999
    candidate = tmp_path / "changed-case.json"
    candidate.write_text(json.dumps(case), encoding="utf-8")

    with pytest.raises(
        WhatIsNeededValidationError,
        match="expected result does not match",
    ):
        evaluate_comparison_case(case_path=candidate, mapping_path=MAPPING_PATH)
