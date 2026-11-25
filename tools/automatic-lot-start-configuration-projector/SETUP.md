# Run the Offline Automatic Lot-Start Configuration Projector

Download the source ZIP and `SHA256SUMS.txt`. In PowerShell use `Get-FileHash .\automatic-lot-start-configuration-projector-0.1.0.zip -Algorithm SHA256` and compare the digest with the checksum file. On Ubuntu run `sha256sum -c SHA256SUMS.txt`. Extract the ZIP and open a terminal there.

Qualification used Windows and Ubuntu x64, CPython 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.

## Run the fictional policy

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe automatic_lot_configuration.py examples/policy.json
```

Ubuntu

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python automatic_lot_configuration.py examples/policy.json
```

The output preserves the reviewed lot size as the calculator's start quantity, along with the modality, part number, prefix, lead time, and lot size status. It keeps unapproved products in the fail-closed list. The `1.00` replenishment factor and separate `0.20` early-WIP valuation rate carry over unchanged. The example projects two configured products and one unapproved product.

## Use the output in the replay reporter

Add `--format replay` to emit the three fields accepted by the [Offline Order Demand Lifecycle Replay Reporter](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/order-demand-lifecycle-replay-reporter). Save that stdout JSON as a rules file and pass it to the reporter with `examples/order-versions.json` from this package. The example produces one recommendation for a 36-unit lot. The default output includes additional configuration fields and is intended for inspecting the full projection.

## Input and limits

Use the shape in `examples/policy.json`. The demand authority is `SAVED_ORDER_SNAPSHOT`. Use fictional or approved identifiers and lot prefixes of the form `LOT` followed by two to eight uppercase letters or digits. The projector validates unique modalities, part numbers, and non-null prefixes across both product lists. It accepts up to 100 rows per list and requires at least one configured product.

The CLI reads one UTF-8 JSON file, limited to 1 MiB. It leaves the file unchanged, writes JSON to stdout and uses no network or database. Refused input returns exit code 2. Successful output includes supplied product details.
