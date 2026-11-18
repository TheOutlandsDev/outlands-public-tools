"""Qualification cases for the standalone server runtime classifier."""

import hashlib
import unittest

from server_runtime.classifier import classify_servers


class ServerRuntimeClassifierTests(unittest.TestCase):
    def test_missing_runtime_status_falls_back_to_down(self) -> None:
        observations = [
            {
                "id": "example",
                "name": "Example Server",
                "status": "down",
                "issues": ["process missing"],
                "notes": "",
            }
        ]
        incident, = classify_servers(observations)

        self.assertEqual(incident.source, "server:example")
        self.assertEqual(incident.code, "health")
        self.assertEqual(incident.severity, "critical")
        self.assertEqual(incident.summary, "Example Server runtime is DOWN: process missing")
        self.assertEqual(incident.evidence["runtime_status"], "down")
        self.assertTrue(incident.evidence["impact"].startswith("OUTAGE"))
        self.assertEqual(
            incident.fingerprint,
            hashlib.sha256(
                b"server:example|health|Example Server runtime is DOWN: process missing"
            ).hexdigest(),
        )

    def test_quiet_planned_off_runtime_is_suppressed(self) -> None:
        observations = [
            {
                "id": "example",
                "name": "Example Server",
                "status": "planned_off",
                "runtime_status": "planned_off",
                "observed_runtime_status": "down",
                "expected_state": "planned_off",
                "automation_issues": [],
                "issues": [],
            },
            {
                "id": "example-healthy",
                "name": "Example Healthy Server",
                "status": "healthy",
                "runtime_status": "online",
            },
        ]
        self.assertEqual(classify_servers(observations), [])

    def test_rejects_malformed_server_rows_and_issue_arrays(self) -> None:
        server = {"id": "example", "name": "Example Server", "status": "warning"}
        cases = [
            ({"servers": []}, "servers must be an array"),
            ([None], "each server must be an object"),
            ([{"id": "example"}], "each server needs a nonempty id and name"),
            ([dict(server, issues=None)], "server issues must be arrays of strings"),
            ([dict(server, issues="warning")], "server issues must be arrays of strings"),
            ([dict(server, automation_issues=[1])], "server issues must be arrays of strings"),
            ([dict(server, runtime_status=1)], "server text fields must be strings"),
            ([dict(server, name="\ud800")], "server text must be valid Unicode"),
        ]
        for observations, error in cases:
            with self.subTest(error=error):
                with self.assertRaisesRegex(ValueError, f"^{error}$"):
                    classify_servers(observations)

    def test_unexpected_online_runtime_reports_planned_off_mismatch(self) -> None:
        observations = [
            {
                "id": "example",
                "name": "Example Server",
                "status": "warning",
                "runtime_status": "online",
                "observed_runtime_status": "online",
                "expected_state": "planned_off",
            }
        ]
        incident, = classify_servers(observations)

        self.assertEqual(incident.severity, "warning")
        self.assertIn("is ONLINE but configured PLANNED OFF", incident.summary)
        self.assertTrue(incident.evidence["impact"].startswith("STATE MISMATCH"))
        self.assertEqual(incident.evidence["expected_state"], "planned_off")
