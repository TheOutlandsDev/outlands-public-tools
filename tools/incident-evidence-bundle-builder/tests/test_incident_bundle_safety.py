from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from opskit.cli import main


class IncidentBundleSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.output = self.root / "incident.zip"
        self.doctor = self.root / "doctor.json"
        self.inventory = self.root / "inventory.json"
        self.ports = self.root / "ports.json"
        self.doctor.write_text(
            json.dumps(
                {
                    "status": "fictional-ready",
                    "checks": [{"api_key": "invented-json-example", "token": "dummy-value"}],
                }
            ),
            encoding="utf-8",
        )
        self.inventory.write_text('{"fixtures":["demo-node"]}\n', encoding="utf-8")
        self.ports.write_text('{"rows":[]}\n', encoding="utf-8")
        self.note = self.root / "note sample!.txt"
        self.note.write_text(
            "Fictional observation preserved.\npassword=invented-text-example\n",
            encoding="utf-8",
        )

    def _run(self, *options: str, output: Path | None = None) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        code = main(
            [
                "--home",
                str(self.root),
                "incident",
                "bundle",
                "--doctor",
                self.doctor.name,
                "--inventory",
                self.inventory.name,
                "--ports",
                self.ports.name,
                "--output",
                str(output if output is not None else self.output),
                "--json",
                *options,
            ],
            stdout=stdout,
            stderr=stderr,
        )
        return code, stdout.getvalue(), stderr.getvalue()

    def _names(self) -> set[str]:
        return {path.name for path in self.root.iterdir()}

    def _assert_refused(self, result: tuple[int, str, str]) -> None:
        code, stdout, stderr = result
        self.assertEqual(2, code, stderr)
        self.assertEqual("", stdout)
        self.assertTrue(stderr.strip())
        self.assertNotIn(str(self.root), stderr)

    def test_redacts_known_fields_and_assignment_lines(self) -> None:
        code, _, stderr = self._run("--include", self.note.name)
        self.assertEqual(0, code, stderr)
        with zipfile.ZipFile(self.output) as archive:
            doctor = json.loads(archive.read("doctor.json"))
            note = archive.read("attachments/01-note_sample_.txt").decode("utf-8")
        self.assertEqual("fictional-ready", doctor["status"])
        self.assertEqual([{"api_key": "[REDACTED]", "token": "[REDACTED]"}], doctor["checks"])
        self.assertIn("Fictional observation preserved.", note)
        self.assertIn("password=[REDACTED]", note)
        self.assertNotIn("invented-text-example", note)

    def test_manifest_matches_written_members(self) -> None:
        second = self.root / "second note.txt"
        second.write_text("Fictional unredacted observation.\n", encoding="utf-8")
        code, stdout, stderr = self._run("--include", self.note.name, "--include", second.name)
        self.assertEqual(0, code, stderr)
        with zipfile.ZipFile(self.output) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            entries = manifest["files"]
            expected = {
                "doctor.json",
                "inventory.json",
                "ports.json",
                "attachments/01-note_sample_.txt",
                "attachments/02-second_note.txt",
            }
            self.assertEqual(expected | {"manifest.json"}, set(archive.namelist()))
            self.assertEqual(len(expected), len(entries))
            self.assertEqual(expected, {entry["name"] for entry in entries})
            for entry in entries:
                with self.subTest(name=entry["name"]):
                    content = archive.read(entry["name"])
                    self.assertEqual(len(content), entry["bytes"])
                    self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"])
                    self.assertEqual(not entry["name"].startswith("attachments/"), entry["generated"])
        attachment_flags = {
            entry["name"]: entry["redacted"] for entry in entries if not entry["generated"]
        }
        self.assertEqual(
            {"attachments/01-note_sample_.txt": True, "attachments/02-second_note.txt": False},
            attachment_flags,
        )
        receipt = json.loads(stdout)["data"]
        content = self.output.read_bytes()
        self.assertEqual(len(content), receipt["bytes"])
        self.assertEqual(hashlib.sha256(content).hexdigest(), receipt["sha256"])

    def test_binary_attachment_refused_without_output(self) -> None:
        for content in (b"Fictional\x00fixture", b"Fictional\xfffixture"):
            with self.subTest(content=content):
                self.note.write_bytes(content)
                before = self._names()
                self._assert_refused(self._run("--include", self.note.name))
                self.assertEqual(before, self._names())
                self.assertEqual(content, self.note.read_bytes())

    def test_oversized_attachment_refused_without_output(self) -> None:
        limit = max(path.stat().st_size for path in (self.doctor, self.inventory, self.ports)) + 64
        self.note.write_bytes(b"x" * (limit + 1))
        before = self._names()
        self._assert_refused(self._run("--include", self.note.name, "--max-file-bytes", str(limit)))
        self.assertEqual(before, self._names())

    def test_late_destination_is_not_overwritten(self) -> None:
        original_link = os.link
        before = self._names()

        def competing_publish(source, destination, *args, **kwargs):
            with Path(destination).open("xb") as stream:
                stream.write(b"fictional competing output")
            return original_link(source, destination, *args, **kwargs)

        with patch("opskit.incidents.os.link", side_effect=competing_publish) as publish:
            self._assert_refused(self._run())
        publish.assert_called_once()
        self.assertEqual(b"fictional competing output", self.output.read_bytes())
        self.assertEqual(before | {self.output.name}, self._names())

    def test_existing_destination_is_not_overwritten(self) -> None:
        self.output.write_bytes(b"fictional existing output")
        before = self._names()
        self._assert_refused(self._run())
        self.assertEqual(b"fictional existing output", self.output.read_bytes())
        self.assertEqual(before, self._names())

    def test_input_files_remain_unchanged(self) -> None:
        sources = (self.doctor, self.inventory, self.ports, self.note)
        before = {path: hashlib.sha256(path.read_bytes()).digest() for path in sources}
        code, _, stderr = self._run("--include", self.note.name)
        self.assertEqual(0, code, stderr)
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).digest() for path in sources})

    def test_force_refuses_output_alias(self) -> None:
        original = self.doctor.read_bytes()
        alias = self.root / "alias.zip"
        os.link(self.doctor, alias)
        before = self._names()
        for destination in (self.doctor, alias):
            with self.subTest(destination=destination.name):
                self._assert_refused(self._run("--force", output=destination))
                self.assertEqual(original, self.doctor.read_bytes())
                self.assertEqual(original, alias.read_bytes())
                self.assertEqual(before, self._names())

    def test_invalid_diagnostic_refused_without_output(self) -> None:
        self.doctor.write_text('{"fictional":"unterminated', encoding="utf-8")
        before = self._names()
        result = self._run()
        self._assert_refused(result)
        self.assertNotIn("unterminated", result[2])
        self.assertEqual(before, self._names())
