#!/usr/bin/env python3
"""Offline validation of explicitly supplied locks in the converter's strict format."""
from __future__ import annotations

import json
from pathlib import Path
import re

from lock_common import (LockError, MAX_LINES, MAX_LINE_CHARS, MAX_LOCK_BYTES, MAX_LOCKS,
                         MAX_PACKAGES, MAX_TOTAL_LOCK_BYTES, Parser, checked_hash,
                         checked_version, error_result, normalize_name, read_bounded, require)

PACKAGE_RE = re.compile(r"([A-Za-z0-9._-]+)==([^\s\\]+) \\\Z", re.ASCII)
HASH_LINE_RE = re.compile(r"    --hash=sha256:([0-9a-fA-F]{64})\Z", re.ASCII)


def validate_lock(data: bytes) -> int:
    require(type(data) is bytes and 0 < len(data) <= MAX_LOCK_BYTES, "INPUT_SIZE_LIMIT")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        raise LockError("LOCK_ENCODING_INVALID") from None
    require(not any(ord(c) < 32 and c not in "\n\r" for c in text), "LOCK_CONTROL_CHARACTER")
    lines = text.splitlines()
    require(len(lines) <= MAX_LINES and all(len(line) <= MAX_LINE_CHARS for line in lines), "LOCK_STRUCTURE_LIMIT")
    names, index = [], 0
    while index < len(lines):
        line = lines[index]
        if not line or line.startswith("#"):
            index += 1
            continue
        match = PACKAGE_RE.fullmatch(line)
        require(match is not None, "LOCK_LINE_INVALID")
        raw_name, raw_version = match.groups()
        name = normalize_name(raw_name)
        require(name == raw_name, "PACKAGE_NAME_NONCANONICAL")
        checked_version(raw_version)
        require(index + 1 < len(lines), "ADJACENT_SHA256_REQUIRED")
        match = HASH_LINE_RE.fullmatch(lines[index + 1])
        require(match is not None, "ADJACENT_SHA256_REQUIRED")
        checked_hash(match.group(1))
        require(name not in names, "DUPLICATE_PACKAGE")
        names.append(name)
        require(len(names) <= MAX_PACKAGES, "LOCK_PACKAGE_LIMIT")
        index += 2
    require(bool(names), "EMPTY_LOCK")
    require(names == sorted(names), "PACKAGE_ORDER_INVALID")
    return len(names)


def verify(paths: list[Path]) -> int:
    require(1 <= len(paths) <= MAX_LOCKS, "LOCK_FILE_COUNT_LIMIT")
    total_bytes = package_records = 0
    for path in paths:
        data = read_bounded(path, MAX_LOCK_BYTES)
        total_bytes += len(data)
        require(total_bytes <= MAX_TOTAL_LOCK_BYTES, "TOTAL_INPUT_SIZE_LIMIT")
        package_records += validate_lock(data)
    return package_records


def main(argv=None) -> int:
    try:
        parser = Parser(description=__doc__)
        parser.add_argument("locks", nargs="+", type=Path)
        args = parser.parse_args(argv)
        count = verify(args.locks)
        print(json.dumps({"result": "PASS", "locks": len(args.locks), "package_records": count}, sort_keys=True))
        return 0
    except LockError as error:
        return error_result(str(error))
    except (OSError, ValueError, UnicodeError):
        return error_result("INPUT_OR_IO_ERROR")


if __name__ == "__main__":
    raise SystemExit(main())
