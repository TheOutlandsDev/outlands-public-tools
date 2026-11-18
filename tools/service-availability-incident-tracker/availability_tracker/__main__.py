"""Apply saved service observations to a local availability state."""

import argparse
import json
import stat
from datetime import UTC, datetime
from pathlib import Path

from .tracker import apply_transition, determine_overall, write_json_atomic


MAX_INPUT_BYTES = 4 * 1024 * 1024
OVERALL_STATES = {"online", "degraded", "offline"}
OUTAGE_STATES = OVERALL_STATES - {"online"}


def _read_json(path: Path) -> object:
    if not path.is_file():
        raise ValueError("input must be a regular file")
    with path.open("rb") as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 4 MiB")
    return json.loads(raw.decode("utf-8-sig"))


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("expected an ISO 8601 timestamp with a time zone")
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("expected an ISO 8601 timestamp with a time zone") from None
    if result.tzinfo is None:
        raise ValueError("expected an ISO 8601 timestamp with a time zone")
    return result.astimezone(UTC)


def _load_state(path: Path | None, observations: Path) -> tuple[dict, datetime | None]:
    if path is None:
        return {}, None
    if not path.parent.is_dir():
        raise ValueError("state needs a file in an existing directory")
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return {}, None
    if not stat.S_ISREG(mode) or path.samefile(observations):
        raise ValueError("state must be a separate regular file")

    state = _read_json(path)
    if (
        not isinstance(state, dict)
        or type(state.get("schemaVersion")) is not int
        or state["schemaVersion"] != 1
    ):
        raise ValueError("state must use schema version 1")
    overall = state.get("previousOverall")
    if not isinstance(overall, str) or overall not in OVERALL_STATES:
        raise ValueError("state contains an invalid availability status")
    previous = _timestamp(state.get("previousObservedAt"))
    active = state.get("activeIncident")
    if overall == "online":
        if active is not None:
            raise ValueError("online state cannot have an active incident")
    else:
        if not isinstance(active, dict) or _timestamp(active.get("startedAt")) > previous:
            raise ValueError("outage state needs a valid incident start")
        for key in ("initialState", "worstState"):
            if not isinstance(active.get(key), str) or active[key] not in OUTAGE_STATES:
                raise ValueError("incident statuses must be degraded or offline")
    return state, previous


def _apply_observations(observations: object, state: dict, previous: datetime | None) -> list[dict]:
    if not isinstance(observations, list) or not observations:
        raise ValueError("observations must be a nonempty JSON array")
    completed = []
    for item in observations:
        if not isinstance(item, dict) or not isinstance(item.get("checks"), list):
            raise ValueError("each observation must have a checks array")
        when = _timestamp(item.get("observedAt"))
        if previous is not None and when <= previous:
            raise ValueError("observation times must increase")
        checks = item["checks"]
        for check in checks:
            if (
                not isinstance(check, dict)
                or type(check.get("ok")) is not bool
                or type(check.get("required", True)) is not bool
            ):
                raise ValueError("check results must use boolean ok and required values")
        _, incident = apply_transition(state, determine_overall(checks), when)
        if incident is not None:
            completed.append(incident)
        previous = when
    return completed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", required=True, type=Path, help="saved observations JSON")
    parser.add_argument("--state", type=Path, help="optional state JSON file to persist")
    args = parser.parse_args()

    try:
        observations = _read_json(args.observations)
        state, previous = _load_state(args.state, args.observations)
        completed = _apply_observations(observations, state, previous)
        report = json.dumps({"state": state, "completedIncidents": completed}, indent=2, allow_nan=False)
        if args.state is not None:
            write_json_atomic(args.state, state)
    except (UnicodeDecodeError, json.JSONDecodeError, OverflowError, RecursionError):
        parser.exit(2, "error: invalid JSON input or timestamp\n")
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")
    except OSError:
        parser.exit(2, "error: could not read input or save state\n")

    print(report)


if __name__ == "__main__":
    main()
