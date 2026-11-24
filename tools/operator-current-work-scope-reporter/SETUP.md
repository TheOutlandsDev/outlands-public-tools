# Offline Operator Current-Work Scope Reporter

Show the current-work or full-schedule view of a saved Operator Queue Filter or work-center JSON report. The CLI prints visible queue rows with their allocations, WIP rows, and a count for each.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt. Use Get-FileHash -Algorithm SHA256 in Windows PowerShell or sha256sum -c SHA256SUMS.txt on Ubuntu. Extract the ZIP and open its top-level directory.

Use Python 3.12.16 or 3.15.2. In Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B operator_current_work.py examples/work-center.json
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B operator_current_work.py examples/work-center.json
~~~

The requirements pin Pydantic 2.14.3 and the runtime wheels qualified on Windows and Ubuntu x64.

## Choose the scope

Current work is the default. It selects a queue row when the risk is exactly Past due or Next shipment, its uncovered quantity is positive, or its recommended lot count is positive. All allocations for those rows stay visible. WIP rows stay visible when a selected allocation references the same lot ID. Two allocations for one lot both count as allocations.

Use --scope full to include all queue rows and all WIP in the supplied file. Both modes preserve row order and the fields in selected rows. The counts describe the displayed rows. For the complete schedule, supply a report saved without earlier filters.

The fictional example returns four orders, three allocations, and two WIP rows in current mode. Full mode returns five orders, four allocations, and four WIP rows. The CLI only reads the saved file. Invalid input exits with status 2 and empty standard output.
