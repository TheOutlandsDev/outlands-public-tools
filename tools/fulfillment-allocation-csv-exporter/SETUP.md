# Export a saved fulfillment result to CSV

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the source ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_fulfillment.py demo.json
& $py fulfillment_csv.py demo.json --part-number DEMO-PART-A --status-color Blue
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_fulfillment.py demo.json
.venv/bin/python fulfillment_csv.py demo.json > fulfillment.csv
~~~

The generator requires a new file. The unfiltered demo has three CSV rows for two orders. The first order has two allocations totaling 20 units, and the second is kept with blank allocation fields. The Windows example selects only the first order. To save raw CSV bytes with PowerShell, use PowerShell 7.4 or later and redirect stdout to a fresh filename with >. [Microsoft PowerShell redirection guide](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_redirection#redirecting-output-from-native-commands)

## Saved input and provenance

Use the demo as a template. Supply a planning timestamp, a source map with bare filenames and SHA-256 digests, the saved orders with their allocations, and the conservation totals. Supply the source hashes from trusted records. The exporter fingerprints the sorted source hash declarations and carries that fingerprint into every row, including filtered exports.

Select an exact part number, a status color, or both. The exporter validates the full saved result before filtering. A filter that matches zero orders yields the CSV header. Invalid input returns status 2, writes a diagnostic to stderr, and produces no CSV.

CSV is emitted on stdout as UTF-8 with a BOM and CRLF line endings. Text beginning with a formula marker or a tab or line break is prefixed with an apostrophe. The formula check also catches markers after leading whitespace. The saved input is unchanged.

For the two adapted CSV tests, install the hash-pinned test requirements and run python -m pytest -q from the extracted directory. The release records include six packaged CLI checks on all four Windows and Ubuntu profiles.
