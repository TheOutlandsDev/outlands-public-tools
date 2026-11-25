"""Preserve the assertions from the original collector-isolation test."""

import json
from pathlib import Path

from server_inventory_fallback import replay_server_inventory


ROOT = Path(__file__).resolve().parents[1]


def test_collector_isolates_server_inventory_and_reuses_previous() -> None:
    recording = json.loads((ROOT / "examples/replay-fallback.json").read_bytes())
    previous = recording["previous"]

    snapshot = replay_server_inventory(**recording)

    assert snapshot["servers"] == previous["servers"]
    assert snapshot["server_summary"] == previous["server_summary"]
    assert snapshot["source_health"]["server_inventory"]["state"] == "stale"
    assert snapshot["source_health"]["server_inventory"]["used_fallback"] is True
    assert snapshot["source_health"]["system"]["state"] == "fresh"
    assert "Fictional inventory read failed" in snapshot["source_health"]["server_inventory"]["error"]
    assert snapshot["source_coverage"]["CAC server inventory"].startswith("Stale:")
    assert snapshot["read_only_collection"] is True
