from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "02_source_catalog" / "source_manifest.json"
OUTPUT = ROOT / "02_source_catalog" / "source_manifest_index.md"


def main() -> None:
    records = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lines = ["# Source Manifest Index", ""]
    for record in sorted(records, key=lambda item: (item["priority"], item["source_type"], item["id"])):
        lines.extend([
            f"## {record['title']}",
            "",
            f"- ID: `{record['id']}`",
            f"- URL: {record['url']}",
            f"- Type: {record['source_type']}",
            f"- Authority: {record['authority']}",
            f"- Priority: {record['priority']}",
            f"- Topics: {', '.join(record['topics'])}",
            f"- License note: {record['license_note']}",
            f"- Retrieval policy: {record['retrieval_policy']}",
            f"- Recommended use: {record['recommended_use']}",
            "",
        ])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
