"""Validated backend contract for persistent operator workflow actions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class OperatorActionIdentity(BaseModel):
    action_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    part_number: str = Field(min_length=1, max_length=40)
    order_id: str = Field(min_length=1, max_length=80)
    lot_id: str = Field(min_length=1, max_length=80)
    kanban: int = Field(ge=1, le=6)
    operation: str = Field(min_length=1, max_length=256)

    model_config = ConfigDict(frozen=True, extra="forbid")


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


class OperatorWorkflowState(BaseModel):
    action_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    part_number: str = Field(min_length=1, max_length=40)
    order_id: str = Field(min_length=1, max_length=80)
    lot_id: str = Field(min_length=1, max_length=80)
    kanban: int = Field(ge=1, le=6)
    operation: str = Field(min_length=1, max_length=256)
    status: OperatorWorkflowStatus
    latest_note: str | None = Field(default=None, max_length=1000)
    exception_code: str | None = Field(default=None, max_length=40)
    row_version: int = Field(ge=0)
    updated_at: datetime | None = None
    updated_by: str | None = Field(default=None, max_length=80)

    model_config = ConfigDict(frozen=True)


class OperatorWorkflowEvent(BaseModel):
    event_id: str
    action_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    occurred_at: datetime
    actor: str = Field(min_length=1, max_length=80)
    actor_role: str = Field(min_length=1, max_length=20)
    command: OperatorCommandName
    from_status: OperatorWorkflowStatus
    to_status: OperatorWorkflowStatus
    note: str | None = Field(default=None, max_length=1000)
    exception_code: str | None = Field(default=None, max_length=40)
    row_version: int = Field(gt=0)
    correlation_id: str

    model_config = ConfigDict(frozen=True)


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
