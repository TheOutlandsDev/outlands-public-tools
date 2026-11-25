from pathlib import Path

from flow_xml import parse_flow_xml
from route_kanban_coverage import AssignmentRules, ProductRoute, read_contract, validate_coverage

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def fixtures(size):
    raw = (EXAMPLES / f"flow-{size}.xml").read_bytes()
    product = read_contract(EXAMPLES / f"product-{size}.json", ProductRoute, "product")
    assignment = read_contract(EXAMPLES / "assignment-rules.json", AssignmentRules, "assignment rules")
    return raw, product, assignment


def test_all_38_fictional_route_steps_have_exact_kanban_coverage():
    raw, product, assignment = fixtures(38)
    document = parse_flow_xml(raw)
    direct = {
        operation: int(kanban)
        for kanban, operations in assignment.direct_kanbans.items()
        for operation in operations
    }

    assert (document.flow_name, document.flow_version, len(document.steps)) == (
        "Fictional Assembly A", "7", 38,
    )
    assert document.source_sha256 == "70d83a60495f39f777b896e8eea4bc972a980ffdeadf51d7145c451039b8830d"
    assert set(product.operation_to_kanban) == {step.step_name for step in document.steps}
    for step in document.steps:
        expected = direct.get(step.step_name)
        if step.step_name in assignment.alternate_operations:
            expected = assignment.alternate_product_kanban[product.part_number]
        assert product.operation_to_kanban[step.step_name] == expected
    assert validate_coverage(raw, product, assignment)["step_count"] == 38


def test_all_40_fictional_route_steps_have_exact_kanban_coverage():
    raw, product, assignment = fixtures(40)
    document = parse_flow_xml(raw)
    direct = {
        operation: int(kanban)
        for kanban, operations in assignment.direct_kanbans.items()
        for operation in operations
    }

    assert (document.flow_name, document.flow_version, len(document.steps)) == (
        "Fictional Assembly B", "9", 40,
    )
    assert document.source_sha256 == "46ef57253faa78d0633512fefd0e4f5fc2e6ab3afd71d7b801c7f544f9211d1b"
    assert set(product.operation_to_kanban) == {step.step_name for step in document.steps}
    assert product.operation_to_kanban["Foam Attachment"] == 5
    assert product.operation_to_kanban["Foam Lamination"] == 5
    for step in document.steps:
        expected = direct.get(step.step_name)
        if step.step_name in assignment.alternate_operations:
            expected = assignment.alternate_product_kanban[product.part_number]
        assert product.operation_to_kanban[step.step_name] == expected
    assert validate_coverage(raw, product, assignment)["step_count"] == 40
