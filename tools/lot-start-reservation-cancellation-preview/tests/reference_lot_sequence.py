"""Test-only sequencing logic from the published Lot-Start Candidate Calculator."""

import re
from typing import Iterable


class LotStartPolicyError(ValueError):
    """Raised when a lot-start candidate cannot be produced safely."""


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
    """Propose identities after all observed and non-reusable reservations."""

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
