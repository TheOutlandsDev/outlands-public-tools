# Offline Service Reliability & Incident Workbench

A complete local CLI/browser application for replaying supplied health observations,
tracking incidents, reviewing evidence coverage and exporting private reports.
MIT, copyright TheOutlandsDev. Python 3.12/3.13 with SQLite; standard-library runtime.
The optional actual-Chromium tests use separately installed hash-pinned packages.

This is an offline recording application. It does not collect system metrics, probe
networks, control hosts, restart services, schedule jobs or execute imported code.
All observations, labels, maintenance intent and reviewer identities are operator
assertions. Reports describe the supplied recording, not independently measured uptime.

## Start with fictional observations

Extract the focused source ZIP and open a terminal in its directory. Select fresh
private sibling directories outside source and any Git repository. The guarded I/O
layer refuses literal parent traversal, so construct absolute sibling paths first.

PowerShell:

```text
$reliabilityParent = Split-Path -Parent (Get-Location).Path
$reliabilityDemo = Join-Path $reliabilityParent 'private-reliability-demo'
$reliabilityPrivate = Join-Path $reliabilityParent 'private-reliability-ui'
$reliabilityArchive = Join-Path $reliabilityParent 'reliability-incident-workbench-source.zip'
python -B workbench.py --workspace "$reliabilityDemo" demo
python -B workbench.py --workspace "$reliabilityPrivate" init
python -B workbench.py --workspace "$reliabilityPrivate" serve
```

Ubuntu shell:

```text
reliabilityParent="$(dirname "$PWD")"
reliabilityDemo="$reliabilityParent/private-reliability-demo"
reliabilityPrivate="$reliabilityParent/private-reliability-ui"
reliabilityArchive="$reliabilityParent/reliability-incident-workbench-source.zip"
python -B workbench.py --workspace "$reliabilityDemo" demo
python -B workbench.py --workspace "$reliabilityPrivate" init
python -B workbench.py --workspace "$reliabilityPrivate" serve
```

Open the printed ephemeral loopback URL on the same computer. Choose **Load
fictional recording draft**, inspect the JSON, then **Submit draft**. The dashboard
shows incident details, a status timeline, time-weighted coverage, acknowledgements,
history, comparisons and reviewed private exports. Append templates bind to the
displayed saved hash; errors retain the exact draft. The JSON file picker loads
bytes into a draft without recording the original filename. Stop the server before
using CLI commands against the same instance.

The complete demo imports ten snapshots, acknowledges a reopened health incident,
creates nine private handoff files and validates a database backup. Its invented
100-second main-service window contains 30 healthy, 25 down, 25 unknown and 20
maintenance seconds. A separate planned-off service has 100 excluded seconds.
No time is extrapolated beyond the final supplied snapshot.

## Useful workflows

```text
python -B workbench.py --workspace "$reliabilityPrivate" list
python -B workbench.py --workspace "$reliabilityPrivate" import --file inbox/sample-recording.json
python -B workbench.py --workspace "$reliabilityPrivate" show --case sample_reliability
python -B workbench.py --workspace "$reliabilityPrivate" act --file inbox/append.json
python -B workbench.py --workspace "$reliabilityPrivate" history --case sample_reliability
python -B workbench.py --workspace "$reliabilityPrivate" compare --case sample_reliability --left 1 --right 2
python -B workbench.py --workspace "$reliabilityPrivate" export --file inbox/export-review.json
python -B workbench.py --workspace "$reliabilityPrivate" backup
```

`create` accepts an actor/reason and an empty case definition. `import` additionally
accepts a nonempty ordered snapshot list. Inputs must already be explicitly selected
inside the private instance. See [sample-recording.json](examples/sample-recording.json)
and the [format contract](docs/CONTRACT.md). The browser generates complete append
commands and hash pins. No implicit field mappings or host discovery are performed.

Change policy or maintenance assumptions by importing a separately named case;
saved case configuration is immutable. Compare versions of one case in the UI.
Different cases have separate histories; this release does not automatically rank
their availability percentages or infer causation.

## Incident and evidence rules

- Identity uses service ID, signal ID and incident kind. Changing note text or
  severity does not manufacture a new incident. Repeated cached bad observations
  do not inflate occurrence counts.
- Missing, stale and declared-unknown facts create freshness incidents and hold
  existing health incidents. Absence of an alert is not recovery evidence.
- Recovery needs the configured number of distinct, fresh qualifying observations.
  Reusing one cached healthy observation cannot clear a problem. Long gaps reset
  recovery progress; pre-gap and pre-maintenance evidence cannot clear it later.
- Fresh bad data can clear a freshness incident while its separate health incident
  stays active. Recovery and reopening retain prior episode summaries.
- Acknowledgement never changes health state. Escalation and reopening invalidate
  earlier acknowledgement assertions. Actor/reason assertions remain private.
- Bounded maintenance windows exclude time only within their exact start/end;
  failures become visible again after expiry. Configured planned-off services are
  excluded throughout the recording. These exclusions do not verify actual intent
  or prove that a service is off.

## Coverage, reports and private state

Intervals run from each supplied snapshot to the next. Freshness expiry, maximum
gap and maintenance boundaries split intervals exactly. Unknown time is always
reported. A fresh down signal is sufficient for a down classification; healthy or
degraded classifications require every required signal to be fresh and known.
The report exposes `healthy_fraction_of_known_seconds` and
`observation_coverage_fraction`, with explicit denominators. Degraded time is not
healthy time. Empty denominators produce JSON null. The last snapshot has no
invented duration. See [analysis rules](docs/ANALYSIS.md).

Every export requires quality/privacy/rights/context checks for the latest exact
case hash. A fresh private directory receives case/recording/report/history/review
JSON, incident/timeline/availability CSV and a byte manifest. The manifest always
says `public_release_authorized: false`. CSV fields escape formula-like prefixes.
Failed partial exports stay private and are not silently reused.

`recording.json` can reproduce observations in a fresh instance after explicit
review. It does not restore acknowledgements or history; those remain in `case.json`,
historical views and the database backup. Backups validate the exact schema and
replay all histories. Automatic restore, deletion and compaction are not provided.
Retain the current instance before a separately reviewed restore into a stopped
private instance.

An instance contains `workspace.json`, `database/`, `inbox/`, `reports/` and
`backups/`. Treat the entire instance as private. The app does not redact future
labels, notes, actor identities or supplied operational information.

## Limits and recovery

Eight cases, eight services per case, four required signals per service, eight
nonoverlapping maintenance windows, 128 snapshots per case, 64 revisions per case,
128 total stored case revisions and 64 acknowledgement records per case.
Each recording spans at most 31 days. UTC timestamps use whole seconds in years
2000-2099. Maintenance windows last at most 24 hours. Case documents are bounded at
512 KiB, each I/O message at 4 MiB and the SQLite store at 64 MiB. History retains
observation copies, so start a separately reviewed fresh instance at a cap.

Windows/POSIX guards refuse links/reparse points, hardlinked files, alternate
streams, unsafe parents, unexpected SQLite schema and live sidecars. Writes create
new outputs exclusively. Trusted parents and no hostile concurrent filesystem editor
are assumed. The single-operator UI binds loopback, checks Host/Origin/token and
renders private text with `textContent`. This is not encrypted storage, multi-user
authentication, malware isolation or tamper-proof attestation. An attacker who can
rewrite the complete database can forge a consistent history.

After a crash, first verify that no instance process remains, then:

```text
python -B workbench.py --workspace "$reliabilityPrivate" recover --confirm-stopped
```

Recovery clears only an unchanged empty session-lock directory. It does not replay
unfinished work. After a write response is lost, reload saved state and inspect its
hash/history before trying again; the app never automatically retries writes.
Filesystem checks do not guarantee zero browser or host-OS writes.

## Validate and package

```text
python -B -W error run_checks.py
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install --with-deps chromium
python -B -W error run_browser_checks.py
python -B release_source.py check
python -B release_source.py package --output "$reliabilityArchive"
```

The deterministic new-only source ZIP contains inventoried source, docs, tests and
invented fixtures. Private instances, raw logs, real telemetry and binaries are
excluded. See [origins](docs/ORIGINS.md) and [validation boundaries](docs/VALIDATION.md).
