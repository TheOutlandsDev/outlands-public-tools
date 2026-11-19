"""Safe SQLite integrity checks and consistent backups."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .common import OpsKitError, path_display, utc_now


_SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")


def _source_path(path: Path) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
        is_file = resolved.is_file()
    except (OSError, RuntimeError, ValueError) as exc:
        raise OpsKitError("SQLite source path is unavailable.") from exc
    if not is_file:
        raise OpsKitError("SQLite source must be a regular file.")
    return resolved


def _read_only_connection(path: Path) -> sqlite3.Connection:
    uri = f"{path.as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        connection.execute("PRAGMA query_only = ON")
    except sqlite3.Error:
        connection.close()
        raise
    return connection


def check_database(path: Path, *, full: bool = False) -> dict[str, Any]:
    resolved = _source_path(path)
    pragma = "integrity_check" if full else "quick_check"
    try:
        with closing(_read_only_connection(resolved)) as connection:
            integrity_rows = [
                row[0] for row in connection.execute(f"PRAGMA {pragma}").fetchall()
            ]
            foreign_key_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
            page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
            page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            journal_mode = str(
                connection.execute("PRAGMA journal_mode").fetchone()[0]
            )
        file_bytes = resolved.stat().st_size
    except (sqlite3.Error, OSError) as exc:
        raise OpsKitError("SQLite check failed.") from exc

    integrity_ok = integrity_rows == ["ok"]
    foreign_keys_ok = not foreign_key_rows
    return {
        "path": path_display(resolved),
        "checked_at": utc_now(),
        "check": pragma,
        "ok": integrity_ok and foreign_keys_ok,
        "integrity_messages": integrity_rows,
        "foreign_key_violations": [
            {
                "table": row[0],
                "rowid": row[1],
                "parent": row[2],
                "foreign_key_index": row[3],
            }
            for row in foreign_key_rows
        ],
        "page_count": page_count,
        "page_size": page_size,
        "estimated_bytes": page_count * page_size,
        "file_bytes": file_bytes,
        "user_version": user_version,
        "journal_mode": journal_mode,
        "read_only": True,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sidecars(path: Path) -> tuple[Path, ...]:
    return tuple(path.with_name(path.name + suffix) for suffix in _SIDECAR_SUFFIXES)


def _resolved_parent_path(path: Path) -> Path:
    expanded = path.expanduser()
    name = expanded.name
    if not name or name == ".." or "\x00" in name:
        raise OpsKitError("A file path is required.")
    if os.name == "nt":
        reserved = getattr(os.path, "isreserved", None)
        is_reserved = reserved(name) if reserved is not None else Path(name).is_reserved()
        if is_reserved or name.endswith((" ", ".")) or any(
            character in '<>:"/\\|?*' or ord(character) < 32 for character in name
        ):
            raise OpsKitError("Windows file name is malformed or reserved.")
    return expanded.parent.resolve(strict=True) / name


def _check_destination(
    destination: Path, protected_paths: set[Path], *, force: bool
) -> bool:
    if destination in protected_paths:
        raise OpsKitError("Destination aliases the source database or one of its sidecars.")
    try:
        destination_info = destination.lstat()
    except FileNotFoundError:
        destination_info = None

    if destination_info is not None:
        reparse_point = getattr(destination_info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
        )
        if reparse_point or not stat.S_ISREG(destination_info.st_mode):
            raise OpsKitError("Destination must be an ordinary file.")
        if not force:
            raise OpsKitError("Destination already exists.")
        for path in protected_paths:
            try:
                same_file = os.path.samestat(destination_info, path.stat())
            except FileNotFoundError:
                continue
            if same_file:
                raise OpsKitError("Destination aliases the source database or one of its sidecars.")

    if any(os.path.lexists(sidecar) for sidecar in _sidecars(destination)):
        raise OpsKitError("Destination has SQLite sidecars and must be closed before replacement.")
    return destination_info is not None


def backup_database(
    source: Path,
    destination: Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Create and validate a SQLite backup, then publish it atomically."""

    source_path = _source_path(source)
    try:
        source_alias = _resolved_parent_path(source)
        destination_path = _resolved_parent_path(destination)
        protected_paths = {
            source_path, source_alias, *_sidecars(source_path), *_sidecars(source_alias)
        }
        if not destination_path.parent.is_dir():
            raise OpsKitError("Destination directory must exist.")
        _check_destination(destination_path, protected_paths, force=force)

        with TemporaryDirectory(prefix=".opskit-sqlite-", dir=destination_path.parent) as staging:
            partial = Path(staging) / "backup.sqlite"
            with (
                closing(_read_only_connection(source_path)) as source_connection,
                closing(sqlite3.connect(partial, timeout=5.0)) as destination_connection,
            ):
                source_connection.backup(destination_connection)
                destination_connection.commit()
                # Keep the published database self-contained even when the source uses WAL.
                mode = destination_connection.execute("PRAGMA journal_mode = DELETE").fetchone()
                if mode != ("delete",):
                    raise OpsKitError("Could not prepare a standalone SQLite backup.")
            validation = check_database(partial, full=False)
            if not validation["ok"]:
                raise OpsKitError("The generated SQLite backup failed its validation check.")
            size = partial.stat().st_size
            digest = _sha256(partial)
            destination_existed = _check_destination(destination_path, protected_paths, force=force)
            if force:
                os.replace(partial, destination_path)
            else:
                # Creating the hard link fails atomically if a competing destination appears.
                try:
                    os.link(partial, destination_path)
                except FileExistsError as exc:
                    raise OpsKitError("Destination appeared while the backup was running.") from exc
    except (sqlite3.Error, OSError, RuntimeError, ValueError) as exc:
        raise OpsKitError("SQLite backup failed.") from exc

    return {
        "source": path_display(source_path),
        "destination": str(destination_path),
        "created_at": utc_now(),
        "bytes": size,
        "sha256": digest,
        "validated": True,
        "replaced_existing": destination_existed and force,
        "force_requested": force,
    }
