# Production Planning & Operations Workbench

A complete local application for multi-product order planning, deterministic WIP
allocation, material needs, lot proposals, shipment-readiness declarations and
operator review. Includes a browser interface, CLI, immutable private revisions,
optimistic action versions, CSV/JSON reports, SQLite backups and a fictional demo.

The planning, versioned-demand, lot-sequencing, readiness and operator-transition
engines adapt the owner's original implementation. A new neutral application
shell replaces customer schemas and live integrations. See [origins](docs/ORIGINS.md),
[design](docs/DESIGN.md), [input contract](docs/CONTRACT.md) and
[validation](docs/VALIDATION.md).

## Requirements and installation

CPython 3.12 or 3.13 on **Windows x64** or **Ubuntu x86_64 with glibc**.
Pydantic and its dependencies are separately installed from eight hash-pinned
compatible wheels. No runtime, dependency implementation or binary is bundled.
Other architectures and Python versions are not covered by this lock.

From this application's source folder, create a virtual environment outside the
source tree, then install the pinned requirements:

```text
python -m venv ../sample-planning-venv
```

Windows PowerShell:

```text
../sample-planning-venv/Scripts/python.exe -m pip install --only-binary=:all: --require-hashes -r requirements.txt
../sample-planning-venv/Scripts/Activate.ps1
```

Ubuntu shell:

```sh
../sample-planning-venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements.txt
. ../sample-planning-venv/bin/activate
```

If shell activation is restricted, use the environment's explicit Python path
instead of `python` in subsequent commands. Ubuntu may need its separately
installed Python venv package. Install downloads contact PyPI; the installed
planning application has no external service client or background worker.

## Complete fictional workflow

Replace `PRIVATE_WORKSPACE` with a new absolute private directory outside the
source or Git checkout, beneath an existing trusted directory. These example paths and all supplied records are
invented.

```text
python -B workbench.py --workspace PRIVATE_WORKSPACE demo
python -B workbench.py --workspace PRIVATE_WORKSPACE list
python -B workbench.py --workspace PRIVATE_WORKSPACE plan --project sample-workshop
python -B workbench.py --workspace PRIVATE_WORKSPACE serve --port 0
```

Open the printed loopback URL. The **Planning board** shows demand, assigned dock
stock, allocated WIP, uncovered units, proposed lots, orders, risks, readiness and
local operator actions. **Project editor** edits a complete scenario document;
**Revision history** shows immutable snapshot identities and parent links.
The demo saves two revisions, acknowledges one fictional action, exports a
private report and verifies a backup. Its initial arithmetic is:

```text
160 remaining units = 25 assigned dock units + 85 allocated WIP units + 50 uncovered units
3 proposed lots; no identities reserved and no production/shipping execution
```

Stop the local server with **Stop local UI** or Ctrl+C before another CLI session
uses the instance. API reads/writes require the random page session token;
writes also check Origin and all requests check Host. This is a trusted local
single-operator application, not a remotely exposed manufacturing service.

## Start a fresh private project

Use a different new `PRIVATE_WORKSPACE` for this empty-instance workflow.

```text
python -B workbench.py --workspace PRIVATE_WORKSPACE init
python -B workbench.py --workspace PRIVATE_WORKSPACE import --file inbox/sample-project.json
python -B workbench.py --workspace PRIVATE_WORKSPACE show --project sample-workshop
python -B workbench.py --workspace PRIVATE_WORKSPACE history --project sample-workshop
python -B workbench.py --workspace PRIVATE_WORKSPACE export --project sample-workshop
python -B workbench.py --workspace PRIVATE_WORKSPACE backup
```

`init` creates an empty private SQLite store and copies only two fictional input
documents into `inbox`. No actual directory, database or operating configuration
is discovered or imported. Place explicitly selected inputs inside the private
instance. For an existing project, `import --expected REVISION_SHA256` requires
the current revision returned by `show`, `plan` or `history`.

Append an order-state revision using the current project revision:

```text
python -B workbench.py --workspace PRIVATE_WORKSPACE revise-order --project sample-workshop --file inbox/sample-order-revision.json --expected REVISION_SHA256
```

Replace the placeholder with your current project SHA-256. Prior order states
cannot be edited or removed. A higher `row_version` is required for changed
order state; exact current-version replay is ignored and older/conflicting
versions are refused. Changes to handoff orders must update their explicit
handoff version/quantities in a complete project revision. See the
[contract](docs/CONTRACT.md) before adapting the invented example.

Operator commands acknowledge, add a note, flag an exception or resolve an
exception. Each requires the current plan revision, action identity, expected
action version and a reviewer alias. Notes and exception codes are validated.
These local records do not authenticate a real person or authorize physical
operations. New plan revisions create new action identities; old review records
remain private history. The UI can submit these commands; CLI `action --file`
accepts an explicitly selected private JSON command. Use `--help` for commands.

## Reports, storage and recovery

Private instances contain `workspace.json`, `database`, `inbox`, `reports` and
`backups`. All project inputs, timing/policy values, identities, histories,
reviewers, notes, exports and backups are private application data. Keep the
whole instance outside Git and shared source folders. Input acceptance and
pattern scanning do not anonymize future data or grant sharing permission.

Each new report folder contains `plan.json`, `orders.csv`, `allocations.csv`,
`readiness.csv` and a hash manifest. CSV text starting with common formula
prefixes is apostrophe-escaped; this is limited spreadsheet handling, not a
general document sanitizer. Partial new folders may remain after a write failure.
Reports and backups never replace existing destinations.

An empty `.session-lock` prevents ordinary concurrent sessions. After an unclean
stop, independently confirm all instance processes have stopped, then run:

```text
python -B workbench.py --workspace PRIVATE_WORKSPACE recover --confirm-stopped
```

Recovery removes only a checked empty lock and opens the existing store. It does
not replay commands, repair damaged databases or clear SQLite journal sidecars.
Preserve failed instances and use a separately verified stopped-instance backup
for manual recovery. SQLite backups contain the database, not inbox source files;
there is no automatic restore, retention deletion or encryption.

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

## Validate and package source

```text
python -B -W error run_checks.py
python -B release_source.py check
python -B release_source.py package --output ../production-planning-workbench-source.zip
```

The pinned source inventory covers this app's code, fictional examples, tests,
requirements, notices and guides. Focused ZIP creation is deterministic, new-only
and excludes instances and installed dependencies. GitHub automatic whole-repo
archives include other collection files outside this application's review.

MIT, copyright TheOutlandsDev. See [dependency notices](THIRD-PARTY-NOTICES.md).
Actual planning authority, manufacturing suitability, shipping verification
and production deployment remain unverified.
