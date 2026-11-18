from sentinel_monitor.formatting import format_bytes, format_duration


def test_format_bytes() -> None:
    assert format_bytes(1536) == "1.5 KB"
    assert format_bytes(1024 * 1024, per_second=True) == "1.0 MB/s"


def test_format_duration() -> None:
    assert format_duration(90061) == "1d 1h 1m"

