"""Classify lifecycle states from saved account flags."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Literal

from pydantic import BaseModel, Field, StrictBool, model_validator


MAX_INPUT_BYTES = 16 * 1024 * 1024
AccountLifecycleState = Literal[
    "inactive", "pending_first_sign_in", "password_reset_required", "active"
]
STATES: tuple[AccountLifecycleState, ...] = (
    "inactive", "pending_first_sign_in", "password_reset_required", "active"
)


def account_lifecycle_state(user_or_row: Any) -> AccountLifecycleState:
    getter = (
        user_or_row.get
        if isinstance(user_or_row, dict)
        else lambda key, default=None: getattr(user_or_row, key, default)
    )
    if not bool(getter("active", False)):
        return "inactive"
    if bool(getter("password_change_required", False)):
        if getter("password_changed_at", None) is None:
            return "pending_first_sign_in"
        return "password_reset_required"
    return "active"


class SavedAccount(BaseModel):
    account_id: str = Field(min_length=1, max_length=80)
    active: StrictBool = False
    password_change_required: StrictBool = False
    password_changed_at: str | None = Field(default=None, min_length=1, max_length=80)


class SavedAccounts(BaseModel):
    accounts: tuple[SavedAccount, ...]

    @model_validator(mode="after")
    def validate_account_ids(self):
        if len({row.account_id for row in self.accounts}) != len(self.accounts):
            raise ValueError("The snapshot contains duplicate account IDs.")
        return self


class ClassifiedAccount(BaseModel):
    account_id: str
    state: AccountLifecycleState


class LifecycleReport(BaseModel):
    counts: dict[AccountLifecycleState, int]
    accounts: tuple[ClassifiedAccount, ...]


def report_lifecycle(snapshot: SavedAccounts) -> LifecycleReport:
    counts = dict.fromkeys(STATES, 0)
    accounts = []
    for row in snapshot.accounts:
        state = account_lifecycle_state(row)
        counts[state] += 1
        accounts.append(ClassifiedAccount(account_id=row.account_id, state=state))
    return LifecycleReport(counts=counts, accounts=tuple(accounts))


class LifecycleInputError(ValueError):
    """A saved account snapshot cannot be read."""


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise LifecycleInputError("The snapshot contains duplicate JSON fields.")
        fields[key] = value
    return fields


def read_snapshot(path: Path) -> SavedAccounts:
    if not path.is_file():
        raise LifecycleInputError("The snapshot must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise LifecycleInputError("The snapshot is empty or exceeds its size limit.")
    return SavedAccounts.model_validate(
        json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args(argv)
    try:
        output = report_lifecycle(read_snapshot(args.snapshot)).model_dump_json(indent=2)
    except LifecycleInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The saved snapshot is unreadable or invalid.", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
