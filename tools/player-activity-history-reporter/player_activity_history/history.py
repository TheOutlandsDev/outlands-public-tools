"""Reconcile baseline, observed, and archived activity from a saved report input."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
from typing import Any


MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_SERVERS = 1_000
MAX_HISTORY_ROWS = 50_000
MAX_NUMBER = 10**12
_MAX_SERVER_ID_BYTES = 128
_EVENT_LIMIT = 40
_ZERO = Decimal(0)
_KINDS = ("players", "connections", "availability_only")
_STATES = ("online", "offline", "degraded", "unknown")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_OFFSET = re.compile(r"([+-])([0-9]{2}):([0-9]{2})")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})"
)


class ReportError(ValueError):
    """The activity input violates the report's data contract."""


@dataclass(slots=True)
class _Totals:
    """Keep all quantities in seconds until the summary is rendered."""

    baseline: Decimal = _ZERO
    observed_7d: Decimal = _ZERO
    observed_30d: Decimal = _ZERO
    active_observed: Decimal = _ZERO
    archived_observed: Decimal = _ZERO
    archived_baseline: Decimal = _ZERO

    def add(self, other: "_Totals") -> None:
        self.baseline += other.baseline
        self.observed_7d += other.observed_7d
        self.observed_30d += other.observed_30d
        self.active_observed += other.active_observed
        self.archived_observed += other.archived_observed
        self.archived_baseline += other.archived_baseline

    def as_report(self) -> dict[str, float]:
        baseline = self.baseline + self.archived_baseline
        active = self.baseline + self.active_observed
        archived = self.archived_baseline + self.archived_observed
        return {
            "baseline_hours": _hours(baseline),
            "observed_7d_hours": _hours(self.observed_7d),
            "observed_30d_hours": _hours(self.observed_30d),
            "observed_lifetime_hours": _hours(self.active_observed + self.archived_observed),
            "active_lifetime_hours": _hours(active),
            "archived_lifetime_hours": _hours(archived),
            "lifetime_hours": _hours(active + archived),
            "seeded_7d_hours": _hours(baseline + self.observed_7d),
            "seeded_30d_hours": _hours(baseline + self.observed_30d),
        }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReportError("JSON objects must have unique keys")
        result[key] = value
    return result


def _reject_constant(_value: str) -> Any:
    raise ReportError("JSON numbers must be finite")


def read_history(path: Path) -> Any:
    """Read a bounded UTF-8 JSON document without opening a non-file input."""
    if not path.is_file():
        raise ReportError("Input must be a regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ReportError("Input exceeds its byte limit")
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_float=Decimal,
            parse_constant=_reject_constant,
        )
    except (ValueError, ArithmeticError, RecursionError) as exc:
        if isinstance(exc, ReportError):
            raise
        raise ReportError("Input must contain valid UTF-8 JSON") from None


def _parse_date(value: object) -> date:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise ReportError("Dates must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ReportError("Date is outside the calendar") from None


def _parse_offset(value: object) -> timezone:
    if value == "Z":
        return UTC
    match = _OFFSET.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise ReportError("UTC offsets must use Z or +/-HH:MM")
    sign, hours, minutes = match.groups()
    if int(hours) > 23 or int(minutes) > 59:
        raise ReportError("UTC offset is out of range")
    delta = timedelta(hours=int(hours), minutes=int(minutes))
    return timezone(-delta if sign == "-" else delta)


def _parse_timestamp(value: object) -> datetime:
    match = _TIMESTAMP.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise ReportError("Observation times must include seconds and a UTC offset")
    try:
        source_zone = _parse_offset(match.group(1))
        local = datetime.fromisoformat(value[:match.start(1)]).replace(tzinfo=source_zone)
        return local.astimezone(UTC)
    except (ValueError, OverflowError):
        raise ReportError("Observation time is outside the calendar") from None


def _number(value: object) -> Decimal:
    if type(value) not in (int, float, Decimal):
        raise ReportError("Activity values must be numbers")
    number = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    if not number.is_finite() or not _ZERO <= number <= MAX_NUMBER:
        raise ReportError("Activity values must be finite and within the numeric limit")
    return max(_ZERO, number)


def _hours(seconds: Decimal, digits: int = 2) -> float:
    return float(round(seconds / 3600, digits))


def _object(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReportError("Report entries must be objects")
    return value


def _list(value: object, limit: int) -> list[Any]:
    if not isinstance(value, list) or len(value) > limit:
        raise ReportError("Report arrays must be within their size limits")
    return value


def _server_id(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > _MAX_SERVER_ID_BYTES:
        raise ReportError("Server ID must be nonblank UTF-8 text of at most 128 bytes")
    try:
        if len(value.encode("utf-8")) <= _MAX_SERVER_ID_BYTES:
            return value
    except UnicodeEncodeError:
        pass
    raise ReportError("Server ID must be nonblank UTF-8 text of at most 128 bytes")


def _metric_kind(value: object) -> str:
    if not isinstance(value, str) or value not in _KINDS:
        raise ReportError("Unsupported activity metric kind")
    return value


def _daily_history(rows: list[Any], report_date: date, tracked: bool) -> dict[date, Decimal]:
    history: dict[date, Decimal] = {}
    for value in rows:
        row = _object(value)
        day = _parse_date(row.get("date"))
        if day > report_date or day in history:
            raise ReportError("Daily dates must be unique and at or before the report date")
        seconds = _number(row.get("activity_seconds"))
        history[day] = seconds if tracked else _ZERO
    return history


def _transitions(
    rows: list[Any],
    server_id: str,
    display_zone: timezone,
    start: date,
    report_date: date,
) -> list[tuple[datetime, str, dict[str, str]]]:
    states: dict[datetime, tuple[datetime, str]] = {}
    for value in rows:
        row = _object(value)
        instant = _parse_timestamp(row.get("observed_at"))
        try:
            local = instant.astimezone(display_zone)
        except OverflowError:
            raise ReportError("Observation time is outside the display calendar") from None
        state = row.get("state")
        if not isinstance(state, str) or state not in _STATES:
            raise ReportError("Unsupported server state")
        if local.date() > report_date or instant in states:
            raise ReportError("Observation times must be unique and at or before the report date")
        states[instant] = local, state

    events = []
    previous = None
    for instant in sorted(states):
        local, state = states[instant]
        if previous is not None and state != previous and local.date() >= start:
            events.append((instant, server_id, {
                "server_id": server_id,
                "observed_at": local.isoformat(),
                "from_state": previous,
                "to_state": state,
            }))
        previous = state
    return events


def _point(day: date, activity: Decimal, cumulative: Decimal) -> dict[str, str | float]:
    return {
        "date": day.isoformat(),
        "activity_hours": _hours(activity, 3),
        "cumulative_hours": _hours(cumulative),
    }


def _daily_points(
    history: dict[date, Decimal], start: date, baseline: Decimal
) -> list[dict[str, str | float]]:
    cumulative_seconds = sum((amount for day, amount in history.items() if day < start), _ZERO)
    points = []
    for offset in range(30):
        day = start + timedelta(days=offset)
        seconds = history.get(day, _ZERO)
        cumulative_seconds += seconds
        points.append(_point(day, seconds, baseline + cumulative_seconds))
    return points


def _weekly_points(
    history: dict[date, Decimal], report_date: date, baseline: Decimal
) -> list[dict[str, str | float]]:
    if not history:
        return []
    weeks: defaultdict[date, Decimal] = defaultdict(Decimal)
    for day, seconds in history.items():
        monday = day - timedelta(days=day.weekday())
        weeks[monday] += seconds
    points = [_point(min(history), _ZERO, baseline)]
    cumulative_seconds = _ZERO
    for monday, seconds in sorted(weeks.items()):
        end = date.fromordinal(min(monday.toordinal() + 6, report_date.toordinal()))
        cumulative_seconds += seconds
        points.append(_point(end, seconds, baseline + cumulative_seconds))
    return points


def _active_totals(
    history: dict[date, Decimal], baseline: Decimal, start_7d: date, start_30d: date
) -> _Totals:
    seconds_7d = sum((amount for day, amount in history.items() if day >= start_7d), _ZERO)
    seconds_30d = sum((amount for day, amount in history.items() if day >= start_30d), _ZERO)
    return _Totals(
        baseline=baseline,
        observed_7d=seconds_7d,
        observed_30d=seconds_30d,
        active_observed=sum(history.values(), _ZERO),
    )


def build_report(
    data: object, as_of: str, display_offset: str = "+00:00"
) -> dict[str, Any]:
    """Build a deterministic report at a caller-supplied local calendar date."""
    report_date = _parse_date(as_of)
    if report_date.toordinal() < 30:
        raise ReportError("Report date is too early for a complete 30-day window")
    display_zone = _parse_offset(display_offset)
    start_7d = report_date - timedelta(days=6)
    start_30d = report_date - timedelta(days=29)
    document = _object(data)
    active_rows = _list(document.get("active"), MAX_SERVERS)
    archived_rows = _list(document.get("archived"), MAX_SERVERS)

    all_totals = {kind: _Totals() for kind in ("players", "connections")}
    seen_ids = set()
    active = []
    archived = []
    events = []
    remaining = MAX_HISTORY_ROWS
    for value in active_rows:
        row = _object(value)
        server_id = _server_id(row.get("server_id"))
        kind = _metric_kind(row.get("metric_kind"))
        if server_id in seen_ids:
            raise ReportError("Server IDs must be unique")
        seen_ids.add(server_id)
        daily_rows = _list(row.get("daily"), remaining)
        state_rows = _list(row.get("states", []), remaining - len(daily_rows))
        remaining -= len(daily_rows) + len(state_rows)
        tracked = kind != "availability_only"
        baseline = _number(row.get("baseline_hours")) * 3600
        baseline = baseline if tracked else _ZERO
        history = _daily_history(daily_rows, report_date, tracked)
        totals = _active_totals(history, baseline, start_7d, start_30d)
        if tracked:
            all_totals[kind].add(totals)
        active.append({
            "server_id": server_id,
            "metric_kind": kind,
            "activity_tracked": tracked,
            "totals": totals.as_report(),
            "daily_30d": _daily_points(history, start_30d, baseline),
            "weekly_lifetime": _weekly_points(history, report_date, baseline) if tracked else [],
        })
        events.extend(_transitions(state_rows, server_id, display_zone, start_30d, report_date))

    for value in archived_rows:
        row = _object(value)
        server_id = _server_id(row.get("server_id"))
        kind = _metric_kind(row.get("metric_kind"))
        if server_id in seen_ids:
            raise ReportError("Server IDs must be unique")
        seen_ids.add(server_id)
        baseline = _number(row.get("baseline_hours")) * 3600
        observed = _number(row.get("observed_activity_seconds"))
        if kind == "availability_only":
            baseline = observed = _ZERO
        else:
            all_totals[kind].add(_Totals(archived_baseline=baseline, archived_observed=observed))
        archived.append({
            "server_id": server_id,
            "metric_kind": kind,
            "baseline_hours": _hours(baseline),
            "observed_lifetime_hours": _hours(observed),
            "lifetime_hours": _hours(baseline + observed),
        })

    events.sort(key=lambda event: event[1])
    events.sort(key=lambda event: event[0], reverse=True)
    return {
        "as_of": report_date.isoformat(),
        "display_offset": display_offset,
        "totals": {kind: totals.as_report() for kind, totals in all_totals.items()},
        "servers": active,
        "archived": archived,
        "events": [record for _, _, record in events[:_EVENT_LIMIT]],
    }
