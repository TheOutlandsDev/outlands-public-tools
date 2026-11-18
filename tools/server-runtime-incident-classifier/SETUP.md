# Use the Offline Server Runtime Incident Classifier

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/server-runtime-incident-classifier-v0.1.0).
Compare the ZIP's SHA-256 with its checksum entry before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\server-runtime-incident-classifier-0.1.0.zip -Algorithm SHA256
Expand-Archive .\server-runtime-incident-classifier-0.1.0.zip .\runtime-demo
Set-Location .\runtime-demo\server-runtime-incident-classifier-0.1.0
```

On Ubuntu, run

```bash
sha256sum server-runtime-incident-classifier-0.1.0.zip
unzip server-runtime-incident-classifier-0.1.0.zip -d runtime-demo
cd runtime-demo/server-runtime-incident-classifier-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu substitute `python3` if needed.

## Run the fictional example

```text
python -B -m server_runtime --input examples/servers.json
```

The command prints an `incidents` array in input order. The sample produces
four incidents.

| Saved observation | Severity |
| --- | --- |
| Archive service with status `down` and missing runtime status | Critical |
| Service in a scheduled restart window | Warning |
| Online service expected to be off | Warning |
| Online service with an automation issue | Warning |

The retired service is intentionally stopped and has no automation
issues, so it is omitted. The healthy service is also omitted.

## Classify your own saved observations

Supply a UTF-8 JSON object up to 4 MiB with a `servers` array. The
classifier accepts a UTF-8 BOM and requires unique keys and finite JSON
numbers. Use one object per server.

| Field | Meaning |
| --- | --- |
| `id`, `name` | Required nonempty text identifier and label |
| `status` | Optional saved health status |
| `runtime_status` | Saved runtime classification, such as `down`, `maintenance`, `planned_off`, or `online` |
| `observed_runtime_status` | Observed runtime state, used to identify an online service expected to be off |
| `expected_state` | Planned runtime state, defaulting to `online` |
| `issues`, `automation_issues` | Optional arrays of text, defaulting to empty arrays |
| `notes`, `expected_state_reason` | Optional text carried into the incident evidence |

When runtime status is missing, health status `down` supplies the fallback
runtime state. The report includes the source, code, severity, summary,
evidence, and a SHA-256 fingerprint of the source, code, and summary.
The evidence reflects saved statements and includes advisory text. Use
fictional observations when sharing examples publicly.

Valid input returns exit status 0, including an empty result. Invalid
arguments, malformed data, or unreadable or oversized files return
exit status 2 with a diagnostic on stderr.

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The validation records cover fresh source extraction and copied command-line
checks on Windows and Ubuntu with Python 3.12.16 and 3.15.2.
