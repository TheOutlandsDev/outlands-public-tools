from pathlib import Path

from activity_timeline import ACTIVITY_DOMAIN_CATALOG, read_snapshot, report_timeline


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "activity.json"


def test_activity_page_gives_ptl_and_manager_operational_scope() -> None:
    result = report_timeline(read_snapshot(EXAMPLE), scope="operational")
    assert result.scope == "operational"
    assert "DEMO-LOT-001" in {event.subject_id for event in result.events}
    assert "Accounts" not in {ACTIVITY_DOMAIN_CATALOG[key] for key in result.domain_counts}
    assert set(result.domain_counts) == {"os", "production", "lot_starts", "panel_flex", "logistics"}


def test_activity_page_gives_developer_full_evidence_scope() -> None:
    result = report_timeline(read_snapshot(EXAMPLE), scope="developer", domain="accounts")
    assert result.scope == "developer"
    assert "Accounts" in {ACTIVITY_DOMAIN_CATALOG[event.domain] for event in result.events}
    assert "Update Access" in {event.action for event in result.events}
    assert {"accounts", "system"}.issubset(result.domain_counts)
