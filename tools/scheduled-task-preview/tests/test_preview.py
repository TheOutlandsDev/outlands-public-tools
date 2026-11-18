"""Qualification of fixed offsets and saved task input."""

from __future__ import annotations

import unittest

from scheduled_task_preview.preview import build_preview


def _task(**details: object) -> dict:
    return {"name": "Fictional task", "installed": True, "enabled": True, **details}


class ScheduledTaskPreviewTests(unittest.TestCase):
    def test_omits_disabled_and_uninstalled_tasks(self) -> None:
        result = build_preview(
            {
                "tasks": [
                    _task(name="Excluded disabled task", enabled=False, next_run="unused"),
                    _task(name="Excluded uninstalled task", installed=False),
                    _task(name="Included task", state="Running", next_run="unused"),
                ]
            },
            display_offset="Z",
        )

        self.assertEqual(result["schedule"], "Included task: RUNNING")
        self.assertEqual(
            build_preview({"tasks": [_task(enabled=False)]}, display_offset="Z")["schedule"],
            "No timed controller",
        )

    def test_rejects_naive_and_malformed_timestamps(self) -> None:
        for invalid in ("2040-01-01T12:00:00", "fictional invalid time", 2040, []):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "next_run must be .* with a UTC offset"):
                    build_preview({"tasks": [_task(next_run=invalid)]}, display_offset="Z")

    def test_formats_warning_and_restart_across_date_rollover(self) -> None:
        result = build_preview(
            {
                "tasks": [
                    _task(
                        label="Restart",
                        next_run="2040-01-01T18:25:00Z",
                        warning_minutes=15,
                    )
                ]
            },
            display_offset="+05:30",
        )

        self.assertEqual(
            result["schedule"],
            "Restart Jan 2 12:10 AM (warnings Jan 1 11:55 PM)",
        )

    def test_rejects_malformed_task_fields_and_display_offsets(self) -> None:
        for server, offset in (
            ({"tasks": {"name": "not an array"}}, "Z"),
            ({"tasks": ["not an object"]}, "Z"),
            ({"tasks": [_task(enabled="true")]}, "Z"),
            ({"tasks": [_task(warning_minutes=True)]}, "Z"),
            ({"tasks": [_task(warning_minutes=-1)]}, "Z"),
            ({"tasks": [_task(label="")]}, "Z"),
            ({"issues": "not an array"}, "Z"),
            ({}, "+24:00"),
            ({}, "+02:60"),
            ({}, "local"),
        ):
            with self.subTest(server=server, display_offset=offset):
                with self.assertRaises(ValueError):
                    build_preview(server, display_offset=offset)
