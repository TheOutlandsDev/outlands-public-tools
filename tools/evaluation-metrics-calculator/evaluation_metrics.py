#!/usr/bin/env python3
"""Calculate exact metrics from declared confusion counts without running models."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

VERSION = "0.1.0"
MAX_INPUT_BYTES = 65536
MAX_CLASSES = 32
MAX_CELL_COUNT = 1000000000
MAX_TOTAL_COUNT = 1000000000000
ID = re.compile(r"[a-z][a-z0-9_-]{0,39}")
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    prefix + digit for prefix in ("com", "lpt") for digit in "123456789¹²³"
}


class ContractError(ValueError):
    """Only a fixed public code, never an input value or native exception."""


def _fail(code):
    raise ContractError(code) from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def parse_counts(data):
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "classes", "counts"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["classes"], list)
        or not 0 < len(data["classes"]) <= MAX_CLASSES
        or not isinstance(data["counts"], list)
    ):
        _fail("COUNTS_SCHEMA_INVALID")
    seen = set()
    for identifier in data["classes"]:
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            _fail("CLASS_ID_INVALID")
        if identifier in seen:
            _fail("DUPLICATE_CLASS_ID")
        seen.add(identifier)
    size = len(data["classes"])
    if len(data["counts"]) != size or any(
        not isinstance(row, list) or len(row) != size for row in data["counts"]
    ):
        _fail("MATRIX_SHAPE_INVALID")
    total = 0
    for row in data["counts"]:
        for value in row:
            if type(value) is not int or not 0 <= value <= MAX_CELL_COUNT:
                _fail("CELL_COUNT_INVALID")
            total += value
    if not 1 <= total <= MAX_TOTAL_COUNT:
        _fail("TOTAL_COUNT_INVALID")
    return dict(
        schema_version=1,
        classes=list(data["classes"]),
        counts=[list(row) for row in data["counts"]],
    )


def _ratio(numerator, denominator):
    if denominator == 0:
        return dict(status="UNDEFINED", numerator=None, denominator=0)
    return dict(status="DEFINED", numerator=numerator, denominator=denominator)


def calculate_metrics(data):
    """Use raw formula counts for exact ratios; do not infer model quality."""
    data = parse_counts(data)
    matrix = data["counts"]
    size = len(data["classes"])
    rows = [sum(row) for row in matrix]
    columns = [
        sum(matrix[row][column] for row in range(size)) for column in range(size)
    ]
    total = sum(rows)
    correct = sum(matrix[index][index] for index in range(size))
    classes = []
    undefined = 0
    for index, identifier in enumerate(data["classes"]):
        true_positive = matrix[index][index]
        false_positive = columns[index] - true_positive
        false_negative = rows[index] - true_positive
        precision = _ratio(true_positive, columns[index])
        recall = _ratio(true_positive, rows[index])
        # F1 is independent of whether precision or recall is defined.
        f1 = _ratio(
            2 * true_positive, 2 * true_positive + false_positive + false_negative
        )
        undefined += sum(
            metric["status"] == "UNDEFINED" for metric in (precision, recall, f1)
        )
        classes.append(
            dict(
                id=identifier,
                support=rows[index],
                true_positive=true_positive,
                false_positive=false_positive,
                false_negative=false_negative,
                precision=precision,
                recall=recall,
                f1=f1,
            )
        )
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED" if undefined else "METRICS_COMPUTED",
        scope="DECLARED_SINGLE_LABEL_CONFUSION_COUNTS_ONLY",
        orientation="EXPECTED_ROWS_PREDICTED_COLUMNS",
        model_executed=False,
        network_probed=False,
        input_modified=False,
        ground_truth_verified=False,
        predictions_verified=False,
        counts=dict(classes=size, observations=total, undefined_metrics=undefined),
        accuracy=_ratio(correct, total),
        classes=classes,
    )


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
        path = Path(os.path.abspath(original))
        if path.parent == path or len(path.parts) > 64 or len(str(path)) > 4096:
            _fail("INPUT_PATH_INVALID")
        for part in path.parts:
            if part == path.anchor:
                continue
            if (
                part.endswith((".", " "))
                or part.split(".")[0].casefold() in RESERVED
                or any(c in '\\:<>"|?*' for c in part)
            ):
                _fail("INPUT_PATH_INVALID")
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


def _read_input_json(value):
    path = _selected_path(value)
    ancestors, before = _snapshot(path)
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
        _regular_input(opened)
        if _identity(opened) != _identity(before):
            _fail("INPUT_CHANGED")
        raw = stream.read(MAX_INPUT_BYTES + 1)
        after = os.fstat(stream.fileno())
    current_ancestors, current = _snapshot(path)
    if (
        ancestors != current_ancestors
        or _identity(after) != _identity(before)
        or _identity(current) != _identity(before)
        or len(raw) != before.st_size
    ):
        _fail("INPUT_CHANGED")
    if len(raw) > MAX_INPUT_BYTES:
        _fail("INPUT_SIZE_LIMIT")
    return json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=_unique_object,
        parse_constant=lambda _: _fail("NONSTANDARD_JSON"),
    )


def read_input_json(value):
    """Read selected bounded JSON; formatted errors suppress native input detail."""
    try:
        return _read_input_json(value)
    except ContractError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        _fail("INPUT_OR_COUNTS_FAILED")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        _fail("ARGUMENTS_INVALID")


def main(argv=None):
    parser = _Parser(
        prog="evaluation-metrics-calculator", description=__doc__, allow_abbrev=False
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("--counts", required=True)
    exit_code = 2
    try:
        args = parser.parse_args(argv)
        result = calculate_metrics(read_input_json(args.counts))
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0 if result["status"] == "METRICS_COMPUTED" else 1
    except ContractError as error:
        code = str(error)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        code = "INPUT_OR_COUNTS_FAILED"
    except KeyboardInterrupt:
        code, exit_code = "INTERRUPTED", 130
    print(
        json.dumps(
            dict(
                status="ERROR",
                code=code,
                model_executed=False,
                network_probed=False,
                input_modified=False,
                ground_truth_verified=False,
                predictions_verified=False,
            ),
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
