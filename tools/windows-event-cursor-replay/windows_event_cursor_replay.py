"""Replay a saved Windows event-log batch against a cursor, entirely offline."""

from __future__ import annotations

import argparse
from collections import deque
from datetime import UTC, datetime, timedelta
import json
import math
from pathlib import Path
import sys
from stat import S_ISREG

HISTORY_LIMIT = 5_000
FILE_LIMIT = 2_000_000
EVENT_LIMIT = 10_000


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("Invalid JSON number")


def _decode(raw):
    return json.loads(
        raw.decode("utf-8-sig"), object_pairs_hook=_unique_keys, parse_constant=_reject_constant,
    )


def _timestamp(value, *, default_zone=None):
    if not isinstance(value, str):
        raise ValueError("Expected an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("Expected an ISO 8601 timestamp") from None
    if parsed.tzinfo is None:
        if default_zone is None:
            raise ValueError("Expected a timestamp with a UTC offset")
        parsed = parsed.replace(tzinfo=default_zone)
    return parsed


def _record_key(record):
    channel = record["channel"]
    number = record["record_id"]
    if not isinstance(channel, str) or not channel.strip() or len(channel) > 256:
        raise ValueError("Invalid channel")
    if type(number) is not int or not 0 <= number <= 2**63 - 1:
        raise ValueError("Invalid record ID")
    return channel, number


def _restore(raw, now):
    if raw is None:
        return None, ()
    try:
        payload = _decode(raw)
        last_query = _timestamp(payload["last_query"], default_zone=now.tzinfo).astimezone(UTC)
        if last_query - now > timedelta(minutes=5):
            return None, ()
        seen = payload.get("seen", [])
        if not isinstance(seen, list):
            return None, ()
    except (KeyError, ValueError, TypeError, OverflowError, RecursionError):
        return None, ()

    recent = {}
    # A cursor emitted by the collector contains unique keys. For repeated
    # entries in incoming state, keep the most recent occurrence.
    for record in reversed(seen[-HISTORY_LIMIT:]):
        try:
            recent.setdefault(_record_key(record), None)
        except (KeyError, TypeError, ValueError):
            continue
    return last_query, tuple(reversed(recent))


def _prepare_events(events):
    if not isinstance(events, list) or len(events) > EVENT_LIMIT:
        raise ValueError("Events must be an array of at most 10,000 records")
    prepared = []
    for index, record in enumerate(events, start=1):
        try:
            key = _record_key(record)
            stamp = _timestamp(record["timestamp"]).astimezone(UTC)
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"Invalid event record at position {index}") from error
        prepared.append((stamp, key))
    return sorted(prepared, key=lambda item: item[0])


def replay(cursor, events, *, observed_at, startup_lookback_seconds=10.0):
    """Return new event identities and a cursor for the successful saved batch.

    The cursor is its saved UTF-8 bytes, or None when no cursor is available.
    Events are previously collected rows with channel, record_id and timestamp.
    """
    if not math.isfinite(startup_lookback_seconds):
        raise ValueError("Startup lookback must be finite")
    observation = _timestamp(observed_at)
    now = observation.astimezone(UTC)
    last_query, history = _restore(cursor, observation)
    cursor_loaded = last_query is not None
    if last_query is None:
        lookback = max(2.0, min(startup_lookback_seconds, 300.0))
        last_query = now - timedelta(seconds=lookback)

    seen_order = deque(history, maxlen=HISTORY_LIMIT)
    seen = set(history)
    new_events = []
    for stamp, key in _prepare_events(events):
        if key in seen:
            continue
        if len(seen_order) == HISTORY_LIMIT:
            seen.remove(seen_order.popleft())
        seen_order.append(key)
        seen.add(key)
        channel, number = key
        new_events.append({"channel": channel, "record_id": number, "timestamp": stamp.isoformat()})

    return {
        "cursor_loaded": cursor_loaded,
        "last_query": last_query.isoformat(),
        "query_since": (last_query - timedelta(seconds=2)).isoformat(),
        "new_events": new_events,
        "next_cursor": {
            "schema_version": 1,
            "updated_at": now.isoformat(),
            "last_query": now.isoformat(),
            "seen": [{"channel": channel, "record_id": number} for channel, number in seen_order],
        },
    }


def _read(path, label, *, allow_missing=False):
    try:
        if not S_ISREG(path.stat().st_mode):
            raise OSError
        with path.open("rb") as stream:
            raw = stream.read(FILE_LIMIT + 1)
    except FileNotFoundError:
        if allow_missing:
            return None
        raise ValueError(f"{label} must be a readable regular file") from None
    except OSError:
        raise ValueError(f"{label} must be a readable regular file") from None
    if len(raw) > FILE_LIMIT:
        raise ValueError(f"{label} exceeds 2,000,000 bytes")
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cursor", type=Path, help="Saved cursor JSON, optional")
    parser.add_argument("--events", required=True, type=Path, help="Saved event batch JSON")
    parser.add_argument("--observed-at", required=True, help="Replay timestamp with a UTC offset")
    parser.add_argument("--startup-lookback-seconds", type=float, default=10.0)
    args = parser.parse_args()
    try:
        cursor = _read(args.cursor, "Cursor", allow_missing=True) if args.cursor else None
        raw = _read(args.events, "Event batch")
        try:
            events = _decode(raw)
        except (ValueError, RecursionError):
            raise ValueError("Event batch must be valid UTF-8 JSON with unique keys") from None
        report = replay(
            cursor, events, observed_at=args.observed_at,
            startup_lookback_seconds=args.startup_lookback_seconds,
        )
    except (ValueError, OverflowError) as error:
        # Avoid echoing malformed timestamps or other caller-supplied text.
        message = str(error)
        if isinstance(error, OverflowError):
            message = "Invalid timestamp or timestamp arithmetic"
        sys.stderr.write(f"{message}\n")
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
