from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from opskit.cli import main


class CLITests(unittest.TestCase):
    def test_game_check_human_output_includes_profile_engine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profiles = root / "config" / "game-profiles"
            profiles.mkdir(parents=True)
            (profiles / "demo.toml").write_text(
                (
                    'name = "demo"\n'
                    'game = "Demo Server"\n'
                    'engine = "standalone"\n'
                    "enabled = false\n"
                    'platform = "any"\n'
                    'install_dir = "servers/demo"\n'
                    'executable = "server.bin"\n'
                    "ports = []\n"
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            code = main(
                ["--home", directory, "game", "check", "--all"],
                stdout=output,
                stderr=io.StringIO(),
            )

            self.assertEqual(0, code)
            self.assertIn(
                "demo | Demo Server | standalone | enabled=false",
                output.getvalue(),
            )
            self.assertNotIn("unknown engine", output.getvalue())
