"""Render saved assistant operations snapshots as compact JSON or Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

MAX_INPUT_BYTES = 2_000_000


def _compact_operations_evidence(encoded: str) -> str:
    """Remove UI-only detail before sending a status snapshot to the model."""

    try:
        envelope = json.loads(encoded)
        payload = envelope.get("result", {}) if envelope.get("ok") else envelope
        programs = []
        for program in payload.get("programs", []):
            programs.append(
                {
                    "id": program.get("id"),
                    "status": program.get("status"),
                    "processes": program.get("processes"),
                    "listeners": program.get("listeners"),
                    "tasks": [
                        {
                            "name": task.get("name"),
                            "installed": task.get("installed"),
                            "enabled": task.get("enabled"),
                            "state": task.get("state"),
                            "last_result": task.get("last_result"),
                            "last_run": task.get("last_run"),
                            "next_run": task.get("next_run"),
                        }
                        for task in program.get("tasks", [])
                    ],
                    "services": program.get("services", []),
                    "endpoints": [
                        {
                            "url": endpoint.get("url"),
                            "healthy": endpoint.get("healthy"),
                            "status": endpoint.get("status"),
                            "milliseconds": endpoint.get("milliseconds"),
                        }
                        for endpoint in program.get("endpoints", [])
                    ],
                    "state": program.get("state"),
                    "issues": program.get("issues"),
                }
            )
        compact = {
            "generated": payload.get("generated"),
            "summary": payload.get("summary"),
            "programs": programs,
            "read_only": True,
        }
        return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, json.JSONDecodeError):
        return encoded[:12000]


def _format_operations_status(encoded: str) -> str:
    """Render current status evidence without spending an LLM generation round."""

    try:
        envelope = json.loads(encoded)
        payload = envelope.get("result", {}) if envelope.get("ok") else envelope
        programs = payload.get("programs", [])
        if not programs:
            return ""
        lines: list[str] = []
        for program in programs:
            if lines:
                lines.append("")
            name = str(program.get("name") or program.get("id") or "Program")
            status = str(program.get("status") or "unknown").upper()
            lines.append(f"**{name}**: {status}.")

            processes = program.get("processes") or []
            if processes:
                process_text = ", ".join(
                    f"{item.get('name')} PID {item.get('pid')}" for item in processes
                )
                lines.append(f"- Processes: {process_text}.")

            tasks = program.get("tasks") or []
            if tasks:
                task_text: list[str] = []
                for task in tasks:
                    if not task.get("installed", True):
                        task_text.append(f"{task.get('name')}: not installed")
                        continue
                    detail = f"{task.get('name')}: {task.get('state', 'unknown')}"
                    if task.get("last_result"):
                        detail += f" ({task.get('last_result')})"
                    if task.get("next_run"):
                        detail += f", next {task.get('next_run')}"
                    task_text.append(detail)
                lines.append(f"- Schedulers: {'; '.join(task_text)}.")

            services = program.get("services") or []
            if services:
                service_text = ", ".join(
                    f"{item.get('name')}: {item.get('state', 'unknown')} "
                    f"({item.get('start_mode', 'unknown')})"
                    for item in services
                )
                lines.append(f"- Services: {service_text}.")

            listeners = program.get("listeners") or {}
            listener_parts = []
            if listeners.get("tcp"):
                listener_parts.append(
                    "TCP " + ", ".join(str(port) for port in listeners["tcp"])
                )
            if listeners.get("udp"):
                listener_parts.append(
                    "UDP " + ", ".join(str(port) for port in listeners["udp"])
                )
            if listener_parts:
                lines.append(f"- Listeners: {'; '.join(listener_parts)}.")

            endpoints = program.get("endpoints") or []
            if endpoints:
                endpoint_text = ", ".join(
                    f"{item.get('url')}={item.get('status', 'unreachable')}"
                    f" ({'healthy' if item.get('healthy') else 'unhealthy'})"
                    for item in endpoints
                )
                lines.append(f"- Endpoints: {endpoint_text}.")

            state = program.get("state")
            if state:
                lines.append(
                    f"- State: {state.get('actual', 'unknown')} "
                    f"(expected {state.get('expected', 'unknown')})."
                )

            issues = program.get("issues") or []
            lines.append(
                f"- Issues: {'; '.join(str(issue) for issue in issues)}."
                if issues
                else "- Issues: none in the current read-only snapshot."
            )
        return "\n".join(lines)
    except (AttributeError, TypeError, json.JSONDecodeError):
        return ""


class SnapshotInputError(ValueError):
    """A saved snapshot violates the CLI input contract."""


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, value in pairs:
        if key in values:
            raise SnapshotInputError("Duplicate JSON key.")
        values[key] = value
    return values


def _reject_constant(_: str) -> None:
    raise SnapshotInputError("Use standard JSON numbers.")


def _check_shape(envelope: Any) -> None:
    if not isinstance(envelope, dict):
        raise SnapshotInputError("Snapshot must be a JSON object.")
    if "ok" in envelope and type(envelope["ok"]) is not bool:
        raise SnapshotInputError("Envelope ok must be a JSON boolean.")
    payload = envelope.get("result") if envelope.get("ok") else envelope
    programs = payload.get("programs") if isinstance(payload, dict) else None
    if not isinstance(programs, list) or any(not isinstance(program, dict) for program in programs):
        raise SnapshotInputError("Snapshot programs must be an array of objects.")

    for program in programs:
        for key in ("processes", "tasks", "services", "endpoints"):
            entries = program.get(key, [])
            if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
                raise SnapshotInputError(f"Program {key} must be an array of objects.")
        if not isinstance(program.get("issues", []), list):
            raise SnapshotInputError("Program issues must be an array.")
        listeners = program.get("listeners")
        if listeners is not None and (
            not isinstance(listeners, dict)
            or any(not isinstance(listeners.get(protocol, []), list) for protocol in ("tcp", "udp"))
        ):
            raise SnapshotInputError("Program listener values for TCP and UDP must be arrays.")
        state = program.get("state")
        if state is not None and not isinstance(state, dict):
            raise SnapshotInputError("Program state must be an object or null.")


def _load_snapshot(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SnapshotInputError("Snapshot input must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise SnapshotInputError("Snapshot exceeds 2,000,000 bytes.")
    try:
        decoded = raw.decode("utf-8-sig")
        envelope = json.loads(decoded, object_pairs_hook=_unique_fields, parse_constant=_reject_constant)
        # Refuse nonfinite floats from exponent overflow and lone Unicode surrogates.
        json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except SnapshotInputError:
        raise
    except (ValueError, RecursionError) as error:
        raise SnapshotInputError("Invalid UTF-8 JSON snapshot.") from error
    _check_shape(envelope)
    return decoded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("format", choices=("compact", "markdown"))
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 JSON snapshot")
    args = parser.parse_args()
    try:
        encoded = _load_snapshot(args.input)
        report = (
            _compact_operations_evidence(encoded)
            if args.format == "compact"
            else _format_operations_status(encoded)
        )
    except SnapshotInputError as error:
        parser.exit(2, f"{error}\n")
    except OSError:
        parser.exit(2, "Could not read the saved snapshot.\n")
    if report:
        sys.stdout.buffer.write((report + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
