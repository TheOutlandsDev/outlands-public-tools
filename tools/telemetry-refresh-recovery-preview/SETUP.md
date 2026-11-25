# Run the Offline Telemetry Refresh Recovery Preview

Download the source ZIP and `SHA256SUMS.txt`. In PowerShell run `Get-FileHash .\telemetry-refresh-recovery-preview-0.1.0.zip -Algorithm SHA256` and compare the digest with the checksum file. On Ubuntu run `sha256sum -c SHA256SUMS.txt`.

Extract the ZIP and open a terminal there. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2. The CLI uses the standard library.

Windows PowerShell

```powershell
python telemetry_refresh_recovery.py examples/refresh-timeout.json
python telemetry_refresh_recovery.py examples/first-failure.json
```

Ubuntu

```sh
python3 telemetry_refresh_recovery.py examples/refresh-timeout.json
python3 telemetry_refresh_recovery.py examples/first-failure.json
```

The timeout example reports a warning, keeps the fictional last sample visible, and previews a 10,000 ms retry. The first-failure example reports a critical status because no previous sample is available.

## Input and output

- Supply `error.type` from `Exception`, `OSError`, `RuntimeError`, `TimeoutError`, or `ValueError`, and an `error.message` string.
- Provide `last_snapshot` as an object with an optional `generated` string, or omit it for a first failure. The report shows its sample label and availability.
- Optionally set `refresh_seconds` to an integer. The dashboard clamps the setting to 10–300 seconds and caps the retry at 10 seconds. Set `closed` to true to see a null retry delay for a closed dashboard. The status text keeps the original retry wording.
- A timeout displays the original generic text. Other errors keep the original whitespace normalization and length limit, so inspect the report before sharing it.

The CLI reads up to 1 MiB of UTF-8 JSON. It prints to stdout and leaves the input unchanged. It never starts a collection, runs a command, or schedules a timer. Invalid input returns exit code 2.
