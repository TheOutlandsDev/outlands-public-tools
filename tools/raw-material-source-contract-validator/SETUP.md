# Run the Offline Raw Material Source Contract Validator

Use Windows or Ubuntu x64 with Python 3.12.16 or 3.15.2. Download and extract the source ZIP. Compare its SHA-256 with the value in `SHA256SUMS.txt` using `Get-FileHash -Algorithm SHA256` in PowerShell or `sha256sum -c SHA256SUMS.txt` on Ubuntu.

Open a terminal in the extracted folder and create a virtual environment.

```text
python -m venv .venv
```

On Windows PowerShell, run:

```powershell
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe raw_material_contract.py examples/pending-source.json
```

On Ubuntu, run:

```bash
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python raw_material_contract.py examples/pending-source.json
```

The example prints `PASS: raw-material source contract is pending approval.` and exits with status 0. Try a copy with `ingestion_enabled` set to `true`. The validator prints a generic error to stderr and exits with status 2.

The input is a contract declaration. It records the fields expected from a future data source. The validator reads only that JSON file and does not contact the listed interfaces, connect to a database, or read actual inventory. The standalone example uses a fictional contract ID and no operational records.

The release validation record covers the original test with a fictional input, CLI behavior from the extracted ZIP, and exact Python and dependency versions across four runner profiles.
