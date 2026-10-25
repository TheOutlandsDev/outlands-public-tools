#!/usr/bin/env python3
"""Verify a local component release and plan updates without executing inputs."""

from __future__ import annotations

import argparse
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
    raw = Path(value)
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


def hash_file(value, *, limit=MAX_FILE, collect=False):
    path = selected_path(value)
    before = path.lstat()
    regular(before)
    if before.st_size > limit:
        refuse("FILE_SIZE_LIMIT")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    digest = hashlib.sha256()
    size = 0
    chunks = []
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        regular(opened)
        if identity(opened) != identity(before):
            refuse("INPUT_CHANGED")
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                refuse("FILE_SIZE_LIMIT")
            digest.update(chunk)
            if collect:
                chunks.append(chunk)
        if identity(os.fstat(stream.fileno())) != identity(before):
            refuse("INPUT_CHANGED")
    if identity(path.lstat()) != identity(before) or size != before.st_size:
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
        with os.scandir(folder) as entries:
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
    root = directory(candidate)
    metadata = selected_path(manifest)
    if metadata.is_relative_to(root):
        refuse("MANIFEST_MUST_BE_EXTERNAL")
    rows = manifest_rows(pinned_json(metadata, manifest_sha))
    if candidate_inventory(root, rows) != rows:
        refuse("CANDIDATE_MISMATCH")
    return root, rows


def update_plan(candidate, current, manifest, manifest_sha):
    source, rows = verify(candidate, manifest, manifest_sha)
    target = directory(current)
    if source.is_relative_to(target) or target.is_relative_to(source):
        refuse("NESTED_INPUT_ROOTS")
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
    with os.fdopen(
        os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        ),
        "wb",
    ) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


class Parser(argparse.ArgumentParser):
    def error(self, message):
        refuse("INVALID_ARGUMENTS")


def main(argv=None):
    parser = Parser(description=__doc__)
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
