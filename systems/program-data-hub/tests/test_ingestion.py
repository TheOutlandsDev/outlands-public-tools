from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from program_data.database import connect_database, search_documents
from program_data.ingest.datasets import ingest_dataset
from program_data.ingest.documents import ingest_document
from program_data.ingest.metrics import record_metric
from program_data.ingest.sql_exports import ingest_sql_export

FIXTURES = Path(__file__).with_name("fixtures")


class IngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temporary_directory.name) / "ingestion.sqlite3"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_document_text_is_indexed_and_file_retry_is_idempotent(self) -> None:
        first = ingest_document(
            FIXTURES / "sample_document.md",
            self.database_path,
        )
        second = ingest_document(
            FIXTURES / "sample_document.md",
            self.database_path,
        )

        self.assertFalse(first.deduplicated)
        self.assertTrue(second.deduplicated)
        self.assertEqual(first.asset_id, second.asset_id)
        results = search_documents("calibration", self.database_path)
        self.assertEqual(len(results), 1)
        self.assertIn("[calibration]", results[0]["snippet"].casefold())

        with closing(
            connect_database(self.database_path, readonly=True)
        ) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM data_assets").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM ingestion_runs").fetchone()[0],
                2,
            )

    def test_dataset_preserves_rows_and_records_inferred_schema(self) -> None:
        result = ingest_dataset(
            FIXTURES / "sample_dataset.csv",
            self.database_path,
            key_column="id",
        )

        self.assertEqual(result.records_written, 2)
        with closing(
            connect_database(self.database_path, readonly=True)
        ) as connection:
            dataset = connection.execute(
                "SELECT row_count, column_count, schema_json FROM datasets"
            ).fetchone()
            self.assertEqual(dataset["row_count"], 2)
            self.assertEqual(dataset["column_count"], 4)
            schema = json.loads(dataset["schema_json"])
            inferred = {
                column["name"]: column["inferred_type"]
                for column in schema["columns"]
            }
            self.assertEqual(inferred["quantity"], "integer")
            self.assertEqual(inferred["active"], "boolean")

            row = json.loads(
                connection.execute(
                    """
                    SELECT row_json
                    FROM dataset_rows
                    WHERE record_key = '1001'
                    """
                ).fetchone()["row_json"]
            )
            self.assertEqual(row["quantity"], "12")

    def test_invalid_dataset_rolls_back_asset_and_keeps_failed_run(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing_key"):
            ingest_dataset(
                FIXTURES / "sample_dataset.csv",
                self.database_path,
                key_column="missing_key",
            )

        with closing(
            connect_database(self.database_path, readonly=True)
        ) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM data_assets").fetchone()[0],
                0,
            )
            run = connection.execute(
                "SELECT status, records_read, error_summary FROM ingestion_runs"
            ).fetchone()
            self.assertEqual(run["status"], "failed")
            self.assertEqual(run["records_read"], 2)
            self.assertIn("missing_key", run["error_summary"])

    def test_sql_export_tracks_query_version_execution_and_rows(self) -> None:
        query_text = (FIXTURES / "sample_query.sql").read_text(encoding="utf-8")
        result = ingest_sql_export(
            FIXTURES / "sample_sql_export.jsonl",
            self.database_path,
            query_key="active_orders",
            query_name="Active orders",
            query_text=query_text,
            server_name="DemoServer",
            database_name="DemoOperations",
            record_key_column="order_id",
            parameters={"statuses": ["active", "queued"]},
        )

        self.assertEqual(result.records_written, 2)
        with closing(
            connect_database(self.database_path, readonly=True)
        ) as connection:
            execution = connection.execute(
                """
                SELECT row_count, server_name, database_name, query_version_id
                FROM sql_executions
                """
            ).fetchone()
            self.assertEqual(execution["row_count"], 2)
            self.assertEqual(execution["server_name"], "DemoServer")
            self.assertEqual(execution["database_name"], "DemoOperations")
            self.assertIsNotNone(execution["query_version_id"])
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM sql_result_rows"
                ).fetchone()[0],
                2,
            )

    def test_sql_snapshot_time_distinguishes_refresh_from_retry(self) -> None:
        first = ingest_sql_export(
            FIXTURES / "sample_sql_export.jsonl",
            self.database_path,
            query_key="active_orders",
            executed_at="2026-07-23T12:00:00Z",
        )
        second = ingest_sql_export(
            FIXTURES / "sample_sql_export.jsonl",
            self.database_path,
            query_key="active_orders",
            executed_at="2026-07-23T13:00:00Z",
        )
        retry = ingest_sql_export(
            FIXTURES / "sample_sql_export.jsonl",
            self.database_path,
            query_key="active_orders",
            executed_at="2026-07-23T13:00:00Z",
        )

        self.assertFalse(first.deduplicated)
        self.assertFalse(second.deduplicated)
        self.assertTrue(retry.deduplicated)
        self.assertNotEqual(first.entity_id, second.entity_id)
        self.assertEqual(second.entity_id, retry.entity_id)

        with closing(
            connect_database(self.database_path, readonly=True)
        ) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM sql_executions"
                ).fetchone()[0],
                2,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM data_assets"
                ).fetchone()[0],
                2,
            )

    def test_metric_retry_is_idempotent_and_conflict_is_rejected(self) -> None:
        observed_at = "2026-07-23T12:00:00Z"
        first = record_metric(
            "queue_depth",
            12,
            self.database_path,
            observed_at=observed_at,
            unit="count",
            dimensions={"area": "A"},
        )
        second = record_metric(
            "queue_depth",
            12,
            self.database_path,
            observed_at=observed_at,
            unit="count",
            dimensions={"area": "A"},
        )

        self.assertFalse(first.deduplicated)
        self.assertTrue(second.deduplicated)
        self.assertEqual(first.entity_id, second.entity_id)

        with self.assertRaisesRegex(ValueError, "different metric value"):
            record_metric(
                "queue_depth",
                13,
                self.database_path,
                observed_at=observed_at,
                unit="count",
                dimensions={"area": "A"},
            )

        with closing(
            connect_database(self.database_path, readonly=True)
        ) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM metric_observations"
                ).fetchone()[0],
                1,
            )
            latest = connection.execute(
                """
                SELECT metric_key, value_number, dimensions_json
                FROM v_latest_metric_observations
                """
            ).fetchone()
            self.assertEqual(latest["metric_key"], "queue_depth")
            self.assertEqual(latest["value_number"], 12.0)
            self.assertEqual(
                json.loads(latest["dimensions_json"]),
                {"area": "A"},
            )
            statuses = [
                row["status"]
                for row in connection.execute(
                    "SELECT status FROM ingestion_runs ORDER BY started_at"
                )
            ]
            self.assertEqual(statuses.count("failed"), 1)


if __name__ == "__main__":
    unittest.main()
