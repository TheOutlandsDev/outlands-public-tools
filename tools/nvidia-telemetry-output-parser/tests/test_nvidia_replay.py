from __future__ import annotations

from sentinel_monitor.collectors.nvidia import _parse_replay_counters


def test_parse_replay_counters_maps_each_pci_bus() -> None:
    output = """
        Bus Id                            : 00000000:A1:00.0
        Replays Since Reset               : 0
        Bus Id                            : 00000000:A2:00.0
        Replays Since Reset               : 7
    """
    assert _parse_replay_counters(output) == {
        "00000000:A1:00.0": 0,
        "00000000:A2:00.0": 7,
    }
