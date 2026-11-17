# Refactor Example: os.path to pathlib

## Before

```python
import json
import os


def load_config(base_dir, name):
    path = os.path.join(base_dir, name + ".json")
    with open(path) as f:
        return json.load(f)
```

## After

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(base_dir: str | Path, name: str) -> dict[str, Any]:
    path = Path(base_dir) / f"{name}.json"
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in config file: {path}")
    return data
```

## Why the second version is better

- Uses `Path` composition instead of manual string joins.
- Uses explicit UTF-8 encoding.
- Has type annotations.
- Validates the expected JSON shape.
