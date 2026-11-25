"""Replay saved telemetry incident observations in a fresh temporary SQLite database."""

import argparse
from datetime import UTC, datetime
import json
from math import isfinite
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory

from incident_store.models import IncidentCandidate
from incident_store.storage import CacStorage


MAX_INPUT_BYTES = 1024 * 1024
MAX_STEPS = 100
MAX_INCIDENTS = 100
IDENTITY = re.compile(r"[0-9a-f]{64}")
CANDIDATE_FIELDS = {"source", "code", "severity", "summary", "evidence"}


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


def read_recording(path):
    try:
        if not path.is_file():
            raise OSError
        with path.open("rb") as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise ValueError("Unable to read the telemetry recording.") from None
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("The telemetry recording exceeds the 1 MiB limit.")
    try:
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant, parse_float=finite_float)
    except (ValueError, RecursionError):
        raise ValueError("Invalid telemetry recording JSON.") from None


def observation(step):
    snapshot = step["snapshot"]
    rows = step["incidents"]
    if (not isinstance(snapshot, dict) or not isinstance(snapshot.get("generated"), str)
            or not isinstance(snapshot.get("overall_status"), str) or not isinstance(rows, list)):
        raise ValueError("Invalid saved observation.")
    try:
        stamp = datetime.fromisoformat(snapshot["generated"])
        if stamp.utcoffset() is None:
            raise ValueError
        stamp = stamp.astimezone(UTC)
    except (ValueError, OverflowError):
        raise ValueError("Invalid observation timestamp. Include an offset.") from None

    candidates = []
    for row in rows:
        if (not isinstance(row, dict) or row.keys() != CANDIDATE_FIELDS
                or not isinstance(row["evidence"], dict)
                or any(not isinstance(row[name], str) or not row[name]
                       for name in CANDIDATE_FIELDS - {"evidence"})):
            raise ValueError("Invalid incident candidate.")
        candidates.append(IncidentCandidate(**row))
    return stamp, {**snapshot, "generated": stamp.isoformat()}, candidates


def replay(recording):
    if not isinstance(recording, dict) or recording.keys() != {"clean_samples", "steps"}:
        raise ValueError("Invalid telemetry recording fields.")
    clean_samples = recording["clean_samples"]
    steps = recording["steps"]
    if (type(clean_samples) is not int or not 1 <= clean_samples <= MAX_STEPS
            or not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS):
        raise ValueError("Invalid clean-sample threshold or step count.")

    last_time = None

    def recorded_clock():
        if last_time is None:
            raise ValueError("Replay requires a snapshot before operator actions.")
        return last_time

    history = []
    seen = set()
    with TemporaryDirectory(prefix="telemetry-incident-replay-") as temp:
        store = CacStorage(Path(temp) / "replay.sqlite", clean_samples=clean_samples,
                           retention_days=7, clock=recorded_clock)
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                raise ValueError("Invalid replay step.")
            action = step.get("action")
            entry = {"step": index, "action": action}
            if action == "snapshot" and step.keys() == {"action", "snapshot", "incidents"}:
                stamp, snapshot, candidates = observation(step)
                if last_time is not None and stamp <= last_time:
                    raise ValueError("Observation times must strictly increase.")
                fingerprints = {item.fingerprint for item in candidates}
                if len(fingerprints) != len(candidates):
                    raise ValueError("Duplicate incident fingerprint in a snapshot.")
                seen.update(fingerprints)
                if len(seen) > MAX_INCIDENTS:
                    raise ValueError("The replay exceeds 100 distinct incident fingerprints.")
                last_time = stamp
                store.save_snapshot(snapshot, candidates)
                entry["generated"] = snapshot["generated"]
            elif action == "acknowledge" and step.keys() == {"action", "fingerprint"}:
                fingerprint = step["fingerprint"]
                if not isinstance(fingerprint, str) or not IDENTITY.fullmatch(fingerprint):
                    raise ValueError("Invalid acknowledgement fingerprint.")
                entry["acknowledged"] = store.acknowledge_incident(fingerprint, actor="offline-replay")
            elif action == "clear_resolved" and step.keys() == {"action"}:
                entry["cleared"] = store.clear_resolved_incidents(actor="offline-replay")
            else:
                raise ValueError("Invalid replay step.")

            incidents = sorted(store.incidents(), key=lambda item: item["fingerprint"])
            entry["incidents"] = [
                {
                    "fingerprint": item["fingerprint"],
                    "state": item["state"],
                    "clean_count": item["clean_count"],
                    "acknowledged": item["acknowledged_at"] is not None,
                }
                for item in incidents
            ]
            history.append(entry)

        latest = store.latest_snapshot()
        return {
            "latest_generated": latest["generated"],
            "integrity_check": store.integrity_check(),
            "steps": history,
            "final_incidents": incidents,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path, help="Saved telemetry observations and operator actions")
    args = parser.parse_args()
    try:
        report = replay(read_recording(args.recording))
        output = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    except (UnicodeError, RecursionError):
        parser.exit(2, "Invalid telemetry text or nesting.\n")
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")
    except (OSError, sqlite3.Error):
        parser.exit(2, "Unable to complete the temporary SQLite replay.\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
