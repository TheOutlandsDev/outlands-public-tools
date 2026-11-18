"""Shared, display-safe source authority and freshness for planning reports."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict

from .system_status import new_york_time


SNAPSHOT_AGING_AFTER_HOURS = 24
SNAPSHOT_STALE_AFTER_HOURS = 72

FlexSourceId = Literal[
    "current-orders",
    "accepted-wip",
    "transfer-history",
    "frozen-comparison",
    "external-evidence",
]


class FlexDataFreshnessSource(BaseModel):
    """One source date with separate authority, freshness, and audience meaning."""

    source_id: FlexSourceId
    label: str
    status: Literal[
        "CURRENT_AUTHORITY",
        "ACCEPTED_SNAPSHOT",
        "HISTORICAL_REFERENCE",
        "FROZEN_COMPARISON",
        "PENDING_SOURCE",
        "UNAVAILABLE",
    ]
    status_label: str
    freshness: Literal[
        "CURRENT",
        "FRESH",
        "AGING",
        "STALE",
        "HISTORICAL",
        "FROZEN",
        "PENDING",
        "UNAVAILABLE",
    ]
    freshness_label: str
    effective_iso: str | None
    effective_display: str
    age_hours: int | None
    operational: bool
    warning_for_power_users: bool
    detail: str
    warning_detail: str | None = None

    model_config = ConfigDict(frozen=True, extra="forbid")


class FlexDataFreshnessView(BaseModel):
    """A page-specific projection of the shared source classifications."""

    sources: tuple[FlexDataFreshnessSource, ...]
    warning_sources: tuple[FlexDataFreshnessSource, ...]
    show_warning: bool

    model_config = ConfigDict(frozen=True, extra="forbid")


def _date_display(value: date | datetime) -> tuple[str, str]:
    if isinstance(value, datetime):
        formatted = new_york_time(value)
        return formatted["iso"], formatted["display"]
    return value.isoformat(), value.strftime("%b %d, %Y")


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _age_hours(value: datetime, evaluated_at: datetime) -> int:
    elapsed = _utc_datetime(evaluated_at) - _utc_datetime(value)
    return max(0, int(elapsed.total_seconds() // 3600))


def _unavailable_source(
    *, source_id: FlexSourceId, label: str, operational: bool
) -> FlexDataFreshnessSource:
    return FlexDataFreshnessSource(
        source_id=source_id,
        label=label,
        status="UNAVAILABLE",
        status_label="Unavailable",
        freshness="UNAVAILABLE",
        freshness_label="Unavailable",
        effective_iso=None,
        effective_display="Unavailable",
        age_hours=None,
        operational=operational,
        warning_for_power_users=operational,
        detail="No accepted source date is currently available.",
        warning_detail=(
            "Restore this operational source before relying on current metrics."
            if operational
            else None
        ),
    )


def _accepted_wip_source(
    *,
    source_revision_at: datetime | None,
    accepted_at: datetime | None,
    evaluated_at: datetime,
) -> FlexDataFreshnessSource:
    if source_revision_at is None:
        return _unavailable_source(
            source_id="accepted-wip",
            label="WIP snapshot",
            operational=True,
        )
    effective_iso, effective_display = _date_display(source_revision_at)
    age_hours = _age_hours(source_revision_at, evaluated_at)
    if age_hours > SNAPSHOT_STALE_AFTER_HOURS:
        freshness = "STALE"
        freshness_label = "Review required"
        warning = True
    elif age_hours > SNAPSHOT_AGING_AFTER_HOURS:
        freshness = "AGING"
        freshness_label = "Aging snapshot"
        warning = False
    else:
        freshness = "FRESH"
        freshness_label = "Fresh snapshot"
        warning = False
    detail = "Accepted analytical snapshot used for bounded WIP coverage."
    if accepted_at is not None:
        _, accepted_display = _date_display(accepted_at)
        detail = f"Accepted {accepted_display} for bounded WIP coverage."
    age_days = age_hours // 24
    return FlexDataFreshnessSource(
        source_id="accepted-wip",
        label="WIP snapshot",
        status="ACCEPTED_SNAPSHOT",
        status_label="Accepted snapshot",
        freshness=freshness,
        freshness_label=freshness_label,
        effective_iso=effective_iso,
        effective_display=effective_display,
        age_hours=age_hours,
        operational=True,
        warning_for_power_users=warning,
        detail=detail,
        warning_detail=(
            f"The accepted WIP source is {age_days} day"
            f"{'s' if age_days != 1 else ''} old. Confirm the physical position "
            "before making planning or completion decisions."
            if warning
            else None
        ),
    )


def build_flex_data_freshness(
    *,
    os_activated_at: datetime | None,
    wip_source_revision_at: datetime | None,
    wip_accepted_at: datetime | None,
    panel_history_accepted_at: datetime | None,
    comparison_planning_date: date | None,
    evaluated_at: datetime | None = None,
) -> tuple[FlexDataFreshnessSource, ...]:
    """Classify each source without turning history into current authority."""

    evaluated_at = evaluated_at or datetime.now(UTC)
    if os_activated_at is None:
        living_os = _unavailable_source(
            source_id="current-orders",
            label="Current orders",
            operational=True,
        )
    else:
        effective_iso, effective_display = _date_display(os_activated_at)
        living_os = FlexDataFreshnessSource(
            source_id="current-orders",
            label="Current orders",
            status="CURRENT_AUTHORITY",
            status_label="Current authority",
            freshness="CURRENT",
            freshness_label="Active revision",
            effective_iso=effective_iso,
            effective_display=effective_display,
            age_hours=None,
            operational=True,
            warning_for_power_users=False,
            detail="Active order and shipping reference.",
        )

    accepted_wip = _accepted_wip_source(
        source_revision_at=wip_source_revision_at,
        accepted_at=wip_accepted_at,
        evaluated_at=evaluated_at,
    )

    if panel_history_accepted_at is None:
        panel_history = _unavailable_source(
            source_id="transfer-history",
            label="Transfer history",
            operational=False,
        )
    else:
        effective_iso, effective_display = _date_display(panel_history_accepted_at)
        panel_history = FlexDataFreshnessSource(
            source_id="transfer-history",
            label="Transfer history",
            status="HISTORICAL_REFERENCE",
            status_label="Historical source",
            freshness="HISTORICAL",
            freshness_label="History only",
            effective_iso=effective_iso,
            effective_display=effective_display,
            age_hours=None,
            operational=False,
            warning_for_power_users=False,
            detail="Accepted transfer history for reference.",
        )

    if comparison_planning_date is None:
        ptla_comparison = _unavailable_source(
            source_id="frozen-comparison",
            label="Planning comparison",
            operational=False,
        )
    else:
        effective_iso, effective_display = _date_display(comparison_planning_date)
        ptla_comparison = FlexDataFreshnessSource(
            source_id="frozen-comparison",
            label="Planning comparison",
            status="FROZEN_COMPARISON",
            status_label="Frozen comparison",
            freshness="FROZEN",
            freshness_label="Reference only",
            effective_iso=effective_iso,
            effective_display=effective_display,
            age_hours=None,
            operational=False,
            warning_for_power_users=False,
            detail="Comparison-only planning case; never today’s action queue.",
        )

    external_evidence = FlexDataFreshnessSource(
        source_id="external-evidence",
        label="External evidence",
        status="PENDING_SOURCE",
        status_label="Pending source",
        freshness="PENDING",
        freshness_label="Not connected",
        effective_iso=None,
        effective_display="Pending authoritative interface",
        age_hours=None,
        operational=False,
        warning_for_power_users=False,
        detail="No receipt or consumption evidence is inferred or fabricated.",
    )

    return (
        living_os,
        accepted_wip,
        panel_history,
        ptla_comparison,
        external_evidence,
    )


def build_flex_data_freshness_view(
    sources: Iterable[FlexDataFreshnessSource],
    *,
    source_ids: Iterable[FlexSourceId],
    show_operational_warning: bool,
) -> FlexDataFreshnessView:
    """Select page-relevant sources while preserving the shared classification."""

    indexed = {source.source_id: source for source in sources}
    selected = tuple(indexed[source_id] for source_id in source_ids)
    warnings = tuple(source for source in selected if source.warning_for_power_users)
    return FlexDataFreshnessView(
        sources=selected,
        warning_sources=warnings,
        show_warning=show_operational_warning and bool(warnings),
    )
