# Offline Operator WIP Reconciliation Checker

Reconcile two saved inputs used by the authoritative operator work center. The checker compares their declared order and work-in-progress (WIP) snapshot hashes, then compares eligible WIP quantities separately for every configured current product.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt. Use Get-FileHash -Algorithm SHA256 in Windows PowerShell or sha256sum -c SHA256SUMS.txt on Ubuntu. Extract the ZIP and open its top-level directory.

Use Python 3.12.16 or 3.15.2. In Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B operator_wip_reconciliation.py examples/order-needs.json examples/operations.json
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B operator_wip_reconciliation.py examples/order-needs.json examples/operations.json
~~~

The requirements pin Pydantic 2.14.3 and the runtime wheels qualified on Windows and Ubuntu x64.

## Prepare the saved snapshots

Order Needs supplies source.revision_sha256 and source.wip_source_sha256, current order rows with part_number, and product summaries with part_number, configured, and eligible_wip. The operations snapshot supplies active_revision.sha256, wip_source_sha256, and wip_rows. Each WIP row carries lot_id, source_product, canonical_product, and total_parts.

The original verification-lot rule excludes rows whose source and canonical products differ, whose lot ID starts with V, or whose source product ends with V. The comparisons for those prefixes and suffixes are case-insensitive. Only configured summaries for current products are reconciled, and a configured product with no eligible rows totals zero.

On success the report prints PASS, the matching declared hashes, and eligible quantities by product. The fictional example reconciles 240 and 120 units for two products and zero for a third. A discrepancy in either hash or any product quantity exits with status 2 and empty standard output. The checker reads these inputs without allocating orders or changing the saved files. The supplied checksums identify snapshots. Verify the underlying snapshot files separately to establish their contents.
