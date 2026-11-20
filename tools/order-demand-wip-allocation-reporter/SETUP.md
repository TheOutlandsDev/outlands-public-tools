# Using the allocation reporter

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/order-demand-wip-allocation-reporter-v0.1.0). Compare the ZIP hash with the published value before extracting.

~~~powershell
Get-FileHash -Algorithm SHA256 .\order-demand-wip-allocation-reporter-0.1.0.zip
~~~

~~~bash
sha256sum -c SHA256SUMS.txt
~~~

From the extracted folder, use Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe -B order_needs.py examples/snapshot.json
.\.venv\Scripts\python.exe -B order_needs.py examples/snapshot.json --format csv --part-number DEMO-01 --date-from 2030-09-11
~~~

~~~bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python -B order_needs.py examples/snapshot.json
.venv/bin/python -B order_needs.py examples/snapshot.json --format csv --part-number DEMO-01 --date-from 2030-09-11
~~~

The JSON report shows 550 units of remaining demand. Eligible WIP covers 300 units on the earliest due date and 60 on the later date. The later row retains that coverage in the filtered CSV, which includes both supplied source hashes. In filtered JSON, totals and product summaries still describe the full snapshot.

The input combines revision metadata, saved orders and the saved lot-start queue. Use the fictional input as a schema reference. All queue rows must reference the same WIP snapshot. Compare the supplied hashes against your own source files when establishing provenance. An invalid input or inconsistent queue returns exit code 2 before a report is emitted. The file must be ordinary UTF-8 JSON up to 1 MiB with at most 1,000 orders and 20 queue rows. Results go to stdout.
