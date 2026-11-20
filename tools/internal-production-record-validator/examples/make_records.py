"""Write a fictional product map and saved record batch."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from production_records import operational_event_identity


DEMAND_ID = "00000000-0000-4000-8000-000000000001"
PRODUCTS = {"products": [
    dict(canonical_modality=f"DEM{number:02}", display_modality=f"XDEM{number:02}",
         assembly=f"99100{number:02}", lot_prefix=f"XDEM{number:02}")
    for number in range(1, 6)
]}
EVIDENCE = dict(source_sha256="a" * 64, source_row_number=14, lot_id="XDEM01_ALPHA",
                canonical_modality="DEM01", display_modality="XDEM01", assembly="9910001",
                quantity=18, step_name="Fictional inspection")


def make_records(root: Path) -> None:
    root.mkdir()
    rows = [
        dict(kind="demand-create", demand_id=DEMAND_ID, modality="XDEM01", requested_quantity=36,
             needed_by="2031-03-02", demand_status="DRAFT", revision_comment="Fictional demand"),
        dict(kind="demand-revision", expected_revision=1, requested_quantity=30,
             needed_by="2031-03-03", demand_status="ACTIVE", revision_comment="Fictional revision"),
        dict(kind="completion", evidence=EVIDENCE,
             command=dict(completion_revision=1, source_sha256="a" * 64, completion_comment="Fictional review")),
        dict(kind="transfer", expected_row_version=2, transfer_comment="Fictional transfer"),
        dict(kind="bulk-transfer", lots=[dict(lot_id="XDEM01_ALPHA", expected_row_version=2),
                                        dict(lot_id="XDEM02_BETA", expected_row_version=4)],
             transfer_comment="Fictional batch"),
        dict(kind="event-identity", event_type="MANUAL_INTERNAL_DEMAND", target_id=DEMAND_ID,
             revision=1, event_id=operational_event_identity("MANUAL_INTERNAL_DEMAND", DEMAND_ID, 1)),
    ]
    for name, value in (("products.json", PRODUCTS), ("records.json", {"records": rows})):
        (root / name).write_text(json.dumps(value, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    make_records(parser.parse_args().directory)
