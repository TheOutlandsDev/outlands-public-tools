"""Regenerate the reviewed template inventory after intentional source changes."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = [{"target": p.relative_to(root / "template").as_posix(),
          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
         for p in sorted((root / "template").rglob("*")) if p.is_file()]
for target, source in [(".kiro/devkit/check_bedrock.py", "scripts/check_bedrock.py"),
                       (".kiro/devkit/pairing-plan.example.json", "pairing-plan.example.json")]:
    files.append({"target": target, "source": source,
                  "sha256": hashlib.sha256((root / source).read_bytes()).hexdigest()})
files.sort(key=lambda entry: entry["target"])
(root / "kit-manifest.json").write_text(
    json.dumps({"version": "1.1.0", "files": files}, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"Reviewed inventory contains {len(files)} template files")
