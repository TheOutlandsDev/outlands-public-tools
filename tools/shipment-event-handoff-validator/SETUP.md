# Verify saved shipment and handoff records

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_records.py demo.json
& $py shipment_events.py demo.json
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_records.py demo.json
.venv/bin/python shipment_events.py demo.json
~~~

The generator requires a new file and writes four fictional records. The validator prints one JSON report only after every record passes. Failure exits with status 2 and prints a diagnostic to stderr. It leaves the input file unchanged.

## Saved record formats

Use the demo JSON as a template. The root contains a records array with one to 500 entries. The file limit is 1 MiB.

- **dock-event** supplies a revision hash, order row ID, positive order row version, and expected event ID.
- **handoff-event** supplies a revision hash, order row ID, lot ID, quantity, action, positive state version, and expected event ID. Supported actions are READY_FOR_LOGISTICS and RETURN_TO_FLEX.
- **ready-record** supplies a revision hash, expected order version, and one to 20 distinct lots with positive quantities. A comment is optional.
- **return-record** supplies a revision hash, expected order version, and one to 20 distinct lots with their expected state versions. A return reason is required.

The event checks use the original canonical SHA-256 calculations over the event fields. Reordering JSON keys leaves the computed ID unchanged. Changing a bound field requires a different event ID. The report shows verified IDs and record counts. Use event IDs from a trusted record source.

For the three adapted tests, install the hash-pinned test requirements into the same environment and run python -m pytest -q in the extracted directory. The release records include six copied-runtime CLI checks across all four Windows and Ubuntu profiles.
