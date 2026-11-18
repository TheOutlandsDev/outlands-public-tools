"""Preserved server-focused cases using fictional runtime observations."""

import unittest

from server_runtime.classifier import classify_servers


class OriginalServerRuntimeTests(unittest.TestCase):
    def test_scheduled_maintenance_is_warning_not_critical_outage(self) -> None:
        servers = [
            {
                "id": "demo",
                "name": "Demo",
                "status": "warning",
                "runtime_status": "maintenance",
                "observed_runtime_status": "down",
                "expected_state": "online",
                "issues": ["scheduled maintenance: Demo Daily Restart"],
                "automation_issues": [],
            }
        ]
        server = next(
            item for item in classify_servers(servers) if item.source == "server:demo"
        )

        self.assertEqual(server.severity, "warning")
        self.assertIn("SCHEDULED MAINTENANCE", server.summary)
        self.assertTrue(server.evidence["impact"].startswith("SCHEDULED MAINTENANCE"))

    def test_online_runtime_scheduler_warning_is_not_labeled_outage(self) -> None:
        servers = [
            {
                "id": "demo",
                "name": "Demo Server",
                "status": "warning",
                "runtime_status": "online",
                "automation_status": "attention",
                "issues": ["scheduler: Demo Task: state=Ready result=0x00000001"],
                "notes": "",
            }
        ]
        incident = next(
            item for item in classify_servers(servers) if item.source == "server:demo"
        )

        self.assertEqual(incident.severity, "warning")
        self.assertIn("runtime is ONLINE", incident.summary)
        self.assertTrue(incident.evidence["impact"].startswith("NO OUTAGE"))

    def test_planned_off_runtime_keeps_automation_warning_separate(self) -> None:
        servers = [
            {
                "id": "demo",
                "name": "Demo Server",
                "status": "warning",
                "runtime_status": "planned_off",
                "observed_runtime_status": "down",
                "expected_state": "planned_off",
                "automation_issues": ["scheduler: Demo Task failed"],
                "issues": ["scheduler: Demo Task failed"],
            }
        ]
        incident = next(
            item for item in classify_servers(servers) if item.source == "server:demo"
        )

        self.assertEqual(incident.severity, "warning")
        self.assertIn("runtime is PLANNED OFF", incident.summary)
        self.assertTrue(incident.evidence["impact"].startswith("NO OUTAGE"))
