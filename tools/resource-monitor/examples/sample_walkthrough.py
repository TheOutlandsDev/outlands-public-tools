"""Original fictional walkthrough. No machine APIs, socket or file output."""
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resource_monitor import Collector, DemoProvider, Store, export_json


def main():
    values = iter([0, 1])
    collector = Collector(DemoProvider(), clock=lambda: next(values), utc_now=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    history = Store("demo", 2, 1)
    history.add(collector.collect())
    history.add(collector.collect())
    print(export_json(history.snapshot()).decode("utf-8"), end="")


if __name__ == "__main__":
    main()
