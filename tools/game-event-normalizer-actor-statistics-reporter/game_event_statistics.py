"""Normalize saved game events and report descriptive actor statistics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SCHEMA_VERSION = 1
MAX_RECORDS = 10_000
MAX_INPUT_BYTES = 2_000_000

COMPUTE_FUNCTIONS = ("normalize_events", "build_behavior_features")

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


def _tokens(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.casefold())).strip("_")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _safe_text(value: Any, *, maximum: int = 160) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:maximum]


def _safe_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return value
    try:
        converted = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(converted):
        return None
    return int(converted) if converted.is_integer() else converted


@dataclass(frozen=True, slots=True)
class ProgramComputeProfile:
    id: str
    name: str
    aliases: tuple[str, ...]
    event_aliases: Mapping[str, str]


def _event_aliases(**groups: Sequence[str]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for canonical, values in groups.items():
        aliases[_tokens(canonical)] = canonical
        aliases.update({_tokens(value): canonical for value in values})
    return aliases


PROGRAM_COMPUTE_PROFILES: tuple[ProgramComputeProfile, ...] = (
    ProgramComputeProfile(
        id='rust',
        name='Rust',
        aliases=('rustserver',),
        event_aliases=_event_aliases(
            player_join=("player connected", "connect", "joined"),
            player_leave=("player disconnected", "disconnect", "left"),
            kill=("killed", "player kill"),
            death=("died", "player death"),
            damage=("hit", "hurt"),
            spawn=("respawn", "spawned"),
            loot=("looted", "gather"),
            raid_start=("raid started", "raid begin"),
            raid_end=("raid ended", "raid complete"),
            error=("exception", "plugin error"),
        ),
    ),
    ProgramComputeProfile(
        id='dayz',
        name='DayZ',
        aliases=('cftools',),
        event_aliases=_event_aliases(
            player_join=("player connected", "connect", "joined"),
            player_leave=("player disconnected", "disconnect", "left"),
            kill=("killed", "player kill"),
            death=("died", "player death"),
            damage=("hit", "hurt"),
            loot=("item taken", "looted"),
            raid_start=("mission start", "session start"),
            raid_end=("mission end", "session end"),
            error=("script error", "exception"),
        ),
    ),
    ProgramComputeProfile(
        id='main_spt',
        name='SPT / Fika',
        aliases=('fika', 'spt', 'tarkov'),
        event_aliases=_event_aliases(
            player_join=("client connected", "joined"),
            player_leave=("client disconnected", "left"),
            kill=("killed", "pmc kill", "scav kill"),
            death=("died", "player death"),
            damage=("hit", "hurt"),
            loot=("item looted", "pickup"),
            raid_start=("raid started", "raid begin"),
            raid_end=("raid ended", "raid complete"),
            extract=("extracted", "exfil"),
            error=("exception", "backend error"),
        ),
    ),
    ProgramComputeProfile(
        id='modern_warfare',
        name='IW4x',
        aliases=('iw4x', 'mw', 'mw2'),
        event_aliases=_event_aliases(
            player_join=("client joined", "connected"),
            player_leave=("client left", "disconnected"),
            kill=("killed", "frag"),
            death=("died", "player death"),
            damage=("hit", "hurt"),
            assist=("assisted",),
            match_start=("match started", "round start"),
            match_end=("match ended", "round end"),
            error=("script error", "exception"),
        ),
    ),
    ProgramComputeProfile(
        id='zomboid',
        name='Project Zomboid',
        aliases=('project zomboid', 'pz'),
        event_aliases=_event_aliases(
            player_join=("player connected", "connected", "joined"),
            player_leave=("player disconnected", "disconnected", "left"),
            kill=("zombie killed", "player kill"),
            death=("player died", "died"),
            damage=("hit", "injury", "hurt"),
            loot=("item looted", "container looted"),
            spawn=("spawned", "respawn"),
            error=("exception", "lua error"),
        ),
    ),
)


_PROFILE_BY_ID = {profile.id: profile for profile in PROGRAM_COMPUTE_PROFILES}
_PROFILE_ALIASES = {
    _tokens(alias): profile.id
    for profile in PROGRAM_COMPUTE_PROFILES
    for alias in (profile.id, *profile.aliases)
}


class ComputeContractError(ValueError):
    """Raised when a job violates the offline compute contract."""


class ComputeBackend:
    """Deterministic compute functions over saved telemetry."""

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        activation_enabled: bool = False,
        gpu_enabled: bool = False,
    ) -> None:
        if activation_enabled or gpu_enabled:
            raise ComputeContractError(
                "Runtime activation and GPU execution are locked until hardware gates pass."
            )
        self._now = now or (lambda: datetime.now(UTC))
        self.activation_enabled = False
        self.gpu_enabled = False

    @staticmethod
    def profile(program: str) -> ProgramComputeProfile:
        normalized = _PROFILE_ALIASES.get(_tokens(program))
        if normalized is None:
            valid = ", ".join(profile.id for profile in PROGRAM_COMPUTE_PROFILES)
            raise ComputeContractError(
                f"Unknown compute program {program!r}. Use one of: {valid}."
            )
        return _PROFILE_BY_ID[normalized]

    def plan(
        self,
        program: str,
        function: str,
        *,
        record_count: int = 0,
    ) -> dict[str, Any]:
        profile = self.profile(program)
        if function not in COMPUTE_FUNCTIONS:
            raise ComputeContractError(f"Unsupported compute function {function!r}.")
        if record_count < 0 or record_count > MAX_RECORDS:
            raise ComputeContractError(f"record_count must be between 0 and {MAX_RECORDS}.")
        return {
            "schema_version": SCHEMA_VERSION,
            "program": profile.id,
            "program_name": profile.name,
            "function": function,
            "record_count": record_count,
            "device": "cpu",
            "mode": "offline_deterministic",
            "read_only": True,
            "dry_run": True,
            "writes": [],
            "server_actions": [],
            "model_actions": [],
            "gpu_actions": [],
            "requires_approval_for_future_activation": True,
        }

    def execute(
        self,
        program: str,
        function: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = self.profile(program)
        payload_dict = dict(payload or {})
        forbidden = sorted(_FORBIDDEN_TOP_LEVEL_KEYS.intersection(payload_dict))
        if forbidden:
            raise ComputeContractError(
                "Offline compute payload contains forbidden execution fields: "
                + ", ".join(forbidden)
            )
        encoded = _canonical_json(payload_dict)
        if len(encoded) > MAX_INPUT_BYTES:
            raise ComputeContractError(
                f"Compute payload exceeds {MAX_INPUT_BYTES} encoded bytes."
            )
        if function not in COMPUTE_FUNCTIONS:
            raise ComputeContractError(f"Unsupported compute function {function!r}.")

        if function == "normalize_events":
            result = self._normalize_result(profile, payload_dict)
        else:
            result = self._feature_result(profile, payload_dict)

        job_identity = {
            "schema_version": SCHEMA_VERSION,
            "program": profile.id,
            "function": function,
            "payload_sha256": hashlib.sha256(encoded).hexdigest(),
        }
        result_sha256 = _sha256(result)
        return {
            "ok": True,
            "job_id": _sha256(job_identity)[:24],
            "generated_utc": self._now().astimezone(UTC).isoformat(),
            "contract": self.plan(
                profile.id,
                function,
                record_count=len(payload_dict.get("records", []))
                if isinstance(payload_dict.get("records", []), list)
                else 0,
            ),
            "input_sha256": job_identity["payload_sha256"],
            "result_sha256": result_sha256,
            "result": result,
            "audit": {
                "read_only": True,
                "write_performed": False,
                "network_used": False,
                "subprocess_used": False,
                "model_used": False,
                "gpu_used": False,
                "server_action_performed": False,
            },
        }

    @staticmethod
    def _records(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        records = payload.get("records", [])
        if not isinstance(records, list):
            raise ComputeContractError("records must be a JSON array.")
        if len(records) > MAX_RECORDS:
            raise ComputeContractError(f"records may contain at most {MAX_RECORDS} items.")
        if any(not isinstance(record, Mapping) for record in records):
            raise ComputeContractError("every telemetry record must be a JSON object.")
        return records

    @classmethod
    def _normalize_events(
        cls,
        profile: ProgramComputeProfile,
        records: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for sequence, record in enumerate(records):
            raw_event = next(
                (
                    record[key]
                    for key in ("event", "type", "kind", "name")
                    if key in record and record[key] is not None
                ),
                "unknown",
            )
            source_event = _safe_text(raw_event) or "unknown"
            event = profile.event_aliases.get(_tokens(source_event), "other")
            item: dict[str, Any] = {
                "sequence": sequence,
                "timestamp": _safe_text(
                    record.get("timestamp", record.get("time", record.get("ts")))
                ),
                "event": event,
                "source_event": source_event,
                "actor": _safe_text(
                    record.get("actor", record.get("player", record.get("user")))
                ),
                "target": _safe_text(record.get("target")),
                "session_id": _safe_text(
                    record.get("session_id", record.get("session"))
                ),
                "value": _safe_number(record.get("value")),
            }
            context = {
                key: _safe_text(record.get(key))
                for key in ("map", "mode", "team", "weapon")
                if _safe_text(record.get(key)) is not None
            }
            if context:
                item["context"] = context
            normalized.append(item)
        return normalized

    @classmethod
    def _normalize_result(
        cls,
        profile: ProgramComputeProfile,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        records = cls._records(payload)
        events = cls._normalize_events(profile, records)
        known = sum(event["event"] != "other" for event in events)
        return {
            "schema_version": SCHEMA_VERSION,
            "program": profile.id,
            "record_count": len(events),
            "known_event_count": known,
            "unknown_event_count": len(events) - known,
            "events": events,
            "raw_messages_retained": False,
        }

    @classmethod
    def _feature_result(
        cls,
        profile: ProgramComputeProfile,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        events = cls._normalize_events(profile, cls._records(payload))
        event_counts = Counter(event["event"] for event in events)
        actors: dict[str, Counter[str]] = defaultdict(Counter)
        actor_damage: Counter[str] = Counter()
        sessions: set[str] = set()

        for event in events:
            actor = event.get("actor")
            if actor:
                actors[actor][event["event"]] += 1
                if event["event"] == "damage" and event.get("value") is not None:
                    actor_damage[actor] += float(event["value"])
            if event.get("session_id"):
                sessions.add(event["session_id"])

        actor_rows: list[dict[str, Any]] = []
        for actor in sorted(actors, key=str.casefold):
            counts = actors[actor]
            kills = counts["kill"]
            deaths = counts["death"]
            actor_rows.append(
                {
                    "actor": actor,
                    "events": sum(counts.values()),
                    "kills": kills,
                    "deaths": deaths,
                    "assists": counts["assist"],
                    "damage": round(actor_damage[actor], 3),
                    "extracts": counts["extract"],
                    "joins": counts["player_join"],
                    "leaves": counts["player_leave"],
                    "kill_death_ratio": round(kills / max(1, deaths), 3),
                    "engagement_score": round(
                        kills * 3
                        + counts["assist"] * 1.5
                        + actor_damage[actor] * 0.01
                        + counts["loot"] * 0.25,
                        3,
                    ),
                }
            )

        known = sum(name != "other" for name in event_counts.elements())
        return {
            "schema_version": SCHEMA_VERSION,
            "program": profile.id,
            "record_count": len(events),
            "session_count": len(sessions),
            "unique_actor_count": len(actors),
            "known_event_ratio": round(known / max(1, len(events)), 4),
            "event_counts": dict(sorted(event_counts.items())),
            "actor_features": actor_rows,
            "feature_scope": "descriptive_only",
            "behavior_control_generated": False,
        }


def read_payload(path: Path) -> Mapping[str, Any]:
    try:
        if not path.is_file():
            raise OSError
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise ComputeContractError("Unable to read the telemetry input.") from None
    if len(raw) > MAX_INPUT_BYTES:
        raise ComputeContractError("The telemetry input exceeds 2,000,000 bytes.")
    try:
        payload = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        raise ComputeContractError("Invalid telemetry JSON.") from None
    if not isinstance(payload, dict):
        raise ComputeContractError("The telemetry input must be an object.")
    return payload


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field.")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("normalize", "statistics"))
    parser.add_argument("program", help="A supported game profile or alias")
    parser.add_argument("input", type=Path, help="Saved JSON telemetry")
    args = parser.parse_args()
    function = "normalize_events" if args.mode == "normalize" else "build_behavior_features"
    try:
        report = ComputeBackend().execute(args.program, function, read_payload(args.input))
        report.pop("generated_utc")
        output = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    except ComputeContractError as error:
        parser.exit(2, f"{error}\n")
    except (ValueError, OverflowError, RecursionError):
        parser.exit(2, "Telemetry contains invalid numeric or text data.\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
