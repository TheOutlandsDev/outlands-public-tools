# Use the Offline WIP Supply Normalizer

## Verify and extract

Download the source ZIP and `SHA256SUMS.txt` from the [GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/wip-supply-normalizer-v0.1.0).
Compare the ZIP digest with its checksum before extracting into a fresh
directory.

PowerShell

```powershell
Get-FileHash .\wip-supply-normalizer-0.1.0.zip -Algorithm SHA256
Expand-Archive .\wip-supply-normalizer-0.1.0.zip .\wip-demo
Set-Location .\wip-demo\wip-supply-normalizer-0.1.0
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B wip_supply.py --input examples/normalization.json
```

Ubuntu shell

```sh
sha256sum wip-supply-normalizer-0.1.0.zip
unzip wip-supply-normalizer-0.1.0.zip -d wip-demo
cd wip-demo/wip-supply-normalizer-0.1.0
python3 -m venv .venv
./.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
./.venv/bin/python -I -B wip_supply.py --input examples/normalization.json
```

Use Python 3.12 or 3.15. The locks pin Pydantic 2.14.3 and the wheels used in
qualification.

## Read the sample results

The selected step applies a 25% loss to a quantity of 10. The exact half-tie
of 2.5 rounds up to 3, leaving 7 in process. The unlisted step keeps all 4 units.
The blank quantity contributes zero. The report totals 14 raw WIP, 11 normalized
WIP, 3 units of loss, and 7 completed parts.

The report gives `normalized` and exits with status 0. Try `examples/invalid.json`
with the same command. Its duplicate source row produces a diagnostic on stderr
and exit status 2.

## Supply your own saved rows

Use a UTF-8 JSON file up to 1 MiB with `configuration` and `records` at the
top level. The configuration has two fields.

| Field | Accepted value |
| --- | --- |
| `early_stage_steps` | One to 100 distinct, trimmed step names |
| `early_stage_loss_rate` | Decimal string or JSON number strictly between zero and one |

Each record supplies `source_row` (5 through 10,000), `material_name` (the lot),
`step_name`, and `product_name`. Use nonnegative integers, `null`, or omitted
fields for `wip_quantity`, `packaging_quantity`, `qa_far_quantity`, and
`pack_and_ship_quantity`. Null or omitted quantities contribute zero.
Source rows and lot identities must be unique.

Step names match exactly. The report preserves input row order and gives the
prepared rows, the totals, `row_set_sha256`, and `configuration_sha256`.
Repeating the same input produces the same result.

## Verify the extracted source

Use the same virtual-environment Python executable shown above for these commands.

```text
python -I -B source_check.py
python -m pip install --only-binary=:all: --require-hashes -r requirements-test.txt
python -B -m pytest -q
```

See `VALIDATION.json` for the Windows and Ubuntu fresh-extraction results.
