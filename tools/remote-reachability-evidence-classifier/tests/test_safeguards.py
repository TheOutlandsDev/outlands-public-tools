"""Test saved-evidence boundaries and the standalone CLI."""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from reachability_evidence import _external_state


CHECKER = Path(__file__).resolve().parents[1] / "reachability_evidence.py"
AS_OF = datetime(2042, 6, 1, 12, tzinfo=timezone.utc)
SERVICE = "fictional-archive"
PRIVATE_TEXT = "fictional diagnostic text withheld from reports"
MAX_AGE = 60


def snapshot(generated: datetime, *statuses: str) -> dict:
    return {
        "generated": generated.isoformat(),
        "services": [
            {"id": SERVICE, "status": status, "evidence": PRIVATE_TEXT}
            for status in statuses
        ],
    }


class RemoteReachabilitySafeguardTests(TestCase):
    def test_maximum_age_cutoff_is_inclusive(self) -> None:
        cutoff = AS_OF - timedelta(seconds=MAX_AGE)
        for generated, expected in (
            (cutoff, "reachable"),
            (cutoff - timedelta(microseconds=1), "stale"),
        ):
            with self.subTest(generated=generated):
                state, _ = _external_state(
                    SERVICE, snapshot(generated, "passed"), MAX_AGE, as_of=AS_OF
                )
                self.assertEqual(state, expected)

    def test_future_tolerance_is_five_seconds_inclusive(self) -> None:
        future = AS_OF + timedelta(seconds=5)
        for generated, expected in (
            (future, "reachable"),
            (future + timedelta(microseconds=1), "stale"),
        ):
            with self.subTest(generated=generated):
                state, _ = _external_state(
                    SERVICE, snapshot(generated, "healthy"), MAX_AGE, as_of=AS_OF
                )
                self.assertEqual(state, expected)

    def test_status_synonyms_and_missing_service(self) -> None:
        for status, expected in (
            ("reachable", "reachable"),
            ("HEALTHY", "reachable"),
            ("passed", "reachable"),
            ("unreachable", "unreachable"),
            ("FAILED", "unreachable"),
            ("down", "unreachable"),
            ("unrecognized", "pending"),
        ):
            with self.subTest(status=status):
                state, reason = _external_state(
                    SERVICE, snapshot(AS_OF, status), MAX_AGE, as_of=AS_OF
                )
                self.assertEqual(state, expected)
                self.assertNotIn(PRIVATE_TEXT, reason)
        missing = snapshot(AS_OF, "reachable")
        missing["services"][0]["id"] = "fictional-other-service"
        state, _ = _external_state(SERVICE, missing, MAX_AGE, as_of=AS_OF)
        self.assertEqual(state, "pending")

    def test_conflicting_duplicate_evidence_stays_pending(self) -> None:
        for statuses in (("passed", "down"), ("down", "passed")):
            with self.subTest(statuses=statuses):
                state, reason = _external_state(
                    SERVICE, snapshot(AS_OF, *statuses), MAX_AGE, as_of=AS_OF
                )
                self.assertEqual(state, "pending")
                self.assertIn("conflict", reason.casefold())
                self.assertNotIn(PRIVATE_TEXT, reason)
        state, _ = _external_state(
            SERVICE, snapshot(AS_OF, "passed", "healthy"), MAX_AGE, as_of=AS_OF
        )
        self.assertEqual(state, "reachable")

    def test_cli_reports_safe_results_and_preserves_input(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fictional-private-evidence.json"
            for evidence, expected, expected_code in (
                (snapshot(AS_OF, "passed"), "reachable", 0),
                (snapshot(AS_OF, "failed"), "unreachable", 0),
                (snapshot(AS_OF, "passed", "down"), "pending", 0),
                (snapshot(AS_OF - timedelta(seconds=MAX_AGE + 1), "passed"), "stale", 0),
                ({}, "pending", 0),
                ({"generated": AS_OF.isoformat(), "services": PRIVATE_TEXT}, None, 2),
            ):
                with self.subTest(status=expected):
                    data = json.dumps({
                        "service_id": SERVICE,
                        "as_of": AS_OF.isoformat(),
                        "maximum_age_seconds": MAX_AGE,
                        "evidence": evidence,
                    }).encode("utf-8")
                    path.write_bytes(data)
                    completed = subprocess.run(
                        [
                            sys.executable, "-I", "-B", "-W", "error",
                            str(CHECKER), "--input", str(path),
                        ],
                        capture_output=True, encoding="utf-8", timeout=15, check=False,
                    )
                    self.assertEqual(completed.returncode, expected_code)
                    if expected is None:
                        self.assertEqual(completed.stdout, "")
                        self.assertTrue(completed.stderr.strip())
                    else:
                        self.assertEqual(completed.stderr, "")
                        report = json.loads(completed.stdout)
                        self.assertEqual(set(report), {"status", "reason"})
                        self.assertEqual(report["status"], expected)
                        self.assertTrue(report["reason"])
                    output = completed.stdout + completed.stderr
                    for value in (SERVICE, PRIVATE_TEXT, str(path), path.name, "Traceback"):
                        self.assertNotIn(value, output)
                    self.assertEqual(path.read_bytes(), data)
                    self.assertEqual(list(path.parent.iterdir()), [path])
