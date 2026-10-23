"""Crash-resumable, verified file moving engine.

The engine deliberately copies before it changes the source path. After the
destination is verified and committed, the source is renamed to a unique
recovery path. The recovery copy is retained by default and can be purged only
after both copies are verified again.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import stat
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable, Iterable, Iterator

from .journal import Journal, OperationRecord, utc_now

CHUNK_SIZE = 4 * 1024 * 1024
MAX_NAMED_STREAM_REBASES = 3
TERMINAL_STATUSES = {"complete", "restored", "abandoned"}
RECOVERABLE_STATUSES = {
    "planned",
    "copying",
    "verified",
    "destination_committed",
    "restoring",
    "purging",
}


class SafeMoveError(Exception):
    """Base exception for controlled move failures."""


class InvalidMoveError(SafeMoveError):
    """The requested source/destination topology is unsafe or invalid."""


class CollisionError(SafeMoveError):
    """The destination or an operation reservation already exists."""


class UnsupportedSourceError(SafeMoveError):
    """The source includes an object the portable engine cannot preserve."""


class SourceChangedError(SafeMoveError):
    """The source changed after the operation's baseline was recorded."""


class VerificationError(SafeMoveError):
    """A copy does not match the recorded content manifest."""


class OperationStateError(SafeMoveError):
    """An operation cannot safely transition from its current state."""


class ConflictPolicy(StrEnum):
    FAIL = "fail"
    RENAME = "rename"


class EntryKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


@dataclass(frozen=True, slots=True)
class NamedStream:
    """A Windows named ``$DATA`` stream attached to a file or directory."""

    name: str
    size: int
    sha256: str

    def identity(self) -> tuple[object, ...]:
        return (self.name, self.size, self.sha256)


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    relative_path: str
    kind: str
    size: int
    sha256: str | None
    link_target: str | None
    device: int
    inode: int
    mtime_ns: int
    mode: int
    named_streams: tuple[NamedStream, ...] = ()

    def content_identity(self) -> tuple[object, ...]:
        identity: tuple[object, ...] = (
            self.relative_path,
            self.kind,
            self.size,
            self.sha256,
            self.link_target,
        )
        # Omitting an empty stream tuple preserves compatibility with journals
        # written before named-stream support was introduced.
        if self.named_streams:
            identity += (tuple(stream.identity() for stream in self.named_streams),)
        return identity

    def snapshot_identity(self) -> tuple[object, ...]:
        return self.content_identity() + (
            self.device,
            self.inode,
            self.mtime_ns,
            self.mode,
        )


@dataclass(frozen=True, slots=True)
class Manifest:
    entries: tuple[ManifestEntry, ...]
    total_bytes: int
    digest: str

    @property
    def item_count(self) -> int:
        return len(self.entries)

    @property
    def file_count(self) -> int:
        return sum(entry.kind == EntryKind.FILE for entry in self.entries)

    @property
    def directory_count(self) -> int:
        return sum(entry.kind == EntryKind.DIRECTORY for entry in self.entries)

    def to_dict(self) -> dict[str, object]:
        return {
            "entries": [asdict(entry) for entry in self.entries],
            "total_bytes": self.total_bytes,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Manifest:
        raw_entries = data.get("entries")
        if not isinstance(raw_entries, list):
            raise VerificationError("The stored manifest is malformed.")
        entries_list: list[ManifestEntry] = []
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                raise VerificationError("The stored manifest entry is malformed.")
            entry_data = dict(raw_entry)
            raw_streams = entry_data.pop("named_streams", [])
            if not isinstance(raw_streams, list):
                raise VerificationError("The stored named-stream manifest is malformed.")
            streams: list[NamedStream] = []
            for raw_stream in raw_streams:
                if not isinstance(raw_stream, dict):
                    raise VerificationError(
                        "The stored named-stream entry is malformed."
                    )
                try:
                    stream = NamedStream(
                        name=str(raw_stream["name"]),
                        size=int(raw_stream["size"]),
                        sha256=str(raw_stream["sha256"]),
                    )
                except (KeyError, TypeError, ValueError) as error:
                    raise VerificationError(
                        "The stored named-stream entry is malformed."
                    ) from error
                _validate_named_stream(stream)
                streams.append(stream)
            entry_data["named_streams"] = tuple(streams)
            try:
                entries_list.append(ManifestEntry(**entry_data))
            except (TypeError, ValueError) as error:
                raise VerificationError("The stored manifest entry is malformed.") from error
        entries = tuple(entries_list)
        manifest = cls(
            entries=entries,
            total_bytes=int(data["total_bytes"]),
            digest=str(data["digest"]),
        )
        if manifest.digest != _manifest_digest(entries):
            raise VerificationError("The stored manifest checksum is invalid.")
        return manifest

    def content_matches(self, other: Manifest) -> bool:
        return [entry.content_identity() for entry in self.entries] == [
            entry.content_identity() for entry in other.entries
        ]

    def snapshot_matches(self, other: Manifest) -> bool:
        return [entry.snapshot_identity() for entry in self.entries] == [
            entry.snapshot_identity() for entry in other.entries
        ]

    def remote_snapshot_matches(self, other: Manifest) -> bool:
        """Compare a remote snapshot without unstable SMB identity metadata.

        SMB clients can observe a directory's updated timestamp after its child
        entries are already visible.  Entry paths and content identities still
        prove the tree structure, so ignore directory timestamp drift while
        retaining strict file timestamps, modes, bytes, links, and streams.
        """
        def remote_identity(entry: ManifestEntry) -> tuple[object, ...]:
            mtime_ns = (
                None if entry.kind == EntryKind.DIRECTORY else entry.mtime_ns
            )
            return entry.content_identity() + (mtime_ns, entry.mode)

        return [
            remote_identity(entry) for entry in self.entries
        ] == [
            remote_identity(entry) for entry in other.entries
        ]


@dataclass(frozen=True, slots=True)
class MovePlan:
    source: Path
    destination: Path
    manifest: Manifest
    conflict_policy: ConflictPolicy
    free_bytes: int
    required_bytes: int
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MoveOperation:
    operation_id: str
    source: Path
    destination: Path
    recovery_copy: Path
    status: str
    total_bytes: int
    item_count: int
    keep_backup: bool
    last_error: str | None

    @classmethod
    def from_record(cls, record: OperationRecord) -> MoveOperation:
        return cls(
            operation_id=record.operation_id,
            source=Path(record.source),
            destination=Path(record.destination),
            recovery_copy=Path(record.backup),
            status=record.status,
            total_bytes=record.total_bytes,
            item_count=record.item_count,
            keep_backup=record.keep_backup,
            last_error=record.last_error,
        )


@dataclass(frozen=True, slots=True)
class Progress:
    phase: str
    path: str
    bytes_done: int
    total_bytes: int
    items_done: int
    item_count: int


ProgressCallback = Callable[[Progress], None]
FaultHook = Callable[[str, Path | None], None]


class SafeMoveEngine:
    """Verified move service with durable recovery records.

    Progress and fault callbacks run synchronously while the operation guard is
    held. They must return promptly and must not call back into an engine from
    another thread. The bundled GUI callbacks only enqueue messages.
    """

    _process_lock = threading.RLock()

    def __init__(
        self,
        state_directory: Path | str | None = None,
        *,
        chunk_size: int = CHUNK_SIZE,
        fault_hook: FaultHook | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.journal = Journal(state_directory)
        if is_remote_path(self.journal.state_directory):
            raise InvalidMoveError(
                "The SQLite recovery journal must be stored on a local drive. "
                "Source and destination paths may be SMB shares, but use a local "
                "--state-dir or the default local application-data directory."
            )
        self.chunk_size = chunk_size
        self.fault_hook = fault_hook
        self._guard_state = threading.local()

    def plan(
        self,
        source: Path | str,
        destination_directory: Path | str,
        *,
        new_name: str | None = None,
        conflict_policy: ConflictPolicy | str = ConflictPolicy.FAIL,
    ) -> MovePlan:
        policy = ConflictPolicy(conflict_policy)
        source_path = _absolute_without_resolving(Path(source).expanduser())
        destination_directory_path = _absolute_without_resolving(
            Path(destination_directory).expanduser()
        )

        if not _lexists(source_path):
            raise InvalidMoveError(f"Source does not exist: {source_path}")
        if source_path.parent == source_path:
            raise InvalidMoveError("A filesystem root cannot be moved.")
        if not destination_directory_path.exists():
            raise InvalidMoveError(
                f"Destination directory does not exist: {destination_directory_path}"
            )
        if not destination_directory_path.is_dir():
            raise InvalidMoveError(
                f"Destination must be a directory: {destination_directory_path}"
            )

        source_path = _canonicalize_windows_network_path(source_path)
        destination_directory_path = _canonicalize_windows_network_path(
            destination_directory_path
        )

        destination_directory_path = destination_directory_path.resolve(strict=True)
        target_name = new_name if new_name is not None else source_path.name
        _validate_target_name(target_name)
        requested_destination = destination_directory_path / target_name

        root_kind = _entry_kind(source_path)
        if root_kind == EntryKind.DIRECTORY:
            source_real = source_path.resolve(strict=True)
            requested_real = destination_directory_path / target_name
            if _is_relative_to(requested_real, source_real):
                raise InvalidMoveError(
                    "The destination cannot be inside the source directory."
                )
            state_real = self.journal.state_directory.resolve(strict=False)
            if _is_relative_to(state_real, source_real):
                raise InvalidMoveError(
                    "The journal directory cannot be inside the source directory."
                )

        if _same_lexical_path(source_path, requested_destination):
            raise InvalidMoveError("Source and destination are the same path.")

        destination = _choose_destination(
            requested_destination,
            policy,
            reservation_blocks=self._reservation_blocks,
        )
        manifest = build_manifest(source_path, chunk_size=self.chunk_size)
        usage = shutil.disk_usage(destination_directory_path)
        overhead = min(max(manifest.item_count * 4096, 1024 * 1024), 64 * 1024 * 1024)
        required = manifest.total_bytes + overhead
        if usage.free < required:
            raise SafeMoveError(
                f"Not enough free space: need about {required:,} bytes, "
                f"but only {usage.free:,} bytes are available."
            )

        warnings = [
            "Close programs that may write to the source before moving it.",
            "Windows named data streams are hashed, copied, and re-verified. ACLs, "
            "ownership, POSIX extended attributes, sparse allocation, and hard-link "
            "relationships are not fully preserved across volumes.",
        ]
        if is_remote_path(source_path) or is_remote_path(destination):
            warnings.append(
                "Verified SMB mode: the share must honor exclusive creation, "
                "same-directory no-replace rename, named streams when present, and "
                "file flush requests. Server/controller power-loss durability remains "
                "outside the client's control."
            )
        else:
            warnings.append(
                "Local-drive mode still depends on the filesystem, controller, and "
                "hardware honoring flush requests."
            )
        return MovePlan(
            source=source_path,
            destination=destination,
            manifest=manifest,
            conflict_policy=policy,
            free_bytes=usage.free,
            required_bytes=required,
            warnings=tuple(warnings),
        )

    def move(
        self,
        source: Path | str,
        destination_directory: Path | str,
        *,
        new_name: str | None = None,
        conflict_policy: ConflictPolicy | str = ConflictPolicy.FAIL,
        keep_backup: bool = True,
        progress: ProgressCallback | None = None,
    ) -> MoveOperation:
        plan = self.plan(
            source,
            destination_directory,
            new_name=new_name,
            conflict_policy=conflict_policy,
        )
        if not keep_backup and is_remote_path(plan.destination):
            raise InvalidMoveError(
                "Automatic recovery-copy deletion is disabled for remote destinations. "
                "Keep the recovery copy, validate the application data, then use purge "
                "with an explicit remote-risk acknowledgment."
            )
        with self._operation_guard():
            record = self._create_operation(plan, keep_backup=keep_backup)
            try:
                record = self._run(record, progress=progress)
            except Exception as error:
                self.journal.update(
                    record.operation_id,
                    message=f"Operation paused after error: {error}",
                    last_error=str(error),
                )
                raise
            return MoveOperation.from_record(record)

    def recover(
        self,
        operation_id: str,
        *,
        progress: ProgressCallback | None = None,
    ) -> MoveOperation:
        with self._operation_guard():
            record = self.journal.get(operation_id)
            _validate_record_paths(record)
            if record.status in TERMINAL_STATUSES:
                self._release_reservation(record)
                return MoveOperation.from_record(record)
            if record.status == "backup_retained":
                self._release_reservation(record)
                if not record.keep_backup:
                    return self.purge_backup(operation_id)
                return MoveOperation.from_record(record)
            if record.status == "restoring":
                return self.restore_backup(operation_id)
            if record.status == "purging":
                return self.purge_backup(operation_id)
            if record.status not in RECOVERABLE_STATUSES:
                raise OperationStateError(
                    f"Operation {operation_id} is not recoverable from {record.status}."
                )
            try:
                self._ensure_reservation(record)
                record = self._run(record, progress=progress)
            except Exception as error:
                self.journal.update(
                    operation_id,
                    message=f"Recovery paused after error: {error}",
                    last_error=str(error),
                )
                raise
            return MoveOperation.from_record(record)

    def recover_all(
        self, *, progress: ProgressCallback | None = None
    ) -> list[MoveOperation]:
        recovered: list[MoveOperation] = []
        for record in reversed(self.journal.list(include_complete=False)):
            if record.status in RECOVERABLE_STATUSES or (
                record.status == "backup_retained" and not record.keep_backup
            ):
                try:
                    recovered.append(
                        self.recover(record.operation_id, progress=progress)
                    )
                except (SafeMoveError, OSError, KeyError, ValueError):
                    # The individual recovery call has already recorded its error.
                    # Continue so one damaged operation cannot strand unrelated ones.
                    recovered.append(
                        MoveOperation.from_record(
                            self.journal.get(record.operation_id)
                        )
                    )
        return recovered

    def purge_backup(
        self,
        operation_id: str,
        *,
        acknowledge_remote_risk: bool = False,
    ) -> MoveOperation:
        """Permanently remove a retained copy, but only after re-verification."""
        with self._operation_guard():
            record = self.journal.get(operation_id)
            _validate_record_paths(record)
            if record.status == "complete":
                return MoveOperation.from_record(record)
            if record.status not in {"backup_retained", "purging"}:
                raise OperationStateError(
                    "Only a verified, retained recovery copy can be purged."
                )
            manifest = Manifest.from_dict(record.manifest)
            destination = Path(record.destination)
            backup = Path(record.backup)
            purging = backup.with_name(backup.name + ".purging")
            if (
                record.status == "backup_retained"
                and is_remote_path(destination)
                and not acknowledge_remote_risk
            ):
                raise OperationStateError(
                    "The destination is remote. Verification proves the bytes returned "
                    "by the share, not server-side power-loss durability. Re-run purge "
                    "with explicit remote-risk acknowledgment after application-level "
                    "validation or a provider snapshot."
                )
            self._verify_content(destination, manifest, "destination")

            if record.status == "backup_retained":
                if not _lexists(backup):
                    if _lexists(purging):
                        raise OperationStateError(
                            f"An unjournaled purge path exists: {purging}"
                        )
                    record = self.journal.update(
                        operation_id,
                        status="complete",
                        message="Recovery copy was already absent; destination re-verified.",
                        clear_error=True,
                    )
                    return MoveOperation.from_record(record)
                if _lexists(purging):
                    raise CollisionError(f"Purge path is occupied: {purging}")
                self._verify_snapshot(backup, manifest, "recovery copy")
                self._hit("before_backup_purge", backup)
                # Recheck after the failpoint/confirmation boundary. This narrows
                # the unavoidable race with non-cooperating external writers.
                self._verify_content(destination, manifest, "destination")
                self._verify_snapshot(backup, manifest, "recovery copy")
                record = self.journal.update(
                    operation_id,
                    status="purging",
                    message="Permanent purge intent recorded after re-verification.",
                    clear_error=True,
                )

            backup_exists = _lexists(backup)
            purging_exists = _lexists(purging)
            if backup_exists and purging_exists:
                if not _same_file_if_possible(backup, purging):
                    raise OperationStateError(
                        "Both recovery and purge paths exist and are different; "
                        "refusing to remove either."
                    )
                self._verify_snapshot(backup, manifest, "recovery copy")
                _fsync_directory(purging.parent)
                backup.unlink()
                _fsync_directory(backup.parent)
                backup_exists = False
            elif backup_exists:
                self._verify_snapshot(backup, manifest, "recovery copy")
                _commit_no_replace(backup, purging)
                backup_exists = False
                purging_exists = True
            elif not purging_exists:
                record = self.journal.update(
                    operation_id,
                    status="complete",
                    message="Finished an interrupted purge; destination re-verified.",
                    clear_error=True,
                )
                return MoveOperation.from_record(record)

            # A previous delete may have stopped part-way through a directory.
            # Once durable purge intent exists, it is safe to resume removing that
            # managed path as long as the destination still verifies.
            self._verify_content(destination, manifest, "destination")
            if _lexists(purging):
                self._hit("before_purge_delete", purging)
                self._verify_content(destination, manifest, "destination")
                _remove_path(purging)
                _fsync_directory(purging.parent)
            self._hit("after_backup_purge", purging)
            record = self.journal.update(
                operation_id,
                status="complete",
                message="Recovery copy permanently removed after re-verification.",
                clear_error=True,
            )
            return MoveOperation.from_record(record)

    def restore_backup(self, operation_id: str) -> MoveOperation:
        """Restore the retained original path; the destination remains untouched."""
        with self._operation_guard():
            record = self.journal.get(operation_id)
            _validate_record_paths(record)
            if record.status == "restored":
                return MoveOperation.from_record(record)
            if record.status not in {"backup_retained", "restoring"}:
                raise OperationStateError("This operation has no retained recovery copy.")
            source = Path(record.source)
            backup = Path(record.backup)
            manifest = Manifest.from_dict(record.manifest)
            if _lexists(source):
                if _lexists(backup) and _same_file_if_possible(source, backup):
                    self._verify_snapshot(source, manifest, "recovery copy")
                    backup.unlink()
                    _fsync_directory(source.parent)
                    record = self.journal.update(
                        operation_id,
                        status="restored",
                        message="Finished an interrupted recovery-copy restore.",
                        clear_error=True,
                    )
                    return MoveOperation.from_record(record)
                if not _lexists(backup):
                    self._verify_snapshot(source, manifest, "restored source")
                    record = self.journal.update(
                        operation_id,
                        status="restored",
                        message="Finished an interrupted recovery-copy restore.",
                        clear_error=True,
                    )
                    return MoveOperation.from_record(record)
                raise CollisionError(f"The original source path is occupied: {source}")
            self._verify_snapshot(backup, manifest, "recovery copy")
            if record.status != "restoring":
                record = self.journal.update(
                    operation_id,
                    status="restoring",
                    message="Recovery-copy restore intent recorded.",
                    clear_error=True,
                )
            _commit_no_replace(backup, source)
            _fsync_directory(source.parent)
            self._hit("after_backup_restore", source)
            record = self.journal.update(
                operation_id,
                status="restored",
                message="Recovery copy restored to the original source path.",
                clear_error=True,
            )
            return MoveOperation.from_record(record)

    def abandon(self, operation_id: str) -> MoveOperation:
        """Discard an uncommitted partial copy while preserving the source."""
        with self._operation_guard():
            record = self.journal.get(operation_id)
            _validate_record_paths(record)
            if record.status not in {"planned", "copying", "verified"}:
                raise OperationStateError(
                    "Only an operation that has not committed its destination can be abandoned."
                )
            manifest = Manifest.from_dict(record.manifest)
            self._verify_snapshot(Path(record.source), manifest, "source")
            staging = Path(record.staging)
            if _lexists(staging):
                _validate_managed_path(staging, record.operation_id, ".partial")
                _remove_path(staging)
                _fsync_directory(staging.parent)
            self._release_reservation(record)
            record = self.journal.update(
                operation_id,
                status="abandoned",
                message="Uncommitted staging data discarded; source preserved.",
                clear_error=True,
            )
            return MoveOperation.from_record(record)

    def list_operations(self, *, include_complete: bool = True) -> list[MoveOperation]:
        return [
            MoveOperation.from_record(record)
            for record in self.journal.list(include_complete=include_complete)
        ]

    @contextmanager
    def _operation_guard(self) -> Iterator[None]:
        """Serialize mutating work across threads and cooperating processes."""
        with self._process_lock:
            depth = getattr(self._guard_state, "depth", 0)
            if depth:
                self._guard_state.depth = depth + 1
                try:
                    yield
                finally:
                    self._guard_state.depth -= 1
                return

            self.journal.initialize()
            lock_path = self.journal.state_directory / "operation.lock"
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0),
                0o600,
            )
            locked = False
            try:
                lock_info = os.fstat(descriptor)
                if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_nlink != 1:
                    raise OperationStateError("The operation lock must be a private regular file.")
                if os.name != "nt" and (
                    lock_info.st_uid != os.getuid()
                    or stat.S_IMODE(lock_info.st_mode) & 0o077
                ):
                    raise OperationStateError("The operation lock must be owner-private.")
                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"\0")
                    os.fsync(descriptor)
                os.lseek(descriptor, 0, os.SEEK_SET)
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as error:
                    raise OperationStateError(
                        "Another Safe File Mover instance is changing files. "
                        "Wait for it to finish, then refresh or recover."
                    ) from error
                locked = True
                self._guard_state.depth = 1
                yield
            finally:
                self._guard_state.depth = 0
                if locked:
                    try:
                        os.lseek(descriptor, 0, os.SEEK_SET)
                        if os.name == "nt":
                            import msvcrt

                            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                        else:
                            import fcntl

                            fcntl.flock(descriptor, fcntl.LOCK_UN)
                    except OSError:
                        pass
                os.close(descriptor)

    def _create_operation(self, plan: MovePlan, *, keep_backup: bool) -> OperationRecord:
        operation_id = uuid.uuid4().hex
        destination = plan.destination
        staging = destination.parent / f".safemove-{operation_id}.partial"
        backup = plan.source.parent / f".safemove-{operation_id}.recovery"
        reservation = _reservation_path(destination)
        now = utc_now()
        record = OperationRecord(
            operation_id=operation_id,
            created_at=now,
            updated_at=now,
            source=str(plan.source),
            destination=str(destination),
            staging=str(staging),
            backup=str(backup),
            reservation=str(reservation),
            status="planned",
            manifest_json=json.dumps(
                plan.manifest.to_dict(), ensure_ascii=False, separators=(",", ":")
            ),
            total_bytes=plan.manifest.total_bytes,
            item_count=plan.manifest.item_count,
            keep_backup=keep_backup,
            conflict_policy=plan.conflict_policy.value,
        )
        self.journal.create(record, "Source manifest recorded; no paths changed yet.")
        try:
            self._create_reservation(record)
        except Exception as error:
            self.journal.update(
                operation_id,
                status="abandoned",
                message=f"Could not reserve destination: {error}",
                last_error=str(error),
            )
            raise
        return self.journal.get(operation_id)

    def _run(
        self,
        record: OperationRecord,
        *,
        progress: ProgressCallback | None,
    ) -> OperationRecord:
        _validate_record_paths(record)
        manifest = Manifest.from_dict(record.manifest)
        source = Path(record.source)
        destination = Path(record.destination)
        staging = Path(record.staging)
        backup = Path(record.backup)

        if record.status in {"planned", "copying"}:
            stream_rebases = 0
            while True:
                try:
                    self._verify_snapshot(source, manifest, "source")
                    if _lexists(destination):
                        raise CollisionError(
                            "Destination appeared before commit; nothing was "
                            f"overwritten: {destination}"
                        )
                    if _lexists(staging):
                        _validate_managed_path(
                            staging, record.operation_id, ".partial"
                        )
                        _remove_path(staging)
                    record = self.journal.update(
                        record.operation_id,
                        status="copying",
                        message="Copying into destination-side staging.",
                        clear_error=True,
                    )
                    self._hit("before_copy", source)
                    self._copy_manifest(source, staging, manifest, progress)
                    self._hit("after_copy", staging)
                    self._hit("before_stage_verification", staging)
                    self._verify_content(staging, manifest, "staged copy")
                    self._hit("after_stage_verification", staging)
                    self._verify_snapshot(source, manifest, "source")
                    record = self.journal.update(
                        record.operation_id,
                        status="verified",
                        message="Staged copy and unchanged source verified.",
                        clear_error=True,
                    )
                    break
                except SourceChangedError:
                    if stream_rebases >= MAX_NAMED_STREAM_REBASES:
                        raise
                    refreshed_manifest = build_manifest(
                        source, chunk_size=self.chunk_size
                    )
                    additions = _named_stream_additions_only(
                        manifest,
                        refreshed_manifest,
                        remote_source=is_remote_path(source),
                    )
                    if not additions:
                        raise
                    stream_rebases += 1
                    record = self.journal.update_precommit_manifest(
                        record.operation_id,
                        manifest_json=json.dumps(
                            refreshed_manifest.to_dict(),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        total_bytes=refreshed_manifest.total_bytes,
                        item_count=refreshed_manifest.item_count,
                        message=(
                            "Pre-commit baseline refreshed to include newly attached "
                            "named data streams: " + ", ".join(additions)
                        ),
                    )
                    manifest = refreshed_manifest
                    self._hit("after_named_stream_rebaseline", source)

        if record.status == "verified":
            if _lexists(destination):
                if _lexists(staging) and not _same_file_if_possible(staging, destination):
                    raise CollisionError(
                        "Both staged data and a destination exist; refusing to guess which is valid."
                    )
                self._verify_content(destination, manifest, "committed destination")
                if _lexists(staging) and _same_file_if_possible(staging, destination):
                    _remove_path(staging)
            else:
                self._verify_content(staging, manifest, "staged copy")
                self._verify_snapshot(source, manifest, "source")
                self._hit("before_destination_commit", staging)
                _commit_no_replace(staging, destination)
                _fsync_directory(destination.parent)
                self._hit("after_destination_commit", destination)
            record = self.journal.update(
                record.operation_id,
                status="destination_committed",
                message="Verified destination committed; source still preserved.",
                clear_error=True,
            )

        if record.status == "destination_committed":
            self._verify_content(destination, manifest, "committed destination")
            source_exists = _lexists(source)
            backup_exists = _lexists(backup)
            if source_exists and backup_exists:
                if _same_file_if_possible(source, backup):
                    self._verify_snapshot(backup, manifest, "recovery copy")
                    source.unlink()
                    _fsync_directory(source.parent)
                    source_exists = False
                else:
                    raise OperationStateError(
                        "Both the source and recovery path exist; refusing to remove either."
                    )
            if backup_exists:
                self._verify_snapshot(backup, manifest, "recovery copy")
            elif source_exists:
                self._verify_snapshot(source, manifest, "source")
                if _lexists(backup):
                    raise CollisionError(f"Recovery path is occupied: {backup}")
                self._hit("before_source_tombstone", source)
                _commit_no_replace(source, backup)
                _fsync_directory(source.parent)
                self._hit("after_source_tombstone", backup)
                self._verify_snapshot(backup, manifest, "recovery copy")
            else:
                record = self.journal.update(
                    record.operation_id,
                    status="complete",
                    message="Destination verified; source and recovery path are already absent.",
                    clear_error=True,
                )
                self._release_reservation(record)
                return record
            record = self.journal.update(
                record.operation_id,
                status="backup_retained",
                message="Original source retained at the recorded recovery path.",
                clear_error=True,
            )
            self._release_reservation(record)

        if record.status == "backup_retained" and not record.keep_backup:
            return self.journal.get(
                self.purge_backup(record.operation_id).operation_id
            )
        return record

    def _copy_manifest(
        self,
        source: Path,
        staging: Path,
        manifest: Manifest,
        progress: ProgressCallback | None,
    ) -> None:
        root_entry = _entry_by_path(manifest, "")
        bytes_done = 0
        items_done = 0

        def report(
            entry: ManifestEntry,
            added_bytes: int = 0,
            *,
            item_finished: bool = True,
        ) -> None:
            nonlocal bytes_done, items_done
            bytes_done += added_bytes
            if item_finished:
                items_done += 1
            if progress is not None:
                progress(
                    Progress(
                        phase="copying",
                        path=entry.relative_path or source.name,
                        bytes_done=bytes_done,
                        total_bytes=manifest.total_bytes,
                        items_done=items_done,
                        item_count=manifest.item_count,
                    )
                )

        if root_entry.kind == EntryKind.FILE:
            self._copy_file(
                source,
                staging,
                root_entry,
                lambda count: report(root_entry, count, item_finished=False),
            )
            report(root_entry)
            _fsync_directory(staging.parent)
            return
        if root_entry.kind == EntryKind.SYMLINK:
            self._copy_symlink(source, staging, root_entry)
            report(root_entry)
            _fsync_directory(staging.parent)
            return

        staging.mkdir(mode=0o700)
        self._copy_named_streams(
            source,
            staging,
            root_entry,
            lambda count: report(root_entry, count, item_finished=False),
        )
        report(root_entry)
        directory_entries: list[ManifestEntry] = [root_entry]
        for entry in manifest.entries:
            if entry.relative_path == "":
                continue
            relative = _relative_path(entry.relative_path)
            source_item = source / relative
            staging_item = staging / relative
            self._hit("before_copy_item", source_item)
            if entry.kind == EntryKind.DIRECTORY:
                staging_item.mkdir(mode=0o700)
                directory_entries.append(entry)
                self._copy_named_streams(
                    source_item,
                    staging_item,
                    entry,
                    lambda count, current=entry: report(
                        current, count, item_finished=False
                    ),
                )
                report(entry)
            elif entry.kind == EntryKind.FILE:
                self._copy_file(
                    source_item,
                    staging_item,
                    entry,
                    lambda count, current=entry: report(
                        current, count, item_finished=False
                    ),
                )
                report(entry)
            elif entry.kind == EntryKind.SYMLINK:
                self._copy_symlink(source_item, staging_item, entry)
                report(entry)
            else:  # pragma: no cover - manifests are validated when created
                raise UnsupportedSourceError(f"Unknown manifest kind: {entry.kind}")
            self._hit("after_copy_item", staging_item)

        for entry in sorted(
            directory_entries,
            key=lambda item: item.relative_path.count("/"),
            reverse=True,
        ):
            relative = _relative_path(entry.relative_path)
            source_item = source if entry.relative_path == "" else source / relative
            staging_item = staging if entry.relative_path == "" else staging / relative
            _copy_metadata(source_item, staging_item)
            _fsync_directory(staging_item)
        _fsync_directory(staging.parent)

    def _copy_file(
        self,
        source: Path,
        destination: Path,
        entry: ManifestEntry,
        chunk_progress: Callable[[int], None] | None = None,
    ) -> None:
        if _entry_kind(source) != EntryKind.FILE:
            raise SourceChangedError(f"Source changed before copy: {source}")
        before = source.stat(follow_symlinks=False)
        if not _stat_matches_entry(before, entry):
            raise SourceChangedError(f"Source changed before copy: {source}")
        digest = hashlib.sha256()
        with _open_regular_source(source, before) as input_file:
            descriptor = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            output_file = os.fdopen(descriptor, "wb")
            with output_file:
                copied = 0
                while True:
                    chunk = input_file.read(self.chunk_size)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > before.st_size:
                        raise SourceChangedError("Source grew while being copied.")
                    output_file.write(chunk)
                    digest.update(chunk)
                    if chunk_progress is not None:
                        chunk_progress(len(chunk))
                output_file.flush()
                os.fsync(output_file.fileno())
        self._copy_named_streams(
            source, destination, entry, chunk_progress
        )
        after = source.stat(follow_symlinks=False)
        if _stat_identity(before) != _stat_identity(after) or digest.hexdigest() != entry.sha256:
            raise SourceChangedError(f"Source changed while being copied: {source}")
        _copy_metadata(source, destination)

    def _copy_named_streams(
        self,
        source: Path,
        destination: Path,
        entry: ManifestEntry,
        chunk_progress: Callable[[int], None] | None = None,
    ) -> None:
        if not entry.named_streams:
            return
        if os.name != "nt":
            raise UnsupportedSourceError(
                "Windows named data streams cannot be recreated on this platform."
            )
        expected_info = tuple(
            (stream.name, stream.size) for stream in entry.named_streams
        )
        if _windows_named_stream_info(source) != expected_info:
            raise SourceChangedError(
                f"Named data streams changed before copy: {source}"
            )
        for stream in entry.named_streams:
            _validate_named_stream(stream)
            digest = hashlib.sha256()
            bytes_copied = 0
            try:
                with open(
                    _windows_stream_path(source, stream.name), "rb"
                ) as input_stream, open(
                    _windows_stream_path(destination, stream.name), "xb"
                ) as output_stream:
                    while True:
                        chunk = input_stream.read(self.chunk_size)
                        if not chunk:
                            break
                        output_stream.write(chunk)
                        digest.update(chunk)
                        bytes_copied += len(chunk)
                        if chunk_progress is not None:
                            chunk_progress(len(chunk))
                    output_stream.flush()
                    os.fsync(output_stream.fileno())
            except FileExistsError as error:
                raise VerificationError(
                    f"A named data stream appeared on staged data: "
                    f"{destination}{stream.name}"
                ) from error
            except OSError as error:
                raise UnsupportedSourceError(
                    f"Could not preserve named data stream {stream.name} from "
                    f"{source} to {destination}: {error}"
                ) from error
            if bytes_copied != stream.size or digest.hexdigest() != stream.sha256:
                raise SourceChangedError(
                    f"Named data stream {stream.name} changed while being copied: "
                    f"{source}"
                )
        if _windows_named_stream_info(source) != expected_info:
            raise SourceChangedError(
                f"Named data streams changed while being copied: {source}"
            )
        if _windows_named_stream_info(destination) != expected_info:
            raise VerificationError(
                f"Staged named data streams do not match the manifest: {destination}"
            )

    @staticmethod
    def _copy_symlink(
        source: Path, destination: Path, entry: ManifestEntry
    ) -> None:
        current_target = os.readlink(source)
        if current_target != entry.link_target:
            raise SourceChangedError(f"Symbolic link changed before copy: {source}")
        try:
            target_is_directory = source.is_dir()
            os.symlink(current_target, destination, target_is_directory=target_is_directory)
        except OSError as error:
            raise UnsupportedSourceError(
                f"Could not recreate symbolic link {source}: {error}"
            ) from error

    def _verify_content(self, path: Path, expected: Manifest, label: str) -> None:
        if not _lexists(path):
            raise VerificationError(f"The {label} is missing: {path}")
        actual = build_manifest(path, chunk_size=self.chunk_size)
        if not expected.content_matches(actual):
            raise VerificationError(f"The {label} does not match the source manifest.")

    def _verify_snapshot(self, path: Path, expected: Manifest, label: str) -> None:
        if not _lexists(path):
            raise SourceChangedError(f"The recorded {label} is missing: {path}")
        actual = build_manifest(path, chunk_size=self.chunk_size)
        matches = (
            expected.remote_snapshot_matches(actual)
            if is_remote_path(path)
            else expected.snapshot_matches(actual)
        )
        if not matches:
            raise SourceChangedError(
                f"The {label} changed after the move was planned; it was not removed."
            )

    def _create_reservation(self, record: OperationRecord) -> None:
        destination = Path(record.destination)
        if _lexists(destination):
            raise CollisionError(f"Destination already exists: {destination}")
        reservation = Path(record.reservation)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(reservation, flags, 0o600)
        except FileExistsError as error:
            if not self._clear_releasable_reservation(reservation):
                raise CollisionError(
                    f"Another safe move has reserved this destination: {destination}"
                ) from error
            try:
                descriptor = os.open(reservation, flags, 0o600)
            except FileExistsError as retry_error:
                raise CollisionError(
                    f"Another safe move reserved this destination: {destination}"
                ) from retry_error
        try:
            payload = (record.operation_id + "\n").encode("ascii")
            written = 0
            while written < len(payload):
                count = os.write(descriptor, payload[written:])
                if count <= 0:
                    raise OSError("Could not write the destination reservation.")
                written += count
            os.fsync(descriptor)
        except Exception:
            os.close(descriptor)
            try:
                reservation.unlink()
            except OSError:
                pass
            raise
        else:
            os.close(descriptor)
        _fsync_directory(reservation.parent)

    def _clear_releasable_reservation(self, reservation: Path) -> bool:
        try:
            owner = reservation.read_text(encoding="ascii").strip()
            old_record = self.journal.get(owner)
            _validate_record_paths(old_record)
        except (OSError, UnicodeError, KeyError, SafeMoveError, ValueError):
            return False
        if Path(old_record.reservation) != reservation:
            return False
        if old_record.status not in TERMINAL_STATUSES | {"backup_retained"}:
            return False
        try:
            reservation.unlink()
            _fsync_directory(reservation.parent)
        except OSError:
            return False
        return True

    def _reservation_blocks(self, destination: Path) -> bool:
        reservation = _reservation_path(destination)
        if not reservation.exists():
            return False
        if not self.journal.database_path.exists():
            return True
        try:
            owner = reservation.read_text(encoding="ascii").strip()
            record = self.journal.get(owner)
            _validate_record_paths(record)
        except (OSError, UnicodeError, KeyError, SafeMoveError, ValueError):
            return True
        return not (
            Path(record.reservation) == reservation
            and record.status in TERMINAL_STATUSES | {"backup_retained"}
        )

    def _ensure_reservation(self, record: OperationRecord) -> None:
        reservation = Path(record.reservation)
        if reservation.exists():
            try:
                owner = reservation.read_text(encoding="ascii").strip()
            except OSError as error:
                raise CollisionError(f"Cannot read destination reservation: {error}") from error
            if owner != record.operation_id:
                raise CollisionError("The destination is reserved by another operation.")
            return
        if record.status in {"planned", "copying", "verified"} and not _lexists(
            Path(record.destination)
        ):
            self._create_reservation(record)

    @staticmethod
    def _release_reservation(record: OperationRecord) -> None:
        reservation = Path(record.reservation)
        if not reservation.exists():
            return
        try:
            owner = reservation.read_text(encoding="ascii").strip()
        except OSError:
            return
        if owner == record.operation_id:
            reservation.unlink()
            _fsync_directory(reservation.parent)

    def _hit(self, phase: str, path: Path | None = None) -> None:
        if self.fault_hook is not None:
            self.fault_hook(phase, path)


def build_manifest(path: Path, *, chunk_size: int = CHUNK_SIZE) -> Manifest:
    """Create a deterministic byte-content and source-identity manifest."""
    entries: list[ManifestEntry] = []
    root_device: int | None = None

    def visit(current: Path, relative_path: str) -> None:
        nonlocal root_device
        entry = _manifest_entry(current, relative_path, chunk_size)
        if relative_path == "":
            root_device = entry.device
            if os.path.ismount(current):
                raise UnsupportedSourceError(
                    f"Filesystem mount roots cannot be moved safely: {current}"
                )
        elif entry.device != root_device or os.path.ismount(current):
            raise UnsupportedSourceError(
                f"Nested filesystem or mount boundary is not traversed: {current}"
            )
        entries.append(entry)
        if entry.kind != EntryKind.DIRECTORY:
            return
        try:
            children = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError as error:
            raise SafeMoveError(f"Cannot read directory {current}: {error}") from error
        for child in children:
            child_relative = child.name if not relative_path else f"{relative_path}/{child.name}"
            visit(Path(child.path), child_relative)

    visit(path, "")
    ordered = tuple(sorted(entries, key=lambda entry: entry.relative_path))
    return Manifest(
        entries=ordered,
        total_bytes=(
            sum(entry.size for entry in ordered if entry.kind == EntryKind.FILE)
            + sum(
                stream.size
                for entry in ordered
                for stream in entry.named_streams
            )
        ),
        digest=_manifest_digest(ordered),
    )


def _manifest_entry(path: Path, relative_path: str, chunk_size: int) -> ManifestEntry:
    kind = _entry_kind(path)
    _reject_unhandled_metadata(path, kind)
    stream_snapshot = (
        _windows_named_stream_info(path) if os.name == "nt" and kind != EntryKind.SYMLINK else ()
    )
    info = path.stat(follow_symlinks=False)
    size = 0
    sha256: str | None = None
    link_target: str | None = None
    if kind == EntryKind.FILE:
        size = info.st_size
        sha256 = _hash_stable_file(path, info, chunk_size)
        info = path.stat(follow_symlinks=False)
    elif kind == EntryKind.SYMLINK:
        link_target = os.readlink(path)
        size = info.st_size
    named_streams = tuple(
        NamedStream(
            name=stream_name,
            size=stream_size,
            sha256=_hash_stable_named_stream(
                path, stream_name, stream_size, chunk_size
            ),
        )
        for stream_name, stream_size in stream_snapshot
    )
    if (
        os.name == "nt"
        and kind != EntryKind.SYMLINK
        and _windows_named_stream_info(path) != stream_snapshot
    ):
        raise SourceChangedError(
            f"Named data streams changed while they were being scanned: {path}"
        )
    info = path.stat(follow_symlinks=False)
    return ManifestEntry(
        relative_path=relative_path,
        kind=kind.value,
        size=size,
        sha256=sha256,
        link_target=link_target,
        device=info.st_dev,
        inode=info.st_ino,
        mtime_ns=info.st_mtime_ns,
        mode=stat.S_IMODE(info.st_mode),
        named_streams=named_streams,
    )


@contextmanager
def _open_regular_source(path: Path, before: os.stat_result):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as source_file:
        opened = os.fstat(source_file.fileno())
        if not stat.S_ISREG(opened.st_mode) or _stat_identity(opened) != _stat_identity(before):
            raise SourceChangedError("Source identity changed before opening.")
        yield source_file
        if _stat_identity(os.fstat(source_file.fileno())) != _stat_identity(before):
            raise SourceChangedError("Source identity changed while open.")


def _hash_stable_file(path: Path, before: os.stat_result, chunk_size: int) -> str:
    digest = hashlib.sha256()
    try:
        with _open_regular_source(path, before) as source_file:
            read_bytes = 0
            while True:
                chunk = source_file.read(chunk_size)
                if not chunk:
                    break
                read_bytes += len(chunk)
                if read_bytes > before.st_size:
                    raise SourceChangedError("Source grew while being scanned.")
                digest.update(chunk)
    except OSError as error:
        raise SafeMoveError(f"Cannot read file {path}: {error}") from error
    after = path.stat(follow_symlinks=False)
    if _stat_identity(before) != _stat_identity(after):
        raise SourceChangedError(f"File changed while it was being scanned: {path}")
    return digest.hexdigest()


def _hash_stable_named_stream(
    path: Path,
    stream_name: str,
    expected_size: int,
    chunk_size: int,
) -> str:
    _validate_windows_stream_name(stream_name)
    digest = hashlib.sha256()
    bytes_read = 0
    stream_path = _windows_stream_path(path, stream_name)
    try:
        with open(stream_path, "rb") as source_stream:
            while True:
                chunk = source_stream.read(chunk_size)
                if not chunk:
                    break
                bytes_read += len(chunk)
                digest.update(chunk)
    except OSError as error:
        raise SafeMoveError(
            f"Cannot read named data stream {stream_name} for {path}: {error}"
        ) from error
    if bytes_read != expected_size:
        raise SourceChangedError(
            f"Named data stream {stream_name} changed while it was scanned: {path}"
        )
    return digest.hexdigest()


def _entry_kind(path: Path) -> EntryKind:
    if hasattr(os.path, "isjunction") and os.path.isjunction(path):
        raise UnsupportedSourceError(f"Windows junctions are not traversed: {path}")
    try:
        info = path.stat(follow_symlinks=False)
    except OSError as error:
        raise SafeMoveError(f"Cannot inspect {path}: {error}") from error
    if stat.S_ISLNK(info.st_mode):
        return EntryKind.SYMLINK
    if stat.S_ISREG(info.st_mode):
        return EntryKind.FILE
    if stat.S_ISDIR(info.st_mode):
        return EntryKind.DIRECTORY
    raise UnsupportedSourceError(
        f"Only regular files, directories, and symbolic links are supported: {path}"
    )


def _reject_unhandled_metadata(path: Path, kind: EntryKind) -> None:
    """Reject metadata that this engine cannot manifest and verify."""
    if kind == EntryKind.SYMLINK:
        return
    if os.name == "nt":
        # Named $DATA streams are represented explicitly in the manifest.
        return
    if not hasattr(os, "listxattr"):
        return
    try:
        attributes = os.listxattr(path, follow_symlinks=False)
    except OSError as error:
        if error.errno in {errno.ENOTSUP, errno.EOPNOTSUPP}:
            return
        raise UnsupportedSourceError(
            f"Cannot verify extended attributes for {path}: {error}"
        ) from error
    if attributes:
        raise UnsupportedSourceError(
            f"Extended attributes are not supported by this portable release: {path} "
            f"({', '.join(attributes)})"
        )


def _windows_named_stream_info(path: Path) -> tuple[tuple[str, int], ...]:
    if os.name != "nt":
        return ()
    import ctypes
    from ctypes import wintypes

    class Win32FindStreamData(ctypes.Structure):
        _fields_ = [
            ("stream_size", ctypes.c_longlong),
            ("stream_name", wintypes.WCHAR * 296),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    find_first = kernel32.FindFirstStreamW
    find_first.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(Win32FindStreamData),
        wintypes.DWORD,
    ]
    find_first.restype = wintypes.HANDLE
    find_next = kernel32.FindNextStreamW
    find_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(Win32FindStreamData)]
    find_next.restype = wintypes.BOOL
    find_close = kernel32.FindClose
    find_close.argtypes = [wintypes.HANDLE]
    find_close.restype = wintypes.BOOL

    data = Win32FindStreamData()
    handle = find_first(_windows_extended_path(path), 0, ctypes.byref(data), 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if handle == invalid_handle:
        error_code = ctypes.get_last_error()
        if error_code in {1, 38, 50, 87}:
            return ()
        raise UnsupportedSourceError(
            f"Cannot enumerate Windows data streams for {path} "
            f"(WinError {error_code})."
        )
    streams: list[tuple[str, int]] = []
    try:
        if data.stream_name != "::$DATA":
            _validate_windows_stream_name(data.stream_name)
            streams.append((data.stream_name, int(data.stream_size)))
        while find_next(handle, ctypes.byref(data)):
            if data.stream_name != "::$DATA":
                _validate_windows_stream_name(data.stream_name)
                streams.append((data.stream_name, int(data.stream_size)))
        error_code = ctypes.get_last_error()
        if error_code != 38:
            raise UnsupportedSourceError(
                f"Cannot finish enumerating Windows data streams for {path} "
                f"(WinError {error_code})."
            )
    finally:
        find_close(handle)
    ordered = tuple(sorted(streams, key=lambda item: item[0]))
    if any(size < 0 for _, size in ordered):
        raise UnsupportedSourceError(f"A named data stream has an invalid size: {path}")
    folded_names = [name.casefold() for name, _ in ordered]
    if len(folded_names) != len(set(folded_names)):
        raise UnsupportedSourceError(f"Duplicate named data streams were reported: {path}")
    return ordered


def _validate_windows_stream_name(stream_name: str) -> None:
    suffix = ":$DATA"
    if not stream_name.startswith(":") or not stream_name.endswith(suffix):
        raise VerificationError(f"Unsafe named data stream: {stream_name!r}")
    name = stream_name[1 : -len(suffix)]
    if not name or "\x00" in name or any(character in name for character in '<>:"/\\|?*'):
        raise VerificationError(f"Unsafe named data stream: {stream_name!r}")


def _validate_named_stream(stream: NamedStream) -> None:
    _validate_windows_stream_name(stream.name)
    if stream.size < 0:
        raise VerificationError("A named data stream has an invalid size.")
    if len(stream.sha256) != 64 or any(
        character not in "0123456789abcdef" for character in stream.sha256
    ):
        raise VerificationError("A named data stream has an invalid SHA-256 digest.")


def _windows_stream_path(path: Path, stream_name: str) -> str:
    _validate_windows_stream_name(stream_name)
    return _windows_extended_path(path) + stream_name


def _manifest_digest(entries: Iterable[ManifestEntry]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        payload = json.dumps(
            entry.snapshot_identity(), ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _named_stream_additions_only(
    previous: Manifest,
    current: Manifest,
    *,
    remote_source: bool,
) -> tuple[str, ...] | None:
    """Return newly attached streams when every previously recorded byte is unchanged."""
    if len(previous.entries) != len(current.entries):
        return None
    additions: list[str] = []
    for old, new in zip(previous.entries, current.entries, strict=True):
        old_primary = (
            old.relative_path,
            old.kind,
            old.size,
            old.sha256,
            old.link_target,
            old.mode,
        )
        new_primary = (
            new.relative_path,
            new.kind,
            new.size,
            new.sha256,
            new.link_target,
            new.mode,
        )
        if old_primary != new_primary:
            return None
        if not remote_source and (old.device, old.inode) != (new.device, new.inode):
            return None
        old_streams = {stream.name.casefold(): stream for stream in old.named_streams}
        new_streams = {stream.name.casefold(): stream for stream in new.named_streams}
        if not old_streams.keys() <= new_streams.keys():
            return None
        if any(
            old_stream.identity() != new_streams[name].identity()
            for name, old_stream in old_streams.items()
        ):
            return None
        entry_additions = [
            stream
            for name, stream in new_streams.items()
            if name not in old_streams
        ]
        if not entry_additions and old.mtime_ns != new.mtime_ns:
            return None
        for stream in sorted(entry_additions, key=lambda item: item.name):
            relative = old.relative_path or "."
            additions.append(f"{relative}{stream.name}")
    return tuple(additions) if additions else None


def _entry_by_path(manifest: Manifest, relative_path: str) -> ManifestEntry:
    for entry in manifest.entries:
        if entry.relative_path == relative_path:
            return entry
    raise VerificationError(f"Manifest entry is missing: {relative_path!r}")


def _relative_path(relative_path: str) -> Path:
    if not relative_path:
        return Path()
    parts = relative_path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise VerificationError(f"Unsafe relative path in manifest: {relative_path!r}")
    return Path(*parts)


def _copy_metadata(source: Path, destination: Path) -> None:
    try:
        shutil.copystat(source, destination, follow_symlinks=False)
    except OSError as error:
        raise SafeMoveError(
            f"Could not preserve basic timestamps/permissions for {source}: {error}"
        ) from error


def _commit_no_replace(staging: Path, destination: Path) -> None:
    if _lexists(destination):
        raise CollisionError(f"Destination appeared before commit: {destination}")
    if _atomic_rename_no_replace(staging, destination):
        _fsync_directory(destination.parent)
        if staging.parent != destination.parent:
            _fsync_directory(staging.parent)
        return

    root_kind = _entry_kind(staging)
    if root_kind not in {EntryKind.FILE, EntryKind.SYMLINK}:
        raise OperationStateError(
            "This platform/filesystem cannot atomically commit a directory without "
            "risking replacement. Staging and source were retained."
        )
    try:
        os.link(staging, destination, follow_symlinks=False)
    except FileExistsError as error:
        raise CollisionError(f"Destination appeared before commit: {destination}") from error
    except (OSError, NotImplementedError) as error:
        raise OperationStateError(
            "This platform/filesystem provides neither exclusive rename nor a safe "
            "hard-link fallback. Staging and source were retained."
        ) from error
    # Make the additional name durable before removing the old name. A crash
    # therefore leaves either both names or at least the intended new name.
    _fsync_directory(destination.parent)
    staging.unlink()
    _fsync_directory(staging.parent)


def _atomic_rename_no_replace(source: Path, destination: Path) -> bool:
    """Atomically rename without replacement; return False if unavailable."""
    if os.name == "nt":
        _windows_rename_no_replace(source, destination)
        return True

    if sys.platform.startswith("linux"):
        return _linux_rename_no_replace(source, destination)
    if sys.platform == "darwin":
        return _darwin_rename_no_replace(source, destination)
    return False


def _windows_rename_no_replace(source: Path, destination: Path) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    move_file = kernel32.MoveFileExW
    move_file.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    move_file.restype = wintypes.BOOL
    movefile_write_through = 0x00000008
    error_number = 0
    transient_errors = {5, 32, 33}
    for attempt in range(8):
        succeeded = move_file(
            _windows_extended_path(source),
            _windows_extended_path(destination),
            movefile_write_through,
        )
        if succeeded:
            return
        error_number = ctypes.get_last_error()
        if error_number in {80, 183}:
            raise CollisionError(f"Destination appeared before commit: {destination}")
        if error_number not in transient_errors or attempt == 7:
            break
        time.sleep(min(0.05 * (2**attempt), 0.4))
    raise OSError(
        error_number,
        ctypes.FormatError(error_number),
        str(source),
        str(destination),
    )


def _windows_extended_path(path: Path) -> str:
    value = os.path.abspath(path)
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value


def _linux_rename_no_replace(source: Path, destination: Path) -> bool:
    import ctypes

    library = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(library, "renameat2", None)
    if renameat2 is None:
        return False
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    at_current_working_directory = -100
    rename_no_replace = 1
    result = renameat2(
        at_current_working_directory,
        os.fsencode(source),
        at_current_working_directory,
        os.fsencode(destination),
        rename_no_replace,
    )
    if result == 0:
        return True
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise CollisionError(f"Destination appeared before commit: {destination}")
    if error_number in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
        return False
    raise OSError(
        error_number,
        os.strerror(error_number),
        str(source),
        str(destination),
    )


def _darwin_rename_no_replace(source: Path, destination: Path) -> bool:
    import ctypes

    library = ctypes.CDLL(None, use_errno=True)
    renamex = getattr(library, "renamex_np", None)
    if renamex is None:
        return False
    renamex.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    renamex.restype = ctypes.c_int
    rename_exclusive = 0x00000004
    result = renamex(
        os.fsencode(source),
        os.fsencode(destination),
        rename_exclusive,
    )
    if result == 0:
        return True
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise CollisionError(f"Destination appeared before commit: {destination}")
    if error_number in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
        return False
    raise OSError(
        error_number,
        os.strerror(error_number),
        str(source),
        str(destination),
    )


def _choose_destination(
    requested: Path,
    policy: ConflictPolicy,
    *,
    reservation_blocks: Callable[[Path], bool] | None = None,
) -> Path:
    is_reserved = reservation_blocks or (
        lambda candidate: _reservation_path(candidate).exists()
    )
    if not _lexists(requested) and not is_reserved(requested):
        return requested
    if policy == ConflictPolicy.FAIL:
        raise CollisionError(f"Destination already exists or is reserved: {requested}")
    stem = requested.stem
    suffix = requested.suffix
    for number in range(1, 100_000):
        candidate = requested.with_name(f"{stem} ({number}){suffix}")
        if not _lexists(candidate) and not is_reserved(candidate):
            return candidate
    raise CollisionError("Could not find an unused destination name.")


def _reservation_path(destination: Path) -> Path:
    key = hashlib.sha256(str(destination).encode("utf-8")).hexdigest()[:16]
    return destination.parent / f".safemove-{key}.lock"


def _validate_target_name(name: str) -> None:
    if not name or name in {".", ".."}:
        raise InvalidMoveError("The destination name is empty or reserved.")
    if Path(name).name != name or "/" in name or "\\" in name:
        raise InvalidMoveError("The destination name must be one filename, not a path.")
    if "\x00" in name:
        raise InvalidMoveError("The destination name contains a null character.")
    if os.name == "nt" and Path(name).is_reserved():
        raise InvalidMoveError(f"Windows reserves the destination name {name!r}.")
    if os.name == "nt":
        forbidden = '<>:"/\\|?*'
        if any(character in forbidden or ord(character) < 32 for character in name):
            raise InvalidMoveError(
                "The destination name contains characters Windows does not allow."
            )
        if name.endswith((" ", ".")):
            raise InvalidMoveError(
                "Windows destination names cannot end with a space or period."
            )


def _validate_managed_path(path: Path, operation_id: str, ending: str) -> None:
    if operation_id not in path.name or not path.name.endswith(ending):
        raise OperationStateError(f"Refusing to remove an unmanaged path: {path}")


def _validate_record_paths(record: OperationRecord) -> None:
    source = Path(record.source)
    destination = Path(record.destination)
    expected_staging = destination.parent / f".safemove-{record.operation_id}.partial"
    expected_backup = source.parent / f".safemove-{record.operation_id}.recovery"
    expected_reservation = _reservation_path(destination)
    if Path(record.staging) != expected_staging:
        raise OperationStateError("The journal contains an unsafe staging path.")
    if Path(record.backup) != expected_backup:
        raise OperationStateError("The journal contains an unsafe recovery path.")
    if Path(record.reservation) != expected_reservation:
        raise OperationStateError("The journal contains an unsafe reservation path.")


def _remove_path(path: Path) -> None:
    kind = _entry_kind(path)
    if kind == EntryKind.DIRECTORY:
        shutil.rmtree(path)
    else:
        path.unlink()


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def is_remote_path(path: Path | str) -> bool:
    """Return whether Windows classifies the path's root as a remote drive."""
    if os.name != "nt":
        return False
    value = os.path.abspath(os.fspath(path))
    if value.startswith("\\\\"):
        return True
    return _windows_drive_type(Path(value)) == 4


def _windows_drive_type(path: Path) -> int:
    if os.name != "nt":
        return 0
    import ctypes
    from ctypes import wintypes

    root = path.anchor
    if not root:
        return 0
    if not root.endswith("\\"):
        root += "\\"
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_drive_type = kernel32.GetDriveTypeW
    get_drive_type.argtypes = [wintypes.LPCWSTR]
    get_drive_type.restype = wintypes.UINT
    return int(get_drive_type(root))


def _canonicalize_windows_network_path(path: Path) -> Path:
    """Convert a mapped-drive path to its UNC identity without resolving links."""
    absolute = _absolute_without_resolving(path)
    if os.name != "nt" or str(absolute).startswith("\\\\"):
        return absolute
    if _windows_drive_type(absolute) != 4:
        return absolute

    import ctypes
    from ctypes import wintypes

    mpr = ctypes.WinDLL("mpr", use_last_error=True)
    get_connection = mpr.WNetGetConnectionW
    get_connection.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    get_connection.restype = wintypes.DWORD
    drive, remainder = os.path.splitdrive(str(absolute))
    if not drive:
        return absolute
    remote_buffer = ctypes.create_unicode_buffer(32768)
    buffer_size = wintypes.DWORD(len(remote_buffer))
    result = get_connection(drive, remote_buffer, ctypes.byref(buffer_size))
    if result != 0:
        return absolute
    remote_root = remote_buffer.value.rstrip("\\")
    if not remote_root:
        return absolute
    return _absolute_without_resolving(Path(remote_root + remainder))


def _same_lexical_path(first: Path, second: Path) -> bool:
    return os.path.normcase(os.path.abspath(first)) == os.path.normcase(
        os.path.abspath(second)
    )


def _same_file_if_possible(first: Path, second: Path) -> bool:
    try:
        return os.path.samefile(first, second)
    except OSError:
        return False


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _stat_identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        stat.S_IMODE(info.st_mode),
    )


def _stat_matches_entry(info: os.stat_result, entry: ManifestEntry) -> bool:
    return (
        info.st_dev == entry.device
        and info.st_ino == entry.inode
        and info.st_size == entry.size
        and info.st_mtime_ns == entry.mtime_ns
        and stat.S_IMODE(info.st_mode) == entry.mode
    )
