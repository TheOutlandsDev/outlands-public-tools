from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from opskit.common import OpsKitError
from opskit.sqlite_tools import backup_database, check_database


class SQLiteToolsTests(unittest.TestCase):
    def test_check_and_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite"
            destination = root / "backup.sqlite"
            with closing(sqlite3.connect(source)) as connection:
                connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
                connection.execute("INSERT INTO sample(value) VALUES ('ok')")
                connection.commit()

            checked = check_database(source)
            self.assertTrue(checked["ok"])
            self.assertTrue(checked["read_only"])

            result = backup_database(source, destination)
            self.assertTrue(result["validated"])
            self.assertEqual(64, len(result["sha256"]))
            with closing(sqlite3.connect(destination)) as connection:
                self.assertEqual(
                    "ok",
                    connection.execute("SELECT value FROM sample").fetchone()[0],
                )

    def test_backup_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite"
            destination = root / "existing.sqlite"
            with closing(sqlite3.connect(source)):
                ...
            destination.write_bytes(b"keep")
            with self.assertRaises(OpsKitError):
                backup_database(source, destination)
            self.assertEqual(b"keep", destination.read_bytes())


if __name__ == "__main__":
    unittest.main()
