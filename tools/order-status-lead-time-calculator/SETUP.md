# Using the order status and lead-time calculator

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/order-status-lead-time-calculator-v0.1.0). Compare the ZIP hash before extracting. On Windows use Get-FileHash -Algorithm SHA256 with the ZIP path. On Ubuntu use sha256sum -c SHA256SUMS.txt.

From the extracted directory, use Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe -B order_status.py examples/orders.json
~~~

~~~bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python -B order_status.py examples/orders.json
~~~

The first fictional order reports Shipped even though it has a dock date. A carrier and tracking pair, a ship date, a supplied ship quantity including zero, or a nonblank shipment number counts as shipping evidence. The second order is Docked and resolves its alias to DEMO-02. Unknown lead-time parts and missing order dates yield null. Lead time is the order date plus the whole number of calendar weeks in the rule table.

Use uppercase keys without whitespace in the rule tables. Alias targets must exist in the lead-time table, and lead times must be between 1 and 52 weeks. Order part inputs are uppercased with whitespace removed before alias lookup. The CLI reads ordinary UTF-8 JSON up to 1 MiB with at most 1,000 orders, emits a report to stdout, and returns exit code 2 for invalid inputs.
