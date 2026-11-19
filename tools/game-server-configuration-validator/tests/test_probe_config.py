"""Original player probe cases with fictional declarations."""

import unittest

from game_server_config import validate_config


def _configuration(*, host: str = "127.0.0.1", probe_type: str = "a2s") -> dict:
    return {
        "schema_version": 1,
        "servers": [
            {
                "id": "fictional-service",
                "root": "C:/Fictional/Service",
                "player_probe": {"type": probe_type, "host": host, "port": 27015},
            }
        ],
    }


class PlayerProbeConfigOriginalTests(unittest.TestCase):
    def test_player_probe_accepts_loopback(self) -> None:
        config = _configuration()
        self.assertEqual(validate_config(config), 1)
        self.assertEqual(config["servers"][0]["player_probe"]["port"], 27015)

    def test_player_probe_rejects_non_loopback(self) -> None:
        with self.assertRaisesRegex(ValueError, "Non-loopback player probe"):
            validate_config(_configuration(host="192.0.2.50"))

    def test_player_probe_rejects_unknown_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported player probe"):
            validate_config(_configuration(probe_type="unsupported"))


if __name__ == "__main__":
    unittest.main()
