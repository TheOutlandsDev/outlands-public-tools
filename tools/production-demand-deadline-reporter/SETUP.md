# Using the production demand deadline reporter

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/production-demand-deadline-reporter-v0.1.0). Compare the ZIP hash before extracting. On Windows use Get-FileHash -Algorithm SHA256 with the ZIP path. On Ubuntu use sha256sum -c SHA256SUMS.txt.

From the extracted folder, run with Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $python -B order_needs.py examples/allocation-input.json | Set-Content -Encoding utf8NoBOM allocation.json
& $python -B demand_deadlines.py allocation.json --as-of 2030-09-05
~~~

~~~bash
python -m venv .venv
python=.venv/bin/python
"$python" -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
"$python" -B order_needs.py examples/allocation-input.json > allocation.json
"$python" -B demand_deadlines.py allocation.json --as-of 2030-09-05
~~~

The Windows example uses PowerShell 7 to save UTF-8 without a byte-order mark. The fictional snapshot has 550 units of remaining production demand. The report identifies 300 overdue units and 200 units due within seven days.

Dates before the report date are overdue. The upcoming window includes the report date and day seven. Without --as-of, the tool uses the date from the saved allocation timestamp. The report sums the rows present in the supplied JSON. Give it an unfiltered allocation report for full-snapshot totals. An empty row list produces zero counts. The CLI reads one ordinary UTF-8 JSON file up to 1 MiB, prints the report to stdout, and returns exit code 2 for invalid input.
