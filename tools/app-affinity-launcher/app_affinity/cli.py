"""Explicit plan/launch terminal interface. No action on import."""
import argparse
import json
import sys

from .core import AffinityError, launch, make_plan


def parser():
    root = argparse.ArgumentParser(description="Preview or explicitly launch a local Windows .exe with selected processor affinity.")
    commands = root.add_subparsers(dest="command")
    commands.add_parser("demo", help="Print a fictional plan without inspecting or launching an application.")
    for name in ("plan", "launch"):
        command = commands.add_parser(name)
        command.add_argument("--exe", required=True, help="Absolute local .exe path; never searched on PATH.")
        selection = command.add_mutually_exclusive_group(required=True)
        selection.add_argument("--cores", help="Zero-based logical processor numbers, e.g. 0,2.")
        selection.add_argument("--mask", help="Nonzero hexadecimal mask, e.g. 0x5.")
        command.add_argument("--cwd", help="Absolute working directory; defaults to the executable's parent.")
        command.add_argument("--allow-existing", action="store_true", help="Allow an additional instance despite visible exact-path matches.")
        command.add_argument("--no-window", action="store_true", help="Suppress a new console window; does not hide GUI application windows.")
        if name == "launch":
            command.add_argument("--wait", type=float, help="Wait up to 300 seconds; timeout leaves the resumed application running.")
        command.add_argument("arguments", nargs=argparse.REMAINDER, help="Literal child arguments after --.")
    return root


def emit(value, stream=None):
    print(json.dumps(value, ensure_ascii=True, indent=2), file=sys.stdout if stream is None else stream)


def main(argv=None):
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if args.command is None:
        argument_parser.print_help()
        return 0
    if args.command == "demo":
        emit({"schema": 1, "action": "demo", "simulated": True, "launch_requested": False,
              "description": "Fictional example only; no application, process list or Windows API was accessed.",
              "example": {"executable": "D:\\Example Apps\\sample.exe", "cwd": "D:\\Example Apps",
                          "args": ["literal argument"], "mask": "0x5", "cores": [0, 2]},
              "application_readiness_verified": False})
        return 0
    try:
        arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
        plan = make_plan(args.exe, cores=args.cores, mask=args.mask, cwd=args.cwd, args=arguments,
                         allow_existing=args.allow_existing, no_window=args.no_window)
        emit(plan if args.command == "plan" else launch(plan, wait_seconds=args.wait))
        return 0
    except AffinityError as error:
        emit({"status": "error", "message": str(error), "details": error.details}, sys.stderr)
        return 130 if error.details.get("interrupted") else 2
    except KeyboardInterrupt:
        emit({"status": "interrupted", "message": "Interrupted before a launch receipt was available."}, sys.stderr)
        return 130
    except (OSError, ValueError, TypeError):
        emit({"status": "error", "message": "Input or Windows operation was unavailable or unsupported."}, sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
