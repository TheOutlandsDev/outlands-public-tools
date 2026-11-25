"""Original in-memory calculator used by the projection parity test."""

from datetime import date, timedelta
from hashlib import sha256
import json
from math import ceil
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from automatic_lot_configuration import AutomaticLotStartConfiguration, AutomaticLotStartError


class AutomaticLotStartConflict(AutomaticLotStartError):
    """Raised when an O&S identity/version attempts conflicting replay."""


class OSOrderState(BaseModel):
    """Canonical O&S demand state consumed by the automatic calculation."""

    order_id: str = Field(min_length=8, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    row_version: int = Field(gt=0)
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    part_number: str = Field(min_length=1, max_length=40)
    ordered_quantity: int = Field(gt=0, le=10_000_000)
    accepted_ship_quantity: int = Field(ge=0, le=10_000_000)
    requested_ship_date: date
    cancelled: bool = False

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_quantity_conservation(self):
        if self.accepted_ship_quantity > self.ordered_quantity:
            raise ValueError("Accepted ship quantity cannot exceed ordered quantity.")
        return self

    @property
    def remaining_quantity(self) -> int:
        if self.cancelled:
            return 0
        return self.ordered_quantity - self.accepted_ship_quantity

    def fingerprint(self, contract_version: str) -> str:
        payload = {
            "contract_version": contract_version,
            **self.model_dump(mode="json"),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()


class ReplenishmentEvent(BaseModel):
    event_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_type: Literal["CREATE", "INCREASE", "DECREASE", "SHIPMENT", "CANCEL"]
    order_id: str
    row_version: int
    modality: str
    part_number: str
    previous_remaining_quantity: int = Field(ge=0)
    current_remaining_quantity: int = Field(ge=0)
    demand_delta: int
    previous_modality_demand: int = Field(ge=0)
    current_modality_demand: int = Field(ge=0)
    previous_recommended_lots: int = Field(ge=0)
    current_recommended_lots: int = Field(ge=0)
    recommendation_delta: int
    start_quantity: int = Field(gt=0)
    recommended_start_by: date
    authority: Literal["DEVELOPMENT_RECOMMENDATION_ONLY"] = (
        "DEVELOPMENT_RECOMMENDATION_ONLY"
    )
    database_writes: Literal[False] = False
    mes_writes: Literal[False] = False

    model_config = ConfigDict(frozen=True)


class IngestResult(BaseModel):
    applied: bool
    replay_ignored: bool
    state_changed_without_demand_change: bool
    event: ReplenishmentEvent | None
    event_count: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class AutomaticLotStartLedger:
    """In-memory reference reducer for the future transactional queue."""

    def __init__(self, configuration: AutomaticLotStartConfiguration):
        self.configuration = configuration
        self._orders: dict[str, OSOrderState] = {}
        self._fingerprints: set[str] = set()
        self._events: list[ReplenishmentEvent] = []

    @property
    def events(self) -> tuple[ReplenishmentEvent, ...]:
        return tuple(self._events)

    def modality_remaining_demand(self, modality: str) -> int:
        return sum(
            order.remaining_quantity
            for order in self._orders.values()
            if self.configuration.product_for_part(order.part_number).modality == modality
        )

    @staticmethod
    def _recommended_lots(demand: int, start_quantity: int) -> int:
        return ceil(demand / start_quantity) if demand else 0

    def ingest(self, order: OSOrderState) -> IngestResult:
        product = self.configuration.product_for_part(order.part_number)
        fingerprint = order.fingerprint(self.configuration.contract_version)
        previous = self._orders.get(order.order_id)

        if previous is not None:
            if order.row_version < previous.row_version:
                raise AutomaticLotStartConflict("An older O&S row version cannot be applied.")
            if order.row_version == previous.row_version:
                if fingerprint in self._fingerprints:
                    return IngestResult(
                        applied=False,
                        replay_ignored=True,
                        state_changed_without_demand_change=False,
                        event=None,
                        event_count=len(self._events),
                    )
                raise AutomaticLotStartConflict(
                    "The same O&S row version cannot represent different state."
                )
            previous_product = self.configuration.product_for_part(previous.part_number)
            if previous_product.modality != product.modality:
                raise AutomaticLotStartConflict(
                    "An existing O&S identity cannot change Flex modality."
                )

        previous_remaining = previous.remaining_quantity if previous else 0
        previous_modality_demand = self.modality_remaining_demand(product.modality)
        previous_lots = self._recommended_lots(
            previous_modality_demand, product.start_quantity
        )
        current_modality_demand = (
            previous_modality_demand - previous_remaining + order.remaining_quantity
        )
        current_lots = self._recommended_lots(
            current_modality_demand, product.start_quantity
        )
        demand_delta = order.remaining_quantity - previous_remaining

        if demand_delta == 0:
            self._orders[order.order_id] = order
            self._fingerprints.add(fingerprint)
            return IngestResult(
                applied=True,
                replay_ignored=False,
                state_changed_without_demand_change=True,
                event=None,
                event_count=len(self._events),
            )
        if previous is None:
            event_type = "CREATE"
        elif order.cancelled:
            event_type = "CANCEL"
        elif order.accepted_ship_quantity > previous.accepted_ship_quantity:
            event_type = "SHIPMENT"
        elif demand_delta > 0:
            event_type = "INCREASE"
        else:
            event_type = "DECREASE"
        event = ReplenishmentEvent(
            event_fingerprint=fingerprint,
            event_type=event_type,
            order_id=order.order_id,
            row_version=order.row_version,
            modality=product.modality,
            part_number=product.part_number,
            previous_remaining_quantity=previous_remaining,
            current_remaining_quantity=order.remaining_quantity,
            demand_delta=demand_delta,
            previous_modality_demand=previous_modality_demand,
            current_modality_demand=current_modality_demand,
            previous_recommended_lots=previous_lots,
            current_recommended_lots=current_lots,
            recommendation_delta=current_lots - previous_lots,
            start_quantity=product.start_quantity,
            recommended_start_by=(
                order.requested_ship_date - timedelta(days=product.lead_time_days)
            ),
        )
        self._orders[order.order_id] = order
        self._fingerprints.add(fingerprint)
        self._events.append(event)
        return IngestResult(
            applied=True,
            replay_ignored=False,
            state_changed_without_demand_change=False,
            event=event,
            event_count=len(self._events),
        )
