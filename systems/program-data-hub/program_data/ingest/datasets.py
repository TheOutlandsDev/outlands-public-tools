"""CSV/JSON dataset ingestion into immutable raw rows."""

from __future__ import annotations

from pathlib import Path

from program_data.ingest.common import (
    IngestResult,
    canonical_json,
    file_metadata,
    ingestion_session,
    sha256_text,
)
from program_data.ingest.tabular import (
    data_format_for_path,
    declared_columns,
    iter_tabular_records,
    schema_from_profile,
    update_type_profile,
)


def ingest_dataset(
    path: str | Path,
    database_path: str | Path | None = None,
    *,
    source_key: str = "local_datasets",
    source_name: str = "Local datasets",
    key_column: str | None = None,
    observed_at_column: str | None = None,
    trigger_type: str = "manual",
) -> IngestResult:
    """Ingest CSV/JSON records while preserving source values as JSON."""

    source_path = Path(path).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Dataset does not exist: {source_path}")

    data_format = data_format_for_path(source_path)
    metadata = file_metadata(source_path)

    with ingestion_session(
        database_path,
        source_key=source_key,
        source_name=source_name,
        source_type="dataset",
        authority_note="The upstream dataset owner remains authoritative.",
        location_hint=str(source_path.parent),
        input_reference=str(source_path),
        input_sha256=metadata["content_sha256"],
        trigger_type=trigger_type,
    ) as context:
        existing_asset = context.existing_asset(
            asset_type="dataset",
            content_sha256=metadata["content_sha256"],
        )
        if existing_asset is not None:
            dataset = context.connection.execute(
                "SELECT dataset_id, row_count FROM datasets WHERE asset_id = ?",
                (int(existing_asset["asset_id"]),),
            ).fetchone()
            context.metadata["deduplicated_asset_id"] = int(
                existing_asset["asset_id"]
            )
            return IngestResult(
                run_id=context.run_id,
                source_id=context.source_id,
                entity_type="dataset",
                entity_id=int(dataset["dataset_id"]) if dataset else None,
                asset_id=int(existing_asset["asset_id"]),
                records_read=0,
                records_written=0,
                deduplicated=True,
                metadata={
                    "existing_row_count": int(dataset["row_count"]) if dataset else 0
                },
            )

        asset_id = context.create_asset(
            asset_type="dataset",
            logical_name=metadata["logical_name"],
            source_uri=metadata["source_uri"],
            media_type=metadata["media_type"],
            byte_size=metadata["byte_size"],
            content_sha256=metadata["content_sha256"],
            source_modified_at=metadata["source_modified_at"],
            metadata={"format": data_format},
        )
        cursor = context.connection.execute(
            """
            INSERT INTO datasets(
                asset_id,
                data_format,
                key_column,
                observed_at_column
            )
            VALUES (?, ?, ?, ?)
            """,
            (asset_id, data_format, key_column, observed_at_column),
        )
        dataset_id = int(cursor.lastrowid)

        type_profile: dict[str, set[str]] = {
            column: set() for column in declared_columns(source_path)
        }
        row_count = 0
        for row_count, row in enumerate(iter_tabular_records(source_path), start=1):
            context.records_read = row_count
            update_type_profile(type_profile, row)
            row_json = canonical_json(row)
            record_key = (
                str(row.get(key_column))
                if key_column and row.get(key_column) is not None
                else None
            )
            observed_at = (
                str(row.get(observed_at_column))
                if observed_at_column and row.get(observed_at_column) is not None
                else None
            )
            context.connection.execute(
                """
                INSERT INTO dataset_rows(
                    dataset_id,
                    row_number,
                    record_key,
                    observed_at,
                    row_json,
                    row_sha256
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    row_count,
                    record_key,
                    observed_at,
                    row_json,
                    sha256_text(row_json),
                ),
            )

        if key_column and key_column not in type_profile:
            raise ValueError(f"Key column {key_column!r} was not found in the dataset")
        if observed_at_column and observed_at_column not in type_profile:
            raise ValueError(
                f"Observed-at column {observed_at_column!r} was not found"
            )

        schema = schema_from_profile(type_profile)
        context.connection.execute(
            """
            UPDATE datasets
            SET row_count = ?,
                column_count = ?,
                schema_json = ?
            WHERE dataset_id = ?
            """,
            (
                row_count,
                len(type_profile),
                canonical_json(schema),
                dataset_id,
            ),
        )
        context.records_read = row_count
        context.records_written = row_count
        context.metadata.update(
            {
                "dataset_id": dataset_id,
                "row_count": row_count,
                "column_count": len(type_profile),
            }
        )
        return IngestResult(
            run_id=context.run_id,
            source_id=context.source_id,
            entity_type="dataset",
            entity_id=dataset_id,
            asset_id=asset_id,
            records_read=row_count,
            records_written=row_count,
            deduplicated=False,
            metadata={"column_count": len(type_profile), "format": data_format},
        )
