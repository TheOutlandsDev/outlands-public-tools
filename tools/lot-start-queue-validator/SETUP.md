# Validate the fictional lot-start queue

Download the ZIP and `SHA256SUMS.txt` from the release page. Verify the ZIP
before extracting it. On Windows, compare the output of the following command
with the ZIP entry in the checksum file.

```powershell
Get-FileHash -Algorithm SHA256 .\lot-start-queue-validator-0.1.0.zip
```

On Ubuntu, run the following command from the download directory.

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. Use a CPython 3.12 or 3.15 executable
in place of `python`, if needed.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe
```

Ubuntu

```sh
python -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python
```

Paste the example into the Python prompt.

```python
import json
from pathlib import Path
from types import SimpleNamespace

from production_planning.automatic_lot_start_validation import (
    validate_and_summarize_automatic_queue,
)

fixture = Path("examples/demo_queue.json")
rows = json.loads(fixture.read_text(encoding="utf-8"))
summary = validate_and_summarize_automatic_queue(SimpleNamespace(**row) for row in rows)
print(summary.coverage_surplus, summary.uncovered_after_wip, summary.starts_required)
```

The example prints `465 170 1`. The first product has 465 units of surplus
work in progress. The second still has 170 uncovered units and requires one
lot. The validator calculates both values for each product before totaling them.

Pass trusted, typed planning rows with positive lot sizes and nonnegative
demand and work-in-progress quantities. The Python API checks the saved
recommendations and expects the rows to share one snapshot reference. The
reference is compared as an identifier. Verify snapshot contents in the
workflow that supplies the rows. Duplicate identifiers, mismatched snapshot
references, or inconsistent calculations raise
`AutomaticLotStartQueueValidationError`. The API returns a summary without
connecting to a database or starting lots.

To run the eight tests, install `requirements-test.txt` with the same pip
flags and run `python -B -m pytest -q -p no:cacheprovider tests` using the virtual
environment's interpreter. `WHEEL-LOCK.json` pins the dependency wheel
hashes, including Pydantic 2.14.3 and its native core. `VALIDATION.json`
records the four Windows and Ubuntu profiles, installed wheels, and the
original and fresh-extraction test results.
