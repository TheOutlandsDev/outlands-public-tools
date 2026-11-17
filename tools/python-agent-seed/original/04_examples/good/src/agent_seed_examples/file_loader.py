"""Safe JSON object loading using pathlib and explicit errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonLoadError(ValueError):
    """Raised when a JSON file cannot be loaded as an object."""


def load_json_object(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON file that must contain a JSON object.

    Args:
        path: File path to read.

    Returns:
        Parsed JSON object.

    Raises:
        JsonLoadError: If the file is missing, invalid JSON, or not an object.
    """
    file_path = Path(path)
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JsonLoadError(f"Could not read JSON file: {file_path}") from exc

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise JsonLoadError(f"Invalid JSON in file: {file_path}") from exc

    if not isinstance(parsed, dict):
        raise JsonLoadError(f"Expected JSON object in file: {file_path}")

    return parsed
