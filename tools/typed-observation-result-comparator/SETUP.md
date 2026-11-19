# Use the Offline Typed Observation Result Comparator

## Verify and extract

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/typed-observation-result-comparator-v0.1.0).
Compare the ZIP digest with its checksum before extracting into a fresh
directory.

PowerShell

```powershell
Get-FileHash .\typed-observation-result-comparator-0.1.0.zip -Algorithm SHA256
Expand-Archive .\typed-observation-result-comparator-0.1.0.zip .\typed-observation-demo
Set-Location .\typed-observation-demo\typed-observation-result-comparator-0.1.0
```

Ubuntu shell

```sh
sha256sum typed-observation-result-comparator-0.1.0.zip
unzip typed-observation-result-comparator-0.1.0.zip -d typed-observation-demo
cd typed-observation-demo/typed-observation-result-comparator-0.1.0
```

## Compare the fictional rows

Run with Python 3.12 or 3.15. Use `python3` if that is your interpreter's
command name.

```text
python -I -B typed_observation_compare.py --expected examples/expected.json --actual examples/matching.json
python -I -B typed_observation_compare.py --expected examples/expected.json --actual examples/mismatch.json
```

The first comparison returns `match`, four matched rows, and exit status 0.
The actual rows appear in a different order and include the same duplicate.
The second returns `mismatch`, three matched rows, one expected-only row,
one actual-only row, and exit status 1. The second timestamp in one duplicate
has changed by one microsecond.

## Supply your own saved result sets

Provide two regular UTF-8 JSON files without a byte-order mark. Each file
can contain up to 10,000 rows and use up to 16 MiB. The outer array contains
five-element row arrays with these fields in order.

| Positions | Accepted values |
| --- | --- |
| 1 through 3 | Exact text or `null` |
| 4 and 5 | `YYYY-MM-DDTHH:MM:SS` with an optional one to six fractional digits, or `null` |

Text comparison preserves whitespace, case, empty strings and leading zeros.
Timestamp comparison uses timezone-naive date-time values at microsecond
precision. For example, `.1` and `.100000` represent the same time. Use the
same clock convention in both files. Both sides can be empty.

The JSON report gives status, match counts, and distinct unmatched-row counts.
Raw field values and input paths are omitted. Invalid input exits with status
2 and writes a diagnostic on stderr. The command reads the two supplied files
and writes the comparison summary to stdout.

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

Read `VALIDATION.json` from the release for the Windows and Ubuntu
fresh-extraction results.
