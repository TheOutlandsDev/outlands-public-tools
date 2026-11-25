# Offline Fulfillment WIP Eligibility Reporter

Extract the source ZIP and open a terminal in the extracted directory. Use Python 3.12 or 3.15. The runtime requirements pin Pydantic 2.14.3 and its dependencies by package hash.

## Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe fulfillment_wip_eligibility.py examples/assigned-wip.json --overrides examples/overrides.json
```

## Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python fulfillment_wip_eligibility.py examples/assigned-wip.json --overrides examples/overrides.json
```

The fictional example reconciles 128 input parts into 80 eligible and 48 verification parts. Eligible totals are 65 for `DEMO-A` and 15 for `DEMO-B`. The override changes the destination of `DEMO-A` at `Stage 1` from K2 to K5.

Use saved JSON from the WIP-to-Kanban Assignment Checker or a compatible object with a `records` array. Each record supplies `lot_id`, `source_product`, `canonical_product`, `current_step`, `kanban`, and `total_parts`. Kanban is an integer from 1 through 6, and parts are nonnegative integers.

A lot goes into the verification group when the source product differs from the canonical product, the lot starts with `V`, or the source product ends in `V`, including `-V`. Prefix and suffix checks are case-insensitive. The source-to-canonical comparison is exact.

The optional overrides file holds `contextual_kanban_overrides`. Each rule declares `part_number`, `operation`, and `kanban`. Matching is exact, overrides apply to eligible lots, and each part and operation pair can appear once. Omit `--overrides` to keep the assigned Kanban values.

Input files are limited to 4 MiB each. The CLI reads the files and prints an eligibility report as JSON. Invalid inputs exit with code 2 and write a diagnostic to standard error.

Compare the ZIP against `SHA256SUMS.txt` with `Get-FileHash -Algorithm SHA256` on Windows or `sha256sum` on Ubuntu. See `VALIDATION.json` for all four qualification profiles.
