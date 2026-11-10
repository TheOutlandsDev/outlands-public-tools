"""Session-start information only. No network, subprocesses, or file writes."""
import json
from pathlib import Path
import sys

root = Path.cwd()
routes_file = root / ".kiro" / "devkit" / "routes.json"
try:
    routes = json.loads(routes_file.read_text(encoding="utf-8"))
except (OSError, ValueError) as exc:
    print(json.dumps({"configuration": "ERROR", "detail": str(exc)}))
    raise SystemExit(1)
print(json.dumps({
    "kit": "1.2.0",
    "python": ".".join(map(str, sys.version_info[:3])),
    "python315": sys.version_info[:2] == (3, 15),
    "configured_model_pins": routes["model_pins"],
    "live_model_and_provider": "Confirm in managed Kiro client; not checked here",
    "handoff_present": (root / ".kiro-kit" / "handoff.md").is_file()
}, indent=2))
if sys.version_info[:2] != (3, 15):
    raise SystemExit(1)
