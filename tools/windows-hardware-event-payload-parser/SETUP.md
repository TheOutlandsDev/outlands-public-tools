# Use the Offline Windows Hardware Event Payload Parser

## Verify and extract the download

Get the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/windows-hardware-event-payload-parser-v0.1.0).
Compare the ZIP's hash with its entry in the checksum file before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\windows-hardware-event-payload-parser-0.1.0.zip -Algorithm SHA256
Expand-Archive .\windows-hardware-event-payload-parser-0.1.0.zip .\event-parser
Set-Location .\event-parser\windows-hardware-event-payload-parser-0.1.0
```

On Ubuntu, run the equivalent commands.

```bash
sha256sum windows-hardware-event-payload-parser-0.1.0.zip
unzip windows-hardware-event-payload-parser-0.1.0.zip -d event-parser
cd event-parser/windows-hardware-event-payload-parser-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu substitute `python3` for `python` if needed.

## Run the fictional example

```text
python -B -m sentinel_monitor --input examples/events.json
```

The command writes a JSON object containing an `events` array to stdout.
The included example reports four events in file order.

| Record ID | Category | Severity |
| --- | --- | --- |
| 101 | WHEA Corrected Hardware | warning |
| 102 | NVIDIA driver | critical |
| 103 | Storage | warning |
| 104 | Application crash | critical |

The output for record 101 contains the cleaned message
`Fictional corrected hardware event.` to illustrate whitespace collapse
and Unicode format-control removal.

## Use a saved payload

Supply a UTF-8 JSON file up to 4 MiB containing one event object or an array.
One event has these fields.

| Field | Meaning |
| --- | --- |
| `record_id` | Event record identifier convertible to an integer |
| `timestamp` | ISO 8601 event time |
| `provider` | Event provider used for category mapping |
| `event_id` | Provider event identifier convertible to an integer |
| `channel` | Optional channel name, defaulting to `System` |
| `level` | Optional Windows severity text, defaulting to `Information` |
| `message` | Optional message text, cleaned of formatting controls |

The parser accepts a UTF-8 BOM and returns an empty list for blank input.
Rows missing required fields or containing invalid record IDs or timestamps
are skipped. Unreadable files, invalid encoding, oversized files, and invalid
JSON cause a controlled error with exit status 2. The CLI reads the selected
file and leaves it unchanged.

The output retains provider, channel, record ID, timestamp, and message
content. Use the fictional examples for public sharing. Category and severity
labels describe supplied data and can be used as inputs to the Hardware
Event Diagnostic Assessor.

## Verify the source

Use `python -I -B source_check.py` to check the source manifest. Runtime use
requires the Python standard library. In an isolated environment, install the
hash-pinned test dependencies with
`python -m pip install --require-hashes -r requirements-test.txt`, then run
`python -B -m pytest -q -p no:cacheprovider`.

The release records cover clean source extraction and copied CLI checks on
Windows and Ubuntu with Python 3.12.16 and 3.15.2.
