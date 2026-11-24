# Offline WIP Scope Partition Reporter

Separate dedicated-workflow lots from general work-in-progress (WIP) using supplied lot prefixes. The CLI reads an existing Kanban assignment report and prints the general-WIP view and the quantities excluded from it.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt. Use Get-FileHash -Algorithm SHA256 in Windows PowerShell or sha256sum -c SHA256SUMS.txt on Ubuntu. Extract the ZIP and open its top-level directory.

Use Python 3.12.16 or 3.15.2. In Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B wip_scope_partition.py examples/assigned-wip.json --exclude-prefix DEMO-PANEL-
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B wip_scope_partition.py examples/assigned-wip.json --exclude-prefix DEMO-PANEL-
~~~

The requirements pin Pydantic 2.14.3 and the runtime wheels qualified on Windows and Ubuntu x64.

## Input and output

Pass the JSON output from Offline WIP-to-Kanban Assignment Checker or a compatible object with a records array. Each record needs lot_id, canonical_product, kanban, total_parts, and parts_completed. Supply one or more --exclude-prefix arguments. Matching is case-insensitive, and a row that matches several prefixes contributes once.

The report gives general total parts, completed parts, and totals for Kanban steps 1 through 6. The panel_flex_excluded fields carry the lot count and parts for the excluded group. The fictional file gives 155 general parts and 70 excluded parts.

Use --product or --kanban to narrow the displayed general rows. The view shows the first 250 matching rows in input order, and wip_results_truncated indicates whether more matched. The totals use the full partition before these display filters and the row limit. Invalid inputs exit with status 2 and empty standard output.
