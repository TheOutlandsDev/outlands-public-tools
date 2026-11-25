# Offline Order Demand Lifecycle Replay Reporter

Extract the source ZIP and open a terminal in the extracted directory. Create a local environment with Python 3.12 or 3.15. On Windows, use its interpreter directly from PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe order_demand_replay.py examples/rules.json examples/versions.json
```

On Ubuntu, use the interpreter under `.venv/bin`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-runtime.txt
.venv/bin/python order_demand_replay.py examples/rules.json examples/versions.json
```

The pinned runtime includes Pydantic 2.14.3 and its dependencies. Dependency installation uses PyPI. The replay itself reads local files, performs the calculation in memory, and prints JSON to standard output.

The sample processes 10 records and emits eight events. One current-version duplicate is ignored and one revision updates order state without changing demand. The two initial 24-unit orders share one 48-unit lot recommendation. The example ends with zero remaining demand after its shipments and cancellation.

The rules file declares `contract_version`, `configured_products`, and `fail_closed_products`. Each configured product specifies a modality, part number, lot prefix, start quantity, lead time, and review status. Use the fictional rules as a template for your own approved quantities.

The second file is a JSON array in observation order. Each order version includes `order_id`, `row_version`, `source_revision_sha256`, `part_number`, `ordered_quantity`, `accepted_ship_quantity`, and `requested_ship_date` (`YYYY-MM-DD`). The optional `cancelled` flag defaults to false. The source revision digest is an input to the event fingerprint. The CLI takes that digest as a supplied label.

An identical record for the current version is ignored. Older versions, conflicting current versions, unapproved products, and shipped quantities above the ordered quantity cause exit code 2 with no JSON output. Input files are limited to 4 MiB each and the replay accepts up to 2,000 versions.

Compare the ZIP against `SHA256SUMS.txt` with `Get-FileHash -Algorithm SHA256` on Windows or `sha256sum` on Ubuntu. See `VALIDATION.json` for the four qualification profiles.
