"""Sampled Windows path and regular-file guards for the public mover.

Adapted from this MIT collection's public native input mechanisms. SQLite and
mutation operations still require stable trusted parents; this is not a sandbox.
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
    prefix + digit
    for prefix in ("com", "lpt")
    for digit in "123456789\u00b9\u00b2\u00b3"
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


class TagInfo(ctypes.Structure):
    _fields_ = [("attributes", w.DWORD), ("tag", w.DWORD)]


def _time(value):
    return value.dwHighDateTime << 32 | value.dwLowDateTime


class Native:
    """Native bindings and explicit handle ownership; fixed errors only."""

    def __init__(self, core, allow_remote=False):
        self.core = core
        self.allow_remote = allow_remote
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
                "WriteFile": (
                    [w.HANDLE, w.LPCVOID, w.DWORD, ctypes.POINTER(w.DWORD), w.LPVOID],
                    w.BOOL,
                ),
                "FlushFileBuffers": ([w.HANDLE], w.BOOL),
                "GetFileInformationByHandle": (
                    [w.HANDLE, ctypes.POINTER(FileInfo)],
                    w.BOOL,
                ),
                "GetFileInformationByHandleEx": (
                    [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD],
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

    def describe(self, handle, directory, allow_symlink=False):
        info = FileInfo()
        if self.dll.GetFileType(handle) != 1 or not self.dll.GetFileInformationByHandle(
            handle, ctypes.byref(info)
        ):
            self.fail("UNSAFE_FILE")
        if info.attributes & REPARSE:
            tag = TagInfo()
            if (
                not allow_symlink
                or not self.dll.GetFileInformationByHandleEx(
                    handle, 9, ctypes.byref(tag), ctypes.sizeof(tag)
                )
                or tag.tag != 0xA000000C
            ):
                self.fail("UNSAFE_PATH")
        if bool(info.attributes & DIRECTORY) != directory:
            self.fail("UNSAFE_PATH" if directory else "UNSAFE_FILE")
        index = info.index_high << 32 | info.index_low
        if not index:
            self.fail("UNSAFE_FILE")
        buffer = ctypes.create_unicode_buffer(32768)
        # Normalized NT volume names avoid reliance on a DOS mount-manager lookup.
        size = self.dll.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 2)
        if not size or size >= len(buffer):
            self.fail("UNSAFE_PATH")
        final = buffer.value
        if re.match(
            r"\\Device\\HarddiskVolume[0-9]+(?:\\|$)", final, re.IGNORECASE
        ) is None and not (
            self.allow_remote
            and re.match(r"\\Device\\(?:Mup|LanmanRedirector)\\", final, re.IGNORECASE)
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

    def open(self, path, directory, expected=None, metadata=False, allow_symlink=False):
        access = 0x80 if directory or metadata else 0x80000000
        # Preserve cooperative data writers; deny ordinary delete sharing while held.
        handle = self.dll.CreateFileW(
            extended_path(path), access, 3, None, 3, 0x02200000, None
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
            identity, final = self.describe(
                handle, directory, allow_symlink=allow_symlink
            )
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
            or raw.replace("/", "\\").startswith(("\\\\?\\", "\\\\.\\"))
        ):
            raise core["Rejected"]("PATH_INVALID")
        path = Path(raw)
        if path.root and not path.drive:
            raise core["Rejected"]("PATH_INVALID")
        if raw.replace("/", "\\").startswith("\\\\"):
            anchor_parts = path.drive[2:].split("\\")
            if (
                not path.drive.startswith("\\\\")
                or len(anchor_parts) != 2
                or any(not _component(part) for part in anchor_parts)
            ):
                raise core["Rejected"]("PATH_INVALID")
        if ".." in path.parts or (path.drive and not path.is_absolute()):
            raise core["Rejected"]("PATH_INVALID")
        if any(not _component(part) for part in path.parts if part != path.anchor):
            raise core["Rejected"]("PATH_INVALID")
        path = path.absolute()
        if (
            not (
                path.is_absolute()
                and (
                    path.drive.startswith("\\\\")
                    or (len(path.drive) == 2 and path.drive[1] == ":")
                )
            )
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
    """Retain ordinary ancestor handles for the selected pathname's lifetime."""

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
                self.native.fail("FILE_CHANGED")

    @contextmanager
    def regular(self, relative):
        parts = relative.split("/")
        if not parts or len(parts) > 64 or any(not _component(part) for part in parts):
            self.native.fail("UNSAFE_PATH")
        extra, fd, owned = [], None, None
        current, parent_final = self.path, self.items[-1][2]
        try:
            self.verify()
            for part in parts[:-1]:
                current /= part
                item = self.native.open(
                    current, True, parent_final.rstrip("\\") + "\\" + part
                )
                extra.append(item)
                parent_final = item[2]
            owned, identity, final = self.native.open(
                current / parts[-1], False, parent_final.rstrip("\\") + "\\" + parts[-1]
            )
            import msvcrt

            fd = msvcrt.open_osfhandle(
                owned, os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT
            )
            owned = None  # CRT descriptor now owns the native handle.
            os.set_inheritable(fd, False)
            yield fd
            now, name = self.native.describe(msvcrt.get_osfhandle(fd), False)
            if now != identity or name.casefold() != final.casefold():
                self.native.fail("FILE_CHANGED")
            self.verify()
            for handle, previous, name in extra:
                current_info, current_name = self.native.describe(handle, True)
                if (
                    current_info != previous
                    or current_name.casefold() != name.casefold()
                ):
                    self.native.fail("FILE_CHANGED")
        finally:
            failure = None
            try:
                if fd is not None:
                    os.close(fd)
                elif owned is not None:
                    self.native.close(owned)
            except BaseException as error:
                failure = error
            while extra:
                try:
                    self.native.close(extra.pop()[0])
                except BaseException as error:
                    failure = failure or error
            if failure is not None:
                raise failure


CORE = {"Rejected": ValueError, "EntryFailure": ValueError}


def extended_path(path):
    value = str(path)
    return "\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value


def _inspect_path(
    value, *, allow_missing=False, allow_leaf_symlink=False, allow_remote=False
):
    """Validate spelling/observed ancestors without DOS mount-manager resolution."""
    path = selected_path(value, CORE)
    if path.drive.startswith("\\\\") and not allow_remote:
        raise ValueError("Remote Windows state paths are unsupported.")
    native = Native(CORE, allow_remote=allow_remote)
    items = []
    try:
        current = Path(path.anchor)
        item = native.open(current, True)
        items.append(item)
        native_key = item[2]
        for index, part in enumerate(path.parts[1:]):
            current /= part
            leaf = index == len(path.parts) - 2
            try:
                info = current.lstat()
            except FileNotFoundError:
                if allow_missing:
                    native_key = (
                        items[-1][2].rstrip("\\")
                        + "\\"
                        + "\\".join(path.parts[index + 1 :])
                    )
                    break
                raise
            if stat.S_ISLNK(info.st_mode):
                if leaf and allow_leaf_symlink:
                    is_directory = bool(
                        getattr(info, "st_file_attributes", 0) & DIRECTORY
                    )
                    expected = items[-1][2].rstrip("\\") + "\\" + part
                    item = native.open(
                        current,
                        is_directory,
                        expected,
                        metadata=True,
                        allow_symlink=True,
                    )
                    items.append(item)
                    native_key = item[2]
                    break
                raise ValueError("Windows parent symlinks are unsupported.")
            elif getattr(info, "st_file_attributes", 0) & REPARSE:
                raise ValueError("Windows reparse paths are unsupported.")
            is_directory = stat.S_ISDIR(info.st_mode)
            if not leaf and not is_directory:
                raise ValueError("Windows path ancestor is not a directory.")
            expected = items[-1][2].rstrip("\\") + "\\" + part
            item = native.open(current, is_directory, expected, metadata=True)
            items.append(item)
            native_key = item[2]
        for handle, identity, final in items:
            is_directory = bool(identity[2] & DIRECTORY)
            now, name = native.describe(
                handle, is_directory, allow_symlink=bool(identity[2] & REPARSE)
            )
            if now != identity or name.casefold() != final.casefold():
                raise ValueError("Windows path changed during inspection.")
        return path, native_key.casefold()
    finally:
        failure = None
        while items:
            try:
                native.close(items.pop()[0])
            except BaseException as error:
                failure = failure or error
        if failure is not None:
            raise failure


def checked_path(
    value, *, allow_missing=False, allow_leaf_symlink=False, allow_remote=False
):
    return _inspect_path(
        value,
        allow_missing=allow_missing,
        allow_leaf_symlink=allow_leaf_symlink,
        allow_remote=allow_remote,
    )[0]


def path_key(value, *, allow_missing=True, allow_leaf_symlink=False):
    """Native-volume key also detects static aliases between different drive letters."""
    return _inspect_path(
        value,
        allow_missing=allow_missing,
        allow_leaf_symlink=allow_leaf_symlink,
        allow_remote=True,
    )[1]


def check_regular(path, *, allow_missing=False, reject_streams=False):
    path = checked_path(path, allow_missing=allow_missing)
    if not path.exists() and allow_missing:
        return
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("Windows journal storage must be a single-link regular file.")
    if reject_streams:
        # Late import avoids a module cycle; this is called after engine import.
        from .core import _windows_named_stream_info

        if _windows_named_stream_info(path):
            raise ValueError("Windows journal storage must not contain named streams.")


@contextmanager
def open_regular(path, before):
    path = checked_path(path, allow_remote=True)
    native = Native(CORE, allow_remote=True)
    with Chain(native, path.parent) as chain:
        with chain.regular(path.name) as fd:
            with os.fdopen(os.dup(fd), "rb") as stream:
                current = os.fstat(fd)
                fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
                if any(
                    getattr(current, field) != getattr(before, field)
                    for field in fields
                ):
                    raise ValueError("Windows source changed before opening.")
                yield stream
                current = os.fstat(fd)
                if any(
                    getattr(current, field) != getattr(before, field)
                    for field in fields
                ):
                    raise ValueError("Windows source changed while open.")
