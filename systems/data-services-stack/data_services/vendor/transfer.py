#!/usr/bin/env python3
"""Reviewed source packages and private opaque stopped-state handoffs. Offline."""

from __future__ import annotations
import argparse
from contextlib import contextmanager, ExitStack
import importlib.util
import codecs
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import unicodedata

REPOSITORY = Path(__file__).resolve().parents[2]
MAX_FILES = 10000
MAX_ENTRIES = 20000
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_METADATA = 4 * 1024 * 1024
SOURCE_FILE_LIMIT = 2 * 1024 * 1024
SOURCE_TOTAL_LIMIT = 64 * 1024 * 1024
SOURCE_FORMAT = "reviewed-source-package-v1"
DATA_FORMAT = "opaque-data-handoff-v1"
MANIFEST = "MANIFEST.json"
CHECKSUM = "MANIFEST.sha256"
HASH = re.compile(r"[a-f0-9]{64}\Z")
RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}
CONTROL_DIRS = {".git", ".aws", ".codex", ".agents", "node_modules"}
PRIVATE_DIRS = CONTROL_DIRS | {
    "runtime",
    "private",
    "logs",
    "backups",
    "secrets",
    "credentials",
    "submissions",
    "artifacts",
    "evidence",
    "uploads",
    "downloads",
}
SOURCE_EXTENSIONS = {
    ".py",
    ".ps1",
    ".sh",
    ".bat",
    ".cmd",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".cs",
    ".php",
    ".sql",
    ".md",
    ".txt",
    ".rst",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".css",
    ".csv",
}
SOURCE_NAMES = {
    ".gitignore",
    ".gitattributes",
    "license",
    "copying",
    "notice",
    "dockerfile",
    "makefile",
}


class TransferError(ValueError):
    pass


def fail(code):
    raise TransferError(code)


def identity(info):
    # Windows path/handle stat calls can disagree on deprecated st_ctime.
    # Python 3.12 exposes creation time explicitly as st_birthtime_ns.
    stamp = (
        getattr(info, "st_birthtime_ns", None) if os.name == "nt" else info.st_ctime_ns
    )
    if stamp is None:
        fail("PLATFORM_IDENTITY_UNAVAILABLE")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, stamp)


def check_type(info, *, directory=False):
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        fail("LINK_OR_REPARSE")
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        fail("TYPE_UNSUPPORTED")
    if not directory and info.st_nlink != 1:
        fail("HARDLINK_UNSUPPORTED")


def selected_path(value, *, output=False):
    raw = _windows().selected_path(value, _windows()._core(TransferError)) if os.name == "nt" else Path(value)
    if ".." in raw.parts:
        fail("PARENT_TRAVERSAL")
    path = Path(os.path.abspath(raw))
    if os.name == "nt" and any(":" in part for part in path.parts[1:]):
        fail("STREAM_PATH_UNSUPPORTED")
    for ancestor in [*reversed(path.parents), path]:
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            continue
        check_type(info, directory=ancestor != path or stat.S_ISDIR(info.st_mode))
    if path.parent == path:
        fail("FILESYSTEM_ROOT_UNSUPPORTED")
    if output and path.is_relative_to(REPOSITORY):
        fail("OUTPUT_INSIDE_REPOSITORY")
    if os.name == "nt":
        backend = _windows()
        backend.checked_selection(path, True, TransferError)
        if output:
            with backend.output_scope(path, REPOSITORY, TransferError):
                pass
    return path


def disjoint(source, destination):
    if source.is_relative_to(destination) or destination.is_relative_to(source):
        fail("NESTED_DESTINATION")
    if os.name == "nt" and destination.parent.is_dir():
        _windows().separate_destination(source, destination, TransferError)



def relative_name(value):
    if (
        not isinstance(value, str)
        or not 0 < len(value) <= 240
        or unicodedata.normalize("NFC", value) != value
    ):
        fail("INVALID_RELATIVE_NAME")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        fail("INVALID_RELATIVE_NAME")
    for part in value.split("/"):
        if (
            part in {"", ".", ".."}
            or part.endswith((".", " "))
            or part.split(".")[0].casefold() in RESERVED
        ):
            fail("INVALID_RELATIVE_NAME")
        if any(
            ord(char) < 32 or ord(char) == 127 or char in '\\:<>"|?*' for char in part
        ):
            fail("INVALID_RELATIVE_NAME")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def validate_inventory(rows, *, source=False):
    if not isinstance(rows, list) or not 0 < len(rows) <= MAX_FILES:
        fail("INVALID_INVENTORY")
    seen = {}
    result = []
    total = 0
    file_names = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "size", "sha256"}:
            fail("INVALID_ENTRY")
        name = relative_name(row["path"])
        parts = name.split("/")
        for index in range(1, len(parts) + 1):
            prefix = "/".join(parts[:index])
            key = prefix.casefold()
            if key in seen and seen[key] != prefix:
                fail("CASE_COLLISION")
            seen[key] = prefix
        if name in file_names:
            fail("DUPLICATE_PATH")
        file_names.add(name)
        if (
            type(row["size"]) is not int
            or not 0 <= row["size"] <= (SOURCE_FILE_LIMIT if source else MAX_FILE)
            or not isinstance(row["sha256"], str)
            or not HASH.fullmatch(row["sha256"])
        ):
            fail("INVALID_ENTRY")
        if any(
            part.casefold() in CONTROL_DIRS or part.casefold().startswith(".venv")
            for part in parts
        ):
            fail("CONTROL_DIRECTORY_UNSUPPORTED")
        if parts[-1].endswith(("-wal", "-shm", "-journal")):
            fail("DATABASE_SIDECAR_UNSUPPORTED")
        if source:
            if any(part.casefold() in PRIVATE_DIRS for part in parts[:-1]):
                fail("PRIVATE_SOURCE_PATH")
            filename = parts[-1].casefold()
            if (
                filename.startswith(".env")
                or filename in {"id_rsa", "id_ed25519"}
                or filename.endswith(
                    ("ed25519", ".pem", ".pfx", ".key", ".db", ".sqlite", ".sqlite3")
                )
            ):
                fail("PRIVATE_SOURCE_PATH")
            if (
                PurePosixPath(name).suffix.lower() not in SOURCE_EXTENSIONS
                and filename not in SOURCE_NAMES
            ):
                fail("SOURCE_FORMAT_UNSUPPORTED")
        total += row["size"]
        if total > (SOURCE_TOTAL_LIMIT if source else MAX_TOTAL):
            fail("TOTAL_LIMIT")
        result.append(dict(path=name, size=row["size"], sha256=row["sha256"]))
    files = {row["path"].casefold() for row in result}
    for row in result:
        parts = row["path"].casefold().split("/")
        if any("/".join(parts[:index]) in files for index in range(1, len(parts))):
            fail("FILE_DIRECTORY_COLLISION")
    return sorted(result, key=lambda row: row["path"])


_WINDOWS_BACKEND = None


def _windows():
    global _WINDOWS_BACKEND
    if _WINDOWS_BACKEND is None:
        spec = importlib.util.spec_from_file_location(
            "outlands_transfer_windows", Path(__file__).with_name("transfer_windows.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _WINDOWS_BACKEND = module
    return _WINDOWS_BACKEND


def _posix_chain(path):
    rows = []
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        check_type(info, directory=True)
        rows.append((part, info.st_dev, info.st_ino, info.st_mode))
    return tuple(rows)


@contextmanager
def _root_scope(value):
    path = selected_path(value)
    check_type(path.lstat(), directory=True)
    if os.name == "nt":
        with _windows().root_scope(path, TransferError):
            yield path
    else:
        before = _posix_chain(path)
        yield path
        if _posix_chain(path) != before:
            fail("INPUT_CHANGED")


@contextmanager
def _entries(path):
    with _root_scope(path):
        with os.scandir(path) as entries:
            yield entries



@contextmanager
def _input_scope(path, maximum):
    if os.name == "nt":
        with _windows().regular(path, TransferError, single_link=True, maximum=maximum) as fd:
            yield fd
    else:
        before = _posix_chain(path.parent)
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        try:
            os.set_inheritable(fd, False)
            check_type(os.fstat(fd))
            yield fd
            check_type(os.fstat(fd))
            if _posix_chain(path.parent) != before:
                fail("INPUT_CHANGED")
        finally:
            os.close(fd)


@contextmanager
def _output_parent_scope(value):
    path = selected_path(value, output=True)
    if not path.parent.is_dir():
        fail("DESTINATION_PARENT_REQUIRED")
    if os.name == "nt":
        with _windows().output_scope(path, REPOSITORY, TransferError):
            yield path
    else:
        before = _posix_chain(path.parent)
        yield path
        if _posix_chain(path.parent) != before:
            fail("OUTPUT_CHANGED")


def _mkdir(path):
    with _output_parent_scope(path):
        path.mkdir(mode=0o700)
        with _root_scope(path):
            pass


def _ensure_parent(path, root):
    root = selected_path(root, output=True)
    relative = path.relative_to(root)
    current = root
    for name in relative.parts:
        with _root_scope(current):
            current = current / name
            if not current.exists():
                _mkdir(current)
            with _root_scope(current):
                pass


class _Writer:
    def __init__(self, fd):
        self.fd, self.size, self.digest = fd, 0, hashlib.sha256()

    def write(self, data):
        if type(data) is not bytes:
            fail("OUTPUT_BYTES_REQUIRED")
        position = 0
        while position < len(data):
            block = data[position:position + 65536]
            count = os.write(self.fd, block)
            if not 0 < count <= len(block):
                fail("OUTPUT_IO_ERROR")
            position += count
        self.digest.update(data)
        self.size += len(data)


@contextmanager
def _new_fd(path):
    if os.name == "nt":
        with _windows().new_file(path, REPOSITORY, TransferError) as fd:
            yield fd
    else:
        flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        fd = os.open(path, flags, 0o600)
        try:
            os.set_inheritable(fd, False)
            yield fd
        finally:
            os.close(fd)


@contextmanager
def _output_stream(value):
    with _output_parent_scope(value) as path, _new_fd(path) as fd:
        before = os.fstat(fd)
        check_type(before)
        if before.st_size != 0:
            fail("OUTPUT_CHANGED")
        writer = _Writer(fd)
        yield writer
        os.fsync(fd)
        written = os.fstat(fd)
        check_type(written)
        if identity(written)[:2] != identity(before)[:2] or written.st_size != writer.size:
            fail("OUTPUT_CHANGED")
        expected = dict(size=writer.size, sha256=writer.digest.hexdigest())
        if checked_file(path, max_bytes=writer.size) != expected:
            fail("OUTPUT_VERIFY_FAILED")
        after, final = os.fstat(fd), path.lstat()
        check_type(after)
        check_type(final)
        if identity(written) != identity(after) or identity(after) != identity(final):
            fail("OUTPUT_CHANGED")


def checked_file(
    path, *, expected=None, output=None, text=False, collect=False, max_bytes=None
):
    path = selected_path(path)
    before = path.lstat()
    check_type(before)
    limit = SOURCE_FILE_LIMIT if text else MAX_FILE
    if max_bytes is not None:
        limit = min(limit, max_bytes)
    if before.st_size > limit:
        fail("FILE_LIMIT")
    digest = hashlib.sha256()
    count = 0
    chunks = []
    decoder = codecs.getincrementaldecoder("utf-8-sig")() if text else None
    with _input_scope(path, limit) as incoming, ExitStack() as writes:
        opened = os.fstat(incoming)
        check_type(opened)
        if identity(opened) != identity(before):
            fail("INPUT_CHANGED")
        target = writes.enter_context(_output_stream(output)) if output is not None else None
        while chunk := os.read(incoming, min(1024 * 1024, limit + 1 - count)):
            count += len(chunk)
            if count > limit:
                fail("FILE_LIMIT")
            if decoder is not None:
                if b"\x00" in chunk:
                    fail("BINARY_SOURCE_CONTENT")
                decoder.decode(chunk)
            digest.update(chunk)
            if collect:
                chunks.append(chunk)
            if target is not None:
                target.write(chunk)
        if decoder is not None:
            decoder.decode(b"", final=True)
        after = os.fstat(incoming)
        final = path.lstat()
        check_type(after)
        check_type(final)
        if (identity(after) != identity(before) or identity(final) != identity(before)
                or count != before.st_size):
            fail("INPUT_CHANGED")
    row = dict(size=count, sha256=digest.hexdigest())
    if expected is not None and any(
        row[key] != expected[key] for key in ("size", "sha256")
    ):
        fail("HASH_OR_SIZE_MISMATCH")
    return (row, b"".join(chunks)) if collect else row


def small_bytes(path):
    path = selected_path(path)
    if path.stat().st_size > MAX_METADATA:
        fail("METADATA_LIMIT")
    return checked_file(path, collect=True, max_bytes=MAX_METADATA)[1]


def parse_json(data):
    if len(data) > MAX_METADATA:
        fail("METADATA_LIMIT")
    return json.loads(
        data.decode("utf-8-sig"),
        object_pairs_hook=unique_object,
        parse_constant=lambda _: fail("NONSTANDARD_JSON"),
    )


def inventory(root):
    with _root_scope(root):
        root = selected_path(root)
        check_type(root.lstat(), directory=True)
        if root.name.casefold() in CONTROL_DIRS:
            fail("CONTROL_DIRECTORY_UNSUPPORTED")
        rows = []
        stack = [root]
        entries_seen = 0
        total = 0
        while stack:
            directory = stack.pop()
            check_type(directory.lstat(), directory=True)
            with _entries(directory) as iterator:
                for entry in iterator:
                    entries_seen += 1
                    if entries_seen > MAX_ENTRIES:
                        fail("ENTRY_LIMIT")
                    path = Path(entry.path)
                    info = path.lstat()
                    if entry.is_dir(follow_symlinks=False):
                        check_type(info, directory=True)
                        if (
                            entry.name.casefold() in CONTROL_DIRS
                            or entry.name.casefold().startswith(".venv")
                        ):
                            fail("CONTROL_DIRECTORY_UNSUPPORTED")
                        stack.append(path)
                        continue
                    check_type(info)
                    total += info.st_size
                    if len(rows) >= MAX_FILES or total > MAX_TOTAL:
                        fail("TOTAL_OR_COUNT_LIMIT")
                    relative = relative_name(path.relative_to(root).as_posix())
                    rows.append(dict(path=relative, **checked_file(path)))
        return validate_inventory(rows)


def write_new(path, data):
    with _output_stream(path) as stream:
        stream.write(data)



def new_destination(path):
    path = selected_path(path, output=True)
    if not path.parent.is_dir():
        fail("DESTINATION_PARENT_REQUIRED")
    _mkdir(path)
    return path


def copy_rows(source, destination, rows, *, text=False):
    with _root_scope(source), _root_scope(destination):
        for row in rows:
            target = destination / row["path"]
            _ensure_parent(target.parent, destination)
            selected_path(target, output=True)
            checked_file(source / row["path"], expected=row, output=target, text=text)
            checked_file(target, expected=row, text=text)


def make_bundle(source, destination, rows, format_name):
    with _root_scope(source), _output_parent_scope(destination):
        source = selected_path(source)
        destination = selected_path(destination, output=True)
        disjoint(source, destination)
        if destination.exists():
            fail("DESTINATION_EXISTS")
        text = format_name == SOURCE_FORMAT
        rows = validate_inventory(rows, source=text)
        for row in rows:
            checked_file(source / row["path"], expected=row, text=text)
        new_destination(destination)
        with _root_scope(destination):
            payload = destination / "payload"
            _mkdir(payload)
            copy_rows(source, payload, rows, text=text)
            # Recheck every selected input after copying, not just the last file.
            for row in rows:
                checked_file(source / row["path"], expected=row, text=text)
            data = (
                json.dumps(
                    dict(schema_version=1, format=format_name, inventory=rows),
                    indent=2,
                    ensure_ascii=True,
                )
                + "\n"
            ).encode("utf-8")
            if len(data) > MAX_METADATA:
                fail("METADATA_LIMIT")
            digest = hashlib.sha256(data).hexdigest()
            write_new(destination / MANIFEST, data)
            write_new(destination / CHECKSUM, (digest + "  " + MANIFEST + "\n").encode("ascii"))
            return verify(destination, expected_manifest_sha=digest)


def package_source(source, manifest, destination, *, expected_manifest_sha):
    with _root_scope(source):
        source = selected_path(source)
        check_type(source.lstat(), directory=True)
        if source.name.casefold() in CONTROL_DIRS:
            fail("CONTROL_DIRECTORY_UNSUPPORTED")
        if not isinstance(expected_manifest_sha, str) or not HASH.fullmatch(
            expected_manifest_sha.lower()
        ):
            fail("TRUSTED_SOURCE_MANIFEST_PIN_REQUIRED")
        manifest_bytes = small_bytes(manifest)
        if hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest_sha.lower():
            fail("SOURCE_MANIFEST_PIN_MISMATCH")
        data = parse_json(manifest_bytes)
        if (
            not isinstance(data, dict)
            or set(data) != {"schema_version", "inventory"}
            or type(data["schema_version"]) is not int
            or data["schema_version"] != 1
        ):
            fail("INVALID_SOURCE_MANIFEST")
        return make_bundle(
            source,
            destination,
            validate_inventory(data["inventory"], source=True),
            SOURCE_FORMAT,
        )


def backup(source, destination, *, confirm_stopped=False):
    if confirm_stopped is not True:
        fail("STOP_CONFIRMATION_REQUIRED")
    source = selected_path(source)
    if source.is_relative_to(REPOSITORY):
        fail("DATA_INSIDE_REPOSITORY")
    rows = inventory(source)
    result = make_bundle(source, destination, rows, DATA_FORMAT)
    if inventory(source) != rows:
        fail("INPUT_CHANGED")
    return result


def verify(bundle, *, expected_manifest_sha=None):
    with _root_scope(bundle):
        bundle = selected_path(bundle)
        check_type(bundle.lstat(), directory=True)
        names = []
        with _entries(bundle) as entries:
            for entry in entries:
                path = Path(entry.path)
                names.append(path.name)
                if len(names) > 3:
                    fail("UNEXPECTED_BUNDLE_ENTRY")
        if set(names) != {MANIFEST, CHECKSUM, "payload"}:
            fail("UNEXPECTED_BUNDLE_ENTRY")
        raw = small_bytes(bundle / MANIFEST)
        digest = hashlib.sha256(raw).hexdigest()
        if expected_manifest_sha is not None and (
            not isinstance(expected_manifest_sha, str)
            or not HASH.fullmatch(expected_manifest_sha.lower())
            or digest != expected_manifest_sha.lower()
        ):
            fail("MANIFEST_PIN_MISMATCH")
        if small_bytes(bundle / CHECKSUM) != (digest + "  " + MANIFEST + "\n").encode(
            "ascii"
        ):
            fail("MANIFEST_CHECKSUM_MISMATCH")
        data = parse_json(raw)
        if (
            not isinstance(data, dict)
            or set(data) != {"schema_version", "format", "inventory"}
            or type(data["schema_version"]) is not int
            or data["schema_version"] != 1
            or data["format"] not in {SOURCE_FORMAT, DATA_FORMAT}
        ):
            fail("INVALID_BUNDLE_MANIFEST")
        rows = validate_inventory(data["inventory"], source=data["format"] == SOURCE_FORMAT)
        if inventory(bundle / "payload") != rows:
            fail("PAYLOAD_MISMATCH")
        if data["format"] == SOURCE_FORMAT:
            for row in rows:
                checked_file(bundle / "payload" / row["path"], expected=row, text=True)
        if small_bytes(bundle / MANIFEST) != raw:
            fail("MANIFEST_CHANGED")
        return dict(format=data["format"], inventory=rows, manifest_sha256=digest)


def restore(bundle, destination, *, expected_manifest_sha, confirm_stopped=False):
    if confirm_stopped is not True:
        fail("STOP_CONFIRMATION_REQUIRED")
    if not isinstance(expected_manifest_sha, str) or not HASH.fullmatch(
        expected_manifest_sha.lower()
    ):
        fail("TRUSTED_MANIFEST_PIN_REQUIRED")
    source = selected_path(bundle)
    target = selected_path(destination, output=True)
    disjoint(source, target)
    result = verify(source, expected_manifest_sha=expected_manifest_sha)
    if result["format"] != DATA_FORMAT:
        fail("DATA_FORMAT_REQUIRED")
    if target.exists():
        fail("DESTINATION_EXISTS")
    new_destination(target)
    copy_rows(source / "payload", target, result["inventory"])
    if inventory(target) != result["inventory"]:
        fail("RESTORE_MISMATCH")
    verify(source, expected_manifest_sha=expected_manifest_sha)
    return result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        fail("INVALID_ARGUMENTS")


def main(argv=None):
    parser = Parser(description=__doc__, prog="transfer.py" if os.name == "nt" else None)
    commands = parser.add_subparsers(dest="command", required=True)
    package = commands.add_parser("package")
    package.add_argument("--source", required=True)
    package.add_argument("--manifest", required=True)
    package.add_argument("--expected-manifest-sha", required=True)
    package.add_argument("--destination", required=True)
    create = commands.add_parser("backup")
    create.add_argument("--source", required=True)
    create.add_argument("--destination", required=True)
    create.add_argument("--confirm-stopped", action="store_true")
    check = commands.add_parser("verify")
    check.add_argument("--bundle", required=True)
    check.add_argument("--expected-manifest-sha")
    recover = commands.add_parser("restore")
    recover.add_argument("--bundle", required=True)
    recover.add_argument("--destination", required=True)
    recover.add_argument("--expected-manifest-sha", required=True)
    recover.add_argument("--confirm-stopped", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.command == "package":
            result = package_source(
                args.source,
                args.manifest,
                args.destination,
                expected_manifest_sha=args.expected_manifest_sha,
            )
        elif args.command == "backup":
            result = backup(
                args.source, args.destination, confirm_stopped=args.confirm_stopped
            )
        elif args.command == "verify":
            result = verify(
                args.bundle, expected_manifest_sha=args.expected_manifest_sha
            )
        else:
            result = restore(
                args.bundle,
                args.destination,
                expected_manifest_sha=args.expected_manifest_sha,
                confirm_stopped=args.confirm_stopped,
            )
        print(
            json.dumps(
                dict(
                    status="VERIFIED",
                    operation=args.command,
                    format=result["format"],
                    files=len(result["inventory"]),
                    bytes=sum(row["size"] for row in result["inventory"]),
                    manifest_sha256=result["manifest_sha256"],
                ),
                sort_keys=True,
            )
        )
        return 0
    except KeyboardInterrupt:
        if os.name != "nt":
            raise
        print(json.dumps(dict(status="ERROR", code="TRANSFER_INTERRUPTED", partial_destination="retained")))
        return 130
    except (OSError, ValueError, UnicodeError, TypeError, KeyError, RecursionError):
        print(
            json.dumps(
                dict(
                    status="ERROR",
                    code="TRANSFER_REFUSED_OR_FAILED",
                    partial_destination="retained",
                )
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
