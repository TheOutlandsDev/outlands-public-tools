import json
from pathlib import Path

import pytest

from platform_rehearsal import PlatformContractError, build_platform_status


def contract():
    path = Path(__file__).resolve().parents[1] / "examples/fictional-registry.json"
    return json.loads(path.read_bytes())


def test_platform_status_api_returns_controlled_registry_projection() -> None:
    payload = build_platform_status(contract())
    assert payload["shell_available"] is True
    assert payload["simulation_active"] is False
    assert payload["summary"] == {
        "AVAILABLE": 15,
        "UNAVAILABLE_SIMULATED": 0,
        "PLANNED": 1,
    }
    assert any(
        service["service_id"] == "fictional-evidence-store"
        and service["status"] == "CURRENT_DEVELOPMENT"
        for service in payload["data_services"]
    )


def test_single_module_failure_rehearsal_is_request_scoped() -> None:
    registry = contract()
    simulated = build_platform_status(registry, simulate="sample-inventory")
    normal = build_platform_status(registry)

    inventory = next(
        module for module in simulated["modules"]
        if module["module_id"] == "sample-inventory"
    )
    assert inventory["status"] == "UNAVAILABLE_SIMULATED"
    assert simulated["summary"]["UNAVAILABLE_SIMULATED"] == 1
    assert normal["summary"]["UNAVAILABLE_SIMULATED"] == 0
    assert registry == contract()


def test_all_module_failure_rehearsal_keeps_shell_available() -> None:
    platform_status = build_platform_status(contract(), simulate="all")
    assert platform_status["shell_available"] is True
    assert platform_status["summary"] == {
        "AVAILABLE": 1,
        "UNAVAILABLE_SIMULATED": 14,
        "PLANNED": 1,
    }
    shell = next(
        module for module in platform_status["modules"]
        if module["module_id"] == "platform-shell"
    )
    assert shell["status"] == "AVAILABLE"


def test_failure_rehearsal_rejects_unknown_or_planned_modules() -> None:
    with pytest.raises(PlatformContractError, match="simulation target"):
        build_platform_status(contract(), simulate="sample-next")
    with pytest.raises(PlatformContractError, match="simulation target"):
        build_platform_status(contract(), simulate="not-registered")
