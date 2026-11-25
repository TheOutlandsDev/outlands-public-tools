"""Filter and paginate saved account-directory records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictBool, StrictInt, model_validator


MAX_INPUT_BYTES = 16 * 1024 * 1024
PAGE_SIZE = 25
AccessLevel = Literal["standard", "power", "developer"]
LabScope = Literal["", "flex", "all"]
AccountStatus = Literal["", "active", "inactive", "pending-first-sign-in", "password-reset-required"]
ShortText = Annotated[str, Field(min_length=1, max_length=80)]
LAB_SCOPE_OPTIONS = (("", "Any lab scope"), ("flex", "Flex"), ("all", "All labs"))
STATUS_LABELS = {
    "": "Any status",
    "active": "Active",
    "inactive": "Inactive",
    "pending-first-sign-in": "Pending first sign-in",
    "password-reset-required": "Password reset required",
}


class AccountRow(BaseModel):
    username: ShortText
    display_name: str = Field(min_length=1, max_length=120)
    access_level: AccessLevel
    functional_roles: tuple[ShortText, ...]
    lab_scopes: tuple[Literal["flex", "all"], ...]
    active: StrictBool
    password_change_required: StrictBool
    password_changed_at: str | None = Field(default=None, min_length=1, max_length=80)


class DirectorySnapshot(BaseModel):
    accounts: tuple[AccountRow, ...]

    @model_validator(mode="after")
    def validate_usernames(self):
        if len({row.username.lower() for row in self.accounts}) != len(self.accounts):
            raise ValueError("The snapshot contains duplicate usernames.")
        return self


class DirectoryFilters(BaseModel):
    access_level: Literal["", "standard", "power", "developer"] = ""
    functional_role: str = Field(default="", max_length=40)
    lab_scope: LabScope = ""
    account_status: AccountStatus = ""
    page: StrictInt = Field(default=1, ge=1, le=100)


class VisibleAccount(BaseModel):
    username: ShortText
    display_name: str
    access_level: AccessLevel
    functional_roles: tuple[str, ...]
    lab_scopes: tuple[str, ...]


class DirectoryPage(BaseModel):
    accounts: tuple[VisibleAccount, ...]
    total: int
    page: int
    page_size: int
    page_count: int
    status_label: str
    lab_scope_options: tuple[tuple[str, str], ...]


def filter_directory(snapshot: DirectorySnapshot, filters: DirectoryFilters) -> DirectoryPage:
    account_status = filters.account_status
    active_filter = (
        True
        if account_status
        in {"active", "pending-first-sign-in", "password-reset-required"}
        else False if account_status == "inactive"
        else None
    )
    password_change_filter = (
        True
        if account_status
        in {"pending-first-sign-in", "password-reset-required"}
        else False if account_status == "active"
        else None
    )
    password_changed_filter = (
        False
        if account_status == "pending-first-sign-in"
        else True if account_status == "password-reset-required"
        else None
    )

    rows = sorted(
        (
            row for row in snapshot.accounts
            if (not filters.access_level or row.access_level == filters.access_level)
            and (not filters.functional_role or filters.functional_role in row.functional_roles)
            and (not filters.lab_scope or filters.lab_scope in row.lab_scopes)
            and (active_filter is None or row.active is active_filter)
            and (password_change_filter is None or row.password_change_required is password_change_filter)
            and (password_changed_filter is None or (row.password_changed_at is not None) is password_changed_filter)
        ),
        key=lambda row: (row.display_name.lower(), row.username.lower()),
    )
    total = len(rows)
    start = (filters.page - 1) * PAGE_SIZE
    return DirectoryPage(
        accounts=tuple(VisibleAccount.model_validate(row, from_attributes=True)
                       for row in rows[start:start + PAGE_SIZE]),
        total=total,
        page=filters.page,
        page_size=PAGE_SIZE,
        page_count=max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
        status_label=STATUS_LABELS[account_status],
        lab_scope_options=LAB_SCOPE_OPTIONS,
    )


class DirectoryInputError(ValueError):
    """The saved directory cannot be read."""


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise DirectoryInputError("The directory contains duplicate JSON fields.")
        fields[key] = value
    return fields


def read_snapshot(path: Path) -> DirectorySnapshot:
    if not path.is_file():
        raise DirectoryInputError("The directory must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise DirectoryInputError("The directory is empty or exceeds its size limit.")
    return DirectorySnapshot.model_validate(
        json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--status", dest="account_status", default="")
    parser.add_argument("--access-level", default="")
    parser.add_argument("--functional-role", default="")
    parser.add_argument("--lab-scope", default="")
    parser.add_argument("--page", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        filters = DirectoryFilters.model_validate(
            {name: value for name, value in vars(args).items() if name != "snapshot"}
        )
        output = filter_directory(read_snapshot(args.snapshot), filters).model_dump_json(indent=2)
    except DirectoryInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The directory or filter request is invalid.", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
