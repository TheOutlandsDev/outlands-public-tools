"""Opt-in native aggregate checks. Captured metrics/tokens are never printed."""
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resource_monitor.core import LiveProvider
from resource_monitor.server import MonitorApp


class NativeLiveModes(unittest.TestCase):
    def setUp(self):
        if importlib.util.find_spec("psutil") is None:
            if os.environ.get("RESOURCE_MONITOR_REQUIRE_LIVE") == "1":
                self.fail("Required native live dependency is missing")
            self.skipTest("Optional psutil dependency is not installed")

    def cli(self, *args, status=0, cwd=ROOT):
        result = subprocess.run([sys.executable, "-B", "-m", "resource_monitor", *args],
                                cwd=cwd, capture_output=True, text=True,
                                encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, status, "Native CLI exit status differs")
        return result

    def valid_history(self, history):
        self.assertEqual(history["mode"], "live")
        self.assertGreaterEqual(len(history["samples"]), 2)
        first, last = history["samples"][0], history["samples"][-1]
        self.assertIsNone(first["cpu_percent"])
        self.assertIsInstance(last["cpu_percent"], float)
        self.assertGreater(last["memory"]["total_bytes"], 0)
        self.assertGreaterEqual(last["network"]["received_bytes"], 0)

    def get(self, origin, token, route):
        request = urllib.request.Request(origin + route, headers={"X-Outlands-Token": token})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=2) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            with error:
                return error.code, error.read()

    def test_bounded_native_json_and_csv_cli(self):
        result = self.cli("sample", "--live", "--count", "2", "--interval", ".2")
        self.valid_history(json.loads(result.stdout))
        result = self.cli("sample", "--live", "--count", "2", "--interval", ".2", "--format", "csv")
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["mode"] for row in rows}, {"live"})
        self.assertGreater(int(rows[-1]["memory_total_bytes"]), 0)

    def test_native_export_is_explicit_and_existing_bytes_survive(self):
        with tempfile.TemporaryDirectory(prefix="monitor-private-") as temporary:
            target = Path(temporary) / "private-live.json"
            args = ("sample", "--live", "--count", "2", "--interval", ".2", "--output", str(target))
            result = self.cli(*args)
            self.assertEqual(result.stdout, "")
            original = target.read_bytes()
            self.valid_history(json.loads(original))
            self.cli(*args, status=2)
            self.assertTrue(target.read_bytes() == original, "Existing private export changed")
            self.assertEqual({p.name for p in Path(temporary).iterdir()}, {target.name})

    def test_native_loopback_history_and_export_require_current_token(self):
        with MonitorApp(LiveProvider(), port=0, interval=.2, capacity=6) as app:
            deadline = time.monotonic() + 3
            while len(app.store.snapshot()["samples"]) < 2 and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertEqual(self.get(app.origin, "", "/api/history")[0], 403)
            status, body = self.get(app.origin, app.token, "/api/history")
            self.assertEqual(status, 200)
            self.valid_history(json.loads(body))
            self.assertEqual(self.get(app.origin, app.token, "/api/export.json")[0], 200)
            status, body = self.get(app.origin, app.token, "/api/export.csv")
            self.assertEqual(status, 200)
            self.assertTrue(all(row["mode"] == "live" for row in csv.DictReader(io.StringIO(body.decode()))))

    def test_native_cli_server_stops_and_restart_rejects_old_token(self):
        def start():
            child = subprocess.Popen([sys.executable, "-B", "-m", "resource_monitor", "serve", "--live",
                                      "--port", "0", "--interval", ".2", "--duration", "2"],
                                     cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, encoding="utf-8")
            lines = queue.Queue()
            def read():
                for line in child.stdout:
                    lines.put(line)
                lines.put(None)
            thread = threading.Thread(target=read, daemon=True)
            thread.start()
            def close():
                if child.poll() is None:
                    child.terminate()
                child.wait(timeout=5)
                thread.join(timeout=2)
                child.stdout.close()
                child.stderr.close()
            self.addCleanup(close)
            while True:
                line = lines.get(timeout=10)
                self.assertIsNotNone(line, "Native server did not start")
                if line.startswith("http://127.0.0.1:"):
                    parts = urlsplit(line.strip())
                    return child, parts.scheme + "://" + parts.netloc, parse_qs(parts.fragment)["token"][0]
        first, origin, token = start()
        self.assertEqual(self.get(origin, token, "/api/history")[0], 200)
        self.assertEqual(first.wait(timeout=7), 0)
        second, origin, fresh = start()
        self.assertTrue(token != fresh, "Restart reused its capability token")
        self.assertEqual(self.get(origin, token, "/api/history")[0], 403)
        self.assertEqual(self.get(origin, fresh, "/api/history")[0], 200)
        self.assertEqual(second.wait(timeout=7), 0)


if __name__ == "__main__":
    unittest.main()
