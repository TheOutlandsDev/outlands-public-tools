# Run the Offline Planning Fixture Replay Verifier

Download the source ZIP and SHA256SUMS.txt. On Windows, run Get-FileHash .\planning-fixture-replay-verifier-0.1.0.zip -Algorithm SHA256 in PowerShell and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal inside it with Python 3.12 or 3.15. Create a virtual environment and install the hash-pinned runtime requirements.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe planning_fixture_replay.py examples/fictional-fixture.json examples/fictional-configuration.json
```

Ubuntu:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python planning_fixture_replay.py examples/fictional-fixture.json examples/fictional-configuration.json
```

The fictional replay matches 160 units of demand against 135 available WIP units. The second order has 25 uncovered units. The configured 1.10 factor rounds that quantity to 28 recommended starts.

Use the examples as the JSON formats. Set the fixture status to APPROVED_MANUAL_GATE_1 only for a fixture whose expected result you have approved. Supply a separate DECLARED_PLAN_ONLY configuration in the public engine's format. The comparison covers ordered lot identifiers, timing and priority, per-order covered and uncovered quantities, recommended starts, and totals. JSON object member order has no effect. Changes to ordered arrays, values, or value types fail the comparison.

The bundled allocation_engine.py is a byte-for-byte copy of the published Planner Handoff Checker allocation engine. It uses caller-declared available WIP and the public configuration schema. The verifier treats the fixture approval field and configuration provenance as caller declarations. It reads both files and prints a report only on a match. Exit status 0 means match and 2 means invalid, unapproved, or mismatched input.

The validation records cover Windows and Ubuntu x64, Python 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.
