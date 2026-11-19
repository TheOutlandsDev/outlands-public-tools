"""Read saved game server status response metadata."""

from __future__ import annotations

import struct
from typing import Any


def _read_c_string(payload: bytes, offset: int) -> tuple[str, int]:
    end = payload.find(b"\x00", offset)
    if end < 0:
        raise ValueError("unterminated A2S string")
    return payload[offset:end].decode("utf-8", errors="replace"), end + 1


def parse_a2s_info(payload: bytes) -> dict[str, Any]:
    """Return the metadata fields from a saved A2S_INFO response."""
    if len(payload) < 6 or payload[:4] != b"\xff\xff\xff\xff":
        raise ValueError("invalid A2S response header")
    if payload[4] != 0x49:
        raise ValueError(f"unexpected A2S response type 0x{payload[4]:02x}")
    offset = 5
    protocol = payload[offset]
    offset += 1
    server_name, offset = _read_c_string(payload, offset)
    map_name, offset = _read_c_string(payload, offset)
    folder, offset = _read_c_string(payload, offset)
    game, offset = _read_c_string(payload, offset)
    if len(payload) < offset + 5:
        raise ValueError("truncated A2S player fields")
    app_id = struct.unpack_from("<H", payload, offset)[0]
    offset += 2
    players, max_players, bots = payload[offset : offset + 3]
    return {
        "protocol": protocol,
        "server_name": server_name,
        "map": map_name,
        "folder": folder,
        "game": game,
        "app_id": app_id,
        "players": players,
        "max_players": max_players,
        "bots": bots,
    }


def parse_quake3_status(payload: bytes) -> dict[str, Any]:
    """Return aggregate metadata from a saved Quake 3 status response."""
    if payload.startswith(b"\xff\xff\xff\xff"):
        payload = payload[4:]
    text = payload.decode("utf-8", errors="replace").replace("\r", "")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "statusResponse":
        raise ValueError("unexpected Quake 3 status response")
    info_line = lines[1].strip() if len(lines) > 1 else ""
    parts = info_line.split("\\")
    if parts and not parts[0]:
        parts = parts[1:]
    info = {
        parts[index]: parts[index + 1]
        for index in range(0, len(parts) - 1, 2)
    }
    player_lines = [line for line in lines[2:] if line.strip()]
    max_players = info.get("sv_maxclients") or info.get("sv_maxClients")
    try:
        capacity = int(max_players) if max_players is not None else None
    except ValueError:
        capacity = None
    return {
        "players": len(player_lines),
        "max_players": capacity,
        "bots": None,
        "server_name": info.get("sv_hostname") or info.get("hostname") or "",
        "map": info.get("mapname") or "",
    }
