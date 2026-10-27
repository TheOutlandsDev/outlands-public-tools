"""Bounded baseline arithmetic over the public, clean ingestion contract."""
from dataclasses import dataclass
import math

from .ingestion import Batch, MAX_PERIOD, MAX_ROWS, Point, ReferenceError

MAX_HORIZON = 32
METHODS = ("last", "mean", "seasonal")


@dataclass(frozen=True)
class Score:
    count: int
    mae: float
    rmse: float


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ReferenceError("FORECAST_PARAMETER_INVALID")


def _parameters(method, window, season):
    if type(method) is not str or method not in METHODS:
        raise ReferenceError("FORECAST_METHOD_INVALID")
    _integer(window, 1, MAX_ROWS)
    _integer(season, 1, MAX_ROWS)


def _history(batch):
    if type(batch) is not Batch:
        raise ReferenceError("FORECAST_BATCH_INVALID")
    if (type(batch.records) is not tuple or type(batch.issues) is not tuple
            or type(batch.duplicates) is not int or batch.duplicates < 0
            or len(batch.records) + len(batch.issues) + batch.duplicates > MAX_ROWS):
        raise ReferenceError("FORECAST_BATCH_INVALID")
    points = batch.require_clean()
    for index, point in enumerate(points):
        if type(point) is not Point:
            raise ReferenceError("FORECAST_POINT_INVALID")
        # Revalidate typed fields; frozen classes are a convenience, not a
        # security boundary against a Python caller deliberately mutating them.
        Point(point.series, point.period, point.value)
        if index and (point.series != points[index - 1].series
                      or point.period != points[index - 1].period + 1):
            raise ReferenceError("FORECAST_ORDER_OR_GAP")
    return points


def _required_history(method, window, season):
    return window if method == "mean" else season if method == "seasonal" else 1


def _predict(history, horizon, method, window, season):
    if len(history) < _required_history(method, window, season):
        raise ReferenceError("FORECAST_HISTORY_REQUIRED")
    if method == "mean":
        value = math.fsum(point.value for point in history[-window:]) / window
        values = [value] * horizon
    elif method == "seasonal":
        values = [history[-season + index % season].value for index in range(horizon)]
    else:
        values = [history[-1].value] * horizon
    return tuple(Point(history[-1].series, history[-1].period + index, value)
                 for index, value in enumerate(values, 1))


def forecast(batch, *, horizon=1, method="last", window=3, season=1):
    """Predict ordinal periods from a clean, single contiguous series.

    Mean holds the observed trailing-window mean fixed across the horizon.
    Seasonal repeats the last complete observed season; no fitting is done.
    """
    history = _history(batch)
    _parameters(method, window, season)
    _integer(horizon, 1, MAX_HORIZON)
    if history[-1].period + horizon > MAX_PERIOD:
        raise ReferenceError("FORECAST_PERIOD_LIMIT")
    return _predict(history, horizon, method, window, season)


def rolling_score(batch, *, min_history=3, method="last", window=3, season=1):
    """Score one-step predictions using only each holdout's earlier prefix.

    min_history is explicit: it is never increased to conceal insufficient
    history. Every point after that prefix contributes equally to MAE/RMSE.
    """
    history = _history(batch)
    _parameters(method, window, season)
    _integer(min_history, 1, MAX_ROWS)
    if min_history >= len(history):
        raise ReferenceError("EVALUATION_HISTORY_REQUIRED")
    if min_history < _required_history(method, window, season):
        raise ReferenceError("FORECAST_HISTORY_REQUIRED")
    errors = []
    for index in range(min_history, len(history)):
        prediction = _predict(history[:index], 1, method, window, season)[0]
        errors.append(prediction.value - history[index].value)
    count = len(errors)
    return Score(count, math.fsum(abs(error) for error in errors) / count,
                 math.sqrt(math.fsum(error * error for error in errors) / count))
