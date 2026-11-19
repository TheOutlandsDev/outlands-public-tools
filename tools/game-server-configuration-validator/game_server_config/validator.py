"""Validate the server declaration portion of a saved configuration."""

from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

_EXPECTED_STATES = {"online", "planned_off"}
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_PROBE_TYPES = {"a2s", "quake3", "tcp_sessions", "jsonl_population"}


def _absolute_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and "\x00" not in value
        and (PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute())
    )


def _valid_port(value: object) -> bool:
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        digits = value.lstrip("0")
        if len(digits) > 5:
            return False
        value = int(digits or "0")
    return type(value) is int and 1 <= value <= 65535


def _validate_health_url(value: object) -> None:
    if (
        not isinstance(value, str)
        or any(character.isspace() or ord(character) < 32 for character in value)
        or "\\" in value
    ):
        raise ValueError("Invalid health URL")
    try:
        url = urlsplit(value)
    except ValueError:
        raise ValueError("Invalid health URL") from None
    if url.scheme not in {"http", "https"}:
        raise ValueError("Health URL must use HTTP(S)")
    if "@" in url.netloc:
        raise ValueError("Credentials are forbidden in health URLs")
    if url.hostname not in _LOOPBACK_HOSTS:
        raise ValueError("Non-loopback health URL is forbidden")
    host = "[::1]" if url.hostname == "::1" else url.hostname
    authority = url.netloc.lower()
    if authority == host:
        return
    if not authority.startswith(f"{host}:") or not _valid_port(authority[len(host) + 1 :]):
        raise ValueError("Invalid health URL port")


def _validate_player_probe(probe: object) -> None:
    if probe is None:
        return
    if not isinstance(probe, dict):
        raise ValueError("Player probe must be an object")
    probe_type = probe.get("type")
    if not isinstance(probe_type, str) or probe_type.casefold() not in _PROBE_TYPES:
        raise ValueError("Unsupported player probe")
    if probe_type.casefold() == "jsonl_population":
        if not _absolute_path(probe.get("path")):
            raise ValueError("JSONL player probe path must be absolute")
        return
    host = probe.get("host", "127.0.0.1")
    if not isinstance(host, str) or host.casefold() not in _LOOPBACK_HOSTS:
        raise ValueError("Non-loopback player probe is forbidden")
    if not _valid_port(probe.get("port")):
        raise ValueError("Invalid player probe port")


def validate_config(config: object) -> int:
    """Validate a saved configuration object and return its server count."""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be an object")
    version = config.get("schema_version")
    if type(version) is not int or version != 1:
        raise ValueError("Unsupported configuration schema")
    servers = config.get("servers")
    if not isinstance(servers, list):
        raise ValueError("Servers must be an array")

    seen: set[str] = set()
    for server in servers:
        if not isinstance(server, dict):
            raise ValueError("Server declarations must be objects")
        server_id = server.get("id")
        if not isinstance(server_id, str) or not server_id.strip() or server_id.strip() in seen:
            raise ValueError("Invalid or duplicate server id")
        seen.add(server_id.strip())

        expected = server.get("expected_state", "online")
        if not isinstance(expected, str) or expected.casefold() not in _EXPECTED_STATES:
            raise ValueError("Invalid expected state")
        if not _absolute_path(server.get("root")):
            raise ValueError("Server root must be absolute")
        health_urls = server.get("health_urls", [])
        if not isinstance(health_urls, list):
            raise ValueError("Health URLs must be an array")
        for url in health_urls:
            _validate_health_url(url)
        _validate_player_probe(server.get("player_probe"))
    return len(servers)
