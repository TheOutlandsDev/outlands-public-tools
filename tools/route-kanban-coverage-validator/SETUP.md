# Offline Route-to-Kanban Coverage Validator

Extract the source ZIP and open a terminal in the extracted directory. Use Python 3.12 or 3.15. The runtime requirements pin Pydantic 2.14.3 and its dependencies with package hashes.

## Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe route_kanban_coverage.py examples/flow-38.xml examples/product-38.json examples/assignment-rules.json
```

## Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python route_kanban_coverage.py examples/flow-40.xml examples/product-40.json examples/assignment-rules.json
```

Either example works on both platforms. Each pins the expected flow name, version, and SHA-256 in the product JSON. The 38-step fixture routes `Fictional Grading` to K2 and the 40-step fixture routes it to K4. Both preserve the repeated `Station 01` occurrence. The 40-step flow also checks two direct K5 operations.

Provide a UTF-8 CMF flow XML of at most 1,000,000 bytes, a product JSON, and an assignment-rules JSON. Each JSON input is limited to 1 MiB. Use the included JSON files as templates. The product's `operation_to_kanban` keys must match the flow's distinct operation names exactly. The rules document groups direct operations by Kanban 1 through 6 and lists any alternate operations alongside a destination per part number.

The CLI checks the raw XML hash before parsing and writes a JSON report to standard output. A failed check exits with code 2 and writes a diagnostic to standard error. Both success and failure leave the input files unchanged.

Check the downloaded ZIP against `SHA256SUMS.txt` with `Get-FileHash -Algorithm SHA256` on Windows or `sha256sum` on Ubuntu. See `VALIDATION.json` for the four qualification profiles.
