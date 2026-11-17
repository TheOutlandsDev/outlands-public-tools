from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from program_data.mes_policy import (
    REQUIRED_TELEMETRY_FIELDS,
    RuntimeGuardrails,
    get_runtime_guardrails,
    validate_query_contract,
)


VALID_DATE_SQL = """\
DECLARE @StartDateTime datetime2 = ?;
DECLARE @EndDateExclusive datetime2 = ?;
DECLARE @MaxRows int = ?;

SELECT TOP (@MaxRows)
    mh.ItemName,
    mh.EventDateTime
FROM DemoManufacturing.dbo.DemoMovement AS mh
WHERE mh.EventDateTime >= @StartDateTime
  AND mh.EventDateTime < @EndDateExclusive
ORDER BY mh.EventDateTime;
"""


class MesPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.queries = self.root / "queries"
        self.contracts = self.root / "query_contracts"
        self.queries.mkdir()
        self.contracts.mkdir()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def valid_contract(self) -> dict[str, object]:
        return {
            "policy_version": "1.0",
            "program_name": "Policy test",
            "report_family": "daily movement",
            "query_file": "../queries/daily_movement.sql",
            "query_version": "1.0.0",
            "database_name": "DemoManufacturing",
            "connection_profile": "DEMO_READ_ONLY_REPORTING",
            "risk_class": "A",
            "scope": {
                "type": "date",
                "parameters": [
                    "StartDateTime",
                    "EndDateExclusive",
                    "MaxRows",
                ],
                "bound_parameters": [
                    "StartDateTime",
                    "EndDateExclusive",
                ],
                "start_parameter": "StartDateTime",
                "end_parameter": "EndDateExclusive",
                "detail_cap_parameter": "MaxRows",
                "indexed_filter_columns": ["EventDateTime"],
                "parameter_defaults": {
                    "StartDateTime": "2026-07-20T00:00:00-04:00",
                    "EndDateExclusive": "2026-07-21T00:00:00-04:00",
                    "MaxRows": 100,
                },
            },
            "validation": {
                "tested_read_only": True,
                "known_test_case": "Fictional reporting day",
                "known_test_case_row_count": 10,
                "useful_rows_returned": True,
                "full_refresh_timed": True,
                "elapsed_seconds": 12.5,
                "expected_row_count": {"min": 1, "max": 1000},
                "row_count_anomaly_policy": "stop",
                "consecutive_warning_runs": 0,
                "retry_reviewed": False,
                "evidence_reference": (
                    "query_contracts/evidence/"
                    "daily-movement.validation-evidence.json"
                ),
            },
            "outputs": {
                "raw_archive_target": "data/archive/mes/daily-movement",
                "processed_artifact_target": (
                    "data/processed/daily-movement"
                ),
                "published_artifact_target": (
                    "data/published/daily-movement"
                ),
                "archive_raw_before_transform": True,
                "keep_previous_published_on_failure": True,
            },
            "scheduling": {
                "enabled": False,
                "on_demand_only": False,
                "business_cadence": None,
                "job_step": None,
                "one_report_family_per_job_step": True,
            },
            "audit_rule": "Known material is visible on the target date.",
            "telemetry_fields": sorted(REQUIRED_TELEMETRY_FIELDS),
        }

    def write_candidate(
        self,
        contract: dict[str, object] | None = None,
        sql_text: str = VALID_DATE_SQL,
    ) -> Path:
        active_contract = contract or self.valid_contract()
        query_path = self.queries / "daily_movement.sql"
        query_path.write_text(sql_text, encoding="utf-8")
        query_sha256 = hashlib.sha256(query_path.read_bytes()).hexdigest()
        active_contract.setdefault(
            "candidate_query_sha256",
            query_sha256,
        )

        validation = active_contract["validation"]
        scope = active_contract["scope"]
        assert isinstance(validation, dict)
        assert isinstance(scope, dict)
        evidence_directory = self.contracts / "evidence"
        evidence_directory.mkdir(exist_ok=True)
        evidence = {
            "evidence_version": "1.0",
            "status": "PASS",
            "program_name": active_contract["program_name"],
            "report_family": active_contract["report_family"],
            "query_file": "queries/daily_movement.sql",
            "query_version": active_contract["query_version"],
            "query_sha256": query_sha256,
            "database_name": active_contract["database_name"],
            "connection_profile": active_contract["connection_profile"],
            "parameters": scope.get("parameter_defaults", {}),
            "start_time": "2026-07-20T12:00:00Z",
            "end_time": "2026-07-20T12:00:12.500Z",
            "elapsed_seconds": validation["elapsed_seconds"],
            "timing_includes": {
                "connection": True,
                "execution": True,
                "fetch": True,
                "raw_archive_write": True,
            },
            "row_count": validation["known_test_case_row_count"],
            "expected_row_count": validation["expected_row_count"],
            "raw_output_path": "data/archive/mes/daily-movement/run-1",
            "processed_output_path": (
                "data/processed/daily-movement/run-1"
            ),
            "published_output_path": None,
            "audit": {
                "column_shape_passed": True,
                "dashboard_visibility_passed": True,
            },
            "error_number": None,
            "error_state": None,
            "error_message": None,
            "previous_published_data_remained_active": True,
            "reviewed_by": "test-reviewer",
            "reviewed_at": "2026-07-20T13:00:00Z",
        }
        (evidence_directory / "daily-movement.validation-evidence.json").write_text(
            json.dumps(evidence),
            encoding="utf-8",
        )

        contract_path = self.contracts / "daily-movement.query-contract.json"
        contract_path.write_text(
            json.dumps(active_contract),
            encoding="utf-8",
        )
        return contract_path

    def validate(
        self,
        contract: dict[str, object] | None = None,
        sql_text: str = VALID_DATE_SQL,
        *,
        guardrails: RuntimeGuardrails | None = None,
    ):
        contract_path = self.write_candidate(contract, sql_text)
        return validate_query_contract(
            contract_path,
            project_root=self.root,
            guardrails=guardrails,
        )

    def test_valid_bounded_contract_passes_static_gate(self) -> None:
        report = self.validate()

        self.assertTrue(report.static_gate_passed, report.errors)
        self.assertEqual(len(report.query_sha256 or ""), 64)
        self.assertIn(
            "Live MES execution remains disabled",
            " ".join(report.warnings),
        )

    def test_class_a_requires_pass_evidence(self) -> None:
        contract_path = self.write_candidate()
        evidence_path = (
            self.contracts
            / "evidence"
            / "daily-movement.validation-evidence.json"
        )
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["status"] = "PENDING"
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

        report = validate_query_contract(
            contract_path,
            project_root=self.root,
        )

        self.assertFalse(report.static_gate_passed)
        self.assertIn(
            "evidence status must be PASS",
            " ".join(report.errors),
        )

    def test_query_hash_lock_detects_post_review_edit(self) -> None:
        contract_path = self.write_candidate()
        query_path = self.queries / "daily_movement.sql"
        query_path.write_text(
            query_path.read_text(encoding="utf-8")
            + "\n-- Changed after evidence capture.\n",
            encoding="utf-8",
        )

        report = validate_query_contract(
            contract_path,
            project_root=self.root,
        )
        joined_errors = " ".join(report.errors)

        self.assertFalse(report.static_gate_passed)
        self.assertIn("candidate_query_sha256", joined_errors)
        self.assertIn("Evidence query SHA-256", joined_errors)

    def test_reference_sql_outside_governed_queries_cannot_pass(self) -> None:
        reference_directory = self.root / "mes_sql-data"
        reference_directory.mkdir()
        (reference_directory / "old.sql").write_text(
            VALID_DATE_SQL,
            encoding="utf-8",
        )
        contract = self.valid_contract()
        contract["query_file"] = "../mes_sql-data/old.sql"

        report = self.validate(contract)

        self.assertFalse(report.static_gate_passed)
        self.assertIn(
            "query_file must resolve under the new project's queries/",
            " ".join(report.errors),
        )

    def test_select_star_and_inclusive_end_date_are_rejected(self) -> None:
        unsafe_sql = """\
DECLARE @StartDateTime datetime2 = ?;
DECLARE @EndDateExclusive datetime2 = ?;
DECLARE @MaxRows int = ?;
SELECT TOP (@MaxRows) mh.*
FROM DemoManufacturing.dbo.DemoMovement AS mh
WHERE mh.EventDateTime >= @StartDateTime
  AND mh.EventDateTime <= @EndDateExclusive;
"""

        report = self.validate(sql_text=unsafe_sql)
        joined_errors = " ".join(report.errors)

        self.assertFalse(report.static_gate_passed)
        self.assertIn("SELECT *", joined_errors)
        self.assertIn("exclusive upper bound", joined_errors)

    def test_permanent_writes_and_non_a_risk_are_rejected(self) -> None:
        contract = self.valid_contract()
        contract["risk_class"] = "C"
        unsafe_sql = VALID_DATE_SQL + (
            "\nUPDATE DemoManufacturing.dbo.DemoMovement "
            "SET ItemName = ItemName;\n"
            "DELETE mh FROM DemoManufacturing.dbo.DemoMovement AS mh;\n"
            "CREATE VIEW dbo.ForbiddenView AS SELECT ItemName "
            "FROM DemoManufacturing.dbo.DemoMovement;\n"
        )

        report = self.validate(contract, unsafe_sql)
        joined_errors = " ".join(report.errors)

        self.assertFalse(report.static_gate_passed)
        self.assertIn("only Class A", joined_errors)
        self.assertIn("UPDATE may target only", joined_errors)
        self.assertIn("DELETE alias may target only", joined_errors)
        self.assertIn("forbidden operation: CREATE VIEW", joined_errors)

    def test_local_temp_table_materialization_is_allowed(self) -> None:
        temp_table_sql = """\
DECLARE @StartDateTime datetime2 = ?;
DECLARE @EndDateExclusive datetime2 = ?;
DECLARE @MaxRows int = ?;

SELECT
    mh.ItemName,
    mh.EventDateTime
INTO #Candidates
FROM DemoManufacturing.dbo.DemoMovement AS mh
WHERE mh.EventDateTime >= @StartDateTime
  AND mh.EventDateTime < @EndDateExclusive;

SELECT TOP (@MaxRows)
    c.ItemName,
    c.EventDateTime
FROM #Candidates AS c
WHERE c.EventDateTime >= @StartDateTime
  AND c.EventDateTime < @EndDateExclusive
ORDER BY c.EventDateTime;

DROP TABLE IF EXISTS #Candidates;
"""

        report = self.validate(sql_text=temp_table_sql)

        self.assertTrue(report.static_gate_passed, report.errors)

    def test_indexed_filter_column_function_is_rejected(self) -> None:
        function_sql = VALID_DATE_SQL.replace(
            "  AND mh.EventDateTime < @EndDateExclusive",
            "  AND mh.EventDateTime < @EndDateExclusive\n"
            "  AND DATEDIFF(day, mh.EventDateTime, GETDATE()) >= 0",
        )

        report = self.validate(sql_text=function_sql)

        self.assertFalse(report.static_gate_passed)
        self.assertIn(
            "indexed filter column EventDateTime",
            " ".join(report.errors),
        )

    def test_cte_and_grouped_predicates_are_not_functions(self) -> None:
        contract = self.valid_contract()
        scope = contract["scope"]
        assert isinstance(scope, dict)
        scope["indexed_filter_columns"] = [
            "EventDateTime",
            "ItemName",
        ]
        cte_sql = """\
DECLARE @StartDateTime datetime2 = ?;
DECLARE @EndDateExclusive datetime2 = ?;
DECLARE @MaxRows int = ?;

;WITH Candidates AS
(
    SELECT
        mh.ItemName,
        mh.EventDateTime
    FROM DemoManufacturing.dbo.DemoMovement AS mh
    WHERE mh.EventDateTime >= @StartDateTime
      AND mh.EventDateTime < @EndDateExclusive
      AND (mh.ItemName LIKE 'P%' OR mh.ItemName LIKE 'V%')
)
SELECT TOP (@MaxRows)
    c.ItemName,
    c.EventDateTime
FROM Candidates AS c
WHERE c.EventDateTime >= @StartDateTime
  AND c.EventDateTime < @EndDateExclusive;
"""

        report = self.validate(contract, cte_sql)

        self.assertTrue(report.static_gate_passed, report.errors)

    def test_runtime_thresholds_warn_then_fail(self) -> None:
        warning_contract = self.valid_contract()
        warning_validation = warning_contract["validation"]
        assert isinstance(warning_validation, dict)
        warning_validation["elapsed_seconds"] = 240

        warning_report = self.validate(warning_contract)

        self.assertTrue(warning_report.static_gate_passed)
        self.assertIn("warning threshold", " ".join(warning_report.warnings))

        failure_contract = copy.deepcopy(warning_contract)
        failure_validation = failure_contract["validation"]
        assert isinstance(failure_validation, dict)
        failure_validation["elapsed_seconds"] = 300

        failure_report = self.validate(failure_contract)

        self.assertFalse(failure_report.static_gate_passed)
        self.assertIn("under 300 seconds", " ".join(failure_report.errors))

    def test_scheduled_lot_drilldown_is_rejected(self) -> None:
        contract = self.valid_contract()
        scope = contract["scope"]
        assert isinstance(scope, dict)
        scope.update(
            {
                "type": "lot",
                "parameters": ["MN", "MaxRows"],
                "bound_parameters": ["MN"],
                "detail_cap_parameter": "MaxRows",
                "indexed_filter_columns": ["ItemName"],
            }
        )
        scope.pop("start_parameter")
        scope.pop("end_parameter")
        scheduling = contract["scheduling"]
        assert isinstance(scheduling, dict)
        scheduling.update(
            {
                "enabled": True,
                "on_demand_only": False,
                "business_cadence": "hourly",
                "job_step": "lot drilldown",
            }
        )
        lot_sql = """\
DECLARE @MN nvarchar(80) = ?;
DECLARE @MaxRows int = ?;
SELECT TOP (@MaxRows)
    mh.ItemName,
    mh.EventDateTime
FROM DemoManufacturing.dbo.DemoMovement AS mh
WHERE mh.ItemName = @MN;
"""

        report = self.validate(contract, lot_sql)
        joined_errors = " ".join(report.errors)

        self.assertFalse(report.static_gate_passed)
        self.assertIn("must not be scheduled", joined_errors)
        self.assertIn("on_demand_only", joined_errors)

    def test_environment_cannot_relax_hard_deadline(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 300"):
            get_runtime_guardrails(
                {"PROGRAM_DATA_MES_TOTAL_REFRESH_DEADLINE_SECONDS": "301"}
            )

        guardrails = get_runtime_guardrails({})
        self.assertFalse(guardrails.live_mes_enabled)
        self.assertEqual(guardrails.connection_timeout_seconds, 30)
        self.assertEqual(guardrails.query_timeout_seconds, 300)
        self.assertEqual(guardrails.warning_threshold_seconds, 240)
        self.assertEqual(guardrails.per_query_retry, 0)


if __name__ == "__main__":
    unittest.main()
