"""Versioned ingestion of exported SQL query result sets."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Mapping

from program_data.database import utc_now
from program_data.ingest.common import (
    IngestResult,
    canonical_json,
    file_metadata,
    ingestion_session,
    normalize_timestamp,
    sha256_text,
)
from program_data.ingest.tabular import (
    data_format_for_path,
    declared_columns,
    iter_tabular_records,
    schema_from_profile,
    update_type_profile,
)


def _ensure_query(
    context_connection: Any,
    *,
    source_id: int,
    query_key: str,
    query_name: str,
    description: str | None,
) -> int:
    now = utc_now()
    row = context_connection.execute(
        """
        SELECT query_id
        FROM sql_queries
        WHERE source_id = ? AND query_key = ?
        """,
        (source_id, query_key),
    ).fetchone()
    if row is not None:
        query_id = int(row["query_id"])
        context_connection.execute(
            """
            UPDATE sql_queries
            SET display_name = ?, description = COALESCE(?, description), updated_at = ?
            WHERE query_id = ?
            """,
            (query_name, description, now, query_id),
        )
        return query_id

    cursor = context_connection.execute(
        """
        INSERT INTO sql_queries(
            source_id,
            query_key,
            display_name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_id, query_key, query_name, description, now, now),
    )
    return int(cursor.lastrowid)


def _ensure_query_version(
    context_connection: Any,
    *,
    query_id: int,
    query_text: str | None,
) -> int | None:
    if query_text is None:
        return None
    normalized = query_text.strip()
    if not normalized:
        return None
    checksum = sha256_text(normalized)
    row = context_connection.execute(
        """
        SELECT query_version_id
        FROM sql_query_versions
        WHERE query_id = ? AND query_sha256 = ?
        """,
        (query_id, checksum),
    ).fetchone()
    if row is not None:
        return int(row["query_version_id"])
    cursor = context_connection.execute(
        """
        INSERT INTO sql_query_versions(
            query_id,
            query_sha256,
            query_text,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (query_id, checksum, normalized, utc_now()),
    )
    return int(cursor.lastrowid)


def ingest_sql_export(
    path: str | Path,
    database_path: str | Path | None = None,
    *,
    query_key: str,
    query_name: str | None = None,
    query_text: str | None = None,
    source_key: str | None = None,
    source_name: str | None = None,
    server_name: str | None = None,
    database_name: str | None = None,
    record_key_column: str | None = None,
    executed_at: str | None = None,
    parameters: Mapping[str, Any] | list[Any] | None = None,
    description: str | None = None,
    trigger_type: str = "manual",
) -> IngestResult:
    """Import a query-result export with query and execution lineage."""

    normalized_query_key = query_key.strip()
    if not normalized_query_key:
        raise ValueError("Query key cannot be blank")

    source_path = Path(path).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"SQL export does not exist: {source_path}")
    data_format = data_format_for_path(source_path)
    metadata = file_metadata(source_path)
    effective_executed_at = normalize_timestamp(
        executed_at or metadata["source_modified_at"]
    )
    executed_at_basis = "provided" if executed_at else "source_modified_at"
    resolved_source_key = source_key or f"sql_{normalized_query_key}"
    resolved_source_name = source_name or (
        f"SQL query: {query_name or normalized_query_key}"
    )

    with ingestion_session(
        database_path,
        source_key=resolved_source_key,
        source_name=resolved_source_name,
        source_type="sql_query",
        authority_note=(
            "The named upstream database and approved query/view remain authoritative."
        ),
        location_hint=" / ".join(
            part for part in (server_name, database_name) if part
        )
        or None,
        input_reference=str(source_path),
        input_sha256=metadata["content_sha256"],
        trigger_type=trigger_type,
    ) as context:
        query_id = _ensure_query(
            context.connection,
            source_id=context.source_id,
            query_key=normalized_query_key,
            query_name=query_name or normalized_query_key,
            description=description,
        )
        query_version_id = _ensure_query_version(
            context.connection,
            query_id=query_id,
            query_text=query_text,
        )
        snapshot_key = sha256_text(
            canonical_json(
                {
                    "query_id": query_id,
                    "executed_at": effective_executed_at,
                    "content_sha256": metadata["content_sha256"],
                }
            )
        )
        existing_execution = context.connection.execute(
            """
            SELECT execution_id, asset_id, row_count
            FROM sql_executions
            WHERE query_id = ? AND snapshot_key = ?
            """,
            (query_id, snapshot_key),
        ).fetchone()
        if existing_execution is not None:
            context.metadata["deduplicated_execution_id"] = str(
                existing_execution["execution_id"]
            )
            return IngestResult(
                run_id=context.run_id,
                source_id=context.source_id,
                entity_type="sql_execution",
                entity_id=str(existing_execution["execution_id"]),
                asset_id=int(existing_execution["asset_id"]),
                records_read=0,
                records_written=0,
                deduplicated=True,
                metadata={
                    "existing_row_count": int(existing_execution["row_count"]),
                    "snapshot_key": snapshot_key,
                },
            )

        asset_id = context.create_asset(
            asset_type="sql_result",
            logical_name=metadata["logical_name"],
            source_uri=metadata["source_uri"],
            media_type=metadata["media_type"],
            byte_size=metadata["byte_size"],
            content_sha256=metadata["content_sha256"],
            source_modified_at=metadata["source_modified_at"],
            observed_at=effective_executed_at,
            metadata={
                "format": data_format,
                "query_key": normalized_query_key,
                "executed_at_basis": executed_at_basis,
            },
        )
        execution_id = str(uuid.uuid4())
        context.connection.execute(
            """
            INSERT INTO sql_executions(
                execution_id,
                query_id,
                query_version_id,
                run_id,
                asset_id,
                server_name,
                database_name,
                execution_status,
                executed_at,
                imported_at,
                parameters_json,
                snapshot_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'imported', ?, ?, ?, ?)
            """,
            (
                execution_id,
                query_id,
                query_version_id,
                context.run_id,
                asset_id,
                server_name,
                database_name,
                effective_executed_at,
                utc_now(),
                canonical_json(parameters or {}),
                snapshot_key,
            ),
        )

        type_profile: dict[str, set[str]] = {
            column: set() for column in declared_columns(source_path)
        }
        row_count = 0
        for row_count, row in enumerate(iter_tabular_records(source_path), start=1):
            context.records_read = row_count
            update_type_profile(type_profile, row)
            row_json = canonical_json(row)
            record_key = (
                str(row.get(record_key_column))
                if record_key_column and row.get(record_key_column) is not None
                else None
            )
            context.connection.execute(
                """
                INSERT INTO sql_result_rows(
                    execution_id,
                    row_number,
                    record_key,
                    row_json,
                    row_sha256
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    row_count,
                    record_key,
                    row_json,
                    sha256_text(row_json),
                ),
            )

        if record_key_column and record_key_column not in type_profile:
            raise ValueError(
                f"Record-key column {record_key_column!r} was not found"
            )
        schema = schema_from_profile(type_profile)
        context.connection.execute(
            """
            UPDATE sql_executions
            SET row_count = ?, result_schema_json = ?
            WHERE execution_id = ?
            """,
            (row_count, canonical_json(schema), execution_id),
        )
        context.records_read = row_count
        context.records_written = row_count
        context.metadata.update(
            {
                "execution_id": execution_id,
                "query_id": query_id,
                "query_version_id": query_version_id,
                "row_count": row_count,
                "snapshot_key": snapshot_key,
                "executed_at_basis": executed_at_basis,
            }
        )
        return IngestResult(
            run_id=context.run_id,
            source_id=context.source_id,
            entity_type="sql_execution",
            entity_id=execution_id,
            asset_id=asset_id,
            records_read=row_count,
            records_written=row_count,
            deduplicated=False,
            metadata={
                "query_id": query_id,
                "query_version_id": query_version_id,
                "format": data_format,
                "snapshot_key": snapshot_key,
                "executed_at": effective_executed_at,
            },
        )
