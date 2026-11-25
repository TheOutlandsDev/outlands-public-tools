"""Replay the server inventory fallback decision from saved collection evidence."""

import argparse
from copy import deepcopy
from datetime import UTC, datetime
import json
from math import isfinite
from pathlib import Path
from typing import Any


MAX_SNAPSHOT_BYTES = 1024 * 1024


def _source_age_seconds(value: Any, *, now: Any = None) -> float | None:
    if not value:
        return None
    try:
        captured = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=UTC)
        if now is None:
            current = datetime.now(UTC)
        else:
            current = datetime.fromisoformat(str(now).replace("Z", "+00:00"))
            if current.tzinfo is None:
                current = current.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None
    return round(
        max(
            0.0,
            (current.astimezone(UTC) - captured.astimezone(UTC)).total_seconds(),
        ),
        3,
    )


def replay_server_inventory(
    *, generated: str, duration_ms: float, inventory: dict[str, Any],
    previous: dict[str, Any], source_health: dict[str, Any],
) -> dict[str, Any]:
    """Report the server inventory and health produced by a recorded collection."""
    previous_sources = previous.get("source_health", {})
    if not isinstance(previous_sources, dict):
        previous_sources = {}
    previous_health = previous_sources.get("server_inventory", {})
    if not isinstance(previous_health, dict):
        previous_health = {}

    result = inventory.get("result")
    if "error" in inventory:
        failure = inventory["error"]
        error = f"{failure['type']}: {failure['message']}"[:500]
    elif (not isinstance(result, dict) or not isinstance(result.get("programs"), list)
          or not isinstance(result.get("summary"), dict)):
        error = "ValueError: Server inventory returned an invalid payload"
    else:
        error = ""

    duration_ms = round(duration_ms, 3)
    if error:
        collected_at = previous_health.get("collected_at") or previous.get("generated") or None
        fallback_available = (
            isinstance(previous.get("servers"), list)
            and isinstance(previous.get("server_summary"), dict)
            and str(previous_health.get("state", "fresh")).casefold() != "unavailable"
        )
        programs = previous["servers"] if fallback_available else []
        summary = previous["server_summary"] if fallback_available else {}
        age = _source_age_seconds(collected_at, now=generated)
        state = "stale" if fallback_available else "unavailable"
        age_text = "unknown age" if age is None else f"{float(age):.0f}s old"
        coverage = (
            f"Stale: using cached data ({age_text})" if fallback_available
            else "Unavailable: isolated collector failed and no fallback exists"
        )
    else:
        programs = result["programs"]
        summary = result["summary"]
        collected_at = generated
        age = 0.0
        state = "fresh"
        fallback_available = False
        coverage = f"Fresh: collected 0.0s before snapshot ({duration_ms:.0f} ms)"

    health = {
        "state": state,
        "collected_at": collected_at,
        "age_seconds": age,
        "duration_ms": duration_ms,
        "used_fallback": fallback_available,
        "error": error,
    }
    return deepcopy({
        "generated": generated,
        "servers": programs,
        "server_summary": summary,
        "source_health": {**source_health, "server_inventory": health},
        "source_coverage": {"CAC server inventory": coverage},
        "read_only_collection": True,
    })


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-JSON constant")


def finite_float(raw):
    value = float(raw)
    if not isfinite(value):
        raise ValueError("Nonfinite JSON number")
    return value


def read_json(path: Path) -> Any:
    try:
        if not path.is_file():
            raise OSError
        with path.open("rb") as stream:
            payload = stream.read(MAX_SNAPSHOT_BYTES + 1)
    except OSError:
        raise ValueError("Unable to read the telemetry snapshot.") from None

    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise ValueError("The telemetry snapshot exceeds the 1 MiB limit.")

    try:
        return json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant, parse_float=finite_float)
    except (ValueError, RecursionError):
        raise ValueError("Invalid telemetry JSON.") from None


def read_recording(path: Path) -> dict[str, Any]:
    data = read_json(path)
    if (not isinstance(data, dict)
            or data.keys() - {"generated", "duration_ms", "inventory", "previous", "source_health"}):
        raise ValueError("Invalid inventory recording fields.")
    generated = data.get("generated")
    if not isinstance(generated, str) or _source_age_seconds(generated, now=generated) is None:
        raise ValueError("A valid replay timestamp is required.")
    duration = data.get("duration_ms")
    try:
        if type(duration) not in (int, float) or not isfinite(duration) or duration < 0:
            raise ValueError
    except (ValueError, OverflowError):
        raise ValueError("Collection duration must be a nonnegative finite number.") from None
    inventory = data.get("inventory")
    if not isinstance(inventory, dict) or inventory.keys() not in ({"result"}, {"error"}):
        raise ValueError("Specify one recorded inventory result or error.")
    if "error" in inventory:
        failure = inventory["error"]
        if (not isinstance(failure, dict) or failure.keys() != {"type", "message"}
                or not isinstance(failure["type"], str) or not failure["type"].isidentifier()
                or len(failure["type"]) > 120 or not isinstance(failure["message"], str)):
            raise ValueError("Invalid recorded inventory error.")
    previous = data.get("previous", {})
    source_health = data.get("source_health", {})
    if not isinstance(previous, dict) or not isinstance(source_health, dict):
        raise ValueError("Previous snapshot and current source health must be objects.")
    return {
        "generated": generated, "duration_ms": duration, "inventory": inventory,
        "previous": previous, "source_health": source_health,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path, help="Saved inventory result or error and optional previous snapshot")
    args = parser.parse_args()
    try:
        report = replay_server_inventory(**read_recording(args.recording))
        output = json.dumps(report, indent=2, allow_nan=False)
    except (UnicodeError, RecursionError, OverflowError):
        parser.exit(2, "Invalid inventory recording text, timestamp, or nesting.\n")
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
