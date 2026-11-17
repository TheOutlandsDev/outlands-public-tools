# Refactor Example: Safe subprocess invocation

## Before

```python
import subprocess


def grep_logs(pattern):
    return subprocess.check_output(f"grep {pattern} app.log", shell=True).decode()
```

## After

```python
from __future__ import annotations

import subprocess


def grep_logs(pattern: str) -> str:
    completed = subprocess.run(
        ["grep", "--", pattern, "app.log"],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode not in {0, 1}:
        raise RuntimeError(completed.stderr.strip() or "grep failed")
    return completed.stdout
```

## Why the second version is better

- Avoids shell command injection.
- Separates command arguments.
- Handles grep return code 1 as "no match" rather than a crash.
- Preserves stderr for troubleshooting.
