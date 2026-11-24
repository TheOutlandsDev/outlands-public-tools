# Run the Offline New Order Request Validator

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\new-order-request-validator-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal inside it. Install the pinned requirements in a virtual environment.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe new_order_request.py examples/fictional-order.json
```

Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python new_order_request.py examples/fictional-order.json
```

Use the fictional request as a template. Supply source_sheet set to C or P, order_date and commit_date in YYYY-MM-DD form, a part_number of 1 through 40 characters, and a positive integer quantity. Optional fields include purchase_order, po_line, requested_ship_date, organization, ship_quantity, ship_date, dock_date, work_request_flow, customer_notes, and planning_notes.

The example omits lot_count and lot_allocations, so it reports zero lots. To include lots, specify a count from 1 through 20 and that many rows with a lot_id and circuits from 1 through 100,000. Lot IDs must be unique regardless of case. The allocated total must fit within the order quantity and match a positive ship quantity when supplied.

A valid request exits 0 and prints a JSON report with valid set to true and the lot count. Try changing quantity to 0 to see a rejection with exit status 2. Invalid or unreadable requests produce a short diagnostic without echoing the saved data.

The CLI reads local JSON and prints a report. It leaves the input unchanged and performs no order submission.

Qualification used Windows and Ubuntu x64, Python 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.
