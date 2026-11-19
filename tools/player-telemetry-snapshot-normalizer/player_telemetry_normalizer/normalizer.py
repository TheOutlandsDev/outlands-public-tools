"""Normalize one of the two supported snapshot formats without external I/O."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, NoReturn

MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_ROWS = 10_000
MAX_ID_BYTES = 128

_ARRAY_KEYS = {"portal": "servers", "collector": "players_connections"}
_METRIC_KINDS = ("availability_only", "connections", "players")
_STATES = {
    "healthy": "online",
    "online": "online",
    "warning": "degraded",
    "degraded": "degraded",
    "down": "offline",
    "offline": "offline",
    "critical": "offline",
}


class SnapshotError(ValueError):
    """A snapshot, mapping, or input file does not meet the input contract."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotError("JSON object contains a duplicate key")
        result[key] = value
    return result


def _reject_nonfinite(_value: str) -> NoReturn:
    raise SnapshotError("JSON number must be finite")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise SnapshotError("JSON number must be finite")
    return number


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise SnapshotError("input must be a regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise SnapshotError("input exceeds the maximum size")
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
            parse_float=_finite_float,
        )
    except SnapshotError:
        raise
    except (ValueError, RecursionError) as exc:
        raise SnapshotError("input must contain valid UTF-8 JSON") from exc


def _valid_id(value: object) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_ID_BYTES:
        return False
    try:
        return len(value.encode("utf-8")) <= MAX_ID_BYTES
    except UnicodeEncodeError:
        return False


def _validate_mapping(mapping: object, source_format: str) -> dict[str, dict[str, str]]:
    if (
        not isinstance(mapping, dict)
        or source_format not in mapping
        or any(section not in _ARRAY_KEYS for section in mapping)
    ):
        raise SnapshotError("mapping must contain the selected format")
    for section, entries in mapping.items():
        if not isinstance(entries, dict) or len(entries) > MAX_ROWS:
            raise SnapshotError("mapping section must be a bounded object")
        kinds = (*_METRIC_KINDS, "auto") if section == "portal" else _METRIC_KINDS
        for source_id, rule in entries.items():
            if (
                not _valid_id(source_id)
                or not isinstance(rule, dict)
                or rule.keys() != {"server_id", "metric_kind"}
                or not _valid_id(rule["server_id"])
                or rule["metric_kind"] not in kinds
            ):
                raise SnapshotError("mapping entry is invalid")
    return mapping[source_format]


def _normalize_state(value: object) -> str:
    return _STATES.get(value.lower(), "unknown") if isinstance(value, str) else "unknown"


def _normalize_count(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _point(row: dict[str, Any], rule: dict[str, str], source_format: str) -> dict[str, Any]:
    kind = rule["metric_kind"]
    if source_format == "portal":
        if kind == "auto":
            label = row.get("populationLabel")
            kind = "connections" if isinstance(label, str) and label.casefold() == "connections" else "players"
        state, population, capacity = row.get("state"), row.get("population"), row.get("capacity")
    else:
        count_key = "connection_sessions" if kind == "connections" else "players"
        state, population, capacity = (
            row.get("server_status"),
            row.get(count_key),
            row.get("max_players"),
        )
    return {
        "server_id": rule["server_id"],
        "state": _normalize_state(state),
        "population": _normalize_count(population),
        "capacity": _normalize_count(capacity),
        "metric_kind": kind,
    }


def normalize_snapshot(
    snapshot: object,
    mapping: object,
    source_format: str,
) -> dict[str, list[dict[str, Any]]]:
    """Convert a decoded snapshot into allowlisted point records in input order.

    The mapping supplies canonical server IDs and metric kinds. Unmapped rows are
    skipped. Both snapshot and mapping are read without modifying either object.
    """
    if source_format not in ("portal", "collector"):
        raise SnapshotError("unsupported snapshot format")
    entries = _validate_mapping(mapping, source_format)
    if not isinstance(snapshot, dict):
        raise SnapshotError("snapshot must be an object")
    rows = snapshot.get(_ARRAY_KEYS[source_format])
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise SnapshotError("snapshot must contain a bounded array for the selected format")
    points = []
    for row in rows:
        if not isinstance(row, dict):
            raise SnapshotError("snapshot rows must be objects")
        source_id = row.get("id")
        if isinstance(source_id, str) and source_id in entries:
            points.append(_point(row, entries[source_id], source_format))
    return {"points": points}
