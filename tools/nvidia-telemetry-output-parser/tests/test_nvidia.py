from sentinel_monitor.collectors.nvidia import _number


def test_number_handles_nvidia_missing_values() -> None:
    assert _number("[N/A]") is None
    assert _number("N/A") is None
    assert _number(" 41 ") == 41.0
