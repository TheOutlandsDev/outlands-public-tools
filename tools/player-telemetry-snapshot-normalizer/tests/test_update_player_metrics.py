"""Original snapshot normalization cases with fictional identifiers."""

import unittest

from player_telemetry_normalizer import normalize_snapshot


class OriginalNormalizationTests(unittest.TestCase):
    def test_availability_only_point_preserves_original_fallback(self):
        snapshot = {
            "servers": [
                {
                    "id": "fictional-beacon",
                    "state": "online",
                    "population": 1,
                    "populationLabel": "assumed online",
                }
            ]
        }
        mapping = {
            "portal": {
                "fictional-beacon": {
                    "server_id": "beacon",
                    "metric_kind": "availability_only",
                }
            }
        }
        points = normalize_snapshot(snapshot, mapping, "portal")["points"]
        self.assertEqual(points[0]["metric_kind"], "availability_only")

    def test_portal_population_preserves_player_and_connection_units(self):
        snapshot = {
            "servers": [
                {
                    "id": "fictional-lobby",
                    "state": "online",
                    "population": 8,
                    "populationLabel": "players",
                },
                {
                    "id": "fictional-relay",
                    "state": "online",
                    "population": 8,
                    "populationLabel": "connections",
                },
            ]
        }
        mapping = {
            "portal": {
                "fictional-lobby": {"server_id": "lobby", "metric_kind": "auto"},
                "fictional-relay": {"server_id": "relay", "metric_kind": "auto"},
            }
        }
        points = normalize_snapshot(snapshot, mapping, "portal")["points"]
        self.assertEqual(
            points[0],
            {
                "server_id": "lobby",
                "state": "online",
                "population": 8,
                "capacity": None,
                "metric_kind": "players",
            },
        )
        self.assertEqual(
            points[1],
            {
                "server_id": "relay",
                "state": "online",
                "population": 8,
                "capacity": None,
                "metric_kind": "connections",
            },
        )
