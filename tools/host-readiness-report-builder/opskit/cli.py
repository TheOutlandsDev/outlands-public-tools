"""Offline doctor argument parsing and report presentation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence, TextIO

from . import __version__
from .system import ObservationError, doctor, read_observations


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ObservationError("Invalid command arguments. Use --help for usage.")


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="opskit",
        description="Build a host readiness report from saved observations.",
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="Write JSON output.")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor_parser = commands.add_parser(
        "doctor", help="Assess saved host observations.", allow_abbrev=False
    )
    doctor_parser.add_argument(
        "--observations", type=Path, required=True, help="Saved UTF-8 JSON observation file."
    )
    doctor_parser.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS, help="Write JSON output."
    )
    return parser


def _report(
    command: str, data: dict[str, Any], *, ok: bool, warnings: list[str]
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "command": command,
        "ok": ok,
        "warnings": warnings,
        "data": data,
    }


def _write_json(value: dict[str, Any], stream: TextIO) -> None:
    json.dump(value, stream, indent=2, sort_keys=True)
    stream.write("\n")


def _write_human(data: dict[str, Any], warnings: list[str], stream: TextIO) -> None:
    stream.write(f"OpsKit doctor: {data['status'].upper()}\n")
    summary = data["summary"]
    stream.write(
        f"  {summary['pass']} passed, {summary['warn']} warning(s), "
        f"{summary['fail']} failed\n"
    )
    for check in data["checks"]:
        stream.write(
            f"  [{check['status'].upper():4}] {check['name']}: {check['message']}\n"
        )
    for warning in warnings:
        stream.write(f"WARNING: {warning}\n")


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parser().parse_args(arguments)
        data, warnings = doctor(read_observations(args.observations))
    except ObservationError as exc:
        if "--json" in arguments:
            error = {"error": str(exc), "type": "ObservationError"}
            _write_json(_report("error", error, ok=False, warnings=[]), errors)
        else:
            errors.write(f"ERROR: {exc}\n")
        return 2
    except KeyboardInterrupt:
        errors.write("Interrupted.\n")
        return 130

    ok = data["status"] != "fail"
    if args.json:
        _write_json(_report("doctor", data, ok=ok, warnings=warnings), output)
    else:
        _write_human(data, warnings, output)
    return 0 if ok else 1
