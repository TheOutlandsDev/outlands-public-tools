from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from safe_file_mover.core import (
    CollisionError,
    ConflictPolicy,
    InvalidMoveError,
    OperationStateError,
    SafeMoveEngine,
    SourceChangedError,
    UnsupportedSourceError,
    VerificationError,
)


class SafeMoveEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.destination_directory = self.root / "destination"
        self.destination_directory.mkdir()
        self.state_directory = self.root / "state"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def engine(self, **kwargs: object) -> SafeMoveEngine:
        return SafeMoveEngine(self.state_directory, chunk_size=7, **kwargs)

    def test_file_move_retains_then_purges_verified_recovery_copy(self) -> None:
        source = self.root / "important data.bin"
        payload = bytes(range(256)) * 4
        source.write_bytes(payload)

        operation = self.engine().move(source, self.destination_directory)

        self.assertEqual(operation.status, "backup_retained")
        self.assertFalse(os.path.lexists(source))
        self.assertEqual(operation.destination.read_bytes(), payload)
        self.assertEqual(operation.recovery_copy.read_bytes(), payload)

        completed = self.engine().purge_backup(operation.operation_id)
        self.assertEqual(completed.status, "complete")
        self.assertFalse(os.path.lexists(operation.recovery_copy))
        self.assertEqual(operation.destination.read_bytes(), payload)

    def test_move_can_purge_recovery_copy_after_commit(self) -> None:
        source = self.root / "one-shot.txt"
        source.write_text("verified", encoding="utf-8")

        operation = self.engine().move(
            source, self.destination_directory, keep_backup=False
        )

        self.assertEqual(operation.status, "complete")
        self.assertFalse(os.path.lexists(source))
        self.assertFalse(os.path.lexists(operation.recovery_copy))
        self.assertEqual(operation.destination.read_text(encoding="utf-8"), "verified")

    def test_recovery_finishes_interrupted_opt_in_purge(self) -> None:
        source = self.root / "purge-crash.txt"
        source.write_text("still verified", encoding="utf-8")
        triggered = False

        def crash(phase: str, path: Path | None) -> None:
            nonlocal triggered
            if phase == "after_backup_purge" and not triggered:
                triggered = True
                raise RuntimeError("simulated failure after recovery-copy deletion")

        with self.assertRaises(RuntimeError):
            self.engine(fault_hook=crash).move(
                source,
                self.destination_directory,
                keep_backup=False,
            )

        record = self.engine().journal.list()[0]
        self.assertEqual(record.status, "purging")
        self.assertFalse(Path(record.backup).exists())
        recovered = self.engine().recover(record.operation_id)

        self.assertEqual(recovered.status, "complete")
        self.assertEqual(recovered.destination.read_text(encoding="utf-8"), "still verified")

    def test_recovery_resumes_partially_deleted_recovery_directory(self) -> None:
        source = self.root / "purge-tree"
        source.mkdir()
        (source / "first.txt").write_text("first", encoding="utf-8")
        (source / "second.txt").write_text("second", encoding="utf-8")
        operation = self.engine().move(source, self.destination_directory)

        def interrupt_delete(phase: str, path: Path | None) -> None:
            if phase == "before_purge_delete" and path is not None:
                (path / "first.txt").unlink()
                raise RuntimeError("simulated interruption during tree deletion")

        with self.assertRaises(RuntimeError):
            self.engine(fault_hook=interrupt_delete).purge_backup(
                operation.operation_id
            )

        record = self.engine().journal.get(operation.operation_id)
        purging = Path(record.backup + ".purging")
        self.assertEqual(record.status, "purging")
        self.assertTrue(purging.exists())
        self.assertFalse((purging / "first.txt").exists())
        self.assertTrue((purging / "second.txt").exists())

        recovered = self.engine().recover(operation.operation_id)

        self.assertEqual(recovered.status, "complete")
        self.assertFalse(purging.exists())
        self.assertTrue(operation.destination.exists())

    def test_purge_rechecks_destination_after_final_failpoint(self) -> None:
        source = self.root / "purge-race.txt"
        source.write_text("baseline", encoding="utf-8")
        operation = self.engine().move(source, self.destination_directory)

        def corrupt_destination(phase: str, path: Path | None) -> None:
            if phase == "before_backup_purge":
                operation.destination.write_text("changed", encoding="utf-8")

        with self.assertRaises(VerificationError):
            self.engine(fault_hook=corrupt_destination).purge_backup(
                operation.operation_id
            )

        self.assertTrue(operation.recovery_copy.exists())
        self.assertEqual(
            operation.recovery_copy.read_text(encoding="utf-8"), "baseline"
        )
        self.assertEqual(
            self.engine().journal.get(operation.operation_id).status,
            "backup_retained",
        )

    def test_nested_directory_move_preserves_content_and_empty_directories(self) -> None:
        source = self.root / "Project Ω"
        (source / "empty").mkdir(parents=True)
        (source / "nested" / "deeper").mkdir(parents=True)
        (source / "nested" / "notes.txt").write_text("hello\n", encoding="utf-8")
        (source / ".hidden").write_bytes(b"\x00\x01\x02")

        operation = self.engine().move(source, self.destination_directory)

        target = operation.destination
        self.assertTrue((target / "empty").is_dir())
        self.assertTrue((target / "nested" / "deeper").is_dir())
        self.assertEqual(
            (target / "nested" / "notes.txt").read_text(encoding="utf-8"),
            "hello\n",
        )
        self.assertEqual((target / ".hidden").read_bytes(), b"\x00\x01\x02")
        self.assertTrue(operation.recovery_copy.is_dir())

    def test_plan_is_read_only_and_reports_exact_target(self) -> None:
        source = self.root / "preview.txt"
        source.write_bytes(b"abc")

        plan = self.engine().plan(
            source, self.destination_directory, new_name="renamed.txt"
        )

        self.assertEqual(
            plan.destination,
            self.destination_directory.resolve() / "renamed.txt",
        )
        self.assertEqual(plan.manifest.total_bytes, 3)
        self.assertFalse(self.state_directory.exists())
        self.assertTrue(source.exists())

    def test_default_collision_never_changes_either_file(self) -> None:
        source = self.root / "same.txt"
        target = self.destination_directory / source.name
        source.write_text("source", encoding="utf-8")
        target.write_text("existing", encoding="utf-8")

        with self.assertRaises(CollisionError):
            self.engine().move(source, self.destination_directory)

        self.assertEqual(source.read_text(encoding="utf-8"), "source")
        self.assertEqual(target.read_text(encoding="utf-8"), "existing")

    def test_operation_lock_rejects_a_second_engine_writer(self) -> None:
        first = self.engine()
        second = self.engine()

        with first._operation_guard():
            with self.assertRaises(OperationStateError):
                with second._operation_guard():
                    self.fail("A second writer acquired the operation lock")

    def test_stale_stable_operation_reservation_is_reclaimed(self) -> None:
        first_source = self.root / "first" / "reused.txt"
        first_source.parent.mkdir()
        first_source.write_text("first", encoding="utf-8")
        first_operation = self.engine().move(
            first_source, self.destination_directory
        )
        first_record = self.engine().journal.get(first_operation.operation_id)

        first_operation.destination.unlink()
        reservation = Path(first_record.reservation)
        reservation.write_text(first_operation.operation_id + "\n", encoding="ascii")
        second_source = self.root / "second" / "reused.txt"
        second_source.parent.mkdir()
        second_source.write_text("second", encoding="utf-8")

        second_operation = self.engine().move(
            second_source, self.destination_directory
        )

        self.assertEqual(
            second_operation.destination.read_text(encoding="utf-8"), "second"
        )
        self.assertFalse(reservation.exists())

    def test_rename_collision_policy_keeps_existing_target(self) -> None:
        source = self.root / "report.txt"
        source.write_text("new report", encoding="utf-8")
        (self.destination_directory / "report.txt").write_text(
            "old report", encoding="utf-8"
        )
        (self.destination_directory / "report (1).txt").write_text(
            "older report", encoding="utf-8"
        )

        operation = self.engine().move(
            source,
            self.destination_directory,
            conflict_policy=ConflictPolicy.RENAME,
        )

        self.assertEqual(operation.destination.name, "report (2).txt")
        self.assertEqual(operation.destination.read_text(encoding="utf-8"), "new report")
        self.assertEqual(
            (self.destination_directory / "report.txt").read_text(encoding="utf-8"),
            "old report",
        )

    def test_destination_inside_source_is_rejected_before_writes(self) -> None:
        source = self.root / "tree"
        destination_inside = source / "output"
        destination_inside.mkdir(parents=True)
        (source / "data.txt").write_text("data", encoding="utf-8")

        with self.assertRaises(InvalidMoveError):
            self.engine().move(source, destination_inside)

        self.assertTrue((source / "data.txt").exists())
        self.assertFalse(self.state_directory.exists())

    def test_corrupt_staging_never_commits_or_changes_source(self) -> None:
        source = self.root / "valuable.bin"
        source.write_bytes(b"good data")

        def corrupt(phase: str, path: Path | None) -> None:
            if phase == "before_stage_verification" and path is not None:
                path.write_bytes(b"bad data")

        with self.assertRaises(VerificationError):
            self.engine(fault_hook=corrupt).move(source, self.destination_directory)

        self.assertEqual(source.read_bytes(), b"good data")
        self.assertFalse((self.destination_directory / source.name).exists())
        record = self.engine().journal.list()[0]
        self.assertEqual(record.status, "copying")
        self.assertIsNotNone(record.last_error)

    def test_source_mutation_after_staging_is_detected_before_commit(self) -> None:
        source = self.root / "live.txt"
        source.write_text("first", encoding="utf-8")

        def mutate(phase: str, path: Path | None) -> None:
            if phase == "after_stage_verification":
                source.write_text("second", encoding="utf-8")

        with self.assertRaises(SourceChangedError):
            self.engine(fault_hook=mutate).move(source, self.destination_directory)

        self.assertEqual(source.read_text(encoding="utf-8"), "second")
        self.assertFalse((self.destination_directory / source.name).exists())

    def test_concurrent_destination_creation_is_never_overwritten(self) -> None:
        source = self.root / "race.txt"
        source.write_text("source", encoding="utf-8")
        target = self.destination_directory / source.name

        def intrude(phase: str, path: Path | None) -> None:
            if phase == "before_destination_commit":
                target.write_text("intruder", encoding="utf-8")

        with self.assertRaises(CollisionError):
            self.engine(fault_hook=intrude).move(source, self.destination_directory)

        self.assertEqual(source.read_text(encoding="utf-8"), "source")
        self.assertEqual(target.read_text(encoding="utf-8"), "intruder")

    def test_recovery_finishes_crash_after_destination_commit(self) -> None:
        source = self.root / "commit-crash.txt"
        source.write_text("survives", encoding="utf-8")
        triggered = False

        def crash(phase: str, path: Path | None) -> None:
            nonlocal triggered
            if phase == "after_destination_commit" and not triggered:
                triggered = True
                raise RuntimeError("simulated process failure")

        with self.assertRaises(RuntimeError):
            self.engine(fault_hook=crash).move(source, self.destination_directory)

        record = self.engine().journal.list()[0]
        self.assertEqual(record.status, "verified")
        self.assertTrue(source.exists())
        self.assertEqual(Path(record.destination).read_text(encoding="utf-8"), "survives")

        recovered = self.engine().recover(record.operation_id)

        self.assertEqual(recovered.status, "backup_retained")
        self.assertFalse(source.exists())
        self.assertTrue(recovered.recovery_copy.exists())

    def test_recovery_finishes_crash_after_source_tombstone(self) -> None:
        source = self.root / "rename-crash.txt"
        source.write_text("two copies", encoding="utf-8")
        triggered = False

        def crash(phase: str, path: Path | None) -> None:
            nonlocal triggered
            if phase == "after_source_tombstone" and not triggered:
                triggered = True
                raise RuntimeError("simulated process failure")

        with self.assertRaises(RuntimeError):
            self.engine(fault_hook=crash).move(source, self.destination_directory)

        record = self.engine().journal.list()[0]
        self.assertEqual(record.status, "destination_committed")
        self.assertFalse(source.exists())
        self.assertTrue(Path(record.backup).exists())

        recovered = self.engine().recover(record.operation_id)

        self.assertEqual(recovered.status, "backup_retained")
        self.assertEqual(recovered.recovery_copy.read_text(encoding="utf-8"), "two copies")

    def test_recover_all_continues_after_one_changed_source(self) -> None:
        first_source = self.root / "first-pending.txt"
        second_source = self.root / "second-pending.txt"
        first_source.write_text("first", encoding="utf-8")
        second_source.write_text("second", encoding="utf-8")

        def pause_after_copy(phase: str, path: Path | None) -> None:
            if phase == "after_copy":
                raise RuntimeError("leave operation pending")

        for source in (first_source, second_source):
            with self.assertRaises(RuntimeError):
                self.engine(fault_hook=pause_after_copy).move(
                    source, self.destination_directory
                )
        first_source.write_text("changed after planning", encoding="utf-8")

        results = self.engine().recover_all()
        by_source = {operation.source.name: operation for operation in results}

        self.assertEqual(by_source[first_source.name].status, "copying")
        self.assertIsNotNone(by_source[first_source.name].last_error)
        self.assertEqual(by_source[second_source.name].status, "backup_retained")
        self.assertTrue(by_source[second_source.name].destination.exists())

    def test_recovery_finishes_interrupted_file_hardlink_tombstone(self) -> None:
        source = self.root / "hardlink-crash.txt"
        source.write_text("one inode", encoding="utf-8")
        if os.name == "nt":
            probe = self.root / "fictional-hardlink-feature-probe"
            try:
                os.link(source, probe)
            except (OSError, NotImplementedError):
                if os.environ.get("OUTLANDS_MOVER_REQUIRE_NATIVE_FEATURES") == "1":
                    self.fail("Native hardlink fixture unavailable")
                self.skipTest("Native hardlink fixture unavailable")
            else:
                probe.unlink()
        real_link = os.link
        link_calls = 0
        rename_calls = 0

        def force_hardlink_for_tombstone(
            existing: Path, new: Path
        ) -> bool:
            nonlocal rename_calls
            rename_calls += 1
            if rename_calls == 1:
                os.rename(existing, new)
                return True
            return False

        def crash_after_link(
            existing: os.PathLike[str] | str,
            new: os.PathLike[str] | str,
            *,
            src_dir_fd: int | None = None,
            dst_dir_fd: int | None = None,
            follow_symlinks: bool = True,
        ) -> None:
            nonlocal link_calls
            link_calls += 1
            real_link(
                existing,
                new,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd,
                follow_symlinks=follow_symlinks,
            )
            if link_calls == 1:
                raise RuntimeError("simulated kill after link, before unlink")

        with mock.patch(
            "safe_file_mover.core._atomic_rename_no_replace",
            side_effect=force_hardlink_for_tombstone,
        ), mock.patch("safe_file_mover.core.os.link", side_effect=crash_after_link):
            with self.assertRaises(RuntimeError):
                self.engine().move(source, self.destination_directory)

        record = self.engine().journal.list()[0]
        self.assertEqual(record.status, "destination_committed")
        self.assertTrue(source.exists())
        self.assertTrue(Path(record.backup).exists())
        self.assertTrue(os.path.samefile(source, record.backup))

        recovered = self.engine().recover(record.operation_id)

        self.assertEqual(recovered.status, "backup_retained")
        self.assertFalse(source.exists())
        self.assertEqual(recovered.recovery_copy.read_text(encoding="utf-8"), "one inode")

    def test_abandon_discards_only_managed_staging_and_preserves_source(self) -> None:
        source = self.root / "cancel.txt"
        source.write_text("keep me", encoding="utf-8")

        def stop(phase: str, path: Path | None) -> None:
            if phase == "after_copy":
                raise RuntimeError("stop after copy")

        with self.assertRaises(RuntimeError):
            self.engine(fault_hook=stop).move(source, self.destination_directory)

        record = self.engine().journal.list()[0]
        self.assertTrue(Path(record.staging).exists())
        abandoned = self.engine().abandon(record.operation_id)

        self.assertEqual(abandoned.status, "abandoned")
        self.assertTrue(source.exists())
        self.assertFalse(Path(record.staging).exists())

    def test_restore_returns_recovery_copy_to_original_path(self) -> None:
        source = self.root / "restore.txt"
        source.write_text("restore me", encoding="utf-8")
        operation = self.engine().move(source, self.destination_directory)

        restored = self.engine().restore_backup(operation.operation_id)

        self.assertEqual(restored.status, "restored")
        self.assertEqual(source.read_text(encoding="utf-8"), "restore me")
        self.assertFalse(operation.recovery_copy.exists())
        self.assertEqual(operation.destination.read_text(encoding="utf-8"), "restore me")

    def test_recovery_finishes_restore_after_filesystem_commit(self) -> None:
        source = self.root / "restore-crash.txt"
        source.write_text("restorable", encoding="utf-8")
        operation = self.engine().move(source, self.destination_directory)

        def crash(phase: str, path: Path | None) -> None:
            if phase == "after_backup_restore":
                raise RuntimeError("simulated crash after restore rename")

        with self.assertRaises(RuntimeError):
            self.engine(fault_hook=crash).restore_backup(operation.operation_id)

        record = self.engine().journal.get(operation.operation_id)
        self.assertEqual(record.status, "restoring")
        self.assertTrue(source.exists())
        self.assertFalse(operation.recovery_copy.exists())

        recovered = self.engine().recover(operation.operation_id)

        self.assertEqual(recovered.status, "restored")
        self.assertEqual(source.read_text(encoding="utf-8"), "restorable")

    @unittest.skipUnless(os.name == "nt", "Windows filename rules")
    def test_windows_unsafe_destination_names_are_rejected(self) -> None:
        source = self.root / "source.txt"
        source.write_text("data", encoding="utf-8")
        for unsafe_name in ("trailing.", "trailing ", "stream:name", "wild?card"):
            with self.subTest(name=unsafe_name):
                with self.assertRaises(InvalidMoveError):
                    self.engine().plan(
                        source,
                        self.destination_directory,
                        new_name=unsafe_name,
                    )

    @unittest.skipIf(os.name == "nt", "POSIX extended attributes")
    def test_posix_extended_attribute_is_rejected(self) -> None:
        if not hasattr(os, "setxattr"):
            self.skipTest("Extended attributes are unavailable")
        source = self.root / "xattrs.txt"
        source.write_text("primary", encoding="utf-8")
        try:
            os.setxattr(source, "user.safe-move-test", b"metadata")
        except OSError as error:
            self.skipTest(f"Filesystem does not support test xattrs: {error}")

        with self.assertRaises(UnsupportedSourceError):
            self.engine().plan(source, self.destination_directory)

    def test_symlink_is_copied_as_link_when_platform_allows_it(self) -> None:
        target = self.root / "link-target.txt"
        target.write_text("target", encoding="utf-8")
        source = self.root / "shortcut"
        try:
            source.symlink_to(target.name)
        except OSError as error:
            self.skipTest(f"Creating symlinks is unavailable: {error}")

        operation = self.engine().move(source, self.destination_directory)

        self.assertTrue(operation.destination.is_symlink())
        self.assertEqual(os.readlink(operation.destination), target.name)
        self.assertTrue(operation.recovery_copy.is_symlink())
        self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
