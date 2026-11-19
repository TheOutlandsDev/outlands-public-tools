# Use the Offline Host Readiness Report Builder

## Verify and extract

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/host-readiness-report-builder-v0.1.0).
Compare the ZIP digest with the corresponding checksum before extraction.
Extract into a fresh directory.

PowerShell

```powershell
Get-FileHash .\host-readiness-report-builder-0.1.0.zip -Algorithm SHA256
Expand-Archive .\host-readiness-report-builder-0.1.0.zip .\readiness-demo
Set-Location .\readiness-demo\host-readiness-report-builder-0.1.0
```

Ubuntu shell

```sh
sha256sum host-readiness-report-builder-0.1.0.zip
unzip host-readiness-report-builder-0.1.0.zip -d readiness-demo
cd readiness-demo/host-readiness-report-builder-0.1.0
```

## Read the fictional snapshots

Run from the extracted directory with Python 3.12 or 3.15. On installations
where the command is named `python3`, use that command.

```text
python -B -m opskit doctor --observations examples/pass.json --json
python -B -m opskit doctor --observations examples/warning.json --json
python -B -m opskit doctor --observations examples/failure.json --json
python -B -m opskit doctor --observations examples/malformed.json --json
```

The examples return `pass` (exit 0), `warn` (exit 0), `fail` (exit 1),
and an input error (exit 2) respectively. An input error writes the diagnostic
to stderr. Omit `--json` for a human-readable report.

## Supply your own saved measurements

Save a regular UTF-8 file without a byte-order mark. The file can contain one JSON object of up to 16 KiB with exactly these fields.

| Field | Accepted value |
| --- | --- |
| `os` | `windows`, `linux`, or `other` |
| `python_version` | Three dot-separated components of one to four digits, such as `3.15.2` |
| `workspace` | `writable`, `read_only`, `missing`, or `not_directory` |
| `disk_total_bytes`, `disk_free_bytes` | Nonnegative integer byte counts with free at most total, or both `null` |
| `memory_total_bytes`, `memory_available_bytes` | Nonnegative integer byte counts with available at most total, or both `null` |
| `temporary_directory_writable`, `hostname_resolution` | Boolean or `null` |

Assessments describe the supplied measurements. They use no live OS probes,
hostname lookup, or directory measurements. Reports contain the supported OS
label, Python version, byte counts and statuses. Local paths, hostnames and IP
addresses are outside the input schema and are omitted from reports.

Disk space fails below 2 GiB free. Otherwise it warns below 5 GiB free or
10% free. Memory fails below 256 MiB available. Otherwise it warns below 10%
available. A failure takes precedence over any warning. When the workspace is
missing or is not a directory, the disk check is skipped. A missing disk measurement fails if the workspace exists. An unknown memory,
temporary-directory, or hostname-resolution observation produces a warning.

## Use the JSON in an incident bundle

Save the JSON from a successful fictional example in a fresh workspace.

PowerShell

```powershell
python -B -m opskit doctor --observations examples/pass.json --json | Out-File -FilePath ..\doctor.json -Encoding ascii -NoClobber
```

Ubuntu shell

```sh
(set -C; python -B -m opskit doctor --observations examples/pass.json --json > ../doctor.json)
```

Use that file for `--doctor` in the
[Incident Evidence Bundle Builder's usage guide](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/incident-evidence-bundle-builder#offline-incident-evidence-bundle-builder).
The bundle builder takes its own saved inventory and ports JSON files.

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The release validation record includes fresh-extraction CLI checks for both
operating systems and Python versions, including a round trip through the
Incident Evidence Bundle Builder with fictional data.
