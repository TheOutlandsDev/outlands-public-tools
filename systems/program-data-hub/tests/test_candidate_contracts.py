from __future__ import annotations

import unittest
from pathlib import Path

from program_data.mes_policy import (
    RuntimeGuardrails,
    validate_query_contract,
)


class CandidateContractTests(unittest.TestCase):
    def test_fictional_candidate_is_blocked_without_fresh_evidence(self) -> None:
        root = Path(__file__).resolve().parents[1]
        contract = (
            root
            / "query_contracts"
            / "demo-movement.query-contract.json"
        )

        report = validate_query_contract(
            contract,
            project_root=root,
            guardrails=RuntimeGuardrails(),
        )

        self.assertFalse(report.static_gate_passed)
        self.assertEqual(
            set(report.errors),
            {
                (
                    "Risk class C is not app-wiring eligible; only Class A "
                    "may pass this gate."
                ),
                (
                    "The contract must confirm a read-only production MES "
                    "test."
                ),
                (
                    "The contract must confirm useful rows for a known test "
                    "case."
                ),
                (
                    "Elapsed validation time must include connection, "
                    "execution, fetch, and raw local write."
                ),
                "Validated full-refresh time must be under 300 seconds.",
                (
                    "validation.known_test_case_row_count must be greater "
                    "than zero."
                ),
                (
                    "Known test-case row count is outside the documented "
                    "expected range."
                ),
            },
        )
        self.assertEqual(
            report.query_sha256,
            "e01a8fb2ef932a61a365c943927a05da5ed7f237b402e863974cd0cd4d8157fa",
        )
        self.assertIsNotNone(report.evidence_path)


if __name__ == "__main__":
    unittest.main()
