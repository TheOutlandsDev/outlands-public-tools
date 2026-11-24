# Run the Offline Order Void Carryover Checker

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\order-void-carryover-checker-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal inside it. Install the pinned requirements in a virtual environment.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe order_void_carryover.py examples/fictional-void.json
```

Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python order_void_carryover.py examples/fictional-void.json
```

Use the fictional request as a template. Both orders specify the same eight fields.

| Field | Expected value |
| --- | --- |
| row_id | 24 lowercase hex characters |
| source_sheet | C or P |
| source_row | Integer from 4 through 500 |
| part_number | Text |
| purchase_order | Text or null |
| po_line | Text or null |
| quantity | Positive integer |
| commit_date | ISO date in YYYY-MM-DD format |

The optional previous order also provides a 64-character lowercase hexadecimal revision SHA-256, a positive row version, a timestamp with a UTC offset or null, and reviewer and reason fields that may be null. The report carries the saved reviewer and reason into its output when the void applies.

For an exact match with a prior void, the CLI prints eligible set to true with the carryover metadata. Change the candidate source row from 4 to 5 to see eligible set to false and an empty carryover object. Missing or active prior orders also produce a false result. Either valid result exits 0. Invalid or unreadable input exits 2.

The CLI reads the saved JSON and writes the report to standard output. It leaves the input unchanged.

Qualification used Windows and Ubuntu x64, Python 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.
