# Using the shipment readiness reporter

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/shipment-readiness-reporter-v0.1.0). Compare the ZIP hash with the published value before extracting.

~~~powershell
Get-FileHash -Algorithm SHA256 .\shipment-readiness-reporter-0.1.0.zip
~~~

~~~bash
sha256sum -c SHA256SUMS.txt
~~~

From the extracted folder, use Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe -B shipment_readiness.py examples/snapshot.json
.\.venv\Scripts\python.exe -B shipment_readiness.py examples/snapshot.json --search DEMO-LOT-A --readiness PARTIALLY_READY_FOR_LOGISTICS
~~~

~~~bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python -B shipment_readiness.py examples/snapshot.json
.venv/bin/python -B shipment_readiness.py examples/snapshot.json --search DEMO-LOT-A --readiness PARTIALLY_READY_FOR_LOGISTICS
~~~

The example includes an order with 180 units ready for logistics and 120 left in production, an order awaiting dock, a docked order with mismatched lot IDs and quantities, and a shipped order with an earlier dock date. To try a return, copy the example and set the first handoff state's lifecycle_state to RETURNED_TO_FLEX. The order's ready quantity falls to zero.

Use the example as a schema reference. The CLI refuses duplicate order identities, repeated handoff state for an order and lot, and handoff states from another source revision or an unknown order. Input must be ordinary UTF-8 JSON up to 1 MiB. Invalid snapshots return exit code 2. Successful reports retain up to 200 matching rows, and their totals reflect those rows. The generated timestamp records when the report ran.
