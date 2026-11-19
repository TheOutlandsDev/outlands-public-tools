from __future__ import annotations

import os
import platform
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from opskit.games import check_profiles, list_profiles


PROFILE = """\
name = "demo"
game = "Demo Server"
engine = "standalone"
enabled = true
platform = "any"
install_dir = "servers/demo"
executable = "server.bin"
required_files = ["required.txt"]
save_paths = ["saves"]
ports = [27015]
expect_running = false
"""


class GameProfileSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.workspace = Path(directory.name)
        self.home = self.workspace / "fixture"
        self.profiles = self.home / "config" / "game-profiles"
        self.install = self.home / "servers" / "demo"
        self.profiles.mkdir(parents=True)
        (self.install / "saves").mkdir(parents=True)
        (self.install / "server.bin").write_text("Fictional executable marker.\n", encoding="utf-8")
        (self.install / "required.txt").write_text("Fictional required file.\n", encoding="utf-8")

    def write_profile(self, source: str = PROFILE, name: str = "demo.toml") -> None:
        (self.profiles / name).write_text(source, encoding="utf-8")

    def check(self) -> tuple[dict, dict[str, str], list[str]]:
        report, warnings = check_profiles(self.profiles, self.home)
        self.assertEqual(1, report["count"])
        entry = report["profiles"][0]
        return entry, {check["name"]: check["status"] for check in entry["checks"]}, warnings

    def test_missing_installation_files_are_reported(self) -> None:
        self.write_profile()
        (self.install / "server.bin").unlink()
        (self.install / "required.txt").unlink()
        (self.install / "saves").rmdir()

        entry, checks, warnings = self.check()
        self.assertEqual([], warnings)
        self.assertEqual("fail", entry["status"])
        self.assertEqual("fail", checks["executable"])
        self.assertEqual("fail", checks["required_file_0"])
        self.assertEqual("warn", checks["save_path_0"])

    def test_duplicate_names_are_warned_and_check_fails(self) -> None:
        self.write_profile(PROFILE, "a.toml")
        duplicate = PROFILE.replace('name = "demo"', 'name = "DEMO"').replace(
            'game = "Demo Server"', 'game = "Duplicate Demo"'
        )
        self.write_profile(duplicate, "z.toml")

        listed, warnings = list_profiles(self.profiles)
        self.assertEqual(1, listed["count"])
        self.assertEqual("Demo Server", listed["profiles"][0]["game"])
        self.assertTrue(warnings)
        checked, warnings = check_profiles(self.profiles, self.home)
        self.assertEqual("fail", checked["status"])
        self.assertTrue(warnings)

    def test_disabled_and_other_platform_profiles_skip_missing_files(self) -> None:
        (self.install / "server.bin").unlink()
        foreign_platform = "linux" if platform.system().casefold() == "windows" else "windows"
        cases = {
            "disabled": PROFILE.replace("enabled = true", "enabled = false"),
            "other platform": PROFILE.replace('platform = "any"', f'platform = "{foreign_platform}"'),
        }
        for name, profile in cases.items():
            with self.subTest(name=name):
                self.write_profile(profile)
                entry, checks, warnings = self.check()
                self.assertEqual([], warnings)
                self.assertEqual("skip", entry["status"])
                self.assertEqual("skip", checks["executable"])

    def test_port_declarations_require_integer_range(self) -> None:
        for ports, expected in {
            "[1, 65535]": "pass",
            "[0]": "fail",
            "[65536]": "fail",
            "[true]": "fail",
            '["27015"]': "fail",
        }.items():
            with self.subTest(ports=ports):
                self.write_profile(PROFILE.replace("[27015]", ports))
                entry, checks, _warnings = self.check()
                self.assertEqual(expected, checks["ports"])
                self.assertEqual(expected, entry["status"])

    def test_expect_running_stays_offline(self) -> None:
        self.write_profile(PROFILE.replace("expect_running = false", "expect_running = true"))
        unexpected_access = AssertionError("Installation check attempted live access.")
        with (
            patch("socket.socket", side_effect=unexpected_access),
            patch("socket.create_connection", side_effect=unexpected_access),
            patch("subprocess.Popen", side_effect=unexpected_access),
        ):
            entry, checks, warnings = self.check()

        self.assertEqual([], warnings)
        self.assertEqual("pass", entry["status"])
        self.assertEqual("pass", checks["ports"])
        self.assertEqual("skip", checks["listening_ports"])

    def test_malformed_toml_diagnostics_are_generic(self) -> None:
        self.write_profile()
        secret_marker = "fictional-private-value-invalid-toml"
        self.write_profile(f'name = [{secret_marker}\n', "invalid.toml")

        listed, warnings = list_profiles(self.profiles)
        self.assertEqual(1, listed["count"])
        self.assertTrue(warnings)
        checked, check_warnings = check_profiles(self.profiles, self.home)
        self.assertEqual("fail", checked["status"])
        for diagnostic in (*warnings, *check_warnings):
            self.assertNotIn(secret_marker, diagnostic)
            self.assertNotIn(str(self.home), diagnostic)

    def test_declared_paths_cannot_escape_installation_root(self) -> None:
        outside = self.workspace / "outside"
        outside.mkdir()
        for name in ("server.bin", "required.txt"):
            (outside / name).write_text("Outside marker.\n", encoding="utf-8")
        cases = (
            ('install_dir = "servers/demo"', f"install_dir = '{outside.as_posix()}'", "install_dir"),
            ('executable = "server.bin"', 'executable = "../../../outside/server.bin"', "executable"),
            ('required_files = ["required.txt"]', r"required_files = ['..\..\..\outside\required.txt']", "required_file_0"),
            ('save_paths = ["saves"]', 'save_paths = ["../../../outside"]', "save_path_0"),
        )
        for original, replacement, check_name in cases:
            with self.subTest(check=check_name):
                self.write_profile(PROFILE.replace(original, replacement))
                entry, checks, _warnings = self.check()
                self.assertEqual("fail", entry["status"])
                self.assertEqual("fail", checks[check_name])

    def test_links_cannot_leave_selected_root(self) -> None:
        outside = self.workspace / "outside"
        outside.mkdir()
        (outside / "server.bin").write_text("Outside executable marker.\n", encoding="utf-8")
        link = self.home / "servers" / "linked"
        if os.name == "nt":
            environment = os.environ | {
                "OPSKIT_TEST_LINK_PATH": str(link),
                "OPSKIT_TEST_LINK_TARGET": str(outside),
            }
            subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "New-Item -ItemType Junction -Path $env:OPSKIT_TEST_LINK_PATH "
                    "-Target $env:OPSKIT_TEST_LINK_TARGET -ErrorAction Stop | Out-Null",
                ],
                env=environment,
                check=True,
                capture_output=True,
                timeout=20,
            )
            self.addCleanup(link.rmdir)
        else:
            link.symlink_to(outside, target_is_directory=True)
            self.addCleanup(link.unlink)
        self.write_profile(PROFILE.replace('install_dir = "servers/demo"', 'install_dir = "servers/linked"'))

        entry, checks, _warnings = self.check()
        self.assertEqual("fail", entry["status"])
        self.assertEqual("fail", checks["install_dir"])
        self.assertTrue((outside / "server.bin").is_file())
