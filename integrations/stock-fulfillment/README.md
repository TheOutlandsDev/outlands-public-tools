# Install and use the stock and fulfillment tools

These four independent MIT wheels review supplied stock declarations offline.
They do not contact operational systems or change stock. Supply Python 3.12 or
3.13; runtime dependencies are the standard library only. See the
[terms and limits](../../methodology/STOCK-FULFILLMENT.md) and
[component contracts](components.json).

| Tool | Selected question | Boundary |
| --- | --- | --- |
| [Stock movement ledger checker](../../tools/stock-movement-ledger-checker/README.md) | What closing balance follows from a selected opening and ordered movements? | Does not verify physical stock or post transactions. |
| [Inventory position calculator](../../tools/inventory-position-calculator/README.md) | What position follows from declared on-hand, eligible inbound and reserved demand? | Does not authenticate inbound or change reservations. |
| [Replenishment proposal planner](../../tools/replenishment-proposal-planner/README.md) | What advisory quantity follows from a pinned position and selected policy? | Does not judge policy suitability or purchase. |
| [Shipment coverage reconciler](../../tools/shipment-coverage-reconciler/README.md) | Do selected order, shipment and receipt declarations reconcile? | Does not establish physical dispatch or delivery. |

Reports retain identifiers, quantities and hashes. Keep real inputs and
reports private. A PASS is consistency under one contract, not an operational
authorization or verified physical event.

## Install

Download selected wheels and SHA256SUMS.txt from the
[v1.0.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/stock-fulfillment-wheels-v1.0.0).
Verify hashes before installing. Create a fresh environment outside this
checkout with Python 3.12 or 3.13 and run:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_stock_movement_ledger_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-stock-fulfillment-collection==1.0.0
```

The collection requires all five wheels in one directory and pins the four
components exactly. Run `outlands-stock-fulfillment` to list commands.
Each component has `outlands-TOOL-demo` for an embedded fictional example and
`outlands-TOOL --input PRIVATE_JSON` for an explicit private input. CLI exit
codes are 0 PASS, 1 REVIEW_REQUIRED, 2 refusal and 130 interruption.

## Python API

Each package exposes `check(raw_json_bytes)`. For example:

```python
from importlib.resources import files
from outlands_stock_movement_ledger_checker.movements import check

raw = files("outlands_stock_movement_ledger_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert report["assessment"]["stocks"][0]["closing_quantity"] == 10
assert report["physical_stock_verified"] is False
```

Run `python -B integrations/stock-fulfillment/exercise.py` in an environment
with the collection installed. It uses embedded fictional examples and checks
four positive cases, four review cases, explicit stock and position pins, and
the declared shipment quantity. It does not create an application adapter or
assert that actual stock, purchasing or delivery changed.

## Package verification

`build_wheels.py` reads only SOURCE-MANIFEST-pinned public source and fictional
examples. `verify_wheels.py` checks wheel members, RECORD hashes, fixed ZIP
metadata, exact release hashes, fresh individual installs, the collection,
commands, APIs and positive/review examples. `compare.py` checks byte-identical
platform builds. `public_download.py` anonymously verifies public assets and
repeats fresh installs. Build output must be an existing empty directory outside
the repository.
