"""Preserved scheduled-task assertions using fictional task declarations."""

from __future__ import annotations

import unittest

from scheduled_task_preview.preview import build_preview


class DashboardScheduleTests(unittest.TestCase):
    def test_dayz_schedule_shows_restart_after_warning_window(self) -> None:
        server = {
            "tasks": [
                {
                    "name": "fictional-warning-controller",
                    "label": "Restart",
                    "warning_minutes": 15,
                    "installed": True,
                    "enabled": True,
                    "state": "Ready",
                    "next_run": "2040-07-28T11:45:00-04:00",
                }
            ]
        }

        rendered = build_preview(server, display_offset="-04:00")["schedule"]

        self.assertIn("Restart", rendered)
        self.assertIn("12:00 PM", rendered)
        self.assertIn("warnings", rendered)
        self.assertIn("11:45 AM", rendered)

    def test_running_restart_is_maintenance_not_an_outage(self) -> None:
        server = {
            "runtime_status": "maintenance",
            "automation_status": "ready",
            "tasks": [
                {
                    "name": "fictional-restart-controller",
                    "label": "Restart",
                    "installed": True,
                    "enabled": True,
                    "state": "Running",
                    "next_run": "2040-07-29T05:00:00-04:00",
                }
            ],
        }

        result = build_preview(server, display_offset="-04:00")

        self.assertEqual(result["runtime_status"], "maintenance")
        self.assertIn("RUNNING", result["schedule"])
        self.assertTrue(result["next_action"].startswith("No outage"))
