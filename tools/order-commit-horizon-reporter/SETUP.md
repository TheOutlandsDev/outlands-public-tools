# Offline Order Commit Horizon Reporter

Classify a saved order snapshot against a fixed report date and show the visible orders and full open demand by product.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt, then extract the ZIP. Use Python 3.12.16 or 3.15.2. From the extracted directory on Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B order_commit_horizon.py examples/orders.json --as-of 2025-01-01 --horizon-days 30
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B order_commit_horizon.py examples/orders.json --as-of 2025-01-01 --horizon-days 30
~~~

The requirements pin Pydantic 2.14.3 and the runtime wheels qualified on Windows and Ubuntu x64.

## Input and output

Supply customer_orders and panel_orders arrays. Each row needs source_row, part_number, quantity, and flex_ptl_commit_date. Set ship_quantity and dock_date to null or omit them if unavailable. An open order has positive quantity, no reported ship quantity, and no dock date. A reported ship quantity of zero is treated as a recorded value. Supply an optional part_to_modality object for product labels. The tool uses Unmapped for missing labels.

Dates before the report date are Late. Days 0 through 7 are High, days 8 through 30 are Watch, and later orders are On track. The horizon defaults to 90 days, includes its endpoint, and keeps overdue rows. Optional product and risk filters narrow the display. Results sort by commit date, part number, and source row, with a 250-row display limit. Open-demand totals include all open rows before display filters and truncation.

The CLI prints JSON with the order fields used for this report and reads the snapshot without changing it. An invalid request exits with status 2 and empty standard output.
