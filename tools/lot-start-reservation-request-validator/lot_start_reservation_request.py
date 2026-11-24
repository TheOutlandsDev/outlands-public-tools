"""Validate a saved lot-start reservation request and fingerprint its evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


LOT_ID_PATTERN = re.compile(r"^[A-Z0-9-]{3,40}$")


class LotIdentityEvidence(BaseModel):
    """Explicit identity sources required before proposing a new standard lot."""

    current_wip: list[str] = Field(max_length=500)
    historical_inventory: list[str] = Field(max_length=5000)
    last_lot_registry: list[str] = Field(max_length=500)
    pending_reservations: list[str] = Field(max_length=500)
    cancelled_reservations: list[str] = Field(max_length=500)
    mes_identity_lookup: list[str] = Field(max_length=500)
    mes_lookup_status: Literal["PASS", "NOT_AVAILABLE"]

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "current_wip",
        "historical_inventory",
        "last_lot_registry",
        "pending_reservations",
        "cancelled_reservations",
        "mes_identity_lookup",
    )
    @classmethod
    def normalize_lot_ids(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            lot_id = value.strip().upper()
            if not LOT_ID_PATTERN.fullmatch(lot_id):
                raise ValueError("A lot identity is invalid.")
            normalized.append(lot_id)
        return normalized


class LotStartCandidateRequest(BaseModel):
    """Bounded, read-only request for a development candidate."""

    modality: str = Field(min_length=3, max_length=12, pattern=r"^[A-Z0-9]+$")
    uncovered_demand: int = Field(ge=0, le=10_000_000)
    identity_evidence: LotIdentityEvidence

    model_config = ConfigDict(extra="forbid")


class LotStartReservationCommand(BaseModel):
    """Saved request for one idempotent reservation."""

    source_request_key: str = Field(
        min_length=8,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    candidate: LotStartCandidateRequest

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def require_positive_demand(self):
        if self.candidate.uncovered_demand <= 0:
            raise ValueError("A reservation requires positive uncovered demand.")
        return self


def identity_source_sha256(evidence: LotIdentityEvidence) -> str:
    payload = json.dumps(
        evidence.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="Saved reservation request in JSON")
    args = parser.parse_args()
    try:
        request = LotStartReservationCommand.model_validate_json(args.request.read_bytes())
    except ValidationError as error:
        message = error.errors(include_input=False, include_context=False, include_url=False)[0]["msg"]
        print(f"Invalid reservation request. {message}", file=sys.stderr)
        return 2
    except OSError:
        print("The saved request could not be read.", file=sys.stderr)
        return 2

    print(json.dumps({
        "request": request.model_dump(mode="json"),
        "evidence_sha256": identity_source_sha256(request.candidate.identity_evidence),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
