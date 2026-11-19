"""Compare saved firewall rule evidence with one declared inbound scope."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any, TextIO


_MAX_BYTES = 256 * 1024
_INPUT_FIELDS = {"service", "policy", "interface_alias", "local_ipv4"}
_SERVICE_FIELDS = {"firewall_rule", "protocol", "ports"}
_PORT_PART = re.compile(r"[0-9]+(?:\s*-\s*[0-9]+)?")
_STATUS_EVIDENCE = {
    "allowed": "Saved rule matches the declared Private scope.",
    "missing": "Expected rule is absent from the saved evidence.",
    "mismatch": "Saved rule scope does not match the declared scope.",
}


class FirewallEvidenceError(ValueError):
    """Raised when the input cannot describe a valid saved check."""


def _port_values(specifications: list[Any]) -> set[int]:
    values: set[int] = set()
    for specification in specifications:
        text = str(specification).strip()
        if not text or text.casefold() == "any":
            continue
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                start_text, end_text = part.split("-", 1)
                try:
                    start, end = int(start_text), int(end_text)
                except ValueError:
                    continue
                if 1 <= start <= end <= 65535 and end - start <= 2048:
                    values.update(range(start, end + 1))
            else:
                try:
                    value = int(part)
                except ValueError:
                    continue
                if 1 <= value <= 65535:
                    values.add(value)
    return values


def _normal_protocol(value: Any) -> str:
    if type(value) is int:
        return {6: "tcp", 17: "udp"}.get(value, "")
    if not isinstance(value, str):
        return ""
    text = _normalized(value)
    if text in {"6", "tcp"}:
        return "tcp"
    if text in {"17", "udp"}:
        return "udp"
    return text


def _list_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _normalized(value: Any) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def _is_enabled(value: Any) -> bool:
    if isinstance(value, str):
        return _normalized(value) in {"true", "1"}
    return value is True or (type(value) is int and value == 1)


def _text_scope(value: Any) -> set[str]:
    return {_normalized(item) for item in _list_values(value)}


def _ipv4(value: Any) -> IPv4Address:
    if not isinstance(value, str):
        raise ValueError
    return IPv4Address(value.strip())


def _address_scope(value: Any) -> set[IPv4Address] | None:
    try:
        return {_ipv4(item) for item in _list_values(value)}
    except ValueError:
        return None


def _exact_ports(value: Any, expected: set[int]) -> bool:
    specifications = _list_values(value)
    if any(
        type(item) not in (str, int) or (type(item) is int and not 1 <= item <= 65535)
        for item in specifications
    ):
        return False
    parts = {part.strip() for item in specifications for part in str(item).split(",")}
    observed: set[int] = set()
    for part in parts:
        if _PORT_PART.fullmatch(part) is None:
            return False
        ports = _port_values([part])
        if not ports or not ports <= expected:
            return False
        observed.update(ports)
    return observed == expected


def _expected_scope(
    service: dict[str, Any],
    interface_alias: str,
    local_ipv4: str,
) -> tuple[str, str, set[int], str, IPv4Address]:
    if not isinstance(service, dict) or not _SERVICE_FIELDS <= service.keys():
        raise FirewallEvidenceError("Expected service has an invalid shape.")
    name = service["firewall_rule"]
    protocol = _normal_protocol(service["protocol"])
    interface = _normalized(interface_alias)
    ports = service["ports"]
    if (
        not isinstance(name, str)
        or not name.strip()
        or interface in {"", "any", "*"}
        or protocol not in {"tcp", "udp"}
    ):
        raise FirewallEvidenceError("Expected scope has an invalid rule, interface, or protocol.")
    if not isinstance(ports, (list, tuple, set)) or not ports:
        raise FirewallEvidenceError("Expected ports must be a nonempty list of concrete ports.")
    normalized_ports: set[int] = set()
    for port in ports:
        if type(port) is int:
            value = port
        elif isinstance(port, str) and re.fullmatch(r"[0-9]{1,5}", port.strip()) is not None:
            value = int(port)
        else:
            raise FirewallEvidenceError("Expected ports must be a nonempty list of concrete ports.")
        if not 1 <= value <= 65535:
            raise FirewallEvidenceError("Expected ports must be a nonempty list of concrete ports.")
        normalized_ports.add(value)
    try:
        address = _ipv4(local_ipv4)
    except ValueError:
        raise FirewallEvidenceError("Expected local address must be a concrete IPv4 address.") from None
    return name, protocol, normalized_ports, interface, address


def _firewall_state(
    service: dict[str, Any],
    policy: dict[str, Any],
    *,
    interface_alias: str,
    local_ipv4: str,
) -> tuple[str, str]:
    name, protocol, ports, interface, address = _expected_scope(service, interface_alias, local_ipv4)
    if not isinstance(policy, dict):
        raise FirewallEvidenceError("Saved policy has an invalid shape.")
    saved_rules = policy.get("rules")
    if not isinstance(saved_rules, (list, tuple)):
        raise FirewallEvidenceError("Saved policy must contain a list of rules.")
    rules = [
        rule for rule in saved_rules
        if isinstance(rule, dict) and rule.get("display_name") == name
    ]
    if not rules:
        return "missing", _STATUS_EVIDENCE["missing"]
    if len(rules) != 1:
        return "mismatch", _STATUS_EVIDENCE["mismatch"]

    rule = rules[0]
    matches = (
        _is_enabled(rule.get("enabled"))
        and _normalized(rule.get("direction")) == "inbound"
        and _normalized(rule.get("action")) == "allow"
        and _text_scope(rule.get("profile")) == {"private"}
        and _normal_protocol(rule.get("protocol")) == protocol
        and _exact_ports(rule.get("local_ports"), ports)
        and _text_scope(rule.get("interface_aliases")) == {interface}
        and _address_scope(rule.get("local_addresses")) == {address}
    )
    status = "allowed" if matches else "mismatch"
    return status, _STATUS_EVIDENCE[status]


def _ordinary_file(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise FirewallEvidenceError("Saved input contains duplicate JSON fields.")
    return result


def _reject_constant(value: str) -> object:
    raise FirewallEvidenceError("Saved input contains an invalid JSON number.")


def _read_input(path: Path) -> dict[str, Any]:
    try:
        selected = path.lstat()
        if not _ordinary_file(selected):
            raise FirewallEvidenceError("Saved input must be an ordinary file.")
        if selected.st_size > _MAX_BYTES:
            raise FirewallEvidenceError("Saved input exceeds the 256 KiB limit.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _ordinary_file(opened) or not os.path.samestat(selected, opened):
                raise FirewallEvidenceError("Saved input changed while opening.")
            payload = stream.read(_MAX_BYTES + 1)
    except FirewallEvidenceError:
        raise
    except (OSError, ValueError):
        raise FirewallEvidenceError("Unable to read the saved input.") from None
    if len(payload) > _MAX_BYTES:
        raise FirewallEvidenceError("Saved input exceeds the 256 KiB limit.")

    try:
        raw = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_unique_fields, parse_constant=_reject_constant
        )
    except FirewallEvidenceError:
        raise
    except (ValueError, RecursionError):
        raise FirewallEvidenceError("Saved input must contain valid UTF-8 JSON.") from None
    if not isinstance(raw, dict) or raw.keys() != _INPUT_FIELDS:
        raise FirewallEvidenceError("Saved input has an invalid shape.")
    service, policy = raw["service"], raw["policy"]
    if (
        not isinstance(service, dict)
        or service.keys() != _SERVICE_FIELDS
        or not isinstance(service["ports"], list)
    ):
        raise FirewallEvidenceError("Expected service has an invalid shape.")
    if not isinstance(policy, dict) or policy.keys() != {"rules"} or not isinstance(policy["rules"], list):
        raise FirewallEvidenceError("Saved policy has an invalid shape.")
    if any(
        not isinstance(rule, dict)
        or not isinstance(rule.get("display_name"), str)
        or not rule["display_name"].strip()
        for rule in policy["rules"]
    ):
        raise FirewallEvidenceError("Saved policy rows must have rule names.")
    return raw


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise FirewallEvidenceError("Invalid arguments. Use --help for usage.")


def main(
    argv: list[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    parser = _ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", required=True, type=Path, help="Saved UTF-8 scope and rule evidence JSON.")
    try:
        args = parser.parse_args(argv)
        saved = _read_input(args.input)
        status, _ = _firewall_state(
            saved["service"],
            saved["policy"],
            interface_alias=saved["interface_alias"],
            local_ipv4=saved["local_ipv4"],
        )
    except FirewallEvidenceError as error:
        errors.write(f"ERROR: {error}\n")
        return 2

    json.dump({"status": status}, output)
    output.write("\n")
    return 0 if status == "allowed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
