"""Original MIT generated/loopback tests. No packet capture or external requests."""
from datetime import datetime, timezone
import http.client
import importlib.util
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from resource_monitor.core import Collector, DemoProvider, LiveProvider, MonitorError, Store, export_csv, export_json, interval_seconds, save_fresh
from resource_monitor.server import MonitorApp


class Provider:
    mode = "demo"

    def __init__(self, values):
        self.values = iter(values)

    def read(self):
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return value


def raw(cpu=20, received=100, sent=50):
    return {"cpu_percent": cpu, "memory": {"percent": 40, "used_bytes": 40, "total_bytes": 100},
            "network": {"received_bytes": received, "sent_bytes": sent}}


class SamplingTests(unittest.TestCase):
    def collector(self, values, clocks):
        clock = iter(clocks)
        return Collector(Provider(values), clock=lambda: next(clock), utc_now=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_demo_is_deterministic_and_fictional(self):
        one, two = DemoProvider(), DemoProvider()
        self.assertEqual([one.read() for _ in range(4)], [two.read() for _ in range(4)])
        self.assertEqual(one.mode, "demo")

    def test_first_cpu_and_network_rate_are_unavailable(self):
        sample = self.collector([raw()], [0]).collect()
        self.assertIsNone(sample["cpu_percent"])
        self.assertIsNone(sample["network"]["received_bps"])
        self.assertEqual(sample["issues"], ["cpu_warming_up"])

    def test_rates_use_monotonic_elapsed_time(self):
        collector = self.collector([raw(), raw(35, 300, 150)], [10, 12])
        collector.collect()
        sample = collector.collect()
        self.assertEqual(sample["cpu_percent"], 35)
        self.assertEqual(sample["network"]["received_bps"], 100)
        self.assertEqual(sample["network"]["sent_bps"], 50)

    def test_counter_reset_is_gap_not_negative_rate(self):
        collector = self.collector([raw(), raw(25, 5, 3), raw(30, 25, 13)], [1, 2, 4])
        collector.collect()
        reset = collector.collect()
        recovered = collector.collect()
        self.assertTrue(reset["network"]["counter_reset"])
        self.assertIsNone(reset["network"]["received_bps"])
        self.assertEqual(recovered["network"]["received_bps"], 10)

    def test_missing_network_clears_previous_baseline(self):
        missing = raw()
        missing["network"] = None
        collector = self.collector([raw(), missing, raw(30, 300, 200)], [1, 2, 3])
        collector.collect()
        self.assertIn("network_unavailable", collector.collect()["issues"])
        self.assertIsNone(collector.collect()["network"]["received_bps"])

    def test_missing_or_invalid_metrics_never_become_false_zero(self):
        invalid = {"cpu_percent": math.nan, "memory": {"percent": 120, "used_bytes": -3, "total_bytes": True},
                   "network": {"received_bytes": -1, "sent_bytes": True}}
        collector = self.collector([raw(), invalid], [0, 1])
        collector.collect()
        sample = collector.collect()
        self.assertIsNone(sample["cpu_percent"])
        self.assertTrue(all(value is None for value in sample["memory"].values()))
        self.assertIsNone(sample["network"]["received_bytes"])
        self.assertIn("network_unavailable", sample["issues"])

    def test_provider_failure_is_generic_unavailable(self):
        sample = self.collector([RuntimeError("Fictional private upstream detail")], [0]).collect()
        self.assertNotIn("private", json.dumps(sample))
        self.assertIn("memory_unavailable", sample["issues"])

    def test_clock_not_advanced_does_not_divide_by_zero(self):
        collector = self.collector([raw(), raw(30, 200, 100)], [1, 1])
        collector.collect()
        sample = collector.collect()
        self.assertIsNone(sample["network"]["received_bps"])
        self.assertIn("clock_not_advanced", sample["issues"])

    def test_invalid_clock_is_refused(self):
        for value in [math.nan, math.inf, None, True]:
            with self.subTest(clock=value), self.assertRaises(MonitorError):
                Collector(DemoProvider(), clock=lambda: value).collect()

    def test_invalid_interval_bounds(self):
        for value in [True, 0, .199, 61, math.nan, math.inf, "1"]:
            with self.subTest(interval=value), self.assertRaises(MonitorError):
                interval_seconds(value)

    def test_history_is_bounded_and_snapshot_defensive(self):
        store = Store("demo", 2, .2)
        collector = self.collector([raw(), raw(), raw()], [0, 1, 2])
        for _ in range(3):
            store.add(collector.collect())
        sample = store.snapshot()
        self.assertEqual([row["sequence"] for row in sample["samples"]], [2, 3])
        sample["samples"][0]["memory"]["percent"] = 999
        self.assertEqual(store.snapshot()["samples"][0]["memory"]["percent"], 40)

    def test_history_invalid_capacity_and_limits(self):
        for size in [0, 601, True, 1.5]:
            with self.subTest(size=size), self.assertRaises(MonitorError):
                Store("demo", size)
        for limit in [0, 3, True]:
            with self.subTest(limit=limit), self.assertRaises(MonitorError):
                Store("demo", 2).snapshot(limit)

    def test_sampling_error_is_explicit_and_recovers_on_success(self):
        store = Store("demo")
        store.mark_sampling_error()
        self.assertTrue(store.snapshot()["sampling_error"])
        store.add(self.collector([raw()], [0]).collect())
        self.assertFalse(store.snapshot()["sampling_error"])

    def test_extremely_small_clock_delta_cannot_emit_infinite_json(self):
        collector = self.collector([raw(), raw(30, 200, 100)], [0, 5e-324])
        collector.collect()
        sample = collector.collect()
        self.assertIsNone(sample["network"]["received_bps"])
        self.assertIn("network_rate_unavailable", sample["issues"])
        self.assertNotIn(b"Infinity", export_json(sample))

    def test_exports_are_strict_json_and_csv_with_no_machine_identifiers(self):
        store = Store("demo", 2)
        store.add(self.collector([raw()], [0]).collect())
        output = export_json(store.snapshot())
        self.assertEqual(json.loads(output)["mode"], "demo")
        self.assertNotIn(b"hostname", output)
        self.assertNotIn(b"address", output)
        self.assertIn(b"received_bytes_per_second", export_csv(store.snapshot()))

    def test_export_is_exclusive_and_retains_existing_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "fresh.json"
            save_fresh(target, b"first")
            with self.assertRaises(MonitorError):
                save_fresh(target, b"replacement")
            self.assertEqual(target.read_bytes(), b"first")

    def test_export_does_not_create_missing_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "missing" / "fresh.json"
            with self.assertRaises(MonitorError):
                save_fresh(target, b"data")
            self.assertFalse(target.parent.exists())

    def test_export_requires_an_absolute_private_destination(self):
        with self.assertRaises(MonitorError):
            save_fresh("relative-report.json", b"fictional")
        self.assertFalse((ROOT / "relative-report.json").exists())

    def test_linked_export_parent_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            real = Path(folder) / "real"
            real.mkdir()
            link = Path(folder) / "linked"
            try:
                link.symlink_to(real, target_is_directory=True)
            except OSError:
                self.skipTest("This account cannot create symlinks")
            with self.assertRaises(MonitorError):
                save_fresh(link / "fresh.json", b"data")
            self.assertFalse((real / "fresh.json").exists())

    def test_live_aggregate_sampling_when_dependency_available(self):
        if importlib.util.find_spec("psutil") is None:
            if os.environ.get("RESOURCE_MONITOR_REQUIRE_LIVE") == "1":
                self.fail("The CI-required live dependency is missing")
            self.skipTest("Optional psutil dependency is not installed")
        collector = Collector(LiveProvider())
        first = collector.collect()
        time.sleep(.2)
        second = collector.collect()
        self.assertEqual(first["mode"], "live")
        self.assertIsNone(first["cpu_percent"])
        self.assertIsInstance(second["cpu_percent"], float)
        self.assertGreater(second["memory"]["total_bytes"], 0)
        self.assertGreaterEqual(second["network"]["received_bytes"], 0)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.app = MonitorApp(DemoProvider(), port=0, interval=.2, capacity=4).start()
        self.addCleanup(self.app.close)

    def request(self, path="/api/history", token=True, method="GET", headers=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.app.port, timeout=3)
        values = {} if headers is None else dict(headers)
        if token:
            values.setdefault("X-Outlands-Token", self.app.token)
        try:
            connection.request(method, path, body=body, headers=values)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_loopback_history_returns_demo_schema(self):
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        value = json.loads(body)
        self.assertEqual(value["schema"], 1)
        self.assertEqual(value["mode"], "demo")
        self.assertLessEqual(len(value["samples"]), 4)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_snapshot_endpoint_uses_same_bounded_state(self):
        status, _, body = self.request("/api/snapshot")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["mode"], "demo")

    def test_token_required_and_never_reflected(self):
        status, _, body = self.request(token=False)
        self.assertEqual(status, 403)
        self.assertNotIn(self.app.token.encode(), body)

    def test_wrong_or_non_ascii_token_is_refused(self):
        for token in ["wrong", "x" * 129, "\xe9"]:
            status, _, _ = self.request(headers={"X-Outlands-Token": token})
            self.assertEqual(status, 403)

    def test_query_token_is_not_authentication(self):
        status, _, _ = self.request("/api/history?token=" + self.app.token, token=False)
        self.assertEqual(status, 403)

    def test_wrong_host_is_refused(self):
        for host in ["example.invalid", "localhost:" + str(self.app.port), "127.0.0.1:1"]:
            status, _, _ = self.request(headers={"Host": host})
            self.assertEqual(status, 403)

    def test_cross_origin_is_refused_without_cors(self):
        status, headers, _ = self.request(headers={"Origin": "http://example.invalid"})
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_same_origin_is_allowed(self):
        self.assertEqual(self.request(headers={"Origin": self.app.origin})[0], 200)

    def test_api_is_read_only(self):
        for method in ["POST", "PUT", "DELETE", "PATCH", "OPTIONS"]:
            self.assertEqual(self.request(method=method)[0], 405)

    def test_static_allowlist_and_security_headers(self):
        for path in ["/", "/index.html", "/style.css", "/app.js", "/presentation.mjs"]:
            status, headers, body = self.request(path, token=False)
            self.assertEqual(status, 200)
            self.assertGreater(len(body), 0)
            self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_path_traversal_and_encoded_paths_are_refused(self):
        for path in ["/../LICENSE", "/%2e%2e/LICENSE", "/app.js?token=secret", "/api/../LICENSE", "/api/history#token=x", "/\\LICENSE"]:
            self.assertIn(self.request(path)[0], [400, 404])

    def test_query_validation_is_bounded_and_strict(self):
        for query in ["limit=0", "limit=5", "limit=-1", "limit=1&limit=2", "extra=1", "limit=", "limit=NaN", "limit"]:
            self.assertEqual(self.request("/api/history?" + query)[0], 400, query)
        status, _, body = self.request("/api/history?limit=1")
        self.assertEqual(status, 200)
        self.assertLessEqual(len(json.loads(body)["samples"]), 1)

    def test_exports_require_token_and_have_attachment_names(self):
        for format in ["json", "csv"]:
            self.assertEqual(self.request("/api/export." + format, token=False)[0], 403)
            status, headers, body = self.request("/api/export." + format)
            self.assertEqual(status, 200)
            self.assertIn("attachment", headers["Content-Disposition"])
            self.assertNotIn(self.app.token.encode(), body)

    def test_get_body_is_refused(self):
        self.assertEqual(self.request(body="x")[0], 400)

    def test_large_header_is_refused(self):
        self.assertEqual(self.request(headers={"X-Too-Large": "x" * 9000})[0], 431)

    def test_head_has_no_body(self):
        status, headers, body = self.request("/", method="HEAD", token=False)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertGreater(int(headers["Content-Length"]), 0)

    def test_duplicate_host_or_token_headers_are_refused(self):
        for name, value in [("Host", f"127.0.0.1:{self.app.port}"), ("X-Outlands-Token", self.app.token)]:
            connection = http.client.HTTPConnection("127.0.0.1", self.app.port, timeout=3)
            try:
                connection.putrequest("GET", "/api/history", skip_host=True)
                connection.putheader("Host", f"127.0.0.1:{self.app.port}")
                connection.putheader("X-Outlands-Token", self.app.token)
                connection.putheader(name, value)
                connection.endheaders()
                response = connection.getresponse()
                self.assertEqual(response.status, 403)
                response.read()
            finally:
                connection.close()

    def test_token_is_distinct_per_server_instance(self):
        other = MonitorApp(DemoProvider(), port=0)
        try:
            self.assertNotEqual(other.token, self.app.token)
        finally:
            other.close()

    def test_graceful_stop_closes_worker_and_sampler(self):
        self.app.close()
        self.assertFalse(self.app.worker.is_alive())
        self.assertFalse(self.app.sampler.is_alive())

    def test_shutdown_closes_a_partial_header_connection(self):
        connection = socket.create_connection(("127.0.0.1", self.app.port), timeout=2)
        try:
            connection.sendall(b"GET / HTTP/1.1\r\nHost:")
            deadline = time.monotonic() + 2
            while not self.app.server.connections and time.monotonic() < deadline:
                time.sleep(.01)
            self.app.close()
            self.assertFalse(self.app.worker.is_alive())
            self.assertEqual(len(self.app.server.connections), 0)
        finally:
            connection.close()


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        return subprocess.run([sys.executable, "-B", "-m", "resource_monitor", *args], cwd=ROOT, env=environment,
                              capture_output=True, text=True, encoding="utf-8", timeout=10)

    def test_help_and_no_arguments_are_safe(self):
        for args in [(), ("--help",)]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Resource Monitor", result.stdout)

    def test_demo_is_marked_and_deterministic(self):
        one, two = self.run_cli("demo"), self.run_cli("demo")
        self.assertEqual(one.returncode, 0)
        self.assertEqual(one.stdout, two.stdout)
        self.assertEqual(json.loads(one.stdout)["mode"], "demo")

    def test_live_and_serve_modes_are_explicit(self):
        for args in [("sample",), ("serve",), ("serve", "--demo", "--live")]:
            self.assertNotEqual(self.run_cli(*args).returncode, 0)

    def test_import_opens_no_socket_and_does_not_import_psutil(self):
        code = "from unittest.mock import patch\nimport socket,sys\nwith patch.object(socket.socket,'bind',side_effect=AssertionError('bind')):\n import resource_monitor,resource_monitor.server\nassert 'psutil' not in sys.modules\n"
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_bounds_refused_without_traceback(self):
        for args in [("serve", "--demo", "--history", "601"), ("serve", "--demo", "--interval", "nan"), ("sample", "--live", "--count", "0")]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)

    def test_bounded_demo_server_exits_cleanly(self):
        result = self.run_cli("serve", "--demo", "--port", "0", "--duration", ".2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("http://127.0.0.1:", result.stdout)
        self.assertIn("/#token=", result.stdout)


if __name__ == "__main__":
    unittest.main()
