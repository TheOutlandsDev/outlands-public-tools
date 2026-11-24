# Run the Offline Planning Reconciliation Contract Renderer

Download the source ZIP with SHA256SUMS.txt. In PowerShell, run Get-FileHash .\planning-reconciliation-contract-renderer-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal inside it with Python 3.12 or 3.15. Install the pinned runtime requirements in a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe planning_reconciliation_contract.py examples/fictional-contract.json --metrics examples/fictional-metrics.json --freshness examples/fictional-freshness.json
```

Ubuntu:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python planning_reconciliation_contract.py examples/fictional-contract.json --metrics examples/fictional-metrics.json --freshness examples/fictional-freshness.json
```

Use the example as the contract format. It declares an inactive, development-only reconciliation proposal with database writes disabled. Required tables document authority, freshness, metrics, lifecycle states, counting, decisions, identities, failure behavior, design notes and change history. Required states and source IDs use the fictional names in the example. Counting and identity rule IDs must be unique within their groups.

The optional metrics and freshness options read previously saved observations. The report is UTF-8 plain text. It preserves the matrix order from the contract and has no database connection. A successful render exits with 0. Invalid inputs exit with 2 and an error message. Each input must fit within 512 KiB.

Qualification used Windows and Ubuntu x64, Python 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.
