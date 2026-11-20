# Verify a saved transfer baseline

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_transfers.py demo
& $py transfer_baseline.py demo/baseline.json --assemblies demo/approved-assemblies.json --include-event-ids
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_transfers.py demo
.venv/bin/python transfer_baseline.py demo/baseline.json --assemblies demo/approved-assemblies.json --include-event-ids
~~~

The generator requires a new directory. The demo checks 29 fictional transfer rows totaling 1,305 units across five fictional assemblies.

## Verify your own baseline

Use the demo files as format examples. Supply a baseline from a trusted source and a separately approved list of seven-digit assembly identifiers. The baseline must state its record and quantity totals, declared date window, and canonical source checksum. Records must be closed, numbered consecutively from one, and include timestamps with explicit offsets. The declared date window is inclusive and uses each transfer's local date.

The source checksum hashes the canonical JSON array of validated records with sorted object keys, compact separators, UTF-8 encoding, and timestamps serialized by Pydantic. It preserves the record order. Each event ID hashes the original transfer event type, source checksum, and source row number. The summary reports the earliest and latest observed event by timestamp and totals by assembly. Omit --include-event-ids for the summary alone.

The input files are unchanged. Validation failure returns status 2 with a diagnostic on stderr and no JSON report. The verifier rejects declarations that authorize database ingestion or claim that the transfer proves consumption.

For the nine adapted original tests, install the hash-pinned test requirements and run python -m pytest -q from the extracted directory. The release records include six packaged CLI checks on all four Windows and Ubuntu profiles.
