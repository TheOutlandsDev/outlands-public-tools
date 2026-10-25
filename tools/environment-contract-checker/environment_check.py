#!/usr/bin/env python3
"""Check declared prerequisite metadata without executing or reading targets."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time
import unicodedata

VERSION = "0.1.0"
REPOSITORY = Path(__file__).resolve().parents[2]
WINDOWS = os.name == "nt"
MAX_INPUT_BYTES = 65536
MAX_REQUIREMENTS = 128
MAX_PROGRAM_DIRS = 16
MAX_TARGET_PROBES = 2048
MAX_CHECK_SECONDS = 5.0
ID = re.compile(r"[a-z][a-z0-9_-]{0,39}")
PROGRAM = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
WINDOWS_SUFFIXES = (".exe", ".com", ".bat", ".cmd")
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit for prefix in ("com", "lpt") for digit in "123456789¹²³"
}


class ContractError(ValueError):
    """A fixed public error code; never include an input value."""


class _ProbeLimit(Exception):
    pass


def _fail(code):
    raise ContractError(code)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _lexical_path(value):
    try:
        raw = os.fspath(value)
        if not isinstance(raw, str) or not 0 < len(raw) <= 4096:
            _fail("SELECTED_PATH_INVALID")
        if raw.startswith(("\\\\", "//")) or any(
            ord(c) < 32 or ord(c) == 127 for c in raw
        ):
            _fail("SELECTED_PATH_INVALID")
        original = Path(raw)
        if ".." in original.parts:
            _fail("PARENT_TRAVERSAL")
        if original.drive and not original.is_absolute():
            _fail("DRIVE_RELATIVE_PATH_UNSUPPORTED")
        path = Path(os.path.abspath(original))
        if path.parent == path or len(path.parts) > 64 or len(str(path)) > 4096:
            _fail("SELECTED_PATH_INVALID")
        for part in path.parts:
            if part == path.anchor:
                continue
            if ":" in part:
                _fail("STREAM_OR_URL_PATH_UNSUPPORTED")
            if part.endswith((".", " ")) or part.split(".")[0].casefold() in RESERVED:
                _fail("SELECTED_PATH_INVALID")
        return path
    except (TypeError, OSError):
        _fail("SELECTED_PATH_INVALID")


def _relative_path(value):
    if not isinstance(value, str) or not 0 < len(value) <= 240:
        _fail("REQUIREMENT_PATH_INVALID")
    if unicodedata.normalize("NFC", value) != value:
        _fail("REQUIREMENT_PATH_INVALID")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or len(path.parts) > 32:
        _fail("REQUIREMENT_PATH_INVALID")
    for part in value.split("/"):
        if (
            part in {"", ".", ".."}
            or part.endswith((".", " "))
            or part.split(".")[0].casefold() in RESERVED
            or any(ord(c) < 32 or ord(c) == 127 or c in '\\:<>"|?*' for c in part)
        ):
            _fail("REQUIREMENT_PATH_INVALID")
    return value


def _program_name(value):
    if (
        not isinstance(value, str)
        or not PROGRAM.fullmatch(value)
        or value.endswith(".")
        or value.split(".")[0].casefold() in RESERVED
    ):
        _fail("PROGRAM_NAME_INVALID")
    return value


def parse_contract(data):
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "requirements"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["requirements"], list)
        or not 0 < len(data["requirements"]) <= MAX_REQUIREMENTS
    ):
        _fail("CONTRACT_SCHEMA_INVALID")
    result = []
    ids = set()
    for row in data["requirements"]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("id"), str)
            or not ID.fullmatch(row["id"])
        ):
            _fail("REQUIREMENT_ID_INVALID")
        if row["id"] in ids:
            _fail("DUPLICATE_REQUIREMENT_ID")
        ids.add(row["id"])
        kind = row.get("kind")
        if not isinstance(kind, str):
            _fail("REQUIREMENT_KIND_INVALID")
        if kind in {"file", "directory"}:
            if set(row) != {"id", "kind", "path"}:
                _fail("REQUIREMENT_SCHEMA_INVALID")
            _relative_path(row["path"])
        elif kind == "program":
            if set(row) != {"id", "kind", "name"}:
                _fail("REQUIREMENT_SCHEMA_INVALID")
            _program_name(row["name"])
        elif kind == "observation":
            if set(row) != {"id", "kind"}:
                _fail("REQUIREMENT_SCHEMA_INVALID")
        else:
            _fail("REQUIREMENT_KIND_INVALID")
        result.append(dict(row))
    return result


def parse_observations(data, requirements):
    rows = parse_contract(
        requirements
        if isinstance(requirements, dict)
        else {"schema_version": 1, "requirements": requirements}
    )
    allowed = {row["id"] for row in rows if row["kind"] == "observation"}
    if data is None:
        return {}
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "observations"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["observations"], list)
        or len(data["observations"]) > MAX_REQUIREMENTS
    ):
        _fail("OBSERVATIONS_SCHEMA_INVALID")
    result = {}
    for row in data["observations"]:
        if not isinstance(row, dict) or set(row) != {"id", "satisfied"}:
            _fail("OBSERVATION_SCHEMA_INVALID")
        key = row["id"]
        if not isinstance(key, str) or key not in allowed:
            _fail("OBSERVATION_ID_NOT_DECLARED")
        if key in result:
            _fail("DUPLICATE_OBSERVATION_ID")
        if type(row["satisfied"]) is not bool:
            _fail("OBSERVATION_VALUE_INVALID")
        result[key] = row["satisfied"]
    return result


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
    return base if directory else (*base, info.st_size, info.st_mtime_ns)


class _Budget:
    def __init__(self):
        self.started = time.monotonic()
        self.probes = 0

    def consume(self):
        if (
            self.probes >= MAX_TARGET_PROBES
            or time.monotonic() - self.started > MAX_CHECK_SECONDS
        ):
            raise _ProbeLimit
        self.probes += 1


def _observe(path, expected, budget=None):
    if budget is not None:
        budget.consume()
    snapshots = []
    try:
        for item in reversed([path, *path.parents]):
            info = item.lstat()
            if _linked(info):
                return "UNSAFE", "LINK_OR_REPARSE_UNSUPPORTED", None
            directory = stat.S_ISDIR(info.st_mode)
            if item != path and not directory:
                return "UNKNOWN", "ANCESTOR_TYPE_MISMATCH", None
            if item == path:
                if not directory and not stat.S_ISREG(info.st_mode):
                    return "UNSAFE", "NODE_TYPE_UNSUPPORTED", None
                if not directory and info.st_nlink != 1:
                    return "UNSAFE", "LINK_COUNT_UNSUPPORTED", None
                if directory != (expected == "directory"):
                    return "UNKNOWN", "TARGET_TYPE_MISMATCH", None
                leaf = info
            snapshots.append((item, _identity(info, directory=directory), directory))
        for item, before, directory in snapshots:
            now = item.lstat()
            if _linked(now):
                return "UNSAFE", "LINK_OR_REPARSE_UNSUPPORTED", None
            if _identity(now, directory=directory) != before:
                return "UNKNOWN", "METADATA_CHANGED", None
        return (
            "PRESENT",
            "DIRECTORY_METADATA"
            if expected == "directory"
            else "REGULAR_FILE_METADATA",
            leaf,
        )
    except FileNotFoundError:
        return "MISSING", "NOT_FOUND", None
    except (NotADirectoryError, OSError, ValueError):
        return "UNKNOWN", "METADATA_UNAVAILABLE", None


def _selected_existing(value, expected, code):
    path = _lexical_path(value)
    status, _, _ = _observe(path, expected)
    if status != "PRESENT":
        _fail(code)
    return path


def read_input_json(value):
    path = _selected_existing(value, "file", "INPUT_UNAVAILABLE_OR_UNSAFE")
    before = path.lstat()
    if before.st_size > MAX_INPUT_BYTES:
        _fail("INPUT_SIZE_LIMIT")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (
            _linked(opened)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or _identity(opened) != _identity(before)
        ):
            _fail("INPUT_CHANGED")
        data = stream.read(MAX_INPUT_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(data) > MAX_INPUT_BYTES:
        _fail("INPUT_SIZE_LIMIT")
    if (
        len(data) != before.st_size
        or _identity(after) != _identity(before)
        or _identity(path.lstat()) != _identity(before)
    ):
        _fail("INPUT_CHANGED")
    return json.loads(
        data.decode("utf-8-sig"),
        object_pairs_hook=_unique_object,
        parse_constant=lambda _: _fail("NONSTANDARD_JSON"),
    )


def _program_names(name):
    if not WINDOWS:
        return (name,)
    if name.casefold().endswith(WINDOWS_SUFFIXES):
        return (name,)
    return tuple(name + suffix for suffix in WINDOWS_SUFFIXES)


def _check_program(name, directories, budget):
    if not directories:
        return "UNKNOWN", "PROGRAM_SEARCH_NOT_SELECTED"
    uncertain = None
    for directory in directories:
        for candidate_name in _program_names(name):
            candidate = directory / candidate_name
            status, evidence, info = _observe(candidate, "file", budget)
            if status == "PRESENT":
                if not WINDOWS:
                    try:
                        executable = os.access(
                            candidate, os.X_OK, follow_symlinks=False
                        )
                        now = candidate.lstat()
                    except (OSError, NotImplementedError, TypeError):
                        uncertain = ("UNKNOWN", "EXECUTE_ACCESS_UNVERIFIED")
                        continue
                    if _linked(now):
                        return "UNSAFE", "LINK_OR_REPARSE_UNSUPPORTED"
                    if _identity(now) != _identity(info):
                        return "UNKNOWN", "METADATA_CHANGED"
                    if not executable:
                        uncertain = ("UNKNOWN", "EXECUTE_ACCESS_UNVERIFIED")
                        continue
                return "PRESENT", "PROGRAM_CANDIDATE_METADATA"
            if status == "UNSAFE":
                return status, evidence
            if status == "UNKNOWN":
                uncertain = status, evidence
    return uncertain or ("MISSING", "PROGRAM_NOT_FOUND")


def check_contract(contract, *, root=None, program_dirs=(), observations=None):
    requirements = parse_contract(contract)
    supplied = parse_observations(observations, requirements)
    selected_root = (
        _selected_existing(root, "directory", "ROOT_UNAVAILABLE_OR_UNSAFE")
        if root is not None
        else None
    )
    if program_dirs is None:
        program_dirs = ()
    if (
        not isinstance(program_dirs, (list, tuple))
        or len(program_dirs) > MAX_PROGRAM_DIRS
    ):
        _fail("PROGRAM_DIRECTORIES_INVALID")
    directories = []
    for value in program_dirs:
        path = _lexical_path(value)
        if path in directories:
            _fail("DUPLICATE_PROGRAM_DIRECTORY")
        directories.append(path)
    budget = _Budget()
    checks = []
    for requirement in requirements:
        kind = requirement["kind"]
        try:
            if kind == "observation":
                state = supplied.get(requirement["id"])
                status = "UNKNOWN"
                evidence = (
                    "OBSERVATION_NOT_SUPPLIED"
                    if state is None
                    else "OPERATOR_REPORTED_TRUE_UNVERIFIED"
                    if state
                    else "OPERATOR_REPORTED_FALSE_UNVERIFIED"
                )
            elif kind == "program":
                status, evidence = _check_program(
                    requirement["name"], directories, budget
                )
            elif selected_root is None:
                status, evidence = "UNKNOWN", "ROOT_NOT_SELECTED"
            else:
                status, evidence, _ = _observe(
                    selected_root / requirement["path"], kind, budget
                )
        except _ProbeLimit:
            status, evidence = "UNKNOWN", "PROBE_BUDGET_EXHAUSTED"
        checks.append(
            dict(id=requirement["id"], kind=kind, status=status, evidence=evidence)
        )
    counts = Counter(row["status"].lower() for row in checks)
    return dict(
        schema_version=1,
        status="ALL_PRESENT" if counts["present"] == len(checks) else "REVIEW_REQUIRED",
        scope="DECLARED_REQUIREMENTS_ONLY",
        target_contents_read=False,
        programs_executed=False,
        versions_verified=False,
        counts={
            key: counts[key] for key in ("present", "missing", "unknown", "unsafe")
        },
        checks=checks,
    )


def _report_data(result):
    fields = {
        "schema_version",
        "status",
        "scope",
        "target_contents_read",
        "programs_executed",
        "versions_verified",
        "counts",
        "checks",
    }
    if not isinstance(result, dict) or set(result) != fields:
        _fail("REPORT_SCHEMA_INVALID")
    if (
        type(result["schema_version"]) is not int
        or result["schema_version"] != 1
        or result["scope"] != "DECLARED_REQUIREMENTS_ONLY"
    ):
        _fail("REPORT_SCHEMA_INVALID")
    if any(
        result[key] is not False
        for key in ("target_contents_read", "programs_executed", "versions_verified")
    ):
        _fail("REPORT_SCHEMA_INVALID")
    checks = result["checks"]
    if not isinstance(checks, list) or not 0 < len(checks) <= MAX_REQUIREMENTS:
        _fail("REPORT_SCHEMA_INVALID")
    evidence_codes = {
        "ROOT_NOT_SELECTED",
        "PROGRAM_SEARCH_NOT_SELECTED",
        "REGULAR_FILE_METADATA",
        "DIRECTORY_METADATA",
        "PROGRAM_CANDIDATE_METADATA",
        "OBSERVATION_NOT_SUPPLIED",
        "OPERATOR_REPORTED_TRUE_UNVERIFIED",
        "OPERATOR_REPORTED_FALSE_UNVERIFIED",
        "METADATA_UNAVAILABLE",
        "METADATA_CHANGED",
        "LINK_OR_REPARSE_UNSUPPORTED",
        "NODE_TYPE_UNSUPPORTED",
        "LINK_COUNT_UNSUPPORTED",
        "TARGET_TYPE_MISMATCH",
        "ANCESTOR_TYPE_MISMATCH",
        "EXECUTE_ACCESS_UNVERIFIED",
        "PROGRAM_NOT_FOUND",
        "NOT_FOUND",
        "PROBE_BUDGET_EXHAUSTED",
    }
    ids = set()
    for row in checks:
        if not isinstance(row, dict) or set(row) != {
            "id",
            "kind",
            "status",
            "evidence",
        }:
            _fail("REPORT_SCHEMA_INVALID")
        if (
            not isinstance(row["id"], str)
            or not ID.fullmatch(row["id"])
            or row["id"] in ids
        ):
            _fail("REPORT_SCHEMA_INVALID")
        ids.add(row["id"])
        if row["kind"] not in ("file", "directory", "program", "observation") or row[
            "status"
        ] not in ("PRESENT", "MISSING", "UNKNOWN", "UNSAFE"):
            _fail("REPORT_SCHEMA_INVALID")
        if (
            not isinstance(row["evidence"], str)
            or row["evidence"] not in evidence_codes
        ):
            _fail("REPORT_SCHEMA_INVALID")
        if row["kind"] == "observation" and (
            row["status"] != "UNKNOWN"
            or row["evidence"]
            not in {
                "OBSERVATION_NOT_SUPPLIED",
                "OPERATOR_REPORTED_TRUE_UNVERIFIED",
                "OPERATOR_REPORTED_FALSE_UNVERIFIED",
            }
        ):
            _fail("REPORT_SCHEMA_INVALID")
    counts = result["counts"]
    expected = Counter(row["status"].lower() for row in checks)
    if (
        not isinstance(counts, dict)
        or set(counts) != {"present", "missing", "unknown", "unsafe"}
        or any(
            type(value) is not int or value != expected[key]
            for key, value in counts.items()
        )
    ):
        _fail("REPORT_SCHEMA_INVALID")
    status = "ALL_PRESENT" if expected["present"] == len(checks) else "REVIEW_REQUIRED"
    if result["status"] != status:
        _fail("REPORT_SCHEMA_INVALID")
    return (json.dumps(result, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def _directory_identity(info):
    if not stat.S_ISDIR(info.st_mode) or not info.st_ino:
        _fail("REPORT_BOUNDARY_IDENTITY_UNAVAILABLE")
    return info.st_dev, info.st_ino


def write_report(value, result, protected_roots=()):
    target = _lexical_path(value)
    protected = [REPOSITORY, *(_lexical_path(p) for p in protected_roots)]
    if any(target.is_relative_to(path) for path in protected):
        _fail("REPORT_MUST_BE_EXTERNAL")
    parent = _selected_existing(
        target.parent, "directory", "REPORT_PARENT_UNAVAILABLE_OR_UNSAFE"
    )
    # Directory identities catch short-name aliases with a protected ancestor
    # whose lexical spelling does not share a prefix. Never enumerate a tree.
    protected_ids = set()
    for path in protected:
        status, evidence, info = _observe(path, "directory")
        if status == "MISSING":
            continue
        if status != "PRESENT":
            _fail("REPORT_BOUNDARY_UNVERIFIED")
        protected_ids.add(_directory_identity(info))
    for ancestor in [parent, *parent.parents]:
        info = ancestor.lstat()
        if _linked(info):
            _fail("REPORT_PARENT_UNAVAILABLE_OR_UNSAFE")
        if _directory_identity(info) in protected_ids:
            _fail("REPORT_MUST_BE_EXTERNAL")
    raw = _report_data(result)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(target, flags, 0o600), "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        _fail("ARGUMENTS_INVALID")


def main(argv=None):
    parser = _Parser(prog="environment-contract-checker", description=__doc__)
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--root")
    parser.add_argument("--program-dir", action="append", default=[])
    parser.add_argument("--observations")
    parser.add_argument("--report")
    try:
        args = parser.parse_args(argv)
        contract = read_input_json(args.contract)
        observations = read_input_json(args.observations) if args.observations else None
        result = check_contract(
            contract,
            root=args.root,
            program_dirs=args.program_dir,
            observations=observations,
        )
        if args.report:
            roots = [*args.program_dir, *([args.root] if args.root is not None else [])]
            write_report(args.report, result, protected_roots=roots)
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0 if result["status"] == "ALL_PRESENT" else 1
    except ContractError as error:
        code = str(error)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        code = "INPUT_OR_REPORT_FAILED"
    print(
        json.dumps(
            dict(
                status="ERROR",
                code=code,
                target_contents_read=False,
                programs_executed=False,
            )
        )
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
