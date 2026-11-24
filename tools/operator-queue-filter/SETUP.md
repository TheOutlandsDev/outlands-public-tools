# Offline Operator Queue Filter

Filter a saved operator work-center JSON report and print the visible orders, actions, queue rows, and work-in-progress (WIP) rows.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt. Use Get-FileHash -Algorithm SHA256 in Windows PowerShell or sha256sum -c SHA256SUMS.txt on Ubuntu. Extract the ZIP and open its top-level directory.

Use Python 3.12.16 or 3.15.2. In Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B operator_queue_filter.py examples/work-center.json --product DEMO-A --kanban 5
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B operator_queue_filter.py examples/work-center.json --product DEMO-A --kanban 5
~~~

The requirements pin Pydantic 2.14.3 and the runtime wheels qualified on Windows and Ubuntu x64.

## Input and output

Use an unfiltered saved snapshot with orders, actions, and wip_rows. The CLI uses these three arrays and derives a new queue view from them. Each action needs its saved ID and a matching part number and order ID. The examples contain fictional records.

- Product matches part numbers exactly and applies to orders, actions, and WIP.
- Kanban matches actions and WIP. It drops queue rows that have no visible allocations while preserving the filtered orders list.
- Risk matches orders and actions independently. It leaves the WIP list available under the product and Kanban filters. Choose a risk present in the saved orders or actions.

Queue rows add allocated_quantity from their visible allocations. The original order fields, including allocation_count and covered quantity, describe the saved order. Action IDs and the input file are preserved.

Invalid snapshots and unknown risk categories exit with status 2 and empty standard output.
