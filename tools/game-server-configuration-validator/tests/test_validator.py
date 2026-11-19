"""Cover portable path checks, bounded ports and private diagnostics."""

import unittest

from game_server_config import validate_config


def _configuration(**server_fields) -> dict:
    server = {"id": "fictional-service", "root": "/fictional/service"}
    return {"schema_version": 1, "servers": [server | server_fields]}


class GameServerConfigValidationTests(unittest.TestCase):
    def test_accepts_ipv6_loopback_health_and_player_probe(self) -> None:
        config = _configuration(
            expected_state="planned_off",
            health_urls=["https://[::1]:8443/health"],
            player_probe={"type": "quake3", "host": "::1", "port": 27960},
        )
        self.assertEqual(validate_config(config), 1)

    def test_validates_port_boundaries(self) -> None:
        for value in (1, 65535, "65535"):
            with self.subTest(valid_player_port=value):
                self.assertEqual(
                    validate_config(_configuration(player_probe={"type": "a2s", "port": value})),
                    1,
                )
        for value in (0, -1, 65536, True, 1.5, "9" * 64, None):
            with self.subTest(invalid_player_port=value):
                with self.assertRaisesRegex(ValueError, "^Invalid player probe port$"):
                    validate_config(_configuration(player_probe={"type": "a2s", "port": value}))
        for suffix in ("1", "65535"):
            with self.subTest(valid_url_port=suffix):
                self.assertEqual(
                    validate_config(_configuration(health_urls=[f"http://localhost:{suffix}/"])),
                    1,
                )
        for suffix in ("0", "65536", "", "text"):
            with self.subTest(invalid_url_port=suffix):
                with self.assertRaisesRegex(ValueError, "^Invalid health URL port$"):
                    validate_config(_configuration(health_urls=[f"http://localhost:{suffix}/"]))

    def test_credential_diagnostics_omit_input(self) -> None:
        markers = ("fictional-user", "fixture-only-password", "fixture-only-token")
        url = f"https://{markers[0]}:{markers[1]}@localhost/health?token={markers[2]}"
        for value in (url, "https://@localhost/health", "https://:@localhost/health"):
            with self.subTest(has_userinfo=True):
                with self.assertRaisesRegex(ValueError, "^Credentials are forbidden in health URLs$") as failure:
                    validate_config(_configuration(health_urls=[value]))
                for marker in (*markers, "localhost", "fictional-service"):
                    self.assertNotIn(marker, str(failure.exception))

    def test_accepts_portable_absolute_jsonl_paths(self) -> None:
        for root, path in (
            ("/fictional/service", "/fictional/log/status.jsonl"),
            ("C:/Fictional/Service", r"D:\Fictional\Log\status.jsonl"),
        ):
            with self.subTest(root=root):
                config = _configuration(root=root, player_probe={"type": "jsonl_population", "path": path})
                self.assertEqual(validate_config(config), 1)
        for path in ("status.jsonl", "D:status.jsonl"):
            with self.subTest(relative_path=path):
                with self.assertRaisesRegex(ValueError, "^JSONL player probe path must be absolute$"):
                    validate_config(_configuration(player_probe={"type": "jsonl_population", "path": path}))


if __name__ == "__main__":
    unittest.main()
