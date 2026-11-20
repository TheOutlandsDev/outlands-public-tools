# Using the coverage checker

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/multi-product-planning-coverage-checker-v0.1.0). Compare the ZIP hash with the published value before extracting.

~~~powershell
Get-FileHash -Algorithm SHA256 .\multi-product-planning-coverage-checker-0.1.0.zip
~~~

~~~bash
sha256sum -c SHA256SUMS.txt
~~~

From the extracted folder, use Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe -B multi_product_preflight.py examples/coverage.json
~~~

~~~bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python -B multi_product_preflight.py examples/coverage.json
~~~

The fictional example returns exit code 1 and a report with seven open orders totaling 127, two mapped products missing planning configuration, and one rejected WIP row. A supplied ship quantity, including zero, or a dock date excludes an order from open-demand totals. Remove DEMO-05 from the part mapping to see it reported as unsupported. Both reports have zero plans.

A complete report returns code 0. Invalid or unreadable JSON returns 2. The CLI reads one ordinary UTF-8 JSON file up to 1 MiB, rejects duplicate JSON keys, and prints the report to stdout. Use the fictional example as the schema reference. The stable digest covers the report fields and issue list. It does not certify the routing rules or the source records.
