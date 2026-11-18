# Use the Offline Hardware Sensor Snapshot Validator

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/hardware-sensor-snapshot-validator-v0.1.0).
Compare the ZIP's hash with its checksum entry before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\hardware-sensor-snapshot-validator-0.1.0.zip -Algorithm SHA256
Expand-Archive .\hardware-sensor-snapshot-validator-0.1.0.zip .\snapshot-demo
Set-Location .\snapshot-demo\hardware-sensor-snapshot-validator-0.1.0
```

On Ubuntu, run

```bash
sha256sum hardware-sensor-snapshot-validator-0.1.0.zip
unzip hardware-sensor-snapshot-validator-0.1.0.zip -d snapshot-demo
cd snapshot-demo/hardware-sensor-snapshot-validator-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu use `python3` if that is the interpreter command.

## Run the fictional snapshot

```text
python -B -m sensor_snapshot --input examples/snapshot.json --now 2040-01-02T03:04:10Z
```

The command prints JSON with `readings` and `status`. The example returns
three temperatures in Celsius. The two CPU readings are 42 and 48
degrees, and the GPU reading is 55. The fan row is skipped.

## Check a saved snapshot

Supply a UTF-8 JSON file up to 4 MiB. The validator accepts a UTF-8 BOM.
An active snapshot needs these fields.

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `administrator` | Input declaration set to JSON `true` |
| `status` | `active` |
| `generated` | ISO 8601 snapshot time. A timestamp without an offset is interpreted as UTC. |
| `sensors` | Array of readings with `sensor_type`, `value`, and CPU-identifying hardware or name text. |

The age limit defaults to 20 seconds. Use `--max-age-seconds` to select
another finite nonnegative age limit. The validator allows a snapshot to
be up to five seconds ahead of the reference time. The CLI uses current
UTC time unless you supply a time-zone-aware `--now` value.

The validator retains numeric temperatures between -50 and 200 degrees
Celsius, inclusive. It identifies CPU entries from hardware and name text
and requires at least two qualifying entries. The administrator flag and
sensor labels are declarations in the input. The command reads the named
file and prints its findings.

| Exit status | Meaning |
| --- | --- |
| 0 | Active snapshot with usable temperature readings |
| 1 | JSON was read and the snapshot is unavailable. The JSON report gives the reason. |
| 2 | Invalid command, unreadable or oversized file, or invalid UTF-8 or JSON |

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The validation records cover fresh extraction and copied CLI checks on
Windows and Ubuntu with Python 3.12.16 and 3.15.2.
