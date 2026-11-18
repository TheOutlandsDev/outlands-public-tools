# Use the Offline Crash Telemetry Report

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/crash-telemetry-report-v0.1.0).
Compare the ZIP's SHA-256 with its checksum entry before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\crash-telemetry-report-0.1.0.zip -Algorithm SHA256
Expand-Archive .\crash-telemetry-report-0.1.0.zip .\crash-report
Set-Location .\crash-report\crash-telemetry-report-0.1.0
```

On Ubuntu, run the equivalent commands.

```bash
sha256sum crash-telemetry-report-0.1.0.zip
unzip crash-telemetry-report-0.1.0.zip -d crash-report
cd crash-report/crash-telemetry-report-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu substitute `python3` for `python` as needed.

## Report on a fictional snapshot

Run these commands from the extracted directory. The first creates a new
directory containing four fictional source files. The second prints a JSON
report.

```text
python -B examples/make_fixture.py fictional-telemetry
python -B -m crash_telemetry --database fictional-telemetry/snapshots.db --sensors fictional-telemetry/sensors.json --thermal-guard fictional-telemetry/thermal-guard.json --quarantine fictional-telemetry/quarantine.json --now-utc 2040-01-02T03:04:20Z
```

The report selects the highest row ID. For this example it reports a
20-second sample age, peak temperatures of 49 °C for CPU, 41 °C for GPU,
and 32 °C for storage, and a recorded thermal guard status of `armed`.

## Report on your own saved files

Use a closed, stable SQLite export in rollback-journal mode, up to 128 MiB.
The export needs a `snapshots` table with `id`, `captured_at`, and
`payload_json` columns. The reader refuses WAL-mode files and files with
SQLite journal or WAL sidecars. Keep the export closed to writers during use.

The three saved JSON files should be UTF-8 objects up to 4 MiB each. The
sensor file can include a `generated` timestamp and a `sensors` array
with `hardware`, `sensor_type`, `name`, and `value`. The thermal guard and
quarantine files supply recorded status fields. The report can include
identifiers and statuses from the files, so use the fictional example when
sharing output publicly.

The report labels snapshots up to 180 seconds old as fresh. It uses current
UTC time unless you pass a time-zone-aware `--now-utc` value. A report with
missing or invalid sources includes an `errors` array and exits with status 1.
Status 0 indicates the files were read successfully. Invalid command
arguments exit with status 2.

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The validation records cover fresh extraction and copied CLI checks on Windows
and Ubuntu with Python 3.12.16 and 3.15.2.
