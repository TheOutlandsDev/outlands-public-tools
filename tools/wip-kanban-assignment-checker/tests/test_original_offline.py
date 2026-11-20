"""Six original direct-assignment tests adapted to fictional inputs."""

from copy import deepcopy
from pathlib import Path

import pytest

from kanban_assignment import (
    KanbanAssignmentError,
    PreparedWIPRecord,
    assign_wip_to_kanbans,
    load_assignment_configuration,
    preflight_wip_assignment,
)


ASSIGNMENT_CONFIG = Path(__file__).resolve().parents[1] / "examples" / "routing.json"


def _prepared(**overrides) -> PreparedWIPRecord:
    values = {
        "source_row": 5,
        "product": "DEMO-01",
        "lot_id": "PF0001TEST",
        "current_step": "STATION-1-01",
        "quantity_in_process_raw": 100,
        "normalization_applied": True,
        "yield_loss_quantity": 20,
        "quantity_in_process": 80,
        "parts_completed": 10,
    }
    values.update(overrides)
    return PreparedWIPRecord.model_validate(values)


def test_fictional_product_alternate_rule_routes_to_k5() -> None:
    record = _prepared(
        source_row=179,
        product="DEMO-02",
        lot_id="PF0002DEMO",
        current_step="ALT-A",
    )

    result = assign_wip_to_kanbans(
        (record,), load_assignment_configuration(ASSIGNMENT_CONFIG)
    )

    assert result.records[0].kanban == 5
    assert result.records[0].assignment_rule == "ALTERNATE_PRODUCT"


def test_validation_alias_is_retained_and_canonicalized() -> None:
    record = _prepared(
        product="DEMO-03-ALIAS",
        lot_id="PF0003DEMO",
        current_step="STATION-1-01",
    )

    result = assign_wip_to_kanbans(
        (record,), load_assignment_configuration(ASSIGNMENT_CONFIG)
    )

    assert result.records[0].source_product == "DEMO-03-ALIAS"
    assert result.records[0].canonical_product == "DEMO-03"


def test_source_specific_alternate_rule_wins_over_canonical_base_rule() -> None:
    record = _prepared(
        product="DEMO-04-ALIAS",
        lot_id="PF0004DEMO",
        current_step="ALT-B",
    )

    result = assign_wip_to_kanbans(
        (record,), load_assignment_configuration(ASSIGNMENT_CONFIG)
    )

    assert result.records[0].canonical_product == "DEMO-04"
    assert result.records[0].kanban == 5


def test_every_direct_operation_maps_to_its_declared_kanban() -> None:
    configuration = load_assignment_configuration(ASSIGNMENT_CONFIG)
    records = []
    expected = {}
    source_row = 100
    for kanban, operations in configuration.direct_kanbans.items():
        for operation in operations:
            source_row += 1
            lot = f"PF0001{source_row:04d}"
            records.append(
                _prepared(
                    source_row=source_row,
                    lot_id=lot,
                    current_step=operation,
                )
            )
            expected[lot] = kanban

    result = assign_wip_to_kanbans(tuple(records), configuration)

    assert len(result.records) == 66
    assert {row.lot_id: row.kanban for row in result.records} == expected


@pytest.mark.parametrize(
    ("record", "code"),
    [
        (_prepared(lot_id="PZZZZZDEMO"), "UNKNOWN_LOT_PREFIX"),
        (_prepared(current_step="NOT_A_REVIEWED_STEP"), "UNMAPPED_OPERATION"),
        (
            _prepared(
                product="DEMO-05",
                lot_id="PF0005DEMO",
                current_step="ALT-A",
            ),
            "UNRESOLVED_ALTERNATE_PRODUCT",
        ),
        (
            _prepared(
                product="DEMO-06",
                lot_id="PF0007DEMO",
                current_step="STATION-2-01",
            ),
            "PREFIX_PRODUCT_MISMATCH",
        ),
    ],
)
def test_unknown_or_unapproved_rules_fail_closed(
    record: PreparedWIPRecord, code: str
) -> None:
    preflight = preflight_wip_assignment(
        (record,), load_assignment_configuration(ASSIGNMENT_CONFIG)
    )

    assert preflight.status == "FAIL"
    assert any(issue.code == code for issue in preflight.issues)
    with pytest.raises(KanbanAssignmentError):
        assign_wip_to_kanbans(
            (record,), load_assignment_configuration(ASSIGNMENT_CONFIG)
        )


def test_assignment_is_immutable_and_yield_is_explicit() -> None:
    record = _prepared()
    before = deepcopy(record.model_dump())

    result = assign_wip_to_kanbans(
        (record,), load_assignment_configuration(ASSIGNMENT_CONFIG)
    )

    assert record.model_dump() == before
    assert result.records[0].total_parts == 90
    assert str(result.records[0].yield_percent) == "25.000000"
