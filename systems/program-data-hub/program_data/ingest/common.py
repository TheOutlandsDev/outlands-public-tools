"""Shared ingestion lifecycle, lineage, hashing, and JSON helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import mimetypes
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Mapping

from program_data.database import connect_database, initialize_database, utc_now


@dataclass(frozen=True)
class IngestResult:
    """Stable, script-friendly result returned by every ingestion adapter."""

    run_id: str
    source_id: int
    entity_type: str
    entity_id: int | str | None
    asset_id: int | None
    records_read: int
    records_written: int
    deduplicated: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_json_value(value: Any) -> Any:
    """Convert common database-driver values into strict JSON-compatible data."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, bytes):
        return {
            "$type": "bytes",
            "encoding": "base64",
            "value": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, Mapping):
        return {
            str(key): normalize_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [normalize_json_value(item) for item in value]
    return str(value)


def canonical_json(value: Any) -> str:
    """Serialize data deterministically for storage, hashes, and idempotency."""

    return json.dumps(
        normalize_json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_timestamp(value: str | datetime | None) -> str:
    """Normalize an input timestamp to UTC ISO-8601, defaulting to now."""

    if value is None:
        return utc_now()
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            raise ValueError("Timestamp cannot be blank")
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        parsed = datetime.fromisoformat(candidate)
    else:
        parsed = value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def file_metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    media_type, _ = mimetypes.guess_type(path.name)
    return {
        "source_uri": str(path.resolve()),
        "logical_name": path.name,
        "media_type": media_type or "application/octet-stream",
        "byte_size": stat.st_size,
        "content_sha256": sha256_file(path),
        "source_modified_at": datetime.fromtimestamp(
            stat.st_mtime, tz=UTC
        ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }


@dataclass
class IngestionContext:
    connection: sqlite3.Connection
    source_id: int
    run_id: str
    input_reference: str | None
    input_sha256: str | None
    records_read: int = 0
    records_written: int = 0
    records_rejected: int = 0
    status: str = "succeeded"
    metadata: dict[str, Any] = field(default_factory=dict)

    def existing_asset(
        self,
        *,
        asset_type: str,
        content_sha256: str | None,
    ) -> sqlite3.Row | None:
        if content_sha256 is None:
            return None
        return self.connection.execute(
            """
            SELECT *
            FROM data_assets
            WHERE source_id = ?
              AND asset_type = ?
              AND content_sha256 = ?
            """,
            (self.source_id, asset_type, content_sha256),
        ).fetchone()

    def create_asset(
        self,
        *,
        asset_type: str,
        logical_name: str,
        source_uri: str | None = None,
        media_type: str | None = None,
        byte_size: int | None = None,
        content_sha256: str | None = None,
        source_modified_at: str | None = None,
        observed_at: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO data_assets(
                source_id,
                run_id,
                asset_type,
                logical_name,
                source_uri,
                media_type,
                byte_size,
                content_sha256,
                source_modified_at,
                observed_at,
                ingested_at,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.source_id,
                self.run_id,
                asset_type,
                logical_name,
                source_uri,
                media_type,
                byte_size,
                content_sha256,
                source_modified_at,
                observed_at,
                utc_now(),
                canonical_json(metadata or {}),
            ),
        )
        return int(cursor.lastrowid)


def _ensure_source(
    connection: sqlite3.Connection,
    *,
    source_key: str,
    display_name: str,
    source_type: str,
    authority_note: str | None,
    location_hint: str | None,
    config: Mapping[str, Any] | None,
) -> int:
    normalized_key = source_key.strip()
    if not normalized_key:
        raise ValueError("Source key cannot be blank")

    existing = connection.execute(
        "SELECT source_id, source_type FROM sources WHERE source_key = ?",
        (normalized_key,),
    ).fetchone()
    now = utc_now()
    if existing is not None:
        if existing["source_type"] != source_type:
            raise ValueError(
                f"Source {normalized_key!r} is already registered as "
                f"{existing['source_type']!r}, not {source_type!r}"
            )
        connection.execute(
            """
            UPDATE sources
            SET display_name = ?,
                authority_note = COALESCE(?, authority_note),
                location_hint = COALESCE(?, location_hint),
                updated_at = ?
            WHERE source_id = ?
            """,
            (
                display_name.strip() or normalized_key,
                authority_note,
                location_hint,
                now,
                int(existing["source_id"]),
            ),
        )
        return int(existing["source_id"])

    cursor = connection.execute(
        """
        INSERT INTO sources(
            source_key,
            display_name,
            source_type,
            authority_note,
            location_hint,
            config_json,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            normalized_key,
            display_name.strip() or normalized_key,
            source_type,
            authority_note,
            location_hint,
            canonical_json(config or {}),
            now,
            now,
        ),
    )
    return int(cursor.lastrowid)


@contextmanager
def ingestion_session(
    database_path: str | Path | None,
    *,
    source_key: str,
    source_name: str,
    source_type: str,
    authority_note: str | None = None,
    location_hint: str | None = None,
    source_config: Mapping[str, Any] | None = None,
    input_reference: str | None = None,
    input_sha256: str | None = None,
    trigger_type: str = "manual",
) -> Iterator[IngestionContext]:
    """Record an ingestion lifecycle while keeping failed loads atomic."""

    initialize_database(database_path)
    connection = connect_database(database_path)
    run_id = str(uuid.uuid4())

    try:
        source_id = _ensure_source(
            connection,
            source_key=source_key,
            display_name=source_name,
            source_type=source_type,
            authority_note=authority_note,
            location_hint=location_hint,
            config=source_config,
        )
        connection.execute(
            """
            INSERT INTO ingestion_runs(
                run_id,
                source_id,
                status,
                trigger_type,
                input_reference,
                input_sha256,
                started_at
            )
            VALUES (?, ?, 'running', ?, ?, ?, ?)
            """,
            (
                run_id,
                source_id,
                trigger_type,
                input_reference,
                input_sha256,
                utc_now(),
            ),
        )
        connection.commit()

        context = IngestionContext(
            connection=connection,
            source_id=source_id,
            run_id=run_id,
            input_reference=input_reference,
            input_sha256=input_sha256,
        )
        try:
            yield context
            connection.execute(
                """
                UPDATE ingestion_runs
                SET status = ?,
                    completed_at = ?,
                    records_read = ?,
                    records_written = ?,
                    records_rejected = ?,
                    metadata_json = ?
                WHERE run_id = ?
                """,
                (
                    context.status,
                    utc_now(),
                    context.records_read,
                    context.records_written,
                    context.records_rejected,
                    canonical_json(context.metadata),
                    run_id,
                ),
            )
            connection.commit()
        except Exception as exc:
            connection.rollback()
            connection.execute(
                """
                UPDATE ingestion_runs
                SET status = 'failed',
                    completed_at = ?,
                    records_read = ?,
                    records_written = 0,
                    records_rejected = ?,
                    error_summary = ?,
                    metadata_json = ?
                WHERE run_id = ?
                """,
                (
                    utc_now(),
                    context.records_read,
                    context.records_rejected,
                    str(exc)[:2000],
                    canonical_json(context.metadata),
                    run_id,
                ),
            )
            connection.commit()
            raise
    finally:
        connection.close()
