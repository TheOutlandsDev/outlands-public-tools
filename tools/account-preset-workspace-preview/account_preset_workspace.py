"""Preview a saved account preset, assignment, and landing workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_INPUT_BYTES = 1024 * 1024
AccessLevel = Literal["standard", "power", "developer"]
AccountPreset = Literal[
    "flex_operator",
    "flex_ptl",
    "flex_engineer",
    "flex_manager",
    "custom",
]
FUNCTIONAL_ROLE_CATALOG = frozenset(('operator', 'ptl', 'engineer', 'manager', 'os_editor', 'panel_flex_operator', 'data_steward'))
LAB_SCOPE_CATALOG = frozenset(('flex', 'all'))
ACCOUNT_PRESET_CATALOG = {'flex_operator': {'access_level': 'standard',
                   'functional_roles': ('operator', 'panel_flex_operator'),
                   'lab_scopes': ('flex',)},
 'flex_ptl': {'access_level': 'power',
              'functional_roles': ('ptl', 'os_editor'),
              'lab_scopes': ('flex',)},
 'flex_engineer': {'access_level': 'power',
                   'functional_roles': ('engineer',),
                   'lab_scopes': ('flex',)},
 'flex_manager': {'access_level': 'power',
                  'functional_roles': ('manager',),
                  'lab_scopes': ('flex',)}}


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


class ApplicationUserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=80,
        pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$",
    )
    display_name: str = Field(min_length=2, max_length=120)
    account_preset: AccountPreset = "flex_operator"
    custom_access_level: Literal["standard", "power"] | None = None
    custom_functional_roles: tuple[str, ...] = ()
    active: bool = True

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("custom_functional_roles")
    @classmethod
    def validate_custom_functional_roles(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(values))
        if any(value not in FUNCTIONAL_ROLE_CATALOG for value in normalized):
            raise ValueError("A custom functional role is not recognized.")
        return normalized

    @model_validator(mode="after")
    def validate_preset_contract(self) -> "ApplicationUserCreate":
        if self.account_preset == "custom":
            if self.custom_access_level is None:
                raise ValueError("Custom accounts require an access level.")
            UserAccessUpdate(
                access_level=self.custom_access_level,
                functional_roles=self.custom_functional_roles,
                lab_scopes=("flex",),
                active=self.active,
            )
        elif self.custom_access_level is not None or self.custom_functional_roles:
            raise ValueError("Preset accounts cannot include custom assignments.")
        return self

    def access_assignment(self) -> UserAccessUpdate:
        if self.account_preset == "custom":
            assert self.custom_access_level is not None
            return UserAccessUpdate(
                access_level=self.custom_access_level,
                functional_roles=self.custom_functional_roles,
                lab_scopes=("flex",),
                active=self.active,
            )
        preset = ACCOUNT_PRESET_CATALOG[self.account_preset]
        return UserAccessUpdate(
            access_level=preset["access_level"],
            functional_roles=preset["functional_roles"],
            lab_scopes=preset["lab_scopes"],
            active=self.active,
        )


def primary_workspace_path(profile: UserAccessUpdate) -> str:
    """Return the least-surprising landing page for one effective profile."""

    roles = set(profile.functional_roles)
    if profile.access_level == "developer":
        return "/dev"
    if roles & {"ptl", "manager"}:
        return "/labs/flex/ptl-suite"
    if roles & {"os_editor", "data_steward"}:
        return "/labs/flex/planning"
    return "/labs/flex/operator-work-center"


class PresetPreview(BaseModel):
    account_preset: AccountPreset
    assignment: UserAccessUpdate
    primary_workspace: str


def preview_preset(request: ApplicationUserCreate) -> PresetPreview:
    assignment = request.access_assignment()
    return PresetPreview(
        account_preset=request.account_preset,
        assignment=assignment,
        primary_workspace=primary_workspace_path(assignment),
    )


class PreviewInputError(ValueError):
    """A saved request cannot be read."""


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise PreviewInputError("The request contains duplicate JSON fields.")
        fields[key] = value
    return fields


def read_request(path: Path) -> ApplicationUserCreate:
    if not path.is_file():
        raise PreviewInputError("The request must be a regular file.")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if not data or len(data) > MAX_INPUT_BYTES:
        raise PreviewInputError("The request is empty or exceeds its size limit.")
    payload = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_fields)
    return ApplicationUserCreate.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("request", type=Path)
    args = parser.parse_args(argv)
    try:
        result = preview_preset(read_request(args.request)).model_dump_json(indent=2)
    except PreviewInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The request is unreadable or violates the preset rules.", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
