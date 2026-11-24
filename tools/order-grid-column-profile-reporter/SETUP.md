# Run the Offline Order Grid Column Profile Reporter

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\order-grid-column-profile-reporter-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. Install the pinned runtime in a virtual environment.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe order_grid_profile.py --view notes
```

Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python order_grid_profile.py --view notes
```

The command prints JSON with selected_view and an ordered visible_columns array. It defaults to all.

| View | Columns | Groups |
| --- | ---: | --- |
| all | 34 | Every group |
| orders | 11 | Identity and order details |
| shipping | 28 | Identity, order details, shipping, and handoff |
| notes | 9 | Identity, notes, and controls, plus the pinned part number |

Status, source and part number are pinned in every view. Each entry includes key, label, group, data_type, source_column, editable, calculated, and pinned. A null source_column marks metadata with no direct worksheet column. The source identity uses the sheet and row together. Public field names include purchase_order, requested_ship_date, commit_date and planning_notes.

To display a saved row from the Order Snapshot Filter and Paginator, iterate visible_columns in order and look up each key in the row. Show a blank for fields absent from that snapshot. Use the flags to render headers or identify calculated values. The command reports column metadata and exits 0. An unsupported view exits 2.

Qualification used Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2 and pinned Pydantic 2.14.3.
