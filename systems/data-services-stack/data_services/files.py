"""Explicit bounded file operations through the reviewed public I/O backend."""
from contextlib import contextmanager
import os
from pathlib import Path

from .contracts import StackError
from .vendor import transfer

APPLICATION = Path(__file__).resolve().parents[1]
PROTECTED = APPLICATION
for _parent in APPLICATION.parents:
    if (_parent / ".git").exists():
        PROTECTED = _parent
        break
# Source snapshots remain unchanged. Their trusted application boundary is
# supplied here so both collection and standalone installations are protected.
transfer.REPOSITORY = PROTECTED


@contextmanager
def errors():
    try:
        yield
    except StackError:
        raise
    except (transfer.TransferError, OSError, UnicodeError):
        raise StackError("FILESYSTEM_REFUSED") from None


def selected(value, *, output=False):
    with errors():
        path = transfer.selected_path(value, output=output)
        if output and (path.is_relative_to(APPLICATION) or path.is_relative_to(PROTECTED)):
            raise StackError("PRIVATE_STATE_INSIDE_SOURCE")
        return path


@contextmanager
def directory(path):
    with errors(), transfer._root_scope(path):
        yield


def entries(path, maximum):
    with errors(), transfer._entries(path) as values:
        result = []
        for item in values:
            if len(result) >= maximum:
                raise StackError("DIRECTORY_ENTRY_LIMIT")
            result.append(item.name)
        return sorted(result)


def read(path, maximum):
    with errors():
        return transfer.checked_file(path, collect=True, max_bytes=maximum)[1]


def write_new(path, raw):
    with errors():
        transfer.write_new(path, raw)
        # POSIX directory fsync adds directory-entry persistence. Windows file
        # handles are flushed by the public writer; power-loss guarantees vary.
        if os.name != "nt":
            fd = os.open(Path(path).parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)


def mkdir(path):
    with errors():
        return transfer.new_destination(path)


def identity(path):
    with errors():
        info = Path(path).lstat()
        transfer.check_type(info, directory=True)
        return info.st_dev, info.st_ino


def remove_empty_lock(root, expected=None):
    """Remove only this fixed empty coordination directory, never recursively."""
    root = selected(root, output=True)
    lock = root / ".writer-lock"
    if lock.parent != root or lock.name != ".writer-lock":
        raise StackError("LOCK_REFUSED")
    with directory(root):
        before = identity(lock)
        if expected is not None and before != expected:
            raise StackError("LOCK_CHANGED")
        if entries(lock, 1):
            raise StackError("LOCK_NOT_EMPTY")
        if identity(lock) != before:
            raise StackError("LOCK_CHANGED")
        with errors():
            lock.rmdir()
