"""Regenerate the reviewed template inventory after intentional source changes."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = [{"target": p.relative_to(root / "template").as_posix(),
          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
         for p in sorted((root / "template").rglob("*")) if p.is_file()]
(root / "kit-manifest.json").write_text(
    json.dumps({"version": "1.0.0", "files": files}, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"Reviewed inventory contains {len(files)} template files")
