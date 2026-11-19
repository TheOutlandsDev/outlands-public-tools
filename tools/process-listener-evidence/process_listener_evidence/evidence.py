"""Check process identity and listener ownership from saved evidence."""

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
import json
import math
import ntpath
from pathlib import Path
import posixpath
from typing import Any


MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_RECORDS = 10_000
MAX_OWNER_PIDS = 100_000
MAX_PID = (1 << 32) - 1
MAX_PATH_BYTES = 4_096
MAX_NAME_BYTES = 256
MAX_TIME_BYTES = 128
_PATH_STYLES = ("windows", "posix")


class EvidenceError(ValueError):
    """The evidence cannot be evaluated under the input contract."""


@dataclass(frozen=True)
class ProcessFact:
    pid: int
    ppid: int
    name: str
    executable: str | None
    created_utc: str | None


@dataclass(frozen=True)
class IdentityResult:
    state: str
    pids: tuple[int, ...]
    created_utc: str | None


def _bounded_text(value: object, label: str, limit: int) -> str:
    if isinstance(value, str) and 0 < len(value) <= limit and value.strip():
        if all(ord(character) >= 32 for character in value):
            try:
                if len(value.encode("utf-8")) <= limit:
                    return value
            except UnicodeEncodeError:
                pass
    raise EvidenceError(f"{label} must be bounded, nonblank UTF-8 text")


def _normalized_path(value: object, path_style: str) -> tuple[str, ...]:
    path = _bounded_text(value, "Executable path", MAX_PATH_BYTES)
    if path_style == "windows":
        path = path.replace("/", "\\")
        if path.startswith(("\\\\?\\", "\\\\.\\")):
            raise EvidenceError("Windows device paths are unsupported")
        drive, tail = ntpath.splitdrive(path)
        if drive.startswith("\\\\"):
            parts = drive[2:].split("\\")
            if len(parts) != 2 or any(part in ("", ".", "..") or ":" in part for part in parts):
                raise EvidenceError("An absolute Windows path is required")
        elif not (
            len(drive) == 2
            and drive[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            and drive[1] == ":"
            and tail.startswith("\\")
        ):
            raise EvidenceError("An absolute Windows path is required")
        if ":" in tail:
            raise EvidenceError("Windows path components cannot contain a colon")
        anchor = drive.lower()
        tail = tail.replace("\\", "/").lower()
    elif path_style == "posix":
        if not path.startswith("/"):
            raise EvidenceError("An absolute POSIX path is required")
        anchor = "/"
        tail = path
    else:
        raise EvidenceError("Unsupported path style")

    # Normalize only the path components, independently of the host filesystem.
    components = posixpath.normpath("/" + tail.lstrip("/")).split("/")[1:]
    return (anchor, *(part for part in components if part))


def _identity(
    processes: Iterable[ProcessFact],
    name: str,
    expected_path: str,
    path_style: str,
    *,
    rooted: bool,
) -> IdentityResult:
    expected = _normalized_path(expected_path, path_style)
    named = tuple(process for process in processes if process.name.casefold() == name.casefold())
    matches = []
    for process in named:
        if process.executable:
            observed = _normalized_path(process.executable, path_style)
            candidate = observed[:len(expected)] if rooted else observed
            if candidate == expected:
                matches.append(process)

    if len(matches) == 1:
        match = matches[0]
        return IdentityResult("proven", (match.pid,), match.created_utc)
    if matches:
        return IdentityResult("failed", tuple(match.pid for match in matches), None)
    if any(process.executable is None for process in named):
        return IdentityResult("unavailable", (), None)
    return IdentityResult("failed", (), None)


def exact_identity(
    processes: Iterable[ProcessFact],
    name: str,
    expected_executable: str,
    *,
    path_style: str,
) -> IdentityResult:
    """Check for one named process at the expected lexical executable path."""
    return _identity(processes, name, expected_executable, path_style, rooted=False)


def rooted_identity(
    processes: Iterable[ProcessFact],
    name: str,
    expected_root: str,
    *,
    path_style: str,
) -> IdentityResult:
    """Check for one named process at or below the expected lexical root."""
    return _identity(processes, name, expected_root, path_style, rooted=True)


def listener_state(
    owners: Mapping[tuple[str, int], set[int]],
    expected_pids: tuple[int, ...],
    specifications: tuple[tuple[str, int], ...],
) -> str:
    """Require every declared listener to have only expected owners."""
    if not expected_pids or not specifications:
        return "failed"
    expected = set(expected_pids)
    port_owners = [owners.get(specification, set()) for specification in specifications]
    if all(item and item.issubset(expected) for item in port_owners):
        return "proven"
    return "failed"


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be an object")
    return value


def _array(value: object, label: str, limit: int = MAX_RECORDS) -> list[Any]:
    if not isinstance(value, list) or len(value) > limit:
        raise EvidenceError(f"{label} must be a bounded array")
    return value


def _integer(value: object, label: str, lower: int, upper: int) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise EvidenceError(f"{label} must be an integer in range")
    return value


def _processes(rows: list[Any], path_style: str) -> list[ProcessFact]:
    processes = []
    seen = set()
    for value in rows:
        row = _object(value, "Process record")
        pid = _integer(row.get("pid"), "PID", 1, MAX_PID)
        if pid in seen:
            raise EvidenceError("Process PIDs must be unique")
        seen.add(pid)
        name = _bounded_text(row.get("name"), "Process name", MAX_NAME_BYTES)
        ppid = _integer(row.get("ppid", 0), "Parent PID", 0, MAX_PID)
        executable = row.get("executable")
        if executable is not None:
            _normalized_path(executable, path_style)
        timestamp = row.get("created_utc")
        if timestamp is not None:
            timestamp = _bounded_text(timestamp, "Creation time", MAX_TIME_BYTES)
        processes.append(ProcessFact(pid, ppid, name, executable, timestamp))
    return processes


def _listener(row: dict[str, Any]) -> tuple[str, int]:
    protocol = row.get("protocol")
    if protocol not in ("tcp", "udp"):
        raise EvidenceError("Listener protocol must be tcp or udp")
    port = _integer(row.get("port"), "Listener port", 1, 65_535)
    return protocol, port


def _declared_listeners(rows: list[Any]) -> tuple[tuple[str, int], ...]:
    listeners = tuple(_listener(_object(row, "Declared listener")) for row in rows)
    if len(listeners) != len(set(listeners)):
        raise EvidenceError("Declared listeners must be unique")
    return listeners


def _listener_owners(rows: list[Any]) -> dict[tuple[str, int], set[int]]:
    owners = {}
    remaining = MAX_OWNER_PIDS
    for value in rows:
        row = _object(value, "Listener ownership record")
        listener = _listener(row)
        if listener in owners:
            raise EvidenceError("Listener ownership records must be unique")
        values = _array(row.get("pids"), "Listener owner PIDs", remaining)
        remaining -= len(values)
        pids = {_integer(pid, "Listener owner PID", 1, MAX_PID) for pid in values}
        if len(pids) != len(values):
            raise EvidenceError("Listener owner PIDs must be unique")
        owners[listener] = pids
    return owners


def check_evidence(document: object) -> dict[str, Any]:
    """Return an allowlisted report about the supplied local facts."""
    data = _object(document, "Evidence")
    request = _object(data.get("identity"), "Identity request")
    mode = request.get("mode")
    if mode not in ("exact", "rooted"):
        raise EvidenceError("Identity mode must be exact or rooted")
    path_style = request.get("path_style")
    if path_style not in _PATH_STYLES:
        raise EvidenceError("Unsupported path style")
    name = _bounded_text(request.get("name"), "Identity name", MAX_NAME_BYTES)
    path = _bounded_text(request.get("path"), "Identity path", MAX_PATH_BYTES)
    processes = _processes(_array(data.get("processes"), "Processes"), path_style)
    specifications = _declared_listeners(_array(data.get("expected_listeners"), "Declared listeners"))
    owners = _listener_owners(_array(data.get("listener_owners"), "Listener ownership records"))

    check_identity = exact_identity if mode == "exact" else rooted_identity
    identity = check_identity(processes, name, path, path_style=path_style)
    pids = identity.pids if identity.state == "proven" else ()
    listeners = listener_state(owners, pids, specifications)
    status = listeners if identity.state == "proven" else identity.state
    return {"status": status, "identity": asdict(identity), "listener_state": listeners}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in pairs:
        if key in data:
            raise EvidenceError("JSON objects must have unique keys")
        data[key] = value
    return data


def _reject_constant(_value: str) -> Any:
    raise EvidenceError("JSON numbers must be finite")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise EvidenceError("JSON numbers must be finite")
    return number


def read_evidence(path: Path) -> Any:
    """Read one bounded UTF-8 JSON file."""
    if not path.is_file():
        raise EvidenceError("Input must be a regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise EvidenceError("Input exceeds its byte limit")
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except EvidenceError:
        raise
    except (ValueError, ArithmeticError, RecursionError):
        raise EvidenceError("Input must contain valid UTF-8 JSON") from None
