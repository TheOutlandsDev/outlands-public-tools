"""Disposable synthetic regressions for the reviewed public candidate."""
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import hashlib
import io
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
from safe_file_mover import cli, core
from safe_file_mover.journal import Journal

@contextmanager
def permissive_umask():
    previous = os.umask(0)
    try:
        yield
    finally:
        os.umask(previous)

class PublicSafetyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mover-fictional-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state = self.root / "state"
        self.destination = self.root / "destination"
        self.destination.mkdir()
        self.source = self.root / "fictional.txt"
        self.source.write_bytes(b"fictional source content")

    def argument_failure(self, arguments):
        output, error = io.StringIO(), io.StringIO()
        with mock.patch.object(cli, "SafeMoveEngine") as engine:
            with redirect_stdout(output), redirect_stderr(error):
                self.assertEqual(cli.main(arguments), 2)
        engine.assert_not_called()
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(error.getvalue(), "Error: ARGUMENTS_INVALID\n")
        self.assertTrue(self.source.exists())
        self.assertFalse(self.state.exists())

    def test_unknown_argument_is_not_echoed(self):
        self.argument_failure(["--unknown", "PRIVATE-ARGUMENT-CANARY"])

    def test_invalid_subcommand_is_not_echoed(self):
        self.argument_failure(["PRIVATE-COMMAND-CANARY"])

    def test_missing_move_destination_is_not_echoed(self):
        self.argument_failure(["move", str(self.source)])

    def test_invalid_choice_is_not_echoed(self):
        self.argument_failure(["move", str(self.source), str(self.destination), "--on-conflict", "PRIVATE-CHOICE-CANARY"])

    def test_no_arguments_show_help_without_engine_or_gui(self):
        output = io.StringIO()
        with mock.patch.object(cli, "SafeMoveEngine") as engine:
            with redirect_stdout(output):
                self.assertEqual(cli.main([]), 0)
        engine.assert_not_called()
        self.assertIn("usage: safe-move", output.getvalue())
        self.assertFalse(self.state.exists())

    @unittest.skipIf(os.name == "nt", "POSIX permission regression")
    def test_fresh_journal_is_private_under_permissive_umask(self):
        journal = Journal(self.state)
        with permissive_umask():
            journal.initialize()
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(journal.database_path.stat().st_mode), 0o600)

    @unittest.skipIf(os.name == "nt", "POSIX permission regression")
    def test_existing_shared_state_is_rejected_without_chmod(self):
        self.state.mkdir(mode=0o755)
        self.state.chmod(0o755)
        with self.assertRaises(ValueError):
            Journal(self.state).initialize()
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o755)
        self.assertEqual(list(self.state.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "POSIX permission regression")
    def test_existing_shared_database_is_rejected_without_chmod(self):
        self.state.mkdir(mode=0o700)
        journal = Journal(self.state)
        journal.initialize()
        journal.database_path.chmod(0o644)
        before = journal.database_path.read_bytes()
        with self.assertRaises(ValueError):
            journal.initialize()
        self.assertEqual(journal.database_path.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(journal.database_path.stat().st_mode), 0o644)

    @unittest.skipIf(os.name == "nt", "POSIX symlink regression")
    def test_symlink_state_is_rejected(self):
        target = self.root / "state-target"
        target.mkdir(mode=0o700)
        self.state.symlink_to(target, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            Journal(self.state).initialize()
        self.assertEqual(list(target.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "POSIX symlink regression")
    def test_symlink_database_is_rejected_without_target_changes(self):
        self.state.mkdir(mode=0o700)
        target = self.root / "database-target"
        target.write_bytes(b"")
        (self.state / "moves.sqlite3").symlink_to(target)
        with self.assertRaises((ValueError, OSError)):
            Journal(self.state).initialize()
        self.assertEqual(target.read_bytes(), b"")

    @unittest.skipIf(os.name == "nt", "POSIX symlink regression")
    def test_environment_state_symlink_is_rejected(self):
        target = self.root / "environment-target"
        target.mkdir(mode=0o700)
        self.state.symlink_to(target, target_is_directory=True)
        with mock.patch.dict(os.environ, {"SAFE_FILE_MOVER_STATE_DIR": str(self.state)}):
            with self.assertRaises((ValueError, OSError)):
                Journal().initialize()
        self.assertEqual(list(target.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "POSIX hard-link regression")
    def test_hardlinked_database_is_rejected(self):
        journal = Journal(self.state)
        journal.initialize()
        os.link(journal.database_path, self.root / "database-alias")
        before = journal.database_path.read_bytes()
        with self.assertRaises(ValueError):
            journal.initialize()
        self.assertEqual(journal.database_path.read_bytes(), before)

    @unittest.skipIf(os.name == "nt", "POSIX lock regression")
    def test_symlink_operation_lock_is_rejected_without_target_changes(self):
        engine = core.SafeMoveEngine(self.state)
        engine.journal.initialize()
        target = self.root / "lock-target"
        target.write_bytes(b"")
        (self.state / "operation.lock").symlink_to(target)
        with self.assertRaises((core.OperationStateError, OSError, ValueError)):
            engine.move(self.source, self.destination)
        self.assertEqual(target.read_bytes(), b"")
        self.assertTrue(self.source.exists())

    @unittest.skipIf(os.name == "nt", "POSIX lock regression")
    def test_shared_operation_lock_is_rejected(self):
        engine = core.SafeMoveEngine(self.state)
        engine.journal.initialize()
        lock = self.state / "operation.lock"
        lock.write_bytes(b"synthetic")
        lock.chmod(0o644)
        with self.assertRaises(core.OperationStateError):
            engine.move(self.source, self.destination)
        self.assertEqual(lock.read_bytes(), b"synthetic")
        self.assertTrue(self.source.exists())

    @unittest.skipIf(os.name == "nt", "POSIX staging regression")
    def test_file_staging_starts_private(self):
        self.source.chmod(0o600)
        observed = []
        def progress(_value):
            observed.extend(stat.S_IMODE(p.stat().st_mode) for p in self.destination.glob("*.partial"))
        with permissive_umask():
            operation = core.SafeMoveEngine(self.state, chunk_size=3).move(self.source, self.destination, progress=progress)
        self.assertTrue(observed)
        self.assertEqual(set(observed), {0o600})
        self.assertEqual(stat.S_IMODE(operation.destination.stat().st_mode), 0o600)

    @unittest.skipIf(os.name == "nt", "POSIX staging regression")
    def test_directory_staging_starts_private(self):
        tree = self.root / "fictional-tree"
        tree.mkdir(mode=0o700)
        (tree / "item.txt").write_bytes(b"fictional")
        observed = []
        def boundary(phase, _path):
            if phase == "before_copy_item":
                observed.extend(stat.S_IMODE(p.stat().st_mode) for p in self.destination.glob("*.partial"))
        with permissive_umask():
            core.SafeMoveEngine(self.state, fault_hook=boundary).move(tree, self.destination)
        self.assertTrue(observed)
        self.assertEqual(set(observed), {0o700})

    @unittest.skipIf(os.name == "nt", "POSIX no-follow regression")
    def test_hash_refuses_replaced_symlink_without_hashing_target(self):
        before = self.source.stat()
        target = self.root / "fictional-other.txt"
        target.write_bytes(b"FOREIGN-FIXTURE-CANARY")
        self.source.unlink()
        self.source.symlink_to(target)
        digest = hashlib.sha256()
        observed = []
        class RecordingDigest:
            def update(self, data):
                observed.append(data)
                digest.update(data)
            def hexdigest(self):
                return digest.hexdigest()
        with mock.patch.object(core.hashlib, "sha256", return_value=RecordingDigest()):
            with self.assertRaises(core.SafeMoveError):
                core._hash_stable_file(self.source, before, 4)
        self.assertEqual(observed, [])
        self.assertEqual(target.read_bytes(), b"FOREIGN-FIXTURE-CANARY")

    def test_purge_rechecks_destination_at_delete_boundary(self):
        engine = core.SafeMoveEngine(self.state)
        operation = engine.move(self.source, self.destination)
        def boundary(phase, _path):
            if phase == "before_purge_delete":
                operation.destination.write_bytes(b"changed fictional destination")
        with self.assertRaises(core.VerificationError):
            core.SafeMoveEngine(self.state, fault_hook=boundary).purge_backup(operation.operation_id)
        purging = Path(str(operation.recovery_copy) + ".purging")
        self.assertEqual(purging.read_bytes(), b"fictional source content")
        self.assertEqual(engine.journal.get(operation.operation_id).status, "purging")

if __name__ == "__main__":
    unittest.main()
