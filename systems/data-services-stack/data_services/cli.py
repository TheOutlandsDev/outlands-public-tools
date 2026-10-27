"""Explicit local CLI; supplied transport mode is fictional and memory-only."""
import argparse
from copy import deepcopy
import json

from . import files
from .components.outbox import FakeTransport
from .contracts import StackError, canonical, fictional_configuration, fictional_input
from .service import Stack


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise StackError("ARGUMENTS_INVALID")


def demo(root):
    Stack.initialize(root)
    with Stack(root) as app:
        app.configure(fictional_configuration())
        completed = app.run("sample", "sample_run", fictional_input())
        rejected = app.run("sample", "rejected_run", b"null")
        retried = app.dispatch(FakeTransport(outcomes=("retry",)), now=0)
    with Stack(root) as app:
        accepted = app.dispatch(FakeTransport(), now=1)
        app.report_delivery("sample_run", "fake_receipt")
        app.run("sample", "uncertain_run", fictional_input())
        uncertain = app.dispatch(FakeTransport(outcomes=("accepted_then_unknown",)), now=2)
    with Stack(root) as app:
        replay = app.dispatch(FakeTransport(), now=100)
        result = app.result("sample_run")["result"]
        return dict(mode="FICTIONAL_DATA_SERVICES_DEMO", completed=completed, rejected=rejected,
                    retry=retried, acceptance=accepted, uncertain=uncertain,
                    replay_after_restart=replay, result=result, persisted_status=app.status(),
                    real_delivery_verified=False)


def parser():
    selected = Parser(prog="data-services", allow_abbrev=False,
                      description="Local data jobs, baseline forecasts and persisted notification state.")
    selected.add_argument("--workspace", help="explicit private workspace outside the source checkout")
    commands = selected.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "demo", "source-check"):
        commands.add_parser(name, allow_abbrev=False)
    config = commands.add_parser("configure", allow_abbrev=False)
    config.add_argument("--config", required=True)
    run = commands.add_parser("run", allow_abbrev=False)
    run.add_argument("--job", required=True)
    run.add_argument("--key", required=True)
    run.add_argument("--input", required=True)
    result = commands.add_parser("result", allow_abbrev=False)
    result.add_argument("--key", required=True)
    export = commands.add_parser("export", allow_abbrev=False)
    export.add_argument("--key", required=True)
    export.add_argument("--output", required=True)
    dispatch = commands.add_parser("dispatch-fake", allow_abbrev=False)
    dispatch.add_argument("--now", required=True, type=int)
    dispatch.add_argument("--limit", type=int, default=10)
    dispatch.add_argument("--outcomes", default="", help="comma-separated fictional outcome tokens")
    report = commands.add_parser("report-delivery", allow_abbrev=False)
    report.add_argument("--key", required=True)
    report.add_argument("--receipt", required=True)
    recover = commands.add_parser("recover", allow_abbrev=False)
    recover.add_argument("--confirm-stopped", action="store_true")
    package = commands.add_parser("package", allow_abbrev=False)
    package.add_argument("--output", required=True)
    return selected


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        if args.command in ("source-check", "package"):
            from .packaging import package, source_check
            result = source_check() if args.command == "source-check" else package(args.output)
        else:
            if args.workspace is None:
                raise StackError("WORKSPACE_REQUIRED")
            if args.command == "recover" and not args.confirm_stopped:
                raise StackError("STOPPED_ASSERTION_REQUIRED")
            if args.command == "init":
                result = Stack.initialize(args.workspace)
            elif args.command == "demo":
                result = demo(args.workspace)
            else:
                with Stack(args.workspace, confirm_stopped=args.command == "recover") as app:
                    if args.command == "configure":
                        result = app.configure(files.read(args.config, 65536))
                    elif args.command == "run":
                        result = app.run(args.job, args.key, files.read(args.input, 65536))
                    elif args.command == "status":
                        result = app.status()
                    elif args.command == "result":
                        result = app.result(args.key)
                    elif args.command == "export":
                        files.write_new(files.selected(args.output, output=True), canonical(app.result(args.key)))
                        result = dict(status="EXPORTED")
                    elif args.command == "dispatch-fake":
                        outcomes = tuple(args.outcomes.split(",")) if args.outcomes else ()
                        result = app.dispatch(FakeTransport(outcomes=outcomes), now=args.now, limit=args.limit)
                    elif args.command == "report-delivery":
                        result = app.report_delivery(args.key, args.receipt)
                    elif args.command == "recover":
                        result = app.recover(confirm_stopped=True)
        print(canonical(result).decode("ascii"))
        return 2 if type(result) is dict and result.get("state") in ("REJECTED", "REVIEW_REQUIRED") else 0
    except StackError as error:
        print(canonical(dict(status="ERROR", code=str(error))).decode("ascii"))
        return 2
    except KeyboardInterrupt:
        print(canonical(dict(status="ERROR", code="INTERRUPTED")).decode("ascii"))
        return 130
    except Exception:
        print(canonical(dict(status="ERROR", code="OPERATION_FAILED")).decode("ascii"))
        return 2
