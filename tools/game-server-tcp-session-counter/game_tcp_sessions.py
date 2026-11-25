"""Count game server sessions from a saved socket table."""

import argparse
from ipaddress import ip_address
import json
from pathlib import Path
from typing import Any


MAX_INPUT_BYTES = 1024 * 1024
MAX_PORT = 65535
MAX_PID = 2**32 - 1
LOOPBACK_ADDRESSES = {"127.0.0.1", "::1"}
SELECTION_FIELDS = {
    "process_ids", "configured_ports", "listener_ports", "exclude_local_peers", "local_addresses",
}


def count_tcp_sessions(rows: list[dict[str, Any]], selection: dict[str, Any]) -> dict[str, Any]:
    """Apply the original owner, port, state, and local-peer filters to saved rows."""
    process_ids = set(selection["process_ids"])
    tcp_ports = set(selection["configured_ports"]) | set(selection["listener_ports"])
    all_sessions = [
        row for row in rows
        if row["protocol"] == "tcp" and row["pid"] in process_ids
        and row["state"] == "ESTABLISHED" and row["local_port"] in tcp_ports
    ]
    exclude_local_peers = selection["exclude_local_peers"]
    local_addresses = set()
    if exclude_local_peers:
        local_addresses = LOOPBACK_ADDRESSES | {
            address.split("%", 1)[0] for address in selection["local_addresses"]
        }
    sessions = [
        row for row in all_sessions
        if (row["remote_address"] or "").split("%", 1)[0] not in local_addresses
    ]
    internal_sessions = len(all_sessions) - len(sessions)
    peers = {row["remote_address"] for row in sessions if row["remote_address"] not in (None, "", "*")}
    return {
        "connection_sessions": len(sessions),
        "internal_connection_sessions": internal_sessions,
        "unique_peers": len(peers),
        "connection_evidence": (
            "ESTABLISHED external TCP sessions on monitored server ports"
            if exclude_local_peers
            else "ESTABLISHED TCP sessions on monitored server ports"
        ),
    }


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-JSON constant")


def read_json(path: Path) -> Any:
    try:
        if not path.is_file():
            raise OSError
        with path.open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise ValueError("Unable to read the saved input.") from None
    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError("The saved input exceeds the 1 MiB limit.")
    try:
        return json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
    except (ValueError, RecursionError):
        raise ValueError("Invalid saved JSON.") from None


def bounded_integer(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def validate_addresses(addresses):
    for address in addresses:
        if not isinstance(address, str) or len(address) > 120:
            raise ValueError("Invalid saved IP address.")
        try:
            ip_address(address)
        except ValueError:
            raise ValueError("Invalid saved IP address.") from None


def read_selection(path):
    selection = read_json(path)
    if not isinstance(selection, dict) or selection.keys() != SELECTION_FIELDS:
        raise ValueError("Invalid session selection fields.")
    for name, minimum, maximum in (
        ("process_ids", 0, MAX_PID),
        ("configured_ports", 1, MAX_PORT),
        ("listener_ports", 1, MAX_PORT),
    ):
        values = selection[name]
        if not isinstance(values, list) or not all(bounded_integer(value, minimum, maximum) for value in values):
            raise ValueError("Invalid process ID or port in the session selection.")
    if type(selection["exclude_local_peers"]) is not bool or not isinstance(selection["local_addresses"], list):
        raise ValueError("Invalid local-peer selection.")
    validate_addresses(selection["local_addresses"])
    return selection


def read_rows(path):
    table = read_json(path)
    if not isinstance(table, dict) or table.keys() != {"rows"} or not isinstance(table["rows"], list):
        raise ValueError("Expected a saved socket table with a rows array.")
    required = {"protocol", "pid", "state", "local_port", "remote_address"}
    for row in table["rows"]:
        if (not isinstance(row, dict) or not required.issubset(row)
                or not isinstance(row["protocol"], str) or not isinstance(row["state"], str)):
            raise ValueError("Invalid socket row.")
        if row["pid"] is not None and not bounded_integer(row["pid"], 0, MAX_PID):
            raise ValueError("Invalid socket owner PID.")
        if row["local_port"] is not None and not bounded_integer(row["local_port"], 0, MAX_PORT):
            raise ValueError("Invalid socket local port.")
        if row["remote_address"] not in (None, "*"):
            validate_addresses([row["remote_address"]])
    return table["rows"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path, help="Saved process, port and local-peer selection")
    parser.add_argument("table", type=Path, help="Saved normalized socket-table JSON")
    args = parser.parse_args()
    try:
        report = count_tcp_sessions(read_rows(args.table), read_selection(args.selection))
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
