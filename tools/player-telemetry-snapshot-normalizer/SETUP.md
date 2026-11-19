# Use the Offline Player Telemetry Snapshot Normalizer

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/player-telemetry-snapshot-normalizer-v0.1.0).
Compare the ZIP's SHA-256 with its entry in `SHA256SUMS.txt` before extracting.

On Windows, calculate the SHA-256 in PowerShell.

```powershell
Get-FileHash .\player-telemetry-snapshot-normalizer-0.1.0.zip -Algorithm SHA256
```

Once it matches, extract into a new directory.

```powershell
Expand-Archive .\player-telemetry-snapshot-normalizer-0.1.0.zip .\normalizer-demo
Set-Location .\normalizer-demo\player-telemetry-snapshot-normalizer-0.1.0
```

On Ubuntu, calculate the SHA-256 with `sha256sum`.

```bash
sha256sum player-telemetry-snapshot-normalizer-0.1.0.zip
```

Once it matches, extract into a new directory.

```bash
unzip player-telemetry-snapshot-normalizer-0.1.0.zip -d normalizer-demo
cd normalizer-demo/player-telemetry-snapshot-normalizer-0.1.0
```

Run the commands from the extracted directory with Python 3.12 or 3.15.
On Ubuntu, substitute `python3` if needed. The CLI uses the standard library.

## Normalize the fictional snapshots

```text
python -B -m player_telemetry_normalizer --input examples/portal-snapshot.json --mapping examples/mapping.json --format portal
python -B -m player_telemetry_normalizer --input examples/collector-snapshot.json --mapping examples/mapping.json --format collector
```

Each command prints three point records. The lobby has eight players. The
relay has three connections. The collector selects `connection_sessions`
for the relay, even when `players` also has a value. The beacon has
metric kind `availability_only`. Its unreported capacity appears as
`null`. The supplied examples also contain an unmapped ID and unrelated
metadata. Both are omitted from the result.

## Supply your own saved snapshots and ID mapping

Use `--format portal` for a JSON object with a `servers` array or
`--format collector` for an object with a `players_connections` array.
Each array entry is an object. The mode determines which fields are read.

| Field | Portal | Collector |
| --- | --- | --- |
| Source identifier | `id` | `id` |
| Reported state | `state` | `server_status` |
| Population | `population` | `connection_sessions` for connections, `players` for other metric kinds |
| Capacity | `capacity` | `max_players` |
| Population label | `populationLabel` when the mapping uses `auto` | Metric kind comes from the mapping |

The mapping file is a JSON object with a `portal` or `collector` section
for the chosen format. Include both sections to use one mapping file for
both formats. Within each section, use the original ID as the key and give
the corresponding record exactly a `server_id` and a `metric_kind`.
Use `players`, `connections`, or `availability_only`. A portal mapping
can also use `auto`, which selects `connections` for a case-insensitive
match on `populationLabel` and `players` otherwise.

Mapped rows retain their order and repeated observations appear as
separate points. Rows with missing, non-text, or unmapped IDs are skipped.
Mapping IDs must contain nonblank text and fit in 128 UTF-8 bytes.
State aliases `healthy` and `online` produce `online`. `warning` and
`degraded` produce `degraded`. `down`, `offline`, and `critical` produce
`offline`. Other values produce `unknown`.

Counts are converted to integers. Fractions in JSON numbers are truncated
toward zero and negative counts are clamped to zero. Missing, boolean,
or unconvertible counts appear as `null`. An availability-only point can
carry a reported population while its metric kind describes how downstream
tools should interpret it.

Each file is limited to 4 MiB. A snapshot may contain up to 10,000 rows and
each mapping section may contain up to 10,000 entries. Input must be UTF-8
JSON with unique object keys and finite numbers.

## Read the result

A successful run exits with status 0 and prints a JSON object with one
`points` array. Each point has five fields.

```json
{
  "points": [
    {
      "server_id": "lantern-lobby",
      "state": "online",
      "population": 8,
      "capacity": 16,
      "metric_kind": "players"
    }
  ]
}
```

Malformed input produces a diagnostic on stderr and exits with status 2.
The CLI reads the snapshot and mapping and writes the report to stdout.

The normalizer produces point observations. To use them with the
[Offline Player Activity Interval Calculator](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/player-activity-interval-calculator),
build intervals from successive observations with explicit `start` and
`end` timestamps. Carry forward `server_id`, `state`, `population`, and
`metric_kind` for each interval.

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The GitHub release includes validation records for fresh extractions on
Windows and Ubuntu with Python 3.12.16 and 3.15.2.
