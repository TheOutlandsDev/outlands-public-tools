"""Focused checks for saved response boundaries and output fields."""

from __future__ import annotations

import struct
import unittest

from game_server_status.parser import parse_a2s_info, parse_quake3_status


A2S_HEADER = b"\xff\xff\xff\xffI\x11"
A2S_METADATA = b"Fictional Server\x00fictional_map\x00demo\x00Fictional Game\x00"


class GameServerStatusParserTests(unittest.TestCase):
    def test_a2s_rejects_truncated_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "unterminated A2S string"):
            parse_a2s_info(A2S_HEADER + A2S_METADATA[:-1])
        fields = struct.pack("<HBBB", 1234, 4, 20, 2)
        for size in range(len(fields)):
            with self.subTest(available_count_field_bytes=size):
                with self.assertRaisesRegex(ValueError, "truncated A2S player fields"):
                    parse_a2s_info(A2S_HEADER + A2S_METADATA + fields[:size])

    def test_quake3_handles_missing_and_invalid_capacity(self) -> None:
        for setting in (b"", b"\\sv_maxclients\\unknown"):
            with self.subTest(setting=setting):
                result = parse_quake3_status(
                    b"statusResponse\r\n\\hostname\\Fictional Arena"
                    + setting
                    + b'\r\n\r\n0 70 "Fictional Player"\r\n'
                )
                self.assertEqual(result["server_name"], "Fictional Arena")
                self.assertEqual(result["players"], 1)
                self.assertIsNone(result["max_players"])
                self.assertIsNone(result["bots"])

    def test_parser_output_contains_only_allowlisted_metadata(self) -> None:
        a2s = parse_a2s_info(
            A2S_HEADER
            + A2S_METADATA
            + struct.pack("<HBBB", 1234, 4, 20, 2)
            + b"ignored fictional trailer"
        )
        self.assertEqual(
            a2s,
            {
                "protocol": 17,
                "server_name": "Fictional Server",
                "map": "fictional_map",
                "folder": "demo",
                "game": "Fictional Game",
                "app_id": 1234,
                "players": 4,
                "max_players": 20,
                "bots": 2,
            },
        )

        quake3 = parse_quake3_status(
            b"statusResponse\n"
            b"\\sv_hostname\\Fictional Arena\\mapname\\fictional_map"
            b"\\sv_maxClients\\24\\extraSetting\\omitted fictional value\n"
            b'5 50 "Omitted Fictional Player"\n'
        )
        self.assertEqual(
            quake3,
            {
                "players": 1,
                "max_players": 24,
                "bots": None,
                "server_name": "Fictional Arena",
                "map": "fictional_map",
            },
        )
