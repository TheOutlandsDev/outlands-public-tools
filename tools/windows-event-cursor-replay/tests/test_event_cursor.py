import json
from datetime import datetime

from windows_event_cursor_replay import replay


NOW = "2020-01-02T08:00:00+00:00"


def test_windows_diagnostics_cursor_prevents_restart_replay(tmp_path):
    batch = [{"channel": "System", "record_id": 101, "timestamp": NOW}]
    first = replay(None, batch, observed_at=NOW)
    cursor_file = tmp_path / "event-cursor.json"
    cursor_file.write_text(json.dumps(first["next_cursor"]), encoding="utf-8")
    restarted = replay(cursor_file.read_bytes(), batch, observed_at=NOW)

    assert [event["record_id"] for event in first["new_events"]] == [101]
    assert len(first["new_events"]) == 1
    assert restarted["new_events"] == []
    assert len(restarted["new_events"]) == 0
    assert restarted["cursor_loaded"]
    assert restarted["next_cursor"] == json.loads(cursor_file.read_bytes())


def test_windows_diagnostics_corrupt_cursor_uses_bounded_startup_window(tmp_path):
    cursor_file = tmp_path / "event-cursor.json"
    cursor_file.write_text("{invalid", encoding="utf-8")
    result = replay(cursor_file.read_bytes(), [], observed_at=NOW, startup_lookback_seconds=15)

    assert result["cursor_loaded"] is False
    before = datetime.fromisoformat(NOW)
    last_query = datetime.fromisoformat(result["last_query"])
    assert 0 <= (before - last_query).total_seconds() <= 16
