"""Offline checks for the RDL command catalog builder."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from rdl_query_lab.build_catalog import (
    PROJECT_ROOT,
    collect,
    compare_output,
    expected_files,
    lexical_class,
    review_queue_rows,
)


FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "rdl_catalog" / "Example.xml"


class CatalogTests(unittest.TestCase):
    def test_extraction_preserves_command_and_metadata(self) -> None:
        with patch.object(Path, "rglob", return_value=[FIXTURE]):
            catalog, commands = collect(FIXTURE.parent)

        self.assertEqual(catalog["summary"]["report_count"], 1)
        self.assertEqual(catalog["summary"]["dataset_count"], 2)
        report = catalog["reports"][0]
        self.assertEqual(report["subreports"], ["OtherReport"])
        self.assertEqual(report["report_parameters"][0]["data_type"], "DateTime")
        self.assertEqual(report["report_parameters"][0]["default_values"], ["=Today()"])
        self.assertEqual(report["report_parameters"][1]["available_dataset"], "Procedure")
        self.assertEqual(report["report_parameters"][1]["available_value_field"], "PartId")
        self.assertEqual(report["report_parameters"][1]["available_label_field"], "PartName")
        self.assertEqual(report["report_parameters"][1]["default_value_field"], "PartId")
        self.assertTrue(report["report_parameters"][1]["multi_value"])
        self.assertEqual(report["report_logic"]["counts"]["subreports"], 1)

        detail, procedure = report["datasets"]
        self.assertEqual(detail["lexical_class"], "select_sql")
        self.assertEqual(detail["shared_source_reference"], "/Datasources/DEMO_MESODS")
        self.assertEqual(detail["query_parameters"][0]["value_expression"], "=Parameters!Day.Value")
        self.assertEqual(detail["fields"][0]["type_name"], "System.Boolean")
        self.assertEqual(commands[Path(detail["command_file"])], b"SELECT 1 < 2 AS Flag")
        self.assertEqual(procedure["lexical_class"], "text_procedure_call")
        self.assertTrue(procedure["command_file"].endswith(".command.txt"))
        self.assertEqual(review_queue_rows(catalog)[0]["tier"], "05_dependency_review")

    def test_check_detects_changed_output(self) -> None:
        with patch.object(Path, "rglob", return_value=[FIXTURE]):
            catalog, commands = collect(FIXTURE.parent)
        expected = expected_files(catalog, commands)
        self.assertIn(Path("catalog.json"), expected)
        self.assertTrue(any("Missing:" in message for message in compare_output(FIXTURE.parent / "not_created", expected)))
        self.assertTrue(any("Content mismatch" in message for message in compare_output(FIXTURE.parent, {Path("Example.xml"): b"changed"})))

    def test_command_classes_keep_dependencies_visible(self) -> None:
        self.assertEqual(lexical_class("-- note\nEXEC dbo.Parts", "Text"), "text_procedure_call")
        self.assertEqual(lexical_class("[Reports].[P_GetDetails]", "Text"), "text_procedure_call")
        self.assertEqual(lexical_class("dbo.Parts", "StoredProcedure"), "stored_procedure")
        self.assertEqual(lexical_class("DECLARE @x int = 1; SELECT @x", "Text"), "script_sql")


if __name__ == "__main__":
    unittest.main()
