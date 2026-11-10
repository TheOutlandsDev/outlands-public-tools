"""Fictional publication receipts only; no GitHub or native metric requests."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("focused_publisher", Path(__file__).with_name("publish.py"))
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class MonitorPublicationGate(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="monitor-receipts-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "output"
        self.output.mkdir()
        self.reports = self.root / "reports"
        self.reports.mkdir()
        (self.output / "fictional.zip").write_bytes(b"Fictional package fixture")
        (self.output / "release-matrix.json").write_text("{}\n")
        self.item = dict(version="0.1.2", source_revision="a" * 40, sha256="b" * 64, filename="fictional.zip")
        self.lanes = []
        for platform in ("win32", "linux"):
            for version in ("3.12.10", "3.13.17", "3.14.10", "3.15.2"):
                self.lanes.append(dict(status="PASS", platform=platform, python=version,
                    source_revision=self.item["source_revision"], zip_sha256=self.item["sha256"],
                    exact_extracted_source=True, native_features_required=True, demo_download_check=True,
                    frontend_tests=13, frontend_failures=0, frontend_skips=0, live_values_published=False,
                    modes=[dict(mode=mode, status="PASS", tests=count, passed=count, skipped=0,
                                failures=0, errors=0, fresh_venv=True, extracted_import=True, psutil=dependency)
                           for mode, count, dependency in (("demo",49,"absent"),("live",5,"7.2.2"))]))

    def invoke(self, lanes):
        for index, lane in enumerate(lanes):
            folder = self.reports / str(index)
            folder.mkdir()
            (folder / "qualification.json").write_text(json.dumps(lane))
        with patch.dict(os.environ, {"GITHUB_RUN_ID":"123"}):
            return publisher.monitor_assets(self.output, self.item, self.reports)

    def test_complete_matrix_checksums_cover_every_other_asset(self):
        paths = self.invoke(self.lanes)
        self.assertEqual({Path(name).name for name in paths}, {"START-HERE.md","VALIDATION.json","SHA256SUMS.txt"})
        checksums = Path(paths[-1]).read_text().splitlines()
        self.assertEqual(len(checksums), 4)
        expected = {"fictional.zip":self.output/"fictional.zip", "release-matrix.json":self.output/"release-matrix.json",
                    **{Path(name).name:Path(name) for name in paths[:-1]}}
        for line in checksums:
            digest, name = line.split("  ")
            self.assertEqual(digest, hashlib.sha256(expected[name].read_bytes()).hexdigest())

    def test_duplicate_runtime_cannot_replace_missing_lane(self):
        lanes = copy.deepcopy(self.lanes)
        lanes[-1] = lanes[0]
        with self.assertRaises(AssertionError):
            self.invoke(lanes)

    def test_skipped_live_case_cannot_qualify(self):
        lanes = copy.deepcopy(self.lanes)
        lanes[0]["modes"][1]["skipped"] = 1
        with self.assertRaises(AssertionError):
            self.invoke(lanes)

    def test_receipt_for_other_zip_is_refused(self):
        lanes = copy.deepcopy(self.lanes)
        lanes[0]["zip_sha256"] = "c" * 64
        with self.assertRaises(AssertionError):
            self.invoke(lanes)

    def test_demo_with_live_dependency_is_refused(self):
        lanes = copy.deepcopy(self.lanes)
        lanes[0]["modes"][0]["psutil"] = "7.2.2"
        with self.assertRaises(AssertionError):
            self.invoke(lanes)


if __name__ == "__main__":
    unittest.main()
