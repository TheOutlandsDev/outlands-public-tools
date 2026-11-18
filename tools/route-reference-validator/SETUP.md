# Validate the fictional route dataset

Download the release ZIP and `SHA256SUMS.txt`. Compare the ZIP digest to the
checksum before extracting it.

Windows PowerShell

```powershell
Get-FileHash -Algorithm SHA256 .\route-reference-validator-0.1.0.zip
```

Ubuntu

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Extract the ZIP and open a terminal at the extracted root. Start a
CPython 3.12 or 3.15 prompt by running `python` (or the full path to your
chosen interpreter). Paste the example.

```python
from pathlib import Path
from production_planning.route_reference import (
    route_occurrence_key,
    validate_route_dataset,
)

data = Path("data/route_reference")
dataset = validate_route_dataset(data / "demo_routes.csv", data / "metadata.json")
print(len(dataset.rows))
repeats = [row for row in dataset.rows
           if row["RequestedFlowName"] == "Demo Circuit"
           and row["StepName"] == "Repeated_Check"]
print([row["StepPosition"] for row in repeats])
print(len({route_occurrence_key(row) for row in repeats}))
```

The three lines print `239`, `['15', '26', '28']` and `3`. Each occurrence
keeps its own order key and correlation ID even though all three share one
step ID.

Use a trusted metadata file with the revision 3 dataset. The 22 header names
and their order, the declared filename, the CSV hash, and the 239 rows must
match the contract. The workbook and query digests are declared provenance
fields. This example uses fictional values for both, and the API verifies
the bytes of the CSV. Validation failures such as a changed hash or duplicate
step position raise `RouteValidationError`. The release is designed for local
trusted inputs and needs no client, database connection or runtime packages.

To run the suite from the extracted root, create a fresh virtual environment
with `python -m venv .venv`. In the following commands, replace `python` with
`.\.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on Ubuntu.

```text
python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-test.txt
python -B -m pytest -q -p no:cacheprovider tests
```

`WHEEL-LOCK.json` lists the approved wheels for pytest and its dependencies.
`VALIDATION.json` records the test and extracted-API results for each
Windows and Ubuntu interpreter profile.
