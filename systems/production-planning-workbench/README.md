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

Use a new private workspace outside the source or Git checkout, beneath an
existing trusted directory. These example paths and all supplied records are
invented.

```text
python -B workbench.py --workspace ../sample-planning-instance demo
python -B workbench.py --workspace ../sample-planning-instance list
python -B workbench.py --workspace ../sample-planning-instance plan --project sample-workshop
python -B workbench.py --workspace ../sample-planning-instance serve --port 0
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

```text
python -B workbench.py --workspace ../sample-planning-empty init
python -B workbench.py --workspace ../sample-planning-empty import --file inbox/sample-project.json
python -B workbench.py --workspace ../sample-planning-empty show --project sample-workshop
python -B workbench.py --workspace ../sample-planning-empty history --project sample-workshop
python -B workbench.py --workspace ../sample-planning-empty export --project sample-workshop
python -B workbench.py --workspace ../sample-planning-empty backup
```

`init` creates an empty private SQLite store and copies only two fictional input
documents into `inbox`. No actual directory, database or operating configuration
is discovered or imported. Place explicitly selected inputs inside the private
instance. For an existing project, `import --expected REVISION_SHA256` requires
the current revision returned by `show`, `plan` or `history`.

Append an order-state revision using the current project revision:

```text
python -B workbench.py --workspace ../sample-planning-empty revise-order --project sample-workshop --file inbox/sample-order-revision.json --expected REVISION_SHA256
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
python -B workbench.py --workspace ../sample-planning-empty recover --confirm-stopped
```

Recovery removes only a checked empty lock and opens the existing store. It does
not replay commands, repair damaged databases or clear SQLite journal sidecars.
Preserve failed instances and use a separately verified stopped-instance backup
for manual recovery. SQLite backups contain the database, not inbox source files;
there is no automatic restore, retention deletion or encryption.

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
Actual planning authority, manufacturing suitability, shipping verification,
browser acceptance and production deployment remain unverified.
