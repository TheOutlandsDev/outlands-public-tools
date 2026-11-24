from datetime import UTC, date, datetime

from order_void_carryover import _exact_void_carryover


def test_revision_import_carries_only_an_exact_void_identity() -> None:
    voided_at = datetime(2030, 9, 4, 18, 0, tzinfo=UTC)
    candidate = {
        "row_id": "b" * 24,
        "source_sheet": "P",
        "source_row": 4,
        "part_number": "DEMO-PART-1",
        "purchase_order": None,
        "po_line": None,
        "quantity": 100,
        "commit_date": date(2030, 9, 17),
    }
    previous = {
        **candidate,
        "revision_sha256": "a" * 64,
        "row_version": 2,
        "voided_at": voided_at,
        "voided_by": "Demo Reviewer",
        "void_reason": "Fictional review voided this sample order.",
    }

    carried = _exact_void_carryover(previous, candidate)

    assert carried == {
        "row_version": 2,
        "voided_at": voided_at,
        "voided_by": "Demo Reviewer",
        "void_reason": "Fictional review voided this sample order.",
        "previous_revision_sha256": "a" * 64,
    }
    for field, replacement in (
        ("row_id", "0" * 24),
        ("source_row", 5),
        ("part_number", "DEMO-PART-2"),
        ("quantity", 101),
        ("commit_date", date(2030, 9, 18)),
    ):
        assert not _exact_void_carryover(
            previous,
            {**candidate, field: replacement},
        )
    assert not _exact_void_carryover(
        {**previous, "voided_at": None},
        candidate,
    )
