"""Replay an approved fixture and verify its expected planning result."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys

if __name__ == "__main__":
    sys.dont_write_bytecode = True

from allocation_engine import (
    FlexOrder,
    FlexPlan,
    FlexWipLot,
    PlanningConfiguration,
    build_flex_plan,
    comparison_result,
)


FIXTURE_STATUS = "APPROVED_MANUAL_GATE_1"
QUANTITY_BASIS = "caller_declared_available"


class FlexFixtureLoadError(ValueError):
    """The fixture cannot be replayed or its approved result differs."""


def _unique_object(items):
    result = dict(items)
    if len(result) != len(items):
        raise FlexFixtureLoadError("A fixture object contains duplicate field names.")
    return result


def _comparison_bytes(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate_fixture(fixture_path: Path, configuration_path: Path) -> tuple[dict, FlexPlan]:
    """Rebuild the approved fixture with the published allocation engine."""
    try:
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(fixture, dict):
            raise FlexFixtureLoadError("Expected a JSON fixture object.")
        if fixture.get("status") != FIXTURE_STATUS:
            raise FlexFixtureLoadError("The fixture is not approved.")
        configuration = PlanningConfiguration.model_validate_json(configuration_path.read_bytes())
        orders = [
            FlexOrder(**record, modality=fixture["modality"], part_number=fixture["part_number"])
            for record in fixture["orders"]
        ]
        wip = [
            FlexWipLot(**record, modality=fixture["modality"], part_number=fixture["part_number"],
                       quantity_basis=QUANTITY_BASIS)
            for record in fixture["wip"]
        ]
        plan = build_flex_plan(
            planning_date=date.fromisoformat(fixture["planning_date"]),
            modality=fixture["modality"],
            part_number=fixture["part_number"],
            orders=orders,
            wip=wip,
            configuration=configuration,
        )
        expected = fixture["expected"]
        actual = comparison_result(plan)
        if _comparison_bytes(actual) != _comparison_bytes(expected):
            raise FlexFixtureLoadError("The fixture expected result does not match the engine.")
        return fixture, plan
    except FlexFixtureLoadError:
        raise
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise FlexFixtureLoadError("Fixture validation failed.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="Approved fixture and expected result in JSON")
    parser.add_argument("configuration", type=Path, help="Caller-declared planning configuration in JSON")
    args = parser.parse_args()
    try:
        _, plan = validate_fixture(args.fixture, args.configuration)
    except FlexFixtureLoadError as error:
        print(str(error), file=sys.stderr)
        return 2
    report = {
        "status": "match",
        "configuration_id": plan.configuration_id,
        "configuration_version": plan.configuration_version,
        "planning_date": plan.planning_date.isoformat(),
        "result": comparison_result(plan),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
