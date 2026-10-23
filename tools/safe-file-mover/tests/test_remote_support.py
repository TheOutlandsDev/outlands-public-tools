from __future__ import annotations

import stat
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from safe_file_mover.core import (
    EntryKind,
    InvalidMoveError,
    Manifest,
    ManifestEntry,
    NamedStream,
    OperationStateError,
    SafeMoveEngine,
)


def _remote_snapshot_fixture() -> Manifest:
    directory = ManifestEntry(
        relative_path=".",
        kind=EntryKind.DIRECTORY,
        size=0,
        sha256=None,
        link_target=None,
        device=10,
        inode=20,
        mtime_ns=1_000,
        mode=stat.S_IFDIR | 0o755,
    )
    payload = ManifestEntry(
        relative_path="payload.bin",
        kind=EntryKind.FILE,
        size=7,
        sha256="a" * 64,
        link_target=None,
        device=10,
        inode=21,
        mtime_ns=2_000,
        mode=stat.S_IFREG | 0o644,
        named_streams=(
            NamedStream(
                name=":metadata:$DATA",
                size=4,
                sha256="b" * 64,
            ),
        ),
    )
    return Manifest(
        entries=(directory, payload),
        total_bytes=11,
        digest="fixture-only",
    )


class RemoteSupportSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.destination = self.root / "destination"
        self.destination.mkdir()

    def test_streamless_preupgrade_manifest_remains_readable(self) -> None:
        source = self.root / "legacy.dat"
        source.write_bytes(b"legacy manifest payload")
        manifest_data = SafeMoveEngine(self.state).plan(
            source, self.destination
        ).manifest.to_dict()
        for entry in manifest_data["entries"]:
            entry.pop("named_streams", None)

        restored = Manifest.from_dict(manifest_data)

        self.assertEqual(restored.digest, manifest_data["digest"])
        self.assertTrue(all(not entry.named_streams for entry in restored.entries))

    def test_remote_sqlite_state_directory_is_rejected(self) -> None:
        with mock.patch(
            "safe_file_mover.core.is_remote_path", return_value=True
        ):
            with self.assertRaisesRegex(InvalidMoveError, "journal must be stored"):
                SafeMoveEngine(self.state)

    def test_remote_move_cannot_auto_delete_recovery_copy(self) -> None:
        source = self.root / "remote-auto-purge.dat"
        source.write_bytes(b"must retain a recovery copy")
        engine = SafeMoveEngine(self.state)

        with mock.patch(
            "safe_file_mover.core.is_remote_path", return_value=True
        ):
            with self.assertRaisesRegex(
                InvalidMoveError, "Automatic recovery-copy deletion"
            ):
                engine.move(source, self.destination, keep_backup=False)

        self.assertTrue(source.exists())
        self.assertFalse((self.destination / source.name).exists())
        self.assertEqual(engine.list_operations(), [])

    def test_remote_purge_requires_explicit_acknowledgment(self) -> None:
        source = self.root / "remote-purge.dat"
        source.write_bytes(b"remote destination bytes")
        engine = SafeMoveEngine(self.state)
        operation = engine.move(source, self.destination)

        with mock.patch(
            "safe_file_mover.core.is_remote_path", return_value=True
        ):
            with self.assertRaisesRegex(OperationStateError, "destination is remote"):
                engine.purge_backup(operation.operation_id)
            self.assertTrue(operation.recovery_copy.exists())
            completed = engine.purge_backup(
                operation.operation_id, acknowledge_remote_risk=True
            )

        self.assertEqual(completed.status, "complete")
        self.assertFalse(operation.recovery_copy.exists())

    def test_remote_snapshot_tolerates_directory_mtime_drift(self) -> None:
        expected = _remote_snapshot_fixture()
        changed_directory = replace(expected.entries[0], mtime_ns=9_999)
        actual = replace(
            expected,
            entries=(changed_directory, expected.entries[1]),
        )

        self.assertTrue(expected.remote_snapshot_matches(actual))
        self.assertTrue(actual.remote_snapshot_matches(expected))

    def test_remote_snapshot_rejects_file_mtime_drift(self) -> None:
        expected = _remote_snapshot_fixture()
        changed_file = replace(expected.entries[1], mtime_ns=9_999)
        actual = replace(expected, entries=(expected.entries[0], changed_file))

        self.assertFalse(expected.remote_snapshot_matches(actual))

    def test_remote_snapshot_rejects_file_content_and_stream_changes(self) -> None:
        expected = _remote_snapshot_fixture()
        payload = expected.entries[1]
        stream = payload.named_streams[0]
        variants = {
            "primary content": replace(payload, sha256="c" * 64),
            "stream content": replace(
                payload,
                named_streams=(replace(stream, sha256="d" * 64),),
            ),
            "removed stream": replace(payload, named_streams=()),
            "added stream": replace(
                payload,
                named_streams=payload.named_streams
                + (
                    NamedStream(
                        name=":extra:$DATA",
                        size=3,
                        sha256="e" * 64,
                    ),
                ),
            ),
        }

        for label, changed_file in variants.items():
            with self.subTest(label):
                actual = replace(
                    expected,
                    entries=(expected.entries[0], changed_file),
                )
                self.assertFalse(expected.remote_snapshot_matches(actual))

    def test_remote_snapshot_rejects_mode_changes(self) -> None:
        expected = _remote_snapshot_fixture()

        for index, label in ((0, "directory"), (1, "file")):
            with self.subTest(label):
                changed = replace(
                    expected.entries[index],
                    mode=expected.entries[index].mode ^ stat.S_IWUSR,
                )
                entries = list(expected.entries)
                entries[index] = changed
                actual = replace(expected, entries=tuple(entries))
                self.assertFalse(expected.remote_snapshot_matches(actual))

    def test_remote_snapshot_rejects_tree_shape_changes(self) -> None:
        expected = _remote_snapshot_fixture()
        payload = expected.entries[1]
        variants = {
            "added entry": expected.entries
            + (replace(payload, relative_path="added.bin"),),
            "removed entry": expected.entries[:1],
            "renamed entry": (
                expected.entries[0],
                replace(payload, relative_path="renamed.bin"),
            ),
        }

        for label, entries in variants.items():
            with self.subTest(label):
                actual = replace(expected, entries=entries)
                self.assertFalse(expected.remote_snapshot_matches(actual))


if __name__ == "__main__":
    unittest.main()
