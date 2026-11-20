"""Original revision inventory and active-pointer integrity assertions."""

from zipfile import ZipFile

import pytest

from examples.make_demo_archive import make_demo_archive
from revision_archive import ArchiveError, verify_archive, verify_revision


def test_revision_inventory_is_bounded_and_hash_verified(tmp_path):
    root = tmp_path / "archive"
    _, pending = make_demo_archive(root)
    candidate = root / "candidates"
    with ZipFile(candidate / f"{pending}.xlsx") as workbook:
        assert workbook.testzip() is None
    revision = verify_revision(candidate, pending)
    assert verify_archive(root, limit=1).revisions == (revision,)
    with pytest.raises(ArchiveError, match="between 1 and 100"):
        verify_archive(root, limit=101)
    (candidate / f"{pending}.xlsx").write_bytes(b"tampered")
    with pytest.raises(ArchiveError, match="checksum validation"):
        verify_revision(candidate, pending)


def test_active_revision_fails_closed_after_stored_content_tamper(tmp_path):
    root = tmp_path / "archive"
    active, _ = make_demo_archive(root)
    assert verify_archive(root, limit=1).active_revision_sha256 == active
    (root / "candidates" / f"{active}.xlsx").write_bytes(b"tampered")
    with pytest.raises(ArchiveError, match="checksum validation"):
        verify_archive(root, limit=1)
