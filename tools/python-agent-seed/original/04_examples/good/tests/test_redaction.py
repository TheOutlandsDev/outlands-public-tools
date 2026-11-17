from __future__ import annotations

from unittest import TestCase

from agent_seed_examples.redaction import REDACTED, redact_sensitive_values


class RedactionTests(TestCase):
    def test_redacts_case_and_dash_variants(self) -> None:
        result = redact_sensitive_values({"Authorization": "Bearer abc", "api-key": "123", "user": "sam"})
        self.assertEqual(result["Authorization"], REDACTED)
        self.assertEqual(result["api-key"], REDACTED)
        self.assertEqual(result["user"], "sam")
