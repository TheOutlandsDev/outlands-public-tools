"""Assess explicitly supplied observations using the OpsKit doctor rules."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Any


MAX_OBSERVATION_BYTES = 16 * 1024
MAX_RECORDED_BYTES = 2**63 - 1
MIB = 1024**2
GIB = 1024**3
REQUIRED_FIELDS = frozenset({
    "os",
    "python_version",
    "workspace",
    "disk_total_bytes",
    "disk_free_bytes",
    "memory_total_bytes",
    "memory_available_bytes",
    "temporary_directory_writable",
    "hostname_resolution",
})
OS_LABELS = {"windows": "Windows", "linux": "Linux", "other": "Other"}
WORKSPACE_CHECKS = {
    "writable": ("pass", "OpsKit home is accessible and writable."),
    "read_only": ("warn", "OpsKit home is accessible but appears read-only."),
    "missing": ("fail", "OpsKit home does not exist."),
    "not_directory": ("fail", "OpsKit home is not a directory."),
}
VERSION_PATTERN = re.compile(r"(?:0|[1-9][0-9]{0,3})(?:\.(?:0|[1-9][0-9]{0,3})){2}")


class ObservationError(ValueError):
    """An expected failure that can be reported without echoing input."""


def _is_regular(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ObservationError("Duplicate JSON field in the observation file.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ObservationError("Non-finite JSON value in the observation file.")


def read_observations(path: Path) -> object:
    try:
        before = path.lstat()
        if not _is_regular(before):
            raise ObservationError("Observations must be in an ordinary file.")
        if before.st_size > MAX_OBSERVATION_BYTES:
            raise ObservationError("Observation file exceeds the 16 KiB limit.")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _is_regular(opened) or not os.path.samestat(before, opened):
                raise ObservationError("Observation file changed while opening.")
            raw = stream.read(MAX_OBSERVATION_BYTES + 1)
    except (OSError, ValueError) as exc:
        if isinstance(exc, ObservationError):
            raise
        raise ObservationError("Unable to read the observation file.") from None
    if len(raw) > MAX_OBSERVATION_BYTES:
        raise ObservationError("Observation file exceeds the 16 KiB limit.")
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=_object_pairs, parse_constant=_reject_constant
        )
    except ObservationError:
        raise
    except (ValueError, RecursionError):
        raise ObservationError("Observation file must contain valid UTF-8 JSON.") from None


def _check(name: str, status: str, message: str, **details: Any) -> dict[str, Any]:
    return {"name": name, "status": status, "message": message, "details": details}


def _byte_counts(total: object, measured: object, label: str) -> tuple[int, int] | None:
    if total is None and measured is None:
        return None
    if type(total) is not int or type(measured) is not int or not 0 <= measured <= total <= MAX_RECORDED_BYTES:
        raise ObservationError(f"Invalid {label} byte counts.")
    return total, measured


def _optional_bool(value: object, label: str) -> bool | None:
    if value is not None and type(value) is not bool:
        raise ObservationError(f"Invalid {label} observation.")
    return value


def _percentage(total: int, measured: int) -> float:
    return (measured / total) * 100 if total else 0.0


def _bytes_human(value: int) -> str:
    amount = float(value)
    for suffix in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024.0 or suffix == "TiB":
            return f"{amount:.1f} {suffix}"
        amount /= 1024.0
    raise AssertionError("Storage unit sequence is incomplete.")


def doctor(observations: object) -> tuple[dict[str, Any], list[str]]:
    """Return the original check outcomes for a validated saved snapshot."""
    if not isinstance(observations, dict) or observations.keys() != REQUIRED_FIELDS:
        raise ObservationError("Observation JSON must contain exactly the documented fields.")
    system_name = observations["os"]
    if not isinstance(system_name, str) or system_name not in OS_LABELS:
        raise ObservationError("Invalid operating system observation.")
    version_text = observations["python_version"]
    if not isinstance(version_text, str) or VERSION_PATTERN.fullmatch(version_text) is None:
        raise ObservationError("Invalid Python version observation.")
    workspace = observations["workspace"]
    if not isinstance(workspace, str) or workspace not in WORKSPACE_CHECKS:
        raise ObservationError("Invalid workspace observation.")
    disk = _byte_counts(observations["disk_total_bytes"], observations["disk_free_bytes"], "disk")
    memory = _byte_counts(
        observations["memory_total_bytes"], observations["memory_available_bytes"], "memory"
    )
    temp = _optional_bool(observations["temporary_directory_writable"], "temporary directory")
    resolved = _optional_bool(observations["hostname_resolution"], "hostname resolution")

    warnings: list[str] = []
    checks: list[dict[str, Any]] = []
    if system_name in {"windows", "linux"}:
        checks.append(_check("supported_os", "pass", f"{OS_LABELS[system_name]} is supported."))
    else:
        checks.append(_check("supported_os", "warn", "The reported OS has not been validated."))

    version = tuple(int(component) for component in version_text.split("."))
    if version >= (3, 12):
        checks.append(_check("python", "pass", f"Python {version_text} meets the 3.12+ requirement."))
    else:
        checks.append(_check("python", "fail", f"Python {version_text} is older than 3.12."))

    workspace_status, workspace_message = WORKSPACE_CHECKS[workspace]
    checks.append(_check("opskit_home", workspace_status, workspace_message))
    if workspace in {"writable", "read_only"}:
        if disk is None:
            checks.append(_check("disk_space", "fail", "Disk space was unavailable."))
        else:
            total, free = disk
            free_percent = _percentage(total, free)
            if free < 2 * GIB:
                status = "fail"
            elif free * 10 < total or free < 5 * GIB:
                status = "warn"
            else:
                status = "pass"
            checks.append(_check(
                "disk_space",
                status,
                f"{_bytes_human(free)} free ({free_percent:.1f}%).",
                total_bytes=total,
                free_bytes=free,
                free_percent=round(free_percent, 1),
            ))

    if memory is None:
        checks.append(_check("memory", "warn", "Memory availability could not be determined."))
    else:
        total, available = memory
        percent = _percentage(total, available)
        if available < 256 * MIB:
            status = "fail"
        elif available * 10 < total:
            status = "warn"
        else:
            status = "pass"
        checks.append(_check(
            "memory",
            status,
            f"{_bytes_human(available)} available ({percent:.1f}%).",
            total_bytes=total,
            available_bytes=available,
            available_percent=round(percent, 1),
        ))

    if temp is True:
        checks.append(_check("temporary_directory", "pass", "Temporary directory was writable."))
    elif temp is False:
        checks.append(_check("temporary_directory", "warn", "Temporary directory was unavailable or read-only."))
    else:
        checks.append(_check("temporary_directory", "warn", "Temporary directory access was unknown."))

    if resolved is True:
        checks.append(_check("hostname_resolution", "pass", "Hostname resolution was reported successful."))
    elif resolved is False:
        checks.append(_check("hostname_resolution", "warn", "Hostname resolution was reported unsuccessful."))
    else:
        message = "Hostname resolution status could not be determined."
        warnings.append(message)
        checks.append(_check("hostname_resolution", "warn", message))

    counts = {
        status: sum(item["status"] == status for item in checks)
        for status in ("pass", "warn", "fail")
    }
    overall = "fail" if counts["fail"] else "warn" if counts["warn"] else "pass"
    return {
        "status": overall,
        "summary": counts,
        "checks": checks,
        "read_only": True,
        "duration_hint": "point-in-time",
    }, warnings
