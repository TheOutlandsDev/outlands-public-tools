from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from opskit.games import check_profiles, list_profiles


class GameProfileTests(unittest.TestCase):
    def test_profile_list_and_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            profiles = home / "config" / "game-profiles"
            install = home / "servers" / "demo"
            profiles.mkdir(parents=True)
            install.mkdir(parents=True)
            (install / "server.bin").write_text("demo", encoding="utf-8")
            (install / "saves").mkdir()
            (profiles / "demo.toml").write_text(
                textwrap.dedent(
                    """
                    name = "demo"
                    game = "Demo Server"
                    engine = "standalone"
                    enabled = true
                    platform = "any"
                    install_dir = "servers/demo"
                    executable = "server.bin"
                    save_paths = ["saves"]
                    ports = [27015]
                    expect_running = false
                    """
                ),
                encoding="utf-8",
            )

            listed, warnings = list_profiles(profiles)
            self.assertEqual([], warnings)
            self.assertEqual(1, listed["count"])
            checked, warnings = check_profiles(
                profiles, home, selected_name="demo"
            )
            self.assertEqual([], warnings)
            self.assertEqual("pass", checked["status"])
            self.assertEqual("pass", checked["profiles"][0]["status"])


if __name__ == "__main__":
    unittest.main()
