from datetime import UTC, date, datetime

from production_planning.flex_data_freshness import (
    SNAPSHOT_AGING_AFTER_HOURS,
    SNAPSHOT_STALE_AFTER_HOURS,
    build_flex_data_freshness,
    build_flex_data_freshness_view,
)


def _sources(*, evaluated_at: datetime) -> tuple:
    return build_flex_data_freshness(
        os_activated_at=datetime(2000, 9, 1, 16, 0, tzinfo=UTC),
        wip_source_revision_at=datetime(2000, 9, 1, 12, 0, tzinfo=UTC),
        wip_accepted_at=datetime(2000, 9, 1, 16, 10, tzinfo=UTC),
        panel_history_accepted_at=datetime(2000, 8, 21, 17, 56, tzinfo=UTC),
        comparison_planning_date=date(2000, 8, 17),
        evaluated_at=evaluated_at,
    )


def test_flex_sources_keep_authority_snapshot_history_and_pending_separate() -> None:
    sources = _sources(evaluated_at=datetime(2000, 9, 1, 20, 0, tzinfo=UTC))

    assert [source.source_id for source in sources] == [
        "current-orders",
        "accepted-wip",
        "transfer-history",
        "frozen-comparison",
        "external-evidence",
    ]
    assert [source.status for source in sources] == [
        "CURRENT_AUTHORITY",
        "ACCEPTED_SNAPSHOT",
        "HISTORICAL_REFERENCE",
        "FROZEN_COMPARISON",
        "PENDING_SOURCE",
    ]
    assert sources[0].effective_display == "Sep 01, 2000 · 12:00:00 PM EDT"
    assert sources[1].effective_display == "Sep 01, 2000 · 08:00:00 AM EDT"
    assert sources[1].freshness == "FRESH"
    assert sources[1].age_hours == 8
    assert "Accepted Sep 01, 2000" in sources[1].detail
    assert sources[3].effective_display == "Aug 17, 2000"
    assert "never today’s action queue" in sources[3].detail
    assert sources[4].effective_iso is None
    assert sources[4].freshness == "PENDING"
    assert "inferred or fabricated" in sources[4].detail


def test_accepted_wip_age_thresholds_are_display_only_and_deterministic() -> None:
    aging = _sources(evaluated_at=datetime(2000, 9, 2, 13, 0, tzinfo=UTC))[1]
    stale = _sources(evaluated_at=datetime(2000, 9, 4, 13, 0, tzinfo=UTC))[1]

    assert SNAPSHOT_AGING_AFTER_HOURS == 24
    assert SNAPSHOT_STALE_AFTER_HOURS == 72
    assert aging.age_hours == 25
    assert aging.freshness == "AGING"
    assert aging.warning_for_power_users is False
    assert stale.age_hours == 73
    assert stale.freshness == "STALE"
    assert stale.warning_for_power_users is True
    assert "Confirm the physical position" in stale.warning_detail


def test_power_user_warning_does_not_alarm_standard_view() -> None:
    sources = _sources(evaluated_at=datetime(2000, 9, 10, 12, 0, tzinfo=UTC))
    source_ids = ("current-orders", "accepted-wip")
    standard = build_flex_data_freshness_view(
        sources,
        source_ids=source_ids,
        show_operational_warning=False,
    )
    power = build_flex_data_freshness_view(
        sources,
        source_ids=source_ids,
        show_operational_warning=True,
    )

    assert [source.source_id for source in standard.sources] == list(source_ids)
    assert [source.source_id for source in standard.warning_sources] == [
        "accepted-wip"
    ]
    assert standard.show_warning is False
    assert power.show_warning is True


def test_missing_operational_dates_fail_closed_while_pending_stays_explicit() -> None:
    sources = build_flex_data_freshness(
        os_activated_at=None,
        wip_source_revision_at=None,
        wip_accepted_at=None,
        panel_history_accepted_at=None,
        comparison_planning_date=None,
        evaluated_at=datetime(2000, 9, 18, tzinfo=UTC),
    )

    assert [source.status for source in sources[:4]] == [
        "UNAVAILABLE",
        "UNAVAILABLE",
        "UNAVAILABLE",
        "UNAVAILABLE",
    ]
    assert all(source.effective_display == "Unavailable" for source in sources[:4])
    assert sources[0].warning_for_power_users is True
    assert sources[1].warning_for_power_users is True
    assert sources[2].warning_for_power_users is False
    assert sources[4].status == "PENDING_SOURCE"
    assert sources[4].warning_for_power_users is False
