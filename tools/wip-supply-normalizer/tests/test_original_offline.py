"""Original WIP normalization assertions exercised with fictional records."""

from copy import deepcopy

import pytest

from wip_supply import (
    FPCWIPRecord,
    WIPNormalizationConfiguration,
    WIPPreparationError,
    prepare_wip_supply,
)


def _configuration() -> WIPNormalizationConfiguration:
    return WIPNormalizationConfiguration.model_validate(
        {
            "early_stage_steps": ["Fictional_Cut"],
            "early_stage_loss_rate": "0.25",
        }
    )


def _record(**overrides) -> FPCWIPRecord:
    values = {
        "source_row": 5,
        "material_name": "Fictional-Lot-01",
        "step_name": "Fictional_Cut",
        "product_name": "Fictional-Part-01",
        "wip_quantity": 13,
        "packaging_quantity": 2,
        "qa_far_quantity": 3,
        "pack_and_ship_quantity": 4,
    }
    values.update(overrides)
    return FPCWIPRecord.model_validate(values)


def test_legacy_normalization_and_completed_material_are_explicit() -> None:
    configuration = _configuration()
    result = prepare_wip_supply((_record(),), configuration)
    row = result.records[0]

    assert row.quantity_in_process_raw == 13
    assert row.yield_loss_quantity == 3
    assert row.quantity_in_process == 10
    assert row.parts_completed == 9
    assert row.normalization_applied is True


def test_unlisted_step_preserves_raw_quantity() -> None:
    configuration = _configuration()
    result = prepare_wip_supply(
        (_record(step_name="Fictional_Inspection"),), configuration
    )

    assert result.records[0].quantity_in_process == 13
    assert result.records[0].yield_loss_quantity == 0
    assert result.records[0].normalization_applied is False


def test_blank_quantities_become_zero_without_mutating_input() -> None:
    configuration = _configuration()
    record = _record(
        wip_quantity=None,
        packaging_quantity=None,
        qa_far_quantity=None,
        pack_and_ship_quantity=None,
    )
    before = deepcopy(record.model_dump())

    result = prepare_wip_supply((record,), configuration)

    assert result.records[0].quantity_in_process == 0
    assert result.records[0].parts_completed == 0
    assert record.model_dump() == before


def test_duplicate_lot_identity_fails_closed() -> None:
    configuration = _configuration()
    records = (_record(source_row=5), _record(source_row=6))

    with pytest.raises(WIPPreparationError, match="duplicate WIP lot identity"):
        prepare_wip_supply(records, configuration)
