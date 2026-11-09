# Install and use the material traceability tools

These four independent MIT wheels review supplied material declarations offline.
They do not contact operational systems or perform transfers. Supply Python 3.12
or 3.13; runtime dependencies are the standard library only. See the
[terms and limits](../../methodology/MATERIAL-TRACEABILITY.md) and
[component contracts](components.json).

| Tool | Selected question | Boundary |
| --- | --- | --- |
| [BOM contract checker](../../tools/bom-contract-checker/README.md) | What whole-unit requirements follow from declared components and links? | Does not establish equipment suitability or inventory availability. |
| [Lot identity checker](../../tools/lot-identity-checker/README.md) | Which declared aliases resolve to canonical lots? | Does not prove physical lot identity or post stock. |
| [Material allocation checker](../../tools/material-allocation-checker/README.md) | Do supplied demands and lot reservations reconcile? | Does not select or execute allocations. |
| [Handoff lifecycle checker](../../tools/handoff-lifecycle-checker/README.md) | Are declared handoffs and receipts internally consistent? | Does not prove physical transfer, delivery or receipt authenticity. |

Reports retain identifiers, quantities and hashes. Keep real inputs and reports
private. A PASS establishes consistency under one declared contract, not an
operational authorization or verified physical event.

## Install

Download selected wheels and SHA256SUMS.txt from the
[v1.0.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/material-traceability-wheels-v1.0.0).
Verify hashes before installing. Create a fresh environment outside this
checkout with Python 3.12 or 3.13 and run:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_bom_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-material-traceability-collection==1.0.0
```

The collection requires all five wheels in one directory and pins the four
components exactly. Run `outlands-material-traceability` to list commands.
Each component has `outlands-TOOL-demo` for an embedded fictional example and
`outlands-TOOL --input PRIVATE_JSON` for an explicit private input. CLI exit
codes are 0 PASS, 1 REVIEW_REQUIRED, 2 refusal and 130 interruption.

## Python API

Each package exposes `check(raw_json_bytes)`. For example:

```python
from importlib.resources import files
from outlands_bom_contract_checker.bom import check

raw = files("outlands_bom_contract_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert {row["component_id"]: row["quantity"] for row in report["requirements"] if row["is_leaf"]} == {"blower-motor": 2, "panel-filter": 4}
assert report["inventory_availability_checked"] is False
```

Run `python -B integrations/material-traceability/exercise.py` in an
environment with the collection installed. It connects four fictional records
with explicit transformations, checks positive and review cases, and confirms
that no operational change was authorized or performed. It is a worked example,
not a live application adapter.

## Package verification

`build_wheels.py` reads only SOURCE-MANIFEST-pinned public source and fictional
examples. `verify_wheels.py` checks wheel members, RECORD hashes, fixed ZIP
metadata, exact release hashes, fresh individual installs, the collection,
commands, APIs and positive/review examples. `compare.py` checks byte-identical
platform builds. `public_download.py` anonymously verifies public assets and
repeats fresh installs. Build output must be an existing empty directory outside
the repository.
