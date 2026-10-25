"""Explicit CLI; importing Resource Monitor samples nothing and opens no socket."""
import argparse
import math
import sys
import time

from .core import Collector, DemoProvider, LiveProvider, MonitorError, Store, export_csv, export_json, integer, interval_seconds, save_fresh


def parser():
    root = argparse.ArgumentParser(description="OUTLANDS Resource Monitor: aggregate metrics, no packet capture or automatic files.")
    commands = root.add_subparsers(dest="command")
    commands.add_parser("demo", help="Print a deterministic fictional sample without a server or live metrics.")
    sample = commands.add_parser("sample", help="Explicitly collect a bounded live sample sequence.")
    sample.add_argument("--live", action="store_true", required=True)
    sample.add_argument("--count", type=int, default=3)
    sample.add_argument("--interval", type=float, default=1)
    sample.add_argument("--format", choices=("json", "csv"), default="json")
    sample.add_argument("--output", help="Optional explicit fresh export file; otherwise stdout only.")
    serve = commands.add_parser("serve", help="Start a loopback-only dashboard and in-memory sampler.")
    mode = serve.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true")
    mode.add_argument("--live", action="store_true")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--interval", type=float, default=1)
    serve.add_argument("--history", type=int, default=120)
    serve.add_argument("--duration", type=float, help="Optional bounded server lifetime, 0.2-3600 seconds; Ctrl+C otherwise.")
    return root


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.command is None:
            cli.print_help()
            return 0
        if args.command == "demo":
            clock = iter((0, 1))
            from datetime import datetime, timezone
            collector = Collector(DemoProvider(), clock=lambda: next(clock), utc_now=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
            store = Store("demo", 2, 1)
            store.add(collector.collect())
            store.add(collector.collect())
            sys.stdout.write(export_json(store.snapshot()).decode("utf-8"))
            return 0
        interval = interval_seconds(args.interval)
        if args.command == "sample":
            count = integer(args.count, 1, 300, "Sample count")
            if (count - 1) * interval > 3600:
                raise MonitorError("Requested sample sequence exceeds one hour.")
            collector = Collector(LiveProvider())
            store = Store("live", count, interval)
            for index in range(count):
                if index:
                    time.sleep(interval)
                store.add(collector.collect())
            output = export_json(store.snapshot()) if args.format == "json" else export_csv(store.snapshot())
            if args.output:
                save_fresh(args.output, output)
                print("Saved the explicit fresh export file.", file=sys.stderr)
            else:
                sys.stdout.write(output.decode("utf-8"))
            return 0
        if args.duration is not None and (not math.isfinite(args.duration) or not .2 <= args.duration <= 3600):
            raise MonitorError("Server duration must be finite and between 0.2 and 3600 seconds.")
        from .server import MonitorApp
        provider = DemoProvider() if args.demo else LiveProvider()
        app = MonitorApp(provider, args.port, interval, args.history)
        with app:
            print(f"OUTLANDS Resource Monitor ({provider.mode}). Open this local capability URL:", flush=True)
            print(app.url, flush=True)
            print("The token stays in this local process/browser. Ctrl+C stops sampling; no history is saved automatically.", flush=True)
            app.stop_event.wait(args.duration)
        return 0
    except KeyboardInterrupt:
        print("\nStopped; no automatic history file was saved.", file=sys.stderr)
        return 130
    except (MonitorError, OSError, ValueError):
        print("Resource Monitor could not complete the selected operation. Check its explicit bounds, dependency, port or output path.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
