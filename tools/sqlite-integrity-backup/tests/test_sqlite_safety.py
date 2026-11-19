from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from opskit.common import OpsKitError
from opskit.sqlite_tools import backup_database, check_database


def create_sample(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES ('fictional sample')")
        connection.commit()


def create_foreign_key_violation(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))"
        )
        connection.execute("INSERT INTO child VALUES (1, 99)")
        connection.commit()


def read_sample_values(path: Path) -> list[str]:
    with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as connection:
        return [row[0] for row in connection.execute("SELECT value FROM sample ORDER BY id")]


def sidecar(path: Path, suffix: str) -> Path:
    return path.with_name(path.name + suffix)


class SQLiteSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.source = self.workspace / "source.sqlite"
        self.destination = self.workspace / "backup.sqlite"

    def test_quick_and_full_integrity_and_foreign_keys(self) -> None:
        create_sample(self.source)
        before = self.source.read_bytes()
        for full, pragma in [(False, "quick_check"), (True, "integrity_check")]:
            with self.subTest(pragma=pragma):
                result = check_database(self.source, full=full)
                self.assertEqual(result["check"], pragma)
                self.assertTrue(result["ok"])
                self.assertTrue(result["read_only"])
                self.assertEqual(result["integrity_messages"], ["ok"])
                self.assertEqual(result["foreign_key_violations"], [])
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(set(self.workspace.iterdir()), {self.source})

        broken = self.workspace / "foreign-keys.sqlite"
        create_foreign_key_violation(broken)
        before = broken.read_bytes()
        for full in (False, True):
            with self.subTest(full=full):
                result = check_database(broken, full=full)
                self.assertFalse(result["ok"])
                self.assertEqual(result["integrity_messages"], ["ok"])
                self.assertEqual(
                    result["foreign_key_violations"],
                    [{"table": "child", "rowid": 1, "parent": "parent", "foreign_key_index": 0}],
                )
        self.assertEqual(broken.read_bytes(), before)
        self.assertEqual(set(self.workspace.iterdir()), {self.source, broken})

    def test_wal_backup_includes_committed_rows_without_changing_source(self) -> None:
        writer = self.enterContext(closing(sqlite3.connect(self.source)))
        self.assertEqual(writer.execute("PRAGMA journal_mode = WAL").fetchone(), ("wal",))
        writer.execute("PRAGMA wal_autocheckpoint = 0")
        writer.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        writer.execute("INSERT INTO sample(value) VALUES ('checkpointed')")
        writer.commit()
        self.assertEqual(writer.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0], 0)
        checkpointed_main = self.source.read_bytes()
        writer.execute("INSERT INTO sample(value) VALUES ('committed in WAL')")
        writer.commit()
        wal = sidecar(self.source, "-wal")
        self.assertGreater(wal.stat().st_size, 32)
        self.assertEqual(self.source.read_bytes(), checkpointed_main)

        writer.execute("INSERT INTO sample(value) VALUES ('uncommitted')")
        source_wal = wal.read_bytes()
        source_entries = set(self.workspace.iterdir())
        checked = check_database(self.source, full=True)
        self.assertTrue(checked["ok"])
        self.assertEqual(checked["journal_mode"], "wal")
        result = backup_database(self.source, self.destination)
        self.assertTrue(result["validated"])
        self.assertEqual(result["sha256"], hashlib.sha256(self.destination.read_bytes()).hexdigest())
        self.assertEqual(read_sample_values(self.destination), ["checkpointed", "committed in WAL"])
        self.assertEqual(self.source.read_bytes(), checkpointed_main)
        self.assertEqual(wal.read_bytes(), source_wal)
        self.assertEqual(set(self.workspace.iterdir()), source_entries | {self.destination})
        self.assertTrue(writer.in_transaction)
        writer.rollback()

    def test_late_destination_is_not_overwritten(self) -> None:
        create_sample(self.source)
        before = self.source.read_bytes()
        real_link = os.link

        def create_competing_file(staged: Path, target: Path) -> None:
            self.assertEqual(Path(target), self.destination.resolve())
            self.assertTrue(check_database(Path(staged))["ok"])
            with self.destination.open("xb") as stream:
                stream.write(b"file created by another writer")
            real_link(staged, target)

        with patch("opskit.sqlite_tools.os.link", side_effect=create_competing_file) as link:
            with self.assertRaises(OpsKitError):
                backup_database(self.source, self.destination)
        link.assert_called_once()
        self.assertEqual(self.destination.read_bytes(), b"file created by another writer")
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(set(self.workspace.iterdir()), {self.source, self.destination})

    def test_same_file_and_hard_link_alias_are_refused(self) -> None:
        create_sample(self.source)
        before = self.source.read_bytes()
        os.link(self.source, self.destination)
        with self.assertRaises(OpsKitError):
            backup_database(self.source, self.source, force=True)
        with self.assertRaises(OpsKitError):
            backup_database(self.source, self.destination, force=True)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.destination.read_bytes(), before)
        self.assertTrue(os.path.samefile(self.source, self.destination))

    def test_explicit_force_replaces_a_regular_destination(self) -> None:
        create_sample(self.source)
        before = self.source.read_bytes()
        with closing(sqlite3.connect(self.destination)) as connection:
            connection.execute("CREATE TABLE old_sample (id INTEGER)")
            connection.commit()
        report = backup_database(self.source, self.destination, force=True)
        self.assertTrue(report["force_requested"])
        self.assertTrue(report["replaced_existing"])
        self.assertTrue(report["validated"])
        self.assertEqual(read_sample_values(self.destination), ["fictional sample"])
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(set(self.workspace.iterdir()), {self.source, self.destination})

    def test_invalid_backup_cleans_staging_and_preserves_source(self) -> None:
        create_foreign_key_violation(self.source)
        before = self.source.read_bytes()
        self.destination.write_bytes(b"preserve prior destination")
        with self.assertRaises(OpsKitError):
            backup_database(self.source, self.destination, force=True)
        self.assertEqual(self.destination.read_bytes(), b"preserve prior destination")
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(set(self.workspace.iterdir()), {self.source, self.destination})

    def test_destination_source_sidecar_is_refused(self) -> None:
        create_sample(self.source)
        before = self.source.read_bytes()
        for suffix in ("-wal", "-shm", "-journal"):
            with self.subTest(suffix=suffix):
                alias = sidecar(self.source, suffix)
                with self.assertRaises(OpsKitError):
                    backup_database(self.source, alias, force=True)
                self.assertFalse(alias.exists())
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(set(self.workspace.iterdir()), {self.source})

    def test_active_destination_sidecars_are_refused(self) -> None:
        create_sample(self.source)
        source = self.source.read_bytes()
        writer = self.enterContext(closing(sqlite3.connect(self.destination)))
        self.assertEqual(writer.execute("PRAGMA journal_mode = WAL").fetchone(), ("wal",))
        writer.execute("CREATE TABLE prior (value TEXT)")
        writer.execute("INSERT INTO prior VALUES ('keep')")
        writer.commit()
        wal = sidecar(self.destination, "-wal")
        self.assertTrue(wal.is_file())
        destination, wal_before = self.destination.read_bytes(), wal.read_bytes()
        entries = set(self.workspace.iterdir())
        with self.assertRaises(OpsKitError):
            backup_database(self.source, self.destination, force=True)
        self.assertEqual(self.source.read_bytes(), source)
        self.assertEqual(self.destination.read_bytes(), destination)
        self.assertEqual(wal.read_bytes(), wal_before)
        self.assertEqual(set(self.workspace.iterdir()), entries)
        self.assertEqual(writer.execute("SELECT value FROM prior").fetchall(), [("keep",)])
