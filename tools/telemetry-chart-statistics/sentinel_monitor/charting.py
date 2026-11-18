from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True, frozen=True)
class SeriesStats:
    minimum: float
    average: float
    p95: float
    maximum: float


def _finite_values(values: Iterable[float | None]) -> list[float]:
    return [
        float(value)
        for value in values
        if value is not None and math.isfinite(float(value))
    ]


def percentile(values: Iterable[float | None], fraction: float) -> float | None:
    """Return an interpolated percentile for finite values."""
    cleaned = sorted(_finite_values(values))
    if not cleaned:
        return None
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction must be between 0 and 1")
    if len(cleaned) == 1:
        return cleaned[0]
    position = (len(cleaned) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return cleaned[lower]
    weight = position - lower
    return cleaned[lower] * (1.0 - weight) + cleaned[upper] * weight


def series_stats(values: Iterable[float | None]) -> SeriesStats | None:
    cleaned = _finite_values(values)
    if not cleaned:
        return None
    p95 = percentile(cleaned, 0.95)
    assert p95 is not None
    return SeriesStats(
        minimum=min(cleaned),
        average=sum(cleaned) / len(cleaned),
        p95=p95,
        maximum=max(cleaned),
    )


def nice_axis_max(
    values: Iterable[float | None],
    *,
    minimum: float = 1.0,
    headroom: float = 1.08,
) -> float:
    """Return a readable 1/2/5/10-based upper axis bound."""
    cleaned = _finite_values(values)
    peak = max((max(0.0, value) for value in cleaned), default=0.0)
    target = max(float(minimum), peak * max(1.0, headroom))
    exponent = math.floor(math.log10(target)) if target > 0 else 0
    magnitude = 10.0**exponent
    fraction = target / magnitude
    for candidate in (1.0, 2.0, 5.0, 10.0):
        if fraction <= candidate:
            return candidate * magnitude
    return 10.0 * magnitude
