"""Offline checks for advisory RDL CommandText classification."""

from __future__ import annotations

import unittest

from rdl_query_lab.sql_classify import classify_sql


class SqlClassifyTests(unittest.TestCase):
    def test_detects_sql_server_features_and_database_dependencies(self) -> None:
        sql = """
        DECLARE @StartDate date = CONVERT(date, GETDATE());
        SELECT TOP (10) ISNULL(m.Name, ''), DATEADD(day, -1, GETDATE()),
               DATEDIFF(day, m.ModifiedOn, GETDATE()),
               m.ModifiedOn AT TIME ZONE 'Eastern Standard Time'
        FROM [DEMO_MESDWH].[dbo].[Material] AS m
        CROSS APPLY (SELECT 1 AS x) AS a
        JOIN DEMO_MESODS.DemoSchema.DemoItem AS ods ON ods.MaterialId = m.Id;
        """
        result = classify_sql(sql)

        self.assertEqual(result["external_database_refs"], ["DEMO_MESDWH", "DEMO_MESODS"])
        self.assertEqual(
            result["tsql_features"],
            [
                "apply",
                "at_time_zone",
                "convert",
                "dateadd",
                "datediff",
                "declare_variable",
                "getdate",
                "isnull",
                "top",
            ],
        )
        self.assertEqual(result["review_flags"], ["external_database_reference"])

    def test_ignores_comments_and_sql_string_literals(self) -> None:
        sql = """
        /* outer comment /* nested EXEC UPDATE DEMO_MES.dbo.Secret */ still comment */
        SELECT '-- DELETE FROM DEMO_MESDWH.dbo.Secret' AS label,
               'It''s not a TOP (10) DATEADD(day, 1, GETDATE())' AS detail;
        -- DROP TABLE DEMO_MESODS.dbo.Hidden
        """
        self.assertEqual(
            classify_sql(sql),
            {"tsql_features": [], "external_database_refs": [], "review_flags": []},
        )

    def test_conservatively_flags_temp_writes_and_procedure_execution(self) -> None:
        result = classify_sql("SELECT TOP 1 Value INTO #Scratch FROM DEMO_MES.dbo.Source; EXEC dbo.NextStep;")

        self.assertEqual(result["external_database_refs"], ["DEMO_MES"])
        self.assertEqual(result["tsql_features"], ["exec", "temp_table", "top"])
        self.assertEqual(
            result["review_flags"],
            ["external_database_reference", "possible_write", "procedure_or_dynamic_sql_review"],
        )

    def test_detects_general_three_part_source_and_non_sql_expression(self) -> None:
        self.assertEqual(
            classify_sql("=Parameters!Query.Value"),
            {
                "tsql_features": [],
                "external_database_refs": [],
                "review_flags": ["no_select_detected", "rdl_expression_review"],
            },
        )
        result = classify_sql('SELECT x FROM [Warehouse].[reporting].[Facts]')
        self.assertEqual(result["external_database_refs"], ["WAREHOUSE"])

    def test_rejects_non_text_input(self) -> None:
        with self.assertRaisesRegex(TypeError, "string"):
            classify_sql(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
