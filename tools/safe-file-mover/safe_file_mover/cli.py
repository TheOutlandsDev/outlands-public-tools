"""Command-line interface for Safe File Mover."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import (
    ConflictPolicy,
    MoveOperation,
    Progress,
    SafeMoveEngine,
    SafeMoveError,
    is_remote_path,
)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("ARGUMENTS_INVALID")


class _DiscardTextStream:
    """Minimal process-lifetime sink for a windowed executable's absent console."""

    encoding = "utf-8"
    errors = "backslashreplace"

    def write(self, value: str) -> int:
        return len(value)

    def writelines(self, values: object) -> None:
        for value in values:
            self.write(str(value))

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False


def _configure_console_streams() -> None:
    """Make redirected Windows output safe for Unicode paths.

    A console application frozen for Windows can inherit a legacy code-page
    encoding when its output is piped or captured.  Paths outside that code
    page must never turn a successful file operation into an output error.
    Windowed builds have no standard streams, so those are intentionally
    ignored.
    """
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if stream is None:
            setattr(sys, stream_name, _DiscardTextStream())
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            # Keep the host's encoding so redirected output remains compatible
            # with that host.  Characters outside it are rendered as explicit
            # escapes instead of aborting the file operation.
            reconfigure(errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            # Some embedded or replaced streams cannot be reconfigured.  The
            # command can still run; individual output calls retain their
            # existing error handling in that unusual host.
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="safe-move",
        description="Copy, SHA-256 verify, commit, and retain a recovery copy.",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        help="Journal directory (defaults to the current user's local state directory).",
    )
    commands = parser.add_subparsers(dest="command")

    plan_parser = commands.add_parser("plan", help="Preview and hash a move without writing.")
    _add_move_arguments(plan_parser, include_backup=False)

    move_parser = commands.add_parser("move", help="Perform a verified move.")
    _add_move_arguments(move_parser, include_backup=True)

    list_parser = commands.add_parser("list", help="List journaled operations.")
    list_parser.add_argument(
        "--pending", action="store_true", help="Hide completed/restored operations."
    )

    recover_parser = commands.add_parser("recover", help="Resume interrupted operations.")
    recover_target = recover_parser.add_mutually_exclusive_group(required=True)
    recover_target.add_argument("--id", dest="operation_id")
    recover_target.add_argument("--all", action="store_true")

    purge_parser = commands.add_parser(
        "purge", help="Permanently remove a re-verified recovery copy."
    )
    purge_parser.add_argument("operation_id")
    purge_parser.add_argument(
        "--acknowledge-remote-risk",
        action="store_true",
        help=(
            "Required for a remote destination: acknowledge that byte verification "
            "cannot prove server-side power-loss durability."
        ),
    )

    for command, description in (
        ("restore", "Restore a retained copy to its original path."),
        ("abandon", "Discard an uncommitted partial copy."),
        ("history", "Show the durable event history for one operation."),
    ):
        action_parser = commands.add_parser(command, help=description)
        action_parser.add_argument("operation_id")

    commands.add_parser("gui", help="Open the desktop interface.")
    return parser


def _add_move_arguments(parser: argparse.ArgumentParser, *, include_backup: bool) -> None:
    parser.add_argument("source", type=Path)
    parser.add_argument("destination_directory", type=Path)
    parser.add_argument("--name", help="Use a different final filename/directory name.")
    parser.add_argument(
        "--on-conflict",
        choices=[policy.value for policy in ConflictPolicy],
        default=ConflictPolicy.FAIL.value,
        help="'fail' never overwrites; 'rename' selects name (1), name (2), and so on.",
    )
    if include_backup:
        parser.add_argument(
            "--delete-recovery-copy",
            action="store_true",
            help="Permanently purge the original only after both copies verify again.",
        )


def main(argv: list[str] | None = None) -> int:
    _configure_console_streams()
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
    except ValueError:
        print("Error: ARGUMENTS_INVALID", file=sys.stderr)
        return 2
    if arguments.command is None:
        parser.print_help()
        return 0
    if arguments.command == "gui":
        from .gui import launch

        launch(state_directory=arguments.state_dir)
        return 0

    try:
        engine = SafeMoveEngine(arguments.state_dir)
        if arguments.command == "plan":
            plan = engine.plan(
                arguments.source,
                arguments.destination_directory,
                new_name=arguments.name,
                conflict_policy=arguments.on_conflict,
            )
            print(f"Source:      {plan.source}")
            print(f"Destination: {plan.destination}")
            print(f"Items:       {plan.manifest.item_count:,}")
            print(f"Files:       {plan.manifest.file_count:,}")
            print(f"Data:        {_format_size(plan.manifest.total_bytes)}")
            print(f"Space need:  approximately {_format_size(plan.required_bytes)}")
            print("No files or journal records were changed.")
            print("Warnings:")
            for warning in plan.warnings:
                print(f"  - {warning}")
            return 0

        if arguments.command == "move":
            operation = engine.move(
                arguments.source,
                arguments.destination_directory,
                new_name=arguments.name,
                conflict_policy=arguments.on_conflict,
                keep_backup=not arguments.delete_recovery_copy,
                progress=_console_progress,
            )
            print()
            _print_operation(operation)
            if operation.status == "backup_retained":
                remote_acknowledgment = (
                    " --acknowledge-remote-risk"
                    if is_remote_path(operation.destination)
                    else ""
                )
                print(
                    "The original is retained as a recovery copy. Purge it with:\n"
                    f"  safe-move purge {operation.operation_id}"
                    f"{remote_acknowledgment}"
                )
            return 0

        if arguments.command == "list":
            operations = engine.list_operations(
                include_complete=not arguments.pending
            )
            if not operations:
                print("No journaled operations.")
                return 0
            for operation in operations:
                _print_operation(operation, compact=True)
            return 0

        if arguments.command == "recover":
            if arguments.all:
                recovered = engine.recover_all(progress=_console_progress)
                print()
                if not recovered:
                    print("No interrupted operations needed recovery.")
                for operation in recovered:
                    _print_operation(operation, compact=True)
            else:
                operation = engine.recover(
                    arguments.operation_id, progress=_console_progress
                )
                print()
                _print_operation(operation)
            return 0

        if arguments.command == "purge":
            _print_operation(
                engine.purge_backup(
                    arguments.operation_id,
                    acknowledge_remote_risk=arguments.acknowledge_remote_risk,
                )
            )
            return 0
        if arguments.command == "restore":
            _print_operation(engine.restore_backup(arguments.operation_id))
            return 0
        if arguments.command == "abandon":
            _print_operation(engine.abandon(arguments.operation_id))
            return 0
        if arguments.command == "history":
            for event in engine.journal.events(arguments.operation_id):
                print(
                    f"{event['occurred_at']}  {event['status']:<24}  {event['message']}"
                )
            return 0
    except (SafeMoveError, OSError, KeyError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(
            "\nInterrupted. The journal and any staging copy were retained; run "
            "'safe-move recover --all'.",
            file=sys.stderr,
        )
        return 130
    parser.error("Unknown command")
    return 2


def _console_progress(progress: Progress) -> None:
    if progress.total_bytes:
        percent = min(100.0, 100.0 * progress.bytes_done / progress.total_bytes)
        summary = f"{percent:6.2f}%"
    else:
        summary = f"{progress.items_done}/{progress.item_count} items"
    print(
        f"\r{progress.phase.capitalize():<10} {summary:<12} {progress.path[:60]:<60}",
        end="",
        flush=True,
    )


def _print_operation(operation: MoveOperation, *, compact: bool = False) -> None:
    if compact:
        print(
            f"{operation.operation_id}  {operation.status:<24}  "
            f"{operation.source} -> {operation.destination}"
        )
        return
    print(f"Operation:    {operation.operation_id}")
    print(f"Status:       {operation.status}")
    print(f"Source:       {operation.source}")
    print(f"Destination:  {operation.destination}")
    print(f"Items:        {operation.item_count:,}")
    print(f"Data:         {_format_size(operation.total_bytes)}")
    if operation.status == "backup_retained":
        print(f"Recovery:     {operation.recovery_copy}")
    if operation.last_error:
        print(f"Last error:   {operation.last_error}")


def _format_size(size: int) -> str:
    value = float(size)
    units = ("bytes", "KiB", "MiB", "GiB", "TiB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:,.0f} {unit}" if unit == "bytes" else f"{value:,.2f} {unit}"
        value /= 1024
    return f"{size:,} bytes"


if __name__ == "__main__":
    raise SystemExit(main())
