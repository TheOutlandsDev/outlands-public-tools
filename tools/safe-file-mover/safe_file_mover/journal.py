"""Durable SQLite journal for safe move operations."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def default_state_directory() -> Path:
    override = os.environ.get("SAFE_FILE_MOVER_STATE_DIR")
    if override:
        if os.name == "nt":
            from .windows_fs import checked_path

            return checked_path(os.path.expanduser(override), allow_missing=True)
        return Path(override).expanduser().absolute()
    if os.name == "nt":
        from .windows_fs import checked_path

        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        return checked_path(base / "SafeFileMover", allow_missing=True)
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state).expanduser() / "safe-file-mover"
    return Path.home() / ".local" / "state" / "safe-file-mover"


@dataclass(frozen=True, slots=True)
class OperationRecord:
    operation_id: str
    created_at: str
    updated_at: str
    source: str
    destination: str
    staging: str
    backup: str
    reservation: str
    status: str
    manifest_json: str
    total_bytes: int
    item_count: int
    keep_backup: bool
    conflict_policy: str
    last_error: str | None = None

    @property
    def manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_json)


class Journal:
    """Small durable operation store; each method uses its own connection."""

    def __init__(self, state_directory: Path | str | None = None) -> None:
        if os.name == "nt":
            from .windows_fs import checked_path

            value = state_directory if state_directory is not None else default_state_directory()
            self.state_directory = checked_path(
                os.path.expanduser(os.fspath(value)), allow_missing=True
            )
            self._check_state_ancestors()
            self.database_path = self.state_directory / "moves.sqlite3"
            return
        selected = Path(
            state_directory if state_directory is not None else default_state_directory()
        ).expanduser()
        if ".." in selected.parts:
            raise ValueError("Journal state must not contain parent traversal.")
        self.state_directory = selected.absolute()
        self._check_state_ancestors()
        self.database_path = self.state_directory / "moves.sqlite3"

    def _check_state_ancestors(self) -> None:
        if os.name == "nt":
            from .windows_fs import checked_path

            checked_path(self.state_directory, allow_missing=True)
            return
        for item in (self.state_directory, *self.state_directory.parents):
            if item.is_symlink():
                raise ValueError("Journal state must not use symlink components.")

    @staticmethod
    def _check_private_file(path: Path, *, create: bool) -> None:
        if os.name == "nt":
            from .windows_fs import check_regular

            check_regular(path, allow_missing=create, reject_streams=True)
        flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        if create:
            flags |= os.O_CREAT
        descriptor = os.open(path, flags, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("Journal storage must be an unshared regular file.")
            if os.name != "nt" and (
                info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077
            ):
                raise ValueError("Journal storage must be owner-private.")
            current = path.lstat()
            if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                raise ValueError("Journal storage changed during inspection.")
            if os.name == "nt" and path.name == "moves.sqlite3" and info.st_size:
                header = os.read(descriptor, 20)
                if (
                    len(header) < 20
                    or not header.startswith(b"SQLite format 3\0")
                    or header[18:20] != b"\1\1"
                ):
                    raise ValueError("Journal storage requires a valid non-WAL SQLite header.")
        finally:
            os.close(descriptor)
        if os.name == "nt":
            check_regular(path, reject_streams=True)

    def _prepare_storage(self) -> None:
        self._check_state_ancestors()
        self.state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == "nt":
            self._check_state_ancestors()
        info = self.state_directory.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("Journal state must be a directory.")
        if os.name != "nt" and (
            info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise ValueError("Journal state directory must be owner-private.")
        if os.name == "nt":
            self._check_windows_sidecars()
        self._check_private_file(self.database_path, create=True)
        rollback = self.database_path.with_name(self.database_path.name + "-journal")
        if os.path.lexists(rollback):
            self._check_private_file(rollback, create=False)

    def _check_windows_sidecars(self) -> None:
        for suffix in ("-wal", "-shm"):
            sidecar = self.database_path.with_name(self.database_path.name + suffix)
            if os.path.lexists(sidecar):
                raise ValueError("WAL/SHM journal sidecars are unsupported; retain them for review.")

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    staging TEXT NOT NULL,
                    backup TEXT NOT NULL,
                    reservation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    item_count INTEGER NOT NULL,
                    keep_backup INTEGER NOT NULL,
                    conflict_policy TEXT NOT NULL,
                    last_error TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    FOREIGN KEY(operation_id) REFERENCES operations(operation_id)
                );

                CREATE INDEX IF NOT EXISTS operations_status_idx
                    ON operations(status, updated_at);
                CREATE INDEX IF NOT EXISTS events_operation_idx
                    ON events(operation_id, event_id);
                """
            )

    def create(self, record: OperationRecord, message: str) -> None:
        self.initialize()
        values = asdict(record)
        values["keep_backup"] = int(record.keep_backup)
        columns = ", ".join(values)
        placeholders = ", ".join(f":{key}" for key in values)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                f"INSERT INTO operations ({columns}) VALUES ({placeholders})", values
            )
            self._insert_event(connection, record.operation_id, record.status, message)
            connection.commit()

    def update(
        self,
        operation_id: str,
        *,
        status: str | None = None,
        message: str,
        last_error: str | None = None,
        clear_error: bool = False,
    ) -> OperationRecord:
        self.initialize()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM operations WHERE operation_id = ?", (operation_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown operation: {operation_id}")
            next_status = status or row["status"]
            next_error = None if clear_error else (
                last_error if last_error is not None else row["last_error"]
            )
            connection.execute(
                """
                UPDATE operations
                SET status = ?, updated_at = ?, last_error = ?
                WHERE operation_id = ?
                """,
                (next_status, utc_now(), next_error, operation_id),
            )
            self._insert_event(connection, operation_id, next_status, message)
            connection.commit()
        return self.get(operation_id)

    def update_precommit_manifest(
        self,
        operation_id: str,
        *,
        manifest_json: str,
        total_bytes: int,
        item_count: int,
        message: str,
    ) -> OperationRecord:
        """Atomically refresh a baseline while no destination has been committed."""
        self.initialize()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown operation: {operation_id}")
            if row["status"] not in {"planned", "copying"}:
                raise ValueError(
                    "A manifest can be refreshed only before destination commit."
                )
            connection.execute(
                """
                UPDATE operations
                SET manifest_json = ?, total_bytes = ?, item_count = ?,
                    updated_at = ?, last_error = NULL
                WHERE operation_id = ?
                """,
                (
                    manifest_json,
                    total_bytes,
                    item_count,
                    utc_now(),
                    operation_id,
                ),
            )
            self._insert_event(
                connection,
                operation_id,
                row["status"],
                message,
            )
            connection.commit()
        return self.get(operation_id)

    def get(self, operation_id: str) -> OperationRecord:
        self.initialize()
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM operations WHERE operation_id = ?", (operation_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown operation: {operation_id}")
        return self._record_from_row(row)

    def list(self, *, include_complete: bool = True) -> list[OperationRecord]:
        self.initialize()
        sql = "SELECT * FROM operations"
        parameters: tuple[str, ...] = ()
        if not include_complete:
            sql += " WHERE status NOT IN (?, ?, ?)"
            parameters = ("complete", "restored", "abandoned")
        sql += " ORDER BY created_at DESC"
        with closing(self._connect()) as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [self._record_from_row(row) for row in rows]

    def events(self, operation_id: str) -> list[dict[str, Any]]:
        self.initialize()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT occurred_at, status, message
                FROM events
                WHERE operation_id = ?
                ORDER BY event_id
                """,
                (operation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        if os.name == "nt":
            return self._connect_windows()
        self._prepare_storage()
        connection = sqlite3.connect(
            self.database_path.as_uri() + "?mode=rw", timeout=30.0, uri=True
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _connect_windows(self) -> sqlite3.Connection:
        self._prepare_storage()
        # Recheck immediately before SQLite's pathname open. Trusted parents
        # are still required; these sampled checks are not an atomic VFS.
        self._check_state_ancestors()
        self._check_windows_sidecars()
        self._check_private_file(self.database_path, create=False)
        rollback = self.database_path.with_name(self.database_path.name + "-journal")
        if os.path.lexists(rollback):
            self._check_private_file(rollback, create=False)
        connection = sqlite3.connect(
            self.database_path.as_uri() + "?mode=rw", timeout=30.0, uri=True
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA busy_timeout = 30000")
        except BaseException:
            connection.close()
            raise
        return connection

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        operation_id: str,
        status: str,
        message: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO events(operation_id, occurred_at, status, message)
            VALUES (?, ?, ?, ?)
            """,
            (operation_id, utc_now(), status, message),
        )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> OperationRecord:
        return OperationRecord(
            operation_id=row["operation_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            source=row["source"],
            destination=row["destination"],
            staging=row["staging"],
            backup=row["backup"],
            reservation=row["reservation"],
            status=row["status"],
            manifest_json=row["manifest_json"],
            total_bytes=row["total_bytes"],
            item_count=row["item_count"],
            keep_backup=bool(row["keep_backup"]),
            conflict_policy=row["conflict_policy"],
            last_error=row["last_error"],
        )
