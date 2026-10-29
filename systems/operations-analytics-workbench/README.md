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

Replace `PRIVATE_WORKSPACE` with a new absolute private directory outside the
source/Git tree, beneath an existing trusted parent. Example paths and data are invented.

```text
python -B workbench.py --workspace PRIVATE_WORKSPACE demo
python -B workbench.py --workspace PRIVATE_WORKSPACE plan --project sample-operations
python -B workbench.py --workspace PRIVATE_WORKSPACE serve --port 0
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

Use a different new `PRIVATE_WORKSPACE` for this empty-instance workflow.

```text
python -B workbench.py --workspace PRIVATE_WORKSPACE init
python -B workbench.py --workspace PRIVATE_WORKSPACE import --file inbox/sample-scenario.json
python -B workbench.py --workspace PRIVATE_WORKSPACE show --project sample-operations
python -B workbench.py --workspace PRIVATE_WORKSPACE history --project sample-operations
python -B workbench.py --workspace PRIVATE_WORKSPACE compare --project sample-operations --left 1 --right 1
python -B workbench.py --workspace PRIVATE_WORKSPACE export --project sample-operations
python -B workbench.py --workspace PRIVATE_WORKSPACE backup
```

`init` creates an empty private store and copies two invented input documents.
It does not discover/import an existing environment. Existing scenario imports
require `--expected REVISION_SHA256` using the current hash from `show`, `plan`
or `history`. Individual areas may be empty; capacity/inventory scenarios do not
require planning orders or a manufacturing database.

```text
python -B workbench.py --workspace PRIVATE_WORKSPACE ingest --project sample-operations --file inbox/sample-events.json --expected REVISION_SHA256
python -B workbench.py --workspace PRIVATE_WORKSPACE plan --project sample-operations --revision 1
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
python -B workbench.py --workspace PRIVATE_WORKSPACE attach-planning --project sample-operations --directory inbox/sample-planning-report --expected REVISION_SHA256
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
python -B workbench.py --workspace PRIVATE_WORKSPACE recover --confirm-stopped
```

Recovery removes only a checked empty stale lock; it does not replay commands,
repair damaged stores or clear SQLite sidecars. Preserve failed instances.
Database backups do not include inbox files. There is no automatic restore,
encryption, retention deletion or distributed locking.

## Browser draft and response boundaries

Edits in JSON, case forms or review fields remain private drafts. Save the intended
draft before another action. Loading a project or example with unsaved changes
requires the **Discard drafts when loading** checkbox. A successful load clears
review fields; review records do not carry approval to a new revision. Stale saves,
review versions and report pins are refused. Navigation does not save anything.

Browser actions run one at a time. If a write reply is lost, the page blocks further
writes instead of retrying. Explicitly load the saved project to inspect its actual
state before deciding what to do next; discard consent is required for a remaining
draft. A lost report/backup reply may leave a completed private artifact: inspect
the private reports/backups directory after stopping the application. The stop
button remains available. Reload does not delete artifacts or repair a store.

The API also serializes complete operations and supplies coherent editor/plan/
history snapshots. Browser report requests include the displayed revision pin.
It refuses duplicate Host/token/Origin/length headers, transfer encoding, ambiguous
queries and a present non-JSON Content-Type. Missing Content-Type/Origin remain
compatible with explicit trusted local clients. These checks do not authenticate
reviewer aliases, encrypt the local store or make remote hosting supported.

Optional development browser tests install separately supplied hash-pinned wheels
and the matching Chromium; they are not application runtime dependencies:

```text
python -m pip install --only-binary=:all: --require-hashes -r requirements-browser.txt
python -m playwright install chromium
python -B -W error run_browser_checks.py
```

Linux test hosts may need Playwright system dependencies (`playwright install
--with-deps chromium`). CI uses fresh fictional workspaces; no browser profile,
runtime output, screenshot or downloaded dependency is included in source ZIPs.

The three actual planning-handoff browser methods separately need the companion
public planning source beside this app and its pinned runtime requirements.
Standalone browser runs explicitly skip those methods when it is absent;
`WORKBENCH_REQUIRE_HANDOFF=1` makes absence a failure. Repository CI requires the
companion, stopped-instance export and all handoff methods. No private source is
used. The installed analytics application itself remains standard-library-only.

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
