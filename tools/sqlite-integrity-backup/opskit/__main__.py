"""Run the standalone OpsKit SQLite commands."""

import argparse
import json
from pathlib import Path
import sys

from .common import OpsKitError
from .sqlite_tools import backup_database, check_database


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "Invalid arguments. See --help for usage.\n")


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser(prog="python -m opskit", description="Check or back up a saved SQLite database.")
    commands = parser.add_subparsers(dest="command", required=True)
    sqlite = commands.add_parser("sqlite", help="Run a SQLite operation.")
    sqlite_commands = sqlite.add_subparsers(dest="operation", required=True)
    check = sqlite_commands.add_parser("check", help="Check a SQLite database.")
    check.add_argument("database", type=Path)
    check.add_argument("--full", action="store_true", help="Run the full integrity check.")
    backup = sqlite_commands.add_parser("backup", help="Create a verified SQLite backup.")
    backup.add_argument("source", type=Path)
    backup.add_argument("destination", type=Path)
    backup.add_argument("--force", action="store_true", help="Replace a closed destination file.")
    args = parser.parse_args(argv)

    try:
        if args.operation == "check":
            result = check_database(args.database, full=args.full)
            exit_code = 0 if result["ok"] else 1
        else:
            result = backup_database(args.source, args.destination, force=args.force)
            exit_code = 0
    except OpsKitError:
        print("Could not complete the supplied SQLite operation.", file=sys.stderr)
        return 2

    print(json.dumps(result, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
