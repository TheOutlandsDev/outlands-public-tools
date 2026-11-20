"""Verify saved order revision workbooks, metadata, and the active pointer."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


MAX_WORKBOOK_BYTES = 25 * 1024 * 1024
MAX_METADATA_BYTES = 1024 * 1024
MAX_REVISIONS = 1000
DIGEST = re.compile(r"[0-9a-f]{64}")


class ArchiveError(ValueError):
    """The saved archive failed an integrity check."""


class RevisionMetadata(BaseModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    original_filename: str = Field(min_length=1, max_length=180)
    size_bytes: int = Field(gt=0, le=MAX_WORKBOOK_BYTES)
    uploaded_at: AwareDatetime
    status: str = Field(pattern=r"^(PENDING_REVIEW|ACTIVE|RETIRED)$")

    model_config = ConfigDict(frozen=True)


class ActivePointer(BaseModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    activated_at: AwareDatetime | None = None

    model_config = ConfigDict(extra="forbid")


class ArchiveReport(BaseModel):
    verified_revision_count: int
    active_revision_sha256: str | None
    revisions: tuple[RevisionMetadata, ...]


def _is_reparse_point(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _ordinary_directory(path: Path, *, optional: bool = False) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        if optional:
            return False
        raise ArchiveError("The archive directory is missing") from None
    if not stat.S_ISDIR(info.st_mode) or _is_reparse_point(info):
        raise ArchiveError("Archive directories must be ordinary directories")
    return True


def _ordinary_file(info: os.stat_result) -> bool:
    return stat.S_ISREG(info.st_mode) and not _is_reparse_point(info)


def _read_file(path: Path, limit: int, *, optional: bool = False) -> bytes | None:
    try:
        selected = path.lstat()
    except FileNotFoundError:
        if optional:
            return None
        raise ArchiveError("A required archive file is missing") from None

    if not _ordinary_file(selected) or selected.st_size > limit:
        raise ArchiveError("Archive files must be ordinary files within the size limit")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not _ordinary_file(opened) or not os.path.samestat(selected, opened):
            raise ArchiveError("An archive file changed while opening")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if len(data) > limit or opened.st_size != after.st_size or opened.st_mtime_ns != after.st_mtime_ns:
        raise ArchiveError("An archive file changed while reading or exceeds the size limit")
    return data


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ArchiveError("Archive JSON contains duplicate fields")
    return fields


def _invalid_number(_value: str) -> object:
    raise ArchiveError("Archive JSON contains an invalid number")


def _read_json(data: bytes) -> object:
    return json.loads(
        data.decode("utf-8"), object_pairs_hook=_unique_fields, parse_constant=_invalid_number,
    )


def verify_revision(candidates: Path, digest: str) -> RevisionMetadata:
    if not DIGEST.fullmatch(digest):
        raise ArchiveError("Invalid revision identity")
    metadata_data = _read_file(candidates / f"{digest}.json", MAX_METADATA_BYTES)
    content = _read_file(candidates / f"{digest}.xlsx", MAX_WORKBOOK_BYTES)
    if sha256(content).hexdigest() != digest:
        raise ArchiveError("The stored order revision failed checksum validation")
    metadata = RevisionMetadata.model_validate(_read_json(metadata_data))
    if (metadata.sha256, metadata.size_bytes) != (digest, len(content)):
        raise ArchiveError("Revision metadata does not match the workbook")
    return metadata


def _candidate_ids(candidates: Path) -> set[str]:
    ids: set[str] = set()
    if not _ordinary_directory(candidates, optional=True):
        return ids
    for path in candidates.iterdir():
        if path.suffix.lower() not in {".xlsx", ".json"}:
            continue
        if path.suffix not in {".xlsx", ".json"} or not DIGEST.fullmatch(path.stem):
            raise ArchiveError("Invalid revision archive filename")
        ids.add(path.stem)
        if len(ids) > MAX_REVISIONS:
            raise ArchiveError("The archive exceeds the revision count limit")
    return ids


def verify_archive(root: Path, *, limit: int = 20) -> ArchiveReport:
    if not 1 <= limit <= 100:
        raise ArchiveError("Revision list limit must be between 1 and 100")
    _ordinary_directory(root)
    candidates = root / "candidates"
    records = {digest: verify_revision(candidates, digest) for digest in sorted(_candidate_ids(candidates))}

    active = _read_file(root / "active.json", MAX_METADATA_BYTES, optional=True)
    active_revision_sha256 = None
    if active is not None:
        pointer = ActivePointer.model_validate(_read_json(active))
        if pointer.sha256 not in records:
            raise ArchiveError("The active pointer does not reference a verified revision")
        active_revision_sha256 = pointer.sha256

    ordered = sorted(records.values(), key=lambda row: (row.uploaded_at, row.sha256), reverse=True)
    return ArchiveReport(
        verified_revision_count=len(records), active_revision_sha256=active_revision_sha256,
        revisions=tuple(ordered[:limit]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Directory with candidates and an optional active.json")
    parser.add_argument("--limit", type=int, default=20, help="Maximum displayed revisions, from 1 to 100")
    args = parser.parse_args()
    try:
        report = verify_archive(args.archive, limit=args.limit)
    except ArchiveError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("Invalid or unreadable revision archive", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((report.model_dump_json() + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
