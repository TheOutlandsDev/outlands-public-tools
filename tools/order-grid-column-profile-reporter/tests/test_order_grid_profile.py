import json

import pytest

from order_grid_profile import main


def test_os_workspace_page_and_api_share_the_validated_active_revision(capsys) -> None:
    assert main([]) == 0
    result = capsys.readouterr()
    assert not result.err
    payload = json.loads(result.out)

    assert payload["selected_view"] == "all"
    assert len(payload["visible_columns"]) == 34
    assert {
        column["key"]
        for column in payload["visible_columns"]
        if column["group"] == "handoff"
    } == {
        "flex_handoff_state",
        "flex_ready_quantity",
        "production_remaining_quantity",
        "flex_ready_lot_ids",
        "flex_ready_at",
        "flex_ready_by",
        "logistics_mes_status",
    }
    assert {column["source_column"] for column in payload["visible_columns"] if column["source_column"] and len(column["source_column"]) == 1} == set("BCDEFGHIJKLMNOPQRSTUVWXY")
    assert any(column["label"] == "Planned lead-time date" for column in payload["visible_columns"])


def test_os_workspace_column_views_are_backend_governed(capsys) -> None:
    assert main(["--view", "notes"]) == 0
    result = capsys.readouterr()
    assert not result.err
    payload = json.loads(result.out)

    assert payload["selected_view"] == "notes"
    assert [column["key"] for column in payload["visible_columns"]] == [
        "status", "source_sheet", "part_number", "customer_notes", "planning_notes",
        "lead_time_calculation", "admin_1_open", "admin_2_used", "admin_3_used",
    ]
    with pytest.raises(SystemExit) as error:
        main(["--view", "unsupported"])
    assert error.value.code == 2
    result = capsys.readouterr()
    assert not result.out and "invalid choice" in result.err
