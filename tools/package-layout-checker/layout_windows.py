"""Native Windows input backend for the public layout manifest contract.

No writes, directory enumeration, network probes or selected-source execution.
The POSIX descriptor backend remains in layout_check.py.
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
import ctypes
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import re

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


def _time(value):
    return value.dwHighDateTime << 32 | value.dwLowDateTime


class Native:
    """Read-only bindings and explicit handle ownership; fixed errors only."""

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
        if info.attributes & REPARSE or bool(info.attributes & DIRECTORY) != directory:
            self.fail("UNSAFE_PATH" if directory else "UNSAFE_FILE")
        index = info.index_high << 32 | info.index_low
        if not index or (not directory and info.links != 1):
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
        access = 0x80 if directory else 0x80000000
        # Share reads only. Incompatible data writers/deleters make open fail.
        handle = self.dll.CreateFileW(
            "\\\\?\\" + str(path), access, 1, None, 3, 0x02200000, None
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
        path = Path(raw)
        if ".." in path.parts or (path.drive and not path.is_absolute()):
            raise core["Rejected"]("PATH_INVALID")
        if any(not _component(part) for part in path.parts if part != path.anchor):
            raise core["Rejected"]("PATH_INVALID")
        path = path.absolute()
        if (
            len(path.drive) != 2
            or path.drive[1] != ":"
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


def load_manifest(path, native, core):
    if not path.name:
        raise core["Rejected"]("MANIFEST_INVALID")
    with Chain(native, path.parent) as chain:
        with chain.regular(path.name) as fd:
            raw = core["read_bounded"](fd, core["MAX_MANIFEST_BYTES"])
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=core["unique_object"],
            parse_constant=core["reject_constant"],
        )
    except (UnicodeError, ValueError, RecursionError):
        raise core["Rejected"]("MANIFEST_INVALID") from None
    return core["validate_manifest"](value)


def inspect_entry(chain, entry, used, core):
    result = dict(path=entry["path"], status="PASS", codes=[])
    try:
        with chain.regular(entry["path"]) as fd:
            info = os.fstat(fd)
            if info.st_size > core["MAX_FILE_BYTES"]:
                raise core["EntryFailure"]("BYTE_LIMIT")
            if entry.get("python_syntax", False) or entry.get("forbidden_literals", []):
                if used + info.st_size > core["MAX_TOTAL_TEXT_BYTES"]:
                    raise core["EntryFailure"]("TOTAL_BYTE_LIMIT")
                used += info.st_size
                raw = core["read_bounded"](fd, info.st_size)
                try:
                    text = raw.decode("utf-8-sig")
                except UnicodeError:
                    raise core["EntryFailure"]("TEXT_INVALID") from None
                if entry.get("python_syntax", False):
                    try:
                        ast.parse(text)
                    except (SyntaxError, ValueError, RecursionError, MemoryError):
                        result["codes"].append("PYTHON_SYNTAX")
                if any(
                    literal.casefold() in text.casefold()
                    for literal in entry.get("forbidden_literals", [])
                ):
                    result["codes"].append("FORBIDDEN_LITERAL")
    except core["EntryFailure"] as error:
        result["codes"].append(str(error))
    except OSError:
        result["codes"].append("READ_ERROR")
    if result["codes"]:
        result["status"] = "FAIL"
    return result, used


def check_windows(root_value, manifest_value, core):
    native = Native(core)
    root, manifest = (
        selected_path(root_value, core),
        selected_path(manifest_value, core),
    )
    if root == Path(root.anchor):
        raise core["Rejected"]("ROOT_INVALID")
    try:
        entries = load_manifest(manifest, native, core)
        with Chain(native, root) as chain:
            results, used = [], 0
            for entry in entries:
                result, used = inspect_entry(chain, entry, used, core)
                results.append(result)
            chain.verify()
        failed = sum(row["status"] == "FAIL" for row in results)
        return dict(
            schema_version=1,
            status="FAIL" if failed else "PASS",
            checked_files=len(results),
            failed_files=failed,
            results=results,
        )
    except core["EntryFailure"]:
        raise core["Rejected"]("INPUT_OR_IO") from None
