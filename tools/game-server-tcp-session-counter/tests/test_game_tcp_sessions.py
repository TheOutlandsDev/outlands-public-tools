"""Original local headless session assertions with documentation addresses."""

from game_tcp_sessions import count_tcp_sessions


def test_tcp_session_probe_excludes_local_headless_connections() -> None:
    selection = {
        "process_ids": [4242],
        "configured_ports": [27015],
        "listener_ports": [27015],
        "exclude_local_peers": True,
        "local_addresses": ["192.0.2.10", "192.0.2.11"],
    }
    sockets = [
        {
            "pid": 4242,
            "state": "ESTABLISHED",
            "protocol": "tcp",
            "local_port": 27015,
            "remote_address": address,
        }
        for address in ("192.0.2.10", "198.51.100.21")
    ]

    rows = [count_tcp_sessions(sockets, selection)]

    assert len(rows) == 1
    assert rows[0]["connection_sessions"] == 1
    assert rows[0]["internal_connection_sessions"] == 1
    assert rows[0]["unique_peers"] == 1
    assert rows[0]["connection_evidence"].startswith("ESTABLISHED external")
