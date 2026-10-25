"""Loopback read-only dashboard/API. Original MIT code, no outbound HTTP client."""
from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
from pathlib import Path
import secrets
import socket
import threading
from urllib.parse import parse_qs, urlsplit

from .core import Collector, MonitorError, Store, export_csv, export_json, integer, interval_seconds

STATIC = Path(__file__).resolve().parent / "static"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/presentation.mjs": ("presentation.mjs", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8")}
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"


class _HeaderReader:
    def __init__(self, stream):
        self.stream, self.remaining = stream, 8192

    def readline(self, size=-1):
        value = self.stream.readline(min(self.remaining + 1, size) if size >= 0 else self.remaining + 1)
        self.remaining -= len(value)
        if self.remaining < 0:
            raise http.client.LineTooLong("header budget")
        return value


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = False
    allow_reuse_address = False

    def __init__(self, address, handler):
        self.slots = threading.BoundedSemaphore(16)
        self.connections = set()
        self.connections_lock = threading.Lock()
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        request.settimeout(2)
        if not self.slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            finally:
                self.shutdown_request(request)
            return
        with self.connections_lock:
            self.connections.add(request)
        try:
            super().process_request(request, client_address)
        except BaseException:
            with self.connections_lock:
                self.connections.discard(request)
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self.connections_lock:
                self.connections.discard(request)
            self.slots.release()

    def close_connections(self):
        with self.connections_lock:
            requests = list(self.connections)
        for request in requests:
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            request.close()

    def handle_error(self, request, client_address):
        pass  # No request data, client addresses, capability tokens or tracebacks in logs.


class MonitorApp:
    def __init__(self, provider, port=8765, interval=1, capacity=120):
        integer(port, 0, 65535, "Port")
        self.interval = interval_seconds(interval)
        self.store = Store(provider.mode, capacity, interval)
        self.collector = Collector(provider)
        self.token = secrets.token_urlsafe(32)
        self.stop_event = threading.Event()
        self.sampler = None
        self.worker = None
        self.server = BoundedServer(("127.0.0.1", port), self._handler())
        self.port = self.server.server_address[1]
        self.origin = f"http://127.0.0.1:{self.port}"
        self.url = self.origin + "/#token=" + self.token

    def _handler(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def parse_request(self):
                original = self.rfile
                self.rfile = _HeaderReader(original)
                try:
                    return super().parse_request()
                finally:
                    self.rfile = original

            def send_error(self, code, message=None, explain=None):
                self.reply(code, b'{"error":"request refused"}\n', "application/json; charset=utf-8")

            def reply(self, status, body, content_type, attachment=None):
                self.close_connection = True
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", CSP)
                if attachment:
                    self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def denied(self, status=403):
                self.reply(status, b'{"error":"request refused"}\n', "application/json; charset=utf-8")

            def do_GET(self):
                hosts = self.headers.get_all("Host", [])
                origins = self.headers.get_all("Origin", [])
                if hosts != [f"127.0.0.1:{app.port}"] or (origins and origins != [app.origin]):
                    return self.denied()
                if len(self.path) > 2048 or self.headers.get("Transfer-Encoding") is not None or self.headers.get_all("Content-Length", []) not in ([], ["0"]):
                    return self.denied(400)
                if "#" in self.path or "%" in self.path or "\\" in self.path:
                    return self.denied(400)
                try:
                    parts = urlsplit(self.path)
                except ValueError:
                    return self.denied(400)
                if parts.scheme or parts.netloc or parts.fragment or not parts.path.startswith("/"):
                    return self.denied(400)
                if parts.path in ASSETS and not parts.query:
                    name, content_type = ASSETS[parts.path]
                    return self.reply(200, (STATIC / name).read_bytes(), content_type)
                if not parts.path.startswith("/api/"):
                    return self.denied(404)
                tokens = self.headers.get_all("X-Outlands-Token", [])
                if len(tokens) != 1 or len(tokens[0]) > 128 or not tokens[0].isascii() or not secrets.compare_digest(tokens[0], app.token):
                    return self.denied()
                try:
                    limit = None
                    if parts.query:
                        if parts.path != "/api/history":
                            return self.denied(400)
                        values = parse_qs(parts.query, keep_blank_values=True, strict_parsing=True)
                        if set(values) != {"limit"} or len(values["limit"]) != 1 or not values["limit"][0].isascii() or not values["limit"][0].isdecimal():
                            return self.denied(400)
                        limit = int(values["limit"][0])
                    if parts.path == "/api/snapshot":
                        return self.reply(200, export_json({"schema": 1, "mode": app.store.mode, "sample": app.store.latest()}), "application/json; charset=utf-8")
                    if parts.path == "/api/history":
                        return self.reply(200, export_json(app.store.snapshot(limit)), "application/json; charset=utf-8")
                    if parts.path == "/api/export.json":
                        return self.reply(200, export_json(app.store.snapshot()), "application/json; charset=utf-8", "outlands-resource-history.json")
                    if parts.path == "/api/export.csv":
                        return self.reply(200, export_csv(app.store.snapshot()), "text/csv; charset=utf-8", "outlands-resource-history.csv")
                    return self.denied(404)
                except (MonitorError, ValueError):
                    return self.denied(400)

            do_HEAD = do_GET

            def method_not_allowed(self):
                return self.denied(405)

            do_POST = do_PUT = do_DELETE = do_OPTIONS = do_PATCH = method_not_allowed

        return Handler

    def _sample(self):
        while not self.stop_event.is_set():
            try:
                self.store.add(self.collector.collect())
            except Exception:
                self.store.mark_sampling_error()
            self.stop_event.wait(self.interval)

    def start(self):
        if self.worker is not None:
            raise MonitorError("Server is already started.")
        self.sampler = threading.Thread(target=self._sample, name="outlands-resource-sampler", daemon=True)
        self.worker = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .1}, name="outlands-resource-http", daemon=True)
        self.sampler.start()
        self.worker.start()
        return self

    def close(self):
        self.stop_event.set()
        if self.worker is not None:
            self.server.shutdown()
        self.server.close_connections()
        self.server.server_close()
        if self.worker is not None:
            self.worker.join(timeout=3)
        if self.sampler is not None:
            self.sampler.join(timeout=3)

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()
