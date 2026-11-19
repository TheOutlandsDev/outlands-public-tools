# Use the Offline Remote Reachability Evidence Classifier

## Verify and extract

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/remote-reachability-evidence-classifier-v0.1.0).
Compare the ZIP digest with its checksum before extracting into a fresh
directory.

PowerShell

```powershell
Get-FileHash .\remote-reachability-evidence-classifier-0.1.0.zip -Algorithm SHA256
Expand-Archive .\remote-reachability-evidence-classifier-0.1.0.zip .\reachability-demo
Set-Location .\reachability-demo\remote-reachability-evidence-classifier-0.1.0
```

Ubuntu shell

```sh
sha256sum remote-reachability-evidence-classifier-0.1.0.zip
unzip remote-reachability-evidence-classifier-0.1.0.zip -d reachability-demo
cd reachability-demo/remote-reachability-evidence-classifier-0.1.0
```

## Classify the fictional snapshots

Run with Python 3.12 or 3.15. Use `python3` if that is the name of your
interpreter.

```text
python -I -B reachability_evidence.py --input examples/reachable.json
python -I -B reachability_evidence.py --input examples/stale.json
python -I -B reachability_evidence.py --input examples/pending.json
```

The first snapshot reports a reachable service exactly at the 60-second age
limit. The second is one microsecond older and returns `stale`. The third
has an empty evidence object and returns `pending`.

## Supply saved evidence

Use a regular UTF-8 JSON file without a byte-order mark and a size of at
most 256 KiB. The top-level object has these fields.

| Field | Meaning |
| --- | --- |
| `service_id` | Nonempty ID matched exactly against saved service records |
| `as_of` | Evaluation time as an ISO timestamp with a timezone offset |
| `maximum_age_seconds` | Finite, nonnegative number |
| `evidence` | Object with optional `generated` timestamp and optional `services` list |

Saved service records have an `id` and may include `status` and probe notes.
A `generated` timestamp without an offset is interpreted as UTC.
Evidence is fresh from five seconds ahead of `as_of` through the maximum
age, inclusive at both ends.

Fresh `reachable`, `healthy`, or `passed` observations return `reachable`.
Fresh `unreachable`, `failed`, or `down` observations return `unreachable`.
Missing or unusable evidence and conflicting matches stay `pending`.
Evidence outside the freshness window is `stale`.

The report contains a status and a fixed reason. It omits submitted IDs and
probe notes. All four classification states exit with status 0. An invalid
input document exits with status 2 and a fixed diagnostic on stderr.

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

See `VALIDATION.json` for the four fresh-extraction results.
