"""Separate reference repair; the original starter remains unchanged."""
import json
from pathlib import Path
from typing import Any

class JsonLoaderError(ValueError):
    pass

def load_json_object(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise JsonLoaderError('JSON input could not be read or parsed') from error
    if not isinstance(value, dict):
        raise JsonLoaderError('JSON input must be an object')
    return value
