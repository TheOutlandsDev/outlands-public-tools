"""Original history and integrity assertions using fictional reviewers and revisions."""

from pathlib import Path

import pytest

from review_ledger import ReviewLedgerIntegrityError, SavedReviewLedger, verify_review_history


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def example(name="ledger"):
    return SavedReviewLedger.model_validate_json((EXAMPLES / f"{name}.json").read_bytes())


def test_latest_decision_controls_saved_review_state():
    ledger = example()
    rejected, returned = ledger.events
    report = verify_review_history(ledger)
    assert report.events == (returned, rejected)
    assert report.latest_decision == "AWAITING_REVIEW"
    assert report.events[0].reviewer == "Fictional reviewer"
    assert report.events[0].comment == "Fictional candidate returned for review"


def test_changed_decision_breaks_saved_event_integrity():
    ledger = example()
    changed = ledger.events[0].model_copy(update={"decision": "AWAITING_REVIEW"})
    ledger = ledger.model_copy(update={"events": (changed, ledger.events[1])})
    with pytest.raises(ReviewLedgerIntegrityError, match="integrity validation"):
        verify_review_history(ledger)


def test_matching_event_hash_does_not_allow_another_revision():
    with pytest.raises(ReviewLedgerIntegrityError, match="integrity validation"):
        verify_review_history(example("foreign-revision"))


def test_older_events_are_verified_even_when_hidden_by_limit():
    ledger = example()
    report = verify_review_history(ledger, limit=1)
    assert report.events == (ledger.events[1],)
    assert report.verified_event_count == 2
    changed = ledger.events[0].model_copy(update={"comment": "Fictional edit"})
    ledger = ledger.model_copy(update={"events": (changed, ledger.events[1])})
    with pytest.raises(ReviewLedgerIntegrityError, match="integrity validation"):
        verify_review_history(ledger, limit=1)
