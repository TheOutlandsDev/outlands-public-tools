#!/usr/bin/env python3
"""Compare supplied Source Inventory reports without reopening inventoried files."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys

VERSION = "0.1.0"
MAX_CSV_BYTES = 16 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_ROWS = 10000
MAX_PATH_CHARS = 4096
HEADERS = ["path", "path_escaped", "bytes", "modified_utc", "sha256", "status"]
ENCODING = "Remove one leading apostrophe only when path_escaped is true."
SUMMARY_KEYS = {
    "schema_version",
    "label",
    "created_at_utc",
    "coverage",
    "file_count",
    "hashed_file_count",
    "total_bytes",
    "top_level_counts",
    "skipped",
    "files_csv_sha256",
    "path_encoding",
    "limits",
    "default_excluded_directories",
    "default_excluded_suffixes",
    "additional_excluded_directories",
    "tree",
}
SUMMARY_REQUIRED = SUMMARY_KEYS - {"additional_excluded_directories", "tree"}
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit
    for prefix in ("com", "lpt")
    for digit in "123456789\u00b9\u00b2\u00b3"
}


class DiffError(Exception):
    """A fixed code without input paths, supplied values or native details."""


def _fail(code):
    raise DiffError(code) from None


def _require(value, code):
    if not value:
        _fail(code)


def _csv_path(value: str) -> tuple[str, str]:
    # Quoting CSV alone does not stop spreadsheet formula evaluation.
    stripped = value.lstrip()
    unsafe = value.startswith(("'", "\t", "\r", "\n")) or stripped.startswith(
        ("=", "+", "-", "@")
    )
    return ("'" + value, "true") if unsafe else (value, "false")


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        _require(key not in result, "JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _not_number(_value: str):
    raise DiffError("JSON_INTEGER_REQUIRED")


def _json(data: bytes) -> dict:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=_not_number,
            parse_constant=_not_number,
        )
    except (UnicodeError, ValueError, RecursionError):
        raise DiffError("INVALID_JSON") from None
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        _require(depth <= 16 and nodes <= 50000, "JSON_STRUCTURE_LIMIT")
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for v in item.values())
            _require(
                all(isinstance(k, str) and len(k) <= MAX_PATH_CHARS for k in item),
                "JSON_STRING_LIMIT",
            )
            try:
                for key in item:
                    key.encode("utf-8")
            except UnicodeError:
                raise DiffError("INVALID_JSON_TEXT") from None
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
        elif isinstance(item, str):
            _require(len(item) <= MAX_PATH_CHARS, "JSON_STRING_LIMIT")
            try:
                item.encode("utf-8")
            except UnicodeError:
                raise DiffError("INVALID_JSON_TEXT") from None
    _require(type(value) is dict, "JSON_OBJECT_REQUIRED")
    return value


def _keys(value: object, required: set[str], allowed: set[str]) -> None:
    _require(
        type(value) is dict and required <= value.keys() <= allowed,
        "JSON_FIELDS_INVALID",
    )


def _integer(value: object, maximum: int) -> bool:
    return type(value) is int and 0 <= value <= maximum


def _utc(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)
    except ValueError:
        return False


def _digest(value: object) -> bool:
    return (
        isinstance(value, str) and re.fullmatch(r"[0-9A-Fa-f]{64}", value) is not None
    )


def parse_inventory(csv_bytes: bytes, summary_bytes: bytes) -> tuple[list[dict], dict]:
    _require(
        type(csv_bytes) is bytes and type(summary_bytes) is bytes,
        "REPORT_BYTES_REQUIRED",
    )
    _require(
        len(csv_bytes) <= MAX_CSV_BYTES and len(summary_bytes) <= MAX_JSON_BYTES,
        "INPUT_BYTE_LIMIT",
    )
    summary = _json(summary_bytes)
    _keys(summary, SUMMARY_REQUIRED, SUMMARY_KEYS)
    _require(
        summary["schema_version"] == "outlands.source_inventory.v1"
        and summary["coverage"] == "selected_regular_files_only"
        and summary["path_encoding"] == ENCODING,
        "INVENTORY_SCHEMA_UNSUPPORTED",
    )
    _require(
        _digest(summary["files_csv_sha256"])
        and hashlib.sha256(csv_bytes).hexdigest().upper()
        == summary["files_csv_sha256"].upper(),
        "CSV_HASH_MISMATCH",
    )
    _require(
        _integer(summary["file_count"], MAX_ROWS)
        and summary["hashed_file_count"] == summary["file_count"]
        and type(summary["hashed_file_count"]) is int
        and _integer(summary["total_bytes"], 256 * 1024 * 1024),
        "INVENTORY_TOTALS_INVALID",
    )
    _require(
        isinstance(summary["label"], str)
        and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", summary["label"]) is not None
        and _utc(summary["created_at_utc"]),
        "INVENTORY_METADATA_INVALID",
    )
    _keys(
        summary["skipped"],
        {"directories", "files", "links", "nonregular"},
        {"directories", "files", "links", "nonregular"},
    )
    _require(
        all(_integer(n, 10000) for n in summary["skipped"].values()),
        "INVENTORY_METADATA_INVALID",
    )
    _keys(
        summary["limits"],
        {"max_files", "max_file_bytes", "max_total_bytes", "max_entries"},
        {"max_files", "max_file_bytes", "max_total_bytes", "max_entries"},
    )
    _require(
        all(
            type(n) is int and 0 < n <= ceiling
            for n, ceiling in zip(
                (
                    summary["limits"][k]
                    for k in (
                        "max_files",
                        "max_file_bytes",
                        "max_total_bytes",
                        "max_entries",
                    )
                ),
                (MAX_ROWS, 64 * 1024 * 1024, 256 * 1024 * 1024, 10000),
            )
        ),
        "INVENTORY_METADATA_INVALID",
    )
    for key in (
        "default_excluded_directories",
        "default_excluded_suffixes",
        "additional_excluded_directories",
    ):
        if key in summary:
            _require(
                type(summary[key]) is list
                and len(summary[key]) <= 256
                and all(isinstance(s, str) and 0 < len(s) <= 255 for s in summary[key]),
                "INVENTORY_METADATA_INVALID",
            )
    _require(
        type(summary["top_level_counts"]) is dict
        and all(_integer(n, MAX_ROWS) for n in summary["top_level_counts"].values()),
        "INVENTORY_METADATA_INVALID",
    )
    if "tree" in summary:
        _require(type(summary["tree"]) is dict, "INVENTORY_METADATA_INVALID")
    try:
        text = csv_bytes.decode("utf-8")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        _require(next(reader, None) == HEADERS, "CSV_HEADER_INVALID")
        rows, seen, total, top = [], set(), 0, {}
        for fields in reader:
            _require(
                len(rows) < MAX_ROWS and len(fields) == len(HEADERS), "CSV_ROWS_INVALID"
            )
            row = dict(zip(HEADERS, fields))
            encoded, escaped = row["path"], row["path_escaped"]
            _require(
                escaped in ("true", "false") and 0 < len(encoded) <= MAX_PATH_CHARS + 1,
                "CSV_PATH_INVALID",
            )
            _require(
                escaped == "false" or encoded.startswith("'"), "CSV_ESCAPE_INVALID"
            )
            path = encoded[1:] if escaped == "true" else encoded
            _require(_csv_path(path) == (encoded, escaped), "CSV_ESCAPE_INVALID")
            # These strings are data only. They are never joined to a filesystem root.
            _require(
                path
                and len(path) <= MAX_PATH_CHARS
                and not path.startswith(("/", "\\"))
                and re.match(r"^[A-Za-z]:", path) is None
                and "\x00" not in path
                and all(part not in ("", ".", "..") for part in path.split("/")),
                "CSV_PATH_INVALID",
            )
            _require(path not in seen, "CSV_PATH_DUPLICATE")
            seen.add(path)
            _require(
                re.fullmatch(r"0|[1-9][0-9]{0,8}", row["bytes"]) is not None,
                "CSV_BYTES_INVALID",
            )
            size = int(row["bytes"])
            _require(
                size <= summary["limits"]["max_file_bytes"]
                and _digest(row["sha256"])
                and row["status"] == "ok"
                and _utc(row["modified_utc"]),
                "CSV_ROW_INVALID",
            )
            total += size
            _require(
                total <= summary["limits"]["max_total_bytes"],
                "INVENTORY_TOTALS_INVALID",
            )
            top[path.split("/", 1)[0]] = top.get(path.split("/", 1)[0], 0) + 1
            rows.append(
                {
                    "path": path,
                    "bytes": size,
                    "sha256": row["sha256"].lower(),
                    "modified_utc": datetime.fromisoformat(
                        row["modified_utc"]
                    ).isoformat(),
                }
            )
    except (UnicodeError, csv.Error):
        raise DiffError("CSV_INVALID") from None
    _require(
        len(rows) == summary["file_count"]
        and len(rows) <= summary["limits"]["max_files"]
        and total == summary["total_bytes"]
        and top == summary["top_level_counts"],
        "INVENTORY_TOTALS_MISMATCH",
    )
    rows.sort(key=lambda row: (row["path"].casefold(), row["path"]))
    return rows, summary


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


def _flags():
    return dict(
        roots_scanned=False,
        inventoried_files_opened=False,
        files_modified=False,
        files_deleted=False,
        renames_verified=False,
        canonical_copy_selected=False,
        authenticity_verified=False,
        scope_equivalence_verified=False,
        tree_metadata_compared=False,
        network_probed=False,
    )


def _path_order(value):
    return value.casefold(), value


def _coverage(summary):
    directories = summary["default_excluded_directories"] + summary.get(
        "additional_excluded_directories", []
    )
    return (
        frozenset(value.casefold() for value in directories),
        frozenset(value.casefold() for value in summary["default_excluded_suffixes"]),
        summary["limits"],
    )


def compare_reports(before_csv, before_summary, after_csv, after_summary):
    """Compare validated supplied bytes; path strings are never filesystem targets."""
    old_rows, old_summary = parse_inventory(before_csv, before_summary)
    new_rows, new_summary = parse_inventory(after_csv, after_summary)
    old = {row["path"]: row for row in old_rows}
    new = {row["path"]: row for row in new_rows}
    counts = dict(
        only_in_before=0,
        only_in_after=0,
        hash_or_size_changed=0,
        mtime_only_changed=0,
        unchanged=0,
    )
    rows = []
    for path in sorted(old.keys() | new.keys(), key=_path_order):
        left, right = old.get(path), new.get(path)
        if left is None:
            kind = "ONLY_IN_AFTER"
        elif right is None:
            kind = "ONLY_IN_BEFORE"
        elif (left["sha256"], left["bytes"]) != (right["sha256"], right["bytes"]):
            kind = "HASH_OR_SIZE_CHANGED"
        elif left["modified_utc"] != right["modified_utc"]:
            kind = "MTIME_ONLY_CHANGED"
        else:
            kind = "UNCHANGED"
        counts[kind.lower()] += 1
        rows.append(
            dict(
                path=path,
                classification=kind,
                before=None
                if left is None
                else {key: left[key] for key in ("bytes", "sha256", "modified_utc")},
                after=None
                if right is None
                else {key: right[key] for key in ("bytes", "sha256", "modified_utc")},
            )
        )

    folded, content, digest_sizes = {}, {}, {}
    for side, records in (("before", old_rows), ("after", new_rows)):
        for row in records:
            group = folded.setdefault(row["path"].casefold(), dict(before=[], after=[]))
            group[side].append(row["path"])
            group = content.setdefault(
                (row["sha256"], row["bytes"]), dict(before=[], after=[])
            )
            group[side].append(row["path"])
            digest_sizes.setdefault(row["sha256"], set()).add(row["bytes"])
    ambiguities = []
    for key in sorted(folded):
        group = folded[key]
        if len(set(group["before"]) | set(group["after"])) > 1:
            ambiguities.append(
                dict(
                    before_paths=sorted(group["before"], key=_path_order),
                    after_paths=sorted(group["after"], key=_path_order),
                )
            )
    hints = []
    for (digest, size), group in sorted(content.items()):
        left, right = (
            sorted(group["before"], key=_path_order),
            sorted(group["after"], key=_path_order),
        )
        if len(left) > 1 or len(right) > 1 or (left and right and left != right):
            hints.append(
                dict(sha256=digest, bytes=size, before_paths=left, after_paths=right)
            )
    conflicts = [
        dict(sha256=digest, reported_sizes=sorted(sizes))
        for digest, sizes in sorted(digest_sizes.items())
        if len(sizes) > 1
    ]

    previous, current = _coverage(old_summary), _coverage(new_summary)
    coverage_issues = [
        code
        for index, code in enumerate(
            ("DIRECTORY_EXCLUSIONS_DIFFER", "SUFFIX_EXCLUSIONS_DIFFER", "LIMITS_DIFFER")
        )
        if previous[index] != current[index]
    ]
    issues = list(coverage_issues)
    if any(old_summary["skipped"].values()) or any(new_summary["skipped"].values()):
        issues.append("SKIPPED_ENTRIES_PRESENT")
    if ambiguities:
        issues.append("CASEFOLD_PATH_AMBIGUITY")
    if conflicts:
        issues.append("DIGEST_SIZE_CONFLICT")
    if hints:
        issues.append("HASH_SIZE_GROUP_HINTS_PRESENT")
    changed = any(value for key, value in counts.items() if key != "unchanged")
    status = (
        "REVIEW_REQUIRED"
        if issues
        else "DIFFERENCES_REPORTED"
        if changed
        else "MATCHING_SELECTED_RECORDS"
    )
    return dict(
        schema_version="outlands.inventory_diff.v1",
        status=status,
        scope="SUPPLIED_SELECTED_REGULAR_FILE_RECORDS_ONLY",
        **_flags(),
        counts=dict(before=len(old), after=len(new), **counts),
        issues=issues,
        coverage=dict(
            declarations_match=not coverage_issues,
            issues=coverage_issues,
            skipped_before=dict(old_summary["skipped"]),
            skipped_after=dict(new_summary["skipped"]),
        ),
        input_hashes=dict(
            before=dict(
                files_csv_sha256=hashlib.sha256(before_csv).hexdigest(),
                summary_json_sha256=hashlib.sha256(before_summary).hexdigest(),
            ),
            after=dict(
                files_csv_sha256=hashlib.sha256(after_csv).hexdigest(),
                summary_json_sha256=hashlib.sha256(after_summary).hexdigest(),
            ),
        ),
        rows=rows,
        casefold_ambiguities=ambiguities,
        hash_size_groups=hints,
        digest_size_conflicts=conflicts,
    )


def read_and_compare(before, after):
    """Read only two fixed files per selected run, then recheck their identities."""
    try:
        selected = [_selected_path(before), _selected_path(after)]
        inputs, checked = [], []
        for directory in selected:
            for name, maximum in (
                ("files.csv", MAX_CSV_BYTES),
                ("summary.json", MAX_JSON_BYTES),
            ):
                path = directory / name
                data, identity = _read_bytes(path, maximum)
                inputs.append(data)
                checked.append((path, identity))
        result = compare_reports(*inputs)
        for path, identity in checked:
            _require(_fingerprint(path) == identity, "INPUT_CHANGED")
        return result
    except DiffError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        _fail("INPUT_OR_REPORT_FAILED")


def render_report(result):
    """Bound serialized JSON before stdout receives any partial report."""
    chunks, size = [], 0
    encoder = json.JSONEncoder(ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    for chunk in encoder.iterencode(result):
        size += len(chunk)
        _require(size <= MAX_OUTPUT_BYTES, "OUTPUT_BYTE_LIMIT")
        chunks.append(chunk)
    return "".join(chunks)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        _fail("ARGUMENTS_INVALID")


def main(argv=None):
    parser = _Parser(
        prog="source-inventory-diff", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    exit_code = 2
    try:
        args = parser.parse_args(argv)
        result = read_and_compare(args.before, args.after)
        output = render_report(result)
        print(output)
        return 0 if result["status"] == "MATCHING_SELECTED_RECORDS" else 1
    except DiffError as error:
        code = str(error)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        code = "INPUT_OR_REPORT_FAILED"
    except KeyboardInterrupt:
        code, exit_code = "INTERRUPTED", 130
    print(json.dumps(dict(status="ERROR", code=code, **_flags()), sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
