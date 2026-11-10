"""Run the shared source suites omitted by per-tool tests-directory discovery.

This is source qualification, not wheel-install or whole-drive clearance.
Only the fixed, reviewed suites below are executable through this runner.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest


SUITES = {
    "test_assessment_records.py": ["assessment-record-checker"],
    "test_backup_chains.py": ["backup-chain-checker"],
    "test_backup_retention.py": ["backup-retention-planner"],
    "test_configuration_contract.py": ["configuration-contract-checker"],
    "test_connection_plan.py": ["connection-plan-checker"],
    "test_evaluation_metrics.py": ["evaluation-metrics-calculator"],
    "test_html_kanban_tools.py": [
        "html-table-grid-extractor", "html-table-revision-comparator",
        "kanban-board-state-checker", "kanban-move-planner",
    ],
    "test_inventory_diff.py": ["source-inventory-diff"],
    "test_json_xml_structures.py": [
        "json-structure-profiler", "json-structure-revision-comparator",
        "xml-structure-profiler", "xml-structure-revision-comparator",
    ],
    "test_lock_diff.py": ["dependency-lock-diff"],
    "test_pareto_model_interface_tools.py": [
        "model-interface-manifest-checker", "model-interface-revision-checker",
        "pareto-contribution-analyzer", "pareto-cutoff-planner",
    ],
    "test_report_chart_contracts.py": [
        "chart-encoding-contract-checker", "report-chart-coverage-reconciler",
        "report-dataset-binding-checker", "report-parameter-contract-checker",
    ],
    "test_week_csv_tools.py": [
        "csv-column-profiler", "csv-profile-revision-comparator",
        "iso-week-claim-checker", "iso-week-cohort-analyzer",
    ],
    "test_workflow_plans.py": ["workflow-plan-checker"],
}


def child(pattern):
    # Keep imported modules and fixture prints separate from structured results.
    with contextlib.redirect_stdout(sys.stderr):
        suite = unittest.defaultTestLoader.discover("tests", pattern=pattern)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    counts = {
        "tests_run": result.testsRun,
        "skipped": len(result.skipped),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
    }
    if result.testsRun == 0:
        status = "NO_TESTS"
    elif result.testsRun == len(result.skipped):
        status = "ALL_SKIPPED"
    elif result.wasSuccessful():
        status = "PASS"
    else:
        status = "FAIL"
    print(json.dumps({"status": status, **counts}))
    return 0 if status == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=sorted(SUITES), help=argparse.SUPPRESS)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--log-dir", type=Path,
                        help="Optional private diagnostics directory; not public evidence")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error("This qualification lane requires Python 3.15")
    root = Path(os.path.abspath(__file__)).parents[2]
    if args.suite:
        os.chdir(root)
        return child(args.suite)

    for pattern, tools in SUITES.items():
        if not (root / "tests" / pattern).is_file():
            parser.error("A reviewed shared test file is missing")
        if not all((root / "tools" / tool / "README.md").is_file() for tool in tools):
            parser.error("A reviewed source tool is missing")
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
           "PYTHONPATH": ""}
    results = []
    for pattern, tools in SUITES.items():
        try:
            completed = subprocess.run(
                [sys.executable, "-B", os.path.abspath(__file__), "--suite", pattern],
                cwd=root, env=env, capture_output=True, text=True, encoding="utf-8",
                timeout=180,
            )
            if args.log_dir:
                (args.log_dir / (pattern + ".log")).write_text(
                    completed.stderr + completed.stdout, encoding="utf-8", newline="\n")
            try:
                result = json.loads(completed.stdout)
                if not isinstance(result, dict) or result.get("status") not in {
                    "PASS", "FAIL", "NO_TESTS", "ALL_SKIPPED", "PROCESS_ERROR"
                }:
                    result = {"status": "INVALID_RESULT"}
                elif completed.returncode != 0 and result.get("status") == "PASS":
                    result = {"status": "PROCESS_ERROR"}
            except (ValueError, TypeError):
                result = {"status": "INVALID_RESULT"}
            if result["status"] != "PASS":
                # Preserve useful failure evidence in CI without a required log folder.
                print("\n".join(completed.stderr.splitlines()[-60:]), file=sys.stderr)
        except subprocess.TimeoutExpired:
            result = {"status": "TIMEOUT"}
        results.append({"test_file": pattern, "tools": tools, **result})
        print(json.dumps(results[-1]), flush=True)

    all_tools = sorted({tool for tools in SUITES.values() for tool in tools})
    passed_tools = sorted({tool for r in results if r["status"] == "PASS"
                           for tool in r["tools"]})
    report = {
        "schema": "shared-python315-source-validation-v1",
        "python": platform.python_version(), "platform": sys.platform,
        "suite_count": len(results), "tool_count": len(all_tools),
        "passed_tool_count": len(passed_tools),
        "tests_run": sum(r.get("tests_run", 0) for r in results),
        "skipped": sum(r.get("skipped", 0) for r in results),
        "status": "PASS" if all(r["status"] == "PASS" for r in results) else "FAIL",
        "results": results,
        "limits": "Shared source suites only; explicit skips retained. No wheel installation, new dependency qualification, live services, or original drive-content clearance.",
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
