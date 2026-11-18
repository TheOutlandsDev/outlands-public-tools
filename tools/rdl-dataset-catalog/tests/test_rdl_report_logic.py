"""Focused checks for report-side RDL logic inventory."""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
import hashlib
from pathlib import Path

from rdl_query_lab.report_logic import summarize_report_logic


FIXTURE = Path(__file__).parent / "fixtures" / "rdl_catalog" / "ReportLogic.xml"


class ReportLogicTests(unittest.TestCase):
    def test_namespace_agnostic_logic_inventory(self) -> None:
        result = summarize_report_logic(ET.parse(FIXTURE).getroot())

        self.assertEqual(
            result["counts"],
            {
                "filters": 2,
                "group_expressions": 2,
                "sort_expressions": 3,
                "calculated_fields": 1,
                "subreports": 1,
                "subreport_parameter_bindings": 2,
                "expression_nodes": 11,
                "embedded_code_blocks": 1,
            },
        )
        self.assertEqual(result["filters"][0]["values"], ["=Parameters!Floor.Value"])
        self.assertEqual(result["filters"][1]["values"], ["Active", "Ready"])
        self.assertEqual(result["group_expressions"][1]["expression"], "=Fields!Lot.Value")
        self.assertEqual(result["sort_expressions"][0]["expression"], "=Fields!Material.Value")
        self.assertEqual(result["sort_expressions"][1]["expression"], "=Fields!Lot.Value")
        self.assertEqual(result["sort_expressions"][2]["container"], "UserSort")
        self.assertEqual(result["sort_expressions"][2]["expression"], "=Fields!Material.Value")
        self.assertEqual(result["calculated_fields"][0]["dataset"], "Detail")
        self.assertEqual(result["calculated_fields"][0]["field"], "Doubled")
        self.assertEqual(result["subreport_parameter_bindings"][0]["parameter"], "Part")
        self.assertEqual(result["subreport_parameter_bindings"][1]["expression"], "true")
        self.assertTrue(result["filters"][0]["location"].startswith("Report[1]/DataSets[1]/DataSet[1]"))
        self.assertIn("Tablix[1]/Filters[1]/Filter[1]", result["filters"][1]["location"])
        hidden = next(item for item in result["expression_nodes"] if item["element_name"] == "Hidden")
        self.assertEqual(hidden["expression"], "\n      =Parameters!Hide.Value")
        self.assertEqual(hidden["text_slot"], "text")
        self.assertIn("Textbox[1]/Visibility[1]/Hidden[1]", hidden["location"])
        code_text = next(node.text for node in ET.parse(FIXTURE).getroot().iter() if node.tag.endswith("}Code"))
        self.assertEqual(
            result["embedded_code_blocks"][0]["sha256"],
            hashlib.sha256(code_text.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(result["embedded_code_blocks"][0]["location"], "Report[1]/Code[1]")

    def test_empty_report_has_zero_counts(self) -> None:
        result = summarize_report_logic(ET.fromstring("<Report />"))
        self.assertTrue(all(count == 0 for count in result["counts"].values()))
        self.assertEqual(result["calculated_fields"], [])


if __name__ == "__main__":
    unittest.main()
