from datetime import UTC, datetime, timedelta
from pathlib import Path

from outbound_projection_health import worker_is_healthy


NOW = datetime(2026, 8, 31, 16, 0, tzinfo=UTC)
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "fictional-status.json"


def test_health_gate_rejects_missing_stale_and_malformed_state(tmp_path: Path) -> None:
    path = tmp_path / "health.json"
    assert not worker_is_healthy(path, now=NOW, max_age_seconds=30)
    path.write_text("not-json", encoding="utf-8")
    assert not worker_is_healthy(path, now=NOW, max_age_seconds=30)
    path.write_bytes(EXAMPLE.read_bytes())
    assert worker_is_healthy(path, now=NOW + timedelta(seconds=29), max_age_seconds=30)
    assert not worker_is_healthy(path, now=NOW + timedelta(seconds=31), max_age_seconds=30)
