"""Bounded, single-caller in-memory outbox; no service or persistence adapter."""
from dataclasses import dataclass
import re
from typing import Protocol

MAX_MESSAGES = 64
MAX_TICK = 1000000000000
MAX_ATTEMPTS = 5
TOKEN = re.compile(r"[a-z][a-z0-9_-]{0,63}")


class OutboxError(ValueError):
    """Fixed diagnostic codes only; never include message or adapter text."""


class _InvalidAcceptance(Exception):
    """Internal outcome marker; never classify an adapter by its exception text."""


def _token(value):
    if type(value) is not str or len(value) > 64 or TOKEN.fullmatch(value) is None:
        raise OutboxError("TOKEN_INVALID")


def _text(value, maximum, *, header=False):
    if type(value) is not str:
        raise OutboxError("MESSAGE_TEXT_INVALID")
    if len(value) > maximum:
        raise OutboxError("MESSAGE_TEXT_LIMIT")
    if not value.strip():
        raise OutboxError("MESSAGE_TEXT_INVALID")
    if any((ord(char) < 32 and (header or char not in "\n\t"))
           or 127 <= ord(char) <= 159 or char in "\u2028\u2029" for char in value):
        raise OutboxError("MESSAGE_TEXT_INVALID")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        raise OutboxError("MESSAGE_TEXT_INVALID") from None
    if size > maximum:
        raise OutboxError("MESSAGE_TEXT_LIMIT")


@dataclass(frozen=True)
class Message:
    key: str
    route: str
    subject: str
    body: str

    def __post_init__(self):
        _token(self.key)
        _token(self.route)
        _text(self.subject, 160, header=True)
        _text(self.body, 8192)


@dataclass(frozen=True)
class Acceptance:
    receipt: str

    def __post_init__(self):
        _token(self.receipt)


class RetryableNotAccepted(Exception):
    """Adapter asserts the operation was definitely not accepted; retry is safe."""


class PermanentNotAccepted(Exception):
    """Adapter asserts definite rejection that must not be retried."""


class DeliveryUncertain(Exception):
    """Acceptance cannot be determined; never automatically replay this attempt."""


class Transport(Protocol):
    def send(self, message: Message) -> Acceptance:
        """Honor message.key idempotency; return acceptance, never delivery proof."""
        ...


@dataclass(frozen=True)
class Snapshot:
    key: str
    state: str
    attempts: int
    next_attempt: int | None
    code: str


@dataclass
class _Entry:
    message: Message
    state: str = "PENDING"
    attempts: int = 0
    next_attempt: int | None = 0
    code: str = "QUEUED"
    receipt: str | None = None


def _copy_message(message):
    if type(message) is not Message:
        raise OutboxError("MESSAGE_REQUIRED")
    return Message(message.key, message.route, message.subject, message.body)


class Outbox:
    """Retain idempotency keys for this instance's lifetime; no concurrency guarantee."""
    def __init__(self, *, max_attempts=3):
        if type(max_attempts) is not int or not 1 <= max_attempts <= MAX_ATTEMPTS:
            raise OutboxError("OUTBOX_PARAMETER_INVALID")
        self._max_attempts = max_attempts
        self._entries = {}
        self._last_tick = 0
        self._busy = False

    @property
    def max_attempts(self):
        return self._max_attempts

    def _idle(self):
        if self._busy:
            raise OutboxError("OUTBOX_BUSY")

    def enqueue(self, message):
        self._idle()
        selected = _copy_message(message)
        existing = self._entries.get(selected.key)
        if existing:
            if existing.message != selected:
                raise OutboxError("IDEMPOTENCY_CONFLICT")
            return False
        if len(self._entries) >= MAX_MESSAGES:
            raise OutboxError("OUTBOX_CAPACITY")
        self._entries[selected.key] = _Entry(selected)
        return True

    def snapshot(self, key):
        _token(key)
        if key not in self._entries:
            raise OutboxError("MESSAGE_NOT_FOUND")
        entry = self._entries[key]
        return Snapshot(key, entry.state, entry.attempts, entry.next_attempt, entry.code)

    def report_delivery(self, key, *, receipt):
        """Record a matching caller assertion; no provider verification occurs."""
        self._idle()
        _token(receipt)
        self.snapshot(key)
        entry = self._entries[key]
        if entry.state not in ("ACCEPTED", "DELIVERY_REPORTED") or entry.receipt != receipt:
            raise OutboxError("DELIVERY_REPORT_REFUSED")
        if entry.state == "DELIVERY_REPORTED":
            return False
        entry.state, entry.code = "DELIVERY_REPORTED", "CALLER_REPORTED_DELIVERY"
        return True

    def dispatch(self, transport: Transport, *, now, limit=10):
        self._idle()
        if type(now) is not int or not self._last_tick <= now <= MAX_TICK:
            raise OutboxError("OUTBOX_CLOCK_INVALID")
        if type(limit) is not int or not 1 <= limit <= MAX_MESSAGES:
            raise OutboxError("OUTBOX_PARAMETER_INVALID")
        try:
            send = transport.send
        except Exception:
            raise OutboxError("OUTBOX_TRANSPORT_INVALID") from None
        if not callable(send):
            raise OutboxError("OUTBOX_TRANSPORT_INVALID")
        self._last_tick = now
        changed = []
        self._busy = True
        try:
            for key, entry in self._entries.items():
                if len(changed) >= limit:
                    break
                if entry.state != "PENDING" or entry.next_attempt > now:
                    continue
                try:
                    entry.attempts += 1
                    entry.state, entry.next_attempt, entry.code = "IN_FLIGHT", None, "ATTEMPTING"
                    result = send(_copy_message(entry.message))
                    if type(result) is not Acceptance:
                        raise _InvalidAcceptance()
                    try:
                        _token(result.receipt)
                    except OutboxError:
                        raise _InvalidAcceptance() from None
                except RetryableNotAccepted:
                    due = now + 2 ** (entry.attempts - 1)
                    if entry.attempts >= self._max_attempts or due > MAX_TICK:
                        entry.state, entry.next_attempt, entry.code = "FAILED", None, "RETRY_EXHAUSTED"
                    else:
                        entry.state, entry.next_attempt, entry.code = "PENDING", due, "RETRY_SCHEDULED"
                except PermanentNotAccepted:
                    entry.state, entry.next_attempt, entry.code = "FAILED", None, "DEFINITELY_REJECTED"
                except BaseException as error:
                    code = "DELIVERY_UNCERTAIN"
                    if isinstance(error, _InvalidAcceptance):
                        code = "ADAPTER_RESULT_INVALID"
                    if not isinstance(error, Exception):
                        code = "DELIVERY_INTERRUPTED"
                    entry.state, entry.next_attempt, entry.code = "REVIEW_REQUIRED", None, code
                    if not isinstance(error, Exception):
                        raise
                else:
                    entry.receipt = result.receipt
                    entry.state, entry.next_attempt, entry.code = "ACCEPTED", None, "ADAPTER_ACCEPTED"
                changed.append(self.snapshot(key))
        finally:
            self._busy = False
        return tuple(changed)


class FakeTransport:
    """Scripted memory-only outcomes; acceptance is never real email delivery."""
    OUTCOMES = ("accept", "retry", "reject", "uncertain", "accepted_then_unknown", "interrupt")

    def __init__(self, *, outcomes=()):
        if (type(outcomes) is not tuple or len(outcomes) > MAX_MESSAGES
                or any(type(item) is not str or item not in self.OUTCOMES for item in outcomes)):
            raise OutboxError("FAKE_PARAMETER_INVALID")
        self._outcomes = outcomes
        self._calls = 0
        self._accepted = {}

    @property
    def calls(self):
        return self._calls

    @property
    def accepted_keys(self):
        return tuple(self._accepted)

    def send(self, message):
        selected = _copy_message(message)
        action = self._outcomes[self._calls] if self._calls < len(self._outcomes) else "accept"
        self._calls += 1
        if selected.key in self._accepted:
            if self._accepted[selected.key] != selected:
                raise PermanentNotAccepted()
            return Acceptance("fake_receipt")
        if len(self._accepted) >= MAX_MESSAGES or action == "reject":
            raise PermanentNotAccepted()
        if action == "retry":
            raise RetryableNotAccepted()
        if action == "uncertain":
            raise DeliveryUncertain()
        if action == "interrupt":
            raise KeyboardInterrupt()
        self._accepted[selected.key] = selected
        if action == "accepted_then_unknown":
            raise DeliveryUncertain()
        return Acceptance("fake_receipt")
