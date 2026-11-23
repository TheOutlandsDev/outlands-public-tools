# Run the Offline Planning Demand Scope Reporter

Download the source ZIP and SHA256SUMS.txt. In the download directory, compare the Windows PowerShell output of Get-FileHash .\planning-demand-scope-reporter-0.1.0.zip -Algorithm SHA256 with SHA256SUMS.txt. On Ubuntu run sha256sum -c SHA256SUMS.txt.

Open a terminal inside the extracted ZIP. Use Python 3.12 or 3.15. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe planning_demand_scope.py examples/fictional-snapshot.json
```

On Ubuntu:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python planning_demand_scope.py examples/fictional-snapshot.json
```

The example reports 250 open units across four lines, including 100 in the configured queue and 150 outside the configured scope. Eligible WIP covers those 100 configured units, so no lot starts are required. A partially shipped order contributes its unshipped balance. A fully shipped order contributes zero.

Supply a JSON file shaped like the example. It contains a runtime status record, at most 1,000 order rows and at most 20 queue rows. Provide the recorded active policy status, its SHA-256 and configured product count. Queue rows must agree on one WIP source hash and satisfy the original per-product demand and lot-count rules. Configured scope is measured from the queue, and the policy status and hashes are supplied evidence.

The CLI reads the saved inputs and reports an aggregate. It returns status 0 for a report and 2 for invalid input, inactive policy, or inconsistent queue or demand. It runs offline and performs no database writes.

The validation records cover Windows and Ubuntu with Python 3.12.16 and 3.15.2 and hash-pinned Pydantic 2.14.3.
