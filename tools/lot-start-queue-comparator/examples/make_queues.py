"""Create fictional baseline and candidate queues in a new directory."""

import argparse
import json
from pathlib import Path


def demo_row(modality="DEMO-A", lots=1, start_by=None):
    return dict(
        modality=modality, part_number=f"{modality}-PART", lot_size=24,
        remaining_demand=30, eligible_wip=12, uncovered_after_wip=18,
        recommended_lots=lots, recommended_start_quantity=lots * 24, recommended_start_by=start_by,
    )


def make_queues(root: Path) -> None:
    root.mkdir()
    before = [demo_row("DEMO-B", start_by="2031-05-10"), demo_row("DEMO-A", start_by="2031-05-09")]
    after = [demo_row("DEMO-A", lots=2, start_by="2031-05-09"), demo_row("DEMO-B", start_by="2031-05-12")]
    for name, rows in (("before.json", before), ("after.json", after)):
        (root / name).write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    make_queues(parser.parse_args().directory)
