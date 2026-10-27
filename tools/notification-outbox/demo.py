"""Built-in fictional notifications only; no email transport or operator input."""
import argparse
from dataclasses import asdict
import json

from outbox import FakeTransport, Message, Outbox, OutboxError


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise OutboxError("ARGUMENTS_INVALID")


def run_demo():
    outbox = Outbox()
    message = Message("notice_a", "sample_route", "Fictional summary", "Invented reference result.")
    outbox.enqueue(message)
    duplicate_suppressed = not outbox.enqueue(message)
    transport = FakeTransport(outcomes=("retry", "accept"))
    retry = outbox.dispatch(transport, now=0)[0]
    accepted = outbox.dispatch(transport, now=1)[0]
    outbox.report_delivery(message.key, receipt="fake_receipt")
    reported = outbox.snapshot(message.key)

    uncertain_box = Outbox()
    uncertain_box.enqueue(Message("notice_b", "sample_route", "Fictional notice", "Invented second result."))
    uncertain_transport = FakeTransport(outcomes=("accepted_then_unknown",))
    uncertain = uncertain_box.dispatch(uncertain_transport, now=0)[0]
    no_replay = uncertain_box.dispatch(uncertain_transport, now=100) == ()
    return dict(mode="FICTIONAL_OUTBOX_DEMO", duplicate_suppressed=duplicate_suppressed,
                retry=asdict(retry), accepted=asdict(accepted), delivery_report=asdict(reported),
                uncertain=asdict(uncertain), uncertain_not_replayed=no_replay,
                fake_acceptance_occurred=uncertain_transport.accepted_keys == ("notice_b",),
                real_delivery_verified=False, application_files_written=0)


def main(argv=None):
    parser = Parser(prog="notification-outbox", description="Run a fictional in-memory outbox example.")
    parser.add_argument("--demo", action="store_true", help="use invented messages and fake transport")
    try:
        args = parser.parse_args(argv)
        if not args.demo:
            parser.print_help()
            return 0
        print(json.dumps(run_demo(), sort_keys=True))
        return 0
    except OutboxError as error:
        print(json.dumps(dict(status="ERROR", code=str(error)), sort_keys=True))
        return 2
    except KeyboardInterrupt:
        print(json.dumps(dict(status="ERROR", code="INTERRUPTED"), sort_keys=True))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
