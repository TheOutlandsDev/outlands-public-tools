"""Test both snapshot formats, data boundaries, and output fields."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from player_telemetry_normalizer import SnapshotError, normalize_snapshot
from player_telemetry_normalizer.normalizer import MAX_INPUT_BYTES, MAX_ROWS, _load_json


class NormalizationTests(unittest.TestCase):
    def test_collector_maps_both_population_fields(self):
        snapshot = {
            "players_connections": [
                {
                    "id": "relay-sample",
                    "server_status": "WARNING",
                    "connection_sessions": 3,
                    "players": 99,
                    "max_players": 8,
                },
                {
                    "id": "lobby-sample",
                    "server_status": "critical",
                    "connection_sessions": 77,
                    "players": 8,
                    "max_players": 16,
                },
            ]
        }
        mapping = {
            "collector": {
                "lobby-sample": {"server_id": "lobby", "metric_kind": "players"},
                "relay-sample": {"server_id": "relay", "metric_kind": "connections"},
            }
        }
        self.assertEqual(
            normalize_snapshot(snapshot, mapping, "collector"),
            {
                "points": [
                    {
                        "server_id": "relay",
                        "state": "degraded",
                        "population": 3,
                        "capacity": 8,
                        "metric_kind": "connections",
                    },
                    {
                        "server_id": "lobby",
                        "state": "offline",
                        "population": 8,
                        "capacity": 16,
                        "metric_kind": "players",
                    },
                ]
            },
        )

    def test_malformed_counts_are_null_and_negative_counts_clamp(self):
        mapping = {"portal": {"sample": {"server_id": "arena", "metric_kind": "auto"}}}
        snapshot = {
            "servers": [
                {"id": "sample", "population": "unknown", "capacity": -5},
                {"id": "sample", "population": True, "capacity": [8]},
                {"id": "sample", "population": " 12 ", "capacity": 16.75},
                {"id": "sample", "population": "3.5", "capacity": None},
            ]
        }
        points = normalize_snapshot(snapshot, mapping, "portal")["points"]
        self.assertEqual(
            [(point["population"], point["capacity"]) for point in points],
            [(None, 0), (None, None), (12, 16), (None, None)],
        )

    def test_unknown_ids_and_unrelated_metadata_are_omitted(self):
        mapping = {"portal": {"sample": {"server_id": "arena", "metric_kind": "auto"}}}
        snapshot = {
            "generatedAt": "2040-01-01T00:00:00Z",
            "servers": [
                {"id": "unmapped", "population": 987},
                {"id": ["malformed"]},
                {"state": "healthy"},
                {
                    "id": "sample",
                    "state": "HEALTHY",
                    "population": 3,
                    "populationLabel": "CoNnEcTiOnS",
                    "capacity": 8,
                    "metadata": {"description": "Fictional test metadata"},
                },
            ],
        }
        original = deepcopy((snapshot, mapping))
        self.assertEqual(
            normalize_snapshot(snapshot, mapping, "portal"),
            {
                "points": [
                    {
                        "server_id": "arena",
                        "state": "online",
                        "population": 3,
                        "capacity": 8,
                        "metric_kind": "connections",
                    },
                ],
            },
        )
        self.assertEqual((snapshot, mapping), original)

    def test_mapping_rejects_malformed_rules(self):
        invalid = [
            {},
            {"portal": []},
            {"portal": {"sample": {"metric_kind": "players"}}},
            {"portal": {"sample": {"server_id": "arena", "metric_kind": []}}},
            {"portal": {"sample": {"server_id": "ñ" * 65, "metric_kind": "players"}}},
            {"portal": {"sample": {"server_id": " ", "metric_kind": "players"}}},
            {"portal": {}, "collector": {"sample": {"server_id": "relay", "metric_kind": "auto"}}},
            {"portal": {}, "unexpected": {}},
        ]
        for mapping in invalid:
            with self.subTest(mapping=mapping), self.assertRaises(SnapshotError):
                normalize_snapshot({"servers": []}, mapping, "portal")

    def test_snapshot_rejects_invalid_shapes(self):
        for snapshot in ([], {}, {"servers": {}}, {"servers": None}, {"servers": [1]}):
            with self.subTest(snapshot=snapshot), self.assertRaises(SnapshotError):
                normalize_snapshot(snapshot, {"portal": {}}, "portal")

        with self.assertRaises(SnapshotError):
            normalize_snapshot({"servers": []}, {"portal": {}}, "unsupported")
        self.assertEqual(normalize_snapshot({"servers": []}, {"portal": {}}, "portal"), {"points": []})

    def test_limits_reject_excessive_rows_and_mappings(self):
        mapping = {"portal": {"sample": {"server_id": "arena", "metric_kind": "auto"}}}
        with self.assertRaises(SnapshotError):
            normalize_snapshot({"servers": [{}] * (MAX_ROWS + 1)}, mapping, "portal")

        rules = {f"sample-{number}": mapping["portal"]["sample"] for number in range(MAX_ROWS + 1)}
        with self.assertRaises(SnapshotError):
            normalize_snapshot({"servers": []}, {"portal": rules}, "portal")

    def test_input_read_rejects_oversize_and_nonregular_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            oversize = parent / "oversize.json"
            oversize.write_bytes(b" " * (MAX_INPUT_BYTES + 1))
            for path in (parent, oversize, parent / "missing.json"):
                with self.subTest(path=path.name), self.assertRaises(SnapshotError):
                    _load_json(path)

    def test_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "snapshot.json"
            for data in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e10000}', b'"\xff"', b"[" * 10000):
                with self.subTest(prefix=data[:20]), self.assertRaises(SnapshotError):
                    source.write_bytes(data)
                    _load_json(source)
