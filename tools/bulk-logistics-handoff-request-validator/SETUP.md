# Run the Offline Bulk Logistics Handoff Request Validator

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\bulk-logistics-handoff-request-validator-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal inside it with Python 3.12 or 3.15. Install the pinned requirements in a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe bulk_logistics_handoff.py ready examples/fictional-ready.json
.\.venv\Scripts\python.exe bulk_logistics_handoff.py return examples/fictional-return.json
```

Ubuntu:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python bulk_logistics_handoff.py ready examples/fictional-ready.json
.venv/bin/python bulk_logistics_handoff.py return examples/fictional-return.json
```

Use the example for the relevant action. Include each order's row ID, source revision hash, expected order version, and selected lots. A ready request carries positive lot quantities and an optional comment. A return request carries the expected state version for each lot and a batch reason of 3 to 500 characters.

Each batch has 1 to 25 distinct orders, each order has 1 to 20 lots, and the batch has at most 100 lots. Lot IDs within an order must be unique regardless of case. The original schema permits ready quantities from 1 to 100,000.

The CLI reads the saved request and prints its action and validated order and lot counts. It leaves the input unchanged and performs no handoff or database operations. Exit status is 0 for valid input and 2 for invalid or unreadable input.

Qualification used Windows and Ubuntu x64, Python 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.
