# Run the Offline Last-Lot Workbook Extractor

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\last-lot-workbook-extractor-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. Install the pinned requirements in a virtual environment and generate the fictional workbook.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe examples/make_workbook.py fictional.xlsx
.\.venv\Scripts\python.exe last_lot_workbook.py fictional.xlsx
```

Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_workbook.py fictional.xlsx
.venv/bin/python last_lot_workbook.py fictional.xlsx
```

## Workbook format

The workbook has one worksheet, named LastLotStarted by default. Use --sheet followed by the exact worksheet name to select a different title. The header occupies A2:F2. Data occupies rows 3 through 23.

| A | B | C | D | E | F |
| --- | --- | --- | --- | --- | --- |
| Product Group | Material Template | Prefix | Last Lot Started | Blank | Next Lot To Start |

The extractor trims and collapses whitespace before checking the header and converting values. It preserves case and row order. The table must yield 21 rows with distinct prefixes, distinct last-lot values, and distinct next-lot values. Blank product and material template cells become JSON null. For reconciliation, supply lot IDs that follow your sequence rules.

The CLI reads cached cell values and prints an object with one top-level key, last_lots. It leaves the workbook intact. A successful extraction exits 0. An invalid workbook or table exits 2 and prints a diagnostic.

## Pass the output to the reconciler

The fictional queue in examples/fictional-queue.json matches the first workbook row. Merge the extractor's last_lots object with that queue. For example, run the following code from the extracted folder with the same virtual environment.

```python
import json
from pathlib import Path
import subprocess
import sys

queue = json.loads(Path("examples/fictional-queue.json").read_bytes())
mapped = subprocess.check_output(
    [sys.executable, "last_lot_workbook.py", "fictional.xlsx"]
)
with Path("reconciliation.json").open("x", encoding="utf-8") as output:
    json.dump(queue | json.loads(mapped), output, indent=2)
```

Run lot_identity.py from the reconciler's release with --input pointing to reconciliation.json. The fictional example produces 21 rows. The first proposes DEMO-01-AABA and DEMO-01-AABB, and the other 20 are reference-only. [Lot-Start Identity Reconciler v0.1.0](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/lot-start-identity-reconciler-v0.1.0)

Qualification used Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2, openpyxl 3.1.5 and Pydantic 2.14.3. The qualification script accepts --reconciler pointing to lot_identity.py from that release and verifies its SHA-256 before use.
