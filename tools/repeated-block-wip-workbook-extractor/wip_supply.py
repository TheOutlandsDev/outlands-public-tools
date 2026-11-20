"""Prepare work-in-process supply from saved rows and a selected loss rule."""

from __future__ import annotations

import argparse
from decimal import Context, Decimal, MAX_EMAX, MIN_EMIN, ROUND_HALF_UP, localcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


_MAX_FILE_BYTES = 1024 * 1024
_MAX_RECORDS = 10_000


class WIPPreparationError(ValueError):
    """A saved input cannot be used to prepare WIP supply."""


class WIPNormalizationConfiguration(BaseModel):
    """Selected steps and their loss fraction."""

    early_stage_loss_rate: Decimal = Field(gt=0, lt=1, allow_inf_nan=False)
    early_stage_steps: tuple[str, ...] = Field(min_length=1, max_length=100)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_contract(self) -> WIPNormalizationConfiguration:
        normalized = tuple(step.strip() for step in self.early_stage_steps)
        if any(not step for step in normalized):
            raise ValueError("normalization step cannot be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("normalization steps must be unique")
        object.__setattr__(self, "early_stage_steps", normalized)
        return self


class FPCWIPRecord(BaseModel):
    """One saved WIP lot and its quantities."""

    source_row: int = Field(ge=5, le=_MAX_RECORDS)
    material_name: str = Field(min_length=1, max_length=120)
    priority: int | None = Field(default=None, ge=0, le=100)
    step_name: str = Field(min_length=1, max_length=256)
    product_name: str = Field(min_length=1, max_length=120)
    comment: str | None = Field(default=None, max_length=4000)
    wip_quantity: int | None = Field(default=None, ge=0)
    packaging_quantity: int | None = Field(default=None, ge=0)
    qa_far_quantity: int | None = Field(default=None, ge=0)
    pack_and_ship_quantity: int | None = Field(default=None, ge=0)
    kanban_quantity: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class PreparedWIPRecord(BaseModel):
    """One immutable prepared supply row."""

    source_row: int = Field(ge=5, le=_MAX_RECORDS)
    product: str = Field(min_length=1, max_length=120)
    lot_id: str = Field(min_length=1, max_length=120)
    current_step: str = Field(min_length=1, max_length=256)
    quantity_in_process_raw: int = Field(ge=0)
    normalization_applied: bool
    yield_loss_quantity: int = Field(ge=0)
    quantity_in_process: int = Field(ge=0)
    parts_completed: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class WIPPreparationResult(BaseModel):
    """Prepared rows, totals, and reproducible digests."""

    records: tuple[PreparedWIPRecord, ...]
    input_record_count: int = Field(ge=0, le=_MAX_RECORDS)
    affected_record_count: int = Field(ge=0, le=_MAX_RECORDS)
    zero_or_blank_wip_count: int = Field(ge=0, le=_MAX_RECORDS)
    raw_wip_total: int = Field(ge=0)
    normalized_wip_total: int = Field(ge=0)
    yield_loss_total: int = Field(ge=0)
    completed_total: int = Field(ge=0)
    row_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True)


class _SavedInput(BaseModel):
    configuration: WIPNormalizationConfiguration
    records: tuple[FPCWIPRecord, ...] = Field(max_length=_MAX_RECORDS)

    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _matlab_positive_round(value: Decimal) -> int:
    """Round a nonnegative value to the nearest integer, with ties rounded up."""

    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _yield_loss(raw_quantity: int, loss_rate: Decimal, rate_digits: int) -> int:
    if raw_quantity == 0:
        return 0
    quantity = Decimal(raw_quantity)
    if quantity.adjusted() + loss_rate.adjusted() < -2:
        return 0
    # The sum of the operand digit counts allows exact multiplication before rounding.
    precision = quantity.adjusted() + 1 + rate_digits
    with localcontext(Context(prec=precision, Emin=MIN_EMIN, Emax=MAX_EMAX)):
        return _matlab_positive_round(quantity * loss_rate)


def prepare_wip_supply(
    records: tuple[FPCWIPRecord, ...],
    configuration: WIPNormalizationConfiguration,
) -> WIPPreparationResult:
    """Prepare WIP supply without mutating input records or external state."""

    source_rows = [record.source_row for record in records]
    if len(source_rows) != len(set(source_rows)):
        raise WIPPreparationError("duplicate WIP source row")
    lot_ids = [record.material_name for record in records]
    if len(lot_ids) != len(set(lot_ids)):
        raise WIPPreparationError("duplicate WIP lot identity")

    normalized_steps = set(configuration.early_stage_steps)
    loss_rate = configuration.early_stage_loss_rate
    rate_digits = len(loss_rate.as_tuple().digits)
    prepared: list[PreparedWIPRecord] = []
    for record in records:
        raw_quantity = record.wip_quantity or 0
        applies = record.step_name in normalized_steps
        loss = _yield_loss(raw_quantity, loss_rate, rate_digits) if applies else 0
        completed = sum(
            value or 0
            for value in (
                record.packaging_quantity,
                record.qa_far_quantity,
                record.pack_and_ship_quantity,
            )
        )
        prepared.append(
            PreparedWIPRecord(
                source_row=record.source_row,
                product=record.product_name,
                lot_id=record.material_name,
                current_step=record.step_name,
                quantity_in_process_raw=raw_quantity,
                normalization_applied=applies,
                yield_loss_quantity=loss,
                quantity_in_process=raw_quantity - loss,
                parts_completed=completed,
            )
        )

    row_payload = [record.model_dump(mode="json") for record in prepared]
    return WIPPreparationResult(
        records=tuple(prepared),
        input_record_count=len(prepared),
        affected_record_count=sum(record.normalization_applied for record in prepared),
        zero_or_blank_wip_count=sum(
            record.quantity_in_process_raw == 0 for record in prepared
        ),
        raw_wip_total=sum(record.quantity_in_process_raw for record in prepared),
        normalized_wip_total=sum(record.quantity_in_process for record in prepared),
        yield_loss_total=sum(record.yield_loss_quantity for record in prepared),
        completed_total=sum(record.parts_completed for record in prepared),
        row_set_sha256=_canonical_sha256(row_payload),
        configuration_sha256=_canonical_sha256(
            configuration.model_dump(mode="json")
        ),
    )


def _ordinary_file(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise WIPPreparationError("Saved input contains duplicate JSON fields.")
    return result


def _reject_constant(_value: str) -> object:
    raise WIPPreparationError("Saved input contains an invalid JSON number.")


def _read_json(path: Path) -> object:
    try:
        selected = path.lstat()
        if not _ordinary_file(selected):
            raise WIPPreparationError("Saved input must be an ordinary file.")
        if selected.st_size > _MAX_FILE_BYTES:
            raise WIPPreparationError("Saved input exceeds the 1 MiB limit.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _ordinary_file(opened) or not os.path.samestat(selected, opened):
                raise WIPPreparationError("Saved input changed while opening.")
            content = stream.read(_MAX_FILE_BYTES + 1)
    except WIPPreparationError:
        raise
    except (OSError, ValueError):
        raise WIPPreparationError("Unable to read the saved input.") from None
    if len(content) > _MAX_FILE_BYTES:
        raise WIPPreparationError("Saved input exceeds the 1 MiB limit.")

    try:
        return json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique_fields,
            parse_constant=_reject_constant,
            parse_float=Decimal,
        )
    except WIPPreparationError:
        raise
    except (ArithmeticError, ValueError, RecursionError):
        raise WIPPreparationError("Saved input must contain valid UTF-8 JSON.") from None


def load_wip_configuration(path: Path) -> WIPNormalizationConfiguration:
    """Load a saved standalone WIP loss rule."""

    try:
        return WIPNormalizationConfiguration.model_validate(_read_json(path))
    except ValidationError:
        raise WIPPreparationError("WIP normalization configuration is invalid") from None


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise WIPPreparationError("Invalid arguments. Use --help for usage.")


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 configuration and rows JSON.")
    try:
        args = parser.parse_args(argv)
        saved = _SavedInput.model_validate(_read_json(args.input))
        result = prepare_wip_supply(saved.records, saved.configuration)
        report = json.dumps({"status": "normalized", **result.model_dump(mode="json")})
    except WIPPreparationError as error:
        sys.stderr.write(f"ERROR: {error}\n")
        return 2
    except ValidationError:
        sys.stderr.write("ERROR: Saved configuration or records have an invalid shape.\n")
        return 2
    except (ArithmeticError, ValueError):
        sys.stderr.write("ERROR: Saved input could not produce a valid report.\n")
        return 2

    sys.stdout.write(report + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
