import pytest

from sentinel_monitor.charting import nice_axis_max, percentile, series_stats


def test_percentile_interpolates_and_ignores_missing_values() -> None:
    assert percentile([None, 0.0, 10.0, 20.0], 0.5) == 10.0
    assert percentile([0.0, 10.0], 0.95) == pytest.approx(9.5)


def test_series_stats_reports_rolling_summary() -> None:
    stats = series_stats([10.0, 20.0, 30.0, 40.0])
    assert stats is not None
    assert stats.minimum == 10.0
    assert stats.average == 25.0
    assert stats.p95 == pytest.approx(38.5)
    assert stats.maximum == 40.0


def test_nice_axis_max_uses_readable_bounds() -> None:
    assert nice_axis_max([0.0]) == 1.0
    assert nice_axis_max([71.0]) == 100.0
    assert nice_axis_max([1_100_000.0]) == 2_000_000.0
