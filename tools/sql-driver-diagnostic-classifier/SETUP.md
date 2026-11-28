# Use Offline SQL Driver Diagnostic Classifier

Download the source ZIP and SHA-256 manifest from the [GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/sql-driver-diagnostic-classifier-v0.1.0). Compare the digest before extracting. On Windows, use PowerShell.

```powershell
Get-FileHash .\sql-driver-diagnostic-classifier-0.1.0.zip -Algorithm SHA256
Expand-Archive .\sql-driver-diagnostic-classifier-0.1.0.zip .\driver-demo
Set-Location .\driver-demo\sql-driver-diagnostic-classifier-0.1.0
python -B sql_driver_diagnostic_classifier.py --input examples/diagnostic.json
```

On Ubuntu, use a shell.

```sh
sha256sum -c SHA256SUMS.txt
unzip sql-driver-diagnostic-classifier-0.1.0.zip
cd sql-driver-diagnostic-classifier-0.1.0
python3 -B sql_driver_diagnostic_classifier.py --input examples/diagnostic.json
```

The fictional record yields SQLSTATE `08001`, category `tls_validation` and reason `certificate_hostname_mismatch`. The report has fixed guidance text.

## Input and output

- Save one JSON object with a message string and an optional `sqlstate` string or null. Use UTF-8 with an optional BOM and a maximum file size of 65,536 bytes.
- Put only the driver's SQLSTATE in the `sqlstate` field. A five-character state made up of uppercase ASCII letters and digits is copied to the result. Missing states and other formats produce `UNKNOWN`.
- The report uses fixed labels for Windows security context, TLS, authentication, connectivity, driver availability, and other database errors. The optional TLS reason uses message phrases and recognized native codes in signed decimal, unsigned decimal or hexadecimal form. Unrecognized TLS messages receive `unknown_tls_error`.
- The CLI omits the original driver message, including hostnames, credentials, and native codes contained in it. Keep the original file local if it contains sensitive data. The tool reads the file without modifying it. It runs offline and uses only the Python standard library.
- Exit code 0 means a diagnostic was classified. Exit code 2 means the input was unreadable, oversized, or invalid. Certificate and connection guidance is based on the saved text.

Validation covers five original tests, their 27 subtests, and seven CLI check groups on Windows and Ubuntu with Python 3.12.16 and 3.15.2.
