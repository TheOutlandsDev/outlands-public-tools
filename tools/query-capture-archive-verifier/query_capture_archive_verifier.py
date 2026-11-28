"""Verify a saved capture archive against a separate reviewed contract."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, datetime
import hashlib
import io
import json
from pathlib import Path
import re
from stat import S_ISREG
import sys


MAX_MANIFEST_BYTES = 5 * 1024 * 1024
MAX_CSV_BYTES = 50 * 1024 * 1024
MAX_CONTRACT_BYTES = 64 * 1024
MAX_TEMPLATE_BYTES = 1024 * 1024
MAX_DETAIL_ROWS = 10_000
SOURCE_HASH_FIELDS = ("source_rdl_sha256", "dataset1_sql_sha256", "dataset2_sql_sha256", "detail_template_sha256")
_DATETIME_TEXT = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,6})?")
_SHA256 = re.compile(r"[0-9A-F]{64}")
_BIND_MARKER = "/*PRODUCT_PARAMETERS*/"


class ArchiveValidationError(ValueError):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def _sha256(value):
    return hashlib.sha256(value).hexdigest().upper()


def _projection_multiset_sha256(rows):
    """Digest the projected fields in canonical order, preserving duplicates."""
    projected = [[row[index] for index in (0, 6, 4, 1)] for row in rows]

    def canonical_json(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    projected.sort(key=canonical_json)
    return _sha256(canonical_json(projected).encode("utf-8"))


def _bounded_bytes(path, limit):
    if path.is_symlink() or not S_ISREG(path.stat().st_mode):
        raise ValueError()
    with path.open("rb") as stream:
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError()
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError()


def _json_object(raw):
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    if not isinstance(value, dict):
        raise ValueError()
    return value


def _distinct_labels(value, length):
    return (
        isinstance(value, list) and len(value) == length
        and all(isinstance(label, str) and bool(label.strip()) for label in value)
        and len(set(value)) == length
    )


def _is_digest(value):
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _contract_case(contract, case):
    for field in ("schema_version", "report", "server_instance", "database"):
        if not isinstance(contract[field], str) or not contract[field].strip():
            raise ValueError()
    if not _distinct_labels(contract["columns"], 8) or not _distinct_labels(contract["products"], 2):
        raise ValueError()
    hashes = contract["source_hashes"]
    if set(hashes) != set(SOURCE_HASH_FIELDS) or not all(_is_digest(hashes[key]) for key in SOURCE_HASH_FIELDS):
        raise ValueError()

    if case not in ("primary", "boundary"):
        raise ValueError()
    selected = contract["cases"][case]
    start, end = selected["start_date"], selected["end_date"]
    dates = [date.fromisoformat(value) for value in (start, end)]
    if [value.isoformat() for value in dates] != [start, end] or dates[0] >= dates[1]:
        raise ValueError()
    counts = selected["instance_row_counts"]
    if (not isinstance(counts, list) or not counts
            or any(type(value) is not int or value < 1 for value in counts)
            or counts != sorted(counts) or sum(counts) > MAX_DETAIL_ROWS):
        raise ValueError()
    expected = selected["expected_projection_sha256"]
    if not (_is_digest(expected) if case == "primary" else expected is None):
        raise ValueError()
    return selected, {"row_count": sum(counts), "instance_count": len(counts), "instance_row_counts": counts}


def _bound_sql_digest(template_path, expected_sha256):
    template = _bounded_bytes(template_path, MAX_TEMPLATE_BYTES)
    if _sha256(template) != expected_sha256:
        raise ValueError()
    sql = template.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    if sql.count(_BIND_MARKER) != 1:
        raise ValueError()
    return _sha256(sql.replace(_BIND_MARKER, "?, ?").encode("utf-8"))


def _check_manifest(manifest, contract, selected, fixture, bound_digest):
    if (manifest.get("schema_version") != contract["schema_version"]
            or manifest.get("report") != contract["report"]
            or manifest.get("status") != "captured_not_validated"):
        raise ValueError()
    if any(manifest.get(key) != digest for key, digest in contract["source_hashes"].items()):
        raise ValueError()
    if manifest.get("bound_sql_sha256") != bound_digest:
        raise ValueError()

    parameters = manifest["parameters"]
    products = parameters.get("Product")
    if (parameters.get("StartDate") != selected["start_date"]
            or parameters.get("EndDate") != selected["end_date"]
            or not _distinct_labels(products, 2)
            or set(products) != set(contract["products"])):
        raise ValueError()
    identity = manifest["actual_connection"]
    if any(identity[key].casefold() != contract[key].casefold() for key in ("server_instance", "database")):
        raise ValueError()

    if any(manifest.get(field) is not True for field in ("fixture_count_match", "fixture_instance_distribution_match")):
        raise ValueError()
    reference = selected["expected_projection_sha256"]
    expected_flag = True if reference is not None else None
    if manifest["fixture_projection_match"] is not expected_flag or manifest["expected_projection_sha256"] != reference:
        raise ValueError()
    declared_fixture = manifest["expected_fixture"]
    for value in (declared_fixture, manifest):
        if any(type(value[key]) is not int for key in ("row_count", "instance_count")):
            raise ValueError()
        if type(value["instance_row_counts"]) is not list or any(type(count) is not int for count in value["instance_row_counts"]):
            raise ValueError()
    if declared_fixture != fixture or any(manifest[key] != value for key, value in fixture.items()):
        raise ValueError()


def _read_rows(path, artifact, columns, expected_count):
    raw_path = path.parent / "raw.csv"
    saved_path = artifact["path"]
    if not isinstance(saved_path, str) or (saved_path != "raw.csv" and Path(saved_path) != raw_path):
        raise ValueError()
    if raw_path.is_symlink() or raw_path.resolve() != raw_path:
        raise ValueError()
    raw = _bounded_bytes(raw_path, MAX_CSV_BYTES)
    digest = _sha256(raw)
    if artifact.get("sha256") != digest or artifact.get("columns") != columns:
        raise ValueError()
    if (type(artifact.get("null_cells_index_base")) is not int or artifact["null_cells_index_base"] != 0
            or artifact.get("null_cells_data_rows_exclude_header") is not True):
        raise ValueError()

    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    if next(reader, None) != columns:
        raise ValueError()
    rows = []
    for row in reader:
        if len(row) != 8 or len(rows) >= MAX_DETAIL_ROWS:
            raise ValueError()
        rows.append(row)
    if type(artifact.get("row_count")) is not int or artifact["row_count"] != len(rows) or len(rows) != expected_count:
        raise ValueError()
    return rows, digest


def _restore_nulls(rows, coordinates):
    if not isinstance(coordinates, list) or len(coordinates) > len(rows) * 8:
        raise ValueError()
    seen = set()
    for coordinate in coordinates:
        if not isinstance(coordinate, list) or len(coordinate) != 2 or any(type(value) is not int for value in coordinate):
            raise ValueError()
        ri, ci = coordinate
        if (ri, ci) in seen or not 0 <= ri < len(rows) or not 0 <= ci < 8 or rows[ri][ci] != "":
            raise ValueError()
        seen.add((ri, ci))
        rows[ri][ci] = None
    return len(seen)


def load_previous(manifest_path: Path, contract: dict, template_path: Path, *, case="primary"):
    """Return verified typed rows and provenance. The CLI exposes only provenance."""
    try:
        selected, fixture = _contract_case(contract, case)
        if manifest_path.name != "manifest.json" or manifest_path.is_symlink():
            raise ValueError()
        path = manifest_path.resolve()
        manifest_bytes = _bounded_bytes(path, MAX_MANIFEST_BYTES)
        manifest = _json_object(manifest_bytes)
        template_digest = contract["source_hashes"]["detail_template_sha256"]
        _check_manifest(manifest, contract, selected, fixture, _bound_sql_digest(template_path, template_digest))

        artifact = manifest["raw_artifacts"]["detail"]
        text_rows, digest = _read_rows(path, artifact, contract["columns"], fixture["row_count"])
        null_count = _restore_nulls(text_rows, artifact["null_cells"])
        for row in text_rows:
            if row[2] is not None:
                if not _DATETIME_TEXT.fullmatch(row[2]):
                    raise ValueError()
                row[2] = datetime.fromisoformat(row[2])
        rows = [tuple(row) for row in text_rows]
        counts = sorted(Counter(row[1] for row in rows).values())
        observed = _projection_multiset_sha256(rows)
        if counts != fixture["instance_row_counts"] or manifest.get("projection_multiset_sha256") != observed:
            raise ValueError()
        reference = selected["expected_projection_sha256"]
        if reference is not None and observed != reference:
            raise ValueError()
    except (OSError, ValueError, TypeError, KeyError, AttributeError, csv.Error, RuntimeError):
        raise ArchiveValidationError("previous_evidence") from None

    return rows, {
        "case": case,
        "manifest_sha256": _sha256(manifest_bytes),
        "raw_csv_sha256": digest,
        "projection_multiset_sha256": observed,
        "row_count": len(rows),
        "null_cell_count": null_count,
        "previous_type_metadata_available": False,
        "historical_projection_digest_available": reference is not None,
        "projection_digest_check": (
            "Independent reference and artifact consistency" if reference is not None
            else "Artifact consistency only"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--case", choices=("primary", "boundary"), default="primary")
    args = parser.parse_args()

    try:
        contract = _json_object(_bounded_bytes(args.contract, MAX_CONTRACT_BYTES))
        _, provenance = load_previous(args.manifest, contract, args.template, case=args.case)
    except (OSError, ValueError, RecursionError):
        sys.stderr.write("Capture archive or reviewed contract failed verification\n")
        return 2
    print(json.dumps({"status": "verified", **provenance}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
