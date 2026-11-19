# Use the Offline Player Activity Interval Calculator

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/player-activity-interval-calculator-v0.1.0).
Compare the ZIP's SHA-256 with its checksum entry before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\player-activity-interval-calculator-0.1.0.zip -Algorithm SHA256
Expand-Archive .\player-activity-interval-calculator-0.1.0.zip .\activity-demo
Set-Location .\activity-demo\player-activity-interval-calculator-0.1.0
```

On Ubuntu, run

```bash
sha256sum player-activity-interval-calculator-0.1.0.zip
unzip player-activity-interval-calculator-0.1.0.zip -d activity-demo
cd activity-demo/player-activity-interval-calculator-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu substitute `python3` if needed.

## Calculate the fictional intervals

```text
python -B -m player_activity_intervals --input examples/intervals.json --display-offset=-04:00
```

The report shows 7,500 observed seconds, 5,700 online seconds, eight
player-hours, and one connection-hour. The arena's eight player-hours
split evenly across July 27 and 28 in the display offset. Its subsequent
offline observation still contributes to observed time. The lobby's
availability-only observation contributes observed and online time.

## Supply your own saved intervals

Use a UTF-8 JSON object up to 4 MiB with an `intervals` array. A
UTF-8 BOM is accepted. Keys must be unique and numbers finite.

| Interval field | Meaning |
| --- | --- |
| `server_id` | Nonempty UTF-8 text identifier up to 128 bytes |
| `state` | `online`, `offline`, `degraded`, or `unknown` |
| `metric_kind` | `players`, `connections`, or `availability_only` |
| `population` | Nonnegative integer or null |
| `start`, `end` | Whole-second ISO 8601 timestamps with an explicit time-zone offset |

An interval includes its start and excludes its end. Each end must follow
its start. Intervals for the same server may meet at a boundary and
must otherwise be disjoint. Choose `Z` for UTC or a fixed
offset such as `-04:00` or `+05:30`.

The calculator reports daily rows by date and server ID. Observed and
online seconds are sums across server intervals. Each online interval's
population is multiplied by the time observed in that interval. This
produces player-hours for player populations and connection-hours for
connection populations. Offline, degraded, and unknown intervals accrue only observed time.
Availability-only or null-population intervals accrue zero activity hours.

Inputs are limited to 10,000 intervals, 366 days per interval, and 10,000
daily segments before grouping. Valid input prints JSON and exits with
status 0. Invalid arguments or input produce a diagnostic on stderr and
exit with status 2.

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The validation records cover fresh extraction and CLI checks on
Windows and Ubuntu with Python 3.12.16 and 3.15.2.
