# Offline Planning Policy Difference Verifier

Compare saved detailed planning and lot reservation results from before and after a policy change. The CLI reads three UTF-8 JSON files and prints a verification report. It exits with status 2 and leaves standard output empty when any check fails.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt. Use Get-FileHash -Algorithm SHA256 in Windows PowerShell or sha256sum -c SHA256SUMS.txt on Ubuntu. Extract the ZIP and open its top-level directory.

Use Python 3.12.16 or 3.15.2. In Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B policy_difference.py examples/before.json examples/after.json examples/review.json
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B policy_difference.py examples/before.json examples/after.json examples/review.json
~~~

The requirements pin Pydantic 2.14.3 and the runtime dependency wheels qualified on Windows and Ubuntu x64.

## Read the report

The before and after snapshots contain a detailed_planning object and a reservation_boundary object. The detailed planning object carries recommended_start_by_order and any comparison fields you want verified. The reservation object carries recommended_lot_count and allowance_demand. The review file supplies both expected vectors for each case and a reason. See the fictional examples for the exact field names.

The two case records report REVIEWED_DIFFERENCE and the SHA-256 of each canonical result vector. In the example, the second order's recommended start falls from 220 to 200. The reservation changes from two lots for 330 units to one lot for 300 units. Every other supplied detailed planning field must compare equal.

Use previously reviewed evidence as input. The tool verifies saved results against that evidence. It reads local JSON and performs no database writes or reservations.
