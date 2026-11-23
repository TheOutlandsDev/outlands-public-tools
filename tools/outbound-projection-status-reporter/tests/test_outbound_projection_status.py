import json
from pathlib import Path

from outbound_projection_status import next_status


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def example(name):
    return json.loads((EXAMPLES / name).read_bytes())


def test_worker_cycle_publishes_bounded_non_sensitive_health() -> None:
    outcome = example("accepted-outcome.json")
    outcome.update(password="fictional", username="fictional", carrier="fictional",
                   tracking_number="fictional", transaction_comment="fictional")
    payload = next_status(outcome, {})

    assert payload["last_result"] == "accepted"
    assert payload["source_event_count"] == 2
    assert payload["inserted_event_count"] == 1
    assert payload["replayed_event_count"] == 1
    assert payload["consecutive_failures"] == 0
    assert not {
        "password",
        "username",
        "carrier",
        "tracking_number",
        "transaction_comment",
    } & set(payload)


def test_worker_failure_preserves_success_and_recovers_exactly_once() -> None:
    accepted = example("accepted-outcome.json")
    initial = next_status(accepted, {})
    failed = next_status(example("failed-outcome.json"), initial)
    assert failed["last_result"] == "failed"
    assert failed["last_success_at"] == "2026-08-31T16:00:00Z"
    assert failed["consecutive_failures"] == 1
    recovered = next_status({**accepted, "projected_at": "2026-08-31T16:00:20Z"}, failed)
    assert recovered["last_result"] == "accepted"
    assert recovered["consecutive_failures"] == 0
    assert recovered["last_success_at"] == "2026-08-31T16:00:20Z"
