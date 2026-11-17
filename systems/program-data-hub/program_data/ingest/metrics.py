"""Typed, idempotent metric definition and observation ingestion."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

from program_data.database import utc_now
from program_data.ingest.common import (
    IngestResult,
    canonical_json,
    ingestion_session,
    normalize_timestamp,
    sha256_text,
)


def _metric_value(value: Any) -> tuple[str, float | None, str | None, str | None]:
    if isinstance(value, bool):
        return "boolean", float(value), None, None
    if isinstance(value, (int, float)):
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("Numeric metric values must be finite")
        return "numeric", numeric_value, None, None
    if isinstance(value, str):
        return "text", None, value, None
    return "json", None, None, canonical_json(value)


def record_metric(
    metric_key: str,
    value: Any,
    database_path: str | Path | None = None,
    *,
    observed_at: str | None = None,
    unit: str | None = None,
    dimensions: Mapping[str, Any] | None = None,
    display_name: str | None = None,
    description: str | None = None,
    source_key: str = "application_metrics",
    source_name: str = "Application metrics",
    quality_status: str = "valid",
    trigger_type: str = "manual",
) -> IngestResult:
    """Record one metric observation with deterministic retry semantics."""

    normalized_key = metric_key.strip()
    if not normalized_key:
        raise ValueError("Metric key cannot be blank")
    if quality_status not in {"valid", "suspect", "invalid"}:
        raise ValueError("quality_status must be valid, suspect, or invalid")
    if dimensions is not None and not isinstance(dimensions, Mapping):
        raise TypeError("Metric dimensions must be a JSON object")

    value_kind, value_number, value_text, value_json = _metric_value(value)
    normalized_observed_at = normalize_timestamp(observed_at)
    dimensions_json = canonical_json(dimensions or {})

    with ingestion_session(
        database_path,
        source_key=source_key,
        source_name=source_name,
        source_type="metric",
        authority_note="Metric authority is defined by its registered source.",
        input_reference=normalized_key,
        trigger_type=trigger_type,
    ) as context:
        now = utc_now()
        definition = context.connection.execute(
            """
            SELECT metric_id, value_kind, unit
            FROM metric_definitions
            WHERE source_id = ? AND metric_key = ?
            """,
            (context.source_id, normalized_key),
        ).fetchone()
        if definition is None:
            cursor = context.connection.execute(
                """
                INSERT INTO metric_definitions(
                    source_id,
                    metric_key,
                    display_name,
                    description,
                    unit,
                    value_kind,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.source_id,
                    normalized_key,
                    display_name or normalized_key.replace("_", " ").title(),
                    description,
                    unit,
                    value_kind,
                    now,
                    now,
                ),
            )
            metric_id = int(cursor.lastrowid)
        else:
            metric_id = int(definition["metric_id"])
            if str(definition["value_kind"]) != value_kind:
                raise ValueError(
                    f"Metric {normalized_key!r} expects "
                    f"{definition['value_kind']!r}, not {value_kind!r}"
                )
            existing_unit = definition["unit"]
            if existing_unit is not None and unit is not None and existing_unit != unit:
                raise ValueError(
                    f"Metric {normalized_key!r} uses unit {existing_unit!r}, "
                    f"not {unit!r}"
                )
            context.connection.execute(
                """
                UPDATE metric_definitions
                SET display_name = COALESCE(?, display_name),
                    description = COALESCE(?, description),
                    unit = COALESCE(unit, ?),
                    updated_at = ?
                WHERE metric_id = ?
                """,
                (display_name, description, unit, now, metric_id),
            )

        dedupe_key = sha256_text(
            canonical_json(
                {
                    "source_id": context.source_id,
                    "metric_key": normalized_key.casefold(),
                    "observed_at": normalized_observed_at,
                    "dimensions": dimensions or {},
                }
            )
        )
        existing = context.connection.execute(
            """
            SELECT
                observation_id,
                value_number,
                value_text,
                value_json,
                quality_status
            FROM metric_observations
            WHERE dedupe_key = ?
            """,
            (dedupe_key,),
        ).fetchone()
        context.records_read = 1
        if existing is not None:
            existing_value = (
                existing["value_number"],
                existing["value_text"],
                existing["value_json"],
                existing["quality_status"],
            )
            requested_value = (
                value_number,
                value_text,
                value_json,
                quality_status,
            )
            if existing_value != requested_value:
                raise ValueError(
                    "A different metric value or quality status already exists "
                    "for this metric, timestamp, and dimensions"
                )
            context.metadata["deduplicated_observation_id"] = int(
                existing["observation_id"]
            )
            return IngestResult(
                run_id=context.run_id,
                source_id=context.source_id,
                entity_type="metric_observation",
                entity_id=int(existing["observation_id"]),
                asset_id=None,
                records_read=1,
                records_written=0,
                deduplicated=True,
                metadata={"metric_id": metric_id},
            )

        cursor = context.connection.execute(
            """
            INSERT INTO metric_observations(
                metric_id,
                run_id,
                observed_at,
                value_number,
                value_text,
                value_json,
                dimensions_json,
                quality_status,
                dedupe_key,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric_id,
                context.run_id,
                normalized_observed_at,
                value_number,
                value_text,
                value_json,
                dimensions_json,
                quality_status,
                dedupe_key,
                now,
            ),
        )
        observation_id = int(cursor.lastrowid)
        context.records_written = 1
        context.metadata.update(
            {"metric_id": metric_id, "observation_id": observation_id}
        )
        return IngestResult(
            run_id=context.run_id,
            source_id=context.source_id,
            entity_type="metric_observation",
            entity_id=observation_id,
            asset_id=None,
            records_read=1,
            records_written=1,
            deduplicated=False,
            metadata={"metric_id": metric_id, "value_kind": value_kind},
        )
