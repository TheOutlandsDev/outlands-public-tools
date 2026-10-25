"""Private-store persistence for neutral, operator-declared assessment records."""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import threading
import time

VERSION = "0.1.0"
TOOL_ROOT = Path(__file__).resolve().parent
REPOSITORY = TOOL_ROOT.parent.parent if TOOL_ROOT.parent.name == "tools" else TOOL_ROOT
MAX_JSON_BYTES = 65536
MAX_HISTORY = 128
MAX_STORE_BYTES = 16 * 1024 * 1024
PAGE_SIZE = 4096
APP_ID = 0x4F415731
SCHEMA_VERSION = 1
STORE_LOCK = threading.RLock()
_ACTIVE_CONNECTIONS = 0
ZERO = "0" * 64
HEX = re.compile(r"[0-9a-f]{64}")
OPERATIONS = ("INIT", "DEMO", "IMPORT", "SAVE")
SCHEMA = {
    "metadata": "CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK (id = 1), revision INTEGER NOT NULL, head TEXT NOT NULL)",
    "history": "CREATE TABLE history (sequence INTEGER PRIMARY KEY, operation TEXT NOT NULL, ledger TEXT NOT NULL, previous TEXT NOT NULL, digest TEXT NOT NULL)",
}

_spec = importlib.util.spec_from_file_location(
    "_oaw_record_contract", TOOL_ROOT / "record_contract.py"
)
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)


class WorkbenchError(ValueError):
    """A fixed public error code; no native values or selected paths."""


def _fail(code):
    raise WorkbenchError(code) from None


def safe_api(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            with STORE_LOCK:
                return function(*args, **kwargs)
        except WorkbenchError:
            raise
        except contract.ContractError:
            _fail("RECORDS_INVALID")
        except sqlite3.Error as error:
            code = getattr(error, "sqlite_errorcode", 0) & 255
            if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                _fail("STORE_BUSY")
            _fail("STORE_OPERATION_FAILED_REOPEN_REQUIRED")
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
            _fail("OPERATION_FAILED")

    return wrapped


def empty_records():
    return dict(schema_version=1, submissions=[], findings=[], retests=[])


def demo_records():
    return dict(
        schema_version=1,
        submissions=[
            dict(id="sample_original", series_id="sample_series", revision=1),
            dict(id="sample_replacement", series_id="sample_series", revision=2),
        ],
        findings=[
            dict(
                id="sample_finding",
                submission_id="sample_original",
                state="closure_claimed",
                selected_retest_id="sample_retest",
            )
        ],
        retests=[
            dict(
                id="sample_retest",
                finding_id="sample_finding",
                submission_id="sample_replacement",
                outcome="not_observed",
            )
        ],
    )


def _normalize(records):
    is_empty = (
        isinstance(records, dict)
        and set(records) == {"schema_version", "submissions", "findings", "retests"}
        and type(records["schema_version"]) is int
        and records["schema_version"] == 1
        and all(
            isinstance(records[name], list) and not records[name]
            for name in ("submissions", "findings", "retests")
        )
    )
    result = empty_records() if is_empty else contract.parse_records(records)
    text = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        _fail("RECORDS_SIZE_LIMIT")
    return result, text


@safe_api
def validate_records(records):
    records, _ = _normalize(records)
    if not records["submissions"]:
        return dict(
            status="REVIEW_REQUIRED",
            empty=True,
            issues=["EMPTY_WORKSPACE"],
            report=None,
        )
    report = contract.check_records(records)
    return dict(status=report["status"], empty=False, issues=[], report=report)


def _path(value, *, absolute=True):
    if absolute and not Path(os.fspath(value)).is_absolute():
        _fail("ABSOLUTE_PRIVATE_PATH_REQUIRED")
    return contract._selected_path(value)


def _directory_id(info):
    if not stat.S_ISDIR(info.st_mode) or not info.st_ino or contract._linked(info):
        _fail("PATH_IDENTITY_UNAVAILABLE")
    return info.st_dev, info.st_ino


def _canonical_existing(path):
    if os.name != "nt":
        return path
    import ctypes
    from ctypes import wintypes

    api = ctypes.WinDLL("kernel32", use_last_error=True).GetLongPathNameW
    api.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD)
    api.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(4097)
    count = api(str(path), buffer, len(buffer))
    if not 0 < count < len(buffer):
        _fail("CANONICAL_PATH_UNAVAILABLE")
    canonical = contract._selected_path(buffer.value)
    before, after = path.lstat(), canonical.lstat()
    if (before.st_dev, before.st_ino, before.st_mode) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
    ):
        _fail("PATH_IDENTITY_CHANGED")
    return canonical


def _external(path):
    if path.is_relative_to(REPOSITORY):
        _fail("PRIVATE_PATH_MUST_BE_EXTERNAL")
    repository_id = _directory_id(REPOSITORY.lstat())
    for parent in reversed([path.parent, *path.parent.parents]):
        if _directory_id(parent.lstat()) == repository_id:
            _fail("PRIVATE_PATH_MUST_BE_EXTERNAL")


def _family(path):
    return [
        path,
        *(Path(str(path) + suffix) for suffix in ("-journal", "-wal", "-shm")),
    ]


def _new_path(value, protected_stores=()):
    path = _path(value)
    _external(path)
    path = _canonical_existing(path.parent) / path.name
    _external(path)
    if path.name.casefold().endswith(("-journal", "-wal", "-shm")):
        _fail("RESERVED_STORE_ARTIFACT")
    parent_id = _directory_id(path.parent.lstat())
    for store in protected_stores:
        if _directory_id(
            store.parent.lstat()
        ) == parent_id and path.name.casefold() in {
            item.name.casefold() for item in _family(store)
        }:
            _fail("RESERVED_STORE_ARTIFACT")
    for artifact in _family(path):
        try:
            artifact.lstat()
        except FileNotFoundError:
            continue
        _fail("DESTINATION_EXISTS_OR_RESERVED")
    return path


def _no_sidecars(path):
    for artifact in _family(path)[1:]:
        try:
            artifact.lstat()
        except FileNotFoundError:
            continue
        _fail("STORE_ARTIFACT_PRESENT")


def _store_path(value):
    if _ACTIVE_CONNECTIONS:
        _fail("REENTRANT_STORE_OPERATION")
    path = _path(value)
    _external(path)
    _, info = contract._snapshot(path)
    if info.st_size > MAX_STORE_BYTES or info.st_size < PAGE_SIZE:
        _fail("STORE_SIZE_INVALID")
    path = _canonical_existing(path)
    _external(path)
    _no_sidecars(path)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        contract._regular_input(opened)
        if contract._identity(opened) != contract._identity(info):
            _fail("STORE_CHANGED_DURING_PREFLIGHT")
        header = stream.read(100)
        after = os.fstat(stream.fileno())
    if contract._identity(after) != contract._identity(info) or contract._identity(
        path.lstat()
    ) != contract._identity(info):
        _fail("STORE_CHANGED_DURING_PREFLIGHT")
    if (
        len(header) != 100
        or header[:16] != b"SQLite format 3\x00"
        or header[16:18] != b"\x10\x00"
    ):
        _fail("STORE_FORMAT_INVALID")
    if header[18] != 1 or header[19] != 1:
        _fail("STORE_JOURNAL_MODE_UNSUPPORTED")
    _no_sidecars(path)
    return path, info


def _same_store(path, before):
    _, after = contract._snapshot(path)
    if (before.st_dev, before.st_ino, before.st_mode) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
    ):
        _fail("STORE_IDENTITY_CHANGED")
    if after.st_size > MAX_STORE_BYTES:
        _fail("STORE_SIZE_INVALID")


def _digest(sequence, operation, previous, ledger):
    raw = f"OAW1\n{sequence}\n{operation}\n{previous}\n{ledger}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _connect(path, *, write):
    connection = sqlite3.connect(
        path.as_uri() + ("?mode=rw" if write else "?mode=ro"),
        uri=True,
        timeout=2.0,
        isolation_level=None,
    )
    try:
        if not hasattr(connection, "enable_load_extension"):
            _fail("SQLITE_RUNTIME_UNSUPPORTED")
        connection.enable_load_extension(False)
        if hasattr(connection, "setconfig") and hasattr(
            sqlite3, "SQLITE_DBCONFIG_DEFENSIVE"
        ):
            try:
                connection.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
            except sqlite3.NotSupportedError:
                pass
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA mmap_size=0")
        connection.execute("PRAGMA cell_size_check=ON")
        connection.execute("PRAGMA temp_store=MEMORY")
        if hasattr(connection, "setlimit"):
            for category, limit in (
                (sqlite3.SQLITE_LIMIT_LENGTH, MAX_JSON_BYTES + 4096),
                (sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8192),
                (sqlite3.SQLITE_LIMIT_COLUMN, 16),
                (sqlite3.SQLITE_LIMIT_ATTACHED, 0),
                (sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 16),
            ):
                connection.setlimit(category, limit)
        connection.execute("PRAGMA busy_timeout=2000")
        if not write:
            connection.execute("PRAGMA query_only=ON")
        else:
            connection.execute("PRAGMA synchronous=FULL")
        deadline = time.monotonic() + 2.0
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        return connection
    except BaseException:
        connection.close()
        raise


def _verify(connection):
    if connection.execute("PRAGMA application_id").fetchone() != (
        APP_ID,
    ) or connection.execute("PRAGMA user_version").fetchone() != (SCHEMA_VERSION,):
        _fail("STORE_FORMAT_INVALID")
    if connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
        _fail("STORE_JOURNAL_MODE_UNSUPPORTED")
    if (
        connection.execute("PRAGMA page_size").fetchone() != (PAGE_SIZE,)
        or connection.execute("PRAGMA page_count").fetchone()[0]
        > MAX_STORE_BYTES // PAGE_SIZE
    ):
        _fail("STORE_SIZE_INVALID")
    schema = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_schema LIMIT 3"
    ).fetchall()
    expected = [("table", name, name, sql) for name, sql in SCHEMA.items()]
    if sorted(schema) != sorted(expected):
        _fail("STORE_SCHEMA_INVALID")
    if connection.execute("PRAGMA quick_check(1)").fetchall() != [("ok",)]:
        _fail("STORE_INTEGRITY_INVALID")
    metadata = connection.execute(
        "SELECT id, revision, head FROM metadata LIMIT 2"
    ).fetchall()
    if len(metadata) != 1:
        _fail("STORE_METADATA_INVALID")
    identifier, revision, head = metadata[0]
    if (
        type(identifier) is not int
        or identifier != 1
        or type(revision) is not int
        or not 0 <= revision < MAX_HISTORY
        or not isinstance(head, str)
        or not HEX.fullmatch(head)
    ):
        _fail("STORE_METADATA_INVALID")
    lengths = connection.execute(
        f"SELECT sequence, length(CAST(ledger AS BLOB)) FROM history ORDER BY sequence LIMIT {MAX_HISTORY + 1}"
    ).fetchall()
    if (
        len(lengths) != revision + 1
        or not lengths
        or any(
            type(seq) is not int
            or seq != index
            or type(size) is not int
            or not 0 < size <= MAX_JSON_BYTES
            for index, (seq, size) in enumerate(lengths)
        )
    ):
        _fail("STORE_HISTORY_INVALID")
    rows = connection.execute(
        f"SELECT sequence, operation, ledger, previous, digest FROM history ORDER BY sequence LIMIT {MAX_HISTORY + 1}"
    ).fetchall()
    previous = ZERO
    for index, (seq, operation, ledger, link, digest) in enumerate(rows):
        if (
            type(seq) is not int
            or seq != index
            or operation not in OPERATIONS
            or (index > 0 and operation != "SAVE")
            or (index == 0 and operation == "SAVE")
        ):
            _fail("STORE_HISTORY_INVALID")
        if (
            not isinstance(ledger, str)
            or not isinstance(link, str)
            or not isinstance(digest, str)
            or link != previous
            or not HEX.fullmatch(digest)
        ):
            _fail("STORE_HISTORY_INVALID")
        records = json.loads(
            ledger,
            object_pairs_hook=contract._unique_object,
            parse_constant=lambda _: _fail("STORE_HISTORY_INVALID"),
        )
        _, canonical = _normalize(records)
        if index == 0 and operation == "INIT" and records != empty_records():
            _fail("STORE_HISTORY_INVALID")
        if index == 0 and operation == "DEMO" and records != demo_records():
            _fail("STORE_HISTORY_INVALID")
        if ledger != canonical or digest != _digest(seq, operation, link, ledger):
            _fail("STORE_HISTORY_INVALID")
        previous = digest
    if previous != head:
        _fail("STORE_HEAD_INVALID")
    return rows


@contextmanager
def _opened(value, *, write=False):
    global _ACTIVE_CONNECTIONS
    path, before = _store_path(value)
    connection = _connect(path, write=write)
    _ACTIVE_CONNECTIONS += 1
    try:
        connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        rows = _verify(connection)
        if write:
            connection.execute(f"PRAGMA max_page_count={MAX_STORE_BYTES // PAGE_SIZE}")
        yield path, connection, rows
        connection.commit()
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
        _ACTIVE_CONNECTIONS -= 1
    _same_store(path, before)
    _no_sidecars(path)


def _snapshot_result(row):
    records = json.loads(row[2])
    return dict(
        revision=row[0],
        records=records,
        validation=validate_records(records),
        head=row[4],
    )


def _create(path, rows):
    global _ACTIVE_CONNECTIONS
    if _ACTIVE_CONNECTIONS:
        _fail("REENTRANT_STORE_OPERATION")
    descriptor = os.open(
        path, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600
    )
    os.close(descriptor)
    connection = _connect(path, write=True)
    _ACTIVE_CONNECTIONS += 1
    try:
        connection.execute(f"PRAGMA page_size={PAGE_SIZE}")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute(f"PRAGMA max_page_count={MAX_STORE_BYTES // PAGE_SIZE}")
        connection.execute(f"PRAGMA application_id={APP_ID}")
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        connection.execute("BEGIN IMMEDIATE")
        for sql in SCHEMA.values():
            connection.execute(sql)
        connection.executemany("INSERT INTO history VALUES (?, ?, ?, ?, ?)", rows)
        connection.execute(
            "INSERT INTO metadata VALUES (1, ?, ?)", (rows[-1][0], rows[-1][4])
        )
        _verify(connection)
        connection.commit()
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
        _ACTIVE_CONNECTIONS -= 1
    return _snapshot_result(rows[-1])


def _initial(value, records, operation):
    _, ledger = _normalize(records)
    path = _new_path(value)
    row = (0, operation, ledger, ZERO, _digest(0, operation, ZERO, ledger))
    return _create(path, [row])


@safe_api
def create_store(path):
    return _initial(path, empty_records(), "INIT")


@safe_api
def create_demo(path):
    return _initial(path, demo_records(), "DEMO")


@safe_api
def import_to_new_store(input_json, new_store):
    records = _read_json(input_json)
    return _initial(new_store, records, "IMPORT")


@safe_api
def load_store(path):
    with _opened(path) as (_, _, rows):
        result = _snapshot_result(rows[-1])
    return result


@safe_api
def save_records(path, records, expected_revision):
    if type(expected_revision) is not int or not 0 <= expected_revision < MAX_HISTORY:
        _fail("EXPECTED_REVISION_INVALID")
    _, ledger = _normalize(records)
    with _opened(path, write=True) as (_, connection, rows):
        previous = rows[-1]
        if previous[0] != expected_revision:
            _fail("STALE_REVISION")
        if len(rows) >= MAX_HISTORY:
            _fail("HISTORY_LIMIT")
        sequence = expected_revision + 1
        row = (
            sequence,
            "SAVE",
            ledger,
            previous[4],
            _digest(sequence, "SAVE", previous[4], ledger),
        )
        connection.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?)", row)
        connection.execute(
            "UPDATE metadata SET revision = ?, head = ? WHERE id = 1",
            (sequence, row[4]),
        )
        _verify(connection)
        result = _snapshot_result(row)
    return result


@safe_api
def list_history(path):
    with _opened(path) as (_, _, rows):
        result = []
        for row in rows:
            validation = validate_records(json.loads(row[2]))
            result.append(
                dict(
                    revision=row[0],
                    operation=row[1],
                    status=validation["status"],
                    empty=validation["empty"],
                )
            )
    return result


def _revision(value, rows):
    if type(value) is not int or not 0 <= value < len(rows):
        _fail("REVISION_NOT_FOUND")
    return rows[value]


@safe_api
def load_revision(path, revision):
    with _opened(path) as (_, _, rows):
        result = _snapshot_result(_revision(revision, rows))
    return result


@safe_api
def export_records(path, new_json):
    with _opened(path) as (source, _, rows):
        target = _new_path(new_json, [source])
        row = rows[-1]
        raw = row[2].encode("utf-8")
        if len(raw) > MAX_JSON_BYTES:
            _fail("EXPORT_SIZE_LIMIT")
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        result = dict(
            status="EXPORTED_PRIVATE_RECORDS",
            revision=row[0],
            validation=validate_records(json.loads(row[2])),
        )
    return result


@safe_api
def clone_store(path, new_store, revision=None):
    with _opened(path) as (source, _, rows):
        target = _new_path(new_store, [source])
        selected = rows[-1][0] if revision is None else _revision(revision, rows)[0]
        preserved = rows[: selected + 1]
    return _create(target, preserved)


@safe_api
def read_records_file(path):
    records = _read_json(path)
    return _normalize(records)[0]


@safe_api
def read_record_file(path):
    return _read_json(path)


def _read_json(path):
    if _ACTIVE_CONNECTIONS:
        _fail("REENTRANT_STORE_OPERATION")
    return contract.read_input_json(path)


def _collection(kind):
    if kind not in ("submissions", "findings", "retests"):
        _fail("RECORD_KIND_INVALID")
    return kind


@safe_api
def put_record(path, kind, record, expected_revision, identifier=None):
    kind = _collection(kind)
    snapshot = load_store(path)
    if type(expected_revision) is not int or not 0 <= expected_revision < MAX_HISTORY:
        _fail("EXPECTED_REVISION_INVALID")
    if snapshot["revision"] != expected_revision:
        _fail("STALE_REVISION")
    records = snapshot["records"]
    if not isinstance(record, dict):
        _fail("RECORDS_INVALID")
    if identifier is None:
        records[kind].append(dict(record))
    else:
        contract._token(identifier)
        if record.get("id") != identifier:
            _fail("RECORD_ID_IMMUTABLE")
        for index, row in enumerate(records[kind]):
            if row["id"] == identifier:
                records[kind][index] = dict(record)
                break
        else:
            _fail("RECORD_NOT_FOUND")
    return save_records(path, records, expected_revision)


@safe_api
def remove_record(path, kind, identifier, expected_revision):
    kind = _collection(kind)
    contract._token(identifier)
    snapshot = load_store(path)
    if type(expected_revision) is not int or not 0 <= expected_revision < MAX_HISTORY:
        _fail("EXPECTED_REVISION_INVALID")
    if snapshot["revision"] != expected_revision:
        _fail("STALE_REVISION")
    records = snapshot["records"]
    for index, row in enumerate(records[kind]):
        if row["id"] == identifier:
            del records[kind][index]
            break
    else:
        _fail("RECORD_NOT_FOUND")
    return save_records(path, records, expected_revision)
