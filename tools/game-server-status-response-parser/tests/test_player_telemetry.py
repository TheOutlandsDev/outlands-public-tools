"""Preserved parser cases using fictional responses."""

from __future__ import annotations

import struct
import unittest

from game_server_status.parser import parse_a2s_info, parse_quake3_status


class OriginalPlayerTelemetryTests(unittest.TestCase):
    def test_parse_a2s_info_player_counts(self) -> None:
        payload = (
            b"\xff\xff\xff\xffI"
            + bytes([17])
            + b"Fictional Server\x00fictional_map\x00demo\x00Fictional Game\x00"
            + struct.pack("<HBBB", 1234, 4, 20, 2)
        )
        result = parse_a2s_info(payload)
        self.assertEqual(result["server_name"], "Fictional Server")
        self.assertEqual(result["map"], "fictional_map")
        self.assertEqual(result["players"], 4)
        self.assertEqual(result["max_players"], 20)
        self.assertEqual(result["bots"], 2)

    def test_parse_quake3_status_player_lines(self) -> None:
        payload = (
            b"\xff\xff\xff\xffstatusResponse\n"
            b"\\sv_hostname\\Fictional Arena\\mapname\\fictional_map\\sv_maxclients\\18\n"
            b'12 50 "Fictional Player One"\n'
            b'8 75 "Fictional Player Two"\n'
        )
        result = parse_quake3_status(payload)
        self.assertEqual(result["players"], 2)
        self.assertEqual(result["max_players"], 18)
        self.assertEqual(result["server_name"], "Fictional Arena")
        self.assertEqual(result["map"], "fictional_map")

    def test_player_parser_rejects_invalid_packets(self) -> None:
        with self.assertRaises(ValueError):
            parse_a2s_info(b"not-a-server-response")
        with self.assertRaises(ValueError):
            parse_quake3_status(b"not-a-status-response")
