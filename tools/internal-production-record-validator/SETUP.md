# Validate saved internal production records

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the source ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_records.py demo
& $py production_records.py demo/records.json --products demo/products.json
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_records.py demo
.venv/bin/python production_records.py demo/records.json --products demo/products.json
~~~

The generator requires a new directory. The demo checks six fictional records against five fictional products. The report includes the computed completion event ID, the verified stored demand event ID, and the bulk transfer lot count.

## Validate your own saved batch

Use the demo files as format examples. Supply a product map from a separate trusted source. Each product declares its canonical and display modalities, assembly, and lot prefix. Ambiguous aliases, assemblies, and overlapping prefixes are rejected.

- **demand-create** and **demand-revision** check the saved demand command fields. New demand must resolve to an approved product.
- **completion** checks the evidence modality, assembly, and lot prefix against the product map. It also requires the evidence checksum and command checksum to match.
- **transfer** checks the saved transfer command. **bulk-transfer** also requires distinct lots with approved prefixes. Both reject fields claiming consumption.
- **event-identity** verifies the saved event ID from its event type, normalized target ID, and revision.

The validator reads saved records and leaves the files unchanged. A failed record prevents any JSON report. The process exits with status 2 and writes a diagnostic to stderr. The output summarizes the evidence and command fields checked by this tool.

For the five adapted original tests, install the hash-pinned test requirements and run python -m pytest -q in the extracted directory. The release records include six packaged CLI checks on all four Windows and Ubuntu profiles.
