#!/usr/bin/env python3
"""Convert an explicitly supplied pip JSON report to a new hash-pinned lock."""
from __future__ import annotations

import json
import os
from pathlib import Path

from lock_common import (LockError, MAX_LOCK_BYTES, MAX_PACKAGES, MAX_REPORT_BYTES, Parser,
                         checked_hash, checked_version, error_result, normalize_name,
                         read_bounded, require, strict_json, write_new)


def records_from_report(payload: dict) -> dict[str, tuple[str, str]]:
    require(type(payload) is dict and payload.get("version") == "1", "REPORT_VERSION_UNSUPPORTED")
    items = payload.get("install")
    require(type(items) is list and 1 <= len(items) <= MAX_PACKAGES, "REPORT_RECORD_LIMIT")
    records = {}
    for item in items:
        require(type(item) is dict and type(item.get("metadata")) is dict, "REPORT_RECORD_INVALID")
        metadata = item["metadata"]
        name = normalize_name(metadata.get("name"))
        version = checked_version(metadata.get("version"))
        download = item.get("download_info")
        require(type(download) is dict and type(download.get("archive_info")) is dict, "ARCHIVE_HASH_REQUIRED")
        archive = download["archive_info"]
        hashes = archive.get("hashes", {})
        require(type(hashes) is dict, "ARCHIVE_HASH_INVALID")
        modern = checked_hash(hashes["sha256"]) if "sha256" in hashes else None
        legacy = None
        if "hash" in archive:
            raw = archive["hash"]
            require(type(raw) is str, "ARCHIVE_HASH_INVALID")
            if raw.startswith("sha256="):
                legacy = checked_hash(raw[7:])
        require(modern is not None or legacy is not None, "ARCHIVE_HASH_REQUIRED")
        require(modern is None or legacy is None or modern == legacy, "ARCHIVE_HASH_CONFLICT")
        current = (version, modern or legacy)
        require(name not in records or records[name] == current, "PACKAGE_ARTIFACT_CONFLICT")
        records[name] = current
    return records


def render_lock(records: dict[str, tuple[str, str]]) -> bytes:
    require(type(records) is dict and 1 <= len(records) <= MAX_PACKAGES, "REPORT_RECORD_LIMIT")
    lines = ["# OUTLANDS dependency lock", "# Offline conversion only; no resolution, download or installation.", ""]
    for name in sorted(records):
        require(normalize_name(name) == name, "PACKAGE_NAME_NONCANONICAL")
        version, digest = records[name]
        lines.extend([f"{name}=={checked_version(version)} \\", f"    --hash=sha256:{checked_hash(digest)}"])
    result = ("\n".join(lines) + "\n").encode("ascii")
    require(len(result) <= MAX_LOCK_BYTES, "OUTPUT_SIZE_LIMIT")
    return result


def convert(report: Path, output: Path) -> int:
    records = records_from_report(strict_json(read_bounded(report, MAX_REPORT_BYTES)))
    write_new(output, render_lock(records))
    return len(records)


def main(argv=None) -> int:
    try:
        parser = Parser(prog="report_to_lock.py", description=__doc__)
        parser.add_argument("--report", required=True, type=str if os.name == "nt" else Path)
        parser.add_argument("--output", required=True, type=str if os.name == "nt" else Path)
        args = parser.parse_args(argv)
        count = convert(args.report, args.output)
        print(json.dumps({"result": "LOCK_WRITTEN", "packages": count}, sort_keys=True))
        return 0
    except LockError as error:
        return error_result(str(error))
    except KeyboardInterrupt:
        return error_result("INTERRUPTED")
    except (OSError, ValueError, UnicodeError):
        return error_result("INPUT_OR_IO_ERROR")


if __name__ == "__main__":
    raise SystemExit(main())
