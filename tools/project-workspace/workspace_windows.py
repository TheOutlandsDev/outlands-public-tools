"""Public MIT Windows guards for private workspace creation.

Sampled checks require trusted stable local parents. This is not an atomic
filesystem transaction, access-control audit or all-stream backup.
"""
from __future__ import annotations
from contextlib import contextmanager
import ctypes
from ctypes import wintypes as w
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


@contextmanager
def regular(value, error, *, single_link=False, maximum=None):
    """Keep the primary leaf and ancestors while a checked CRT fd is read."""
    import msvcrt

    path = selected_path(value, _core(error))
    native = Native(_core(error))
    owned, fd = None, None
    with Chain(native, path.parent) as chain:
        try:
            expected = chain.items[-1][2].rstrip("\\") + "\\" + path.name
            owned, identity, final = native.open(path, False, expected)
            if single_link and identity[3] != 1:
                raise error("CONTROL_NOT_SINGLE_LINK")
            if maximum is not None and identity[4] > maximum:
                raise error("INPUT_SIZE_LIMIT")
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


def checked_path(value, error):
    path = selected_path(value, _core(error))
    native = Native(_core(error))
    with Chain(native, path.parent) as parent:
        try:
            info = path.lstat()
        except FileNotFoundError:
            return path
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & REPARSE:
            raise error("LINKED_PATH")
        parent.verify()
    return path


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_bounded(value, maximum, error, *, expected=None, single_link=False, budget=None):
    path = selected_path(value, _core(error))
    with regular(path, error, single_link=single_link, maximum=maximum) as fd:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise error("INPUT_NOT_REGULAR")
        if expected is not None and identity(before) != identity(expected):
            raise error("INPUT_CHANGED")
        if before.st_size > maximum:
            raise error("INPUT_SIZE_LIMIT")
        chunks, size = [], 0
        while True:
            amount = min(65536, maximum + 1 - size)
            if budget is not None:
                amount = min(amount, max(0, budget[0]) + 1)
            block = os.read(fd, amount)
            if not block:
                break
            if budget is not None:
                budget[0] -= len(block)
                if budget[0] < 0:
                    raise error("TOTAL_BYTE_LIMIT")
            size += len(block)
            if size > maximum:
                raise error("INPUT_SIZE_LIMIT")
            chunks.append(block)
        after = os.fstat(fd)
        if (size != before.st_size or identity(before) != identity(after)
                or before.st_ctime_ns != after.st_ctime_ns
                or identity(path.lstat()) != identity(after)):
            raise error("INPUT_CHANGED")
        return b"".join(chunks)


@contextmanager
def root_scope(value, error):
    path = selected_path(value, _core(error))
    with Chain(Native(_core(error)), path) as chain:
        chain.verify()
        yield path
        chain.verify()


@contextmanager
def fresh_directory(value, error):
    """Create exclusively, then retain the observed directory until exit."""
    path = selected_path(value, _core(error))
    native = Native(_core(error))
    with Chain(native, path.parent) as parent:
        parent.verify()
        path.mkdir()
        owned, identity, final = native.open(
            path, True, parent.items[-1][2].rstrip("\\") + "\\" + path.name)
        try:
            parent.verify()
            yield path
            current, name = native.describe(owned, True)
            if current != identity or name.casefold() != final.casefold():
                raise error("OUTPUT_CHANGED")
            parent.verify()
        finally:
            native.close(owned)
