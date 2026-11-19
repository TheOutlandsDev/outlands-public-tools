"""Retained original missing-evidence case with a fictional service."""

from datetime import datetime, timezone
from unittest import TestCase

from reachability_evidence import _external_state


class RemoteReachabilityOriginalTests(TestCase):
    def test_external_status_never_claims_success_without_remote_evidence(self) -> None:
        state, evidence = _external_state(
            "fictional-archive", {}, 86400,
            as_of=datetime(2042, 6, 1, 12, tzinfo=timezone.utc),
        )
        assert state == "pending"
        assert "no remote probe" in evidence
