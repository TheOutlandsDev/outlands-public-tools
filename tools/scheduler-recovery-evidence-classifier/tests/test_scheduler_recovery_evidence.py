import unittest

from scheduler_recovery_evidence import classify_recovery


class SchedulerRecoveryTests(unittest.TestCase):
    def test_stale_logon_recovery_failure_becomes_advisory_after_success(self) -> None:
        tasks = [
            {
                "name": "ExampleRecoverAtLogon", "enabled": True,
                "state": "Ready", "last_run": "2020-01-02T21:31:00Z",
                "last_result": "0x00000001",
            },
            {
                "name": "ExampleDailyRestart", "enabled": True,
                "state": "Ready", "last_run": "2020-01-03T08:00:00Z",
                "last_result": "0x00000000",
            },
        ]
        program = classify_recovery("online", True, ["ExampleRecoverAtLogon", "ExampleDailyRestart"], tasks)
        self.assertEqual(program["status"], "healthy")
        self.assertEqual(program["automation_status"], "advisory")
        self.assertEqual(program["automation_issues"], [])
        self.assertIn("superseded", program["automation_notices"][0])
        failed_task = next(
            task for task in program["tasks"]
            if task["name"] == "ExampleRecoverAtLogon"
        )
        self.assertFalse(failed_task["healthy"])
