"""Create checksummed event snapshots from saved game logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Callable, Mapping, Sequence


TELEMETRY_SCHEMA_VERSION = 1
MAX_SOURCE_FILES = 3
MAX_TAIL_BYTES = 512 * 1024
MAX_EVENTS_PER_EXPORT = 10_000
MAX_SNAPSHOT_BYTES = 2_000_000

_ALLOWED_SUFFIXES = {".log", ".rpt", ".txt"}
_DENIED_NAME_PARTS = {
    ".env",
    "authorization",
    "certificate",
    "credential",
    "database",
    "password",
    "private",
    "secret",
    "sqlite",
    "token",
}
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


@dataclass(frozen=True, slots=True)
class TelemetrySourceProfile:
    id: str
    name: str
    root: Path
    patterns: tuple[str, ...]
    notes: str = ""


PROGRAM_NAMES = {
    "rust": "Rust",
    "dayz": "DayZ",
    "main_spt": "SPT",
    "modern_warfare": "Modern Warfare / IW4x",
    "zomboid": "Project Zomboid",
}

_PROGRAM_ALIASES = {
    "rustserver": "rust",
    "fika": "main_spt",
    "mainsp": "main_spt",
    "spt": "main_spt",
    "tarkov": "main_spt",
    "iw4x": "modern_warfare",
    "mw": "modern_warfare",
    "mw2": "modern_warfare",
    "project_zomboid": "zomboid",
    "pz": "zomboid",
}


class TelemetryExportError(ValueError):
    """Raised when a source, destination, or snapshot violates the contract."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _snapshot_bytes(snapshot: Mapping[str, Any]) -> bytes:
    data = _canonical_json(snapshot) + b"\n"
    if len(data) > MAX_SNAPSHOT_BYTES:
        raise TelemetryExportError("Snapshot exceeds 2,000,000 bytes; select fewer source logs.")
    return data


def _is_link(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _through_link(path: Path, root: Path) -> bool:
    return _is_link(path) or any(
        _is_link(parent) for parent in path.parents if parent != root and parent.is_relative_to(root)
    )


def _actor_token(program: str, value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().strip("\"'[](){} ")
    if not cleaned:
        return None
    digest = hashlib.sha256(
        f"cac-telemetry-v1\0{program}\0{cleaned}".encode("utf-8")
    ).hexdigest()[:16]
    return f"actor_{digest}"


def _numeric(value: str | int | float | None) -> int | float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return int(number) if number.is_integer() else number


def _record(
    program: str,
    event: str,
    *,
    actor: str | None = None,
    target: str | None = None,
    value: str | int | float | None = None,
    context: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "event": event,
        "actor": _actor_token(program, actor),
        "target": _actor_token(program, target),
        "value": _numeric(value),
    }
    safe_context: dict[str, str] = {}
    for key, raw_value in (context or {}).items():
        if key not in {"damage_type", "hit_location", "mode", "team", "weapon"}:
            continue
        cleaned = str(raw_value).strip()[:80]
        if (
            cleaned
            and not _IPV4_RE.search(cleaned)
            and not _LONG_ID_RE.search(cleaned)
            and not _SECRET_RE.search(cleaned)
        ):
            safe_context[key] = cleaned
    if safe_context:
        item["context"] = safe_context
    return item


def _rust_event(line: str) -> dict[str, Any] | None:
    if re.search(r"(?i)\[(?:chat|global|team)\]", line):
        return None
    match = re.search(
        r"(?P<actor>.+?)\[(?:\d+)\]\s+has (?:entered the game|connected)\b",
        line,
        re.IGNORECASE,
    )
    if match:
        return _record("rust", "player_join", actor=match.group("actor"))
    match = re.search(
        r"(?P<actor>.+?)\[(?:\d+)\]\s+has (?:left the game|disconnected)\b",
        line,
        re.IGNORECASE,
    )
    if match:
        return _record("rust", "player_leave", actor=match.group("actor"))
    match = re.search(
        r"(?P<actor>.+?)\[(?:\d+)\]\s+has spawned\b",
        line,
        re.IGNORECASE,
    )
    if match:
        return _record("rust", "spawn", actor=match.group("actor"))
    match = re.search(
        r"(?P<target>.+?)\[(?:\d+)\]\s+was killed by "
        r"(?P<actor>.+?)(?:\[(?:\d+)\]|\s+\(entity\)|\s+at\s|\s*$)",
        line,
        re.IGNORECASE,
    )
    if match:
        return _record(
            "rust",
            "kill",
            actor=match.group("actor"),
            target=match.group("target"),
        )
    if re.search(r"(?i)\b(exception|plugin error|compile error)\b", line):
        return _record("rust", "error")
    return None


def _dayz_event(line: str) -> dict[str, Any] | None:
    match = re.search(
        r'Player\s+"(?P<actor>[^"]+)"[^\r\n]*\b(?:is connected|connected)\b',
        line,
        re.IGNORECASE,
    )
    if match:
        return _record("dayz", "player_join", actor=match.group("actor"))
    match = re.search(
        r'Player\s+"(?P<actor>[^"]+)"[^\r\n]*\b(?:disconnected|is disconnected)\b',
        line,
        re.IGNORECASE,
    )
    if match:
        return _record("dayz", "player_leave", actor=match.group("actor"))
    match = re.search(
        r'Player\s+"(?P<target>[^"]+)"\s+(?:was )?killed by '
        r'(?:Player\s+)?"(?P<actor>[^"]+)"',
        line,
        re.IGNORECASE,
    )
    if match:
        return _record(
            "dayz",
            "kill",
            actor=match.group("actor"),
            target=match.group("target"),
        )
    if re.search(
        r"(?i)(?:\bSCRIPT\s+\(E\)|\bPHYSICS\s+\(E\)|causing search overtime|exception)",
        line,
    ):
        return _record("dayz", "error")
    return None


def _main_spt_event(line: str) -> dict[str, Any] | None:
    if re.search(r"(?i)/client/game/keepalive|request|response body", line):
        return None
    match = re.search(
        r"(?i)(?:player|client)\s+[\"']?(?P<actor>[A-Za-z0-9_. -]{2,50})"
        r"[\"']?\s+(?:connected|joined)\b",
        line,
    )
    if match:
        return _record("main_spt", "player_join", actor=match.group("actor"))
    match = re.search(
        r"(?i)(?:player|client)\s+[\"']?(?P<actor>[A-Za-z0-9_. -]{2,50})"
        r"[\"']?\s+(?:disconnected|left)\b",
        line,
    )
    if match:
        return _record("main_spt", "player_leave", actor=match.group("actor"))
    match = re.search(
        r"(?i)raid\s+(?:started|begin)[^\r\n]*?(?:for|player)\s+"
        r"[\"']?(?P<actor>[A-Za-z0-9_. -]{2,50})",
        line,
    )
    if match:
        return _record("main_spt", "raid_start", actor=match.group("actor"))
    match = re.search(
        r"(?i)(?P<actor>[A-Za-z0-9_. -]{2,50})\s+"
        r"(?:extracted|exfiltrated)\b",
        line,
    )
    if match:
        return _record("main_spt", "extract", actor=match.group("actor"))
    match = re.search(
        r"(?i)(?P<actor>[A-Za-z0-9_. -]{2,50})\s+killed\s+"
        r"(?P<target>[A-Za-z0-9_. -]{2,50})",
        line,
    )
    if match:
        return _record(
            "main_spt",
            "kill",
            actor=match.group("actor"),
            target=match.group("target"),
        )
    if re.search(r"(?i)\b(exception|fatal|backend error)\b", line):
        return _record("main_spt", "error")
    return None


def _iw4x_event(line: str) -> dict[str, Any] | None:
    structured = re.search(r"(?:^|\s)(?P<kind>[JKQD]);(?P<body>.+)$", line)
    if structured:
        kind = structured.group("kind")
        fields = structured.group("body").split(";")
        if kind in {"J", "Q"} and len(fields) >= 3:
            return _record(
                "modern_warfare",
                "player_join" if kind == "J" else "player_leave",
                actor=fields[2],
            )
        if kind in {"K", "D"} and len(fields) >= 9:
            context = {
                "team": fields[2],
                "weapon": fields[8] if len(fields) > 8 else "",
                "damage_type": fields[10] if len(fields) > 10 else "",
                "hit_location": fields[11] if len(fields) > 11 else "",
            }
            return _record(
                "modern_warfare",
                "kill" if kind == "K" else "damage",
                actor=fields[3],
                target=fields[7],
                value=fields[9] if kind == "D" and len(fields) > 9 else None,
                context=context,
            )
    if re.search(r"(?i)\b(script compile error|fatal error|unhandled exception)\b", line):
        return _record("modern_warfare", "error")
    return None


def _zomboid_event(line: str) -> dict[str, Any] | None:
    match = re.search(
        r'(?i)(?:user|player)\s+"?(?P<actor>[A-Za-z0-9_. -]{2,50})"?'
        r"\s+(?:connected|joined)\b",
        line,
    )
    if match:
        return _record("zomboid", "player_join", actor=match.group("actor"))
    match = re.search(
        r'(?i)(?:user|player)\s+"?(?P<actor>[A-Za-z0-9_. -]{2,50})"?'
        r"\s+(?:disconnected|left)\b",
        line,
    )
    if match:
        return _record("zomboid", "player_leave", actor=match.group("actor"))
    match = re.search(
        r'(?i)(?:player\s+)?"?(?P<actor>[A-Za-z0-9_. -]{2,50})"?\s+died\b',
        line,
    )
    if match:
        return _record("zomboid", "death", actor=match.group("actor"))
    match = re.search(
        r'(?i)zombie[^\r\n]*\bkilled by\s+"?'
        r"(?P<actor>[A-Za-z0-9_. -]{2,50})",
        line,
    )
    if match:
        return _record("zomboid", "kill", actor=match.group("actor"))
    if re.search(r"(?i)\b(lua error|fatal error|unhandled exception)\b", line):
        return _record("zomboid", "error")
    return None


_PARSER_BY_PROGRAM: Mapping[str, Callable[[str], dict[str, Any] | None]] = {
    "rust": _rust_event,
    "dayz": _dayz_event,
    "main_spt": _main_spt_event,
    "modern_warfare": _iw4x_event,
    "zomboid": _zomboid_event,
}


class TelemetryExporter:
    """Read bounded allowlisted tails and write only sanitized CAC snapshots."""

    def __init__(
        self,
        profiles: Sequence[TelemetrySourceProfile],
        *,
        output_root: Path | None = None,
        now: Callable[[], datetime] | None = None,
        max_source_files: int = MAX_SOURCE_FILES,
        max_tail_bytes: int = MAX_TAIL_BYTES,
    ) -> None:
        self.profiles = tuple(profiles)
        self.output_root = output_root
        self._now = now or (lambda: datetime.now(UTC))
        self.max_source_files = max(1, min(max_source_files, 10))
        self.max_tail_bytes = max(4_096, min(max_tail_bytes, MAX_TAIL_BYTES))

    def _profile(self, program: str) -> TelemetrySourceProfile:
        key = re.sub(r"[^a-z0-9]+", "_", program.casefold()).strip("_")
        normalized = _PROGRAM_ALIASES.get(key, key)
        for profile in self.profiles:
            if profile.id == normalized:
                return profile
        raise TelemetryExportError("No telemetry source profile for the requested program.")

    @staticmethod
    def _validate_profile(profile: TelemetrySourceProfile) -> None:
        if profile.id not in _PARSER_BY_PROGRAM:
            raise TelemetryExportError("No parser registered for the requested program.")
        for pattern in profile.patterns:
            windows = PureWindowsPath(pattern)
            posix = PurePosixPath(pattern)
            if (
                not pattern or "\x00" in pattern or ":" in pattern
                or windows.anchor or posix.anchor
                or ".." in windows.parts or ".." in posix.parts
            ):
                raise TelemetryExportError("Unsafe source pattern.")

    def discover(self, program: str) -> list[Path]:
        profile = self._profile(program)
        self._validate_profile(profile)
        if _is_link(profile.root):
            raise TelemetryExportError("Source root may not be a symlink or junction.")
        root = profile.root.resolve(strict=True)
        if not root.is_dir():
            raise TelemetryExportError("Source root must be a directory.")
        candidates: set[Path] = set()
        for pattern in profile.patterns:
            for path in root.glob(pattern.replace("\\", "/")):
                try:
                    if _through_link(path, root):
                        continue
                    resolved = path.resolve(strict=True)
                except (FileNotFoundError, OSError):
                    continue
                lowered = resolved.name.casefold()
                if (
                    not resolved.is_file()
                    or not _is_within(resolved, root)
                    or resolved.suffix.casefold() not in _ALLOWED_SUFFIXES
                    or any(part in lowered for part in _DENIED_NAME_PARTS)
                ):
                    continue
                candidates.add(resolved)
        return sorted(
            candidates,
            key=lambda path: (-path.stat().st_mtime_ns, path.relative_to(root).as_posix()),
        )[: self.max_source_files]

    def _tail(self, path: Path) -> tuple[list[str], str]:
        before = path.stat()
        with path.open("rb") as handle:
            start = max(0, before.st_size - self.max_tail_bytes)
            handle.seek(start)
            raw = handle.read(self.max_tail_bytes)
        after = path.stat()
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise TelemetryExportError(
                "Source changed during bounded read; retry with a saved copy."
            )
        if start:
            first_newline = raw.find(b"\n")
            raw = raw[first_newline + 1 :] if first_newline >= 0 else b""
        return raw.decode("utf-8", errors="replace").splitlines(), hashlib.sha256(
            raw
        ).hexdigest()

    def collect(self, program: str) -> dict[str, Any]:
        profile = self._profile(program)
        source_files = self.discover(profile.id)
        parser = _PARSER_BY_PROGRAM[profile.id]
        records: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []

        for index, source in enumerate(source_files, 1):
            source_label = f"log-{index:03d}{source.suffix.lower()}"
            lines, tail_sha256 = self._tail(source)
            source_events = 0
            for line in lines:
                if len(records) >= MAX_EVENTS_PER_EXPORT:
                    break
                parsed = parser(line)
                if parsed is None:
                    continue
                parsed["source_file"] = source_label
                records.append(parsed)
                source_events += 1
            stat = source.stat()
            sources.append(
                {
                    "path": source_label,
                    "size_bytes": stat.st_size,
                    "last_write_utc": datetime.fromtimestamp(
                        stat.st_mtime, UTC
                    ).isoformat(),
                    "tail_sha256": tail_sha256,
                    "parsed_event_count": source_events,
                }
            )

        generated = self._now().astimezone(UTC)
        body: dict[str, Any] = {
            "schema_version": TELEMETRY_SCHEMA_VERSION,
            "generated_utc": generated.isoformat(),
            "program": profile.id,
            "program_name": profile.name,
            "source_read_only": True,
            "source_file_count": len(sources),
            "record_count": len(records),
            "sources": sources,
            "records": records,
            "privacy": {
                "raw_lines_retained": False,
                "chat_retained": False,
                "player_names_retained": False,
                "platform_ids_retained": False,
                "ip_addresses_retained": False,
                "credentials_retained": False,
                "actors_pseudonymized": True,
            },
            "runtime": {
                "model_used": False,
                "gpu_used": False,
                "network_used": False,
                "subprocess_used": False,
                "server_action_performed": False,
            },
        }
        body["snapshot_sha256"] = _sha256(body)
        validate_snapshot(body)
        return body

    def export(self, program: str) -> dict[str, Any]:
        if self.output_root is None:
            raise TelemetryExportError("An output root is required to write a snapshot.")
        profile = self._profile(program)
        source_root = profile.root.resolve(strict=True)
        output_root = self.output_root.resolve(strict=False)
        program_root = output_root / profile.id
        if (
            _is_link(self.output_root) or _is_link(program_root)
            or not _is_within(program_root.resolve(strict=False), output_root)
            or _is_within(program_root.resolve(strict=False), source_root)
        ):
            raise TelemetryExportError("Snapshot destination must be outside the source tree and free of links.")
        snapshot = self.collect(program)
        data = _snapshot_bytes(snapshot)
        program_root.mkdir(parents=True, exist_ok=True)
        stamp = (
            datetime.fromisoformat(snapshot["generated_utc"])
            .astimezone(UTC)
            .strftime("%Y%m%dT%H%M%SZ")
        )
        destination = (
            program_root / f"{snapshot['program']}-{stamp}-{snapshot['snapshot_sha256'][:12]}.json"
        )
        with tempfile.NamedTemporaryFile(dir=program_root, prefix=".snapshot-", delete=False) as handle:
            temporary = Path(handle.name)
            try:
                handle.write(data)
                handle.close()
                os.link(temporary, destination)
            except FileExistsError:
                raise TelemetryExportError("Snapshot destination already exists.") from None
            finally:
                handle.close()
                temporary.unlink()
        return {
            "path": str(destination),
            "snapshot_sha256": snapshot["snapshot_sha256"],
            "record_count": snapshot["record_count"],
            "source_file_count": snapshot["source_file_count"],
            "read_only_source": True,
            "raw_data_written": False,
        }


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    if snapshot.get("schema_version") != TELEMETRY_SCHEMA_VERSION:
        raise TelemetryExportError("Unsupported telemetry snapshot schema.")
    program = snapshot.get("program")
    if not isinstance(program, str) or program not in PROGRAM_NAMES:
        raise TelemetryExportError(f"Unsupported telemetry program {program!r}.")
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


def _timestamp(text: str) -> datetime:
    try:
        value = datetime.fromisoformat(text)
        if value.tzinfo is not None:
            return value.astimezone(UTC)
    except (ValueError, OverflowError):
        pass
    raise argparse.ArgumentTypeError("Use an ISO 8601 timestamp with a UTC offset.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", choices=tuple(PROGRAM_NAMES))
    parser.add_argument("--source-root", required=True, type=Path, help="Directory of saved input logs")
    parser.add_argument("--pattern", required=True, action="append", help="Relative log glob. Repeat to add patterns.")
    parser.add_argument("--at", type=_timestamp, help="Use a fixed generated timestamp")
    parser.add_argument("--output-root", type=Path, help="Write a new snapshot under this directory")
    args = parser.parse_args()

    profile = TelemetrySourceProfile(
        args.program, PROGRAM_NAMES[args.program], args.source_root, tuple(args.pattern)
    )
    exporter = TelemetryExporter(
        (profile,), output_root=args.output_root, now=None if args.at is None else lambda: args.at
    )
    try:
        if args.output_root is None:
            payload = _snapshot_bytes(exporter.collect(args.program))
        else:
            payload = _canonical_json(exporter.export(args.program)) + b"\n"
        sys.stdout.buffer.write(payload)
    except TelemetryExportError as error:
        parser.exit(2, f"{error}\n")
    except ValueError:
        parser.exit(2, "Could not interpret the supplied log pattern or snapshot data.\n")
    except OSError:
        parser.exit(2, "Could not read the saved logs or write the snapshot.\n")


if __name__ == "__main__":
    main()
