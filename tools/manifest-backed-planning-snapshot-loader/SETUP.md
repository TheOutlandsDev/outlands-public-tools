# Load a manifest-backed development snapshot

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the ZIP against the release's SHA256SUMS.txt and extract it. Open a terminal in the extracted directory. The runtime lock pins openpyxl 3.1.5, Pydantic 2.14.3, and their dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_snapshot.py demo
& $py planning_snapshot.py demo demo/manifest.json
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_snapshot.py demo
.venv/bin/python planning_snapshot.py demo demo/manifest.json
~~~

The generator requires a new directory. The demo reports 118 customer orders, two panel orders, nine mappings, and 130 WIP records. The summary gives the SHA-256 digests of both workbooks. Output is JSON on stdout. The loader leaves the input files unchanged.

## Load your own snapshot

Use the generated manifest as the format example. Supply a trusted manifest that declares the development-only environment, excludes production, and accepts the source revision. The file hash pins identify the intended workbook bytes. The manifest gives the expected order counts and declares exactly one inventory source.

The orders workbook uses the C, P, and Mapping sheets used by the Order and Part Mapping Workbook Extractor. The inventory uses the FPC_Production_Inventory sheet with 26 repeated blocks. Its manifest entry gives the expected headers, worksheet dimensions, normalized WIP count, formula count, and external-link count. A normalized count excludes headers, total lines, and rows without the required lot, step, and product values. The loader reads cached cell values and keeps source row numbers on the typed records.

Workbook paths are relative to the supplied root. The optional --orders and --inventory arguments assert that the configured local workbook paths agree with the manifest. Validation errors return exit status 2, write a diagnostic to stderr, and produce no JSON.

To rerun the four tests, install the pinned test requirements into the same virtual environment and run python -m pytest -q in the extracted directory. The release validation records contain the full Windows and Ubuntu matrix, fresh offline installations from hash-verified wheels, and copied-runtime checks.
