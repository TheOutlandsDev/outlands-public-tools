"""The original direct projection test using a fictional saved plan."""

from pathlib import Path
import sys

from lot_priority import build_todays_priorities, load_saved_plan

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_plan import make_plan


def test_priority_projection_is_deterministic_and_bounded(tmp_path: Path) -> None:
    source = tmp_path / "fictional.json"
    make_plan(source)
    saved = load_saved_plan(source)
    result = build_todays_priorities(saved.plan, case_id=saved.case_id, source_status=saved.source_status)

    assert result.row_count == 4
    assert [row.priority_lot for row in result.rows] == [
        "DEMO-K4-A", "DEMO-K2-A", "DEMO-K2-B", "DEMO-K6-A",
    ]
    assert result.rows[0].risk_category == "Severe process risk"
    assert result.rows[-1].risk_category == "Next shipment"
    assert all(row.yield_percent is None for row in result.rows)
