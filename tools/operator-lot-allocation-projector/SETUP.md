# Offline Operator Lot Allocation Projector

Turn saved Order Needs, work-in-progress (WIP), and planning rules into per-lot operator actions. The JSON report includes orders, actions, and WIP rows for the Offline Operator Queue Filter.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt. Use Get-FileHash -Algorithm SHA256 in Windows PowerShell or sha256sum -c SHA256SUMS.txt on Ubuntu. Extract the ZIP and open its top-level directory.

Use Python 3.12.16 or 3.15.2. In Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B operator_lot_allocation.py examples/order-needs.json examples/operations.json examples/planning-rules.json
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B operator_lot_allocation.py examples/order-needs.json examples/operations.json examples/planning-rules.json
~~~

The requirements pin Pydantic 2.14.3 and the runtime wheels qualified on Windows and Ubuntu x64.

## Prepare inputs and read results

Use the three fictional examples as a schema guide. Supply the saved Order Needs rows in their reported order. The projector checks declared snapshot hashes and eligible WIP totals by product before allocating. It uses the operation-to-Kanban mapping when available and the lot's assigned Kanban otherwise. Higher Kanban steps come first. Within a step, the smallest remaining lot quantity comes first, with lot ID breaking ties. Unused quantities stay available for the next order.

The projector verifies covered and uncovered quantities for each configured order. An unconfigured product has no allocation or recommended start. Each action includes its original source-based ID, timing and priority information. The fictional example reports 550 units of demand, 360 allocated across two actions, and 190 uncovered. It recommends 140 start units for configured demand.

The CLI reads snapshots without changing them. It exits with status 2 and empty standard output if a snapshot, coverage check, or planning rule is invalid. It compares declared snapshot hashes. Verify the underlying files separately when you need evidence of their contents.
