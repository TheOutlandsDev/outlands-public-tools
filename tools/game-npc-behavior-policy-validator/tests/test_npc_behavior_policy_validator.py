import unittest

from npc_behavior_policy_validator import validate_behavior_policy


class ComputeBackendTests(unittest.TestCase):
    def test_policy_validator_rejects_unsafe_ranges_and_warns_on_robotic_mix(self) -> None:
        invalid = validate_behavior_policy(
            "rust",
            {"policy": {"reaction_ms": 50, "perception_range_m": 900}},
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual(len(invalid["errors"]), 2)

        warning = validate_behavior_policy(
            "dayz",
            {
                "policy": {
                    "reaction_ms": 180,
                    "aim_error_deg": 0.75,
                    "aggressiveness": 0.95,
                    "retreat_health_percent": 5,
                }
            },
        )
        self.assertTrue(warning["valid"])
        self.assertEqual(len(warning["warnings"]), 3)
        self.assertFalse(warning["live_activation_allowed"])
