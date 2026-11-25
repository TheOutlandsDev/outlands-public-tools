# Offline Lot Timing and Shipment Risk Calculator

Extract the source ZIP and open a terminal in the extracted directory. Use Python 3.12 or 3.15. The runtime requirements pin Pydantic 2.14.3 and its dependencies by package hash.

## Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe lot_timing_risk.py examples/timing-request.json
```

## Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python lot_timing_risk.py examples/timing-request.json
```

The fictional example has two orders and four saved allocations. Lot `DEMO-K6-A` has two days remaining and seven days until its due date, for five days of positive schedule slack. The first order's risk follows its highest-priority lot, `DEMO-K2-A`. A lower `priority_sort` takes precedence, with lot ID breaking ties.

Use the example as an input template. Supply the fixed `planning_date`, days remaining for K1 through K7, priority thresholds, and orders with due dates and already-assigned lots. Dates use YYYY-MM-DD. Orders are sorted by due date, sequence, then order ID. The report preserves the supplied lot order within each order.

`legacy_days_remaining` is the configured Kanban value or a matching timing override. An override needs an `exception_id`, `days_remaining_override`, and at least one selector, `operation` or `lot_prefix`. If both selectors are present, both must match. Overlapping overrides cause the request to fail. Schedule slack (`schedule_delta`) is days until due minus days remaining.

The priority calculation considers overdue shipments, severe risk, the earliest non-overdue shipment, moderate risk, and subsequent shipments within the configured horizon. The report labels an order with no lots as `No allocated WIP`. The CLI takes an input file up to 1 MiB and prints JSON to standard output. Invalid input exits with code 2 and sends a diagnostic to standard error.

Compare the ZIP against `SHA256SUMS.txt` with `Get-FileHash -Algorithm SHA256` on Windows or `sha256sum` on Ubuntu. See `VALIDATION.json` for the four qualification profiles.
