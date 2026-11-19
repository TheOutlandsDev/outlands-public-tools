"""Original firewall evidence cases with fictional inputs."""

from __future__ import annotations

import unittest

from firewall_evidence import _firewall_state, _port_values


class FirewallOriginalTests(unittest.TestCase):
    def test_port_ranges_expand_for_firewall_comparison(self) -> None:
        assert _port_values(["34001-34004", "35001"]) == {
            34001,
            34002,
            34003,
            34004,
            35001,
        }


    def test_exact_private_firewall_contract_is_allowed(self) -> None:
        service = {
            "firewall_rule": "Fictional Datagram Range",
            "protocol": "udp",
            "ports": [34001, 34002, 34003, 34004],
        }
        policy = {
            "rules": [
                {
                    "display_name": "Fictional Datagram Range",
                    "enabled": "True",
                    "direction": "Inbound",
                    "action": "Allow",
                    "profile": "Private",
                    "protocol": "UDP",
                    "local_ports": ["34001-34004"],
                    "local_addresses": ["192.0.2.15"],
                    "interface_aliases": ["Fictional Adapter A"],
                }
            ]
        }
        state, evidence = _firewall_state(
            service,
            policy,
            interface_alias="Fictional Adapter A",
            local_ipv4="192.0.2.15",
        )
        assert state == "allowed"
        assert "Private" in evidence


    def test_firewall_contract_rejects_broad_or_wrong_scope(self) -> None:
        service = {
            "firewall_rule": "Fictional Datagram Service",
            "protocol": "udp",
            "ports": [35001],
        }
        policy = {
            "rules": [
                {
                    "display_name": "Fictional Datagram Service",
                    "enabled": "True",
                    "direction": "Inbound",
                    "action": "Allow",
                    "profile": "Any",
                    "protocol": "UDP",
                    "local_ports": ["35001"],
                    "local_addresses": ["Any"],
                    "interface_aliases": ["Any"],
                }
            ]
        }
        state, _ = _firewall_state(
            service,
            policy,
            interface_alias="Fictional Adapter A",
            local_ipv4="192.0.2.15",
        )
        assert state == "mismatch"
