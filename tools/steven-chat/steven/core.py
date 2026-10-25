"""Bounded local API client and explicit session handling. Original MIT code."""
from __future__ import annotations

import ipaddress
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import re
import stat
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_BYTES = 1024 * 1024
MAX_MESSAGES = 128
MAX_CHARS = 65536
MAX_PROMPT = 8192


class ChatError(Exception):
    """A safe user-facing error that excludes server bodies and private inputs."""


def _integer(value, minimum, maximum, label):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ChatError(f"{label} is outside its supported bounds.")
    return value


def canonical_endpoint(value: str) -> str:
    """Accept only literal loopback HTTP origins; no names requiring DNS."""
    try:
        if not isinstance(value, str) or len(value) > 128 or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
            raise ValueError
        parts = urlsplit(value)
        if (parts.scheme != "http" or parts.username is not None or parts.password is not None
                or parts.path not in ("", "/") or parts.query or parts.fragment or "?" in value or "#" in value):
            raise ValueError
        host = parts.hostname
        if host == "localhost":
            host = "127.0.0.1"
        if host not in ("127.0.0.1", "::1"):
            raise ValueError
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError
        port = parts.port if parts.port is not None else 11434
        if not 1 <= port <= 65535 or parts.netloc.endswith(":"):
            raise ValueError
        # Explicitly reject noncanonical spellings of IPv4 and alternate numeric forms.
        authority = parts.netloc
        allowed_host = "[::1]" if host == "::1" else ("localhost" if parts.hostname == "localhost" else host)
        if authority != allowed_host and authority != f"{allowed_host}:{port}":
            raise ValueError
        return f"http://{'[::1]' if host == '::1' else host}:{port}"
    except (ValueError, TypeError):
        raise ChatError("Endpoint must be an HTTP loopback origin using 127.0.0.1, localhost or [::1].") from None


def _model_shape(value):
    return (isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", value)
            and ".." not in value and "//" not in value and not value.endswith(("/", ":")))


def _cloud_label(value):
    return re.search(r"(?:[:/-])cloud(?:[:/-]|$)", value, re.IGNORECASE)


def validate_model(value: str) -> str:
    if not _model_shape(value):
        raise ChatError("Provide a supported installed-model name (1-128 simple characters).")
    if _cloud_label(value):
        raise ChatError("Cloud-labelled models are refused; choose a local model and disable backend cloud features.")
    return value


def safe_text(value: str) -> str:
    """Render untrusted text without terminal escapes, bidi controls or C1 controls."""
    result = []
    for char in str(value):
        category = unicodedata.category(char)
        if char == "\n":
            result.append(char)
        elif category.startswith("C") or ord(char) == 127:
            code = ord(char)
            result.append(f"\\u{code:04x}" if code <= 0xffff else f"\\U{code:08x}")
        else:
            result.append(char)
    return "".join(result)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key")
        result[key] = value
    return result


def _json(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    except (ValueError, UnicodeError, RecursionError):
        raise ChatError("Response or session is not supported strict UTF-8 JSON.") from None


def _messages(value, complete=True):
    if not isinstance(value, list) or len(value) > MAX_MESSAGES:
        raise ChatError("Conversation message count is outside its supported bounds.")
    result = []
    expected = "user"
    total = 0
    for index, message in enumerate(value):
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise ChatError("Unsupported conversation message shape.")
        role, content = message["role"], message["content"]
        if role == "system" and index == 0:
            pass
        elif role == expected:
            expected = "assistant" if expected == "user" else "user"
        else:
            raise ChatError("Conversation must alternate complete user/assistant turns after an optional system message.")
        if not isinstance(content, str) or not content.strip() or len(content) > MAX_CHARS:
            raise ChatError("Conversation content is empty or too large.")
        try:
            content.encode("utf-8")
        except UnicodeError:
            raise ChatError("Conversation content must be valid Unicode encodable as UTF-8.") from None
        if role in ("user", "system") and len(content) > MAX_PROMPT:
            raise ChatError("User/system content exceeds 8192 characters.")
        total += len(content)
        result.append({"role": role, "content": content})
    if total > MAX_CHARS:
        raise ChatError("Conversation exceeds 65536 characters.")
    if complete and expected != "user":
        raise ChatError("Session contains an incomplete turn.")
    if not complete and (not result or result[-1]["role"] != "user"):
        raise ChatError("A chat request must end with a user message.")
    return result


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        return None


class OllamaClient:
    """Local-origin requests only. This cannot enforce the server's own routing/privacy."""
    def __init__(self, endpoint="http://127.0.0.1:11434", timeout=60, max_output_tokens=256):
        self.endpoint = canonical_endpoint(endpoint)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 1 <= timeout <= 300:
            raise ChatError("Timeout must be finite and between 1 and 300 seconds.")
        self.timeout = timeout
        self.max_output_tokens = _integer(max_output_tokens, 1, 4096, "Output token limit")
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    def _request(self, route, body=None):
        raw = None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if raw is not None and len(raw) > MAX_BYTES:
            raise ChatError("Request exceeds the supported byte limit.")
        request = Request(self.endpoint + route, data=raw,
                          headers={"Accept": "application/json", "Content-Type": "application/json"},
                          method="GET" if body is None else "POST")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ChatError("Local backend returned an unsuccessful response.")
                declared = response.headers.get("Content-Length")
                if declared is not None and (not declared.isdecimal() or int(declared) > MAX_BYTES):
                    raise ChatError("Backend response exceeds the supported byte limit.")
                payload = response.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise ChatError("Backend response exceeds the supported byte limit.")
                if declared is not None and len(payload) != int(declared):
                    raise ChatError("Backend response was truncated before its declared length.")
                value = _json(payload)
                if not isinstance(value, dict) or "error" in value:
                    raise ChatError("Local backend returned an error or unsupported response shape.")
                return value
        except HTTPError as error:
            error.close()
            raise ChatError("Local backend request failed. Check its availability, installed model and timeout; redirects are refused.") from None
        except (URLError, OSError, TimeoutError, ValueError, HTTPException):
            raise ChatError("Local backend request failed. Check its availability, installed model and timeout; redirects are refused.") from None

    def models(self) -> list[str]:
        value = self._request("/api/tags")
        rows = value.get("models")
        if not isinstance(rows, list) or len(rows) > MAX_MESSAGES:
            raise ChatError("Backend model list has an unsupported shape or count.")
        names = []
        for row in rows:
            if not isinstance(row, dict) or "name" not in row:
                raise ChatError("Backend model list contains an unsupported entry.")
            if _model_shape(row["name"]) and _cloud_label(row["name"]):
                continue
            names.append(validate_model(row["name"]))
        return sorted(set(names))

    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        value = self._request("/api/chat", {"model": validate_model(model), "messages": _messages(messages, complete=False),
                                           "stream": False, "options": {"num_predict": self.max_output_tokens}})
        message = value.get("message")
        if (value.get("done") is not True or not isinstance(message, dict)
                or message.get("role") != "assistant" or not isinstance(message.get("content"), str)
                or not message["content"].strip() or len(message["content"]) > MAX_CHARS
                or message.get("tool_calls")):
            raise ChatError("Backend did not return a completed plain-text assistant response.")
        try:
            message["content"].encode("utf-8")
        except UnicodeError:
            raise ChatError("Backend response must contain valid Unicode encodable as UTF-8.") from None
        return message["content"]


class Conversation:
    def __init__(self, model: str, messages=None, context_chars=16384):
        self.model = validate_model(model)
        self.context_chars = _integer(context_chars, 1024, MAX_CHARS, "Context character limit")
        self._messages = _messages([] if messages is None else messages)

    @property
    def messages(self):
        return [dict(item) for item in self._messages]

    def clear(self):
        self._messages = self._messages[:1] if self._messages and self._messages[0]["role"] == "system" else []

    def _trim(self, messages, reserve=0):
        result = [dict(item) for item in messages]
        start = 1 if result and result[0]["role"] == "system" else 0
        while sum(len(item["content"]) for item in result) > self.context_chars or len(result) + reserve > MAX_MESSAGES:
            # The newest request/response is never silently dropped.
            end = len(result) - (1 if result[-1]["role"] == "user" else 2)
            if end - start < 2:
                raise ChatError("Newest turn and system message exceed the context limit; shorten them or start a new session.")
            del result[start:start + 2]
        return result

    def ask(self, client, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT:
            raise ChatError("Prompt must contain 1-8192 characters.")
        request = self._trim(self.messages + [{"role": "user", "content": prompt}], reserve=1)
        _messages(request, complete=False)
        reply = client.chat(self.model, request)
        if not isinstance(reply, str) or not reply.strip() or len(reply) > MAX_CHARS:
            raise ChatError("Backend response content is empty or too large.")
        updated = self._trim(request + [{"role": "assistant", "content": reply}])
        self._messages = _messages(updated)
        return reply

    def to_dict(self):
        return {"schema": 1, "model": self.model, "messages": self.messages}


def _path(path):
    try:
        value = Path(path).absolute()
        for entry in (value, *value.parents):
            if entry.is_symlink() or getattr(entry, "is_junction", lambda: False)():
                raise ChatError("Linked session paths and linked parents are unsupported.")
        if not value.parent.is_dir():
            raise ChatError("The explicit session parent directory must already exist.")
        return value
    except (OSError, ValueError, TypeError):
        raise ChatError("Session path is unavailable or unsupported.") from None


def load_session(path) -> Conversation:
    value = _path(path)
    try:
        before = value.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
            raise ChatError("Session must be a bounded regular UTF-8 JSON file.")
        descriptor = os.open(value, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise ChatError("Session must be a bounded regular UTF-8 JSON file.")
            raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ChatError("Session exceeds the supported byte limit.")
        data = _json(raw)
        if not isinstance(data, dict) or set(data) != {"schema", "model", "messages"} or type(data["schema"]) is not int or data["schema"] != 1:
            raise ChatError("Unsupported session schema; expected schema 1 with model and messages only.")
        return Conversation(data["model"], data["messages"])
    except OSError:
        raise ChatError("Could not read the explicit session file.") from None


def save_session(path, conversation: Conversation) -> None:
    value = _path(path)
    data = conversation.to_dict()
    # Revalidate instead of trusting a changed/mocked object.
    checked = Conversation(data["model"], data["messages"])
    raw = (json.dumps(checked.to_dict(), ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ChatError("Session exceeds the supported byte limit.")
    try:
        descriptor = os.open(value, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise ChatError("Save target already exists; choose a new filename.") from None
    except OSError:
        # A failed write may leave a partial fresh file; never overwrite or remove an unrelated file.
        raise ChatError("Could not save the fresh session file; inspect the target privately for a partial file.") from None
