from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "04_examples" / "good"


def main() -> None:
    env = os.environ.copy()
    src = str(EXAMPLES / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(EXAMPLES / "tests")]
    completed = subprocess.run(cmd, env=env, check=False, text=True)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
