from pathlib import Path

import pytest

from planning_demand_scope import (
    AuthoritativeConsumerError,
    SavedSnapshot,
    build_authoritative_consumer_snapshot,
)


def fictional_snapshot():
    example = Path(__file__).resolve().parents[1] / "examples" / "fictional-snapshot.json"
    return SavedSnapshot.model_validate_json(example.read_bytes())


def load_authoritative_flex_policy_runtime(mode):
    runtime = fictional_snapshot().runtime
    if mode == "authoritative_gate_a":
        return runtime
    return runtime.model_copy(update={
        "status": runtime.status.model_copy(update={"active": False, "mode": mode}),
    })


class ConsumerRepository:
    def __init__(self, *, complete: bool = True) -> None:
        snapshot = fictional_snapshot()
        self.orders = snapshot.orders
        self.queue = snapshot.queue if complete else snapshot.queue[:-1]

    def list_active_orders(self, *, limit: int = 1000):
        assert limit == 1000
        return self.orders

    def list_automatic_lot_start_queue(self, *, limit: int = 20):
        assert limit == 20
        return self.queue


def test_authoritative_consumer_uses_one_current_policy_scope() -> None:
    runtime = load_authoritative_flex_policy_runtime("authoritative_gate_a")
    snapshot = build_authoritative_consumer_snapshot(runtime, ConsumerRepository())

    assert snapshot.authority == "AUTHORITATIVE_GATE_A_ACTIVE"
    assert snapshot.recommendation_factor == "1.00"
    assert snapshot.configured_modalities == 12
    assert snapshot.all_open_order_lines == 4
    assert snapshot.all_open_order_demand == 250
    assert snapshot.configured_open_demand == 100
    assert snapshot.outside_authoritative_configuration_demand == 150
    assert snapshot.covered_by_wip == 100
    assert snapshot.uncovered_after_wip == 0
    assert snapshot.starts_required == 0
    assert snapshot.database_writes is False
    assert snapshot.comparison_only_data_included is False


def test_authoritative_consumer_fails_closed_on_incomplete_queue() -> None:
    runtime = load_authoritative_flex_policy_runtime("authoritative_gate_a")
    with pytest.raises(AuthoritativeConsumerError, match="every configured modality"):
        build_authoritative_consumer_snapshot(
            runtime, ConsumerRepository(complete=False)
        )


def test_authoritative_consumer_rejects_legacy_rollback_mode() -> None:
    runtime = load_authoritative_flex_policy_runtime("legacy")
    with pytest.raises(AuthoritativeConsumerError, match="not active"):
        build_authoritative_consumer_snapshot(runtime, ConsumerRepository())
