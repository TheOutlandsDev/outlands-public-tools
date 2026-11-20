# Using the assignment checker

Download the [source ZIP and SHA-256 file](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/wip-kanban-assignment-checker-v0.1.0). Compare the ZIP hash with the published value before extracting.

~~~powershell
Get-FileHash -Algorithm SHA256 .\wip-kanban-assignment-checker-0.1.0.zip
~~~

~~~bash
sha256sum -c SHA256SUMS.txt
~~~

From the extracted folder, run these commands with Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B kanban_assignment.py examples/assignment.json --preflight
.\.venv\Scripts\python.exe -I -B kanban_assignment.py examples/assignment.json
~~~

~~~bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python -I -B kanban_assignment.py examples/assignment.json --preflight
.venv/bin/python -I -B kanban_assignment.py examples/assignment.json
~~~

The example assigns one row to K1 by its operation and one to K5 by its source product rule. The total is 180 parts, made up of 160 normalized WIP and 20 completed parts. Preflight should report two assignable rows. Change the second row’s current step to an unknown value to see preflight diagnostics. Assignment returns exit code 1 and emits no assignment JSON for that input. An invalid file or schema returns 2.

Use the WIP Supply Normalizer output’s records array in the input JSON, alongside a configuration object. The configuration retains the original contract shape of 66 distinct direct operations, three distinct alternate operations, 24 unique start prefixes, and destinations K1 through K6. The input is limited to 8 MiB and 10,000 rows. The CLI reads a local file and prints results to stdout. The runtime has no service connections.
