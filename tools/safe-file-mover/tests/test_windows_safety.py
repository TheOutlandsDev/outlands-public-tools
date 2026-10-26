"""Generated local fixtures only: no real inputs, live shares or GUI use."""

from contextlib import redirect_stderr, redirect_stdout
import builtins
import ctypes
from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from safe_file_mover import cli, core, windows_fs as win
from safe_file_mover.journal import Journal


HERE = Path(__file__).absolute().parents[1]
ERRORS = (core.SafeMoveError, ValueError, OSError)
ADS = "fictional.metadata"


def stream_path(path, name=ADS):
    return str(path) + ":" + name


def write_stream(path, payload):
    with open(stream_path(path), "wb") as target:
        target.write(payload)
        target.flush()
        os.fsync(target.fileno())


def read_stream(path):
    with open(stream_path(path), "rb") as source:
        return source.read()


def guarded_cleanup(root, base, temporary):
    root, base = root.absolute(), base.absolute()
    if os.name == "nt":
        from safe_file_mover.windows_fs import checked_path

        # Native normalized-name checks avoid a DOS resolve() query, which can
        # be unavailable in a restricted Windows environment.
        root, base = checked_path(root), checked_path(base)
    if root == base or not root.is_relative_to(base):
        raise RuntimeError("UNEXPECTED_FIXTURE_CLEANUP_TARGET")
    # Check every actual ancestor before the recursive TemporaryDirectory cleanup.
    # No link/reparse component is permitted in the owned cleanup pathname.
    for item in (root, *root.parents):
        if item.exists() and (
            item.is_symlink() or getattr(item.lstat(), "st_file_attributes", 0) & 0x400
        ):
            raise RuntimeError("LINKED_FIXTURE_CLEANUP_TARGET")
    temporary.cleanup()


class PortableSafetyContracts(unittest.TestCase):
    def test_no_arguments_and_help_do_not_create_an_engine(self):
        for args in ([], ["--help"]):
            output, errors = io.StringIO(), io.StringIO()
            with (
                patch.object(cli, "SafeMoveEngine") as engine,
                redirect_stdout(output),
                redirect_stderr(errors),
            ):
                if args:
                    with self.assertRaises(SystemExit) as stopped:
                        cli.main(args)
                    self.assertEqual(stopped.exception.code, 0)
                else:
                    self.assertEqual(cli.main(args), 0)
            engine.assert_not_called()
            self.assertIn("usage: safe-move", output.getvalue())
            self.assertEqual(errors.getvalue(), "")

    def test_argument_errors_do_not_echo_values_or_construct_engine(self):
        for args in (
            ["--fictional-unknown", "FICTIONAL_ARGUMENT_CANARY"],
            ["move", "fictional-source"],
            [
                "move",
                "fictional-source",
                "fictional-destination",
                "--on-conflict",
                "FICTIONAL_CHOICE_CANARY",
            ],
        ):
            output, errors = io.StringIO(), io.StringIO()
            with (
                patch.object(cli, "SafeMoveEngine") as engine,
                redirect_stdout(output),
                redirect_stderr(errors),
            ):
                self.assertEqual(cli.main(args), 2)
            engine.assert_not_called()
            self.assertEqual(output.getvalue(), "")
            self.assertEqual(errors.getvalue(), "Error: ARGUMENTS_INVALID\n")

    def test_named_stream_names_refuse_separators_stream_types_and_traversal(self):
        for value in (
            "",
            "::$DATA",
            ":fixture:$INDEX_ALLOCATION",
            ":bad/name:$DATA",
            ":bad\\name:$DATA",
            ":bad:name:$DATA",
            ":bad\x00name:$DATA",
        ):
            with self.subTest(value=value), self.assertRaises(core.VerificationError):
                core._validate_windows_stream_name(value)
        core._validate_windows_stream_name(":" + ADS + ":$DATA")

    def test_named_stream_size_and_digest_validation_remains_strict(self):
        for size, digest in ((-1, "a" * 64), (1, "x" * 64), (1, "a" * 63)):
            with self.assertRaises(core.VerificationError):
                core._validate_named_stream(
                    core.NamedStream(":" + ADS + ":$DATA", size, digest)
                )

    def test_managed_path_name_check_rejects_unrelated_names(self):
        with self.assertRaises(core.OperationStateError):
            core._validate_managed_path(
                Path("fictional-unrelated"), "a" * 32, ".partial"
            )


@unittest.skipUnless(os.name == "nt", "Native Windows safety fixture")
class NativeWindowsSafety(unittest.TestCase):
    def setUp(self):
        base = Path(
            os.environ.get("OUTLANDS_TEST_TEMP", tempfile.gettempdir())
        ).absolute()
        self.temporary = tempfile.TemporaryDirectory(prefix="mover-native-", dir=base)
        self.root = Path(self.temporary.name)
        self.addCleanup(guarded_cleanup, self.root, base, self.temporary)
        self.source = self.root / "fictional-source.txt"
        self.source.write_bytes(b"Fictional primary payload\x00\xff")
        self.original = self.source.read_bytes()
        self.destination = self.root / "fictional-destination"
        self.destination.mkdir()
        self.state = self.root / "fictional-state"

    def engine(self, **kwargs):
        return core.SafeMoveEngine(self.state, chunk_size=7, **kwargs)

    def unavailable(self, message):
        if os.environ.get("OUTLANDS_MOVER_REQUIRE_NATIVE_FEATURES") == "1":
            self.fail(message)
        self.skipTest(message)

    def junction(self, link, target):
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            self.unavailable("Native junction fixture unavailable")

    def hardlink(self, link, target):
        try:
            os.link(target, link)
        except (OSError, NotImplementedError):
            self.unavailable("Native hardlink fixture unavailable")

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError):
            self.unavailable("Native symlink fixture unavailable")

    def ads(self, path, payload=b"Fictional stream payload\x00\xff"):
        try:
            write_stream(path, payload)
            self.assertEqual(read_stream(path), payload)
        except OSError:
            self.unavailable("Native named-data-stream fixture unavailable")
        return payload

    def test_plan_hashes_without_source_state_or_destination_mutation(self):
        before = set(self.root.iterdir())
        result = self.engine().plan(self.source, self.destination)
        self.assertEqual(result.manifest.total_bytes, len(self.original))
        self.assertEqual(result.manifest.file_count, 1)
        self.assertEqual(
            result.manifest.entries[0].sha256, hashlib.sha256(self.original).hexdigest()
        )
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(set(self.root.iterdir()), before)
        self.assertFalse(self.state.exists())
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_verified_move_retains_content_and_restore_keeps_destination(self):
        operation = self.engine().move(self.source, self.destination)
        self.assertEqual(operation.status, "backup_retained")
        self.assertEqual(operation.destination.read_bytes(), self.original)
        self.assertEqual(operation.recovery_copy.read_bytes(), self.original)
        self.assertFalse(self.source.exists())
        restored = self.engine().restore_backup(operation.operation_id)
        self.assertEqual(restored.status, "restored")
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(operation.destination.read_bytes(), self.original)
        self.assertFalse(operation.recovery_copy.exists())

    def test_nested_tree_and_empty_directory_are_verified(self):
        tree = self.root / "fictional-tree"
        (tree / "nested" / "empty").mkdir(parents=True)
        (tree / "nested" / "payload.bin").write_bytes(self.original)
        operation = self.engine().move(tree, self.destination)
        self.assertTrue((operation.destination / "nested" / "empty").is_dir())
        self.assertEqual(
            (operation.destination / "nested" / "payload.bin").read_bytes(),
            self.original,
        )
        self.assertEqual(
            (operation.recovery_copy / "nested" / "payload.bin").read_bytes(),
            self.original,
        )

    def test_preexisting_destination_is_never_overwritten(self):
        target = self.destination / self.source.name
        target.write_bytes(b"Fictional existing destination")
        with self.assertRaises(core.CollisionError):
            self.engine().move(self.source, self.destination)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(target.read_bytes(), b"Fictional existing destination")

    def test_destination_appearing_at_commit_is_preserved(self):
        target = self.destination / self.source.name

        def intrude(phase, _path):
            if phase == "before_destination_commit":
                target.write_bytes(b"Fictional concurrent destination")

        with self.assertRaises(core.CollisionError):
            self.engine(fault_hook=intrude).move(self.source, self.destination)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(target.read_bytes(), b"Fictional concurrent destination")

    def test_recovery_after_destination_commit_retains_both_verified_copies(self):
        def crash(phase, _path):
            if phase == "after_destination_commit":
                raise RuntimeError("Fictional interrupted commit")

        with self.assertRaises(RuntimeError):
            self.engine(fault_hook=crash).move(self.source, self.destination)
        record = self.engine().journal.list()[0]
        self.assertTrue(self.source.exists())
        self.assertEqual(Path(record.destination).read_bytes(), self.original)
        operation = self.engine().recover(record.operation_id)
        self.assertEqual(operation.status, "backup_retained")
        self.assertEqual(operation.destination.read_bytes(), self.original)
        self.assertEqual(operation.recovery_copy.read_bytes(), self.original)

    def test_abandon_discards_only_uncommitted_generated_staging(self):
        def crash(phase, _path):
            if phase == "after_copy":
                raise RuntimeError("Fictional interrupted copy")

        with self.assertRaises(RuntimeError):
            self.engine(fault_hook=crash).move(self.source, self.destination)
        record = self.engine().journal.list()[0]
        self.assertTrue(Path(record.staging).exists())
        operation = self.engine().abandon(record.operation_id)
        self.assertEqual(operation.status, "abandoned")
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse(Path(record.staging).exists())
        self.assertFalse(Path(record.destination).exists())

    def test_purge_deletes_only_the_reverified_generated_recovery_copy(self):
        operation = self.engine().move(self.source, self.destination)
        final = self.engine().purge_backup(operation.operation_id)
        self.assertEqual(final.status, "complete")
        self.assertEqual(operation.destination.read_bytes(), self.original)
        self.assertFalse(operation.recovery_copy.exists())

    def test_purge_changed_destination_keeps_recovery_bytes(self):
        operation = self.engine().move(self.source, self.destination)
        operation.destination.write_bytes(b"Fictional changed destination")
        with self.assertRaises(core.VerificationError):
            self.engine().purge_backup(operation.operation_id)
        self.assertEqual(operation.recovery_copy.read_bytes(), self.original)

    def test_purge_final_callback_change_retains_managed_purging_copy(self):
        operation = self.engine().move(self.source, self.destination)

        def changed(phase, _path):
            if phase == "before_purge_delete":
                operation.destination.write_bytes(b"Fictional late change")

        with self.assertRaises(core.VerificationError):
            self.engine(fault_hook=changed).purge_backup(operation.operation_id)
        purging = Path(str(operation.recovery_copy) + ".purging")
        self.assertEqual(purging.read_bytes(), self.original)

    def test_named_streams_on_file_and_directory_are_available_and_preserved(self):
        payload = self.ads(self.source)
        directory = self.root / "fictional-streamed-directory"
        directory.mkdir()
        (directory / "payload.bin").write_bytes(self.original)
        directory_payload = self.ads(directory, b"Fictional directory stream")
        file_operation = self.engine().move(self.source, self.destination)
        self.assertEqual(read_stream(file_operation.destination), payload)
        self.assertEqual(read_stream(file_operation.recovery_copy), payload)
        directory_operation = self.engine().move(directory, self.destination)
        self.assertEqual(
            read_stream(directory_operation.destination), directory_payload
        )
        self.assertEqual(
            read_stream(directory_operation.recovery_copy), directory_payload
        )

    def test_changed_named_stream_blocks_purge_without_touching_recovery(self):
        payload = self.ads(self.source)
        operation = self.engine().move(self.source, self.destination)
        before = operation.destination.stat(follow_symlinks=False)
        write_stream(operation.destination, b"Z" * len(payload))
        os.utime(operation.destination, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaises(core.VerificationError):
            self.engine().purge_backup(operation.operation_id)
        self.assertEqual(read_stream(operation.recovery_copy), payload)

    def test_native_symlink_copy_preserves_link_and_target_bytes(self):
        link = self.root / "fictional-link"
        self.symlink(link, self.source.name)
        operation = self.engine().move(link, self.destination)
        self.assertTrue(operation.destination.is_symlink())
        self.assertEqual(os.readlink(operation.destination), self.source.name)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertTrue(operation.recovery_copy.is_symlink())

    def test_native_junction_source_and_destination_parents_are_refused(self):
        target = self.root / "fictional-junction-target"
        target.mkdir()
        (target / "payload.txt").write_bytes(self.original)
        junction = self.root / "fictional-junction"
        self.junction(junction, target)
        for source, destination in (
            (junction, self.destination),
            (junction / "payload.txt", self.destination),
            (self.source, junction),
        ):
            with (
                self.subTest(source=source, destination=destination),
                self.assertRaises(ERRORS),
            ):
                self.engine().plan(source, destination)
        self.assertEqual((target / "payload.txt").read_bytes(), self.original)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_native_junction_state_is_refused_before_database_creation(self):
        target = self.root / "fictional-state-target"
        target.mkdir()
        self.junction(self.state, target)
        with self.assertRaises(ERRORS):
            Journal(self.state).initialize()
        self.assertEqual(list(target.iterdir()), [])

    def test_native_junction_state_ancestor_is_refused_before_child_creation(self):
        target = self.root / "fictional-state-parent-target"
        target.mkdir()
        parent = self.root / "fictional-state-parent-link"
        self.junction(parent, target)
        with self.assertRaises(ERRORS):
            Journal(parent / "new-state").initialize()
        self.assertEqual(list(target.iterdir()), [])

    def test_hardlinked_database_and_operation_lock_are_refused(self):
        journal = Journal(self.state)
        journal.initialize()
        alias = self.root / "fictional-database-alias"
        self.hardlink(alias, journal.database_path)
        before = alias.read_bytes()
        with self.assertRaises(ERRORS):
            Journal(self.state).initialize()
        self.assertEqual(alias.read_bytes(), before)
        alias.unlink()
        lock = self.state / "operation.lock"
        lock.write_bytes(b"Fictional lock sentinel")
        lock_alias = self.root / "fictional-lock-alias"
        self.hardlink(lock_alias, lock)
        before_lock = lock.read_bytes()
        with self.assertRaises(ERRORS):
            self.engine().move(self.source, self.destination)
        self.assertEqual(lock.read_bytes(), before_lock)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_symlink_database_lock_and_rollback_are_refused_without_target_change(self):
        journal = Journal(self.state)
        journal.initialize()
        target = self.root / "fictional-outside-sentinel"
        target.write_bytes(b"Fictional untouched bytes")
        for name in ("moves.sqlite3-journal", "operation.lock", "moves.sqlite3"):
            path = self.state / name
            if path.exists():
                path.unlink()
            self.symlink(path, target)
            with self.subTest(name=name), self.assertRaises(ERRORS):
                if name == "operation.lock":
                    self.engine().move(self.source, self.destination)
                else:
                    Journal(self.state).initialize()
            self.assertEqual(target.read_bytes(), b"Fictional untouched bytes")
            path.unlink()
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_wal_and_shared_memory_sidecars_are_rejected_without_mutation(self):
        journal = Journal(self.state)
        journal.initialize()
        for name in ("moves.sqlite3-wal", "moves.sqlite3-shm"):
            path = self.state / name
            path.write_bytes(b"Fictional sidecar sentinel")
            with self.subTest(name=name), self.assertRaises(ERRORS):
                Journal(self.state).initialize()
            self.assertEqual(path.read_bytes(), b"Fictional sidecar sentinel")
            path.unlink()

    def test_named_stream_journal_and_lock_are_rejected_without_mutation(self):
        journal = Journal(self.state)
        journal.initialize()
        payload = self.ads(journal.database_path)
        before = journal.database_path.read_bytes()
        with self.assertRaises(ERRORS):
            Journal(self.state).initialize()
        self.assertEqual(journal.database_path.read_bytes(), before)
        self.assertEqual(read_stream(journal.database_path), payload)

    def test_named_stream_operation_lock_is_refused_before_mutation(self):
        journal = Journal(self.state)
        journal.initialize()
        lock = self.state / "operation.lock"
        lock.write_bytes(b"\0")
        payload = self.ads(lock)
        before = lock.read_bytes()
        with self.assertRaises(ERRORS):
            self.engine().move(self.source, self.destination)
        self.assertEqual(lock.read_bytes(), before)
        self.assertEqual(read_stream(lock), payload)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_named_stream_rollback_journal_is_refused_before_sqlite_open(self):
        journal = Journal(self.state)
        journal.initialize()
        rollback = self.state / "moves.sqlite3-journal"
        rollback.write_bytes(b"Fictional rollback bytes")
        payload = self.ads(rollback)
        before = journal.database_path.read_bytes()
        with (
            patch(
                "safe_file_mover.journal.sqlite3.connect",
                side_effect=AssertionError("NO_SQLITE_OPEN"),
            ),
            self.assertRaises(ERRORS),
        ):
            Journal(self.state).initialize()
        self.assertEqual(journal.database_path.read_bytes(), before)
        self.assertEqual(rollback.read_bytes(), b"Fictional rollback bytes")
        self.assertEqual(read_stream(rollback), payload)

    def test_wal_header_without_sidecars_is_refused_before_sqlite_open(self):
        journal = Journal(self.state)
        journal.initialize()
        original = journal.database_path.read_bytes()
        self.assertGreater(len(original), 20)
        wal_marked = original[:18] + b"\x02\x02" + original[20:]
        journal.database_path.write_bytes(wal_marked)
        with (
            patch(
                "safe_file_mover.journal.sqlite3.connect",
                side_effect=AssertionError("NO_SQLITE_OPEN"),
            ),
            self.assertRaises(ERRORS),
        ):
            Journal(self.state).initialize()
        self.assertEqual(journal.database_path.read_bytes(), wal_marked)
        self.assertFalse((self.state / "moves.sqlite3-wal").exists())
        self.assertFalse((self.state / "moves.sqlite3-shm").exists())

    def test_even_empty_wal_and_shared_memory_files_are_refused_before_sqlite(self):
        journal = Journal(self.state)
        journal.initialize()
        for name in ("moves.sqlite3-wal", "moves.sqlite3-shm"):
            sidecar = self.state / name
            sidecar.write_bytes(b"")
            before = journal.database_path.read_bytes()
            with (
                patch(
                    "safe_file_mover.journal.sqlite3.connect",
                    side_effect=AssertionError("NO_SQLITE_OPEN"),
                ),
                self.subTest(name=name),
                self.assertRaises(ERRORS),
            ):
                Journal(self.state).initialize()
            self.assertEqual(sidecar.read_bytes(), b"")
            self.assertEqual(journal.database_path.read_bytes(), before)
            sidecar.unlink()

    def test_raw_ambiguous_state_paths_are_refused_before_creation(self):
        for value in (
            str(self.state) + ".",
            str(self.state) + " ",
            str(self.state) + ":" + ADS,
            "C:fictional",
            str(self.root / "NUL"),
            str(self.root / "sub" / ".." / "fictional-state"),
        ):
            with self.subTest(value=value), self.assertRaises(ERRORS):
                Journal(value).initialize()
        self.assertFalse(self.state.exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_raw_ambiguous_paths_are_refused_without_creating_state(self):
        for value in (
            str(self.source) + ".",
            str(self.source) + " ",
            str(self.source) + ":" + ADS,
            "C:fictional",
            str(self.root / "NUL.txt"),
            str(self.root / "a" / ".." / self.source.name),
        ):
            with self.subTest(value=value), self.assertRaises(ERRORS):
                self.engine().plan(value, self.destination)
        self.assertFalse(self.state.exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_unsafe_windows_relative_manifest_paths_are_refused(self):
        for value in (
            "../outside",
            "..\\outside",
            "folder\\..\\outside",
            "folder/payload:metadata",
            "C:outside",
            "/outside",
        ):
            with self.subTest(value=value), self.assertRaises(core.VerificationError):
                core._relative_path(value)

    def test_junction_attached_after_plan_is_refused_on_new_move(self):
        folder = self.root / "fictional-source-parent"
        folder.mkdir()
        source = folder / "payload.txt"
        source.write_bytes(self.original)
        self.engine().plan(source, self.destination)
        moved = self.root / "fictional-original-parent"
        folder.rename(moved)
        self.junction(folder, moved)
        with self.assertRaises(ERRORS):
            self.engine().move(source, self.destination)
        self.assertEqual((moved / "payload.txt").read_bytes(), self.original)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_operation_lock_blocks_a_second_process_then_releases(self):
        engine = self.engine()
        program = "from pathlib import Path;from safe_file_mover.core import SafeMoveEngine,SafeMoveError;import sys;engine=SafeMoveEngine(Path(sys.argv[1]));\ntry:\n with engine._operation_guard(): pass\nexcept (SafeMoveError,OSError,ValueError): raise SystemExit(7)\n"
        with engine._operation_guard():
            child = subprocess.run(
                [sys.executable, "-B", "-c", program, str(self.state)],
                cwd=HERE,
                capture_output=True,
                timeout=15,
            )
        self.assertEqual(child.returncode, 7)
        after = subprocess.run(
            [sys.executable, "-B", "-c", program, str(self.state)],
            cwd=HERE,
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(after.returncode, 0)

    def test_cli_plan_move_list_history_restore_use_only_private_fixture_state(self):
        unicode_source = self.root / "fictional-Ω-雪.txt"
        self.source.rename(unicode_source)
        self.source = unicode_source
        prefix = [
            sys.executable,
            "-B",
            "-m",
            "safe_file_mover",
            "--state-dir",
            str(self.state),
        ]

        def run(*args):
            return subprocess.run(
                prefix + list(args),
                cwd=HERE,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )

        plan = run("plan", str(self.source), str(self.destination))
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertFalse(self.state.exists())
        moved = run("move", str(self.source), str(self.destination))
        self.assertEqual(moved.returncode, 0, moved.stderr)
        records = Journal(self.state).list()
        self.assertEqual(len(records), 1)
        operation_id = records[0].operation_id
        self.assertEqual(run("list").returncode, 0)
        self.assertEqual(run("history", operation_id).returncode, 0)
        self.assertEqual(run("restore", operation_id).returncode, 0)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_all_fixture_file_operations_remain_local_without_network_calls(self):
        with (
            patch.object(socket, "socket", side_effect=AssertionError("NO_NETWORK")),
            patch.object(
                socket, "create_connection", side_effect=AssertionError("NO_NETWORK")
            ),
        ):
            operation = self.engine().move(self.source, self.destination)
            self.assertEqual(operation.destination.read_bytes(), self.original)
            self.engine().purge_backup(operation.operation_id)
        self.assertEqual(operation.destination.read_bytes(), self.original)

    def test_forward_device_prefixes_and_unsafe_unc_anchors_stop_before_native_open(
        self,
    ):
        slash = "\\"
        unc = slash * 2
        values = ["//?/" + self.source.as_posix(), "//./" + self.source.as_posix()]
        for server, share in (
            ("fictional.", "share"),
            ("NUL", "share"),
            ("fictional", "share "),
            ("fictional", "share:metadata"),
            ("fictional\x01", "share"),
        ):
            values.append(unc + server + slash + share + slash + "payload")
        with (
            patch.object(
                win.Native, "open", side_effect=AssertionError("NO_NATIVE_OPEN")
            ),
            patch.object(socket, "socket", side_effect=AssertionError("NO_NETWORK")),
            patch.object(
                socket, "create_connection", side_effect=AssertionError("NO_NETWORK")
            ),
        ):
            for value in values:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    win.checked_path(value, allow_remote=True)
        self.assertFalse(self.state.exists())

    def test_native_volume_keys_detect_synthetic_cross_drive_ancestry(self):
        child = Path("X:" + os.sep) / "fictional" / "child"
        parent = Path("Y:" + os.sep) / "fictional"
        native_parent = "\\Device\\HarddiskVolume77\\fictional"
        cases = (
            (native_parent + "\\child", native_parent, True),
            (native_parent, native_parent, True),
            (native_parent + "-other\\child", native_parent, False),
            ("\\Device\\HarddiskVolume78\\fictional\\child", native_parent, False),
        )
        for child_key, parent_key, expected in cases:
            with (
                self.subTest(child_key=child_key, parent_key=parent_key),
                patch.object(
                    win, "path_key", side_effect=[child_key, parent_key]
                ) as keys,
            ):
                self.assertIs(core._is_relative_to(child, parent), expected)
                self.assertEqual(keys.call_args_list[0].args, (child,))
                self.assertEqual(keys.call_args_list[1].args, (parent,))

    def test_native_volume_key_failure_refuses_unverifiable_topology(self):
        with (
            patch.object(
                win, "path_key", side_effect=ValueError("FICTIONAL_METADATA_FAILURE")
            ),
            self.assertRaises(core.InvalidMoveError),
        ):
            core._is_relative_to(self.source, self.root)

    def test_stream_hash_growth_stops_before_hashing_beyond_recorded_size(self):
        payload = self.ads(self.source, b"Fictional stream exceeds recorded size")
        observed = bytearray()
        digest = hashlib.sha256()

        class RecordingDigest:
            def update(self, data):
                observed.extend(data)
                digest.update(data)

            def hexdigest(self):
                return digest.hexdigest()

        with (
            patch.object(core.hashlib, "sha256", return_value=RecordingDigest()),
            self.assertRaises(core.SourceChangedError),
        ):
            core._hash_stable_named_stream(self.source, ":" + ADS + ":$DATA", 3, 2)
        self.assertEqual(bytes(observed), payload[:2])
        self.assertLessEqual(len(observed), 3)
        self.assertEqual(read_stream(self.source), payload)

    def test_stream_copy_growth_never_writes_beyond_recorded_size(self):
        payload = self.ads(self.source, b"Fictional stream exceeds recorded size")
        entry = core.build_manifest(self.source, chunk_size=2).entries[0]
        bounded_stream = core.NamedStream(
            ":" + ADS + ":$DATA", 3, hashlib.sha256(payload[:3]).hexdigest()
        )
        bounded_entry = replace(entry, named_streams=(bounded_stream,))
        target = self.root / "fictional-stream-growth-target.bin"
        target.write_bytes(b"Fictional staged primary")
        engine = core.SafeMoveEngine(self.state, chunk_size=2)
        with (
            patch.object(
                core,
                "_windows_named_stream_info",
                return_value=((bounded_stream.name, 3),),
            ),
            self.assertRaises(core.SourceChangedError),
        ):
            engine._copy_named_streams(self.source, target, bounded_entry)
        copied = read_stream(target)
        self.assertEqual(copied, payload[:2])
        self.assertLessEqual(len(copied), 3)
        self.assertEqual(read_stream(self.source), payload)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_staging_mutation_at_destination_commit_keeps_source_and_no_destination(
        self,
    ):
        def mutate(phase, path):
            if phase == "before_destination_commit":
                path.write_bytes(b"Fictional late staged mutation")

        with self.assertRaises(core.VerificationError):
            self.engine(fault_hook=mutate).move(self.source, self.destination)
        record = self.engine().journal.list()[0]
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse((self.destination / self.source.name).exists())
        self.assertTrue(Path(record.staging).exists())
        self.assertFalse(Path(record.backup).exists())

    def test_destination_mutation_at_source_tombstone_keeps_original_source_path(self):
        target = self.destination / self.source.name

        def mutate(phase, _path):
            if phase == "before_source_tombstone":
                target.write_bytes(b"Fictional late committed mutation")

        with self.assertRaises(core.VerificationError):
            self.engine(fault_hook=mutate).move(self.source, self.destination)
        record = self.engine().journal.list()[0]
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(target.read_bytes(), b"Fictional late committed mutation")
        self.assertFalse(Path(record.backup).exists())

    def test_dangling_directory_symlink_is_recreated_without_target_probe(self):
        target = self.root / "fictional-missing-directory"
        link = self.root / "fictional-directory-link"
        self.symlink(link, target.name, directory=True)
        original_is_dir, original_open = Path.is_dir, builtins.open

        def checked_is_dir(path):
            if path in (link, target):
                raise AssertionError("NO_SYMLINK_TARGET_PROBE")
            return original_is_dir(path)

        def checked_open(file, *args, **kwargs):
            if isinstance(file, (str, os.PathLike)) and any(
                str(path) in os.fspath(file) for path in (link, target)
            ):
                raise AssertionError("NO_SYMLINK_TARGET_OPEN")
            return original_open(file, *args, **kwargs)

        with (
            patch.object(Path, "is_dir", new=checked_is_dir),
            patch.object(builtins, "open", new=checked_open),
        ):
            operation = self.engine().move(link, self.destination)
        self.assertTrue(operation.destination.is_symlink())
        self.assertTrue(operation.recovery_copy.is_symlink())
        self.assertTrue(operation.destination.lstat().st_file_attributes & 0x10)
        self.assertTrue(operation.recovery_copy.lstat().st_file_attributes & 0x10)
        self.assertEqual(os.readlink(operation.destination), target.name)
        self.assertFalse(target.exists())

    def reservation_actions_refuse_unchanged(self, reservation, expected):
        target = self.destination / self.source.name
        record = SimpleNamespace(
            destination=str(target), reservation=str(reservation), operation_id="a" * 32
        )
        engine = self.engine()
        for action in (
            lambda: engine._reservation_blocks(target),
            lambda: engine._create_reservation(record),
            lambda: engine._clear_releasable_reservation(reservation),
            lambda: engine._release_reservation(record),
        ):
            with self.assertRaises(core.CollisionError):
                action()
            self.assertEqual(reservation.read_bytes(), expected)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse(target.exists())
        self.assertFalse(self.state.exists())

    def test_reservation_named_stream_is_refused_without_replacing_original(self):
        reservation = core._reservation_path(self.destination / self.source.name)
        content = b"Fictional reservation sentinel"
        reservation.write_bytes(content)
        payload = self.ads(reservation)
        self.reservation_actions_refuse_unchanged(reservation, content)
        self.assertEqual(read_stream(reservation), payload)

    def test_reservation_hardlink_is_refused_without_replacing_either_name(self):
        reservation = core._reservation_path(self.destination / self.source.name)
        content = b"Fictional reservation sentinel"
        reservation.write_bytes(content)
        alias = self.root / "fictional-reservation-alias"
        self.hardlink(alias, reservation)
        self.reservation_actions_refuse_unchanged(reservation, content)
        self.assertEqual(alias.read_bytes(), content)

    def test_unsupported_stream_enumeration_api_fails_closed(self):
        invalid_handle = ctypes.c_void_p(-1).value
        for code in (1, 50, 87):
            dll = SimpleNamespace(
                FindFirstStreamW=Mock(return_value=invalid_handle),
                FindNextStreamW=Mock(side_effect=AssertionError("NO_ENUMERATION")),
                FindClose=Mock(side_effect=AssertionError("NO_INVALID_CLOSE")),
            )
            with (
                self.subTest(code=code),
                patch.object(ctypes, "WinDLL", return_value=dll),
                patch.object(ctypes, "get_last_error", return_value=code),
                self.assertRaises(core.UnsupportedSourceError),
            ):
                core._windows_named_stream_info(self.source)
            dll.FindFirstStreamW.assert_called_once()
            dll.FindNextStreamW.assert_not_called()
            dll.FindClose.assert_not_called()

    def test_stream_enumeration_close_failure_is_not_reported_as_success(self):
        def first(_path, _kind, pointer, _flags):
            pointer._obj.stream_name = "::$DATA"
            pointer._obj.stream_size = 0
            return 1234

        dll = SimpleNamespace(
            FindFirstStreamW=Mock(side_effect=first),
            FindNextStreamW=Mock(return_value=0),
            FindClose=Mock(return_value=0),
        )
        with (
            patch.object(ctypes, "WinDLL", return_value=dll),
            patch.object(ctypes, "get_last_error", return_value=38),
            self.assertRaises(core.UnsupportedSourceError),
        ):
            core._windows_named_stream_info(self.source)
        dll.FindClose.assert_called_once_with(1234)

    def test_failed_windows_journal_setup_closes_created_connection(self):
        journal = Journal(self.state)

        class FailedConnection:
            def __init__(self, fail_on_assignment):
                self.fail_on_assignment = fail_on_assignment
                self.close_count = 0

            @property
            def row_factory(self):
                return None

            @row_factory.setter
            def row_factory(self, _value):
                if self.fail_on_assignment:
                    raise RuntimeError("FICTIONAL_ROW_FACTORY_FAILURE")

            def execute(self, _sql):
                raise RuntimeError("FICTIONAL_PRAGMA_FAILURE")

            def close(self):
                self.close_count += 1

        for assignment_failure in (False, True):
            connection = FailedConnection(assignment_failure)
            with (
                self.subTest(assignment_failure=assignment_failure),
                patch(
                    "safe_file_mover.journal.sqlite3.connect", return_value=connection
                ),
                self.assertRaises(RuntimeError),
            ):
                journal._connect()
            self.assertEqual(connection.close_count, 1)
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
