# Run the Offline Order Snapshot Filter and Paginator

Download the source ZIP and SHA256SUMS.txt together. On Windows, run Get-FileHash .\order-snapshot-filter-paginator-0.1.0.zip -Algorithm SHA256 in PowerShell and compare the result with SHA256SUMS.txt. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. Use Python 3.12 or 3.15.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe order_snapshot_filter.py examples/fictional-orders.json --search watch --sheet P --page-size 10
```

Ubuntu:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python order_snapshot_filter.py examples/fictional-orders.json --search watch --sheet P --page-size 10
```

The example selects one of three fictional orders. Its JSON includes revision metadata, the total and matching row counts, the page count and the current page rows. The saved snapshot supplies the status, modality and other display values for each order. Use the example as the input format.

Use --modality for one or more modalities from the snapshot, --status for Open, Shipped or Docked, and --date-field with order_date, requested_ship_date, commit_date or ship_date. Supply --date-from and --date-to as YYYY-MM-DD. Date bounds are inclusive. Undated rows appear last in the default newest-first order. Same-date rows sort by part number, sheet and source row.

Pages start at 1 and page size must be between 10 and 200. A page beyond the last match is empty and still reports the full matching count. The CLI exits with 0 on success and 2 for invalid inputs or options. It processes saved inputs offline.

Qualification used Windows and Ubuntu x64, Python 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.
