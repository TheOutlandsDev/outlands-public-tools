"""Preview the local assistant route for a saved prompt."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


OPERATIONS_TOOL_NAMES = (
    "operations_status",
    "program_log_tail",
    "program_inventory",
    "program_read_file",
    "program_search_text",
    "program_control_capabilities",
    "program_control",
)
WORKSPACE_TOOL_NAMES = (
    "environment_info",
    "list_files",
    "read_file",
    "write_file",
    "replace_text",
    "make_directory",
    "move_path",
    "move_to_trash",
    "search_text",
    "run_python",
    "run_process",
)

OPERATIONS_TERMS = {
    "rust",
    "rustserver",
    "dayz",
    "cftools",
    "architect",
    "mainsp",
    "spt",
    "fika",
    "headless",
    "email service",
    "email_service",
    "stalwart",
    "iw4x",
    "mw2",
    "modern warfare",
    "zomboid",
    "project zomboid",
    "project-zomboid",
    "system monitor",
    "system-monitor",
    "env ai",
    "env-ai",
    "ollama",
    "local model",
    "scheduler",
    "scheduled task",
    "task scheduler",
    "server health",
    "listener",
    "listening port",
    "restart task",
    "runtime health",
    "all programs",
    "all systems",
    "managed programs",
    "servers",
}

OPERATIONS_ACTIONS = {
    "healthy",
    "health",
    "running",
    "online",
    "offline",
    "status",
    "process",
    "port",
    "task",
    "schedule",
    "log",
    "error",
    "warning",
    "crash",
    "uptime",
    "monitor",
    "ensure",
    "manage",
    "manager",
    "start",
    "restart",
    "recover",
    "recovery",
    "keep",
}

WORKSPACE_TERMS = {
    "workspace",
    "attached",
    "attachment",
    "file",
    "folder",
    "directory",
    "python",
    "script",
    "code",
    "project",
    "readme",
    "json",
    "xml",
    "csv",
    "git",
}

WORKSPACE_ACTIONS = {
    "create",
    "write",
    "edit",
    "change",
    "replace",
    "move",
    "rename",
    "delete",
    "remove",
    "read",
    "inspect",
    "list",
    "search",
    "find",
    "run",
    "execute",
    "test",
    "build",
    "fix",
}

CASUAL_PATTERNS = (
    r"^\s*(hi|hello|hey|good (morning|afternoon|evening))[\s!.?]*$",
    r"^\s*(thanks|thank you|thx|ok|okay|got it|sounds good)[\s!.?]*$",
    r"^\s*(who are you|what can you do|are you there)[\s!.?]*$",
)


@dataclass(frozen=True, slots=True)
class TurnRoute:
    kind: str
    label: str
    model: str
    reasoning: str | bool
    tool_names: tuple[str, ...]
    context_window: int


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def route_turn(
    user_text: str,
    *,
    main_model: str,
    fast_model: str,
    fast_routing: bool,
    main_context_window: int,
    fast_context_window: int,
    configured_reasoning: str,
    context_hint: str = "",
) -> TurnRoute:
    """Choose a model and only the tools relevant to this turn."""

    lowered = user_text.casefold()
    combined = f"{context_hint[-1000:]} {lowered}".casefold()
    operation_named = _contains_any(combined, OPERATIONS_TERMS)
    operation_action = _contains_any(lowered, OPERATIONS_ACTIONS)
    workspace_named = _contains_any(combined, WORKSPACE_TERMS)
    workspace_action = _contains_any(lowered, WORKSPACE_ACTIONS)
    attached = "[attached local file:" in lowered

    if operation_named and (operation_action or len(user_text) < 220):
        proposal_requested = _contains_any(
            lowered,
            {"fix", "patch", "draft", "create", "write", "edit", "change", "replace", "copy", "build"},
        )
        tool_names = OPERATIONS_TOOL_NAMES
        if proposal_requested or (workspace_named and workspace_action):
            tool_names = (*OPERATIONS_TOOL_NAMES, *WORKSPACE_TOOL_NAMES)
        return TurnRoute(
            kind="operations",
            label="Operations intelligence",
            model=main_model,
            reasoning="low" if configured_reasoning == "auto" else configured_reasoning,
            tool_names=tool_names,
            context_window=main_context_window,
        )

    if attached or (workspace_named and workspace_action):
        tool_names = WORKSPACE_TOOL_NAMES
        if operation_named:
            tool_names = (*WORKSPACE_TOOL_NAMES, *OPERATIONS_TOOL_NAMES)
        return TurnRoute(
            kind="workspace",
            label="Workspace agent",
            model=main_model,
            reasoning="medium"
            if configured_reasoning == "auto"
            else configured_reasoning,
            tool_names=tool_names,
            context_window=main_context_window,
        )

    is_casual = any(re.match(pattern, lowered) for pattern in CASUAL_PATTERNS)
    is_short_general = (
        len(user_text) <= 180
        and not operation_named
        and not workspace_named
        and user_text.count("\n") <= 2
    )
    if fast_routing and fast_model and (is_casual or is_short_general):
        return TurnRoute(
            kind="fast_chat",
            label="Fast local chat",
            model=fast_model,
            reasoning=False,
            tool_names=(),
            context_window=fast_context_window,
        )

    return TurnRoute(
        kind="main_chat",
        label="Main local reasoning",
        model=main_model,
        reasoning="low" if configured_reasoning == "auto" else configured_reasoning,
        tool_names=(),
        context_window=main_context_window,
    )


def infer_operations_program(text: str) -> str:
    """Resolve a named program without another model call."""

    lowered = text.casefold()
    checks = (
        ("modern_warfare", ("iw4x", "mw2", "modern warfare")),
        ("zomboid", ("zomboid", "project zomboid", "project-zomboid")),
        ("dayz", ("dayz", "cftools", "architect")),
        ("main_spt", ("mainsp", "spt", "fika", "headless")),
        ("email", ("email", "mail", "stalwart")),
        ("system_monitor", ("system monitor", "system-monitor")),
        ("env_ai", ("env ai", "env-ai", "ollama", "local model")),
        ("rust", ("rust",)),
    )
    matched = [program for program, terms in checks if any(term in lowered for term in terms)]
    return matched[0] if len(matched) == 1 else "all"


MAX_INPUT_BYTES = 2_000_000
REQUIRED_FIELDS = {
    "user_text": str,
    "main_model": str,
    "fast_model": str,
    "fast_routing": bool,
    "main_context_window": int,
    "fast_context_window": int,
    "configured_reasoning": str,
}


class PreviewInputError(ValueError):
    pass


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PreviewInputError("Duplicate JSON key.")
        result[key] = value
    return result


def _reject_constant(_constant: str) -> None:
    raise PreviewInputError("Use standard JSON values.")


def _read_input(path: Path) -> dict[str, object]:
    if path.drive.startswith(("\\", "//")) or path.is_symlink() or path.is_junction() or not path.is_file():
        raise PreviewInputError("Input must be a regular local JSON file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise PreviewInputError("Input exceeds 2,000,000 bytes.")

    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_keys,
            parse_constant=_reject_constant,
        )
    except PreviewInputError:
        raise
    except (ValueError, RecursionError) as error:
        raise PreviewInputError("Invalid UTF-8 JSON input.") from error

    if not isinstance(data, dict):
        raise PreviewInputError("Input must be a JSON object.")
    if REQUIRED_FIELDS.keys() - data.keys():
        raise PreviewInputError("Missing required input fields.")
    if data.keys() - (REQUIRED_FIELDS.keys() | {"context_hint"}):
        raise PreviewInputError("Unknown input fields.")
    for field, expected_type in REQUIRED_FIELDS.items():
        if type(data[field]) is not expected_type:
            raise PreviewInputError(f"{field} must be a JSON {expected_type.__name__}.")
    if not isinstance(data.get("context_hint", ""), str):
        raise PreviewInputError("context_hint must be a JSON string.")
    if data["main_context_window"] <= 0 or data["fast_context_window"] <= 0:
        raise PreviewInputError("Context windows must be positive integers.")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 JSON request.")
    args, extra = parser.parse_known_args()
    if extra:
        parser.error("expected --input FILE")
    try:
        data = _read_input(args.input)
    except PreviewInputError as error:
        parser.exit(2, f"{error}\n")
    except OSError:
        parser.exit(2, "Could not read the saved JSON request.\n")

    route = route_turn(**data)
    report = asdict(route)
    report["operations_program"] = (
        infer_operations_program(data["user_text"]) if route.kind == "operations" else None
    )
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
