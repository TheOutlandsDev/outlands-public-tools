"""Report environment-specific platform menus and workspace resources."""

import argparse
import json
from math import isfinite
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlsplit


MAX_REGISTRY_BYTES = 1024 * 1024
ENVIRONMENTS = ("development", "production")
MODULE_LIFECYCLES = {"CURRENT_EMBEDDED", "CURRENT_EMBEDDED_READ_ONLY", "PLANNED_DISABLED"}
WORKSPACE_TYPES = {"PRODUCTION_LAB", "ENGINEERING_LAB", "SHARED_OPERATION"}


class PlatformContractError(ValueError):
    """The saved registry or requested workspace is invalid."""


def _text(record, key):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PlatformContractError(f"The registry requires a nonempty {key} field.")
    return value


def _objects(record, key, *, required_items=False):
    items = record.get(key)
    if (not isinstance(items, list) or (required_items and not items)
            or any(not isinstance(item, dict) for item in items)):
        raise PlatformContractError(f"The registry requires a valid {key} array.")
    return items


def _order(record, key="order"):
    value = record.get(key)
    if type(value) is not int or value <= 0:
        raise PlatformContractError(f"The registry requires a positive integer {key}.")
    return value


def _environments(record):
    values = record.get("environments")
    if not isinstance(values, list) or not values or any(value not in ENVIRONMENTS for value in values):
        raise PlatformContractError("The registry contains invalid environments.")
    return set(values)


def _unique(value, seen, label):
    if value in seen:
        raise PlatformContractError(f"The registry contains a duplicate {label}.")
    seen.add(value)


def _link(item, *, external=False):
    _text(item, "label")
    _text(item, "description")
    _order(item)
    href = _text(item, "href")
    if any(char.isspace() or ord(char) < 32 or char == "\\" for char in href):
        raise PlatformContractError("The registry contains an invalid link.")
    if external:
        try:
            parsed = urlsplit(href)
            valid = parsed.scheme in {"http", "https"} and bool(parsed.hostname)
        except ValueError:
            valid = False
    else:
        valid = href.startswith("/") and not href.startswith("//")
    if not valid:
        raise PlatformContractError("The registry contains an invalid link.")
    return href


def validate_platform_contract(contract: dict[str, Any]) -> None:
    """Validate the fields required for the two standalone projections."""
    if not isinstance(contract, dict):
        raise PlatformContractError("The registry must be a JSON object.")

    groups = {}
    for group in _objects(contract, "navigation_groups", required_items=True):
        name = _text(group, "name")
        if name in groups:
            raise PlatformContractError("The registry contains a duplicate navigation group.")
        groups[name] = _order(group), _environments(group)

    module_ids, hrefs, workspace_ids = set(), set(), set()
    for module in _objects(contract, "modules", required_items=True):
        _unique(_text(module, "module_id"), module_ids, "module ID")
        if _text(module, "lifecycle") not in MODULE_LIFECYCLES:
            raise PlatformContractError("A module has an invalid lifecycle.")
        navigation = module.get("navigation")
        if not isinstance(navigation, dict):
            raise PlatformContractError("A module is missing its navigation object.")
        group = groups.get(_text(navigation, "group"))
        if group is None or _order(navigation, "group_order") != group[0]:
            raise PlatformContractError("A module has an invalid navigation group or group order.")
        for item in _objects(navigation, "items"):
            _unique(_link(item), hrefs, "menu link")
            _environments(item)
        if "workspace" in module:
            workspace = module["workspace"]
            if not isinstance(workspace, dict):
                raise PlatformContractError("A workspace must be an object.")
            _unique(_text(workspace, "workspace_id"), workspace_ids, "workspace ID")
            _text(workspace, "label")
            _text(workspace, "description")
            if _text(workspace, "workspace_type") not in WORKSPACE_TYPES:
                raise PlatformContractError("A workspace has an invalid type.")
            resource_hrefs = set()
            for resource in _objects(workspace, "resources", required_items=True):
                _unique(_link(resource), resource_hrefs, "workspace resource link")
                _environments(resource)
                if _text(resource, "presentation") not in {"PRIMARY", "REFERENCE"}:
                    raise PlatformContractError("A workspace resource has an invalid presentation.")

    for item in _objects(contract, "external_navigation_items"):
        group = groups.get(_text(item, "group"))
        if group is None or not _environments(item) <= group[1]:
            raise PlatformContractError("An external link has an invalid group or environment.")
        _unique(_link(item, external=True), hrefs, "menu link")


def build_platform_navigation(
    contract: dict[str, Any],
    *,
    environment: str = "development",
) -> list[dict[str, Any]]:
    """Build deterministic shell navigation from the validated registry."""

    validate_platform_contract(contract)
    groups: dict[tuple[int, str], list[dict[str, Any]]] = {
        (group["order"], group["name"]): []
        for group in contract["navigation_groups"]
        if environment in group["environments"]
    }
    for module in contract["modules"]:
        navigation = module["navigation"]
        registered_group = next(
            group
            for group in contract["navigation_groups"]
            if group["name"] == navigation["group"]
        )
        if environment not in registered_group["environments"]:
            continue
        group_key = (navigation["group_order"], navigation["group"])
        group_items = groups.setdefault(group_key, [])
        for item in navigation["items"]:
            if environment not in item["environments"]:
                continue
            href = item["href"]
            group_items.append(
                {
                    "module_id": module["module_id"],
                    "label": item["label"],
                    "href": href,
                    "href_base": href.split("#", 1)[0],
                    "description": item["description"],
                    "order": item["order"],
                    "is_anchor": "#" in href,
                    "planned": module["lifecycle"] == "PLANNED_DISABLED",
                    "environments": item["environments"],
                    "external": False,
                }
            )

    for item in contract["external_navigation_items"]:
        if environment not in item["environments"]:
            continue
        group = next(
            group for group in contract["navigation_groups"] if group["name"] == item["group"]
        )
        group_items = groups[(group["order"], group["name"])]
        group_items.append(
            {
                "module_id": None,
                "label": item["label"],
                "href": item["href"],
                "href_base": item["href"],
                "description": item["description"],
                "order": item["order"],
                "is_anchor": False,
                "planned": False,
                "environments": item["environments"],
                "external": True,
            }
        )

    return [
        {
            "name": group_name,
            "slug": "nav-group-" + "-".join(group_name.lower().replace("&", "and").split()),
            "items": sorted(items, key=lambda item: (item["order"], item["label"])),
        }
        for (_, group_name), items in sorted(groups.items(), key=lambda value: value[0])
    ]


def build_workspace_landing(
    contract: dict[str, Any],
    *,
    workspace_id: str,
    environment: str,
) -> dict[str, Any]:
    """Return one registered lab/operation workspace and visible resources."""

    validate_platform_contract(contract)
    matches = [
        module
        for module in contract["modules"]
        if module.get("workspace", {}).get("workspace_id") == workspace_id
    ]
    if len(matches) != 1:
        raise PlatformContractError("workspace is not uniquely registered")
    module = matches[0]
    workspace = module["workspace"]
    resources = [
        resource
        for resource in workspace["resources"]
        if environment in resource["environments"]
    ]
    return {
        "module_id": module["module_id"],
        "workspace_id": workspace["workspace_id"],
        "workspace_type": workspace["workspace_type"],
        "label": workspace["label"],
        "description": workspace["description"],
        "resources": sorted(resources, key=lambda row: (row["order"], row["label"])),
        "primary_resources": sorted(
            (row for row in resources if row["presentation"] == "PRIMARY"),
            key=lambda row: (row["order"], row["label"]),
        ),
        "reference_resources": sorted(
            (row for row in resources if row["presentation"] == "REFERENCE"),
            key=lambda row: (row["order"], row["label"]),
        ),
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
    parser.add_argument("--environment", choices=ENVIRONMENTS, default="development")
    parser.add_argument("--workspace", help="Return the named workspace instead of the platform menu")
    args = parser.parse_args(argv)
    try:
        contract = _load_registry(args.registry)
        if args.workspace is None:
            report = build_platform_navigation(contract, environment=args.environment)
        else:
            report = build_workspace_landing(
                contract, workspace_id=args.workspace, environment=args.environment,
            )
    except PlatformContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
