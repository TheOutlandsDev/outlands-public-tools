from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pathlib import Path

from incident_store.models import IncidentCandidate
from incident_store.storage import CacStorage


def test_incident_transitions_to_resolved(tmp_path: Path) -> None:
    storage = CacStorage(tmp_path / "fictional-replay.db", clean_samples=2, retention_days=7)
    candidate = IncidentCandidate(
        "test",
        "failure",
        "warning",
        "fictional sensor failure",
        {"value": 1},
    )
    generated = datetime.now(timezone.utc).replace(microsecond=0)
    snapshot = {"generated": generated.isoformat(), "overall_status": "warning"}
    storage.save_snapshot(snapshot, [candidate])
    snapshot["generated"] = (generated + timedelta(minutes=1)).isoformat()
    storage.save_snapshot(snapshot, [])
    assert storage.incidents()[0]["state"] == "monitoring"
    snapshot["generated"] = (generated + timedelta(minutes=2)).isoformat()
    storage.save_snapshot(snapshot, [])
    assert storage.incidents()[0]["state"] == "resolved"
    latest = storage.latest_snapshot()
    assert latest is not None
    assert latest["generated"] == (generated + timedelta(minutes=2)).isoformat()
    assert storage.integrity_check() == "ok"



def test_acknowledge_and_clear_resolved_are_bounded(tmp_path: Path) -> None:
    storage = CacStorage(tmp_path / "fictional-replay.db", clean_samples=1, retention_days=7)
    candidate = IncidentCandidate("server:demo", "health", "warning", "test", {})
    generated = datetime.now(timezone.utc).replace(microsecond=0)
    snapshot = {"generated": generated.isoformat(), "overall_status": "warning"}
    storage.save_snapshot(snapshot, [candidate])
    fingerprint = storage.incidents()[0]["fingerprint"]
    assert storage.acknowledge_incident(fingerprint) is True
    assert storage.incidents()[0]["acknowledged_at"] is not None
    assert storage.clear_resolved_incidents() == 0
    snapshot["generated"] = (generated + timedelta(minutes=1)).isoformat()
    storage.save_snapshot(snapshot, [])
    assert storage.incidents()[0]["state"] == "resolved"
    assert storage.clear_resolved_incidents() == 1
    assert storage.incidents() == []