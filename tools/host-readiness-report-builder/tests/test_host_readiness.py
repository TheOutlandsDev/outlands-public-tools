from __future__ import annotations

from contextlib import ExitStack
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from opskit.cli import main


MIB = 1024**2
GIB = 1024**3
READY = {
    "os": "windows",
    "python_version": "3.15.2",
    "workspace": "writable",
    "disk_total_bytes": 50 * GIB,
    "disk_free_bytes": 5 * GIB,
    "memory_total_bytes": 2560 * MIB,
    "memory_available_bytes": 256 * MIB,
    "temporary_directory_writable": True,
    "hostname_resolution": True,
}


class HostReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.observations = self.directory / "fictional observation file.json"

    def _invoke(self, path: Path | None = None) -> tuple[int, str, str]:
        output = io.StringIO()
        errors = io.StringIO()
        code = main(
            ["doctor", "--observations", str(path or self.observations), "--json"],
            stdout=output,
            stderr=errors,
        )
        return code, output.getvalue(), errors.getvalue()

    def _report(self, **observations: object) -> tuple[int, dict]:
        self.observations.write_text(json.dumps(READY | observations), encoding="utf-8")
        code, output, errors = self._invoke()
        self.assertEqual("", errors)
        return code, json.loads(output)

    def _assert_rejected(self, path: Path | None = None) -> str:
        code, output, errors = self._invoke(path)
        self.assertEqual(2, code)
        self.assertEqual("", output)
        self.assertTrue(errors.strip())
        self.assertNotIn(str(self.directory), errors)
        return errors

    @staticmethod
    def _statuses(report: dict) -> dict[str, str]:
        return {check["name"]: check["status"] for check in report["data"]["checks"]}

    def test_disk_absolute_thresholds(self) -> None:
        cases = (
            (2 * GIB - 1, "fail", 1),
            (2 * GIB, "warn", 0),
            (5 * GIB - 1, "warn", 0),
            (5 * GIB, "pass", 0),
        )
        for free, status, exit_code in cases:
            with self.subTest(free=free):
                code, report = self._report(disk_total_bytes=8 * GIB, disk_free_bytes=free)
                self.assertEqual(exit_code, code)
                self.assertEqual(status, self._statuses(report)["disk_space"])

    def test_disk_percentage_threshold(self) -> None:
        for free, status in ((10 * GIB - 1, "warn"), (10 * GIB, "pass"), (10 * GIB + 1, "pass")):
            with self.subTest(free=free):
                code, report = self._report(disk_total_bytes=100 * GIB, disk_free_bytes=free)
                self.assertEqual(0, code)
                self.assertEqual(status, self._statuses(report)["disk_space"])

    def test_memory_absolute_and_percentage_thresholds(self) -> None:
        cases = (
            (GIB, 256 * MIB - 1, "fail", 1),
            (GIB, 256 * MIB, "pass", 0),
            (0, 0, "fail", 1),
            (5 * GIB, 512 * MIB - 1, "warn", 0),
            (5 * GIB, 512 * MIB, "pass", 0),
            (5 * GIB, 512 * MIB + 1, "pass", 0),
        )
        for total, available, status, exit_code in cases:
            with self.subTest(total=total, available=available):
                code, report = self._report(memory_total_bytes=total, memory_available_bytes=available)
                self.assertEqual(exit_code, code)
                self.assertEqual(status, self._statuses(report)["memory"])

    def test_original_severity_precedence_and_summary(self) -> None:
        cases = (
            ({}, 0, True, "pass", {"pass": 7, "warn": 0, "fail": 0}),
            ({"workspace": "read_only"}, 0, True, "warn", {"pass": 6, "warn": 1, "fail": 0}),
            ({"workspace": "read_only", "disk_free_bytes": 0},
             1, False, "fail", {"pass": 5, "warn": 1, "fail": 1}),
        )
        for overrides, exit_code, ok, status, summary in cases:
            with self.subTest(status=status):
                code, report = self._report(**overrides)
                self.assertEqual(exit_code, code)
                self.assertIs(ok, report["ok"])
                self.assertEqual(status, report["data"]["status"])
                self.assertEqual(summary, report["data"]["summary"])

    def test_platform_python_workspace_and_missing_observations(self) -> None:
        code, linux = self._report(os="linux", python_version="3.12.0")
        self.assertEqual(0, code)
        self.assertEqual("pass", self._statuses(linux)["supported_os"])
        self.assertEqual("pass", self._statuses(linux)["python"])

        code, unavailable = self._report(
            os="other",
            python_version="3.11.99",
            workspace="read_only",
            disk_total_bytes=None,
            disk_free_bytes=None,
            memory_total_bytes=None,
            memory_available_bytes=None,
            temporary_directory_writable=None,
            hostname_resolution=None,
        )
        self.assertEqual(1, code)
        self.assertEqual({
            "supported_os": "warn",
            "python": "fail",
            "opskit_home": "warn",
            "disk_space": "fail",
            "memory": "warn",
            "temporary_directory": "warn",
            "hostname_resolution": "warn",
        }, self._statuses(unavailable))

        _, negative = self._report(temporary_directory_writable=False, hostname_resolution=False)
        self.assertEqual("warn", self._statuses(negative)["temporary_directory"])
        self.assertEqual("warn", self._statuses(negative)["hostname_resolution"])

    def test_uncalculated_disk_for_invalid_workspace(self) -> None:
        for workspace in ("missing", "not_directory"):
            with self.subTest(workspace=workspace):
                code, report = self._report(workspace=workspace, disk_total_bytes=None, disk_free_bytes=None)
                statuses = self._statuses(report)
                self.assertEqual(1, code)
                self.assertEqual("fail", statuses["opskit_home"])
                self.assertNotIn("disk_space", statuses)

    def test_report_is_deterministic_allowlisted_and_preserves_saved_input(self) -> None:
        content = json.dumps(READY, indent=2).encode("utf-8")
        self.observations.write_bytes(content)
        code, output, errors = self._invoke()
        self.assertEqual(0, code)
        self.assertEqual("", errors)
        self.assertEqual((code, output, errors), self._invoke())
        self.assertEqual(content, self.observations.read_bytes())
        self.assertEqual([self.observations], list(self.directory.iterdir()))

        report = json.loads(output)
        self.assertEqual({"command", "schema_version", "ok", "warnings", "data"}, set(report))
        self.assertEqual({"status", "summary", "checks", "read_only", "duration_hint"}, set(report["data"]))
        for check in report["data"]["checks"]:
            self.assertEqual({"name", "status", "message", "details"}, set(check))
            for key in ("path", "executable", "hostname", "address", "addresses"):
                self.assertNotIn(key, check["details"])
        self.assertNotIn(str(self.directory), output)
        self.assertNotIn(self.observations.name, output)

        self.observations.write_text(json.dumps(dict(reversed(tuple(READY.items())))), encoding="utf-8")
        self.assertEqual((code, output, errors), self._invoke())

    def test_assessment_uses_no_live_host_probes(self) -> None:
        self.observations.write_text(json.dumps(READY), encoding="utf-8")
        probes = (
            "os.access",
            "platform.release",
            "platform.system",
            "platform.python_version",
            "shutil.disk_usage",
            "socket.gethostname",
            "socket.getaddrinfo",
            "socket.socket",
            "subprocess.Popen",
            "tempfile.gettempdir",
            "time.time",
        )
        with ExitStack() as stack:
            for probe in probes:
                stack.enter_context(patch(probe, side_effect=AssertionError(f"Live probe called: {probe}")))
            code, output, errors = self._invoke()
        self.assertEqual(0, code)
        self.assertEqual("", errors)
        self.assertEqual("pass", json.loads(output)["data"]["status"])

    def test_invalid_observation_schema_withholds_report(self) -> None:
        cases = (
            [],
            {key: value for key, value in READY.items() if key != "hostname_resolution"},
            READY | {"os": "Solaris"},
            READY | {"python_version": "3.15"},
            READY | {"workspace": "uncertain"},
            READY | {"disk_total_bytes": None},
            READY | {"disk_free_bytes": -1},
            READY | {"disk_total_bytes": 2**63},
            READY | {"disk_free_bytes": 51 * GIB},
            READY | {"memory_total_bytes": None},
            READY | {"memory_available_bytes": True},
            READY | {"memory_available_bytes": 256.0 * MIB},
            READY | {"memory_available_bytes": 2561 * MIB},
            READY | {"temporary_directory_writable": 1},
            READY | {"hostname_resolution": "true"},
        )
        for index, data in enumerate(cases):
            with self.subTest(case=index):
                self.observations.write_text(json.dumps(data), encoding="utf-8")
                self._assert_rejected()

    def test_bad_json_withholds_report_without_echoing_private_values(self) -> None:
        marker = "fictional-private-host.invalid"
        baseline = json.dumps(READY).encode("utf-8")
        cases = (
            b"{",
            b"\xff\xfe",
            baseline + b" " * (16 * 1024),
            baseline[:-1] + b', "os": "other"}',
            json.dumps(READY | {"disk_total_bytes": float("inf")}).encode("utf-8"),
            json.dumps(READY | {marker: "192.0.2.71"}).encode("utf-8"),
            json.dumps(READY | {"hostname": marker, "addresses": ["192.0.2.71"]}).encode("utf-8"),
            json.dumps(READY | {"workspace_path": str(self.observations)}).encode("utf-8"),
            json.dumps(READY | {"os": marker}).encode("utf-8"),
        )
        for index, content in enumerate(cases):
            with self.subTest(case=index):
                self.observations.write_bytes(content)
                errors = self._assert_rejected()
                self.assertNotIn(marker, errors)
                self.assertNotIn("192.0.2.71", errors)
                self.assertEqual(content, self.observations.read_bytes())

        errors = self._assert_rejected(self.directory / marker)
        self.assertNotIn(marker, errors)
