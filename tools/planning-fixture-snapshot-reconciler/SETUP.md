# Run the Offline Planning Fixture Snapshot Reconciler

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\planning-fixture-snapshot-reconciler-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal inside it with Python 3.12 or 3.15. The CLI uses the standard library.

```text
python planning_fixture_snapshot.py examples/approved-fixture.json examples/empty-snapshot.json
```

Use python3 on Ubuntu if that selects the intended interpreter. The example prints an empty result with seven expected rows and zero stored rows. To see a matching result, run the same command with examples/approved-fixture.json as both inputs.

Use separately approved expected rows and the rows exported from the snapshot you want to check. Each UTF-8 JSON file must contain the three table keys shown in the example. Use an empty array for a table with zero rows. The case table is keyed by case_id, orders by case_id and order_id, and WIP by case_id and lot_id. Identity fields are nonempty text. Other fields use scalar values. Represent dates as strings in JSON. The Python API also decodes UTF-8 byte values before comparison.

An entirely empty snapshot reports expected counts. A populated snapshot must match all three tables exactly, including field values and types. Row order and field order do not affect comparison. The CLI prints only status and counts. It leaves both files unchanged and performs no database operations. Exit status is 0 for an empty or matching snapshot and 2 for a mismatch or invalid input.

The validation records cover Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2.
