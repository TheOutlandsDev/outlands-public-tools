# Run the Offline Order Lot Allocation Validator

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\order-lot-allocation-validator-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal inside it with Python 3.12 or 3.15. Install the pinned runtime requirements in a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe order_lot_allocation.py examples/fictional-allocation.json
```

Ubuntu:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python order_lot_allocation.py examples/fictional-allocation.json
```

Use the example JSON as the input format. Supply a positive order_quantity and, when recorded, a nonnegative ship_quantity. Supply lot_count and lot_allocations together. The count must match the number of rows and be at most 20. Each lot ID must be unique regardless of case and each circuits value must be between 1 and 100,000. The allocated total must fit within the order quantity and equal a positive ship quantity.

The example outputs lot_ids as DEMO-LOT-01 DEMO-LOT-02 and lot_quantities as 160 140. Both fields keep the input row order. An omitted allocation pair prints an empty JSON object. An explicit count of zero with an empty allocation array prints the two fields as null, subject to the same shipment quantity rule.

The CLI prints accepted fields to stdout and leaves the saved order unchanged. It exits 0 for accepted input and 2 for a validation or read error.

Qualification used Windows and Ubuntu x64, Python 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.
