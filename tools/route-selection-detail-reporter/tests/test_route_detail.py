"""Four route-page tests adapted to a saved snapshot and fictional route IDs."""

import pytest

from route_detail import RouteError, report_routes


@pytest.fixture
def snapshot():
    routes = [(f"Workshop {letter}", "1", count)
              for letter, count in zip("ABCDE", [38, 40, 42, 111, 8], strict=True)]
    summaries = [dict(requested_flow_name=flow, requested_version=version,
                      occurrence_count=count) for flow, version, count in reversed(routes)]
    contract = {"routes": summaries}
    occurrences = []
    repeats = {15: "CID:15", 26: "CID:20", 28: "CID:22"}
    for flow, version, count in routes:
        for position in range(1, count + 1):
            repeat = repeats.get(position) if flow == "Workshop C" else None
            occurrences.append(dict(
                requested_flow_name=flow, requested_version=version,
                route_order_key=f"R:{position:04d}", step_position=position,
                step_name="Recheck" if repeat else "Inspect",
                step_id="ID:recheck" if repeat else f"ID:step-{position}",
                step_correlation_id=repeat or f"CID:step-{position}",
            ))
    return contract, dict(total_occurrences=239, summaries=[dict(row) for row in summaries],
                          occurrences=list(reversed(occurrences)))


def test_route_page_lists_exactly_five_validated_routes(snapshot):
    result = report_routes(*snapshot)
    assert [(row["requested_flow_name"], row["requested_version"]) for row in result["routes"]] == [
        (f"Workshop {letter}", "1") for letter in "ABCDE"
    ]
    assert result["total_occurrences"] == 239
    assert result["selected_route"] == result["routes"][0]
    assert len(result["occurrences"]) == 38


def test_selected_route_keeps_repeated_occurrences_separate(snapshot):
    result = report_routes(*snapshot, "Workshop C", "1")
    assert len(result["occurrences"]) == 42
    assert [row["step_position"] for row in result["occurrences"]] == list(range(1, 43))
    repeated = [row for row in result["occurrences"] if row["step_name"] == "Recheck"]
    assert [row["step_id"] for row in repeated] == ["ID:recheck"] * 3
    assert [row["step_correlation_id"] for row in repeated] == ["CID:15", "CID:20", "CID:22"]


def test_route_selector_rejects_partial_and_unknown_keys(snapshot):
    with pytest.raises(RouteError, match="both its flow name and version"):
        report_routes(*snapshot, flow="Workshop C")
    with pytest.raises(RouteError, match="requested route was not found"):
        report_routes(*snapshot, "Unlisted", "1")


def test_route_page_fails_closed_on_count_mismatch(snapshot):
    contract, saved = snapshot
    bad_summary = [dict(row) for row in saved["summaries"]]
    bad_summary[0]["occurrence_count"] = 7
    with pytest.raises(RouteError, match="Route summaries did not pass"):
        report_routes(contract, {**saved, "summaries": bad_summary})
    with pytest.raises(RouteError, match="Selected route did not pass"):
        report_routes(contract, {**saved, "occurrences": saved["occurrences"][:-1]})
