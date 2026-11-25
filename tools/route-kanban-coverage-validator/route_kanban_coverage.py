"""Verify a saved route's complete operation-to-Kanban coverage."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from flow_xml import MAX_FLOW_XML_BYTES, parse_flow_xml

MAX_JSON_BYTES = 1024 * 1024
Operation = Annotated[str, StringConstraints(min_length=1, max_length=256)]
Kanban = Annotated[int, Field(strict=True, ge=1, le=6)]
Bucket = Literal["1", "2", "3", "4", "5", "6"]


class CoverageError(ValueError):
    """A saved flow or its Kanban coverage failed validation."""


class ProductRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    part_number: Operation
    flow_name: Operation
    flow_version: Operation
    flow_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_to_kanban: dict[Operation, Kanban] = Field(min_length=1, max_length=1000)


class AssignmentRules(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    direct_kanbans: dict[Bucket, tuple[Operation, ...]]
    alternate_operations: tuple[Operation, ...] = Field(max_length=1000)
    alternate_product_kanban: dict[Operation, Kanban] = Field(max_length=1000)

    @model_validator(mode="after")
    def validate_operations(self):
        names = [name for operations in self.direct_kanbans.values() for name in operations]
        names.extend(self.alternate_operations)
        if len(names) > 1000 or any(not name.strip() or name != name.strip() for name in names):
            raise ValueError("Assignment rules require bounded and trimmed operation names")
        if len(names) != len(set(names)):
            raise ValueError("An operation must have one assignment rule")
        return self


def read_bounded(path: Path, limit: int) -> bytes:
    if not path.is_file():
        raise CoverageError("Expected a saved file")
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise CoverageError("Input exceeds its size limit")
    return content


def unique_fields(pairs):
    result = dict(pairs)
    if len(pairs) != len(result):
        raise ValueError("Duplicate JSON field")
    return result


def read_contract(path: Path, model, label: str):
    try:
        content = read_bounded(path, MAX_JSON_BYTES)
        fields = json.loads(content.decode("utf-8-sig"), object_pairs_hook=unique_fields)
        return model.model_validate(fields)
    except (OSError, ValueError, RecursionError) as exc:
        raise CoverageError(f"Invalid {label} JSON") from exc


def validate_coverage(content: bytes, product: ProductRoute, assignment: AssignmentRules) -> dict:
    if len(content) > MAX_FLOW_XML_BYTES:
        raise CoverageError("Flow XML exceeds its size limit")
    if sha256(content).hexdigest() != product.flow_sha256:
        raise CoverageError("Flow XML SHA-256 differs from the product pin")
    try:
        content.decode("utf-8-sig")
    except UnicodeError as exc:
        raise CoverageError("Flow XML must be UTF-8 text") from exc
    if b"\x00" in content:
        raise CoverageError("Flow XML must be UTF-8 text")
    try:
        document = parse_flow_xml(content)
    except (ValueError, LookupError) as exc:
        raise CoverageError("Flow XML violates the parsing and safety contract") from exc
    if (document.flow_name, document.flow_version) != (product.flow_name, product.flow_version):
        raise CoverageError("Flow name or version differs from the product pin")

    route_operations = {step.step_name for step in document.steps}
    configured = set(product.operation_to_kanban)
    if route_operations != configured:
        missing = len(route_operations - configured)
        extra = len(configured - route_operations)
        raise CoverageError(f"Product assignment coverage has {missing} missing and {extra} extra operations")

    direct = {name: int(kanban) for kanban, names in assignment.direct_kanbans.items() for name in names}
    alternate = set(assignment.alternate_operations)
    results = []
    for step in document.steps:
        name = step.step_name
        expected = direct.get(name)
        rule = "DIRECT_OPERATION"
        if name in alternate:
            expected = assignment.alternate_product_kanban.get(product.part_number)
            rule = "ALTERNATE_PRODUCT"
        if expected is None:
            raise CoverageError(f"Route position {step.position} has no applicable Kanban rule")
        if product.operation_to_kanban[name] != expected:
            raise CoverageError(f"Route position {step.position} maps to the wrong Kanban")
        results.append({"position": step.position, "operation": name, "kanban": expected, "rule": rule})
    return {
        "status": "PASS",
        "flow_name": document.flow_name,
        "flow_version": document.flow_version,
        "source_sha256": document.source_sha256,
        "part_number": product.part_number,
        "step_count": len(results),
        "operation_count": len(route_operations),
        "steps": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("flow", type=Path)
    parser.add_argument("product", type=Path)
    parser.add_argument("assignment_rules", type=Path)
    args = parser.parse_args()
    try:
        product = read_contract(args.product, ProductRoute, "product")
        assignment = read_contract(args.assignment_rules, AssignmentRules, "assignment rules")
        report = validate_coverage(read_bounded(args.flow, MAX_FLOW_XML_BYTES), product, assignment)
    except CoverageError as exc:
        print(f"Route coverage: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("Route coverage: cannot read saved flow XML", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
