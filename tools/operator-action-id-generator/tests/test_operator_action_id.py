from pathlib import Path

from operator_action_id import action_report, read_actions


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "actions.json"


def test_operator_action_ids_are_stable_across_filters() -> None:
    actions = read_actions(EXAMPLE)
    complete = action_report(actions)
    filtered = action_report(actions, product="DEMO-PART-A")

    complete_ids = {
        (row["part_number"], row["order_id"], row["lot_id"]): row["action_id"]
        for row in complete["actions"]
    }
    assert filtered["actions"]
    assert all(
        complete_ids[(row["part_number"], row["order_id"], row["lot_id"])]
        == row["action_id"]
        for row in filtered["actions"]
    )
