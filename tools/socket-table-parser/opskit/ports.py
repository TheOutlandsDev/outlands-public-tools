"""Parse saved Windows netstat and Linux socket tables."""

from __future__ import annotations

from ipaddress import IPv6Address, ip_address
import re
from typing import Any


TCP_STATES = {
    "01": "ESTABLISHED",
    "02": "SYN_SENT",
    "03": "SYN_RECV",
    "04": "FIN_WAIT1",
    "05": "FIN_WAIT2",
    "06": "TIME_WAIT",
    "07": "CLOSE",
    "08": "CLOSE_WAIT",
    "09": "LAST_ACK",
    "0A": "LISTEN",
    "0B": "CLOSING",
}
_PROTOCOLS = {"tcp", "tcp6", "udp", "udp6"}
_MAX_PORT = 65_535
_MAX_PID = 4_294_967_295
_HEX = re.compile(r"[0-9a-fA-F]+")
_TCP_STATE = re.compile(r"[A-Z][A-Z0-9_]*")


def _decimal(value: str, maximum: int) -> int:
    if not value.isascii() or not value.isdecimal():
        raise ValueError("Expected an unsigned decimal number.")
    digits = value.lstrip("0") or "0"
    if len(digits) > len(str(maximum)):
        raise ValueError("Number is out of range.")
    number = int(digits)
    if number > maximum:
        raise ValueError("Number is out of range.")
    return number


def _endpoint(value: str, *, remote: bool = False) -> tuple[str, int | None]:
    if remote and value in {"*:*", "*"}:
        return "*", None
    if value.startswith("["):
        address, separator, port_text = value[1:].partition("]:")
        if not separator or not isinstance(ip_address(address), IPv6Address):
            raise ValueError("Expected a bracketed IPv6 endpoint.")
    else:
        address, separator, port_text = value.rpartition(":")
        if not separator or (address != "*" and ip_address(address).version != 4):
            raise ValueError("Expected an IPv4 or wildcard endpoint.")
    if remote and port_text == "*":
        return address, None
    return address, _decimal(port_text, _MAX_PORT)


def parse_windows_netstat(
    text: str,
    *,
    include_connections: bool = False,
) -> list[dict[str, Any]]:
    """Return records from a saved Windows netstat numeric table."""
    rows: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        parts = raw_line.split()
        if not parts:
            continue
        protocol = parts[0].lower()
        if protocol == "tcp" and len(parts) == 5:
            state = parts[3].upper()
            if not _TCP_STATE.fullmatch(state):
                continue
            if not include_connections and state not in {"LISTENING", "LISTEN"}:
                continue
        elif protocol == "udp" and len(parts) == 4:
            state = "BOUND"
        else:
            continue
        try:
            local_address, local_port = _endpoint(parts[1])
            remote_address, remote_port = _endpoint(parts[2], remote=True)
            pid = _decimal(parts[-1], _MAX_PID)
        except ValueError:
            continue
        rows.append(
            {
                "protocol": protocol,
                "local_address": local_address,
                "local_port": local_port,
                "remote_address": remote_address if include_connections else None,
                "remote_port": remote_port if include_connections else None,
                "state": state,
                "pid": pid,
            }
        )
    return rows


def _decode_proc_address(address_hex: str) -> str:
    raw = bytes.fromhex(address_hex)
    reordered = b"".join(raw[index : index + 4][::-1] for index in range(0, len(raw), 4))
    address = ip_address(reordered)
    if isinstance(address, IPv6Address) and address.ipv4_mapped is not None:
        return f"::ffff:{address.ipv4_mapped}"
    return str(address)


def _proc_endpoint(value: str, width: int) -> tuple[str, int]:
    address, separator, port = value.partition(":")
    if (
        not separator
        or len(address) != width
        or len(port) != 4
        or not _HEX.fullmatch(address)
        or not _HEX.fullmatch(port)
    ):
        raise ValueError("Expected a hexadecimal proc endpoint.")
    return _decode_proc_address(address), int(port, 16)


def parse_proc_net(
    text: str,
    protocol: str,
    *,
    include_connections: bool = False,
) -> list[dict[str, Any]]:
    """Return records from a saved Linux tcp, tcp6, udp, or udp6 table."""
    if protocol not in _PROTOCOLS:
        raise ValueError("Expected tcp, tcp6, udp, or udp6.")
    width = 32 if protocol.endswith("6") else 8
    is_udp = protocol.startswith("udp")
    rows: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        fields = raw_line.split()
        if len(fields) < 10:
            continue
        slot = fields[0]
        if not slot.endswith(":") or not slot[:-1].isascii() or not slot[:-1].isdecimal():
            continue
        state_hex = fields[3].upper()
        if len(state_hex) != 2 or not _HEX.fullmatch(state_hex):
            continue
        if not is_udp and not include_connections and state_hex != "0A":
            continue
        try:
            local_address, local_port = _proc_endpoint(fields[1], width)
            remote_address, remote_port = _proc_endpoint(fields[2], width)
        except ValueError:
            continue
        rows.append(
            {
                "protocol": "udp" if is_udp else "tcp",
                "local_address": local_address,
                "local_port": local_port,
                "remote_address": remote_address if include_connections else None,
                "remote_port": remote_port if include_connections else None,
                "state": "BOUND" if is_udp else TCP_STATES.get(state_hex, state_hex),
                "pid": None,
            }
        )
    return rows
