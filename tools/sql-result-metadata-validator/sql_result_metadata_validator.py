"""Validate saved SQL Server metadata for a reviewed eight-column result."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import re
from stat import S_ISREG
import sys


MAX_INPUT_BYTES = 1_048_576


class ValidationError(ValueError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


METADATA_COLUMNS = ("column_ordinal", "name", "system_type_name", "max_length", "precision", "scale", "is_nullable", "collation_name", "error_number", "error_type_desc")
METADATA_SQL = (
    "SELECT column_ordinal, name, system_type_name, max_length, precision, scale, "
    "is_nullable, collation_name, error_number, error_type_desc "
    "FROM sys.dm_exec_describe_first_result_set(?, ?, 0) ORDER BY column_ordinal"
)


def validate_metadata(rows: Sequence[Sequence[object]], *,
                      expected_columns: Sequence[str]) -> list[dict[str, object]]:
    """Validate eight known fields and reject unsupported timestamp precision."""
    if (not isinstance(expected_columns, (list, tuple)) or len(expected_columns) != 8
            or any(not isinstance(name, str) or not name.strip() for name in expected_columns)
            or len(set(expected_columns)) != 8):
        raise ValidationError("invalid_contract")
    if not isinstance(rows, (list, tuple)) or len(rows) != 8:
        raise ValidationError("result_shape")
    result = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, (list, tuple)) or len(raw) != len(METADATA_COLUMNS):
            raise ValidationError("result_shape")
        item = dict(zip(METADATA_COLUMNS, raw))
        if item["error_number"] is not None or item["error_type_desc"] is not None:
            raise ValidationError("result_shape")
        if type(item["column_ordinal"]) is not int or item["column_ordinal"] != index + 1 or item["name"] != expected_columns[index]:
            raise ValidationError("result_shape")
        if any(type(item[field]) is not int for field in ("max_length", "precision", "scale")):
            raise ValidationError("result_shape")
        if (item["max_length"] != -1 and item["max_length"] <= 0) or item["precision"] < 0 or item["scale"] < 0:
            raise ValidationError("result_shape")
        if item["is_nullable"] not in (False, True, 0, 1) or type(item["is_nullable"]) not in (bool, int):
            raise ValidationError("result_shape")
        sql_type = item["system_type_name"]
        if not isinstance(sql_type, str):
            raise ValidationError("result_shape")
        if index == 2:
            match = re.fullmatch(r"datetime2\(([0-7])\)", sql_type)
            if match and int(match.group(1)) > 6:
                raise ValidationError("unsupported_precision")
            expected_scale = {"datetime": 3, "smalldatetime": 0}.get(sql_type)
            if match:
                expected_scale = int(match.group(1))
            if expected_scale is None or item["scale"] != expected_scale or item["collation_name"] is not None:
                raise ValidationError("result_shape")
        else:
            if not re.fullmatch(r"(?:n?varchar|n?char)\((?:max|[1-9][0-9]*)\)", sql_type) or not isinstance(item["collation_name"], str):
                raise ValidationError("result_shape")
            if item["scale"] != 0 or item["precision"] != 0:
                raise ValidationError("result_shape")
        result.append(item)
    return result


def _reject_constant(_value):
    raise ValueError("Invalid JSON number")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _load_json(path: Path):
    if path.is_symlink() or not S_ISREG(path.stat().st_mode):
        raise ValueError("Input must be a regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds its byte limit")
    return json.loads(
        raw.decode("utf-8-sig"), object_pairs_hook=_unique_keys, parse_constant=_reject_constant,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True, help="Reviewed column names in report order")
    parser.add_argument("--metadata", type=Path, required=True, help="Saved result metadata rows")
    args = parser.parse_args()

    try:
        contract = _load_json(args.contract)
        rows = _load_json(args.metadata)
        if not isinstance(contract, dict) or contract.keys() != {"columns"}:
            raise ValidationError("invalid_contract")
        if not isinstance(rows, list):
            raise ValidationError("result_shape")
        validated = validate_metadata(rows, expected_columns=contract["columns"])
    except ValidationError as error:
        category = error.category
    except (OSError, ValueError, RecursionError):
        category = "invalid_input"
    else:
        print(json.dumps({"status": "validated", "column_count": len(validated)}))
        return 0

    print(json.dumps({"status": "rejected", "category": category}), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
