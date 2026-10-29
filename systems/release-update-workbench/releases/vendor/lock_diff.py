#!/usr/bin/env python3
"""Compare two supported dependency lock declarations without package operations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

VERSION = "0.1.0"
MAX_LOCK_BYTES = 1024 * 1024
MAX_PACKAGES = 2000
MAX_LINES = 6000
MAX_LINE_CHARS = 512
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit
    for prefix in ("com", "lpt")
    for digit in "123456789\u00b9\u00b2\u00b3"
}
NAME_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,198}[A-Za-z0-9])?\Z", re.ASCII)
VERSION_RE = re.compile(
    r"(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?"
    r"(?:\.post[0-9]+)?(?:\.dev[0-9]+)?(?:\+[a-z0-9]+(?:[.-][a-z0-9]+)*)?\Z",
    re.ASCII,
)
HASH_RE = re.compile(r"[0-9a-fA-F]{64}\Z", re.ASCII)
PACKAGE_RE = re.compile(r"([A-Za-z0-9._-]+)==([^\s\\]+) \\\Z", re.ASCII)
HASH_LINE_RE = re.compile(r"    --hash=sha256:([0-9a-fA-F]{64})\Z", re.ASCII)


class DiffError(Exception):
    """A fixed code without supplied package values, paths or native details."""


def _fail(code):
    raise DiffError(code) from None


def _require(condition, code):
    if not condition:
        _fail(code)


def normalize_name(value):
    _require(
        type(value) is str and NAME_RE.fullmatch(value) is not None,
        "PACKAGE_NAME_INVALID",
    )
    return re.sub(r"[-_.]+", "-", value).lower()


def checked_version(value):
    _require(
        type(value) is str
        and len(value) <= 128
        and VERSION_RE.fullmatch(value) is not None,
        "VERSION_UNSUPPORTED",
    )
    return value


def checked_hash(value):
    _require(
        type(value) is str and HASH_RE.fullmatch(value) is not None, "SHA256_INVALID"
    )
    return value.lower()


def parse_lock(data):
    """Parse the existing public narrow grammar, retaining compared declarations."""
    _require(
        type(data) is bytes and 0 < len(data) <= MAX_LOCK_BYTES, "INPUT_SIZE_LIMIT"
    )
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        _fail("LOCK_ENCODING_INVALID")
    _require(
        not any(ord(c) < 32 and c not in "\n\r" for c in text), "LOCK_CONTROL_CHARACTER"
    )
    lines = text.splitlines()
    _require(
        len(lines) <= MAX_LINES and all(len(line) <= MAX_LINE_CHARS for line in lines),
        "LOCK_STRUCTURE_LIMIT",
    )
    records, index = {}, 0
    while index < len(lines):
        line = lines[index]
        if not line or line.startswith("#"):
            index += 1
            continue
        match = PACKAGE_RE.fullmatch(line)
        _require(match is not None, "LOCK_LINE_INVALID")
        raw_name, raw_version = match.groups()
        name = normalize_name(raw_name)
        _require(name == raw_name, "PACKAGE_NAME_NONCANONICAL")
        version = checked_version(raw_version)
        _require(index + 1 < len(lines), "ADJACENT_SHA256_REQUIRED")
        match = HASH_LINE_RE.fullmatch(lines[index + 1])
        _require(match is not None, "ADJACENT_SHA256_REQUIRED")
        digest = checked_hash(match.group(1))
        _require(name not in records, "DUPLICATE_PACKAGE")
        records[name] = dict(version=version, sha256=digest)
        _require(len(records) <= MAX_PACKAGES, "LOCK_PACKAGE_LIMIT")
        index += 2
    _require(bool(records), "EMPTY_LOCK")
    _require(list(records) == sorted(records), "PACKAGE_ORDER_INVALID")
    return records


def _flags():
    return dict(
        filesystem_scanned=False,
        packages_downloaded=False,
        packages_installed=False,
        environment_inspected=False,
        artifacts_verified=False,
        dependencies_resolved=False,
        advisories_checked=False,
        upgrade_direction_inferred=False,
        locks_modified=False,
        network_probed=False,
    )


def compare_locks(before, after):
    """Compare text versions and declared hashes, without semantic version ranking."""
    old, new = parse_lock(before), parse_lock(after)
    counts = dict(
        only_in_before=0,
        only_in_after=0,
        version_text_changed=0,
        hash_only_changed=0,
        unchanged=0,
    )
    rows = []
    for name in sorted(old.keys() | new.keys()):
        left, right = old.get(name), new.get(name)
        version_changed = (
            None
            if left is None or right is None
            else left["version"] != right["version"]
        )
        hash_changed = (
            None if left is None or right is None else left["sha256"] != right["sha256"]
        )
        if left is None:
            kind = "ONLY_IN_AFTER"
        elif right is None:
            kind = "ONLY_IN_BEFORE"
        elif version_changed:
            kind = "VERSION_TEXT_CHANGED"
        elif hash_changed:
            kind = "HASH_ONLY_CHANGED"
        else:
            kind = "UNCHANGED"
        counts[kind.lower()] += 1
        rows.append(
            dict(
                name=name,
                classification=kind,
                before=left,
                after=right,
                version_text_changed=version_changed,
                hash_changed=hash_changed,
            )
        )
    changed = any(value for key, value in counts.items() if key != "unchanged")
    return dict(
        schema_version="outlands.lock_diff.v1",
        status="LOCK_DIFFERENCES_REPORTED" if changed else "MATCHING_LOCK_RECORDS",
        scope="SUPPORTED_LOCK_DECLARATIONS_ONLY",
        **_flags(),
        counts=dict(before=len(old), after=len(new), **counts),
        rows=rows,
        input_sha256=dict(
            before=hashlib.sha256(before).hexdigest(),
            after=hashlib.sha256(after).hexdigest(),
        ),
    )


def _validate_path_parts(path):
    for part in path.parts:
        if part == path.anchor:
            continue
        if (
            part.endswith((".", " "))
            or part.split(".")[0].casefold() in RESERVED
            or any(c in '\\:<>"|?*' for c in part)
        ):
            _fail("INPUT_PATH_INVALID")


def _selected_path(value):
    try:
        raw = os.fspath(value)
        if (
            not isinstance(raw, str)
            or not 0 < len(raw) <= 4096
            or raw.startswith(("\\\\", "//"))
            or any(ord(c) < 32 or ord(c) == 127 for c in raw)
        ):
            _fail("INPUT_PATH_INVALID")
        original = Path(raw)
        if ".." in original.parts or (original.drive and not original.is_absolute()):
            _fail("INPUT_PATH_INVALID")
        # Windows absolute-path normalization can erase trailing dots/spaces.
        _validate_path_parts(original)
        path = Path(os.path.abspath(original))
        if path.parent == path or len(path.parts) > 64 or len(str(path)) > 4096:
            _fail("INPUT_PATH_INVALID")
        _validate_path_parts(path)
        return path
    except (OSError, TypeError, ValueError):
        _fail("INPUT_PATH_INVALID")


def _linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


def _identity(info, *, directory=False):
    base = (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        getattr(info, "st_file_attributes", 0) & 0x400,
    )
    return base if directory else (*base, info.st_nlink, info.st_size, info.st_mtime_ns)


def _regular_input(info):
    if _linked(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _fail("INPUT_UNAVAILABLE_OR_UNSAFE")
    if not info.st_ino:
        _fail("INPUT_IDENTITY_UNAVAILABLE")


def _snapshot(path):
    ancestors = []
    for ancestor in reversed(path.parents):
        info = ancestor.lstat()
        if _linked(info) or not stat.S_ISDIR(info.st_mode):
            _fail("INPUT_UNAVAILABLE_OR_UNSAFE")
        if not info.st_ino:
            _fail("INPUT_IDENTITY_UNAVAILABLE")
        ancestors.append(_identity(info, directory=True))
    leaf = path.lstat()
    _regular_input(leaf)
    return tuple(ancestors), leaf


def _read_bytes(value, maximum):
    path = _selected_path(value)
    ancestors, before = _snapshot(path)
    _require(before.st_size <= maximum, "INPUT_BYTE_LIMIT")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        _regular_input(opened)
        _require(_identity(opened) == _identity(before), "INPUT_CHANGED")
        data = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    current_ancestors, current = _snapshot(path)
    _require(
        ancestors == current_ancestors
        and _identity(after) == _identity(before)
        and _identity(current) == _identity(before)
        and len(data) == before.st_size,
        "INPUT_CHANGED",
    )
    _require(len(data) <= maximum, "INPUT_BYTE_LIMIT")
    return data, (ancestors, _identity(current))


def _fingerprint(path):
    ancestors, leaf = _snapshot(path)
    return ancestors, _identity(leaf)


def render_report(result):
    """Bound serialized JSON before stdout receives any partial report."""
    chunks, size = [], 0
    encoder = json.JSONEncoder(ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    for chunk in encoder.iterencode(result):
        size += len(chunk)
        _require(size <= MAX_OUTPUT_BYTES, "OUTPUT_BYTE_LIMIT")
        chunks.append(chunk)
    return "".join(chunks)


def read_and_compare(before, after):
    """Read exactly two selected files and recheck their sampled identities."""
    try:
        paths = [_selected_path(before), _selected_path(after)]
        inputs, checked = [], []
        for path in paths:
            data, identity = _read_bytes(path, MAX_LOCK_BYTES)
            inputs.append(data)
            checked.append((path, identity))
        result = compare_locks(*inputs)
        for path, identity in checked:
            _require(_fingerprint(path) == identity, "INPUT_CHANGED")
        return result
    except DiffError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        _fail("INPUT_OR_LOCK_FAILED")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        _fail("ARGUMENTS_INVALID")


def main(argv=None):
    parser = _Parser(
        prog="dependency-lock-diff", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    exit_code = 2
    try:
        args = parser.parse_args(argv)
        result = read_and_compare(args.before, args.after)
        print(render_report(result))
        return 0 if result["status"] == "MATCHING_LOCK_RECORDS" else 1
    except DiffError as error:
        code = str(error)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        code = "INPUT_OR_LOCK_FAILED"
    except KeyboardInterrupt:
        code, exit_code = "INTERRUPTED", 130
    print(json.dumps(dict(status="ERROR", code=code, **_flags()), sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
