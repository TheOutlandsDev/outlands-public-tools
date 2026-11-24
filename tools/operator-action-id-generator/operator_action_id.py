"""Generate authoritative operator work-center action IDs from saved identities."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt

MAX_INPUT_BYTES = 2 * 1024 * 1024
SourceHash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ActionIdentity(BaseModel):
    source_revision_sha256: SourceHash
    wip_source_sha256: SourceHash
    part_number: str = Field(min_length=1, max_length=40)
    order_id: str = Field(min_length=1, max_length=80)
    lot_id: str = Field(min_length=1, max_length=80)
    kanban: StrictInt = Field(ge=1, le=6)
    operation: str = Field(min_length=1, max_length=256)

    model_config = ConfigDict(frozen=True, extra="forbid")


class ActionBatch(BaseModel):
    actions: tuple[ActionIdentity, ...]

    model_config = ConfigDict(frozen=True, extra="forbid")


def generate_action_id(action: ActionIdentity) -> str:
    identity = action.model_dump()
    return sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def action_report(batch: ActionBatch, *, product: str | None = None) -> dict:
    return {"actions": [
        {**action.model_dump(), "action_id": generate_action_id(action)}
        for action in batch.actions
        if product is None or action.part_number == product
    ]}


class ActionInputError(ValueError):
    """A saved batch cannot be read safely."""


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ActionInputError("The batch contains duplicate JSON fields.")
        fields[key] = value
    return fields


def read_actions(path: Path) -> ActionBatch:
    if not path.is_file():
        raise ActionInputError("The batch must be a regular file.")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if not data or len(data) > MAX_INPUT_BYTES:
        raise ActionInputError("The batch is empty or exceeds its size limit.")
    payload = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_fields)
    return ActionBatch.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("batch", type=Path, help="Saved UTF-8 JSON action batch")
    parser.add_argument("--product", help="Return actions with this exact part number")
    args = parser.parse_args(argv)
    try:
        report = action_report(read_actions(args.batch), product=args.product)
    except ActionInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The saved batch is unreadable or invalid.", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
