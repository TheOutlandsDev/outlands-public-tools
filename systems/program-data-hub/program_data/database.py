"""SQLite connection, migration, health, search, and backup services."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from program_data.config import get_backup_directory, get_database_path

MIGRATIONS_DIRECTORY = Path(__file__).with_name("migrations")
MIGRATION_FILE_PATTERN = re.compile(r"^(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql$")

SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    applied_at TEXT NOT NULL
) STRICT;
"""

COUNTED_TABLES = (
    "sources",
    "ingestion_runs",
    "data_assets",
    "documents",
    "document_chunks",
    "datasets",
    "dataset_rows",
    "sql_queries",
    "sql_executions",
    "sql_result_rows",
    "metric_definitions",
    "metric_observations",
    "data_quality_issues",
    "rejected_records",
)


class MigrationError(RuntimeError):
    """Raised when an applied migration is missing, changed, or cannot apply."""


def utc_now() -> str:
    """Return a sortable UTC timestamp."""

    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def connect_database(
    database_path: str | Path | None = None,
    *,
    readonly: bool = False,
) -> sqlite3.Connection:
    """Open a configured SQLite connection with consistent safety pragmas."""

    path = get_database_path(database_path)
    if readonly:
        if not path.is_file():
            raise FileNotFoundError(f"SQLite database does not exist: {path}")
        connection = sqlite3.connect(
            f"{path.as_uri()}?mode=ro",
            uri=True,
            timeout=5.0,
        )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=5.0)

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")

    if readonly:
        connection.execute("PRAGMA query_only = ON")
    else:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")

    return connection


def _migration_files() -> list[tuple[int, Path, str]]:
    migrations: list[tuple[int, Path, str]] = []
    seen_versions: set[int] = set()
    for path in sorted(MIGRATIONS_DIRECTORY.glob("*.sql")):
        match = MIGRATION_FILE_PATTERN.fullmatch(path.name)
        if match is None:
            raise MigrationError(
                f"Migration filename must match NNN_lowercase_name.sql: {path.name}"
            )
        version = int(match.group("version"))
        if version in seen_versions:
            raise MigrationError(f"Duplicate migration version: {version}")
        seen_versions.add(version)
        sql = path.read_text(encoding="utf-8")
        migrations.append((version, path, sql))
    return migrations


def initialize_database(
    database_path: str | Path | None = None,
) -> list[str]:
    """Create the database and apply all pending checksum-controlled migrations."""

    applied_now: list[str] = []
    with closing(connect_database(database_path)) as connection:
        connection.execute(SCHEMA_MIGRATIONS_DDL)
        connection.commit()

        applied = {
            int(row["version"]): (str(row["filename"]), str(row["sha256"]))
            for row in connection.execute(
                "SELECT version, filename, sha256 FROM schema_migrations"
            )
        }

        migrations = _migration_files()
        available_versions = {version for version, _, _ in migrations}
        missing_files = sorted(set(applied) - available_versions)
        if missing_files:
            raise MigrationError(
                "Applied migration files are missing: "
                + ", ".join(str(version) for version in missing_files)
            )

        for version, path, sql in migrations:
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            if version in applied:
                applied_filename, applied_checksum = applied[version]
                if applied_filename != path.name or applied_checksum != checksum:
                    raise MigrationError(
                        f"Applied migration {version:03d} has changed; "
                        "create a new migration instead"
                    )
                continue

            try:
                connection.executescript("BEGIN IMMEDIATE;\n" + sql + "\n")
                connection.execute(
                    """
                    INSERT INTO schema_migrations(version, filename, sha256, applied_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (version, path.name, checksum, utc_now()),
                )
                connection.commit()
            except Exception as exc:
                if connection.in_transaction:
                    connection.rollback()
                raise MigrationError(
                    f"Failed to apply migration {path.name}: {exc}"
                ) from exc
            applied_now.append(path.name)

    return applied_now


def database_status(database_path: str | Path | None = None) -> dict[str, Any]:
    """Return integrity, schema, journal, and key record counts."""

    path = get_database_path(database_path)
    if not path.is_file():
        return {
            "database_path": str(path),
            "exists": False,
            "initialized": False,
        }

    with closing(connect_database(path, readonly=True)) as connection:
        quick_check_rows = [
            str(row[0]) for row in connection.execute("PRAGMA quick_check")
        ]
        foreign_key_violations = [
            tuple(row) for row in connection.execute("PRAGMA foreign_key_check")
        ]
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        schema_rows = connection.execute(
            """
            SELECT type, name
            FROM sqlite_schema
            WHERE name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        ).fetchall()
        table_names = {
            str(row["name"]) for row in schema_rows if row["type"] == "table"
        }
        if "schema_migrations" in table_names:
            migration_rows = connection.execute(
                """
                SELECT version, filename, sha256, applied_at
                FROM schema_migrations
                ORDER BY version
                """
            ).fetchall()
        else:
            migration_rows = []
        counts = {
            table: int(
                connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            )
            for table in COUNTED_TABLES
            if table in table_names
        }

    return {
        "database_path": str(path),
        "exists": True,
        "initialized": bool(migration_rows),
        "sqlite_version": sqlite3.sqlite_version,
        "journal_mode": journal_mode,
        "user_version": user_version,
        "quick_check": quick_check_rows,
        "foreign_key_violations": len(foreign_key_violations),
        "migrations": [
            {
                "version": int(row["version"]),
                "filename": str(row["filename"]),
                "sha256": str(row["sha256"]),
                "applied_at": str(row["applied_at"]),
            }
            for row in migration_rows
        ],
        "schema_objects": {
            "tables": sum(row["type"] == "table" for row in schema_rows),
            "views": sum(row["type"] == "view" for row in schema_rows),
            "indexes": sum(row["type"] == "index" for row in schema_rows),
            "triggers": sum(row["type"] == "trigger" for row in schema_rows),
        },
        "counts": counts,
    }


def search_documents(
    query: str,
    database_path: str | Path | None = None,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search extracted document chunks with FTS5."""

    if not query.strip():
        raise ValueError("Search query cannot be blank")
    if limit < 1 or limit > 100:
        raise ValueError("Search limit must be between 1 and 100")

    with closing(connect_database(database_path, readonly=True)) as connection:
        rows = connection.execute(
            """
            SELECT
                d.document_id,
                d.title,
                a.source_uri,
                dc.chunk_index,
                snippet(document_chunks_fts, 0, '[', ']', '...', 18) AS snippet,
                bm25(document_chunks_fts) AS rank
            FROM document_chunks_fts
            JOIN document_chunks AS dc
              ON dc.chunk_id = document_chunks_fts.rowid
            JOIN documents AS d
              ON d.document_id = dc.document_id
            JOIN data_assets AS a
              ON a.asset_id = d.asset_id
            WHERE document_chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def backup_database(
    database_path: str | Path | None = None,
    destination: str | Path | None = None,
) -> Path:
    """Create and integrity-check a consistent backup via SQLite's backup API."""

    source_path = get_database_path(database_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite database does not exist: {source_path}")

    if destination is None:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        destination_path = get_backup_directory() / (
            f"{source_path.stem}_{timestamp}.sqlite3"
        )
    else:
        destination_path = Path(destination).expanduser()
        if not destination_path.is_absolute():
            destination_path = Path.cwd() / destination_path
        destination_path = destination_path.resolve()

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        raise FileExistsError(f"Backup destination already exists: {destination_path}")

    with closing(connect_database(source_path, readonly=True)) as source:
        with closing(sqlite3.connect(destination_path)) as target:
            source.backup(target)
            target.commit()

    with closing(sqlite3.connect(destination_path)) as check_connection:
        result = str(check_connection.execute("PRAGMA quick_check").fetchone()[0])
    if result != "ok":
        destination_path.unlink(missing_ok=True)
        raise RuntimeError(f"Backup integrity check failed: {result}")

    return destination_path
