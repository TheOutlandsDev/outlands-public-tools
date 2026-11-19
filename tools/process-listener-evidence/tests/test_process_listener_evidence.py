"""The original evidence cases and regressions for the standalone checker."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from process_listener_evidence import (
    ProcessFact,
    exact_identity,
    listener_state,
    rooted_identity,
)


ROOT = Path(__file__).resolve().parents[1]
WINDOWS_EXAMPLE = ROOT / "examples" / "proven-windows.json"
POSIX_EXAMPLE = ROOT / "examples" / "unavailable-posix.json"


def run_checker(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", "process_listener_evidence", "--input", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=15,
    )


class OriginalEvidenceTests(unittest.TestCase):
    def test_exact_identity_requires_one_exact_executable(self) -> None:
        expected = r"R:\storybook\harbor.exe"
        matching = ProcessFact(
            pid=4101,
            ppid=1,
            name="harbor.exe",
            executable=expected,
            created_utc="2042-03-18T12:00:00Z",
        )
        proven = exact_identity(
            (matching,), "harbor.exe", expected, path_style="windows"
        )
        self.assertEqual(proven.state, "proven")
        self.assertEqual(proven.pids, (4101,))

        unknown = ProcessFact(
            pid=4102,
            ppid=1,
            name="harbor.exe",
            executable=None,
            created_utc=None,
        )
        inaccessible = exact_identity(
            (unknown,), "harbor.exe", expected, path_style="windows"
        )
        self.assertEqual(inaccessible.state, "unavailable")
        missing = exact_identity((), "harbor.exe", expected, path_style="windows")
        self.assertEqual(missing.state, "failed")

    def test_listener_proof_requires_every_port_owned_by_exact_pid(self) -> None:
        owners = {
            ("udp", 46101): {4101},
            ("tcp", 46102): {4101},
            ("udp", 46103): {4101},
        }
        specifications = (("udp", 46101), ("tcp", 46102), ("udp", 46103))
        self.assertEqual(listener_state(owners, (4101,), specifications), "proven")
        owners[("udp", 46103)] = {4199}
        self.assertEqual(listener_state(owners, (4101,), specifications), "failed")

    def test_rooted_identity_accepts_versioned_release_but_rejects_other_roots(self) -> None:
        release_root = r"R:\storybook\releases"
        current = ProcessFact(
            pid=4101,
            ppid=1,
            name="harbor.exe",
            executable=r"R:\storybook\releases\v7\harbor.exe",
            created_utc="2042-03-18T12:00:00Z",
        )
        match = rooted_identity(
            (current,), "harbor.exe", release_root, path_style="windows"
        )
        self.assertEqual(match.state, "proven")

        unrelated = ProcessFact(
            pid=4102,
            ppid=1,
            name="harbor.exe",
            executable=r"R:\storybook\releases-old\harbor.exe",
            created_utc="2042-03-18T12:00:00Z",
        )
        mismatch = rooted_identity(
            (unrelated,), "harbor.exe", release_root, path_style="windows"
        )
        self.assertEqual(mismatch.state, "failed")


class EvidenceRegressionTests(unittest.TestCase):
    def test_multiple_matching_processes_fail_identity(self) -> None:
        root = "/opt/storybook/bin"
        executable = f"{root}/relay"
        processes = (
            ProcessFact(5101, 1, "relay", executable, None),
            ProcessFact(5102, 1, "relay", executable, None),
        )
        for checker, target in ((exact_identity, executable), (rooted_identity, root)):
            with self.subTest(checker=checker.__name__):
                match = checker(processes, "relay", target, path_style="posix")
                self.assertEqual(match.state, "failed")
                self.assertEqual(match.pids, (5101, 5102))
                self.assertIsNone(match.created_utc)

    def test_empty_and_mixed_listener_owners_fail(self) -> None:
        specification = (("tcp", 46102),)
        owners = {specification[0]: {4101, 4199}}
        self.assertEqual(listener_state(owners, (4101,), specification), "failed")
        self.assertEqual(listener_state(owners, (4101,), ()), "failed")
        self.assertEqual(listener_state({}, (4101,), specification), "failed")
        self.assertEqual(listener_state(owners, (), specification), "failed")

    def test_windows_lexical_paths_use_windows_rules(self) -> None:
        process = ProcessFact(
            4101,
            1,
            "Harbor.exe",
            r"r:\STORYBOOK\releases\.\v7\harbor.exe",
            "2042-03-18T12:00:00Z",
        )
        match = exact_identity(
            (process,), "harbor.exe", "R:/storybook/releases/v7/harbor.exe",
            path_style="windows",
        )
        self.assertEqual(match.state, "proven")
        self.assertEqual(match.created_utc, process.created_utc)
        escaped = ProcessFact(
            4103,
            1,
            "harbor.exe",
            r"R:\storybook\releases\..\releases-old\harbor.exe",
            None,
        )
        self.assertEqual(
            rooted_identity(
                (escaped,), "harbor.exe", r"R:\storybook\releases", path_style="windows"
            ).state,
            "failed",
        )

    def test_posix_paths_are_case_sensitive_and_check_component_boundaries(self) -> None:
        root = "/opt/storybook/releases"
        process = ProcessFact(5101, 1, "relay", f"{root}/v2/relay", None)
        sibling = ProcessFact(5102, 1, "relay", f"{root}-old/relay", None)
        self.assertEqual(
            exact_identity(
                (process,), "relay", f"{root}/v2/RELAY", path_style="posix"
            ).state,
            "failed",
        )
        self.assertEqual(
            rooted_identity((process,), "relay", root, path_style="posix").state,
            "proven",
        )
        self.assertEqual(
            rooted_identity((sibling,), "relay", root, path_style="posix").state,
            "failed",
        )

    def test_fictional_windows_and_posix_examples(self) -> None:
        examples = (
            (
                WINDOWS_EXAMPLE,
                0,
                {
                    "status": "proven",
                    "identity": {
                        "state": "proven",
                        "pids": [4101],
                        "created_utc": "2042-03-18T12:00:00Z",
                    },
                    "listener_state": "proven",
                },
            ),
            (
                POSIX_EXAMPLE,
                1,
                {
                    "status": "unavailable",
                    "identity": {
                        "state": "unavailable",
                        "pids": [],
                        "created_utc": None,
                    },
                    "listener_state": "failed",
                },
            ),
        )
        for path, exit_code, expected in examples:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                result = run_checker(path)
                self.assertEqual(result.returncode, exit_code, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout), expected)
                self.assertEqual(path.read_bytes(), original)

    def test_cli_never_credits_listeners_to_ambiguous_processes(self) -> None:
        document = json.loads(WINDOWS_EXAMPLE.read_bytes())
        additional = dict(document["processes"][0], pid=4102)
        document["processes"].append(additional)
        for listener in document["listener_owners"]:
            listener["pids"].append(4102)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ambiguous.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            result = run_checker(path)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["identity"]["state"], "failed")
        self.assertCountEqual(report["identity"]["pids"], [4101, 4102])
        self.assertEqual(report["listener_state"], "failed")

    def test_malformed_evidence_is_refused_without_exposing_input(self) -> None:
        document = json.loads(WINDOWS_EXAMPLE.read_bytes())
        cases = (
            ("identity", "path_style", "fictional-private-value"),
            ("identity", "path", "relative/harbor.exe"),
            ("processes", "pid", True),
            ("expected_listeners", "port", 65536),
            ("listener_owners", "pids", [-1]),
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fictional-private-filename.json"
            for section, field, value in cases:
                with self.subTest(section=section, field=field):
                    bad = copy.deepcopy(document)
                    target = bad[section] if section == "identity" else bad[section][0]
                    target[field] = value
                    path.write_text(json.dumps(bad), encoding="utf-8")
                    self.assert_refused(path)
            duplicate_identity = '{"identity":null,' + json.dumps(document)[1:]
            path.write_text(duplicate_identity, encoding="utf-8")
            self.assert_refused(path)

    def assert_refused(self, path: Path) -> None:
        result = run_checker(path)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr)
        self.assertNotIn(path.name, result.stderr)
        self.assertNotIn("fictional-private-value", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
