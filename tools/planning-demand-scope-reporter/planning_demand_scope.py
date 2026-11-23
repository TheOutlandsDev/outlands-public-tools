"""Report in-scope and out-of-scope demand from a saved planning snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from automatic_lot_start_validation import (
    AutomaticLotStartQueueValidationError,
    validate_and_summarize_automatic_queue,
)


class SavedRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class SavedPolicy(SavedRecord):
    active: bool
    mode: str
    policy_revision: str
    policy_sha256: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    recommendation_factor: str
    configured_products: int = Field(ge=0, le=20)


class SavedRuntime(SavedRecord):
    status: SavedPolicy


class SavedOrder(SavedRecord):
    status: str
    quantity: int = Field(ge=0)
    ship_quantity: int | None = Field(default=None, ge=0)


class SavedQueueRow(SavedRecord):
    modality: str = Field(min_length=1)
    part_number: str = Field(min_length=1)
    lot_prefix: str = Field(min_length=1)
    start_quantity: int = Field(gt=0)
    remaining_demand: int = Field(ge=0)
    eligible_wip: int = Field(ge=0)
    uncovered_demand: int = Field(ge=0)
    recommended_lot_count: int = Field(ge=0)
    queue_status: Literal["ACTIVE", "CLEAR"]
    wip_source_sha256: str | None = Field(pattern=r"^[0-9a-f]{64}$")


class SavedSnapshot(SavedRecord):
    runtime: SavedRuntime
    orders: tuple[SavedOrder, ...] = Field(max_length=1000)
    queue: tuple[SavedQueueRow, ...] = Field(max_length=20)

    def list_active_orders(self, *, limit: int = 1000) -> tuple[SavedOrder, ...]:
        return self.orders[:limit]

    def list_automatic_lot_start_queue(self, *, limit: int = 20) -> tuple[SavedQueueRow, ...]:
        return self.queue[:limit]


class AuthoritativeConsumerError(ValueError):
    """Raised when a current consumer cannot prove one authoritative scope."""


class AuthoritativeConsumerRepository(Protocol):
    def list_active_orders(self, *, limit: int = 1000) -> tuple[SavedOrder, ...]: ...

    def list_automatic_lot_start_queue(
        self, *, limit: int = 20
    ) -> tuple[SavedQueueRow, ...]: ...


class AuthoritativeConsumerSnapshot(BaseModel):
    authority: str = "AUTHORITATIVE_GATE_A_ACTIVE"
    policy_revision: str
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    recommendation_factor: str
    configured_modalities: int = Field(ge=1, le=20)
    all_open_order_lines: int = Field(ge=0)
    all_open_order_demand: int = Field(ge=0)
    configured_open_demand: int = Field(ge=0)
    outside_authoritative_configuration_demand: int = Field(ge=0)
    eligible_wip: int = Field(ge=0)
    covered_by_wip: int = Field(ge=0)
    uncovered_after_wip: int = Field(ge=0)
    wip_remaining_after_demand: int = Field(ge=0)
    starts_required: int = Field(ge=0)
    wip_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    database_writes: bool = False
    comparison_only_data_included: bool = False

    model_config = ConfigDict(frozen=True, extra="forbid")


def build_authoritative_consumer_snapshot(
    runtime: SavedRuntime,
    repository: AuthoritativeConsumerRepository,
) -> AuthoritativeConsumerSnapshot:
    """Build the aggregate for the supplied active planning scope."""

    if not runtime.status.active or runtime.status.mode != "authoritative_gate_a":
        raise AuthoritativeConsumerError("The authoritative planning policy is not active.")
    if runtime.status.policy_sha256 is None:
        raise AuthoritativeConsumerError("The authoritative policy hash is unavailable.")

    orders = repository.list_active_orders(limit=1000)
    queue = repository.list_automatic_lot_start_queue(limit=20)
    summary = validate_and_summarize_automatic_queue(queue)
    if summary.configured_modalities != runtime.status.configured_products:
        raise AuthoritativeConsumerError(
            "The authoritative queue does not contain every configured modality."
        )
    if summary.wip_source_sha256 is None:
        raise AuthoritativeConsumerError("The accepted WIP source hash is unavailable.")

    # Docked and partially shipped rows retain demand. A row leaves the
    # replenishment scope only when accepted ship quantity covers the order.
    open_orders = tuple(
        order
        for order in orders
        if max(0, order.quantity - (order.ship_quantity or 0)) > 0
    )
    all_open_demand = sum(
        max(0, order.quantity - (order.ship_quantity or 0)) for order in open_orders
    )
    if all_open_demand < summary.open_order_demand:
        raise AuthoritativeConsumerError(
            "Configured demand exceeds the total active order demand."
        )

    return AuthoritativeConsumerSnapshot(
        policy_revision=runtime.status.policy_revision,
        policy_sha256=runtime.status.policy_sha256,
        recommendation_factor=runtime.status.recommendation_factor,
        configured_modalities=summary.configured_modalities,
        all_open_order_lines=len(open_orders),
        all_open_order_demand=all_open_demand,
        configured_open_demand=summary.open_order_demand,
        outside_authoritative_configuration_demand=(
            all_open_demand - summary.open_order_demand
        ),
        eligible_wip=summary.eligible_wip,
        covered_by_wip=summary.covered_by_wip,
        uncovered_after_wip=summary.uncovered_after_wip,
        wip_remaining_after_demand=summary.coverage_surplus,
        starts_required=summary.starts_required,
        wip_source_sha256=summary.wip_source_sha256,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Saved policy status, orders and lot-start queue JSON")
    args = parser.parse_args()
    try:
        snapshot = SavedSnapshot.model_validate_json(args.snapshot.read_bytes())
        report = build_authoritative_consumer_snapshot(snapshot.runtime, snapshot)
    except AuthoritativeConsumerError as error:
        print(str(error), file=sys.stderr)
        return 2
    except AutomaticLotStartQueueValidationError:
        print("The saved lot-start queue is inconsistent.", file=sys.stderr)
        return 2
    except (OSError, ValidationError, OverflowError):
        print("The saved planning snapshot is unreadable or invalid.", file=sys.stderr)
        return 2
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
