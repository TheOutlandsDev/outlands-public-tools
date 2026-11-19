"""Command line entry point for selected saved incident evidence."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys
from typing import TextIO

from .common import OpsKitError, make_report
from .incidents import MAX_FILE_BYTES, create_bundle


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise OpsKitError("Invalid arguments. See --help for usage.")


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="opskit", description="Package selected saved incident evidence.")
    parser.add_argument("--home", type=Path, required=True, help="Existing directory for relative paths.")
    commands = parser.add_subparsers(dest="command", required=True)
    incident = commands.add_parser("incident", help="Work with saved incident evidence.")
    incident_commands = incident.add_subparsers(dest="incident_command", required=True)
    bundle = incident_commands.add_parser("bundle", help="Create and hash a bundle.")
    bundle.add_argument("--doctor", type=Path, required=True, help="Saved doctor JSON object.")
    bundle.add_argument("--inventory", type=Path, required=True, help="Saved inventory JSON object.")
    bundle.add_argument("--ports", type=Path, required=True, help="Saved ports JSON object.")
    bundle.add_argument("--output", type=Path, required=True, help="Bundle ZIP destination.")
    bundle.add_argument("--include", type=Path, action="append", default=[], help="Explicit UTF-8 text attachment.")
    bundle.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES)
    bundle.add_argument("--force", action="store_true", help="Replace an existing bundle at the selected output.")
    bundle.add_argument("--json", action="store_true", help="Print a JSON receipt.")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    try:
        args = _parser().parse_args(argv)
        data, warnings = create_bundle(
            args.output,
            args.home,
            doctor_file=args.doctor,
            inventory_file=args.inventory,
            ports_file=args.ports,
            include_files=args.include,
            max_file_bytes=args.max_file_bytes,
            force=args.force,
        )
    except OpsKitError as exc:
        errors.write(f"ERROR: {exc}\n")
        return 2

    if args.json:
        json.dump(make_report("incident-bundle", data, warnings=warnings), output,
                  indent=2, sort_keys=True, ensure_ascii=True)
        output.write("\n")
    else:
        output.write(f"Incident bundle created. SHA-256 {data['sha256']}\n")
    return 0
