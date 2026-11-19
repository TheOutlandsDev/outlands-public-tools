"""Split known observation intervals and aggregate activity by metric unit."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, timezone
from typing import Any


MAX_INTERVALS = 10_000
MAX_SEGMENTS = 10_000
MAX_INTERVAL_DURATION = timedelta(days=366)
MAX_SERVER_ID_BYTES = 128
_STATES = {"online", "offline", "degraded", "unknown"}
_KINDS = {"players", "connections", "availability_only"}
_OFFSET = re.compile(r"([+-])([0-9]{2}):([0-9]{2})")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})"
)


@dataclass(frozen=True, slots=True)
class _Interval:
    server_id: str
    state: str
    kind: str
    population: int | None
    start: datetime
    end: datetime


@dataclass(slots=True)
class _Totals:
    observed: int = 0
    online: int = 0
    player_seconds: int = 0
    connection_seconds: int = 0

    def add(self, observed: int, online: int, players: int, connections: int) -> None:
        self.observed += observed
        self.online += online
        self.player_seconds += players
        self.connection_seconds += connections

    def as_report(self) -> dict[str, int | float]:
        try:
            player_hours = self.player_seconds / 3600
            connection_hours = self.connection_seconds / 3600
        except OverflowError:
            raise ValueError("Activity totals are too large") from None
        return {
            "observed_seconds": self.observed,
            "online_seconds": self.online,
            "player_hours": player_hours,
            "connection_hours": connection_hours,
        }


def _parse_offset(value: object) -> timezone:
    if value == "Z":
        return UTC
    match = _OFFSET.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise ValueError("UTC offset must be Z or +/-HH:MM")
    sign, hours, minutes = match.groups()
    if int(hours) >= 24 or int(minutes) >= 60:
        raise ValueError("UTC offset is out of range")
    delta = timedelta(hours=int(hours), minutes=int(minutes))
    return timezone(-delta if sign == "-" else delta)


def _parse_time(value: object, display_zone: timezone) -> datetime:
    match = _TIMESTAMP.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise ValueError("Interval timestamps must use whole seconds and an explicit UTC offset")
    try:
        source_zone = _parse_offset(match.group(1))
        return datetime.fromisoformat(value[:19]).replace(tzinfo=source_zone).astimezone(display_zone)
    except (OverflowError, ValueError):
        raise ValueError("Interval timestamp is invalid or outside the display range") from None


def _parse_interval(row: object, display_zone: timezone) -> _Interval:
    if not isinstance(row, dict):
        raise ValueError("Intervals must contain objects")
    server_id = row.get("server_id")
    if not isinstance(server_id, str) or not server_id.strip() or len(server_id) > MAX_SERVER_ID_BYTES:
        raise ValueError("Server ID must be nonblank UTF-8 text of at most 128 bytes")
    try:
        if len(server_id.encode("utf-8")) > MAX_SERVER_ID_BYTES:
            raise ValueError("Server ID must be nonblank UTF-8 text of at most 128 bytes")
    except UnicodeEncodeError:
        raise ValueError("Server ID must be nonblank UTF-8 text of at most 128 bytes") from None

    state = row.get("state")
    if not isinstance(state, str) or state not in _STATES:
        raise ValueError("Invalid interval state")
    kind = row.get("metric_kind")
    if not isinstance(kind, str) or kind not in _KINDS:
        raise ValueError("Invalid interval metric kind")
    population = row.get("population")
    if population is not None and (type(population) is not int or population < 0):
        raise ValueError("Population must be a nonnegative integer or null")

    start = _parse_time(row.get("start"), display_zone)
    end = _parse_time(row.get("end"), display_zone)
    duration = end - start
    if not timedelta() < duration <= MAX_INTERVAL_DURATION:
        raise ValueError("Interval duration must be positive and at most 366 days")
    return _Interval(server_id, state, kind, population, start, end)


def calculate_intervals(
    intervals: object,
    *,
    display_offset: str,
) -> dict[str, Any]:
    """Report daily and aggregate totals for disjoint intervals by server."""
    if not isinstance(intervals, list) or len(intervals) > MAX_INTERVALS:
        raise ValueError("Expected an array of at most 10000 intervals")
    display_zone = _parse_offset(display_offset)
    ordered = sorted(
        (_parse_interval(row, display_zone) for row in intervals),
        key=lambda interval: (interval.server_id, interval.start),
    )

    previous: _Interval | None = None
    segments = 0
    totals = _Totals()
    daily: dict[tuple[str, str], _Totals] = {}
    for interval in ordered:
        if (
            previous is not None
            and interval.server_id == previous.server_id
            and interval.start < previous.end
        ):
            raise ValueError("Intervals for the same server must not overlap")
        previous = interval

        cursor = interval.start
        while cursor < interval.end:
            segments += 1
            if segments > MAX_SEGMENTS:
                raise ValueError("At most 10000 daily segments are allowed")
            day = cursor.date()
            segment_end = interval.end
            if day != interval.end.date():
                segment_end = datetime.combine(day + timedelta(days=1), time.min, display_zone)
            elapsed = segment_end - cursor
            observed = elapsed.days * 86_400 + elapsed.seconds
            online = observed if interval.state == "online" else 0
            activity = (
                online * (interval.population or 0) if interval.kind != "availability_only" else 0
            )
            players = activity if interval.kind == "players" else 0
            connections = activity if interval.kind == "connections" else 0
            key = (day.isoformat(), interval.server_id)
            if key not in daily:
                daily[key] = _Totals()
            daily[key].add(observed, online, players, connections)
            totals.add(observed, online, players, connections)
            cursor = segment_end

    return {
        "daily": [
            {"day": day, "server_id": server_id, **bucket.as_report()}
            for (day, server_id), bucket in sorted(daily.items())
        ],
        "totals": totals.as_report(),
    }
