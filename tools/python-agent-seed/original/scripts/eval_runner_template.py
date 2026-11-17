from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_eval(eval_dir: Path) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(eval_dir) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(eval_dir / "tests")]
    print("Running", " ".join(cmd))
    return subprocess.run(cmd, env=env, check=False).returncode


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/eval_runner_template.py 05_evals/eval_001_pathlib_json_loader")
    eval_dir = (ROOT / sys.argv[1]).resolve()
    if not eval_dir.exists():
        raise SystemExit(f"Eval directory does not exist: {eval_dir}")
    raise SystemExit(run_eval(eval_dir))


if __name__ == "__main__":
    main()
