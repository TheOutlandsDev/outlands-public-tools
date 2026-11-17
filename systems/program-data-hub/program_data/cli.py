"""Command-line interface for database and ingestion operations."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Sequence

from program_data import __version__
from program_data.config import get_database_path
from program_data.database import (
    backup_database,
    database_status,
    initialize_database,
    search_documents,
)
from program_data.ingest.datasets import ingest_dataset
from program_data.ingest.documents import ingest_document
from program_data.ingest.metrics import record_metric
from program_data.ingest.sql_exports import ingest_sql_export
from program_data.mes_policy import validate_query_contract


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _json_object(value: str, *, label: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed


def _metric_value(raw_value: str, value_kind: str) -> Any:
    if value_kind == "text":
        return raw_value
    if value_kind == "numeric":
        try:
            return int(raw_value)
        except ValueError:
            return float(raw_value)
    if value_kind == "boolean":
        normalized = raw_value.strip().casefold()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
        raise ValueError("Boolean metric values must be true/false, yes/no, or 1/0")
    if value_kind == "json":
        return json.loads(raw_value)

    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def _handle_init(args: argparse.Namespace) -> int:
    applied = initialize_database(args.database)
    status = database_status(args.database)
    status["applied_now"] = applied
    _print_json(status)
    return 0


def _handle_status(args: argparse.Namespace) -> int:
    _print_json(database_status(args.database))
    return 0


def _handle_backup(args: argparse.Namespace) -> int:
    backup_path = backup_database(args.database, args.destination)
    _print_json(
        {
            "source": str(get_database_path(args.database)),
            "backup": str(backup_path),
            "quick_check": "ok",
        }
    )
    return 0


def _handle_ingest_document(args: argparse.Namespace) -> int:
    result = ingest_document(
        args.path,
        args.database,
        source_key=args.source_key,
        source_name=args.source_name,
        title=args.title,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    _print_json(result.to_dict())
    return 0


def _handle_ingest_dataset(args: argparse.Namespace) -> int:
    result = ingest_dataset(
        args.path,
        args.database,
        source_key=args.source_key,
        source_name=args.source_name,
        key_column=args.key_column,
        observed_at_column=args.observed_at_column,
    )
    _print_json(result.to_dict())
    return 0


def _handle_ingest_sql_export(args: argparse.Namespace) -> int:
    query_text = (
        Path(args.query_file).read_text(encoding="utf-8")
        if args.query_file
        else None
    )
    parameters: dict[str, Any] | list[Any] | None = None
    if args.parameters_json:
        parameters = json.loads(args.parameters_json)
        if not isinstance(parameters, (dict, list)):
            raise ValueError("SQL parameters must be a JSON object or array")

    result = ingest_sql_export(
        args.path,
        args.database,
        query_key=args.query_key,
        query_name=args.query_name,
        query_text=query_text,
        source_key=args.source_key,
        source_name=args.source_name,
        server_name=args.server_name,
        database_name=args.database_name,
        record_key_column=args.record_key_column,
        executed_at=args.executed_at,
        parameters=parameters,
        description=args.description,
    )
    _print_json(result.to_dict())
    return 0


def _handle_record_metric(args: argparse.Namespace) -> int:
    dimensions = (
        _json_object(args.dimensions_json, label="Metric dimensions")
        if args.dimensions_json
        else {}
    )
    result = record_metric(
        args.metric_key,
        _metric_value(args.value, args.value_kind),
        args.database,
        observed_at=args.observed_at,
        unit=args.unit,
        dimensions=dimensions,
        display_name=args.display_name,
        description=args.description,
        source_key=args.source_key,
        source_name=args.source_name,
        quality_status=args.quality_status,
    )
    _print_json(result.to_dict())
    return 0


def _handle_search(args: argparse.Namespace) -> int:
    _print_json(search_documents(args.query, args.database, limit=args.limit))
    return 0


def _handle_validate_query_contract(args: argparse.Namespace) -> int:
    report = validate_query_contract(args.contract)
    _print_json(report.to_dict())
    return 0 if report.static_gate_passed else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="program-data",
        description="Manage the program's local SQLite data hub.",
    )
    parser.add_argument(
        "--database",
        help=(
            "SQLite path. Relative paths are anchored at the project root; "
            "defaults to PROGRAM_DATA_DB or data/runtime/program_data.sqlite3."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init-db", help="Create the database and apply pending migrations."
    )
    init_parser.set_defaults(handler=_handle_init)

    status_parser = subparsers.add_parser(
        "status", help="Run integrity checks and report schema/data counts."
    )
    status_parser.set_defaults(handler=_handle_status)

    backup_parser = subparsers.add_parser(
        "backup", help="Create an online SQLite backup and verify it."
    )
    backup_parser.add_argument(
        "--destination",
        help="Optional new backup path; generated under data/backups by default.",
    )
    backup_parser.set_defaults(handler=_handle_backup)

    document_parser = subparsers.add_parser(
        "ingest-document", help="Catalog and optionally text-index a document."
    )
    document_parser.add_argument("path")
    document_parser.add_argument("--source-key", default="local_documents")
    document_parser.add_argument("--source-name", default="Local documents")
    document_parser.add_argument("--title")
    document_parser.add_argument("--chunk-size", type=int, default=2000)
    document_parser.add_argument("--overlap", type=int, default=200)
    document_parser.set_defaults(handler=_handle_ingest_document)

    dataset_parser = subparsers.add_parser(
        "ingest-dataset", help="Ingest a CSV, JSON, JSONL, or NDJSON dataset."
    )
    dataset_parser.add_argument("path")
    dataset_parser.add_argument("--source-key", default="local_datasets")
    dataset_parser.add_argument("--source-name", default="Local datasets")
    dataset_parser.add_argument("--key-column")
    dataset_parser.add_argument("--observed-at-column")
    dataset_parser.set_defaults(handler=_handle_ingest_dataset)

    sql_parser = subparsers.add_parser(
        "ingest-sql-export",
        help="Ingest an exported SQL result with query and execution lineage.",
    )
    sql_parser.add_argument("path")
    sql_parser.add_argument("--query-key", required=True)
    sql_parser.add_argument("--query-name")
    sql_parser.add_argument("--query-file")
    sql_parser.add_argument("--source-key")
    sql_parser.add_argument("--source-name")
    sql_parser.add_argument("--server-name")
    sql_parser.add_argument("--database-name")
    sql_parser.add_argument("--record-key-column")
    sql_parser.add_argument("--executed-at")
    sql_parser.add_argument("--parameters-json")
    sql_parser.add_argument("--description")
    sql_parser.set_defaults(handler=_handle_ingest_sql_export)

    metric_parser = subparsers.add_parser(
        "record-metric", help="Record one typed metric observation."
    )
    metric_parser.add_argument("--metric-key", required=True)
    metric_parser.add_argument("--value", required=True)
    metric_parser.add_argument(
        "--value-kind",
        choices=("auto", "numeric", "text", "boolean", "json"),
        default="auto",
    )
    metric_parser.add_argument("--observed-at")
    metric_parser.add_argument("--unit")
    metric_parser.add_argument("--dimensions-json")
    metric_parser.add_argument("--display-name")
    metric_parser.add_argument("--description")
    metric_parser.add_argument("--source-key", default="application_metrics")
    metric_parser.add_argument("--source-name", default="Application metrics")
    metric_parser.add_argument(
        "--quality-status",
        choices=("valid", "suspect", "invalid"),
        default="valid",
    )
    metric_parser.set_defaults(handler=_handle_record_metric)

    search_parser = subparsers.add_parser(
        "search-documents", help="Search indexed document chunks with FTS5."
    )
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.set_defaults(handler=_handle_search)

    contract_parser = subparsers.add_parser(
        "validate-query-contract",
        help=(
            "Statically validate a project-owned MES query contract and SQL "
            "without connecting to MES."
        ),
    )
    contract_parser.add_argument("contract")
    contract_parser.set_defaults(handler=_handle_validate_query_contract)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (
        FileNotFoundError,
        FileExistsError,
        ValueError,
        TypeError,
        RuntimeError,
        sqlite3.Error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
