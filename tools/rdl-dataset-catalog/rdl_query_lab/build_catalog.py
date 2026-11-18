"""Extract an auditable, offline catalog of SSRS RDL dataset commands.

This tool never opens a database connection and never executes extracted SQL.
The generated command files contain the RDL CommandText exactly as XML parsing
returns it, encoded as UTF-8 without newline rewriting.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

if __package__:
    from .report_logic import summarize_report_logic
    from .sql_classify import classify_sql
else:
    from report_logic import summarize_report_logic
    from sql_classify import classify_sql


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "examples"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "generated"
FORMAT_VERSION = 2


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    return next((item for item in parent if local_name(item.tag) == name), None)


def children(parent: ET.Element | None, name: str) -> list[ET.Element]:
    if parent is None:
        return []
    return [item for item in parent if local_name(item.tag) == name]


def value(parent: ET.Element | None, name: str) -> str | None:
    item = child(parent, name)
    return item.text if item is not None else None


def slug(text: str) -> str:
    result = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:48]
    return result or "unnamed"


def significant_sql(sql: str) -> str:
    """Remove comments only for lexical classification, not for extraction."""
    without_blocks = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    without_lines = re.sub(r"--[^\r\n]*", " ", without_blocks)
    return without_lines.lstrip("\ufeff \t\r\n;")


def lexical_class(command: str, command_type: str) -> str:
    lead = significant_sql(command)
    if not lead:
        return "empty_command"
    if lead.startswith("="):
        return "rdl_expression"
    if command_type.casefold() == "storedprocedure":
        return "stored_procedure"
    if re.match(r"(?i)^EXEC(?:UTE)?\b", lead):
        return "text_procedure_call"
    if re.match(r"^\[[^\]]+\]\.\[[^\]]+\]", lead):
        return "text_procedure_call"
    if re.match(r"(?i)^SELECT\b", lead):
        return "select_sql"
    return "script_sql"


def command_suffix(kind: str) -> str:
    if kind in {"select_sql", "script_sql"}:
        return ".sql"
    if kind == "rdl_expression":
        return ".expression.txt"
    return ".command.txt"


def source_references(root: ET.Element) -> dict[str, dict[str, str | None]]:
    result: dict[str, dict[str, str | None]] = {}
    for item in children(child(root, "DataSources"), "DataSource"):
        name = item.get("Name", "")
        connection = child(item, "ConnectionProperties")
        result[name] = {
            "shared_reference": value(item, "DataSourceReference"),
            "embedded_provider": value(connection, "DataProvider"),
        }
    return result


def report_parameters(root: ET.Element) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for item in children(child(root, "ReportParameters"), "ReportParameter"):
        valid = child(item, "ValidValues")
        if valid is None:
            valid = child(item, "AvailableValues")
        default = child(item, "DefaultValue")
        valid_reference = child(valid, "DataSetReference")
        default_reference = child(default, "DataSetReference")
        result.append(
            {
                "name": item.get("Name", ""),
                "data_type": value(item, "DataType"),
                "prompt": value(item, "Prompt"),
                "multi_value": (value(item, "MultiValue") or "").casefold() == "true",
                "nullable": (value(item, "Nullable") or "").casefold() == "true",
                "allow_blank": (value(item, "AllowBlank") or "").casefold() == "true",
                "hidden": (value(item, "Hidden") or "").casefold() == "true",
                "available_dataset": value(valid_reference, "DataSetName"),
                "available_value_field": value(valid_reference, "ValueField"),
                "available_label_field": value(valid_reference, "LabelField"),
                "available_values": [
                    {"value": value(option, "Value"), "label": value(option, "Label")}
                    for option in children(child(valid, "ParameterValues"), "ParameterValue")
                ],
                "default_dataset": value(default_reference, "DataSetName"),
                "default_value_field": value(default_reference, "ValueField"),
                "default_values": [option.text for option in children(child(default, "Values"), "Value")],
            }
        )
    return result


def query_parameters(query: ET.Element | None) -> list[dict[str, str | None]]:
    result: list[dict[str, str | None]] = []
    for item in children(child(query, "QueryParameters"), "QueryParameter"):
        result.append({"name": item.get("Name", ""), "value_expression": value(item, "Value")})
    return result


def fields(dataset: ET.Element) -> list[dict[str, str | None]]:
    result: list[dict[str, str | None]] = []
    for item in children(child(dataset, "Fields"), "Field"):
        result.append(
            {
                "name": item.get("Name", ""),
                "data_field": value(item, "DataField"),
                "value_expression": value(item, "Value"),
                "type_name": value(item, "TypeName"),
            }
        )
    return result


def collect(source: Path) -> tuple[dict[str, object], dict[Path, bytes]]:
    paths = sorted(source.rglob("*.rdl"), key=lambda p: p.relative_to(source).as_posix().casefold())
    if not paths:
        raise ValueError(f"No RDL files found under {source}")

    report_rows: list[dict[str, object]] = []
    command_files: dict[Path, bytes] = {}
    snapshot_lines: list[str] = []
    used_ids: set[str] = set()
    kinds: Counter[str] = Counter()
    data_sources: Counter[str] = Counter()

    for source_file in paths:
        relative = source_file.relative_to(source).as_posix()
        raw = source_file.read_bytes()
        source_hash = sha256(raw)
        snapshot_lines.append(f"{relative}\t{source_hash}\n")
        report_id = sha256(relative.encode("utf-8"))[:16]
        if report_id in used_ids:
            raise ValueError(f"Report ID collision for {relative}")
        used_ids.add(report_id)
        root = ET.fromstring(raw)
        source_map = source_references(root)
        subreports = [value(node, "ReportName") for node in root.iter() if local_name(node.tag) == "Subreport"]
        report_filters = sum(1 for node in root.iter() if local_name(node.tag) == "Filters")
        report_logic = summarize_report_logic(root)
        datasets: list[dict[str, object]] = []

        for number, dataset in enumerate(children(child(root, "DataSets"), "DataSet"), start=1):
            dataset_name = dataset.get("Name", f"DataSet{number}")
            query = child(dataset, "Query")
            command_node = child(query, "CommandText")
            command = command_node.text if command_node is not None and command_node.text is not None else ""
            command_type = value(query, "CommandType") or "Text"
            kind = lexical_class(command, command_type)
            kinds[kind] += 1
            source_name = value(query, "DataSourceName")
            source_info = source_map.get(source_name or "", {})
            shared_reference = source_info.get("shared_reference")
            data_sources[str(shared_reference or source_name or "<unresolved>")] += 1
            command_path: Path | None = None
            command_hash: str | None = None
            if command:
                command_path = Path("commands") / report_id / f"{number:03d}_{slug(dataset_name)}{command_suffix(kind)}"
                command_bytes = command.encode("utf-8")
                command_files[command_path] = command_bytes
                command_hash = sha256(command_bytes)

            analysis = classify_sql(command) if command else {
                "tsql_features": [], "external_database_refs": [], "review_flags": []
            }
            datasets.append(
                {
                    "ordinal": number,
                    "name": dataset_name,
                    "data_source_name": source_name,
                    "shared_source_reference": shared_reference,
                    "data_source_resolved_locally": source_name in source_map,
                    "command_type": command_type,
                    "lexical_class": kind,
                    "command_file": command_path.as_posix() if command_path else None,
                    "command_sha256": command_hash,
                    "query_parameters": query_parameters(query),
                    "fields": fields(dataset),
                    "static_analysis": analysis,
                    "validation_state": "source_text_extracted" if kind in {"select_sql", "script_sql"} else "dependency_review_required",
                }
            )

        report_rows.append(
            {
                "report_id": report_id,
                "source_path": relative,
                "source_sha256": source_hash,
                "data_sources": source_map,
                "report_parameters": report_parameters(root),
                "subreports": [item for item in subreports if item],
                "report_filter_container_count": report_filters,
                "report_logic": report_logic,
                "datasets": datasets,
            }
        )

    summary = {
        "report_count": len(report_rows),
        "dataset_count": sum(len(row["datasets"]) for row in report_rows),
        "command_class_counts": dict(sorted(kinds.items())),
        "dataset_shared_source_counts": dict(sorted(data_sources.items())),
        "reports_with_subreports": sum(bool(row["subreports"]) for row in report_rows),
        "reports_with_report_filters": sum(bool(row["report_filter_container_count"]) for row in report_rows),
        "report_logic_counts": {
            key: sum(row["report_logic"]["counts"][key] for row in report_rows)
            for key in (
                "filters", "group_expressions", "sort_expressions", "calculated_fields",
                "subreports", "subreport_parameter_bindings", "expression_nodes",
                "embedded_code_blocks",
            )
        },
        "source_tree_sha256": sha256("".join(snapshot_lines).encode("utf-8")),
    }
    catalog: dict[str, object] = {
        "format_version": FORMAT_VERSION,
        "source_root_name": source.name,
        "summary": summary,
        "reports": report_rows,
    }
    return catalog, command_files


def datasets_csv(catalog: dict[str, object]) -> bytes:
    output = io.StringIO(newline="")
    column_names = [
        "report_id", "source_path", "source_sha256", "dataset_ordinal", "dataset_name",
        "lexical_class", "command_type", "shared_source_reference", "command_file",
        "command_sha256", "query_parameters", "field_names", "tsql_features",
        "external_database_refs", "review_flags", "subreport_count", "ssrs_filter_count",
        "group_expression_count", "sort_expression_count", "calculated_field_count",
        "subreport_parameter_binding_count", "expression_node_count",
        "embedded_code_block_count", "validation_state",
    ]
    writer = csv.DictWriter(output, fieldnames=column_names, lineterminator="\n")
    writer.writeheader()
    for report in catalog["reports"]:
        for dataset in report["datasets"]:
            analysis = dataset["static_analysis"]
            writer.writerow(
                {
                    "report_id": report["report_id"],
                    "source_path": report["source_path"],
                    "source_sha256": report["source_sha256"],
                    "dataset_ordinal": dataset["ordinal"],
                    "dataset_name": dataset["name"],
                    "lexical_class": dataset["lexical_class"],
                    "command_type": dataset["command_type"],
                    "shared_source_reference": dataset["shared_source_reference"],
                    "command_file": dataset["command_file"],
                    "command_sha256": dataset["command_sha256"],
                    "query_parameters": "|".join(item["name"] for item in dataset["query_parameters"]),
                    "field_names": "|".join(item["name"] for item in dataset["fields"]),
                    "tsql_features": "|".join(analysis["tsql_features"]),
                    "external_database_refs": "|".join(analysis["external_database_refs"]),
                    "review_flags": "|".join(analysis["review_flags"]),
                    "subreport_count": len(report["subreports"]),
                    "ssrs_filter_count": report["report_logic"]["counts"]["filters"],
                    "group_expression_count": report["report_logic"]["counts"]["group_expressions"],
                    "sort_expression_count": report["report_logic"]["counts"]["sort_expressions"],
                    "calculated_field_count": report["report_logic"]["counts"]["calculated_fields"],
                    "subreport_parameter_binding_count": report["report_logic"]["counts"]["subreport_parameter_bindings"],
                    "expression_node_count": report["report_logic"]["counts"]["expression_nodes"],
                    "embedded_code_block_count": report["report_logic"]["counts"]["embedded_code_blocks"],
                    "validation_state": dataset["validation_state"],
                }
            )
    return output.getvalue().encode("utf-8")


def review_queue_rows(catalog: dict[str, object]) -> list[dict[str, object]]:
    """Suggest a review order; these tiers are not validation or approval."""
    rows: list[dict[str, object]] = []
    for report in catalog["reports"]:
        datasets = report["datasets"]
        kinds = {item["lexical_class"] for item in datasets}
        source_refs = {str(item["shared_source_reference"] or "<unresolved>") for item in datasets}
        database_refs = {
            reference
            for item in datasets
            for reference in item["static_analysis"]["external_database_refs"]
        }
        query_flags = {
            flag
            for item in datasets
            for flag in item["static_analysis"]["review_flags"]
        }
        report_params = report["report_parameters"]
        datetime_params = [item["name"] for item in report_params if item["data_type"] == "DateTime"]
        parameter_expressions = [
            str(parameter["value_expression"] or "")
            for item in datasets
            for parameter in item["query_parameters"]
        ]
        path_lower = str(report["source_path"]).casefold()
        notes: list[str] = []
        if re.search(r"(?:^|/)(?:_history|_archive|archive|obsolete|old reports?)(?:/|$)", path_lower):
            notes.append("archive_like_path")
        if source_refs != {"/Datasources/DEMO_MESODS"}:
            notes.append("other_or_multiple_shared_source")
        if database_refs - {"DEMO_MESODS"}:
            notes.append("other_explicit_database_qualifier")
        if kinds & {"text_procedure_call", "stored_procedure"}:
            notes.append("procedure_definition_needed")
        if kinds & {"rdl_expression", "empty_command"}:
            notes.append("dynamic_or_missing_command")
        if report["subreports"]:
            notes.append("subreport_dependency")
        if report["report_filter_container_count"]:
            notes.append("ssrs_filter_review")
        if report["report_logic"]["counts"]["calculated_fields"]:
            notes.append("ssrs_calculated_field_review")
        if report["report_logic"]["counts"]["embedded_code_blocks"]:
            notes.append("embedded_code_dependency")
        if any("User!" in expression for expression in parameter_expressions):
            notes.append("user_identity_parameter")
        if "script_sql" in kinds or query_flags & {"possible_write", "possible_ddl", "procedure_or_dynamic_sql_review"}:
            notes.append("tsql_script_review")

        if "archive_like_path" in notes:
            tier = "06_historical_review"
        elif any(note in notes for note in (
            "other_or_multiple_shared_source", "other_explicit_database_qualifier",
            "procedure_definition_needed", "dynamic_or_missing_command", "subreport_dependency",
            "embedded_code_dependency",
        )):
            tier = "05_dependency_review"
        elif "tsql_script_review" in notes:
            tier = "04_tsql_script_review"
        elif any(note in notes for note in (
            "ssrs_filter_review", "ssrs_calculated_field_review", "user_identity_parameter",
        )):
            tier = "03_report_logic_review"
        elif len(datasets) == 1 and datetime_params:
            tier = "01_direct_date_candidate"
        else:
            tier = "02_direct_select_candidate"

        rows.append(
            {
                "tier": tier,
                "report_id": report["report_id"],
                "source_path": report["source_path"],
                "dataset_count": len(datasets),
                "command_classes": "|".join(sorted(kinds)),
                "shared_sources": "|".join(sorted(source_refs)),
                "explicit_database_qualifiers": "|".join(sorted(database_refs)),
                "datetime_parameters": "|".join(datetime_params),
                "subreport_count": len(report["subreports"]),
            "filter_container_count": report["report_filter_container_count"],
            "ssrs_filter_count": report["report_logic"]["counts"]["filters"],
            "calculated_field_count": report["report_logic"]["counts"]["calculated_fields"],
            "expression_node_count": report["report_logic"]["counts"]["expression_nodes"],
            "embedded_code_block_count": report["report_logic"]["counts"]["embedded_code_blocks"],
            "review_notes": "|".join(notes),
                "validation_state": "source_extracted_only",
            }
        )
    return sorted(rows, key=lambda item: (item["tier"], str(item["source_path"]).casefold()))


def review_queue_csv(catalog: dict[str, object]) -> bytes:
    rows = review_queue_rows(catalog)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def summary_md(catalog: dict[str, object]) -> bytes:
    summary = catalog["summary"]
    lines = [
        "# RDL command extraction snapshot",
        "",
        f"Source tree SHA-256: `{summary['source_tree_sha256']}`",
        f"Reports: **{summary['report_count']}**; datasets: **{summary['dataset_count']}**.",
        "",
        "| Lexical command class | Datasets |",
        "| --- | ---: |",
    ]
    for kind, count in summary["command_class_counts"].items():
        lines.append(f"| `{kind}` | {count} |")
    tiers = Counter(item["tier"] for item in review_queue_rows(catalog))
    lines.extend(["", "| Suggested review tier | Reports |", "| --- | ---: |"])
    for tier, count in sorted(tiers.items()):
        lines.append(f"| `{tier}` | {count} |")
    lines.extend(
        [
            "",
            f"Reports with subreports: **{summary['reports_with_subreports']}**.",
            f"Reports with report-side filter containers: **{summary['reports_with_report_filters']}**.",
            f"SSRS filter expressions: **{summary['report_logic_counts']['filters']}**; "
            f"group expressions: **{summary['report_logic_counts']['group_expressions']}**; "
            f"sort expressions: **{summary['report_logic_counts']['sort_expressions']}**.",
            f"Calculated dataset fields: **{summary['report_logic_counts']['calculated_fields']}**; "
            f"subreport parameter bindings: **{summary['report_logic_counts']['subreport_parameter_bindings']}**.",
            f"Expression nodes: **{summary['report_logic_counts']['expression_nodes']}**; "
            f"embedded code blocks: **{summary['report_logic_counts']['embedded_code_blocks']}**.",
            "",
            "The extracted command files are source evidence, not executed or production-approved queries.",
            "Procedure calls need procedure definitions. Query parameters, report grouping, and shared data sources need separate review.",
            "The catalog and commands can be checked without a database by running `python rdl_query_lab/build_catalog.py --check`.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def expected_files(catalog: dict[str, object], commands: dict[Path, bytes]) -> dict[Path, bytes]:
    result = dict(commands)
    result[Path("catalog.json")] = (json.dumps(catalog, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    result[Path("datasets.csv")] = datasets_csv(catalog)
    result[Path("review_queue.csv")] = review_queue_csv(catalog)
    result[Path("summary.md")] = summary_md(catalog)
    return result


def compare_output(output: Path, expected: dict[Path, bytes]) -> list[str]:
    actual_paths = {path.relative_to(output) for path in output.rglob("*") if path.is_file()} if output.exists() else set()
    expected_paths = set(expected)
    errors = [f"Missing: {path.as_posix()}" for path in sorted(expected_paths - actual_paths)]
    errors.extend(f"Unexpected: {path.as_posix()}" for path in sorted(actual_paths - expected_paths))
    for relative in sorted(actual_paths & expected_paths):
        actual = (output / relative).read_bytes()
        if actual != expected[relative]:
            errors.append(f"Content mismatch: {relative.as_posix()}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Directory containing extracted RDL files")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="Generated catalog directory")
    parser.add_argument("--check", action="store_true", help="Read only: compare generated files to every current RDL")
    args = parser.parse_args(argv)

    source = args.source.resolve()
    output = args.out.resolve()
    catalog, commands = collect(source)
    expected = expected_files(catalog, commands)
    if args.check:
        errors = compare_output(output, expected)
        if errors:
            for error in errors[:20]:
                print(error, file=sys.stderr)
            if len(errors) > 20:
                print(f"... and {len(errors) - 20} more differences", file=sys.stderr)
            return 1
        print(f"PASS: {catalog['summary']['report_count']} RDLs, {catalog['summary']['dataset_count']} datasets, {len(commands)} exact command files")
        return 0

    existing_paths = {path.relative_to(output) for path in output.rglob("*") if path.is_file()} if output.exists() else set()
    stale = existing_paths - set(expected)
    if stale:
        print(f"Refusing to leave {len(stale)} stale generated files under {output}; use a fresh --out directory", file=sys.stderr)
        return 1
    for relative, content in expected.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    errors = compare_output(output, expected)
    if errors:
        for error in errors[:20]:
            print(error, file=sys.stderr)
        return 1
    print(f"Wrote and verified {catalog['summary']['report_count']} RDLs, {catalog['summary']['dataset_count']} datasets, {len(commands)} exact command files in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
