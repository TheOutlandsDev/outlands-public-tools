# Run the Offline XLSX Header and Row Extractor

Download the source ZIP and SHA256SUMS.txt. Check the ZIP's SHA-256 before extracting it.

```powershell
Get-FileHash .\xlsx-header-row-extractor-0.1.0.zip -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

On Ubuntu, run:

```bash
sha256sum -c SHA256SUMS.txt
```

Open a terminal in the extracted folder. With Python 3.12 or 3.15 on Windows PowerShell, run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe examples/make_workbook.py fictional.xlsx
.\.venv\Scripts\python.exe xlsx_header_rows.py fictional.xlsx --sheet Inventory --header-start-column 2 --header Item --header Count --header Received
```

On Ubuntu, run:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_workbook.py fictional.xlsx
.venv/bin/python xlsx_header_rows.py fictional.xlsx --sheet Inventory --header-start-column 2 --header Item --header Count --header Received
```

The fictional workbook omits cached dimensions. The reader finds its header at row 20 and reports data from rows 21, 23, and 24. Row 22 contains only whitespace. Each output row has a one-based source_row and a values array. Dates and times are ISO strings. Formula cells use values cached in the workbook, so the uncached formula in row 24 appears as null.

The sheet name and headers are supplied explicitly. The reported span starts at the one-based header column and matches the number of headers. Header text matches exactly after worksheet whitespace is normalized. The CLI reads the workbook with external-link loading disabled. It exits with status 0 on success and 2 when the input or header is invalid.

The release validation records cover Windows and Ubuntu with Python 3.12.16 and 3.15.2 and hash-pinned openpyxl 3.1.5.
