# Use the Offline Lot-Start Identity Reconciler

## Verify and extract

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/lot-start-identity-reconciler-v0.1.0).
Compare the ZIP digest with its checksum before extracting into a fresh
directory.

PowerShell

```powershell
Get-FileHash .\lot-start-identity-reconciler-0.1.0.zip -Algorithm SHA256
Expand-Archive .\lot-start-identity-reconciler-0.1.0.zip .\lot-identity-demo
Set-Location .\lot-identity-demo\lot-start-identity-reconciler-0.1.0
```

Ubuntu shell

```sh
sha256sum lot-start-identity-reconciler-0.1.0.zip
unzip lot-start-identity-reconciler-0.1.0.zip -d lot-identity-demo
cd lot-identity-demo/lot-start-identity-reconciler-0.1.0
```

## Set up the environment

Use Python 3.12 or 3.15. The commands below create a virtual environment and
install only matching wheels for the hash-locked runtime requirements.

PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
```

Ubuntu shell

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
```

The qualification records identify Pydantic 2.14.3 and the exact Python
interpreters and dependency wheels checked on each platform.

## Reconcile fictional lots

PowerShell

```powershell
.\.venv\Scripts\python.exe -I -B lot_identity.py --input examples/reconciliation.json
```

Ubuntu shell

```sh
./.venv/bin/python -I -B lot_identity.py --input examples/reconciliation.json
```

The tool returns `reconciled` with two rows. For prefix `DEMO-`, the last lot
`DEMO-AAAZ` rolls over to `DEMO-AABA`. The active recommendation proposes
`DEMO-AABA` and `DEMO-AABB`. The `REF-` mapping stays `REFERENCE_ONLY`,
with a recommendation count of zero. Try `examples/invalid.json` to see
the next-ID mismatch return exit status 2 and a diagnostic on stderr.

## Supply your own saved input

The input is a UTF-8 JSON file with no byte-order mark, at most 256 KiB.
Provide two arrays named `queue` and `last_lots`, each with up to 1,024 rows.

| Array | Row fields |
| --- | --- |
| `queue` | `modality`, `part_number`, `lot_prefix`, `recommended_lot_count`, `queue_status`, optional `recommended_start_by` in `YYYY-MM-DD` format or `null` |
| `last_lots` | `prefix`, `last_lot_started`, `next_lot_to_start`, `product`, `material_template`. The last two may be `null`. |

Use 3 to 20 uppercase letters, digits, or hyphens for a prefix. Standard lot
IDs end with four uppercase letters. Each queue count is an integer from 0
through 100, and queue status is `ACTIVE` or `CLEAR`. Keep prefixes unique
within each array. Product consistency is checked case-insensitively when a
mapping supplies a product.

The report preserves mapping order and gives proposed IDs for review. Inputs
are read only. Invalid input returns status 2 with a fixed diagnostic.

## Verify the extracted source

Run `python -I -B source_check.py` with the selected interpreter. For the test
suite, install the additional hash-locked requirements into the same virtual
environment and run pytest.

```text
python -m pip install --only-binary=:all: --require-hashes -r requirements-test.txt
python -B -m pytest -q
```

In the last commands, use the same virtual-environment Python executable shown
above. See `VALIDATION.json` for the four fresh-extraction results.
