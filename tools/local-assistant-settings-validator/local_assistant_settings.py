"""Validate and normalize saved local assistant settings offline."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, fields
import json
import math
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

MAX_INPUT_BYTES = 2_000_000
LOOPBACK_AUTHORITY = re.compile(r"(?:127\.0\.0\.1|localhost|\[::1\])(?::[0-9]+)?", re.IGNORECASE)


def validate_local_url(url: str) -> str:
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in url):
        raise ValueError("The Ollama URL may not contain spaces or control characters.")
    try:
        parsed = urlparse(url)
    except ValueError:
        raise ValueError("Invalid Ollama URL.") from None
    if parsed.scheme != "http":
        raise ValueError("The Ollama URL must use local HTTP.")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Only a loopback Ollama server is allowed.")
    if "@" in parsed.netloc or "?" in url or "#" in url:
        raise ValueError("The Ollama URL may not contain credentials, query data, or a fragment.")
    if not LOOPBACK_AUTHORITY.fullmatch(parsed.netloc):
        raise ValueError("Invalid loopback address or port.")
    try:
        parsed.port
    except ValueError:
        raise ValueError("Invalid loopback address or port.") from None
    return url.rstrip("/")


@dataclass(slots=True)
class Settings:
    settings_version: int = 3
    owner_name: str = "Example Owner"
    model: str = "fictional-main"
    fast_model: str = "fictional-fast"
    fast_routing: bool = True
    ollama_url: str = "http://127.0.0.1:11434"
    temperature: float = 0.2
    context_window: int = 8192
    fast_context_window: int = 4096
    reasoning: str = "auto"
    approval_mode: str = "ask"
    show_thinking: bool = False
    max_tool_rounds: int = 8
    max_output_tokens: int = 1536
    history_messages: int = 24
    keep_alive: str = "0s"

    def validate(self) -> "Settings":
        self.ollama_url = validate_local_url(self.ollama_url)
        self.owner_name = (self.owner_name or "Example Owner").strip()[:80] or "Example Owner"
        self.model = (self.model or "fictional-main").strip()
        self.fast_model = (self.fast_model or "fictional-fast").strip()
        self.temperature = max(0.0, min(float(self.temperature), 2.0))
        self.context_window = max(4096, min(int(self.context_window), 131072))
        self.fast_context_window = max(
            2048, min(int(self.fast_context_window), 16384)
        )
        self.reasoning = (
            self.reasoning
            if self.reasoning in {"auto", "low", "medium", "high"}
            else "auto"
        )
        self.approval_mode = (
            self.approval_mode
            if self.approval_mode in {"ask", "autonomous"}
            else "ask"
        )
        self.max_tool_rounds = max(1, min(int(self.max_tool_rounds), 30))
        self.max_output_tokens = max(128, min(int(self.max_output_tokens), 8192))
        self.history_messages = max(8, min(int(self.history_messages), 100))
        self.settings_version = 3
        return self


class SettingsInputError(ValueError):
    """A saved settings file violates the CLI input contract."""


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field, value in pairs:
        if field in values:
            raise SettingsInputError("Duplicate JSON key.")
        values[field] = value
    return values


def _reject_constant(_: str) -> None:
    raise SettingsInputError("Use standard JSON numbers.")


def _load_settings(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise SettingsInputError("Settings input must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise SettingsInputError("Settings input exceeds 2,000,000 bytes.")
    try:
        values = json.loads(
            raw.decode("utf-8-sig"), object_pairs_hook=_unique_fields, parse_constant=_reject_constant
        )
        json.dumps(values, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except SettingsInputError:
        raise
    except (ValueError, RecursionError) as error:
        raise SettingsInputError("Invalid UTF-8 JSON settings.") from error
    if not isinstance(values, dict):
        raise SettingsInputError("Settings must be a JSON object.")
    return values


def _normalize(values: dict[str, Any]) -> Settings:
    defaults = {field.name: field.default for field in fields(Settings)}
    if values.keys() - defaults.keys():
        raise SettingsInputError("Unknown settings fields.")
    for name, value in values.items():
        default_type = type(defaults[name])
        if default_type is bool:
            if type(value) is not bool:
                raise SettingsInputError(f"{name} must be a JSON boolean.")
        elif default_type in (int, float):
            if type(value) not in (int, float, str):
                raise SettingsInputError(f"{name} must be numeric.")
            try:
                number = default_type(value)
            except (ValueError, OverflowError):
                raise SettingsInputError(f"{name} must be numeric.") from None
            if isinstance(number, float) and not math.isfinite(number):
                raise SettingsInputError(f"{name} must be finite.")
        elif not (
            isinstance(value, str) or (value is None and name in {"owner_name", "model", "fast_model"})
        ):
            raise SettingsInputError(f"{name} must be a JSON string.")

    try:
        return Settings(**values).validate()
    except ValueError as error:
        # Conversion passed above, so these are path-neutral URL validation messages.
        raise SettingsInputError(str(error)) from None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 JSON settings")
    args = parser.parse_args()
    try:
        settings = _normalize(_load_settings(args.input))
    except SettingsInputError as error:
        parser.exit(2, f"{error}\n")
    except OSError:
        parser.exit(2, "Could not read the saved settings.\n")
    print(json.dumps(asdict(settings), sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
