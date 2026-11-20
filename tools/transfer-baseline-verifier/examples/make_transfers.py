"""Create a fictional transfer baseline and approved assembly list."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def make_transfers(root: Path) -> None:
    root.mkdir()
    assemblies = [f"99000{number:02}" for number in range(1, 6)]
    records = []
    for number in range(1, 30):
        records.append(dict(
            source_row_number=number, assembly=assemblies[(number - 1) % len(assemblies)],
            lot_id=f"DEMO_LOT_{number:02}", quantity=number * 3, status="CLOSED",
            occurred_at=f"2031-01-{number:02}T12:00:00{'-05:00' if number == 1 else '-04:00'}",
        ))
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload = dict(
        schema_version="0.1.0", status="DEVELOPMENT_VALIDATION_FIXTURE", source_identity="FICTIONAL-TRANSFER-01",
        source_sha256=sha256(canonical).hexdigest(),
        declared_window_start="2031-01-01", declared_window_end="2031-01-29",
        event_type="FLEX_TO_HLA_TRANSFER", expected_records=29, expected_quantity=1305,
        proves_hla_consumption=False, database_ingestion_authorized=False, records=records,
    )
    (root / "approved-assemblies.json").write_text(json.dumps({"assemblies": assemblies}), encoding="utf-8")
    (root / "baseline.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    make_transfers(parser.parse_args().directory)
