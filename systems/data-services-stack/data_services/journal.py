"""Immutable verified snapshots with empty commit markers and exclusive sessions."""
from copy import deepcopy
import re

from . import files
from .contracts import MAX_JSON, StackError, canonical, decode, digest
from .state import FORMAT, empty, validate

MAX_GENERATIONS = 2048
MAX_TOTAL = 64 * 1024 * 1024
SLOT = re.compile(r"r[0-9]{6}")
ZERO = "0" * 64


class Journal:
    def __init__(self, root, *, confirm_stopped=False, initializing=False):
        if type(confirm_stopped) is not bool:
            raise StackError("STOPPED_ASSERTION_REQUIRED")
        self.root = files.selected(root, output=True)
        self.closed = True
        self.poisoned = False
        self._root_guard = files.directory(self.root)
        self._root_guard.__enter__()
        self._lock_guard = None
        self._lock_identity = None
        try:
            lock = self.root / ".writer-lock"
            if lock.exists() or lock.is_symlink():
                if not confirm_stopped:
                    raise StackError("WORKSPACE_BUSY_OR_STALE")
                files.remove_empty_lock(self.root)
            files.mkdir(lock)
            self._lock_identity = files.identity(lock)
            self._lock_guard = files.directory(lock)
            self._lock_guard.__enter__()
            self.closed = False
            self._load(initializing)
        except BaseException:
            self.close()
            raise

    @classmethod
    def initialize(cls, root):
        root = files.mkdir(root)
        with cls(root, initializing=True) as journal:
            journal.commit(empty())
            return journal.status()

    def _load(self, initializing):
        names = files.entries(self.root, MAX_GENERATIONS + 1)
        if any(name != ".writer-lock" and SLOT.fullmatch(name) is None for name in names):
            raise StackError("WORKSPACE_ENTRY_INVALID")
        slots = [name for name in names if name != ".writer-lock"]
        self.head = ZERO
        self.sequence = -1
        self.next_sequence = 0
        self.total_bytes = 0
        self.orphans = []
        self._state = None
        for name in slots:
            folder = self.root / name
            names_inside = files.entries(folder, 3)
            if not set(names_inside) <= {"state.json", "COMMITTED"}:
                raise StackError("JOURNAL_ENTRY_INVALID")
            sequence = int(name[1:])
            self.next_sequence = max(self.next_sequence, sequence + 1)
            if "COMMITTED" not in names_inside:
                # Preserve interrupted output, including partial bytes. Do not
                # interpret it or treat it as a committed state.
                if "state.json" in names_inside:
                    self.total_bytes += len(files.read(folder / "state.json", MAX_JSON))
                if self.total_bytes > MAX_TOTAL:
                    raise StackError("JOURNAL_BYTE_LIMIT")
                self.orphans.append(sequence)
                continue
            if files.read(folder / "COMMITTED", 0) != b"":
                raise StackError("COMMIT_MARKER_INVALID")
            raw = files.read(folder / "state.json", MAX_JSON)
            self.total_bytes += len(raw)
            if self.total_bytes > MAX_TOTAL:
                raise StackError("JOURNAL_BYTE_LIMIT")
            envelope = decode(raw)
            if (type(envelope) is not dict or set(envelope) != {"format", "sequence", "previous", "state"}
                    or envelope["format"] != FORMAT or type(envelope["sequence"]) is not int
                    or envelope["sequence"] != sequence or envelope["previous"] != self.head
                    or raw != canonical(envelope)):
                raise StackError("JOURNAL_CHAIN_INVALID")
            self._state = validate(envelope["state"])
            self.head, self.sequence = digest(raw), sequence
        if (self._state is None and not initializing) or (initializing and slots):
            raise StackError("WORKSPACE_NOT_INITIALIZED")

    def commit(self, data):
        if self.closed or self.poisoned:
            raise StackError("SESSION_UNAVAILABLE")
        checked = validate(data)
        if self.next_sequence >= MAX_GENERATIONS:
            raise StackError("JOURNAL_GENERATION_LIMIT")
        envelope = dict(format=FORMAT, sequence=self.next_sequence, previous=self.head, state=checked)
        raw = canonical(envelope)
        if len(raw) > MAX_JSON or self.total_bytes + len(raw) > MAX_TOTAL:
            raise StackError("JOURNAL_BYTE_LIMIT")
        folder = self.root / ("r" + str(self.next_sequence).zfill(6))
        try:
            files.mkdir(folder)
            files.write_new(folder / "state.json", raw)
            files.write_new(folder / "COMMITTED", b"")
        except BaseException:
            self.poisoned = True
            raise
        self._state = deepcopy(checked)
        self.sequence = self.next_sequence
        self.next_sequence += 1
        self.head = digest(raw)
        self.total_bytes += len(raw)

    def status(self):
        if self.closed or self.poisoned:
            raise StackError("SESSION_UNAVAILABLE")
        return dict(sequence=self.sequence, head_sha256=self.head, orphan_generations=len(self.orphans),
                    recovery_required=any(r["state"] == "RUNNING" for r in self._state["runs"].values())
                    or any(q["state"] == "IN_FLIGHT" for q in self._state["queue"].values()))

    def close(self):
        try:
            if self._lock_guard is not None:
                self._lock_guard.__exit__(None, None, None)
                self._lock_guard = None
            if self._lock_identity is not None:
                files.remove_empty_lock(self.root, self._lock_identity)
                self._lock_identity = None
        finally:
            self.closed = True
            self._root_guard.__exit__(None, None, None)

    def __enter__(self):
        return self

    def __exit__(self, kind, error, trace):
        self.close()
