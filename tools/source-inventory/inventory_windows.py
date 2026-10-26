"""Windows local-volume guards for the public Source Inventory.

Adapted from public MIT native mechanisms in this collection. These sampled
checks require trusted, quiescent paths; they are not a hostile-filesystem VFS.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes as w
import hashlib
import os
from pathlib import Path
import re
import stat

RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit for prefix in ("com", "lpt") for digit in "123456789\u00b9\u00b2\u00b3"
}
DIRECTORY = 0x10
REPARSE = 0x400
INVALID_HANDLE = ctypes.c_void_p(-1).value


class FileInfo(ctypes.Structure):
    _fields_ = [
        ("attributes", w.DWORD),
        ("created", w.FILETIME),
        ("accessed", w.FILETIME),
        ("written", w.FILETIME),
        ("volume", w.DWORD),
        ("size_high", w.DWORD),
        ("size_low", w.DWORD),
        ("links", w.DWORD),
        ("index_high", w.DWORD),
        ("index_low", w.DWORD),
    ]


def _time(value):
    return value.dwHighDateTime << 32 | value.dwLowDateTime


class Native:
    """Sampled metadata checks; retain handles without delete sharing."""

    def __init__(self, core):
        self.core = core
        if os.name != "nt":
            raise core["Rejected"]("WINDOWS_API_UNAVAILABLE")
        try:
            self.dll = ctypes.WinDLL("kernel32", use_last_error=True)
            signatures = {
                "CreateFileW": (
                    [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE],
                    w.HANDLE,
                ),
                "CloseHandle": ([w.HANDLE], w.BOOL),
                "GetDriveTypeW": ([w.LPCWSTR], w.UINT),
                "GetFileInformationByHandle": (
                    [w.HANDLE, ctypes.POINTER(FileInfo)],
                    w.BOOL,
                ),
                "GetFileType": ([w.HANDLE], w.DWORD),
                "GetFinalPathNameByHandleW": (
                    [w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD],
                    w.DWORD,
                ),
            }
            for name, (arguments, result) in signatures.items():
                function = getattr(self.dll, name)
                function.argtypes, function.restype = arguments, result
        except (OSError, AttributeError, TypeError):
            raise core["Rejected"]("WINDOWS_API_UNAVAILABLE") from None

    def fail(self, code):
        raise self.core["EntryFailure"](code) from None

    def close(self, handle):
        if not self.dll.CloseHandle(handle):
            self.fail("READ_ERROR")

    def describe(self, handle, directory):
        info = FileInfo()
        if self.dll.GetFileType(handle) != 1 or not self.dll.GetFileInformationByHandle(
            handle, ctypes.byref(info)
        ):
            self.fail("UNSAFE_FILE")
        if info.attributes & REPARSE:
            self.fail("LINKED_PATH")
        if bool(info.attributes & DIRECTORY) != directory:
            self.fail("DIRECTORY_REQUIRED" if directory else "NONREGULAR_INPUT")
        index = info.index_high << 32 | info.index_low
        if not index or (not directory and info.links < 1):
            self.fail("UNSAFE_FILE")
        buffer = ctypes.create_unicode_buffer(32768)
        # Normalized NT volume names avoid reliance on a DOS mount-manager lookup.
        size = self.dll.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 2)
        if not size or size >= len(buffer):
            self.fail("UNSAFE_PATH")
        final = buffer.value
        if (
            re.match(r"\\Device\\HarddiskVolume[0-9]+(?:\\|$)", final, re.IGNORECASE)
            is None
        ):
            self.fail("UNSAFE_PATH")
        identity = (info.volume, index, info.attributes)
        if not directory:
            identity += (
                info.links,
                info.size_high << 32 | info.size_low,
                _time(info.created),
                _time(info.written),
            )
        return identity, final

    def open(self, path, directory, expected=None):
        if path == Path(path.anchor) and self.dll.GetDriveTypeW(str(path)) not in (2, 3):
            self.fail("LOCAL_VOLUME_REQUIRED")
        access = 0x80 if directory else 0x80000000
        # Permit cooperative data writers; deny ordinary deletion/rename while held.
        handle = self.dll.CreateFileW(
            "\\\\?\\" + str(path), access, 3, None, 3, 0x02200000, None
        )
        if handle == INVALID_HANDLE:
            error = ctypes.get_last_error()
            self.fail(
                "MISSING"
                if error in (2, 3)
                else "UNSAFE_PATH"
                if error in (123, 206)
                else "READ_ERROR"
            )
        try:
            identity, final = self.describe(handle, directory)
            if expected is not None and final.casefold() != expected.casefold():
                # Refuse short-name aliases and observed ancestry changes.
                self.fail("UNSAFE_PATH")
            return handle, identity, final
        except BaseException:
            self.close(handle)
            raise


def _component(part):
    return (
        bool(part)
        and len(part) <= 255
        and not part.endswith((".", " "))
        and part.split(".")[0].rstrip(" ").casefold() not in RESERVED
        and not any(c in '\\/:<>"|?*' or ord(c) < 32 or ord(c) == 127 for c in part)
        and part not in (".", "..")
    )


def selected_path(value, core):
    try:
        raw = os.fspath(value)
        if (
            type(raw) is not str
            or not 0 < len(raw) <= 4096
            or raw.startswith(("\\\\", "//"))
        ):
            raise core["Rejected"]("PATH_INVALID")
        raw.encode("utf-16-le")
        path = Path(raw)
        if (path.root and not path.drive) or ".." in path.parts or (path.drive and not path.is_absolute()):
            raise core["Rejected"]("PATH_INVALID")
        if any(not _component(part) for part in path.parts if part != path.anchor):
            raise core["Rejected"]("PATH_INVALID")
        path = path.absolute()
        if (
            re.fullmatch(r"[A-Za-z]:", path.drive) is None
            or len(path.parts) > 64
            or len(str(path)) > 4096
        ):
            raise core["Rejected"]("PATH_INVALID")
        if any(not _component(part) for part in path.parts if part != path.anchor):
            raise core["Rejected"]("PATH_INVALID")
        return path
    except (OSError, ValueError, TypeError):
        raise core["Rejected"]("PATH_INVALID") from None


class Chain:
    """Retain and recheck ordinary directory ancestors."""

    def __init__(self, native, path):
        self.native, self.path, self.items = native, path, []

    def __enter__(self):
        try:
            current = Path(self.path.anchor)
            item = self.native.open(current, True)
            self.items.append(item)
            for part in self.path.parts[1:]:
                current /= part
                expected = self.items[-1][2].rstrip("\\") + "\\" + part
                self.items.append(self.native.open(current, True, expected))
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        failure = None
        while self.items:
            try:
                self.native.close(self.items.pop()[0])
            except BaseException as error:
                failure = failure or error
        if failure is not None:
            raise failure

    def verify(self):
        for handle, identity, final in self.items:
            current, name = self.native.describe(handle, True)
            if current != identity or name.casefold() != final.casefold():
                self.native.fail("SOURCE_CHANGED")



def _core(error):
    return {"Rejected": error, "EntryFailure": error}


def checked_directory(value, error):
    path = selected_path(value, _core(error))
    with Chain(Native(_core(error)), path) as chain:
        chain.verify()
    return path


def _inside(child, parent):
    child, parent = child.casefold().rstrip("\\"), parent.casefold().rstrip("\\")
    return child == parent or child.startswith(parent + "\\")


@contextmanager
def boundaries(root, output, error):
    root = selected_path(root, _core(error))
    output = selected_path(output, _core(error))
    if root.parent == root:
        raise error("FILESYSTEM_ROOT_REJECTED")
    native = Native(_core(error))
    with Chain(native, root) as source, Chain(native, output) as reports:
        if _inside(reports.items[-1][2], source.items[-1][2]):
            raise error("OUTPUT_INSIDE_INPUT")
        source.verify()
        reports.verify()
        yield root, output
        source.verify()
        reports.verify()


def walk(root, *, topdown, followlinks, onerror, error):
    """One-level os.walk calls: acquire each directory before enumeration.

    The caller still filters the yielded mutable directory list. No second
    inventory/tree traversal is performed; stack growth remains entry-bounded.
    """
    if not topdown or followlinks:
        raise error("INVALID_WALK")
    native = Native(_core(error))
    stack = [selected_path(root, _core(error))]
    while stack:
        here = stack.pop()
        with Chain(native, here) as chain:
            chain.verify()
            iterator = os.walk(here, topdown=True, followlinks=False, onerror=onerror)
            try:
                entry = next(iterator, None)
                if entry is None:
                    raise error("SOURCE_SCAN_FAILED")
                current, directories, files = entry
                if Path(current) != here:
                    raise error("SOURCE_CHANGED")
                yield current, directories, files
                chain.verify()
                for name in reversed(directories):
                    if not _component(name):
                        raise error("PATH_INVALID")
                    stack.append(selected_path(here / name, _core(error)))
            finally:
                close = getattr(iterator, "close", None)
                if close is not None:
                    close()


@contextmanager
def regular(value, error):
    """Keep the primary leaf and ancestors while a checked CRT fd is read."""
    import msvcrt

    path = selected_path(value, _core(error))
    native = Native(_core(error))
    owned, fd = None, None
    with Chain(native, path.parent) as chain:
        try:
            expected = chain.items[-1][2].rstrip("\\") + "\\" + path.name
            owned, identity, final = native.open(path, False, expected)
            fd = os.open(path, os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT)
            os.set_inheritable(fd, False)
            actual, name = native.describe(msvcrt.get_osfhandle(fd), False)
            if actual != identity or name.casefold() != final.casefold():
                raise error("SOURCE_CHANGED")
            chain.verify()
            yield fd
            actual, name = native.describe(msvcrt.get_osfhandle(fd), False)
            primary, primary_name = native.describe(owned, False)
            if actual != identity or primary != identity or name.casefold() != final.casefold() or primary_name.casefold() != final.casefold():
                raise error("SOURCE_CHANGED")
            chain.verify()
        finally:
            try:
                if fd is not None:
                    os.close(fd)
            finally:
                if owned is not None:
                    native.close(owned)


def hash_file(path, expected, limit, error, identity, descriptor_identity):
    with regular(path, error) as fd:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or identity(before) != identity(expected):
            raise error("SOURCE_CHANGED")
        digest, actual = hashlib.sha256(), 0
        while True:
            block = os.read(fd, min(65536, limit + 1 - actual))
            if not block:
                break
            actual += len(block)
            if actual > limit:
                raise error("FILE_BYTE_LIMIT")
            digest.update(block)
        after = os.fstat(fd)
        if actual != before.st_size or descriptor_identity(before) != descriptor_identity(after) or identity(Path(path).lstat()) != identity(after):
            raise error("SOURCE_CHANGED")
        return digest.hexdigest().upper()


@contextmanager
def new_directory(value, error):
    path = selected_path(value, _core(error))
    native = Native(_core(error))
    with Chain(native, path.parent) as parent:
        parent.verify()
        try:
            os.mkdir(path, 0o700)
        except FileExistsError:
            raise error("OUTPUT_EXISTS") from None
        # Creation and opening are separate: stable trusted parents are required.
        handle, identity, final = native.open(path, True, parent.items[-1][2].rstrip("\\") + "\\" + path.name)
        try:
            yield path
            actual, name = native.describe(handle, True)
            if actual != identity or name.casefold() != final.casefold():
                raise error("OUTPUT_CHANGED")
            parent.verify()
        finally:
            native.close(handle)


def exclusive_write(value, data, error):
    """Create only a new file; retain partial/unconfirmed output on failure."""
    import msvcrt

    if type(data) is not bytes:
        raise error("INVALID_OUTPUT")
    path = selected_path(value, _core(error))
    native = Native(_core(error))
    with Chain(native, path.parent) as parent:
        parent.verify()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_BINARY | os.O_NOINHERIT, 0o600)
        try:
            os.set_inheritable(fd, False)
            handle = msvcrt.get_osfhandle(fd)
            previous, final = native.describe(handle, False)
            expected = parent.items[-1][2].rstrip("\\") + "\\" + path.name
            if previous[3] != 1 or previous[4] != 0 or final.casefold() != expected.casefold():
                raise error("OUTPUT_CHANGED")
            position = 0
            while position < len(data):
                block = data[position:position + 65536]
                written = os.write(fd, block)
                if not 0 < written <= len(block):
                    raise error("OUTPUT_IO_ERROR")
                position += written
            os.fsync(fd)
            actual, name = native.describe(handle, False)
            if actual[:4] != previous[:4] or actual[4] != len(data) or actual[5] != previous[5] or name.casefold() != final.casefold():
                raise error("OUTPUT_CHANGED")
            parent.verify()
        finally:
            os.close(fd)
