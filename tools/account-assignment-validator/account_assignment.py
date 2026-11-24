"""Validate a saved access-level, role, and lab-scope assignment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_INPUT_BYTES = 1024 * 1024
AccessLevel = Literal["standard", "power", "developer"]
FUNCTIONAL_ROLE_CATALOG = frozenset(('operator', 'ptl', 'engineer', 'manager', 'os_editor', 'panel_flex_operator', 'data_steward'))
LAB_SCOPE_CATALOG = frozenset(('flex', 'all'))


class UserAccessUpdate(BaseModel):
    access_level: AccessLevel
    functional_roles: tuple[str, ...] = Field(default=())
    lab_scopes: tuple[str, ...] = Field(default=("flex",))
    active: bool = True

    model_config = ConfigDict(extra="forbid")

    @field_validator("functional_roles")
    @classmethod
    def validate_functional_roles(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(values))
        if any(value not in FUNCTIONAL_ROLE_CATALOG for value in normalized):
            raise ValueError("A functional role is not recognized.")
        return normalized

    @field_validator("lab_scopes")
    @classmethod
    def validate_lab_scopes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(values))
        if not normalized or any(value not in LAB_SCOPE_CATALOG for value in normalized):
            raise ValueError("At least one recognized lab scope is required.")
        if "all" in normalized and len(normalized) != 1:
            raise ValueError("All labs cannot be combined with an individual lab scope.")
        return normalized

    @model_validator(mode="after")
    def validate_developer_contract(self) -> "UserAccessUpdate":
        if self.access_level == "developer" and self.lab_scopes != ("all",):
            raise ValueError("Developer access must use the All labs scope.")
        if self.access_level != "developer" and "all" in self.lab_scopes:
            raise ValueError("All labs scope is reserved for Developer access.")
        if self.access_level == "standard" and any(
            role in {"ptl", "engineer", "manager", "os_editor", "data_steward"}
            for role in self.functional_roles
        ):
            raise ValueError("That functional role requires Power User access.")
        return self


class AssignmentInputError(ValueError):
    """A saved assignment cannot be read."""


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise AssignmentInputError("The assignment contains duplicate JSON fields.")
        fields[key] = value
    return fields


def read_assignment(path: Path) -> UserAccessUpdate:
    if not path.is_file():
        raise AssignmentInputError("The assignment must be a regular file.")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if not data or len(data) > MAX_INPUT_BYTES:
        raise AssignmentInputError("The assignment is empty or exceeds its size limit.")
    payload = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_fields)
    return UserAccessUpdate.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("assignment", type=Path, help="Saved UTF-8 JSON assignment")
    args = parser.parse_args(argv)
    try:
        result = read_assignment(args.assignment).model_dump_json(indent=2)
    except AssignmentInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The saved assignment is unreadable or violates the assignment rules.", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
