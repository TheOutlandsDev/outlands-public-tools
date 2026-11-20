# Compare two saved lot-start recommendation queues

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the source ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_queues.py demo
& $py lot_queue.py demo/before.json demo/after.json
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_queues.py demo
.venv/bin/python lot_queue.py demo/before.json demo/after.json
~~~

The generator requires a new directory. The example changes the recommended lot count and start quantity for DEMO-A and the start-by date for DEMO-B.

## Read the results

Use the example JSON files as format references. Each snapshot contains a rows array of up to 1,000 records in a 2 MiB file. Modalities must be unique within a snapshot and both snapshots must cover the same modality set. Start-by dates use ISO format or null. The saved uncovered quantity must equal demand minus eligible WIP, floored at zero.

The recommendation section captures changes to the saved lot count or start quantity. The timing section captures start-by date changes. Totals are reported for each snapshot and calculate coverage and surplus for each modality before summing them. A surplus in one modality stays separate from a shortage in another.

The tool compares saved recommendations and leaves the inputs unchanged. It writes one JSON result to stdout. Invalid inputs produce an exit status of 2 and a diagnostic on stderr. The result schema checks that each reported change count equals the size of its change list.

For the three adapted direct tests and the original result-count check, install the hash-pinned test requirements and run python -m pytest -q in the extracted directory. The release records include six copied-runtime CLI checks across all four Windows and Ubuntu profiles.
