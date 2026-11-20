# Using the workbook snapshot manifest validator

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/workbook-snapshot-manifest-validator-v0.1.0). Compare the ZIP hash before extracting. On Windows use Get-FileHash -Algorithm SHA256 with the ZIP path. On Ubuntu use sha256sum -c SHA256SUMS.txt.

From the extracted directory, use Python 3.12.16 or 3.15.2 with the pinned openpyxl runtime.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe -B examples/make_snapshots.py demo-snapshots
.\.venv\Scripts\python.exe -B snapshot_manifest.py demo-snapshots/manifest.json
~~~

~~~bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python -B examples/make_snapshots.py demo-snapshots
.venv/bin/python -B snapshot_manifest.py demo-snapshots/manifest.json
~~~

The generator creates a new directory containing fictional inventory and scrap workbooks and their manifest. The report verifies three inventory rows and five scrap rows. Edit the inventory row count in the manifest to see the row-count gate reject a workbook whose checksum still matches. The validator prints a report only when every source passes and returns exit code 2 on failure.

Declare 1 to 16 sources with workbook paths relative to the manifest. The validator checks SHA-256 before inspecting workbook contents. It measures the saved worksheet dimensions and counts nonblank data rows and formula cells after the matching header in the declared column band. It looks for the header in the first 20 rows. External-link counts are counts of saved external-link XML parts. Inventory row counts refer to this tabular worksheet view.

The tool accepts ordinary XLSX files up to 25 MiB with declared worksheet dimensions up to 20,000 rows and 128 columns. It uses the bundled preflight guards and keeps links disabled while loading worksheets. Reports contain counts and snapshot identifiers. Formula evaluation, external link access, and workbook changes are outside this workflow.
