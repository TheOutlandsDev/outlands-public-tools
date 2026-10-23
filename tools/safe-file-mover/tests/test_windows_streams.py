from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from safe_file_mover.core import (
    SafeMoveEngine,
    SourceChangedError,
    VerificationError,
)


STREAM_NAME = "demo.metadata"


def _stream_path(path: Path, name: str = STREAM_NAME) -> str:
    return f"{path}:{name}"


def _write_stream(path: Path, payload: bytes, name: str = STREAM_NAME) -> None:
    with open(_stream_path(path, name), "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _read_stream(path: Path, name: str = STREAM_NAME) -> bytes:
    with open(_stream_path(path, name), "rb") as stream:
        return stream.read()


def _mutate_stream_without_primary_stat_change(path: Path, payload: bytes) -> None:
    """Change only ADS bytes so a primary-file stat check cannot detect it."""
    before = path.stat(follow_symlinks=False)
    _write_stream(path, payload)
    os.utime(
        path,
        ns=(before.st_atime_ns, before.st_mtime_ns),
    )
    after = path.stat(follow_symlinks=False)
    if (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_mode,
    ) != (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_mode,
    ):
        raise AssertionError("Could not restore the primary-file snapshot metadata")


@unittest.skipUnless(os.name == "nt", "Windows named data streams")
class WindowsNamedStreamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.destination_directory = self.root / "destination"
        self.destination_directory.mkdir()
        self.state_directory = self.root / "state"

        probe = self.root / "stream-probe.txt"
        probe.write_bytes(b"probe")
        try:
            _write_stream(probe, b"named-stream-probe")
            if _read_stream(probe) != b"named-stream-probe":
                self.skipTest("Filesystem did not preserve the ADS probe bytes")
        except OSError as error:
            self.skipTest(f"Filesystem does not support named data streams: {error}")
        finally:
            try:
                probe.unlink()
            except FileNotFoundError:
                pass

    def engine(self, **kwargs: object) -> SafeMoveEngine:
        return SafeMoveEngine(self.state_directory, chunk_size=7, **kwargs)

    def create_streamed_file(
        self,
        path: Path,
        *,
        primary: bytes = b"primary program data",
        stream: bytes = b"endpoint policy\x00\xffpayload",
    ) -> tuple[bytes, bytes]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(primary)
        _write_stream(path, stream)
        return primary, stream

    def test_plan_records_named_stream_sha256(self) -> None:
        source = self.root / "manifest.json"
        primary, stream = self.create_streamed_file(source)

        plan = self.engine().plan(source, self.destination_directory)
        serialized_manifest = json.dumps(
            plan.manifest.to_dict(), ensure_ascii=False, sort_keys=True
        )

        self.assertIn(STREAM_NAME, serialized_manifest)
        self.assertIn(hashlib.sha256(stream).hexdigest(), serialized_manifest)
        self.assertIn(hashlib.sha256(primary).hexdigest(), serialized_manifest)

    def test_directory_move_preserves_named_stream_in_destination_and_recovery(self) -> None:
        source = self.root / "application-data"
        streamed_file = source / "nested" / "settings.json"
        primary, stream = self.create_streamed_file(streamed_file)
        (source / "empty").mkdir()

        operation = self.engine().move(source, self.destination_directory)

        destination_file = operation.destination / "nested" / "settings.json"
        recovery_file = operation.recovery_copy / "nested" / "settings.json"
        self.assertEqual(operation.status, "backup_retained")
        self.assertFalse(os.path.lexists(source))
        self.assertEqual(destination_file.read_bytes(), primary)
        self.assertEqual(recovery_file.read_bytes(), primary)
        self.assertEqual(_read_stream(destination_file), stream)
        self.assertEqual(_read_stream(recovery_file), stream)

    def test_interrupted_move_recovery_preserves_named_stream(self) -> None:
        source = self.root / "recover.dat"
        _, stream = self.create_streamed_file(source)
        triggered = False

        def crash_after_commit(phase: str, path: Path | None) -> None:
            nonlocal triggered
            if phase == "after_destination_commit" and not triggered:
                triggered = True
                raise RuntimeError("simulated interruption after destination commit")

        with self.assertRaises(RuntimeError):
            self.engine(fault_hook=crash_after_commit).move(
                source, self.destination_directory
            )

        record = self.engine().journal.list()[0]
        destination = Path(record.destination)
        self.assertTrue(source.exists())
        self.assertEqual(_read_stream(source), stream)
        self.assertEqual(_read_stream(destination), stream)

        recovered = self.engine().recover(record.operation_id)

        self.assertEqual(recovered.status, "backup_retained")
        self.assertFalse(source.exists())
        self.assertEqual(_read_stream(recovered.destination), stream)
        self.assertEqual(_read_stream(recovered.recovery_copy), stream)

    def test_restore_preserves_named_stream_at_both_paths(self) -> None:
        source = self.root / "restore.txt"
        primary, stream = self.create_streamed_file(source)
        operation = self.engine().move(source, self.destination_directory)

        restored = self.engine().restore_backup(operation.operation_id)

        self.assertEqual(restored.status, "restored")
        self.assertEqual(source.read_bytes(), primary)
        self.assertEqual(operation.destination.read_bytes(), primary)
        self.assertEqual(_read_stream(source), stream)
        self.assertEqual(_read_stream(operation.destination), stream)
        self.assertFalse(os.path.lexists(operation.recovery_copy))

    def test_purge_preserves_verified_destination_named_stream(self) -> None:
        source = self.root / "purge.txt"
        _, stream = self.create_streamed_file(source)
        operation = self.engine().move(source, self.destination_directory)

        completed = self.engine().purge_backup(operation.operation_id)

        self.assertEqual(completed.status, "complete")
        self.assertFalse(os.path.lexists(operation.recovery_copy))
        self.assertEqual(_read_stream(operation.destination), stream)

    def test_staged_named_stream_mutation_is_detected_by_content_verification(self) -> None:
        source = self.root / "staging-mutation.txt"
        _, stream = self.create_streamed_file(source)
        changed_stream = b"X" * len(stream)

        def corrupt_staging(phase: str, path: Path | None) -> None:
            if phase == "before_stage_verification" and path is not None:
                _mutate_stream_without_primary_stat_change(path, changed_stream)

        with self.assertRaises(VerificationError):
            self.engine(fault_hook=corrupt_staging).move(
                source, self.destination_directory
            )

        self.assertTrue(source.exists())
        self.assertEqual(_read_stream(source), stream)
        self.assertFalse((self.destination_directory / source.name).exists())

    def test_destination_named_stream_mutation_prevents_purge(self) -> None:
        source = self.root / "destination-mutation.txt"
        _, stream = self.create_streamed_file(source)
        operation = self.engine().move(source, self.destination_directory)
        _mutate_stream_without_primary_stat_change(
            operation.destination, b"Y" * len(stream)
        )

        with self.assertRaises(VerificationError):
            self.engine().purge_backup(operation.operation_id)

        self.assertTrue(operation.recovery_copy.exists())
        self.assertEqual(_read_stream(operation.recovery_copy), stream)

    def test_recovery_named_stream_mutation_prevents_restore(self) -> None:
        source = self.root / "recovery-mutation.txt"
        _, stream = self.create_streamed_file(source)
        operation = self.engine().move(source, self.destination_directory)
        _mutate_stream_without_primary_stat_change(
            operation.recovery_copy, b"Z" * len(stream)
        )

        with self.assertRaises(SourceChangedError):
            self.engine().restore_backup(operation.operation_id)

        self.assertFalse(source.exists())
        self.assertTrue(operation.recovery_copy.exists())
        self.assertEqual(_read_stream(operation.destination), stream)

    def test_source_named_stream_mutation_before_commit_is_detected(self) -> None:
        source = self.root / "source-mutation.txt"
        _, stream = self.create_streamed_file(source)

        def mutate_source(phase: str, path: Path | None) -> None:
            if phase == "after_stage_verification":
                _mutate_stream_without_primary_stat_change(
                    source, b"Q" * len(stream)
                )

        with self.assertRaises(SourceChangedError):
            self.engine(fault_hook=mutate_source).move(
                source, self.destination_directory
            )

        self.assertTrue(source.exists())
        self.assertFalse((self.destination_directory / source.name).exists())

    def test_new_stream_attached_precommit_is_rebaselined_and_preserved(self) -> None:
        source = self.root / "late-endpoint-tag.txt"
        primary = b"program data before endpoint classification"
        stream = b"late endpoint policy payload"
        source.write_bytes(primary)
        attached = False

        def attach_stream_after_first_copy(phase: str, path: Path | None) -> None:
            nonlocal attached
            if phase == "after_copy" and not attached:
                attached = True
                _write_stream(source, stream)

        operation = self.engine(fault_hook=attach_stream_after_first_copy).move(
            source, self.destination_directory
        )

        self.assertTrue(attached)
        self.assertEqual(operation.status, "backup_retained")
        self.assertEqual(operation.destination.read_bytes(), primary)
        self.assertEqual(_read_stream(operation.destination), stream)
        self.assertEqual(_read_stream(operation.recovery_copy), stream)
        history = self.engine().journal.events(operation.operation_id)
        self.assertTrue(
            any("baseline refreshed" in event["message"] for event in history)
        )

    def test_directory_named_stream_is_preserved(self) -> None:
        source = self.root / "streamed-directory"
        source.mkdir()
        (source / "data.bin").write_bytes(b"directory payload")
        stream = b"directory endpoint metadata"
        try:
            _write_stream(source, stream)
        except OSError as error:
            self.skipTest(f"Directory named streams are unavailable: {error}")

        operation = self.engine().move(source, self.destination_directory)

        self.assertEqual(_read_stream(operation.destination), stream)
        self.assertEqual(_read_stream(operation.recovery_copy), stream)


if __name__ == "__main__":
    unittest.main()
