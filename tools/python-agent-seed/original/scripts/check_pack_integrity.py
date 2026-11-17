from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    "00_START_HERE.md",
    "01_agent_seed/agent_operating_spec.md",
    "01_agent_seed/python_3127_coding_doctrine.md",
    "02_source_catalog/source_manifest.json",
    "02_source_catalog/source_manifest.csv",
    "03_ingestion_templates/chunking_policy.md",
    "04_examples/good/src/agent_seed_examples/file_loader.py",
    "05_evals/README.md",
]


def main() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        raise SystemExit(f"Missing required files: {missing}")

    manifest_path = ROOT / "02_source_catalog/source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list) or len(manifest) < 20:
        raise SystemExit("Source manifest is unexpectedly small or invalid")

    required_keys = {"id", "title", "url", "source_type", "authority", "license_note", "retrieval_policy", "priority", "topics", "recommended_use"}
    for entry in manifest:
        missing_keys = required_keys - entry.keys()
        if missing_keys:
            raise SystemExit(f"Manifest entry {entry.get('id')} missing keys: {sorted(missing_keys)}")

    print(f"OK: seed pack integrity check passed with {len(manifest)} source records.")


if __name__ == "__main__":
    main()
