"""Preserved selected maintenance fixtures; unrelated transfer fixtures are excluded."""
from datetime import date
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("original_maintenance_runtime", ROOT / "maintenance.py")
maintenance = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(maintenance)


class MaintenanceTests(unittest.TestCase):
    def request(self, **changes):
        value = dict(
            action="restart",
            state="running",
            players=0,
            observation_age_seconds=0,
            maximum_age_seconds=60,
            cooldown_remaining_seconds=0,
            previous_attempt="completed",
            target_verified=True,
            backup_verified=True,
        )
        value.update(changes)
        return value

    def test_restart_has_ordered_save_stop_backup_start_checks(self):
        result = maintenance.maintenance_plan(self.request())
        steps = result["steps"]
        self.assertEqual(result["status"], "PLAN_READY")
        self.assertFalse(result["execution_performed"])
        self.assertLess(steps.index("verify_stopped"), steps.index("refresh_backup"))
        self.assertLess(steps.index("verify_backup_pin"), steps.index("start"))

    def test_unknown_players_block_plan(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(players=None))["status"],
            "PLAYER_COUNT_UNKNOWN",
        )

    def test_present_players_defer_plan(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(players=1))["status"],
            "PLAYERS_PRESENT",
        )

    def test_stale_or_missing_observation_blocks_plan(self):
        for age in (None, 61):
            self.assertEqual(
                maintenance.maintenance_plan(self.request(observation_age_seconds=age))[
                    "status"
                ],
                "OBSERVATION_STALE_OR_MISSING",
            )

    def test_incomplete_attempt_requires_review(self):
        for status in ("incomplete", "unknown"):
            self.assertEqual(
                maintenance.maintenance_plan(self.request(previous_attempt=status))[
                    "status"
                ],
                "REVIEW_PREVIOUS_ATTEMPT",
            )

    def test_unverified_target_and_unknown_state_block(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(target_verified=False))["status"],
            "TARGET_NOT_VERIFIED",
        )
        self.assertEqual(
            maintenance.maintenance_plan(self.request(state="unknown"))["status"],
            "STATE_NOT_ESTABLISHED",
        )

    def test_cooldown_defers_plan(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(cooldown_remaining_seconds=1))[
                "status"
            ],
            "COOLDOWN_PENDING",
        )

    def test_updates_and_backups_need_stopped_state(self):
        for action in ("update", "backup"):
            self.assertEqual(
                maintenance.maintenance_plan(self.request(action=action))["status"],
                "STOP_REQUIRED",
            )

    def test_update_and_restart_need_verified_backup(self):
        for action in ("update", "restart"):
            self.assertEqual(
                maintenance.maintenance_plan(
                    self.request(action=action, state="stopped", backup_verified=False)
                )["status"],
                "VERIFIED_BACKUP_REQUIRED",
            )

    def test_contradictory_stopped_players_refused(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(state="stopped", players=1))[
                "status"
            ],
            "OBSERVATION_INCONSISTENT",
        )

    def test_boolean_integer_and_unknown_fields_rejected(self):
        for changes in (
            {"players": False},
            {"maximum_age_seconds": 0},
            {"extra": True},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(maintenance.PlanError),
            ):
                maintenance.maintenance_plan(self.request(**changes))

    def test_start_running_and_stop_stopped_are_no_actions(self):
        self.assertEqual(
            maintenance.maintenance_plan(self.request(action="start"))["status"],
            "NO_ACTION",
        )
        self.assertEqual(
            maintenance.maintenance_plan(self.request(action="stop", state="stopped"))[
                "status"
            ],
            "NO_ACTION",
        )

    def test_readiness_needs_all_observations(self):
        value = dict(
            target_verified=True,
            new_instance=True,
            fresh_log_markers=True,
            probe_succeeded=True,
        )
        self.assertEqual(
            maintenance.readiness_rule(value)["status"], "OBSERVATIONS_COMPLETE"
        )
        value["new_instance"] = False
        self.assertEqual(maintenance.readiness_rule(value)["status"], "NOT_ESTABLISHED")

    def test_first_weekday_handles_leap_month_and_year_boundary(self):
        self.assertEqual(maintenance.first_weekday(2024, 2, 3), date(2024, 2, 1))
        result = maintenance.schedule_window(2026, 12, 3, 14)
        self.assertEqual(result["anchor"], "2026-12-03")
        self.assertEqual(result["next_anchor"], "2027-01-07")

    def test_overlapping_offsets_and_bad_dates_rejected(self):
        for args in ((2026, 13, 3, 14), (2026, 2, 3, 0), (2026, 2, 8, 14)):
            with self.subTest(args=args), self.assertRaises(maintenance.PlanError):
                maintenance.schedule_window(*args)
        with self.assertRaises(maintenance.PlanError):
            maintenance.schedule_window(2021, 2, 0, 28)


if __name__ == "__main__":
    unittest.main()
