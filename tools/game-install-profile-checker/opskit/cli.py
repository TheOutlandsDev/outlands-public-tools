"""List or check local TOML game-install profiles."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys
from typing import TextIO

from . import __version__
from .common import OpsKitError, make_report
from .games import check_profiles, list_profiles, profiles_directory


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise OpsKitError("Invalid arguments. See --help for usage.")


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="opskit", description="Inspect local TOML game-install profiles.")
    parser.add_argument("--home", type=Path, required=True, help="Select an existing local root.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    game = commands.add_parser("game", help="Inspect game profiles.")
    games = game.add_subparsers(dest="game_command", required=True)
    list_command = games.add_parser("list", help="List TOML game profiles.")
    list_command.add_argument("--profiles-dir", type=Path, help="Select a directory under the root.")
    check = games.add_parser("check", help="Check one profile or all profiles.")
    selection = check.add_mutually_exclusive_group()
    selection.add_argument("name", nargs="?", help="Select a profile by name.")
    selection.add_argument("--name", dest="named_selection", help="Select a profile by name.")
    selection.add_argument("--all", action="store_true", help="Check all profiles (the default).")
    check.add_argument("--profiles-dir", type=Path, help="Select a directory under the root.")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout if stdout is not None else sys.stdout
    errors = stderr if stderr is not None else sys.stderr
    arguments = list(argv if argv is not None else sys.argv[1:])
    json_output = "--json" in arguments
    arguments = [argument for argument in arguments if argument != "--json"]
    json_output = json_output or any(
        argument == "--format=json" or (argument == "--format" and following == "json")
        for argument, following in zip(arguments, [*arguments[1:], ""])
    )
    try:
        args = _parser().parse_args(arguments)
        directory = profiles_directory(args.home, args.profiles_dir)
        if args.game_command == "list":
            data, warnings = list_profiles(directory)
            ok = True
        else:
            data, warnings = check_profiles(
                directory, args.home, selected_name=args.name or args.named_selection
            )
            ok = data["status"] != "fail"
    except OpsKitError as exc:
        if json_output:
            json.dump(make_report("error", {"error": str(exc)}, ok=False), errors, indent=2)
            errors.write("\n")
        else:
            errors.write(f"ERROR: {exc}\n")
        return exc.exit_code
    except KeyboardInterrupt:
        errors.write("Interrupted.\n")
        return 130

    if json_output:
        json.dump(make_report(f"game-{args.game_command}", data, ok=ok, warnings=warnings),
                  output, indent=2, sort_keys=True)
        output.write("\n")
    else:
        output.write(f"Game profiles: {data['count']} ({data['profiles_directory']})\n")
        for profile in data["profiles"]:
            status = profile.get("status")
            prefix = f"[{status.upper():4}] " if status else ""
            output.write(
                f"  {prefix}{profile['name']} | "
                f"{profile.get('game') or 'unknown game'} | "
                f"{profile.get('engine') or 'unknown engine'} | "
                f"enabled={str(profile.get('enabled', False)).lower()}\n"
            )
            for check in profile.get("checks", []):
                output.write(
                    f"      [{check['status'].upper():4}] {check['name']}: {check['message']}\n"
                )
        for warning in warnings:
            output.write(f"Warning: {warning}\n")
    return 0 if ok else 1


def entrypoint() -> None:
    raise SystemExit(main())
