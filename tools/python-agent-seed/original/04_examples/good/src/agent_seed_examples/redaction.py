"""Logging redaction helpers."""

from __future__ import annotations

SENSITIVE_KEYS = frozenset({
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
})


REDACTED = "<redacted>"


def redact_sensitive_values(values: dict[str, object]) -> dict[str, object]:
    """Return a copy of a mapping with sensitive values redacted.

    Key comparison is case-insensitive and allows common dash/underscore variants.
    """
    redacted: dict[str, object] = {}
    for key, value in values.items():
        normalized = key.lower().replace("-", "_")
        redacted[key] = REDACTED if normalized in SENSITIVE_KEYS else value
    return redacted
