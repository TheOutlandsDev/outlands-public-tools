"""Preview a dashboard recovery decision from a saved telemetry collection failure."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


MAX_INPUT_BYTES = 1024 * 1024
ERROR_TYPES = {
    error_type.__name__: error_type
    for error_type in (Exception, OSError, RuntimeError, TimeoutError, ValueError)
}


def _format_collection_error(error: Exception) -> str:
    message = " ".join(str(error).split())
    if "timed out" in message.casefold():
        return "Windows health inventory timed out"
    if not message:
        return type(error).__name__
    if len(message) > 160:
        return f"{type(error).__name__}: {message[:130]}..."
    return message


@dataclass(frozen=True)
class RecoveryPreview:
    last_snapshot: dict[str, Any] | None
    last_sample: str
    severity: str
    status_text: str
    retry_delay_ms: int | None


def preview_refresh_recovery(
    error: Exception,
    last_snapshot: dict[str, Any] | None,
    *,
    refresh_seconds: int = 30,
    closed: bool = False,
) -> RecoveryPreview:
    """Apply the dashboard's refresh interval, failure status and timer rules."""
    configured_interval = max(10, min(refresh_seconds, 300))
    retry_seconds = min(10, configured_interval)
    last_sample = str(last_snapshot.get("generated", "unknown")) if last_snapshot is not None else "unavailable"
    status_text = (
        f"REFRESH DELAYED - {_format_collection_error(error)} - "
        f"showing last sample {last_sample} - retrying in {retry_seconds}s"
    )
    return RecoveryPreview(
        last_snapshot=last_snapshot,
        last_sample=last_sample,
        severity="warning" if last_snapshot is not None else "critical",
        status_text=status_text,
        retry_delay_ms=None if closed else max(1, int(retry_seconds)) * 1000,
    )


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-JSON constant")


def read_failure(path: Path) -> RecoveryPreview:
    try:
        if not path.is_file():
            raise OSError
        with path.open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise ValueError("Unable to read the saved refresh failure.") from None
    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError("The saved refresh failure exceeds the 1 MiB limit.")

    try:
        data = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
    except (ValueError, RecursionError):
        raise ValueError("Invalid saved refresh failure JSON.") from None

    if not isinstance(data, dict) or data.keys() - {"error", "last_snapshot", "refresh_seconds", "closed"}:
        raise ValueError("Invalid saved refresh failure fields.")
    error = data.get("error")
    if (not isinstance(error, dict) or error.keys() != {"type", "message"}
            or not isinstance(error["type"], str) or error["type"] not in ERROR_TYPES
            or not isinstance(error["message"], str)):
        raise ValueError("Invalid saved collection error.")
    snapshot = data.get("last_snapshot")
    if snapshot is not None and (
        not isinstance(snapshot, dict) or not isinstance(snapshot.get("generated", ""), str)
    ):
        raise ValueError("Invalid last snapshot.")
    refresh_seconds = data.get("refresh_seconds", 30)
    closed = data.get("closed", False)
    if type(refresh_seconds) is not int or type(closed) is not bool:
        raise ValueError("Invalid refresh interval or closed state.")
    return preview_refresh_recovery(ERROR_TYPES[error["type"]](error["message"]), snapshot,
                                    refresh_seconds=refresh_seconds, closed=closed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("failure", type=Path, help="Saved collection error and optional previous snapshot")
    args = parser.parse_args()
    try:
        preview = read_failure(args.failure)
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps({
        "last_sample": preview.last_sample,
        "last_sample_available": preview.last_snapshot is not None,
        "retry_delay_ms": preview.retry_delay_ms,
        "severity": preview.severity,
        "status_text": preview.status_text,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
