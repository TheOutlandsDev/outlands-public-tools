from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from program_data.database import (
    backup_database,
    connect_database,
    database_status,
    initialize_database,
)


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database_path = self.root / "test.sqlite3"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialization_is_repeatable_and_healthy(self) -> None:
        applied = initialize_database(self.database_path)
        self.assertEqual(
            applied,
            ["001_initial.sql", "002_sql_snapshot_identity.sql"],
        )
        self.assertEqual(initialize_database(self.database_path), [])

        status = database_status(self.database_path)
        self.assertTrue(status["initialized"])
        self.assertEqual(status["quick_check"], ["ok"])
        self.assertEqual(status["foreign_key_violations"], 0)
        self.assertEqual(status["journal_mode"], "wal")
        self.assertEqual(status["user_version"], 2)
        self.assertGreaterEqual(status["schema_objects"]["tables"], 22)
        self.assertEqual(status["schema_objects"]["views"], 3)

    def test_readonly_connections_enforce_query_only(self) -> None:
        initialize_database(self.database_path)
        with closing(
            connect_database(self.database_path, readonly=True)
        ) as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("CREATE TABLE forbidden(value TEXT)")

    def test_backup_uses_consistent_sqlite_copy(self) -> None:
        initialize_database(self.database_path)
        backup_path = self.root / "backup.sqlite3"

        result = backup_database(self.database_path, backup_path)

        self.assertEqual(result, backup_path.resolve())
        self.assertTrue(backup_path.is_file())
        with closing(sqlite3.connect(backup_path)) as connection:
            self.assertEqual(
                connection.execute("PRAGMA quick_check").fetchone()[0],
                "ok",
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM schema_migrations"
                ).fetchone()[0],
                2,
            )


if __name__ == "__main__":
    unittest.main()
