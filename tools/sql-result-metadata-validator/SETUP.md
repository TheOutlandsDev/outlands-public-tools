# Use Offline SQL Result Metadata Validator

Download the ZIP and SHA-256 checksums from the [GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/sql-result-metadata-validator-v0.1.0). Verify the ZIP digest before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\sql-result-metadata-validator-0.1.0.zip -Algorithm SHA256
Expand-Archive .\sql-result-metadata-validator-0.1.0.zip .\metadata-demo
Set-Location .\metadata-demo\sql-result-metadata-validator-0.1.0
python -B sql_result_metadata_validator.py --contract examples/contract.json --metadata examples/metadata.json
```

On Ubuntu, use a shell.

```sh
sha256sum -c SHA256SUMS.txt
unzip sql-result-metadata-validator-0.1.0.zip
cd sql-result-metadata-validator-0.1.0
python3 -B sql_result_metadata_validator.py --contract examples/contract.json --metadata examples/metadata.json
```

The fictional example reports eight validated columns. It uses datetime2(6) in column three, with scale 6. Change the timestamp type to datetime2(7) and its scale to 7 to see `unsupported_precision`.

## Saved inputs

- The contract is a JSON object with a columns array of eight distinct, nonempty names in reviewed order.
- The metadata input is a JSON array of eight rows. Each row is an array in the exact field order below. Ordinals must run from 1 through 8. Both error fields must be null. The maximum length, precision and scale fields must be integers. Nullability accepts JSON booleans or integers 0 and 1.
- The third column accepts `datetime` at scale 3, `smalldatetime` at scale 0, and datetime2(0) through datetime2(6) at their declared scales. Its collation field must be null. The other columns use the original character-type rules, with a text collation and zero scale and precision.
- Each input may contain up to 1 MiB of UTF-8 JSON with an optional BOM. The CLI reads local inputs and prints a count on success. On exit 2 it prints a fixed error category to stderr. Saved column names, values and describe-error text stay out of the CLI output.

```text
column_ordinal, name, system_type_name, max_length, precision, scale,
is_nullable, collation_name, error_number, error_type_desc
```

The validation records cover all three original tests with fictional columns and seven CLI check groups on Windows and Ubuntu with Python 3.12.16 and 3.15.2. The runtime uses only the Python standard library.
