# Operations Analytics & Scenario Workbench

A complete private local application for capacity/coverage scenarios, process
and cycle metrics, stock/reorder proposals, explainable dispatch and completion
reconciliation. Includes interactive browser forms, JSON editing, immutable
scenario revisions, comparisons, review notes, CLI, reports and SQLite backups.

CPython 3.12 or 3.13, standard library only, on Windows or Ubuntu. No package
installation, accounts, original data or external service is required. Node.js
is used only for the optional developer JavaScript syntax check, not at runtime.
See [design](docs/DESIGN.md), [contracts](docs/CONTRACT.md),
[validation](docs/VALIDATION.md) and [source origins](docs/ORIGINS.md).

## Complete fictional demonstration

From this source folder, select a new private directory outside the source/Git
tree, beneath an existing trusted parent. Example paths and data are invented.

```text
python -B workbench.py --workspace ../sample-analytics-instance demo
python -B workbench.py --workspace ../sample-analytics-instance plan --project sample-operations
python -B workbench.py --workspace ../sample-analytics-instance serve --port 0
```

Open the loopback URL printed by `serve`. **Overview** displays calculated
results; **Scenario forms** edits individual capacity, process, inventory,
dispatch-candidate or dispatch-policy cases. Saving creates a new revision.
**JSON editor** handles complete scenarios, active lots and reporting windows.
**Compare & history** shows changes between selected saved revisions.
**Review & integration** records local notes or ingests explicitly selected
private completion batches and planning-report references.

The fictional workflow produces 201 units of capacity, a three-person algebraic
minimum under its assumptions, OEE 0.5625, P90 cycle time 7.1 minutes, an 18-unit
reorder proposal, two eligible/two blocked dispatch candidates, and 25 then 33
completed units after event ingestion. Repeating the same batch adds no event
or revision. The demo records a fictional review, exports seven private report
files and verifies a database backup. No mail or physical action is executed.

Use **Stop local UI** or Ctrl+C before running another CLI session on that
instance. The server is loopback-only and requires a random page token on API
reads/writes, checks Host, and checks Origin on writes. Keep the page/token
private. This is a trusted single-operator local application, not a production
web service or manufacturing/purchasing authority.

## Empty instance and CLI workflow

```text
python -B workbench.py --workspace ../sample-analytics-empty init
python -B workbench.py --workspace ../sample-analytics-empty import --file inbox/sample-scenario.json
python -B workbench.py --workspace ../sample-analytics-empty show --project sample-operations
python -B workbench.py --workspace ../sample-analytics-empty history --project sample-operations
python -B workbench.py --workspace ../sample-analytics-empty compare --project sample-operations --left 1 --right 1
python -B workbench.py --workspace ../sample-analytics-empty export --project sample-operations
python -B workbench.py --workspace ../sample-analytics-empty backup
```

`init` creates an empty private store and copies two invented input documents.
It does not discover/import an existing environment. Existing scenario imports
require `--expected REVISION_SHA256` using the current hash from `show`, `plan`
or `history`. Individual areas may be empty; capacity/inventory scenarios do not
require planning orders or a manufacturing database.

```text
python -B workbench.py --workspace ../sample-analytics-empty ingest --project sample-operations --file inbox/sample-events.json --expected REVISION_SHA256
python -B workbench.py --workspace ../sample-analytics-empty plan --project sample-operations --revision 1
```

Replace the hash placeholder with the current scenario revision. Valid batches
commit atomically. Invalid rows or changed `(source, event_id)` content refuse
the entire batch; identical replay is a no-op. Saved scenarios pin their selected
completion set, so later ingestion cannot silently alter historical results.
Changing reporting assumptions creates a new scenario revision, not an event
identity rewrite. The event ledger retains earlier accepted identities even if
an edited scenario selects a smaller completion set.

Review notes require a current revision, case/domain, expected review version,
reviewer alias, status and note. They are local assertions, not authenticated
signatures or execution approvals. CLI `review --file` accepts a private JSON
command; the browser provides the version and identifiers automatically.

## Explicit planning-report integration

This app remains independent of the companion
[Production Planning Workbench](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/systems/production-planning-workbench).
Export a report there, stop that instance, then explicitly copy its five report
files into a new directory inside this analytics instance, such as
`inbox/sample-planning-report`. Use fictional data when testing the handoff.

```text
python -B workbench.py --workspace ../sample-analytics-empty attach-planning --project sample-operations --directory inbox/sample-planning-report --expected REVISION_SHA256
```

The importer requires the exact supported file inventory, checks byte counts and
SHA-256 hashes, validates source identity/authority flags and reconciles demand,
dock, covered and uncovered totals. It stores a hash receipt plus totals in a
new scenario revision. Hashes establish consistency, not authenticity or verified
physical observations. Planning stages and shipping readiness are not
automatically converted into dispatch eligibility or snapshot states. No
planning database or original application is opened. The standalone download
does not bundle or require the companion application's dependencies.

## Private storage, reports and recovery

The instance contains `workspace.json`, `database`, `inbox`, `reports` and
`backups`. Inputs, policy values, identifiers, notes, histories, reports, mail
drafts and backups are private data. Keep the whole instance outside Git/shared
source folders. Source review does not anonymize future inputs or outputs.

Reports use a fresh UUID directory and include `analytics.json`, five area CSVs,
`summary.eml` and `manifest.json`. Email addresses are reserved fictional
addresses and the draft stays local. CSV formula prefixes are apostrophe-escaped
as a limited spreadsheet measure. Reports/backups never replace destinations;
failed writes may leave a partial new directory for inspection.

Only one ordinary session per instance is supported. After an unclean stop,
independently confirm all instance processes have stopped, then run:

```text
python -B workbench.py --workspace ../sample-analytics-empty recover --confirm-stopped
```

Recovery removes only a checked empty stale lock; it does not replay commands,
repair damaged stores or clear SQLite sidecars. Preserve failed instances.
Database backups do not include inbox files. There is no automatic restore,
encryption, retention deletion or distributed locking.

## Verify and package source

```text
python -B -W error run_checks.py
python -B release_source.py check
python -B release_source.py package --output ../operations-analytics-workbench-source.zip
```

The deterministic focused source ZIP contains the pinned code, guides, tests,
license and fictional examples. It excludes instances, generated reports,
databases and runtime binaries. GitHub automatic whole-repository archives
contain additional collection files outside this focused review.

MIT, copyright TheOutlandsDev. Python, SQLite and OS APIs are separately supplied
under their own terms. All operating assumptions and observations remain
unverified; no workforce optimization, trained prediction, purchasing, physical
execution, standards conformity or production acceptance is implied.
