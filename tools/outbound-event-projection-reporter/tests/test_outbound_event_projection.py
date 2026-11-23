from pathlib import Path
from uuid import UUID

import pytest

from outbound_event_projection import (
    HISTORY_COLUMNS,
    MAX_SOURCE_EVENTS,
    OutboundProjectionError,
    SavedProjection,
    project_outbound_events,
)


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "fictional-shipments.json"


def fictional_snapshot():
    return SavedProjection.model_validate_json(EXAMPLE.read_bytes())


def test_projection_is_idempotent_and_excludes_sensitive_fields() -> None:
    snapshot = fictional_snapshot()
    first = project_outbound_events(snapshot)
    replay_input = snapshot.model_copy(update={
        "seen_event_ids": tuple(row["event_identity"] for row in first.rows),
        "projection_run_id": UUID("00000000-0000-0000-0000-000000000002"),
    })
    replay = project_outbound_events(replay_input)

    assert first.new_event_count == 1 and first.replayed_event_count == 0
    assert replay.new_event_count == 0 and replay.replayed_event_count == 1
    assert len(first.rows) == 1 and not replay.rows
    assert first.source_event_count == replay.source_event_count == 1
    assert tuple(first.rows[0]) == HISTORY_COLUMNS
    assert first.rows[0]["lot_count"] == 2
    assert not {
        "carrier",
        "tracking_number",
        "transaction_comment",
        "transacted_by",
        "lot_ids",
        "lot_quantities",
    } & set(first.rows[0])


def test_projection_fails_closed_at_source_bound() -> None:
    snapshot = fictional_snapshot()
    event = snapshot.events[0]
    bounded = tuple(
        event.model_copy(update={"event_identity": f"{index:064x}"})
        for index in range(1, MAX_SOURCE_EVENTS + 1)
    )
    result = project_outbound_events(snapshot.model_copy(update={"events": bounded[:-1]}))
    assert result.new_event_count == MAX_SOURCE_EVENTS - 1
    with pytest.raises(OutboundProjectionError, match="bounded projection limit"):
        project_outbound_events(snapshot.model_copy(update={"events": bounded}))
