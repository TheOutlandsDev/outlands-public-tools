import json
import unittest

from assistant_operations_status import _compact_operations_evidence, _format_operations_status


class OperationsStatusTests(unittest.TestCase):
    def test_compact_evidence_keeps_service_and_endpoint_health(self) -> None:
        encoded = json.dumps(
            {
                "ok": True,
                "result": {
                    "generated": "2020-01-02T00:00:00Z",
                    "summary": {"healthy": 1, "warning": 0, "down": 0},
                    "programs": [
                        {
                            "id": "example-mail",
                            "status": "healthy",
                            "processes": [],
                            "listeners": {"tcp": [18080, 18787], "udp": []},
                            "tasks": [],
                            "services": [
                                {
                                    "name": "Example Mail Service",
                                    "state": "Running",
                                    "start_mode": "Auto",
                                    "healthy": True,
                                }
                            ],
                            "endpoints": [
                                {
                                    "url": "http://127.0.0.1:18787/api/health",
                                    "healthy": True,
                                    "status": 200,
                                    "milliseconds": 12,
                                    "ignored": "large response body",
                                }
                            ],
                            "state": None,
                            "issues": [],
                        }
                    ],
                },
            }
        )
        compact = json.loads(_compact_operations_evidence(encoded))
        program = compact["programs"][0]
        self.assertEqual(compact["summary"]["healthy"], 1)
        self.assertEqual(program["services"][0]["name"], "Example Mail Service")
        self.assertEqual(program["endpoints"][0]["status"], 200)
        self.assertNotIn("ignored", program["endpoints"][0])

    def test_instant_status_includes_current_ownership_evidence(self) -> None:
        encoded = json.dumps(
            {
                "ok": True,
                "result": {
                    "programs": [
                        {
                            "name": "Example Mail",
                            "status": "healthy",
                            "processes": [{"name": "example-worker", "pid": 1234}],
                            "tasks": [
                                {
                                    "name": "Example Mail Scheduler",
                                    "installed": True,
                                    "state": "Running",
                                    "last_result": "0x00041301",
                                }
                            ],
                            "services": [
                                {
                                    "name": "Example Mail Service",
                                    "state": "Running",
                                    "start_mode": "Auto",
                                }
                            ],
                            "listeners": {"tcp": [18080, 18787], "udp": []},
                            "endpoints": [
                                {
                                    "url": "http://127.0.0.1:18787/api/health",
                                    "healthy": True,
                                    "status": 200,
                                }
                            ],
                            "state": None,
                            "issues": [],
                        }
                    ]
                },
            }
        )
        rendered = _format_operations_status(encoded)
        self.assertIn("Example Mail", rendered)
        self.assertIn("Example Mail Scheduler: Running", rendered)
        self.assertIn("Example Mail Service: Running (Auto)", rendered)
        self.assertIn("18080, 18787", rendered)
        self.assertIn("api/health=200 (healthy)", rendered)
        self.assertIn("Issues: none", rendered)
