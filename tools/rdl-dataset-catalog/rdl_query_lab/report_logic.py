"""Inventory SSRS transformations that live outside a dataset's CommandText.

The input is an already parsed RDL XML root. This module only reads that tree;
it does not evaluate VB expressions or change report/query semantics.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from collections.abc import Iterator


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    return next((item for item in parent if _local_name(item.tag) == name), None)


def _children(parent: ET.Element | None, name: str) -> list[ET.Element]:
    if parent is None:
        return []
    return [item for item in parent if _local_name(item.tag) == name]


def _text(parent: ET.Element | None, name: str) -> str | None:
    item = _child(parent, name)
    return item.text if item is not None else None


def _walk(
    node: ET.Element,
    path: str,
    ancestors: tuple[ET.Element, ...] = (),
) -> Iterator[tuple[ET.Element, str, tuple[ET.Element, ...]]]:
    """Walk in document order with stable, namespace-free, indexed paths."""
    yield node, path, ancestors
    ordinals: dict[str, int] = {}
    for item in node:
        name = _local_name(item.tag)
        ordinals[name] = ordinals.get(name, 0) + 1
        yield from _walk(item, f"{path}/{name}[{ordinals[name]}]", ancestors + (node,))


def _nearest_ancestor(ancestors: tuple[ET.Element, ...], name: str) -> ET.Element | None:
    return next((item for item in reversed(ancestors) if _local_name(item.tag) == name), None)


def summarize_report_logic(root: ET.Element) -> dict[str, object]:
    """Return deterministic locations and text for report-side RDL behavior.

    A filter is counted per ``Filter`` child, not per ``Filters`` wrapper. Field
    ``Value`` nodes under datasets are counted as calculated fields; plain
    ``DataField`` mappings are omitted. Subreport bindings are counted per
    parameter even when the parameter value is a literal or empty. The generic
    expression inventory retains exact parsed XML text and includes captured
    categories, display expressions, and expressions in other RDL elements.
    Embedded VB ``Code`` blocks are inventoried by hash, without their text.
    """
    filters: list[dict[str, object]] = []
    groups: list[dict[str, str | None]] = []
    sorts: list[dict[str, str | None]] = []
    calculated_fields: list[dict[str, str | None]] = []
    subreport_bindings: list[dict[str, str | None]] = []
    expression_nodes: list[dict[str, str]] = []
    code_blocks: list[dict[str, str]] = []
    subreport_count = 0

    for node, location, ancestors in _walk(root, f"{_local_name(root.tag)}[1]"):
        name = _local_name(node.tag)
        parent_name = _local_name(ancestors[-1].tag) if ancestors else None

        for text_slot, expression in (("text", node.text), ("tail", node.tail)):
            if expression is not None and expression.lstrip().startswith("="):
                expression_nodes.append(
                    {
                        "location": location,
                        "element_name": name,
                        "text_slot": text_slot,
                        "expression": expression,
                    }
                )

        if name == "Code" and node.text and node.text.strip():
            code_blocks.append(
                {
                    "location": location,
                    "sha256": hashlib.sha256(node.text.encode("utf-8")).hexdigest(),
                }
            )

        if name == "Filter" and parent_name == "Filters":
            filters.append(
                {
                    "location": location,
                    "expression": _text(node, "FilterExpression"),
                    "operator": _text(node, "Operator"),
                    "values": [item.text for item in _children(_child(node, "FilterValues"), "FilterValue")],
                }
            )
        elif name == "GroupExpression" and parent_name == "GroupExpressions":
            groups.append({"location": location, "expression": node.text})
        elif name == "SortExpression" and parent_name in {"SortExpressions", "UserSort"}:
            sort_value = _child(node, "Value")
            sorts.append(
                {
                    "location": location,
                    "expression": sort_value.text if sort_value is not None else node.text,
                    "container": parent_name,
                }
            )
        elif name == "Field" and parent_name == "Fields":
            dataset = _nearest_ancestor(ancestors, "DataSet")
            field_value = _child(node, "Value")
            if dataset is not None and field_value is not None:
                calculated_fields.append(
                    {
                        "location": f"{location}/Value[1]",
                        "dataset": dataset.get("Name"),
                        "field": node.get("Name"),
                        "expression": field_value.text,
                    }
                )
        elif name == "Subreport":
            subreport_count += 1
            for index, parameter in enumerate(_children(_child(node, "Parameters"), "Parameter"), start=1):
                subreport_bindings.append(
                    {
                        "location": f"{location}/Parameters[1]/Parameter[{index}]/Value[1]",
                        "subreport": node.get("Name"),
                        "report_name": _text(node, "ReportName"),
                        "parameter": parameter.get("Name"),
                        "expression": _text(parameter, "Value"),
                    }
                )

    counts = {
        "filters": len(filters),
        "group_expressions": len(groups),
        "sort_expressions": len(sorts),
        "calculated_fields": len(calculated_fields),
        "subreports": subreport_count,
        "subreport_parameter_bindings": len(subreport_bindings),
        "expression_nodes": len(expression_nodes),
        "embedded_code_blocks": len(code_blocks),
    }
    return {
        "counts": counts,
        "filters": filters,
        "group_expressions": groups,
        "sort_expressions": sorts,
        "calculated_fields": calculated_fields,
        "subreport_parameter_bindings": subreport_bindings,
        "expression_nodes": expression_nodes,
        "embedded_code_blocks": code_blocks,
    }
