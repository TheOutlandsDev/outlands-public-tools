# Use the Offline Availability Evidence Exporter

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/availability-evidence-exporter-v0.1.0).
Compare the ZIP's SHA-256 with its checksum entry before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\availability-evidence-exporter-0.1.0.zip -Algorithm SHA256
Expand-Archive .\availability-evidence-exporter-0.1.0.zip .\evidence-demo
Set-Location .\evidence-demo\availability-evidence-exporter-0.1.0
```

On Ubuntu, run

```bash
sha256sum availability-evidence-exporter-0.1.0.zip
unzip availability-evidence-exporter-0.1.0.zip -d evidence-demo
cd evidence-demo/availability-evidence-exporter-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu substitute `python3` for `python` if needed.

## Run the fictional example

```text
python -B -m availability_evidence --input examples/availability.json
```

The command prints a JSON object with `safety` and `signals`. The example
reports 23.25% disk free space, temperatures of 61 °C for the CPU and
57.5 °C for the GPU, a recorded quarantine state of `clear`, and one
`storage` event category.

## Provide saved evidence

Supply a UTF-8 JSON object up to 4 MiB with a `snapshot` object and a
`signals` array. The exporter accepts a UTF-8 BOM. It requires unique keys
and finite JSON numbers. Use an empty array when the snapshot has no check
results.

The `safety` object contains `diskFreePercent`, `hardwareQuarantine`,
`maximumGpuTemperatureC`, `maximumCpuTemperatureC`, and
`criticalHardwareEvents`. Freshness comes from the supplied
`source_health.system.state` field. Stale or unavailable system data yields
null measurements, an unavailable quarantine state, and an empty event list.
The quarantine field also requires a saved diagnostics status that declares
active storage coverage. Event categories are derived from warning and
critical rows and deduplicated.

Each signal needs these fields.

| Field | Meaning |
| --- | --- |
| `state` | Caller-supplied `proven`, `failed`, or `unavailable` |
| `method` | Text label for the check, limited to 80 characters in the report |
| `observedAtUtc` | ISO 8601 timestamp with an explicit UTC offset of zero |
| `result` | JSON value used to calculate `resultSha256` |

The digest uses compact UTF-8 JSON with object keys sorted recursively.
Changing key order produces the same digest. Array order and values are
part of the digest. The report carries the declared state, method,
timestamp, and digest. Use fictional input when sharing examples publicly.

A valid input returns exit status 0 and prints the report to stdout.
Malformed, unreadable, or oversized input returns exit status 2 with a
diagnostic on stderr.

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The validation records cover fresh source extraction and copied command-line
checks on Windows and Ubuntu with Python 3.12.16 and 3.15.2.
