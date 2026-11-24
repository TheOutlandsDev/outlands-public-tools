import json
from pathlib import Path

from platform_navigation import build_platform_navigation, build_workspace_landing


def contract():
    path = Path(__file__).resolve().parents[1] / "examples/fictional-registry.json"
    return json.loads(path.read_bytes())


def test_navigation_is_registry_driven_and_deterministic() -> None:
    navigation = build_platform_navigation(contract())
    assert [group["name"] for group in navigation] == [
        "Operations",
        "References",
        "Workspaces",
        "Training",
        "Support",
        "Development only",
    ]
    links = [item for group in navigation for item in group["items"]]
    assert len({item["href"] for item in links}) == len(links)
    assert next(item for item in links if item["href"] == "/demo/orders")["planned"] is False
    assert next(
        item for item in links if item["href"] == "/demo/studio"
    )["label"] == "Studio"
    assert not any(item["href"] == "/retired-plan" for item in links)
    references = navigation[1]
    assert [item["label"] for item in references["items"]] == [
        "Safety sheets",
        "Sample inventory",
        "Training inventory",
    ]
    assert all(item["external"] is True for item in references["items"])
    assert navigation[3]["items"] == []
    assert navigation[4]["items"] == []
    development = navigation[-1]
    assert [item["label"] for item in development["items"]] == [
        "Route Samples",
        "XML Examples",
        "Example Catalog",
        "Product Rules",
        "Candidate Inputs",
        "Workflow Notes",
        "Verification Results",
        "Module Diagnostics",
    ]


def test_production_navigation_excludes_development_tools() -> None:
    navigation = build_platform_navigation(contract(), environment="production")
    links = [item for group in navigation for item in group["items"]]
    hrefs = {item["href"] for item in links}

    assert "/legacy-orders" not in hrefs
    assert "/sample/routes" not in hrefs
    assert "/demo/studio" in hrefs
    assert "/demo/orders" in hrefs
    assert "/dev/module-diagnostics" not in hrefs
    assert "/legacy-operations" not in hrefs
    assert "/dev/examples" not in hrefs
    assert "/dev/xml" not in hrefs
    assert "Development only" not in {group["name"] for group in navigation}
    assert [group["name"] for group in navigation] == [
        "Operations",
        "References",
        "Workspaces",
        "Training",
        "Support",
    ]


def test_workspace_collects_environment_safe_resources() -> None:
    development = build_workspace_landing(
        contract(), workspace_id="demo-studio", environment="development"
    )
    production = build_workspace_landing(
        contract(), workspace_id="demo-studio", environment="production"
    )

    assert development["workspace_type"] == "PRODUCTION_LAB"
    assert [resource["href"] for resource in development["resources"]] == [
        "/demo/studio/operator-desk",
        "/demo/studio/review-queue",
        "/demo/studio/plan-preview",
        "/demo/studio/materials",
        "/demo/studio/fulfillment",
        "/sample/routes",
    ]
    assert [resource["href"] for resource in development["primary_resources"]] == [
        "/demo/studio/operator-desk",
        "/demo/studio/review-queue",
        "/demo/studio/plan-preview",
        "/demo/studio/materials",
    ]
    assert [resource["href"] for resource in development["reference_resources"]] == [
        "/demo/studio/fulfillment",
        "/sample/routes",
    ]
    assert [resource["href"] for resource in production["resources"]] == [
        "/demo/studio/operator-desk",
        "/demo/studio/review-queue",
        "/demo/studio/plan-preview",
        "/demo/studio/materials",
        "/demo/studio/fulfillment",
        "/sample/routes",
    ]
