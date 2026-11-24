"""Report platform module status and rehearse offline failure scenarios."""

import argparse
import json
from math import isfinite
from pathlib import Path
import sys
from typing import Any


MAX_REGISTRY_BYTES = 1024 * 1024
MODULE_LIFECYCLES = {
    "CURRENT_EMBEDDED",
    "CURRENT_EMBEDDED_READ_ONLY",
    "PLANNED_DISABLED",
}
FAILURE_MODES = {"SHELL_REMAINS_AVAILABLE", "ISOLATED_UNAVAILABLE_CARD"}


class PlatformContractError(ValueError):
    """The saved registry or requested rehearsal is invalid."""


def _text(record, field):
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PlatformContractError(f"The registry requires a nonempty {field} field.")
    return value


def validate_platform_contract(contract: dict[str, Any]) -> None:
    """Validate the registry fields used by the offline status projection."""
    if not isinstance(contract, dict):
        raise PlatformContractError("The registry must be a JSON object.")
    for field in ("contract_version", "status", "platform_name", "organization_name"):
        _text(contract, field)

    modules = contract.get("modules")
    services = contract.get("data_services")
    if not isinstance(modules, list) or not modules or not isinstance(services, list):
        raise PlatformContractError("The registry requires module and data-service arrays.")
    if any(not isinstance(item, dict) for item in modules + services):
        raise PlatformContractError("Modules and data services must be objects.")

    module_ids = [_text(module, "module_id") for module in modules]
    if len(module_ids) != len(set(module_ids)) or "all" in module_ids:
        raise PlatformContractError("Module identifiers must be unique and cannot use the reserved target 'all'.")
    service_ids = [_text(service, "service_id") for service in services]
    if len(service_ids) != len(set(service_ids)):
        raise PlatformContractError("Data-service identifiers must be unique.")
    known_services = set(service_ids)
    for module in modules:
        _text(module, "display_name")
        if _text(module, "lifecycle") not in MODULE_LIFECYCLES:
            raise PlatformContractError("A module has an invalid lifecycle.")
        if _text(module, "failure_mode") not in FAILURE_MODES:
            raise PlatformContractError("A module has an invalid failure mode.")
        if not _text(module, "health_endpoint").startswith("/health/"):
            raise PlatformContractError("A module health endpoint must start with /health/.")
        stores = module.get("data_stores")
        if not isinstance(stores, list) or any(
            not isinstance(store, str) or store not in known_services for store in stores
        ):
            raise PlatformContractError("A module refers to an unregistered data service.")
        navigation = module.get("navigation")
        if not isinstance(navigation, dict) or not isinstance(navigation.get("items"), list):
            raise PlatformContractError("A module must declare a navigation items array.")
        for item in navigation["items"]:
            if not isinstance(item, dict):
                raise PlatformContractError("Navigation entries must be objects.")
            _text(item, "description")
            _text(item, "href")

    shell = next((module for module in modules if module["module_id"] == "platform-shell"), None)
    if (shell is None or not shell["lifecycle"].startswith("CURRENT_EMBEDDED")
            or shell["failure_mode"] != "SHELL_REMAINS_AVAILABLE" or shell.get("dependencies")):
        raise PlatformContractError("The registry requires an available, independent platform shell.")


def build_platform_status(
    contract: dict[str, Any],
    *,
    simulate: str | None = None,
) -> dict[str, Any]:
    """Return a read-only, request-scoped module status projection.

    Simulation never changes the registry, a container, or application state. It is
    deliberately limited to currently embedded business modules so the shell's
    isolation behavior can be rehearsed without creating a misleading outage.
    """

    validate_platform_contract(contract)
    current_business_ids = {
        module["module_id"]
        for module in contract["modules"]
        if module["lifecycle"].startswith("CURRENT_EMBEDDED")
        and module["module_id"] != "platform-shell"
    }
    normalized_simulation = simulate.strip() if simulate else None
    if normalized_simulation not in {None, "all"} and normalized_simulation not in current_business_ids:
        raise PlatformContractError("simulation target is not an active business module")

    module_rows: list[dict[str, Any]] = []
    for module in contract["modules"]:
        module_id = module["module_id"]
        simulated_unavailable = module_id != "platform-shell" and (
            normalized_simulation == "all" or normalized_simulation == module_id
        )
        if module["lifecycle"] == "PLANNED_DISABLED":
            module_status = "PLANNED"
        elif simulated_unavailable:
            module_status = "UNAVAILABLE_SIMULATED"
        else:
            module_status = "AVAILABLE"
        first_item = next(iter(module["navigation"]["items"]), None)
        module_rows.append(
            {
                "module_id": module_id,
                "display_name": module["display_name"],
                "description": (
                    first_item["description"]
                    if first_item
                    else "Registered platform capability with no active navigation entry."
                ),
                "lifecycle": module["lifecycle"],
                "status": module_status,
                "failure_mode": module["failure_mode"],
                "health_endpoint": module["health_endpoint"],
                "primary_href": first_item["href"] if first_item else None,
                "data_stores": module["data_stores"],
            }
        )

    summary = {
        status: sum(module["status"] == status for module in module_rows)
        for status in ("AVAILABLE", "UNAVAILABLE_SIMULATED", "PLANNED")
    }
    return {
        "contract_version": contract["contract_version"],
        "contract_status": contract["status"],
        "platform_name": contract["platform_name"],
        "organization_name": contract["organization_name"],
        "simulation": normalized_simulation,
        "simulation_active": normalized_simulation is not None,
        "shell_available": True,
        "summary": summary,
        "modules": module_rows,
        "data_services": contract["data_services"],
    }


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PlatformContractError("The registry contains a duplicate JSON field.")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise PlatformContractError("The registry contains a nonfinite JSON value.")


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        _invalid_constant(value)
    return number


def _load_registry(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise PlatformContractError("The registry must be a readable file.")
        with path.open("rb") as stream:
            raw = stream.read(MAX_REGISTRY_BYTES + 1)
    except OSError as exc:
        raise PlatformContractError("The registry could not be read.") from exc
    if len(raw) > MAX_REGISTRY_BYTES:
        raise PlatformContractError("The registry exceeds the 1 MiB input limit.")
    try:
        return json.loads(raw.decode("utf-8-sig"),
                          object_pairs_hook=_unique_fields, parse_constant=_invalid_constant,
                          parse_float=_finite_float)
    except PlatformContractError:
        raise
    except (ValueError, RecursionError) as exc:
        raise PlatformContractError("The registry is not valid JSON.") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--simulate", help="A current business module ID or all")
    args = parser.parse_args(argv)
    try:
        report = build_platform_status(_load_registry(args.registry), simulate=args.simulate)
    except PlatformContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
