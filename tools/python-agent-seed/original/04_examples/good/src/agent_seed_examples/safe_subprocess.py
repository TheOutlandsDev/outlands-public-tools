"""Small subprocess wrapper that avoids shell=True by default."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Completed command result."""

    returncode: int
    stdout: str
    stderr: str


def run_command(args: Sequence[str], cwd: str | Path | None = None, timeout_seconds: float = 30.0) -> CommandResult:
    """Run a command with explicit arguments and captured text output.

    This wrapper intentionally does not support shell=True. Callers must pass each argument as a separate sequence item.
    """
    if not args:
        raise ValueError("args must contain at least one command element")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    completed = subprocess.run(
        list(args),
        cwd=Path(cwd) if cwd is not None else None,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout_seconds,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
