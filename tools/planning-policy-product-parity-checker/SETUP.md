# Run the Offline Planning Policy Product Parity Checker

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\planning-policy-product-parity-checker-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. Install the pinned runtime in a virtual environment.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe policy_product_parity.py examples/baseline.json examples/candidate.json
```

Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python policy_product_parity.py examples/baseline.json examples/candidate.json
```

The fictional example has 12 configured products and 11 blocked products. The candidate lists the same rows in reverse order. The command prints an equivalent status and both counts.

## Snapshot format

Each file is UTF-8 JSON up to 1 MiB. Keep the configured_products and fail_closed_products arrays in the saved snapshot.

| Array | Fields |
| --- | --- |
| configured_products | modality, part_number, lot_prefix, start_quantity, lead_time_days, status |
| fail_closed_products | modality, part_number, lot_prefix, reason |

Each configured modality, part number, and lot prefix must be unique. Each blocked part number must be unique. A blocked lot prefix can be null. Configured start quantities are 1 through 10,000 and lead times are 1 through 365 days. The public format allows configured lot prefixes of 3 through 20 uppercase letters, digits, or hyphens.

The checker compares the configured rules by modality. The part number, lot prefix, start quantity, and lead time must match. A matching set of 11 blocked part numbers must also fail to resolve to a configured rule in either file, including under case-insensitive lookup. The status and reason fields remain snapshot context.

Try changing one candidate start quantity to see a mismatch. The CLI reads both files and leaves them intact. An equivalent pair exits 0. Invalid input or a mismatch exits 2 and reports the error on standard error.

Qualification used Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2 and pinned Pydantic 2.14.3.
