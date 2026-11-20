"""Write four fictional saved shipment records to a new JSON file."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shipment_events import flex_handoff_event_identity, outbound_event_identity


def make_records(path: Path) -> None:
    revision, row_id = "a" * 64, "b" * 24
    handoff = dict(revision_sha256=revision, row_id=row_id, lot_id="DEMO-LOT-01",
                   quantity=12, action="READY_FOR_LOGISTICS", state_version=1)
    payload = {"records": [
        dict(kind="dock-event", revision_sha256=revision, row_id=row_id, order_row_version=3,
             event_id=outbound_event_identity(revision, row_id, 3)),
        dict(kind="handoff-event", **handoff, event_id=flex_handoff_event_identity(**handoff)),
        dict(kind="ready-record", source_revision_sha256=revision, expected_order_version=3,
             lots=[dict(lot_id="DEMO-LOT-01", quantity=12), dict(lot_id="DEMO-LOT-02", quantity=8)]),
        dict(kind="return-record", source_revision_sha256=revision, expected_order_version=4,
             lots=[dict(lot_id="DEMO-LOT-01", expected_state_version=1)],
             reason="Fictional lot requires review"),
    ]}
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    make_records(parser.parse_args().output)
