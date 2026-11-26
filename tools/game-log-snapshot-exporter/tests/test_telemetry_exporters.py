from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from game_log_snapshot_exporter import (
    TelemetryExportError,
    TelemetryExporter,
    TelemetrySourceProfile,
    validate_snapshot,
)


FIXED_NOW = datetime(2020, 1, 2, 3, 0, tzinfo=UTC)
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "examples"

FIXTURES = {
    "rust": ("rust.log", {"player_join", "spawn", "kill", "player_leave"}),
    "dayz": ("dayz.RPT", {"player_join", "kill", "error", "player_leave"}),
    "main_spt": (
        "main_spt.log",
        {"player_join", "raid_start", "kill", "extract", "player_leave"},
    ),
    "modern_warfare": (
        "modern_warfare.log",
        {"player_join", "damage", "kill", "player_leave"},
    ),
    "zomboid": ("zomboid.log", {"player_join", "kill", "death", "player_leave"}),
}


class TelemetryExporterTests(unittest.TestCase):
    def _exporter(
        self,
        program: str,
        source_root: Path,
        output_root: Path,
        pattern: str,
    ) -> TelemetryExporter:
        profile = TelemetrySourceProfile(
            id=program,
            name=program,
            root=source_root,
            patterns=(pattern,),
        )
        return TelemetryExporter(
            (profile,),
            output_root=output_root,
            now=lambda: FIXED_NOW,
        )

    def test_all_five_sanitized_fixtures_parse_expected_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp) / "output"
            for program, (fixture_name, expected) in FIXTURES.items():
                exporter = self._exporter(
                    program,
                    FIXTURE_ROOT,
                    output_root,
                    fixture_name,
                )
                snapshot = exporter.collect(program)
                events = {record["event"] for record in snapshot["records"]}
                self.assertTrue(expected.issubset(events), (program, events))
                validate_snapshot(snapshot)

    def test_snapshot_contains_no_raw_names_ids_ips_chat_or_log_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            exporter = self._exporter(
                "rust",
                FIXTURE_ROOT,
                Path(temp) / "output",
                "rust.log",
            )
            snapshot = exporter.collect("rust")
            encoded = json.dumps(snapshot, sort_keys=True)
            self.assertNotIn("Alpha", encoded)
            self.assertNotIn("Bravo", encoded)
            self.assertNotIn("12345678901234567", encoded)
            self.assertNotIn("private conversation", encoded)
            for record in snapshot["records"]:
                self.assertNotIn("line", record)
                self.assertNotIn("message", record)
                self.assertRegex(record.get("actor") or "actor_0000000000000000", r"^actor_[0-9a-f]{16}$")

        with tempfile.TemporaryDirectory() as temp:
            exporter = self._exporter(
                "main_spt",
                FIXTURE_ROOT,
                Path(temp) / "output",
                "main_spt.log",
            )
            encoded = json.dumps(exporter.collect("main_spt"), sort_keys=True)
            self.assertNotIn("192.0.2.44", encoded)
            self.assertNotIn("keepalive", encoded.casefold())

    def test_source_files_are_unchanged_by_collect_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = FIXTURE_ROOT / "modern_warfare.log"
            before = source.read_bytes()
            exporter = self._exporter(
                "modern_warfare",
                FIXTURE_ROOT,
                Path(temp) / "output",
                source.name,
            )
            exporter.collect("modern_warfare")
            exported = exporter.export("modern_warfare")
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue(Path(exported["path"]).is_file())
            self.assertFalse(exported["raw_data_written"])

    def test_unsafe_source_pattern_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "source"
            root.mkdir()
            outside = Path(temp) / "outside.log"
            outside.write_text("Player Alpha connected\n", encoding="utf-8")
            exporter = self._exporter(
                "zomboid",
                root,
                Path(temp) / "output",
                "../outside.log",
            )
            with self.assertRaises(TelemetryExportError):
                exporter.discover("zomboid")

    def test_denied_and_non_log_files_are_not_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "source"
            root.mkdir()
            (root / "good.log").write_text("user Alpha connected\n", encoding="utf-8")
            (root / "secret-token.log").write_text(
                "user Secret connected\n", encoding="utf-8"
            )
            (root / "state.sqlite").write_bytes(b"SQLite format 3")
            profile = TelemetrySourceProfile(
                id="zomboid",
                name="zomboid",
                root=root,
                patterns=("*",),
            )
            exporter = TelemetryExporter(
                (profile,),
                output_root=Path(temp) / "output",
            )
            self.assertEqual([path.name for path in exporter.discover("zomboid")], ["good.log"])
