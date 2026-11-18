# Use the Offline Service Availability Incident Tracker

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/service-availability-incident-tracker-v0.1.0).
Compare the ZIP's checksum with its entry before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\service-availability-incident-tracker-0.1.0.zip -Algorithm SHA256
Expand-Archive .\service-availability-incident-tracker-0.1.0.zip .\availability-demo
Set-Location .\availability-demo\service-availability-incident-tracker-0.1.0
```

On Ubuntu, run

```bash
sha256sum service-availability-incident-tracker-0.1.0.zip
unzip service-availability-incident-tracker-0.1.0.zip -d availability-demo
cd availability-demo/service-availability-incident-tracker-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu substitute `python3` for `python` if needed.

## Run the fictional incident

```text
python -B -m availability_tracker --observations examples/observations.json
```

The command prints JSON with `state` and `completedIncidents`. The supplied
example starts an incident as `degraded`, escalates it to `offline`, and
recovers to `online`. The completed incident has `initialState` set to
`degraded`, `worstState` set to `offline`, and `durationSeconds` set to
420. Without a state file, each invocation starts with an empty state and
prints its result without writing files.

## Provide saved observations

Use a nonempty UTF-8 JSON array up to 4 MiB. Each entry needs an
`observedAt` ISO 8601 timestamp with a time zone and a `checks` array.
Each check needs a Boolean `ok` value. The optional Boolean `required`
defaults to true. Timestamps must strictly increase.

- **Online** requires at least one required check and success for all required checks.
- **Degraded** means at least one check succeeded and the online condition was unmet.
- **Offline** means no check succeeded. An empty check array also produces this state.

## Continue an incident across invocations

Select a state path in an existing directory you control, for example
`availability-state.json` while working in a scratch folder. From the
extracted package, pass the path to that file.

```text
python -B -m availability_tracker --observations examples/observations.json --state PATH_TO_STATE_JSON
```

Use a new state file for the example. On later runs, supply observations
after the saved `previousObservedAt` time. A complete valid batch creates
or atomically replaces the selected state. The `completedIncidents`
array covers incidents completed in that invocation. Retain stdout if you
need a history of completed incidents.

Use one writer per state file. An invalid batch, timestamp, or state file
returns exit status 2 without replacing state. Keep the observations and
state in separate files.

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The release records cover fresh extraction and copied CLI checks on Windows
and Ubuntu with Python 3.12.16 and 3.15.2.
