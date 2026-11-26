"""Verify and replay a saved game telemetry snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Mapping

from game_event_statistics import (
    ComputeBackend,
    ComputeContractError,
    MAX_INPUT_BYTES,
    _PROFILE_BY_ID,
    _canonical_json,
    _sha256,
)


TELEMETRY_SCHEMA_VERSION = 1

MAX_EVENTS_PER_EXPORT = 10_000

_RAW_FIELD_NAMES = {
    "chat",
    "command",
    "line",
    "message",
    "raw",
    "text",
}

_IPV4_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?!\d)")

_LONG_ID_RE = re.compile(r"(?<!\d)\d{12,20}(?!\d)")

_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization)\b"
)


class TelemetryExportError(ValueError):
    """Raised when a source, destination, or snapshot violates the contract."""


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    if snapshot.get("schema_version") != TELEMETRY_SCHEMA_VERSION:
        raise TelemetryExportError("Unsupported telemetry snapshot schema.")
    program = snapshot.get("program")
    if not isinstance(program, str) or program not in _PROFILE_BY_ID:
        raise TelemetryExportError("Unsupported telemetry program.")
    records = snapshot.get("records")
    if not isinstance(records, list) or len(records) > MAX_EVENTS_PER_EXPORT:
        raise TelemetryExportError("Invalid telemetry record array.")
    claimed = snapshot.get("snapshot_sha256")
    body = dict(snapshot)
    body.pop("snapshot_sha256", None)
    if not isinstance(claimed, str) or claimed != _sha256(body):
        raise TelemetryExportError("Telemetry snapshot hash validation failed.")
    for record in records:
        if not isinstance(record, Mapping):
            raise TelemetryExportError("Telemetry records must be JSON objects.")
        if _RAW_FIELD_NAMES.intersection(record):
            raise TelemetryExportError("Telemetry record contains a prohibited raw field.")
        for identity_field in ("actor", "target"):
            value = record.get(identity_field)
            if value is not None and not re.fullmatch(r"actor_[0-9a-f]{16}", str(value)):
                raise TelemetryExportError(
                    f"Telemetry {identity_field} is not pseudonymized."
                )
        non_identity_fields = {
            key: value
            for key, value in record.items()
            if key not in {"actor", "target", "source_file"}
        }
        encoded_record = _canonical_json(non_identity_fields).decode("utf-8")
        if _IPV4_RE.search(encoded_record) or _LONG_ID_RE.search(encoded_record):
            raise TelemetryExportError("Telemetry record contains a network or platform ID.")
        if _SECRET_RE.search(encoded_record):
            raise TelemetryExportError("Telemetry record contains a secret-like field.")


def replay_snapshot(
    snapshot: Mapping[str, Any],
    *,
    backend: ComputeBackend | None = None,
) -> dict[str, Any]:
    """Run a sanitized snapshot through deterministic compute functions."""

    validate_snapshot(snapshot)
    compute = backend or ComputeBackend()
    program = str(snapshot["program"])
    records = list(snapshot["records"])
    try:
        normalized = compute.execute(program, "normalize_events", {"records": records})
        features = compute.execute(
            program,
            "build_behavior_features",
            {"records": records},
        )
        manifest = compute.execute(
            program,
            "build_training_manifest",
            {
                "dataset_name": f"{program}-sanitized-replay",
                "records": records,
            },
        )
    except ComputeContractError as exc:
        raise TelemetryExportError(str(exc)) from exc
    return {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "program": program,
        "source_snapshot_sha256": snapshot["snapshot_sha256"],
        "record_count": len(records),
        "normalized": normalized,
        "features": features,
        "training_manifest": manifest,
        "runtime": {
            "model_used": False,
            "gpu_used": False,
            "network_used": False,
            "subprocess_used": False,
            "server_action_performed": False,
            "write_performed": False,
        },
    }


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field.")
        result[key] = value
    return result


def _read_snapshot(path: Path) -> Mapping[str, Any]:
    try:
        if not path.is_file():
            raise OSError
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise TelemetryExportError("Unable to read the telemetry snapshot.") from None
    if len(raw) > MAX_INPUT_BYTES:
        raise TelemetryExportError("The telemetry input exceeds 2,000,000 bytes.")
    try:
        snapshot = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        raise TelemetryExportError("Invalid telemetry JSON.") from None
    if not isinstance(snapshot, dict):
        raise TelemetryExportError("The telemetry snapshot must be an object.")
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "replay"))
    parser.add_argument("input", type=Path, help="Saved game telemetry snapshot")
    args = parser.parse_args()
    try:
        snapshot = _read_snapshot(args.input)
        if args.mode == "verify":
            validate_snapshot(snapshot)
            report = {
                "ok": True,
                "program": snapshot["program"],
                "record_count": len(snapshot["records"]),
                "snapshot_sha256": snapshot["snapshot_sha256"],
            }
        else:
            report = replay_snapshot(snapshot)
            for name in ("normalized", "features", "training_manifest"):
                report[name].pop("generated_utc")
        output = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    except TelemetryExportError as error:
        parser.exit(2, f"{error}\n")
    except (ValueError, OverflowError, RecursionError):
        parser.exit(2, "Telemetry contains invalid numeric or text data.\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
