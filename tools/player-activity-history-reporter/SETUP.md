# Use the Offline Player Activity History Reporter

## Verify the download

Get the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/player-activity-history-reporter-v0.1.0).
Compare the ZIP's SHA-256 with the entry in `SHA256SUMS.txt`.

On Windows, calculate the hash in PowerShell.

```powershell
Get-FileHash .\player-activity-history-reporter-0.1.0.zip -Algorithm SHA256
```

After it matches, extract into a new folder.

```powershell
Expand-Archive .\player-activity-history-reporter-0.1.0.zip .\history-demo
Set-Location .\history-demo\player-activity-history-reporter-0.1.0
```

On Ubuntu, calculate the hash with `sha256sum`.

```sh
sha256sum player-activity-history-reporter-0.1.0.zip
```

After it matches, extract into a new folder.

```sh
unzip player-activity-history-reporter-0.1.0.zip -d history-demo
cd history-demo/player-activity-history-reporter-0.1.0
```

## Run the fictional example

Use Python 3.12 or 3.15 from the extracted directory. Substitute `python3`
for `python` if that is the name of your interpreter.

```text
python -B -m player_activity_history --input examples/history.json --as-of 2040-07-28 --display-offset=-04:00
```

The player totals show a baseline of 14 hours, 1.03 observed lifetime
hours, and 15.03 total lifetime hours. The archived garden is included
once and contributes 5 of the 15.03 player-hours. The connection total
is 20.05 hours. The availability-only beacon shows a transition from
online to offline on July 27 in the supplied display offset, and its
activity remains zero.

## Supply saved totals

Provide a UTF-8 JSON object with `active` and `archived` arrays. Either
array may be empty. Each ID belongs to one record across both arrays.
Set `metric_kind` to `players`, `connections`, or `availability_only`.

| Active record field | Meaning |
| --- | --- |
| `server_id` | Identifier for a server |
| `metric_kind` | Unit for its activity |
| `baseline_hours` | Historical carry-in for that server, in hours |
| `daily` | Saved observed activity, as objects with a `date` and `activity_seconds`. Use one row per date and include the saved lifetime history. |
| `states` | Optional state samples, as objects with an offset-aware ISO 8601 `observed_at` timestamp and a `state` of `online`, `offline`, `degraded`, or `unknown`. |

Each archived record has a `server_id`, `metric_kind`, `baseline_hours`,
and `observed_activity_seconds` for the already summarized history.
Supply the observed amount separately from the baseline. Zero is valid
for either. State observations and daily dates must be on or before
the report date in the selected display offset. Provide daily dates
using that same calendar.

Input is limited to 4 MiB, 1,000 records per server array, and 50,000
daily and state rows combined. Every ID is nonblank and at most 128 UTF-8
bytes. Activity values must be nonnegative finite numbers no greater
than 1 trillion. Daily dates and state instants must be unique per
server. Timestamps require seconds and an explicit offset or `Z`.

The CLI requires `--as-of YYYY-MM-DD` and uses UTC by default. Use
`--display-offset=±HH:MM` to choose a fixed offset for displaying and
grouping state events. Calendar-date windows include the report date.
Fixed offsets apply throughout the report.

## Read the report

- `totals.players` and `totals.connections` use their own units. Within
  each unit, `lifetime_hours` is the baseline plus observed lifetime
  activity. It also equals the active and archived lifetime amounts
  combined, subject to rounding of displayed values.
- The 7- and 30-day observed window totals use dated active rows.
  The seeded window totals add each historical baseline once, including
  the archived baseline. Archived observed activity belongs to lifetime
  totals because it has no supplied daily dates.
- Each active server has a 30-day daily series with gaps filled and a
  cumulative lifetime series grouped by Monday–Sunday weeks. The final
  partial week ends on the report date. Daily cumulative values include
  the baseline and prior activity from the supplied history.
- State transitions are shown newest first for the last 30 dates, up to
  40 events. A state observed before the window can establish the
  starting state. Availability-only records can still produce events.

The CLI writes JSON to stdout and leaves the input file untouched.
Malformed input produces a diagnostic on stderr and exits with status 2.

## Check the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The release includes validation records for fresh extractions on Windows
and Ubuntu with Python 3.12.16 and 3.15.2.
