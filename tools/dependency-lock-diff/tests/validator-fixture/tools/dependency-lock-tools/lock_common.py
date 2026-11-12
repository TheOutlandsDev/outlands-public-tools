"""Shared bounded file and requirements-format helpers. Standard library only."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import stat

MAX_REPORT_BYTES = 2 * 1024 * 1024
MAX_LOCK_BYTES = 1024 * 1024
MAX_PACKAGES = 2000
MAX_LOCKS = 32
MAX_TOTAL_LOCK_BYTES = 8 * 1024 * 1024
MAX_LINES = 6000
MAX_LINE_CHARS = 512
NAME_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,198}[A-Za-z0-9])?\Z", re.ASCII)
# A deliberately limited fixed-version subset, not a complete PEP 440 parser.
VERSION_RE = re.compile(
    r"(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?"
    r"(?:\.post[0-9]+)?(?:\.dev[0-9]+)?(?:\+[a-z0-9]+(?:[.-][a-z0-9]+)*)?\Z", re.ASCII)
HASH_RE = re.compile(r"[0-9a-fA-F]{64}\Z", re.ASCII)


class LockError(Exception):
    """Fixed error code only; never package records, endpoints or input paths."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise LockError(code)


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise LockError("ARGUMENTS_INVALID")


def checked_path(value: Path) -> Path:
    p = Path(value)
    require(".." not in p.parts, "PATH_TRAVERSAL")
    p = p if p.is_absolute() else Path.cwd() / p
    return p


def no_links(path: Path) -> None:
    for item in (path, *path.parents):
        require(not stat.S_ISLNK(item.lstat().st_mode), "SYMLINK_PATH")


def read_bounded(path: Path, limit: int) -> bytes:
    if os.name == "nt":
        return windows_backend().read_bounded(path, limit, LockError)
    require(hasattr(os, "O_NOFOLLOW"), "PLATFORM_UNSUPPORTED")
    p = checked_path(path)
    no_links(p)
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), "INPUT_NOT_REGULAR")
        require(0 < before.st_size <= limit, "INPUT_SIZE_LIMIT")
        chunks, size = [], 0
        while True:
            block = os.read(fd, min(65536, limit + 1 - size))
            if not block:
                break
            size += len(block)
            require(size <= limit, "INPUT_SIZE_LIMIT")
            chunks.append(block)
        after = os.fstat(fd)
        current = p.lstat()
        for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"):
            require(getattr(before, field) == getattr(after, field) == getattr(current, field), "INPUT_CHANGED")
        require(size == before.st_size, "INPUT_CHANGED")
        return b"".join(chunks)
    finally:
        os.close(fd)


def write_new(path: Path, data: bytes) -> None:
    if os.name == "nt":
        return windows_backend().write_new(path, data, LockError)
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
            and os.open in os.supports_dir_fd, "PLATFORM_UNSUPPORTED")
    require(type(data) is bytes and 0 < len(data) <= MAX_LOCK_BYTES, "OUTPUT_SIZE_LIMIT")
    p = checked_path(path)
    no_links(p.parent)
    parent_fd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            fd = os.open(p.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent_fd)
        except FileExistsError:
            raise LockError("OUTPUT_EXISTS") from None
        identity = os.fstat(fd)
        try:
            with os.fdopen(fd, "wb") as target:
                target.write(data)
                target.flush()
                os.fsync(target.fileno())
            os.fsync(parent_fd)
        except BaseException:
            try:
                current = os.stat(p.name, dir_fd=parent_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                    os.unlink(p.name, dir_fd=parent_fd)
            except OSError:
                pass
            raise
    finally:
        os.close(parent_fd)


def windows_backend():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_outlands_lock_windows", Path(__file__).with_name("lock_windows.py"))
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    return backend


def normalize_name(value: str) -> str:
    require(type(value) is str and NAME_RE.fullmatch(value) is not None, "PACKAGE_NAME_INVALID")
    return re.sub(r"[-_.]+", "-", value).lower()


def checked_version(value: str) -> str:
    require(type(value) is str and len(value) <= 128 and VERSION_RE.fullmatch(value) is not None,
            "VERSION_UNSUPPORTED")
    return value


def checked_hash(value: str) -> str:
    require(type(value) is str and HASH_RE.fullmatch(value) is not None, "SHA256_INVALID")
    return value.lower()


def strict_json(data: bytes):
    require(type(data) is bytes and 0 < len(data) <= MAX_REPORT_BYTES, "INPUT_SIZE_LIMIT")
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, "JSON_DUPLICATE_KEY")
            result[key] = value
        return result
    def invalid_constant(_value):
        raise LockError("JSON_NONFINITE")
    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (ValueError, UnicodeError):
        raise LockError("JSON_INVALID") from None
    except RecursionError:
        raise LockError("JSON_STRUCTURE_LIMIT") from None
    pending, nodes = [(value, 1)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        require(depth <= 64 and nodes <= 50000, "JSON_STRUCTURE_LIMIT")
        require(not isinstance(item, float) or math.isfinite(item), "JSON_NONFINITE")
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
    return value


def error_result(code: str) -> int:
    print(json.dumps({"result": "ERROR", "code": code}, sort_keys=True))
    return 2
