#!/usr/bin/env python3
"""Verify a local component release and plan updates without executing inputs."""

from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
import importlib.util
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import unicodedata

REPOSITORY = Path(__file__).resolve().parents[2]
MAX_METADATA = 1024 * 1024
MAX_FILES = 4096
MAX_ENTRIES = 8192
MAX_FILE = 256 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024
HASH = re.compile(r"[a-f0-9]{64}")
RESERVED = {"con", "prn", "aux", "nul"} | {
    prefix + str(index) for prefix in ("com", "lpt") for index in range(1, 10)
}


class PreflightError(ValueError):
    pass


def refuse(code):
    raise PreflightError(code)


def regular(info, *, directory=False):
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        refuse("LINK_OR_REPARSE_UNSUPPORTED")
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        refuse("FILE_TYPE_UNSUPPORTED")
    if not directory and info.st_nlink != 1:
        refuse("HARDLINK_UNSUPPORTED")


def selected_path(value, *, missing=False):
    raw = _windows().selected_path(value, _windows()._core(PreflightError)) if os.name == "nt" else Path(value)
    if ".." in raw.parts:
        refuse("PARENT_TRAVERSAL")
    path = Path(os.path.abspath(raw))
    if path.parent == path or path.drive.startswith("\\\\"):
        refuse("FILESYSTEM_ROOT_OR_SHARE_UNSUPPORTED")
    if os.name == "nt" and any(":" in part for part in path.parts[1:]):
        refuse("STREAM_PATH_UNSUPPORTED")
    for item in reversed([path, *path.parents]):
        try:
            info = item.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise
        regular(info, directory=item != path or stat.S_ISDIR(info.st_mode))
    if os.name == "nt":
        _windows().checked_selection(path, missing, PreflightError)
    return path


def directory(value):
    path = selected_path(value)
    regular(path.lstat(), directory=True)
    return path


def relative_name(value):
    if not isinstance(value, str) or not 0 < len(value) <= 240:
        refuse("INVALID_RELATIVE_PATH")
    if unicodedata.normalize("NFC", value) != value:
        refuse("NONCANONICAL_PATH")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or len(path.parts) > 32:
        refuse("INVALID_RELATIVE_PATH")
    for part in value.split("/"):
        if (
            part in {"", ".", ".."}
            or part.casefold() == ".git"
            or part.endswith((".", " "))
            or part.split(".")[0].casefold() in RESERVED
            or any(
                ord(char) < 32 or ord(char) == 127 or char in '\\:<>"|?*'
                for char in part
            )
        ):
            refuse("INVALID_RELATIVE_PATH")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            refuse("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


_WINDOWS_BACKEND = None


def _windows():
    global _WINDOWS_BACKEND
    if _WINDOWS_BACKEND is None:
        spec = importlib.util.spec_from_file_location(
            "outlands_preflight_windows", Path(__file__).with_name("preflight_windows.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _WINDOWS_BACKEND = module
    return _WINDOWS_BACKEND


def _posix_chain(path):
    rows = []
    for item in [*reversed(path.parents), path]:
        info = item.lstat()
        regular(info, directory=True)
        rows.append((item, info.st_dev, info.st_ino, info.st_mode))
    return tuple(rows)


@contextmanager
def _root_scope(value):
    path = directory(value)
    if os.name == "nt":
        with _windows().root_scope(path, PreflightError):
            yield path
    else:
        before = _posix_chain(path)
        yield path
        if _posix_chain(path) != before:
            refuse("INPUT_CHANGED")


@contextmanager
def _entries(folder):
    with _root_scope(folder):
        with os.scandir(folder) as entries:
            yield entries


@contextmanager
def _input_scope(path, limit):
    if os.name == "nt":
        with _windows().regular(path, PreflightError, single_link=True, maximum=limit) as fd:
            yield fd
    else:
        parents = _posix_chain(path.parent)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        try:
            os.set_inheritable(fd, False)
            before = os.fstat(fd)
            regular(before)
            yield fd
            after = os.fstat(fd)
            regular(after)
            if (before.st_nlink != after.st_nlink or _posix_chain(path.parent) != parents):
                refuse("INPUT_CHANGED")
        finally:
            os.close(fd)


@contextmanager
def _report_scope(target, protected_roots):
    if os.name == "nt":
        with _windows().report_scope(target, [REPOSITORY, *protected_roots], PreflightError):
            yield
    else:
        with ExitStack() as stack:
            for root in [REPOSITORY, *protected_roots]:
                stack.enter_context(_root_scope(root))
            stack.enter_context(_root_scope(target.parent))
            yield


def _write_posix(target, raw):
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    fd = os.open(target, flags, 0o600)
    try:
        os.set_inheritable(fd, False)
        before = os.fstat(fd)
        regular(before)
        if before.st_size != 0:
            refuse("OUTPUT_CHANGED")
        position = 0
        while position < len(raw):
            block = raw[position:position + 65536]
            written = os.write(fd, block)
            if not 0 < written <= len(block):
                refuse("OUTPUT_IO_ERROR")
            position += written
        os.fsync(fd)
        written = os.fstat(fd)
        regular(written)
        if (identity(written)[:2] != identity(before)[:2] or written.st_size != len(raw)):
            refuse("OUTPUT_CHANGED")
        expected = {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        if hash_file(target, limit=len(raw)) != expected:
            refuse("REPORT_VERIFY_FAILED")
        after = os.fstat(fd)
        final = target.lstat()
        regular(final)
        if (identity(after) != identity(written) or identity(final) != identity(after)
                or after.st_ctime_ns != written.st_ctime_ns or final.st_ctime_ns != after.st_ctime_ns):
            refuse("OUTPUT_CHANGED")
    finally:
        os.close(fd)


def hash_file(value, *, limit=MAX_FILE, collect=False):
    path = selected_path(value)
    before = path.lstat()
    regular(before)
    if before.st_size > limit:
        refuse("FILE_SIZE_LIMIT")
    digest = hashlib.sha256()
    size = 0
    chunks = []
    with _input_scope(path, limit) as fd:
        opened = os.fstat(fd)
        regular(opened)
        if identity(opened) != identity(before):
            refuse("INPUT_CHANGED")
        while chunk := os.read(fd, min(1024 * 1024, limit + 1 - size)):
            size += len(chunk)
            if size > limit:
                refuse("FILE_SIZE_LIMIT")
            digest.update(chunk)
            if collect:
                chunks.append(chunk)
        if (identity(os.fstat(fd)) != identity(before)
                or os.fstat(fd).st_ctime_ns != opened.st_ctime_ns):
            refuse("INPUT_CHANGED")
        final = path.lstat()
        regular(final)
        if identity(final) != identity(before) or size != before.st_size:
            refuse("INPUT_CHANGED")
    result = {"size": size, "sha256": digest.hexdigest()}
    return (result, b"".join(chunks)) if collect else result


def pinned_json(path, pin):
    if not isinstance(pin, str) or not HASH.fullmatch(pin):
        refuse("EXTERNAL_SHA256_PIN_REQUIRED")
    info, raw = hash_file(path, limit=MAX_METADATA, collect=True)
    if info["sha256"] != pin:
        refuse("PIN_MISMATCH")
    return json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=unique_object,
        parse_constant=lambda _: refuse("NONSTANDARD_JSON"),
    )


def manifest_rows(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "inventory"}
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or not isinstance(value["inventory"], list)
        or not 0 < len(value["inventory"]) <= MAX_FILES
    ):
        refuse("INVALID_MANIFEST")
    rows = []
    prefixes = {}
    seen = set()
    total = 0
    for item in value["inventory"]:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            refuse("INVALID_MANIFEST_ENTRY")
        name = relative_name(item["path"])
        if name.casefold() in seen:
            refuse("DUPLICATE_PATH")
        seen.add(name.casefold())
        for index in range(1, len(name.split("/")) + 1):
            prefix = "/".join(name.split("/")[:index])
            if prefix.casefold() in prefixes and prefixes[prefix.casefold()] != prefix:
                refuse("CASE_COLLISION")
            prefixes[prefix.casefold()] = prefix
        if (
            type(item["size"]) is not int
            or not 0 <= item["size"] <= MAX_FILE
            or not isinstance(item["sha256"], str)
            or not HASH.fullmatch(item["sha256"])
        ):
            refuse("INVALID_MANIFEST_ENTRY")
        total += item["size"]
        if total > MAX_TOTAL:
            refuse("TOTAL_SIZE_LIMIT")
        rows.append(dict(item))
    for item in rows:
        parts = item["path"].split("/")
        if any(
            "/".join(parts[:index]).casefold() in seen for index in range(1, len(parts))
        ):
            refuse("FILE_DIRECTORY_COLLISION")
    return sorted(rows, key=lambda row: row["path"])


def candidate_inventory(root, rows):
    expected_files = {row["path"] for row in rows}
    expected_sizes = {row["path"]: row["size"] for row in rows}
    expected_dirs = set()
    for row in rows:
        parts = row["path"].split("/")
        expected_dirs.update("/".join(parts[:index]) for index in range(1, len(parts)))
    found = []
    stack = [root]
    count = 0
    while stack:
        folder = stack.pop()
        regular(folder.lstat(), directory=True)
        with _entries(folder) as entries:
            for entry in entries:
                count += 1
                if count > MAX_ENTRIES:
                    refuse("ENTRY_LIMIT")
                path = Path(entry.path)
                name = relative_name(path.relative_to(root).as_posix())
                info = path.lstat()
                is_directory = stat.S_ISDIR(info.st_mode)
                regular(info, directory=is_directory)
                if is_directory:
                    if name not in expected_dirs:
                        refuse("UNLISTED_DIRECTORY")
                    stack.append(path)
                else:
                    if name not in expected_files:
                        refuse("UNLISTED_FILE")
                    if info.st_size != expected_sizes[name]:
                        refuse("CANDIDATE_MISMATCH")
                    found.append({"path": name, **hash_file(path)})
    return sorted(found, key=lambda row: row["path"])


def verify(candidate, manifest, manifest_sha):
    with _root_scope(candidate):
        root = directory(candidate)
        metadata = selected_path(manifest)
        if metadata.is_relative_to(root):
            refuse("MANIFEST_MUST_BE_EXTERNAL")
        rows = manifest_rows(pinned_json(metadata, manifest_sha))
        if candidate_inventory(root, rows) != rows:
            refuse("CANDIDATE_MISMATCH")
        return root, rows


def update_plan(candidate, current, manifest, manifest_sha):
    with _root_scope(candidate), _root_scope(current):
        source, rows = verify(candidate, manifest, manifest_sha)
        target = directory(current)
        if source.is_relative_to(target) or target.is_relative_to(source):
            refuse("NESTED_INPUT_ROOTS")
        if os.name == "nt":
            _windows().separate_roots(source, target, PreflightError)
        result = []
        current_total = 0
        for row in rows:
            path = selected_path(target / row["path"], missing=True)
            try:
                path.lstat()
            except FileNotFoundError:
                existing = None
            else:
                existing = hash_file(path, limit=min(MAX_FILE, MAX_TOTAL - current_total))
                current_total += existing["size"]
                if current_total > MAX_TOTAL:
                    refuse("TOTAL_SIZE_LIMIT")
            action = (
                "ADD"
                if existing is None
                else "UNCHANGED"
                if existing == {key: row[key] for key in ("size", "sha256")}
                else "REPLACE"
            )
            result.append(
                {
                    "path": row["path"],
                    "action": action,
                    "expected": {key: row[key] for key in ("size", "sha256")},
                    "current": existing,
                }
            )
        # Detect changes across the overall read, not just within a single file.
        for item in result:
            path = selected_path(target / item["path"], missing=True)
            if item["current"] is None:
                if path.exists():
                    refuse("INPUT_CHANGED")
            elif hash_file(path, limit=item["current"]["size"]) != item["current"]:
                refuse("INPUT_CHANGED")
        verify(source, manifest, manifest_sha)
        return {
            "schema_version": 1,
            "operation": "plan",
            "execution_performed": False,
            "manifest_sha256": manifest_sha,
            "counts": dict(Counter(item["action"] for item in result)),
            "files": result,
            "unlisted_current_files": "NOT_INSPECTED_OR_SELECTED",
            "recovery": [
                "Confirm a maintenance window and application-consistent stopped state independently.",
                "Make and verify a private backup; retain its manifest digest separately.",
                "Review this plan and recheck both trees before applying changes with another tool.",
                "Verify the resulting candidate version before starting the application.",
                "If recovery is needed, restore the verified backup to a new directory and review it before switching.",
            ],
        }


def launcher_check(candidate, manifest, manifest_sha, spec, spec_sha):
    with _root_scope(candidate):
        root, rows = verify(candidate, manifest, manifest_sha)
        metadata = selected_path(spec)
        if metadata.is_relative_to(root):
            refuse("LAUNCH_SPEC_MUST_BE_EXTERNAL")
        data = pinned_json(metadata, spec_sha)
        if (
            not isinstance(data, dict)
            or set(data)
            != {"schema_version", "executable", "working_directory", "arguments"}
            or type(data["schema_version"]) is not int
            or data["schema_version"] != 1
        ):
            refuse("INVALID_LAUNCH_SPEC")
        name = relative_name(data["executable"])
        if name not in {row["path"] for row in rows}:
            refuse("EXECUTABLE_NOT_IN_MANIFEST")
        working = data["working_directory"]
        if working != ".":
            working = relative_name(working)
            directory(root / working)
        arguments = data["arguments"]
        if (
            not isinstance(arguments, list)
            or len(arguments) > 64
            or any(
                not isinstance(arg, str)
                or len(arg) > 2048
                or any(ord(c) < 32 or ord(c) == 127 for c in arg)
                for arg in arguments
            )
            or sum(map(len, arguments)) > 8192
        ):
            refuse("INVALID_ARGUMENT_VECTOR")
        verify(root, manifest, manifest_sha)
        return {
            "schema_version": 1,
            "operation": "launcher-check",
            "execution_performed": False,
            "manifest_sha256": manifest_sha,
            "launch_spec_sha256": spec_sha,
            "argument_count": len(arguments),
            "executable_listed_and_verified": True,
            "working_directory_exists": True,
            "runtime_acceptance": "NOT_TESTED",
        }


def write_report(path, result, protected_roots):
    target = selected_path(path, missing=True)
    if target.is_relative_to(REPOSITORY) or any(
        target.is_relative_to(root) for root in protected_roots
    ):
        refuse("REPORT_MUST_BE_EXTERNAL")
    if not target.parent.is_dir():
        refuse("REPORT_PARENT_REQUIRED")
    raw = (json.dumps(result, indent=2, ensure_ascii=True) + "\n").encode()
    with _report_scope(target, protected_roots):
        if os.name == "nt":
            backend = _windows()
            backend.exclusive_write(target, raw, PreflightError)
            if backend.read_bounded(target, len(raw), PreflightError, single_link=True) != raw:
                refuse("REPORT_VERIFY_FAILED")
        else:
            _write_posix(target, raw)



class Parser(argparse.ArgumentParser):
    def error(self, message):
        refuse("INVALID_ARGUMENTS")


def main(argv=None):
    parser = Parser(description=__doc__, prog="preflight.py" if os.name == "nt" else None)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("verify", "plan", "launcher-check"):
        child = commands.add_parser(command)
        child.add_argument("--candidate", required=True)
        child.add_argument("--manifest", required=True)
        child.add_argument("--manifest-sha", required=True)
        child.add_argument("--report")
        if command == "plan":
            child.add_argument("--current", required=True)
        if command == "launcher-check":
            child.add_argument("--spec", required=True)
            child.add_argument("--spec-sha", required=True)
    try:
        args = parser.parse_args(argv)
        protected = [directory(args.candidate)]
        if args.command == "plan":
            protected.append(directory(args.current))
            result = update_plan(
                args.candidate, args.current, args.manifest, args.manifest_sha
            )
        elif args.command == "launcher-check":
            result = launcher_check(
                args.candidate,
                args.manifest,
                args.manifest_sha,
                args.spec,
                args.spec_sha,
            )
        else:
            _, rows = verify(args.candidate, args.manifest, args.manifest_sha)
            result = {
                "schema_version": 1,
                "operation": "verify",
                "execution_performed": False,
                "manifest_sha256": args.manifest_sha,
                "files_verified": len(rows),
            }
        if args.report:
            write_report(args.report, result, protected)
        summary = {
            key: value
            for key, value in result.items()
            if key not in {"files", "recovery"}
        }
        print(json.dumps({"status": "VERIFIED", **summary}, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        if os.name != "nt":
            raise
        print(json.dumps({"status": "ERROR", "code": "PREFLIGHT_INTERRUPTED", "execution_performed": False}))
        return 130
    except PreflightError as error:
        print(
            json.dumps(
                {"status": "ERROR", "code": str(error), "execution_performed": False}
            )
        )
        return 2
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "code": "PREFLIGHT_REFUSED_OR_FAILED",
                    "execution_performed": False,
                }
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
