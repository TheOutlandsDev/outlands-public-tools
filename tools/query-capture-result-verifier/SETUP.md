# Use Offline Query Capture Result Verifier

Download the source ZIP and checksum manifest from the [GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/query-capture-result-verifier-v0.1.0). Compare the SHA-256 before extracting. On Windows, use PowerShell.

```powershell
Get-FileHash .\query-capture-result-verifier-0.1.0.zip -Algorithm SHA256
Expand-Archive .\query-capture-result-verifier-0.1.0.zip .\capture-demo
Set-Location .\capture-demo\query-capture-result-verifier-0.1.0
python -B query_capture_result_verifier.py --contract examples/contract.json --manifest examples/manifest.json
```

On Ubuntu, use a shell.

```sh
sha256sum -c SHA256SUMS.txt
unzip query-capture-result-verifier-0.1.0.zip
cd query-capture-result-verifier-0.1.0
python3 -B query_capture_result_verifier.py --contract examples/contract.json --manifest examples/manifest.json
```

The fictional example reports `matched` for two rows with nine matching fields. `parity_status` remains `not_established` because the summary applies to a single comparison case.

## Input and results

- Supply a separate contract with `report`, `start`, `end`, `expected_columns` and `ordered`. Set the report label and expected column count from your reviewed report definition. Use timezone-free timestamps in `YYYY-MM-DDTHH:MM:SS` format starting in 1753 or later and a positive window of at most 24 hours.
- The manifest must report `compared_not_validated` and contain the same `StartDate` and `EndDate`. The `comparison` object supplies its reported `status`, column and row counts, value and SQL metadata flags, and ordering evidence. See the fictional manifest for the field names.
- For an ordered contract, both `order_check_applicable` and `ordered_group_keys_match` must be true. For unordered comparisons, the former is false and the latter is explicit null. The maximum matching row count is 10,000.
- The result is `matched` for a consistent nonempty match, `empty_not_validated` when both verified counts are zero, `mismatch` for inconsistent evidence, or `failed` for a capture failure or window mismatch. Failure summaries include approved category, SQLSTATE, and evidence labels when available.
- Use JSON files up to 1 MiB each, encoded as UTF-8 with an optional BOM. The CLI reads both files and prints the summary to stdout. It returns 0 for a completed summary and 2 for an invalid input file or contract. It uses the Python standard library and works on results saved by an earlier capture.

The release validation records cover both original summary tests with fictional manifests and seven CLI check groups against the extracted ZIP on Windows and Ubuntu with Python 3.12.16 and 3.15.2.
