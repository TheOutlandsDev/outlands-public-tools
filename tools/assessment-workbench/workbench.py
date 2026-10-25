#!/usr/bin/env python3
"""Offline Assessment Workbench: explicit private records, no target testing."""

from __future__ import annotations

import argparse
import json
import sys

import workbench_core as core


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise core.WorkbenchError("ARGUMENTS_INVALID") from None


def _parser():
    parser = Parser(
        prog="assessment-workbench", description=__doc__, allow_abbrev=False
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + core.VERSION
    )
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    commands.add_parser("gui", allow_abbrev=False)
    for name in (
        "init",
        "demo",
        "show",
        "check",
        "history",
        "revision",
        "save",
        "put",
        "remove",
        "import",
        "export",
        "clone",
        "recover",
    ):
        item = commands.add_parser(name, allow_abbrev=False)
        item.add_argument("--store", required=True)
        if name in ("show", "revision"):
            item.add_argument("--records", action="store_true")
        if name == "revision":
            item.add_argument("--revision", type=int, required=True)
        if name in ("save", "import"):
            item.add_argument("--input", required=True)
        if name in ("save", "put", "remove"):
            item.add_argument("--expected-revision", type=int, required=True)
        if name in ("put", "remove"):
            item.add_argument(
                "--kind", choices=("submissions", "findings", "retests"), required=True
            )
            item.add_argument("--id", required=name == "remove")
        if name == "put":
            item.add_argument("--record", required=True)
        if name in ("export", "clone", "recover"):
            item.add_argument("--output", required=True)
        if name in ("clone", "recover"):
            item.add_argument("--revision", type=int)
    return parser


def _summary(snapshot, *, records=False):
    result = dict(revision=snapshot["revision"], validation=snapshot["validation"])
    if records:
        result["records"] = snapshot["records"]
    return result


def main(argv=None):
    values = sys.argv[1:] if argv is None else list(argv)
    try:
        if not values or values == ["gui"]:
            from workbench_gui import main as launch_gui

            launch_gui()
            return 0
        args = _parser().parse_args(values)
        name = args.command
        if name == "init":
            result = _summary(core.create_store(args.store))
        elif name == "demo":
            result = _summary(core.create_demo(args.store))
        elif name == "import":
            result = _summary(core.import_to_new_store(args.input, args.store))
        elif name == "show":
            result = _summary(core.load_store(args.store), records=args.records)
        elif name == "check":
            result = core.load_store(args.store)["validation"]
        elif name == "history":
            result = dict(history=core.list_history(args.store))
        elif name == "revision":
            result = _summary(
                core.load_revision(args.store, args.revision), records=args.records
            )
        elif name == "save":
            result = _summary(
                core.save_records(
                    args.store,
                    core.read_records_file(args.input),
                    args.expected_revision,
                )
            )
        elif name == "put":
            result = _summary(
                core.put_record(
                    args.store,
                    args.kind,
                    core.read_record_file(args.record),
                    args.expected_revision,
                    args.id,
                )
            )
        elif name == "remove":
            result = _summary(
                core.remove_record(
                    args.store, args.kind, args.id, args.expected_revision
                )
            )
        elif name == "export":
            result = core.export_records(args.store, args.output)
        elif name in ("clone", "recover"):
            result = _summary(core.clone_store(args.store, args.output, args.revision))
        else:
            raise core.WorkbenchError("ARGUMENTS_INVALID")
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 1 if name == "check" and result["status"] == "REVIEW_REQUIRED" else 0
    except core.WorkbenchError as error:
        code = str(error)
    except KeyboardInterrupt:
        print(json.dumps(dict(status="ERROR", code="INTERRUPTED_REOPEN_BEFORE_RETRY")))
        return 130
    except (OSError, ValueError, TypeError, ImportError, UnicodeError, RecursionError):
        code = "OPERATION_FAILED_REOPEN_REQUIRED"
    print(json.dumps(dict(status="ERROR", code=code), sort_keys=True))
    return 2


if __name__ == "__main__":
    sys.exit(main())
