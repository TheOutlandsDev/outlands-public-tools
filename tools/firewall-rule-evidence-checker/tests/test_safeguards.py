"""Regressions for exact scope and privacy of the offline diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from firewall_evidence import _firewall_state


CLI = Path(__file__).resolve().parents[1] / "firewall_evidence.py"
RULE_NAME = "Fictional Scope Marker Rule"
INTERFACE = "Fictional Scope Marker Adapter"
ADDRESS = "198.51.100.21"


def saved_input(**overrides):
    return {
        "service": {"firewall_rule": RULE_NAME, "protocol": "udp", "ports": [55000, 55001]},
        "policy": {
            "rules": [
                {
                    "display_name": RULE_NAME,
                    "enabled": True,
                    "direction": "Inbound",
                    "action": "Allow",
                    "profile": "Private",
                    "protocol": 17,
                    "local_ports": ["55000-55001"],
                    "local_addresses": [ADDRESS],
                    "interface_aliases": [INTERFACE],
                    **overrides,
                }
            ]
        },
        "interface_alias": INTERFACE,
        "local_ipv4": ADDRESS,
    }


def compare(payload):
    return _firewall_state(
        payload["service"],
        payload["policy"],
        interface_alias=payload["interface_alias"],
        local_ipv4=payload["local_ipv4"],
    )


class FirewallSafeguardTests(unittest.TestCase):
    def test_mixed_or_lookalike_profiles_fail_closed(self):
        self.assertEqual(compare(saved_input())[0], "allowed")
        for profile in ("Private, Public", "Public, Private", "NotPrivate"):
            with self.subTest(profile=profile):
                self.assertEqual(compare(saved_input(profile=profile))[0], "mismatch")

    def test_extra_ports_or_wildcard_fail_closed(self):
        for ports in (["55000-55002"], ["55000-55001", "Any"], ["55000-55001", "invalid"]):
            with self.subTest(ports=ports):
                self.assertEqual(compare(saved_input(local_ports=ports))[0], "mismatch")

    def test_extra_interfaces_and_addresses_fail_closed(self):
        for extra_scope in (
            {"interface_aliases": [INTERFACE, "Fictional Extra Adapter"]},
            {"local_addresses": [ADDRESS, "198.51.100.22"]},
        ):
            with self.subTest(scope=extra_scope):
                self.assertEqual(compare(saved_input(**extra_scope))[0], "mismatch")

    def test_cli_omits_saved_rule_details_from_all_outcomes(self):
        missing = saved_input()
        missing["policy"]["rules"] = []
        invalid = saved_input()
        invalid["service"]["ports"] = ["Fictional Invalid Port Marker"]
        for payload, status, code in (
            (saved_input(), "allowed", 0),
            (saved_input(profile="Private, Public"), "mismatch", 1),
            (missing, "missing", 1),
            (invalid, None, 2),
        ):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "fictional-input-marker.json"
                original = json.dumps(payload).encode("utf-8")
                path.write_bytes(original)
                result = subprocess.run(
                    [sys.executable, "-I", "-B", str(CLI), "--input", str(path)],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=20,
                )

                self.assertEqual(result.returncode, code)
                if status is None:
                    self.assertEqual(result.stdout, "")
                    self.assertTrue(result.stderr.strip())
                else:
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(json.loads(result.stdout), {"status": status})
                    evidence_status, evidence = compare(payload)
                    self.assertEqual(evidence_status, status)
                    for field in (RULE_NAME, INTERFACE, ADDRESS):
                        self.assertNotIn(field, evidence)
                for field in (RULE_NAME, INTERFACE, ADDRESS, "Fictional Invalid Port Marker", path.name, "Traceback"):
                    self.assertNotIn(field, result.stdout + result.stderr)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(Path(directory).iterdir()), [path])
