"""Package selected saved reports and bounded, redacted text attachments."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import zipfile

from . import __version__
from .common import OpsKitError, utc_now


MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ATTACHMENTS = 16
_MAX_JSON_DEPTH = 32
_REDACTED = "[REDACTED]"
_SECRET_KEY = re.compile(r"(?:password|passwd|secret|token|api[_-]?key)$", re.IGNORECASE | re.ASCII)
_TEXT_ASSIGNMENT = re.compile(
    r"(?P<prefix>[ \t]*(?:export[ \t]+)?(?P<quote>[\"']?)(?P<key>[A-Za-z0-9_.-]+)"
    r"(?P=quote)[ \t]*[:=][ \t]*)(?P<value>[^\r\n]*)",
    re.IGNORECASE | re.ASCII,
)
_BINARY_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def _redact_text(text: str) -> tuple[str, bool]:
    lines = []
    redacted = False
    for line in text.splitlines(keepends=True):
        value = line.rstrip("\r\n\u2028\u2029")
        assignment = _TEXT_ASSIGNMENT.fullmatch(value)
        if assignment is not None and _SECRET_KEY.search(assignment["key"]) and assignment["value"]:
            lines.append(assignment["prefix"] + _REDACTED + line[len(value):])
            redacted = True
        else:
            lines.append(line)
    return "".join(lines), redacted


def _redact_json(value: Any, depth: int = 0) -> bool:
    if depth > _MAX_JSON_DEPTH:
        raise OpsKitError("A saved report exceeds the JSON nesting limit.")
    redacted = False
    if isinstance(value, dict):
        for key, item in value.items():
            if _SECRET_KEY.search(key):
                value[key] = _REDACTED
                redacted = True
            elif _redact_json(item, depth + 1):
                redacted = True
    elif isinstance(value, list):
        for item in value:
            if _redact_json(item, depth + 1):
                redacted = True
    return redacted


def _json_bytes(value: Any, limit: int) -> bytes:
    encoder = json.JSONEncoder(indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    data = bytearray()
    for fragment in encoder.iterencode(value):
        encoded = fragment.encode("utf-8")
        if len(data) + len(encoded) >= limit:
            raise OpsKitError("A normalized archive member exceeds the size limit.")
        data.extend(encoded)
    data.extend(b"\n")
    return bytes(data)


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    values = {}
    for key, value in pairs:
        if key in values:
            raise ValueError("Duplicate JSON key.")
        values[key] = value
    return values


def _reject_constant(_value: str) -> Any:
    raise ValueError("Nonfinite JSON constant.")


def _saved_report(text: str, limit: int) -> tuple[bytes, bool]:
    try:
        data = json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object.")
        redacted = _redact_json(data)
        return _json_bytes(data, limit), redacted
    except (ValueError, RecursionError):
        raise OpsKitError("A saved report is not a supported JSON object.") from None


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _ordinary(info: os.stat_result) -> bool:
    return not (
        stat.S_ISLNK(info.st_mode)
        or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _local_path(path: Path, home: Path | None = None) -> Path:
    if (path.anchor and not path.is_absolute()) or path.drive.startswith("\\\\") or path.anchor == "//":
        raise OpsKitError("Paths must select local files or directories.")
    absolute = (home / path if home is not None and not path.is_absolute() else path).absolute()
    if ".." in absolute.parts or (
        os.name == "nt" and any(":" in part or part.endswith((" ", ".")) for part in absolute.parts[1:])
    ):
        raise OpsKitError("A supplied path contains an unsupported component.")
    if os.name == "posix" and any(
        absolute.is_relative_to(directory) for directory in ("/dev", "/proc", "/sys")
    ):
        raise OpsKitError("Paths must select saved files or ordinary directories.")
    return absolute


def _directory_info(directory: Path) -> os.stat_result:
    current = Path(directory.anchor)
    info = current.lstat()
    for part in directory.parts[1:]:
        current /= part
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode) or not _ordinary(info):
            raise OpsKitError("A selected directory is not an ordinary directory.")
    return info


def _read_text(path: Path, limit: int) -> tuple[str, os.stat_result]:
    _directory_info(path.parent)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or not _ordinary(before):
        raise OpsKitError("An input must be an ordinary local file.")
    if before.st_size > limit:
        raise OpsKitError("An input exceeds the file size limit.")

    flags = (
        os.O_RDONLY | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as source:
        opened = os.fstat(source.fileno())
        if (
            not stat.S_ISREG(opened.st_mode) or not _ordinary(opened)
            or not os.path.samestat(before, opened)
        ):
            raise OpsKitError("An input changed before it was opened.")
        data = source.read(limit + 1)
        after = os.fstat(source.fileno())
        if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise OpsKitError("An input changed during collection.")
    if len(data) > limit:
        raise OpsKitError("An input exceeds the file size limit.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise OpsKitError("An input is not UTF-8 text.") from None
    if _BINARY_CONTROL.search(text):
        raise OpsKitError("An input contains binary control characters.")
    return text, opened


def _output_info(path: Path) -> os.stat_result | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or not _ordinary(info):
        raise OpsKitError("Output must select an ordinary local file.")
    return info


def _write_member(
    archive: zipfile.ZipFile,
    files: list[dict[str, Any]],
    name: str,
    content: bytes,
    *,
    generated: bool,
    redacted: bool,
) -> None:
    archive.writestr(name, content)
    files.append({
        "name": name,
        "bytes": len(content),
        "sha256": _sha256_bytes(content),
        "generated": generated,
        "redacted": redacted,
    })


def create_bundle(
    output: Path,
    home: Path,
    *,
    doctor_file: Path,
    inventory_file: Path,
    ports_file: Path,
    include_files: list[Path] | None = None,
    max_file_bytes: int = MAX_FILE_BYTES,
    force: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Create a bundle from explicitly named saved inputs and return its receipt."""
    if type(max_file_bytes) is not int or not 1 <= max_file_bytes <= MAX_FILE_BYTES:
        raise OpsKitError("The file size limit must be from 1 to 2097152 bytes.")
    attachments = include_files or []
    if len(attachments) > MAX_ATTACHMENTS:
        raise OpsKitError("Too many attachments were supplied.")
    selected = {
        "doctor.json": doctor_file,
        "inventory.json": inventory_file,
        "ports.json": ports_file,
    }
    files: list[dict[str, Any]] = []
    manifest = {
        "created_at": utc_now(),
        "opskit_version": __version__,
        "privacy": (
            "Only selected saved reports and text attachments are included. "
            "Redaction covers recognized keys and assignments."
        ),
        "files": files,
    }

    try:
        home = _local_path(home)
        _directory_info(home)
        destination = _local_path(output, home)
        parent = _directory_info(destination.parent)
        existing = _output_info(destination)
        if existing is not None and not force:
            raise OpsKitError("Incident bundle already exists. Use --force to replace it.")

        with TemporaryDirectory(prefix=".opskit-incident-", dir=destination.parent) as staging:
            partial = Path(staging) / "bundle.zip"
            with zipfile.ZipFile(partial, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for name, requested in selected.items():
                    path = _local_path(requested, home)
                    text, source = _read_text(path, max_file_bytes)
                    if existing is not None and os.path.samestat(existing, source):
                        raise OpsKitError("Output aliases a selected input.")
                    content, redacted = _saved_report(text, max_file_bytes)
                    _write_member(archive, files, name, content, generated=True, redacted=redacted)

                for index, requested in enumerate(attachments, start=1):
                    path = _local_path(requested, home)
                    text, source = _read_text(path, max_file_bytes)
                    if existing is not None and os.path.samestat(existing, source):
                        raise OpsKitError("Output aliases a selected input.")
                    text, redacted = _redact_text(text)
                    content = text.encode("utf-8")
                    if len(content) > max_file_bytes:
                        raise OpsKitError("A redacted attachment exceeds the size limit.")
                    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", path.name)
                    _write_member(archive, files, f"attachments/{index:02d}-{safe_name}", content,
                                  generated=False, redacted=redacted)

                archive.writestr("manifest.json", _json_bytes(manifest, MAX_FILE_BYTES))
            with partial.open("rb") as staged:
                digest = hashlib.file_digest(staged, "sha256").hexdigest()
                size = os.fstat(staged.fileno()).st_size

            if not os.path.samestat(parent, _directory_info(destination.parent)):
                raise OpsKitError("The output directory changed while staging the bundle.")
            if existing is None:
                os.link(partial, destination)
            else:
                current = _output_info(destination)
                if current is None or not os.path.samestat(existing, current):
                    raise OpsKitError("The selected output changed while staging the bundle.")
                os.replace(partial, destination)
    except FileExistsError:
        raise OpsKitError("An output appeared while the bundle was being created.") from None
    except (OSError, ValueError, zipfile.BadZipFile):
        raise OpsKitError("The supplied incident bundle could not be created.") from None

    return {
        "path": str(destination),
        "bytes": size,
        "sha256": digest,
        "generated_files": len(selected),
        "included_attachments": len(attachments),
        "forced_replace": existing is not None,
    }, []
