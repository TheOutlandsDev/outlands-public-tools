# Verify saved order identity aliases

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the source ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_orders.py demo.json
& $py order_alias.py demo.json --include-aliases
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_orders.py demo.json
.venv/bin/python order_alias.py demo.json --include-aliases
~~~

The generator requires a new file. The sample contains two versions of one fictional order and one version of a second order. The verifier reports three distinct mappings.

## Verify your own records

Use the demo JSON as the format example. The namespaces object sets legacy_contract_version and candidate_policy_revision. Supply the original legacy contract version and stored event fingerprints from trusted records. Each record contains the stored legacy_event_fingerprint and its canonical order. The limit is 1,000 records in a 2 MiB file.

The legacy identity includes the contract version. The candidate identity includes the candidate policy revision. The semantic identity hashes the canonical order fields alone. Changing the candidate policy revision changes only the candidate identity. Identical records in the same batch are rejected as duplicate aliases, and two different canonical states cannot share one order ID and row version.

The CLI writes a summary to stdout. Add --include-aliases to include order IDs, row versions, and verified fingerprints. The input is unchanged. A failed validation exits with status 2, writes a diagnostic to stderr, and produces no report.

For the nine adapted tests, install the hash-pinned test requirements and run python -m pytest -q in the extracted source directory. The release records include six copied-runtime CLI checks across all four Windows and Ubuntu profiles.
