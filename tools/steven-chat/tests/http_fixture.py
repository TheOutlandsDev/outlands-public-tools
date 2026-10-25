"""Original MIT loopback-only HTTP fixture; never a model or external service."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time


@contextmanager
def http_fixture(responses):
    """Yield (endpoint, requests); response entries are HTTP fixture dictionaries."""
    requests = []
    pending = list(responses)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_request(self):
            length = int(self.headers.get("Content-Length", "0"))
            data = self.rfile.read(length) if length else b""
            requests.append({"method": self.command, "path": self.path,
                             "headers": dict(self.headers), "body": data})
            response = pending.pop(0) if pending else {"status": 500, "body": b"No fixture response"}
            time.sleep(response.get("delay", 0))
            if "raw_http" in response:
                self.connection.sendall(response["raw_http"])
                self.close_connection = True
                return
            body = response.get("body", b"")
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            try:
                self.send_response(response.get("status", 200))
                self.send_header("Content-Type", response.get("content_type", "application/json"))
                if response.get("length", True):
                    self.send_header("Content-Length", str(response.get("declared_length", len(body))))
                for name, value in response.get("headers", {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass  # Expected when a bounded client rejects or times out.

        do_GET = handle_request
        do_POST = handle_request

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def chat_reply(content="Fictional local response."):
    return {"body": {"model": "fixture:tiny", "done": True,
                     "message": {"role": "assistant", "content": content}}}
