"""Fictional fixtures for the original archive-loading assertions."""

from contextlib import contextmanager
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import query_capture_archive_verifier as helper
from query_capture_archive_verifier import ArchiveValidationError


COLUMNS = ("Item", "Instance", "RecordedAt", "RecordedBy", "Product", "Attribute", "Sample", "Value")
PRODUCTS = ("DEMO-A", "DEMO-B")
TEMPLATE = b"SELECT item FROM example_inventory WHERE product IN (/*PRODUCT_PARAMETERS*/);\n"
CASE_WINDOWS = {
    "primary": ("2020-04-02", "2020-04-03", [6, 14, 16]),
    "boundary": ("2020-04-01", "2020-04-02", [3, 10]),
}


@contextmanager
def scratch():
    with tempfile.TemporaryDirectory(prefix="query-capture-") as folder:
        yield Path(folder)


def synthetic_rows(case="primary"):
    start, _, counts = CASE_WINDOWS[case]
    stamp = datetime.fromisoformat(start + "T01:02:03.456789")
    return [
        ("Example item", f"example-instance-{group}", stamp, "Example reviewer", PRODUCTS[0],
         "", f"00{index} Example sample", None if index == 0 else "Yes")
        for group, count in enumerate(counts, 1) for index in range(count)
    ]


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def projection_digest(rows):
    projection = [[row[0], row[6], row[4], row[1]] for row in rows]
    encoded_rows = sorted(json.dumps(row, separators=(",", ":"), ensure_ascii=False) for row in projection)
    return digest(("[" + ",".join(encoded_rows) + "]").encode("utf-8"))


def json_file(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def fictional_contract():
    return {
        "schema_version": "example_query_capture.v1",
        "report": "Example inventory report",
        "columns": list(COLUMNS),
        "products": list(PRODUCTS),
        "server_instance": "example-sql.invalid",
        "database": "ExampleInventory",
        "source_hashes": {
            "source_rdl_sha256": digest(b"example report definition"),
            "dataset1_sql_sha256": digest(b"example dataset one"),
            "dataset2_sql_sha256": digest(b"example dataset two"),
            "detail_template_sha256": digest(TEMPLATE),
        },
        "cases": {
            case: {
                "start_date": start,
                "end_date": end,
                "instance_row_counts": counts,
                "expected_projection_sha256": projection_digest(synthetic_rows(case)) if case == "primary" else None,
            }
            for case, (start, end, counts) in CASE_WINDOWS.items()
        },
    }


def write_capture(directory, contract, case):
    rows = synthetic_rows(case)
    raw_path = directory / "raw.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    nulls = [[r, c] for r, row in enumerate(rows) for c, value in enumerate(row) if value is None]

    selected = contract["cases"][case]
    fixture = dict(row_count=len(rows), instance_count=len(selected["instance_row_counts"]),
                   instance_row_counts=selected["instance_row_counts"])
    projection = projection_digest(rows)
    manifest = {
        "schema_version": contract["schema_version"],
        "report": contract["report"],
        "status": "captured_not_validated",
        "parameters": {"StartDate": selected["start_date"], "EndDate": selected["end_date"], "Product": list(PRODUCTS)},
        "actual_connection": {"server_instance": contract["server_instance"], "database": contract["database"]},
        **contract["source_hashes"],
        "bound_sql_sha256": digest(TEMPLATE.replace(b"/*PRODUCT_PARAMETERS*/", b"?, ?")),
        "expected_fixture": fixture,
        **fixture,
        "fixture_count_match": True,
        "fixture_instance_distribution_match": True,
        "fixture_projection_match": True if case == "primary" else None,
        "expected_projection_sha256": selected["expected_projection_sha256"],
        "projection_multiset_sha256": projection,
        "raw_artifacts": {"detail": {
            "path": "raw.csv",
            "sha256": digest(raw_path.read_bytes()),
            "columns": list(COLUMNS),
            "row_count": len(rows),
            "null_cells_index_base": 0,
            "null_cells_data_rows_exclude_header": True,
            "null_cells": nulls,
        }},
    }
    path = directory / "manifest.json"
    json_file(path, manifest)
    return path, manifest, projection


class CaptureArchiveTests(unittest.TestCase):
    def create_previous(self, directory, *, case="primary"):
        (directory / "detail-template.sql").write_bytes(TEMPLATE)
        return write_capture(directory, fictional_contract(), case)

    def load_synthetic(self, path, projection, *, case="primary"):
        contract = fictional_contract()
        if case == "primary":
            contract["cases"]["primary"]["expected_projection_sha256"] = projection
        return helper.load_previous(path, contract, path.parent / "detail-template.sql", case=case)



    def test_boundary_previous_capture_checks_internal_projection_only(self):
        with scratch() as directory:
            path, _, digest = self.create_previous(directory, case="boundary")
            rows, provenance = self.load_synthetic(path, digest, case="boundary")
            self.assertEqual(rows, synthetic_rows("boundary"))
            self.assertEqual(len(rows), 13)
            self.assertEqual(provenance["case"], "boundary")
            self.assertFalse(provenance["historical_projection_digest_available"])
            self.assertIn("Artifact consistency only", provenance["projection_digest_check"])

    def test_fixed_case_reader_rejects_other_case_dates(self):
        for saved, requested in (("primary", "boundary"), ("boundary", "primary"), ("primary", "arbitrary")):
            with scratch() as directory:
                path, _, digest = self.create_previous(directory, case=saved)
                with self.assertRaises(ArchiveValidationError) as caught:
                    self.load_synthetic(path, digest, case=requested)
                self.assertEqual(caught.exception.category, "previous_evidence")

    def test_boundary_rejects_projection_claims_or_missing_projection_state(self):
        for change in (lambda m: m.update(fixture_projection_match=True), lambda m: m.update(fixture_projection_match=False),
                       lambda m: m.update(expected_projection_sha256="IMPROPER-HISTORICAL-CLAIM"),
                       lambda m: m.pop("fixture_projection_match"), lambda m: m.pop("expected_projection_sha256")):
            with scratch() as directory:
                path, manifest, digest = self.create_previous(directory, case="boundary")
                change(manifest)
                path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(ArchiveValidationError):
                    self.load_synthetic(path, digest, case="boundary")

    def test_boundary_rejects_inconsistent_counts_or_projection_digest(self):
        for change in (lambda m: m.update(projection_multiset_sha256="BAD"), lambda m: m.update(instance_row_counts=[4, 9]),
                       lambda m: m.update(fixture_count_match=False), lambda m: m.update(fixture_instance_distribution_match=False)):
            with scratch() as directory:
                path, manifest, digest = self.create_previous(directory, case="boundary")
                change(manifest)
                path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(ArchiveValidationError):
                    self.load_synthetic(path, digest, case="boundary")

    def test_previous_manifest_rehydrates_nulls_empty_strings_and_microseconds(self):
        with scratch() as directory:
            path, _, digest = self.create_previous(directory)
            rows, provenance = self.load_synthetic(path, digest)
            self.assertEqual(rows, synthetic_rows())
            self.assertEqual(rows[0][5], "")
            self.assertIsNone(rows[0][7])
            self.assertEqual(rows[0][2].microsecond, 456789)
            self.assertTrue(rows[0][6].startswith("000"))
            self.assertEqual(provenance["raw_csv_sha256"], helper._sha256((directory / "raw.csv").read_bytes()))
            self.assertEqual(provenance["manifest_sha256"], helper._sha256(path.read_bytes()))
            self.assertFalse(provenance["previous_type_metadata_available"])

    def test_previous_rejects_tampering_and_wrong_case_or_source(self):
        for change in (lambda m: m.update(status="failed"), lambda m: m.update(fixture_projection_match=False),
                       lambda m: m["parameters"].update(EndDate="2020-04-04"), lambda m: m.update(source_rdl_sha256="BAD"),
                       lambda m: m.update(bound_sql_sha256="BAD"), lambda m: m.update(row_count=35),
                       lambda m: m["actual_connection"].update(database="OTHER"),
                       lambda m: m["raw_artifacts"]["detail"].update(sha256="BAD"),
                       lambda m: m["raw_artifacts"]["detail"].update(path="outside.csv")):
            with scratch() as directory:
                path, manifest, digest = self.create_previous(directory)
                change(manifest)
                path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(ArchiveValidationError) as caught:
                    self.load_synthetic(path, digest)
                self.assertEqual(caught.exception.category, "previous_evidence")

    def test_previous_rejects_invalid_null_coordinates(self):
        for coords in ([[0, 7], [0, 7]], [[-1, 7]], [[36, 0]], [[0, 8]], [[False, 7]], [[0, 0]], ["0,7"]):
            with scratch() as directory:
                path, manifest, digest = self.create_previous(directory)
                manifest["raw_artifacts"]["detail"]["null_cells"] = coords
                path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(ArchiveValidationError):
                    self.load_synthetic(path, digest)

    def test_previous_rejects_timestamps_beyond_six_digits_or_with_timezone(self):
        for text in ("2020-04-02 01:02:03.4567891", "2020-04-02 01:02:03.456789+00:00", "2020-04-02", "invalid"):
            with scratch() as directory:
                path, manifest, digest = self.create_previous(directory)
                raw = directory / "raw.csv"
                raw.write_bytes(raw.read_bytes().replace(b"2020-04-02 01:02:03.456789", text.encode()))
                manifest["raw_artifacts"]["detail"]["sha256"] = helper._sha256(raw.read_bytes())
                path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(ArchiveValidationError):
                    self.load_synthetic(path, digest)

    def test_previous_rejects_oversized_files_and_duplicate_json_keys(self):
        with scratch() as directory:
            path, _, digest = self.create_previous(directory)
            with patch.object(helper, "MAX_MANIFEST_BYTES", 8), self.assertRaises(ArchiveValidationError):
                self.load_synthetic(path, digest)
            with patch.object(helper, "MAX_CSV_BYTES", 8), self.assertRaises(ArchiveValidationError):
                self.load_synthetic(path, digest)
            path.write_text('{"status":"a","status":"b"}', encoding="utf-8")
            with self.assertRaises(ArchiveValidationError):
                self.load_synthetic(path, digest)

    def test_previous_rejects_wrong_header_even_with_updated_hash(self):
        with scratch() as directory:
            path, manifest, digest = self.create_previous(directory)
            raw = directory / "raw.csv"
            raw.write_bytes(raw.read_bytes().replace(b"RecordedBy", b"ChangedBy", 1))
            manifest["raw_artifacts"]["detail"]["sha256"] = helper._sha256(raw.read_bytes())
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ArchiveValidationError):
                self.load_synthetic(path, digest)
