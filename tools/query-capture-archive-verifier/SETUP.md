# Use Offline Query Capture Archive Verifier

Download the ZIP and SHA-256 checksums from the [GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/query-capture-archive-verifier-v0.1.0). Verify the digest before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\query-capture-archive-verifier-0.1.0.zip -Algorithm SHA256
Expand-Archive .\query-capture-archive-verifier-0.1.0.zip .\capture-archive-demo
Set-Location .\capture-archive-demo\query-capture-archive-verifier-0.1.0
python -B query_capture_archive_verifier.py --contract examples/contract.json --template examples/detail-template.sql --manifest examples/primary/manifest.json
```

On Ubuntu, use a shell.

```sh
sha256sum -c SHA256SUMS.txt
unzip query-capture-archive-verifier-0.1.0.zip
cd query-capture-archive-verifier-0.1.0
python3 -B query_capture_archive_verifier.py --contract examples/contract.json --template examples/detail-template.sql --manifest examples/primary/manifest.json
```

The fictional primary capture has 36 rows and three null cells. The verifier checks the archive's projection digest against the independent reference in the contract. For the 13-row boundary case, add `--case boundary` and point `--manifest` to `examples/boundary/manifest.json`. That case checks the archive's internal projection digest.

## Prepare your saved inputs

- Obtain the contract from a trusted, independently reviewed source. It specifies the report and manifest schema, eight ordered column names, two products, the expected recorded server/database identity, and four SHA-256 source pins. Each case fixes its dates and sorted row counts per instance. The primary case has an independent projection digest. The boundary reference is explicit JSON null.
- Supply the detail template bytes separately. The verifier checks their SHA-256, normalizes line endings and replaces the single `/*PRODUCT_PARAMETERS*/` marker with two positional placeholders before comparing the bound digest. The template is read as text.
- Keep `manifest.json` and `raw.csv` together. The manifest's CSV path may be the portable filename `raw.csv` or the exact absolute path to that sibling file. The CSV header must match the contract. Row and column positions in the NULL sidecar start at zero and exclude the header. The third column accepts naive timestamps through microsecond precision.
- The verifier checks the original four-field projection in positional order (first, seventh, fifth and second columns), retaining duplicates and preserving empty strings separately from NULL. Its output includes counts and digests. The independent reference covers that projection. The archive verification uses the supplied evidence and runs offline.
- Limits are 64 KiB for the contract, 1 MiB for the template, 5 MiB for the manifest, 50 MiB for the CSV, and 10,000 data rows. SHA-256 pins and digests use uppercase hexadecimal. Exit code 0 means the archive passed. Exit code 2 means the evidence failed verification. The CLI reads the inputs without changing them.

The validation records cover all 10 original archive-loading tests and seven copied-CLI check groups on Windows and Ubuntu with Python 3.12.16 and 3.15.2.
