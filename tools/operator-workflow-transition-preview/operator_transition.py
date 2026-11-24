"""Preview one operator workflow command using a saved action status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_INPUT_BYTES = 64 * 1024


OperatorCommandName = Literal[
    "ACKNOWLEDGE",
    "ADD_NOTE",
    "FLAG_EXCEPTION",
    "RESOLVE_EXCEPTION",
]


OperatorWorkflowStatus = Literal["OPEN", "ACKNOWLEDGED", "EXCEPTION", "RESOLVED"]


class OperatorWorkflowError(RuntimeError):
    """Fail-closed workflow error without database or credential details."""


class OperatorWorkflowConflict(OperatorWorkflowError):
    """Raised for stale writes or invalid state transitions."""


class OperatorWorkflowCommand(BaseModel):
    command: OperatorCommandName
    expected_version: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=1000)
    exception_code: str | None = Field(
        default=None,
        pattern=r"^[A-Z0-9][A-Z0-9_-]{1,39}$",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_command_fields(self):
        if self.command in {"ADD_NOTE", "FLAG_EXCEPTION", "RESOLVE_EXCEPTION"}:
            if self.note is None:
                raise ValueError(f"{self.command} requires a bounded note")
        if self.command == "FLAG_EXCEPTION":
            if self.exception_code is None:
                raise ValueError("FLAG_EXCEPTION requires an exception code")
        elif self.exception_code is not None:
            raise ValueError("exception_code is only valid for FLAG_EXCEPTION")
        return self


def resolve_operator_transition(
    current_status: OperatorWorkflowStatus,
    command: OperatorWorkflowCommand,
) -> OperatorWorkflowStatus:
    """Resolve one reviewed command without silently changing workflow meaning."""

    if command.command == "ADD_NOTE":
        return current_status
    if command.command == "ACKNOWLEDGE":
        if current_status != "OPEN":
            raise OperatorWorkflowConflict("Only an open action can be acknowledged.")
        return "ACKNOWLEDGED"
    if command.command == "FLAG_EXCEPTION":
        if current_status == "EXCEPTION":
            raise OperatorWorkflowConflict("The action already has an open exception.")
        return "EXCEPTION"
    if command.command == "RESOLVE_EXCEPTION":
        if current_status != "EXCEPTION":
            raise OperatorWorkflowConflict("Only an exception can be resolved.")
        return "RESOLVED"
    raise OperatorWorkflowConflict("The operator command is not supported.")


class PreviewRequest(BaseModel):
    current_status: OperatorWorkflowStatus
    change: OperatorWorkflowCommand

    model_config = ConfigDict(extra="forbid")


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise OperatorWorkflowError("The request contains duplicate JSON fields.")
        fields[key] = value
    return fields


def _read_request(path: Path) -> PreviewRequest:
    if not path.is_file():
        raise OperatorWorkflowError("The request must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise OperatorWorkflowError("The request is empty or exceeds its size limit.")
    payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields)
    return PreviewRequest.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("request", type=Path, help="Path to a saved UTF-8 JSON request")
    args = parser.parse_args(argv)
    try:
        request = _read_request(args.request)
        proposed = resolve_operator_transition(request.current_status, request.change)
    except OperatorWorkflowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The request is unreadable or invalid.", file=sys.stderr)
        return 2
    print(json.dumps({
        "command": request.change.command,
        "current_status": request.current_status,
        "proposed_status": proposed,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
