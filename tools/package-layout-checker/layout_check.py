"""OUTLANDS manifest-driven package layout and static source checks."""
from __future__ import annotations

import argparse
import ast
import errno
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

MAX_MANIFEST_BYTES = 65536
MAX_FILES = 100
MAX_FILE_BYTES = 262144
MAX_TOTAL_TEXT_BYTES = 2097152
MAX_LITERALS = 16
MAX_LITERAL_CHARS = 256


class Rejected(Exception):
    """Invalid control input; messages are fixed categories, never contents."""


class EntryFailure(Exception):
    """A finding for one explicitly selected relative file."""


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise Rejected("ARGUMENTS_INVALID")


def platform_supported() -> bool:
    return os.name == "posix" and all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")) and os.open in os.supports_dir_fd


def absolute_path(value: str) -> Path:
    path = Path(value)
    if not value or ".." in path.parts:
        raise Rejected("PATH_INVALID")
    return path.absolute()


def open_directory(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            following = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def open_regular(parent: int, relative: str) -> int:
    if type(relative) is not str or not relative or relative.startswith("/") or "\\" in relative or any(part in {"", ".", ".."} for part in relative.split("/")):
        raise EntryFailure("UNSAFE_PATH")
    parts = PurePosixPath(relative).parts
    current = os.dup(parent)
    try:
        for part in parts[:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = following
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
        try:
            info = os.fstat(fd)
        except BaseException:
            os.close(fd)
            raise
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            os.close(fd)
            raise EntryFailure("UNSAFE_FILE")
        return fd
    finally:
        os.close(current)


def identity(info: os.stat_result) -> tuple:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_bounded(fd: int, limit: int) -> bytes:
    before = os.fstat(fd)
    if before.st_size > limit:
        raise EntryFailure("BYTE_LIMIT")
    chunks = []
    size = 0
    while size < before.st_size:
        chunk = os.read(fd, min(65536, before.st_size - size))
        if not chunk:
            raise EntryFailure("FILE_CHANGED")
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            raise EntryFailure("BYTE_LIMIT")
    if identity(before) != identity(os.fstat(fd)):
        raise EntryFailure("FILE_CHANGED")
    return b"".join(chunks)


def unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected("MANIFEST_INVALID")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise Rejected("MANIFEST_INVALID")


def validate_manifest(value: object) -> list[dict]:
    if type(value) is not dict or set(value) != {"schema_version", "files"} or type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise Rejected("MANIFEST_INVALID")
    entries = value["files"]
    if type(entries) is not list or not 1 <= len(entries) <= MAX_FILES:
        raise Rejected("MANIFEST_INVALID")
    seen = set()
    for entry in entries:
        if type(entry) is not dict or "path" not in entry or not set(entry) <= {"path", "python_syntax", "forbidden_literals"}:
            raise Rejected("MANIFEST_INVALID")
        path = entry["path"]
        if type(path) is not str or not 1 <= len(path) <= 512 or path.startswith("/") or any(c in path for c in "\\:*?\"<>|") or any(ord(c) < 32 or ord(c) == 127 for c in path) or any(part in {"", ".", ".."} for part in path.split("/")):
            raise Rejected("MANIFEST_PATH_INVALID")
        if path.casefold() in seen:
            raise Rejected("MANIFEST_PATH_DUPLICATE")
        seen.add(path.casefold())
        if "python_syntax" in entry and type(entry["python_syntax"]) is not bool:
            raise Rejected("MANIFEST_INVALID")
        literals = entry.get("forbidden_literals", [])
        if type(literals) is not list or len(literals) > MAX_LITERALS or any(type(item) is not str or not 1 <= len(item) <= MAX_LITERAL_CHARS for item in literals):
            raise Rejected("MANIFEST_INVALID")
    return entries


def load_manifest(path: Path) -> list[dict]:
    if not path.name:
        raise Rejected("MANIFEST_INVALID")
    parent = open_directory(path.parent)
    try:
        fd = open_regular(parent, path.name)
        try:
            raw = read_bounded(fd, MAX_MANIFEST_BYTES)
        finally:
            os.close(fd)
    finally:
        os.close(parent)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise Rejected("MANIFEST_INVALID") from None
    return validate_manifest(value)


def inspect_entry(root: int, entry: dict, used: int) -> tuple[dict, int]:
    result = {"path": entry["path"], "status": "PASS", "codes": []}
    try:
        fd = open_regular(root, entry["path"])
        try:
            info = os.fstat(fd)
            if info.st_size > MAX_FILE_BYTES:
                raise EntryFailure("BYTE_LIMIT")
            if entry.get("python_syntax", False) or entry.get("forbidden_literals", []):
                if used + info.st_size > MAX_TOTAL_TEXT_BYTES:
                    raise EntryFailure("TOTAL_BYTE_LIMIT")
                # Reserve the full observed size even if a read later fails.
                # A changed/growing file cannot increase the reserved read cap.
                used += info.st_size
                raw = read_bounded(fd, info.st_size)
                try:
                    text = raw.decode("utf-8-sig")
                except UnicodeError:
                    raise EntryFailure("TEXT_INVALID") from None
                if entry.get("python_syntax", False):
                    try:
                        ast.parse(text)
                    except (SyntaxError, ValueError, RecursionError, MemoryError):
                        result["codes"].append("PYTHON_SYNTAX")
                if any(literal.casefold() in text.casefold() for literal in entry.get("forbidden_literals", [])):
                    result["codes"].append("FORBIDDEN_LITERAL")
        finally:
            os.close(fd)
    except FileNotFoundError:
        result["codes"].append("MISSING")
    except EntryFailure as error:
        result["codes"].append(str(error))
    except OSError as error:
        result["codes"].append("UNSAFE_PATH" if error.errno in {errno.ELOOP, errno.ENOTDIR} else "READ_ERROR")
    if result["codes"]:
        result["status"] = "FAIL"
    return result, used


def check_layout(root_path: Path, entries: list[dict]) -> dict:
    if root_path == Path(root_path.anchor):
        raise Rejected("ROOT_INVALID")
    descriptor = open_directory(root_path)
    try:
        results, used = [], 0
        for entry in entries:
            result, used = inspect_entry(descriptor, entry, used)
            results.append(result)
    finally:
        os.close(descriptor)
    failed = sum(result["status"] == "FAIL" for result in results)
    return {"schema_version": 1, "status": "FAIL" if failed else "PASS", "checked_files": len(results), "failed_files": failed, "results": results}


def windows_report(root_value: str, manifest_value: str) -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("_outlands_layout_windows", Path(__file__).with_name("layout_windows.py"))
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    return backend.check_windows(root_value, manifest_value, globals())


def main(argv: list[str] | None = None) -> int:
    parser = SafeParser(description="Check explicit package files and optional static source rules without executing them.")
    parser.add_argument("--root", required=True, help="Explicit package root; no project default")
    parser.add_argument("--manifest", required=True, help="Caller-authored JSON expectations; may contain sensitive patterns")
    try:
        args = parser.parse_args(argv)
        if os.name == "nt":
            report = windows_report(args.root, args.manifest)
        else:
            if not platform_supported():
                raise Rejected("UNSUPPORTED_PLATFORM")
            entries = load_manifest(absolute_path(args.manifest))
            report = check_layout(absolute_path(args.root), entries)
    except Rejected as error:
        print(json.dumps({"status": "REJECTED", "code": str(error)}))
        return 2
    except (OSError, EntryFailure, ValueError, RecursionError):
        print(json.dumps({"status": "REJECTED", "code": "INPUT_OR_IO"}))
        return 2
    except KeyboardInterrupt:
        print(json.dumps({"status": "REJECTED", "code": "INTERRUPTED"}))
        return 130
    print(json.dumps(report, ensure_ascii=True, separators=(",", ":")))
    return 1 if report["failed_files"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
