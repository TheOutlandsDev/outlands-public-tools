"""Check saved game NPC behavior policies offline."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
import math
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 2_000_000
PROGRAMS = ("rust", "dayz", "main_spt", "modern_warfare", "zomboid")

_FORBIDDEN_TOP_LEVEL_KEYS = {
    "command",
    "execute",
    "executable",
    "gpu_reset",
    "model_endpoint",
    "rcon",
    "restart_server",
    "start_server",
    "stop_server",
    "url",
    "write_path",
}

_POLICY_LIMITS: dict[str, tuple[float, float]] = {
    "reaction_ms": (150.0, 2_000.0),
    "aim_error_deg": (0.5, 30.0),
    "aggressiveness": (0.0, 1.0),
    "coordination": (0.0, 1.0),
    "retreat_health_percent": (1.0, 100.0),
    "pursuit_seconds": (0.0, 300.0),
    "decision_interval_ms": (100.0, 5_000.0),
    "perception_range_m": (5.0, 500.0),
}


class ComputeContractError(ValueError):
    """A saved policy violates the input contract."""


def _safe_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return value
    except OverflowError:
        return None
    try:
        converted = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(converted):
        return None
    return int(converted) if converted.is_integer() else converted


def _policy_result(
    program: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    policy = payload.get("policy", {})
    if not isinstance(policy, Mapping):
        raise ComputeContractError("policy must be a JSON object.")

    errors: list[str] = []
    warnings: list[str] = []
    normalized: dict[str, float] = {}
    unknown = sorted(set(policy).difference(_POLICY_LIMITS))
    if unknown:
        errors.append("Unsupported policy fields: " + ", ".join(unknown))

    for field, (minimum, maximum) in _POLICY_LIMITS.items():
        if field not in policy:
            continue
        number = _safe_number(policy[field])
        if number is None:
            errors.append(f"{field} must be a finite number.")
            continue
        numeric = float(number)
        normalized[field] = numeric
        if numeric < minimum or numeric > maximum:
            errors.append(
                f"{field}={numeric:g} is outside the safe design range "
                f"{minimum:g}..{maximum:g}."
            )

    if normalized.get("reaction_ms", 1_000) < 200:
        warnings.append("Reaction time is near-superhuman; validate player fairness.")
    if normalized.get("aim_error_deg", 10) < 1:
        warnings.append("Aim error is extremely low; validate player fairness.")
    if (
        normalized.get("aggressiveness", 0) > 0.9
        and normalized.get("retreat_health_percent", 100) < 10
    ):
        warnings.append(
            "High aggression with a very low retreat threshold can look robotic."
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "program": program,
        "valid": not errors,
        "normalized_policy": normalized,
        "errors": errors,
        "warnings": warnings,
        "live_activation_allowed": False,
        "requires_offline_simulation": True,
        "requires_game_specific_review": True,
        "requires_user_approval": True,
    }


def validate_behavior_policy(program: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Check a saved NPC policy and return the original policy result fields."""
    if program not in PROGRAMS:
        raise ComputeContractError("Unsupported game profile.")
    if not isinstance(payload, Mapping):
        raise ComputeContractError("Policy input must be a JSON object.")
    forbidden = sorted(_FORBIDDEN_TOP_LEVEL_KEYS.intersection(payload))
    if forbidden:
        raise ComputeContractError(
            "Offline compute payload contains forbidden execution fields: "
            + ", ".join(forbidden)
        )
    return _policy_result(program, payload)


def _unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in items:
        if key in obj:
            raise ComputeContractError("Duplicate JSON key.")
        obj[key] = value
    return obj


def _invalid_constant(_: str) -> None:
    raise ComputeContractError("Use standard JSON numbers.")


def _load_payload(path: Path) -> Any:
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise ComputeContractError("Input must be a regular JSON file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ComputeContractError("Policy input exceeds 2,000,000 bytes.")
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
    except ComputeContractError:
        raise
    except (ValueError, RecursionError) as error:
        raise ComputeContractError("Invalid UTF-8 JSON policy input.") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", choices=PROGRAMS)
    parser.add_argument("--input", required=True, type=Path, help="Saved JSON policy")
    args = parser.parse_args()
    try:
        result = validate_behavior_policy(args.program, _load_payload(args.input))
    except ComputeContractError as error:
        parser.exit(2, f"{error}\n")
    except OSError:
        parser.exit(2, "Could not read the saved policy.\n")
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
