"""Original health URL and expected-state cases with fictional declarations."""

import unittest

from game_server_config import validate_config


class GameServerConfigOriginalTests(unittest.TestCase):
    def test_config_rejects_non_loopback(self) -> None:
        config = {
            "schema_version": 1,
            "servers": [
                {
                    "id": "fictional-non-loopback",
                    "root": "C:/Fictional/Service",
                    "health_urls": ["http://service.example/health"],
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "Non-loopback"):
            validate_config(config)

    def test_config_rejects_invalid_expected_state(self) -> None:
        config = {
            "schema_version": 1,
            "servers": [
                {
                    "id": "fictional-state",
                    "root": "C:/Fictional/Service",
                    "expected_state": "sometimes",
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "Invalid expected state"):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()
