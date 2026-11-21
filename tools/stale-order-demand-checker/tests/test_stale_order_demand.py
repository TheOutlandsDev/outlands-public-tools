from stale_order_demand import (
    stale_open_order_ids,
)


def test_completed_historical_orders_are_not_stale_live_demand() -> None:
    states = {
        "active": {"cancelled": False, "remaining_quantity": 25},
        "completed-history": {"cancelled": False, "remaining_quantity": 0},
        "cancelled-history": {"cancelled": True, "remaining_quantity": 40},
        "stale-open": {"cancelled": False, "remaining_quantity": 10},
    }

    assert stale_open_order_ids(states, {"active"}) == ["stale-open"]
