"""Reconcile a saved lot-start queue with declared last-lot mappings."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from datetime import date
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Literal, Protocol, TextIO

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


_MAX_INPUT_BYTES = 256 * 1024
_MAX_ROWS = 1_024


class AutomaticLotIdentityError(ValueError):
    """Raised when a queued recommendation cannot be tied to a safe identity."""


class LotStartPolicyError(ValueError):
    """Raised when a standard lot sequence cannot be calculated."""


class AutomaticLotStartQueueView(Protocol):
    modality: str
    part_number: str
    lot_prefix: str
    recommended_lot_count: int
    recommended_start_by: date | None
    queue_status: Literal["ACTIVE", "CLEAR"]


class LastLotMapping(BaseModel):
    product: str | None
    material_template: str | None
    prefix: str
    last_lot_started: str
    next_lot_to_start: str

    model_config = ConfigDict(frozen=True)


class AutomaticLotIdentityRow(BaseModel):
    modality: str
    product_group: str | None
    material_template: str | None
    lot_prefix: str
    last_lot_started: str
    next_lot_to_start: str
    recommended_lot_ids: tuple[str, ...]
    recommended_lot_count: int
    queue_status: Literal["ACTIVE", "CLEAR", "REFERENCE_ONLY"]

    model_config = ConfigDict(frozen=True)


class _SavedQueueRow(BaseModel):
    modality: str
    part_number: str
    lot_prefix: str
    recommended_lot_count: int
    recommended_start_by: date | None = None
    queue_status: Literal["ACTIVE", "CLEAR"]

    @field_validator("recommended_start_by", mode="before")
    @classmethod
    def _parse_date(cls, value: object) -> object:
        if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return date.fromisoformat(value)
        return value


class _SavedInputs(BaseModel):
    queue: list[_SavedQueueRow] = Field(max_length=_MAX_ROWS)
    last_lots: list[LastLotMapping] = Field(max_length=_MAX_ROWS)


def _letters_to_number(value: str) -> int:
    result = 0
    for character in value:
        result = result * 26 + (ord(character) - ord("A"))
    return result


def _number_to_letters(value: int, *, width: int = 4) -> str:
    if value < 0 or value >= 26**width:
        raise LotStartPolicyError("The standard lot sequence is exhausted.")
    characters = ["A"] * width
    for index in range(width - 1, -1, -1):
        characters[index] = chr(ord("A") + value % 26)
        value //= 26
    return "".join(characters)


def propose_standard_lot_ids(
    *,
    lot_prefix: str,
    observed_lot_ids: Iterable[str],
    count: int,
) -> tuple[str, ...]:
    """Propose sequential identities after the supplied standard lot IDs."""

    if not re.fullmatch(r"[A-Z0-9-]{3,20}", lot_prefix):
        raise LotStartPolicyError("The lot prefix is invalid.")
    if count < 0 or count > 100:
        raise LotStartPolicyError("The proposed lot count is outside the bounded limit.")
    if count == 0:
        return ()
    pattern = re.compile(rf"^{re.escape(lot_prefix)}([A-Z]{{4}})$")
    standard_sequences: list[int] = []
    for raw_lot_id in observed_lot_ids:
        lot_id = str(raw_lot_id).strip().upper()
        match = pattern.fullmatch(lot_id)
        if match:
            standard_sequences.append(_letters_to_number(match.group(1)))
    if not standard_sequences:
        raise LotStartPolicyError(
            "No standard historical lot identity is available for safe sequencing."
        )
    next_sequence = max(standard_sequences) + 1
    return tuple(
        f"{lot_prefix}{_number_to_letters(next_sequence + offset)}"
        for offset in range(count)
    )


def _reference_modality(prefix: str) -> str:
    if prefix.startswith("P") and len(prefix) > 1:
        return prefix[1:]
    return prefix


def build_automatic_lot_identity_rows(
    queue: Iterable[AutomaticLotStartQueueView],
    last_lots: Iterable[LastLotMapping],
) -> tuple[AutomaticLotIdentityRow, ...]:
    """Join the queue to the declared last-lot sequence, failing closed."""

    queue_items = tuple(queue)
    queue_by_prefix = {item.lot_prefix: item for item in queue_items}
    if len(queue_by_prefix) != len(queue_items):
        raise AutomaticLotIdentityError("The saved lot-start queue contains duplicate prefixes.")

    mappings = tuple(last_lots)
    mapping_prefixes = {item.prefix for item in mappings}
    if len(mapping_prefixes) != len(mappings):
        raise AutomaticLotIdentityError("The saved last-lot mappings contain duplicate prefixes.")
    if set(queue_by_prefix) - mapping_prefixes:
        raise AutomaticLotIdentityError(
            "A queued modality has no controlled last-lot mapping."
        )

    rows: list[AutomaticLotIdentityRow] = []
    try:
        for mapping in mappings:
            calculated_next = propose_standard_lot_ids(
                lot_prefix=mapping.prefix,
                observed_lot_ids=(mapping.last_lot_started,),
                count=1,
            )[0]
            if calculated_next != mapping.next_lot_to_start:
                raise AutomaticLotIdentityError(
                    "A controlled next-lot value does not match the sequence rule."
                )

            queue_item = queue_by_prefix.get(mapping.prefix)
            if queue_item is not None and mapping.product:
                if mapping.product.upper() != queue_item.part_number.upper():
                    raise AutomaticLotIdentityError(
                        "A queued product does not match its controlled lot mapping."
                    )
            recommended_ids = (
                propose_standard_lot_ids(
                    lot_prefix=mapping.prefix,
                    observed_lot_ids=(mapping.last_lot_started,),
                    count=queue_item.recommended_lot_count,
                )
                if queue_item is not None
                else ()
            )
            rows.append(
                AutomaticLotIdentityRow(
                    modality=(
                        queue_item.modality
                        if queue_item is not None
                        else _reference_modality(mapping.prefix)
                    ),
                    product_group=mapping.product,
                    material_template=mapping.material_template,
                    lot_prefix=mapping.prefix,
                    last_lot_started=mapping.last_lot_started,
                    next_lot_to_start=mapping.next_lot_to_start,
                    recommended_lot_ids=recommended_ids,
                    recommended_lot_count=(
                        queue_item.recommended_lot_count if queue_item is not None else 0
                    ),
                    queue_status=(
                        queue_item.queue_status
                        if queue_item is not None
                        else "REFERENCE_ONLY"
                    ),
                )
            )
    except LotStartPolicyError as exc:
        raise AutomaticLotIdentityError(
            "The controlled lot sequence cannot be calculated safely."
        ) from exc
    return tuple(rows)


def _is_regular(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise AutomaticLotIdentityError("The saved input contains a duplicate JSON field.")
    return result


def _read_input(path: Path) -> _SavedInputs:
    try:
        selected = path.lstat()
        if not _is_regular(selected):
            raise AutomaticLotIdentityError("The saved input must be an ordinary file.")
        if selected.st_size > _MAX_INPUT_BYTES:
            raise AutomaticLotIdentityError("The saved input exceeds the 256 KiB limit.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _is_regular(opened) or not os.path.samestat(selected, opened):
                raise AutomaticLotIdentityError("The saved input changed while opening.")
            data = stream.read(_MAX_INPUT_BYTES + 1)
    except AutomaticLotIdentityError:
        raise
    except (OSError, ValueError):
        raise AutomaticLotIdentityError("Unable to read the saved input.") from None
    if len(data) > _MAX_INPUT_BYTES:
        raise AutomaticLotIdentityError("The saved input exceeds the 256 KiB limit.")

    try:
        decoded = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    except AutomaticLotIdentityError:
        raise
    except (ValueError, RecursionError):
        raise AutomaticLotIdentityError("The saved input must contain valid UTF-8 JSON.") from None
    try:
        return _SavedInputs.model_validate(decoded, strict=True, extra="forbid")
    except ValidationError:
        raise AutomaticLotIdentityError("The saved queue or last-lot mapping has an invalid shape.") from None


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise AutomaticLotIdentityError("Invalid arguments. Use --help for usage.")


def main(
    argv: list[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    parser = _ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 queue and mappings JSON.")
    try:
        args = parser.parse_args(argv)
        saved = _read_input(args.input)
        rows = build_automatic_lot_identity_rows(saved.queue, saved.last_lots)
    except AutomaticLotIdentityError as error:
        errors.write(f"ERROR: {error}\n")
        return 2

    json.dump({"status": "reconciled", "row_count": len(rows), "rows": [
        row.model_dump(mode="json") for row in rows
    ]}, output)
    output.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
