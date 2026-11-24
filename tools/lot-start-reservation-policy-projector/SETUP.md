# Run the Offline Lot-Start Reservation Policy Projector

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\lot-start-reservation-policy-projector-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. Install the hash-pinned runtime in a virtual environment.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe reservation_policy.py examples/candidate-policy.json
```

Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python reservation_policy.py examples/candidate-policy.json
```

## Input and output

Use the fictional candidate as a template. Save it as UTF-8 JSON up to 1 MiB. The public schema accepts policy_id, technical_owner, calculation_rules, event_and_identity_rules, configured_products, and fail_closed_products.

- The active recommendation factor is the string "1.00". The legacy comparison factor is "1.10" with status COMPARISON_ONLY_NOT_EXECUTABLE.
- Configured products supply modality, part_number, lot_prefix, lot_size, and recommendation_status. Use CONFIGURED for the status and a positive lot size of at most 10,000.
- Blocked products supply modality, part_number, a nullable lot_prefix, and reason. Product identifiers remain unique across both lists.
- Supply the required identity-source names in order. Verification lots stay linked to their standard base and leave the standard sequence unchanged.

The CLI prints the projected policy as JSON. Each configured product receives a start_factor of "1.00". The output keeps the CANDIDATE_SHADOW_ONLY status with production authority, production inclusion, and development cutover authorization set to false. The input file stays intact. Exit code 0 means a valid projection. Exit code 2 means the input was invalid.

## Fictional calculator check

The example contains 12 configured products. For GROUP01, the existing offline calculator receives 300 units of uncovered demand, a 300-unit lot size, and DEMO-01-AAAA as observed history.

| Policy | Factor | Demand after factor | Lots |
| --- | --- | ---: | ---: |
| Projected candidate | 1.00 | 300 | 1 |
| Legacy comparison example | 1.10 | 330 | 2 |

The qualification passes the actual JSON output to a hash-verified copy of the repository's existing lot-start calculator. The test copy is included under tests. [Reference calculator source](https://github.com/TheOutlandsDev/outlands-public-tools/blob/a788d6fdc46aa264ea8a09723c112377f8441820/tools/planner-handoff-checker/planner_contract/engines/identity.py)

Qualification used Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2 and pinned Pydantic 2.14.3.
