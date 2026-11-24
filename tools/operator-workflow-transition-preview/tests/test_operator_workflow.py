import pytest
from pydantic import ValidationError

from operator_transition import (
    OperatorWorkflowCommand,
    OperatorWorkflowConflict,
    resolve_operator_transition,
)


def _command(command: str, **changes) -> OperatorWorkflowCommand:
    return OperatorWorkflowCommand(
        command=command,
        expected_version=changes.pop("expected_version", 0),
        **changes,
    )


def test_operator_workflow_valid_transitions_are_explicit() -> None:
    assert resolve_operator_transition("OPEN", _command("ACKNOWLEDGE")) == "ACKNOWLEDGED"
    assert (
        resolve_operator_transition(
            "ACKNOWLEDGED",
            _command("FLAG_EXCEPTION", note="Material is unavailable", exception_code="MATERIAL_HOLD"),
        )
        == "EXCEPTION"
    )
    assert (
        resolve_operator_transition(
            "EXCEPTION",
            _command("ADD_NOTE", note="Team lead notified"),
        )
        == "EXCEPTION"
    )
    assert (
        resolve_operator_transition(
            "EXCEPTION",
            _command("RESOLVE_EXCEPTION", note="Material released"),
        )
        == "RESOLVED"
    )


def test_operator_workflow_rejects_ambiguous_or_invalid_commands() -> None:
    with pytest.raises(ValidationError):
        _command("ADD_NOTE")
    with pytest.raises(ValidationError):
        _command("FLAG_EXCEPTION", note="blocked")
    with pytest.raises(ValidationError):
        _command("ACKNOWLEDGE", exception_code="UNEXPECTED")
    with pytest.raises(ValidationError):
        _command("FLAG_EXCEPTION", note="blocked", exception_code="bad code")
    with pytest.raises(OperatorWorkflowConflict):
        resolve_operator_transition("ACKNOWLEDGED", _command("ACKNOWLEDGE"))
    with pytest.raises(OperatorWorkflowConflict):
        resolve_operator_transition(
            "OPEN",
            _command("RESOLVE_EXCEPTION", note="not currently blocked"),
        )


def test_operator_notes_are_trimmed_and_bounded() -> None:
    command = _command("ADD_NOTE", note="  Shift handoff reviewed.  ")
    assert command.note == "Shift handoff reviewed."
    with pytest.raises(ValidationError):
        _command("ADD_NOTE", note="x" * 1001)
