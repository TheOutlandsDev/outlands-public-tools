# Using the production priority reporter

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/production-follow-up-priority-reporter-v0.1.0). Compare the ZIP hash before extracting. On Windows use Get-FileHash -Algorithm SHA256 with the ZIP path. On Ubuntu use sha256sum -c SHA256SUMS.txt.

From the extracted folder, run with Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $python -B order_needs.py examples/allocation-input.json | Set-Content -Encoding utf8NoBOM allocation.json
& $python -B shipment_readiness.py examples/readiness-input.json | Set-Content -Encoding utf8NoBOM readiness.json
& $python -B flex_priorities.py operator allocation.json --as-of 2030-09-01
& $python -B flex_priorities.py program-lead readiness.json --as-of 2030-09-01 --limit 1
~~~

~~~bash
python -m venv .venv
python=.venv/bin/python
"$python" -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
"$python" -B order_needs.py examples/allocation-input.json > allocation.json
"$python" -B shipment_readiness.py examples/readiness-input.json > readiness.json
"$python" -B flex_priorities.py operator allocation.json --as-of 2030-09-01
"$python" -B flex_priorities.py program-lead readiness.json --as-of 2030-09-01 --limit 1
~~~

The Windows commands use PowerShell 7 for UTF-8 output without a byte-order mark. Each input must be ordinary UTF-8 JSON up to 1 MiB. Give operator mode an unfiltered allocation report so it can find due-date rows. Use --panel-lots examples/panel-lots.json with program-lead mode to include the optional transfer group.

The operator example has two actions. The program lead example has three actions and shows only the top row when limited to one. The limit may be 1 through 25 and defaults to 8. Without --as-of, the report uses the date of the saved report's timestamp. Bad inputs return exit code 2. Workspace references in the JSON are identifiers from the original application.
