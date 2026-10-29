# Offline Dataset Review Workbench

A private local browser/CLI application around the public Dataset Review Manager:
explicit JSONL imports, exact deduplication, conservative group holdouts, searchable
records, provenance, review history, content-pinned decisions, private exports and
database-only backups. MIT, copyright TheOutlandsDev.

CPython 3.12/3.13 with SQLite, Windows x64 or Ubuntu x86_64; standard-library runtime.
Browser automation dependencies are optional developer tools, installed separately.
No corpus, model, private configuration, account, browser profile or original system
is bundled. This application does not execute records, contact providers or discover
files. All example records and labels are invented.

## Start a fictional instance

Extract the focused source ZIP. From that source directory, choose a **new absolute
private workspace** under an existing trusted parent, outside source and Git.
Replace `PRIVATE_WORKSPACE` in these commands with that absolute path. Literal
parent traversal is refused by the existing I/O guards.

```text
python -B workbench.py --workspace PRIVATE_WORKSPACE demo
python -B workbench.py --workspace PRIVATE_WORKSPACE status
python -B workbench.py --workspace PRIVATE_WORKSPACE serve --port 0
```

The demo explicitly imports five fictional rows into four records, promotes both
duplicate-linked records to test, approves one unrelated train record, exports it
and validates a database backup. Init alone imports/approves nothing:

```text
python -B workbench.py --workspace NEW_PRIVATE_WORKSPACE init
python -B workbench.py --workspace NEW_PRIVATE_WORKSPACE serve --port 0
```

Open the printed literal loopback URL. Stop with **Stop local UI** or Ctrl+C before
using any CLI against that instance. Only one trusted operator/session is supported.
Legacy CLI tools do not honor the workbench session marker: stop the workbench
before using them. No remote hosting, authenticated accounts or multiuser guarantee.

## Complete browser workflow

1. Place an explicitly selected JSONL inside the private instance's `inbox` and
   import its workspace-relative path. The copied fictional file is available as
   `inbox/sample-records.jsonl`. Each row requires `text` and `group`; optional split
   is train, validation or test. Inputs are 4 MiB, normalized text records 64 KiB.
   Imported approval fields never approve a new record. Reimport preserves reviews.
2. Search text, filter status/split, page through records, then select one to inspect
   literal text, source hashes/row numbers, linked groups, aliases and saved reviews.
   Holdout precedence is test, then validation, then train. Exact text deduplication
   is not semantic similarity or comprehensive benchmark contamination detection.
3. Choose pending, approved or rejected; supply a reviewer alias and evidence note.
   Approval requires all four quality/privacy/rights/context assertions. Credential
   patterns refuse approval and require a **new redacted record**. Records cannot be
   overwritten in place. This is a limited pattern check, not a privacy/IP sanitizer.
4. Save explicitly. State pins include review history, aliases, splits and provenance,
   so stale decisions are refused even when the record text is unchanged. Drafts block
   record switching, refresh and transfers until saved or explicitly discarded. Loaded
   records start with unchecked review fields; saved approval is never a new assertion.
5. Export approved rows privately or create a database-only backup. Every output uses
   a fresh UUID destination; existing files are never replaced. Exports include exact
   checked JSONL bytes and a hash manifest. No output grants public sharing permission.

The interface serializes actions and the application serializes state operations.
New transaction callbacks check pins under SQLite `BEGIN IMMEDIATE` before imports
and reviews. Post-write view-limit validation rolls back before commit. Legacy calls
without callbacks retain their prior parsing, review, deduplication and export rules.
The schema, Windows/POSIX I/O implementations and original tests remain unchanged.

Lost write replies block further browser writes until explicit saved-state refresh;
they are never retried automatically. Server-side uncertain failures similarly hold
writes until a successful explicit refresh. Inspect private export/backup folders
after stopping: a failed/lost reply can leave a complete or partial new artifact.
Refresh does not delete outputs, replay commands or repair a store.

## Existing stores and legacy CLI

Independently stop every writer to an explicitly selected legacy store, protect its
backup, then copy it into a **different new workspace**:

```text
python -B workbench.py --workspace NEW_PRIVATE_WORKSPACE init --from-store SELECTED_PRIVATE_STORE
```

This opens the selected source read-only, validates its canonical schema, and uses
SQLite backup into a new store; no migration or source rewriting occurs. Workbench
views support 2,000 groups/records, 4,000 aliases, 20,000 provenance rows and 5,000
reviews under the existing 64 MiB store limit. Larger/incompatible stores are refused;
refusal can leave a new partial workspace for inspection. The legacy CLI retains its
own existing limits. Only fictional stores are qualified; do not import real data
for public demonstration.

The original interface remains available for stopped instances or separate stores:

```text
python -B review_store.py --store NEW_PRIVATE_STORE init
python -B review_store.py --store PRIVATE_STORE import --input SELECTED_PRIVATE_JSONL
python -B review_store.py --store PRIVATE_STORE list
python -B review_store.py --store PRIVATE_STORE review --id RECORD_ID --decision approved --actor sample_reviewer --note "Fictional review" --quality --privacy --rights --context
python -B review_store.py --store PRIVATE_STORE export --output NEW_PRIVATE_JSONL
```

Standalone source protection now uses this application's folder; a normal `systems`
checkout retains the collection boundary. No absolute machine path is embedded.
See [JSONL I/O](docs/JSONL-IO.md) and [store/schema checks](docs/STORE-SCHEMA.md).

The new CLI accepts `import`, `review`, `export`, `backup` with `--request` pointing
to an explicit private JSON file inside the workspace. [Contracts](docs/WORKBENCH.md)
define request shapes. No arbitrary query, shell, provider URL or output path is
accepted by the browser API.

## Recovery, storage and limits

The whole instance (`workspace.json`, database, inbox, exports, backups and session
marker) is private. Notes, reviewer aliases, content hashes and provenance can identify
people/systems. Review assertions do not independently establish correctness, rights
or anonymity. The browser page/session token also stays private.

After an unclean stop, independently confirm all instance processes have stopped:

```text
python -B workbench.py --workspace PRIVATE_WORKSPACE recover --confirm-stopped
```

Recovery removes only a checked empty stale session directory and reopens the checked
store; no replay, sidecar removal, damaged-store repair or automatic restore occurs.
SQLite backups omit inbox and exports; they are not a full-instance archive. No
encryption, distributed locking, hostile database/filesystem resistance, live-store
copy guarantee, power-loss validation or automatic retention deletion is claimed.

## Validate and package source

```text
python -B -W error run_checks.py
python -m pip install --only-binary=:all: --require-hashes -r requirements-browser.txt
python -m playwright install chromium
python -B -W error run_browser_checks.py
python -B release_source.py check
python -B release_source.py package --output NEW_SOURCE_ZIP
```

Linux test hosts may need `python -m playwright install --with-deps chromium`.
Development installs contact package/browser providers; the fictional application
requires no external service. Source ZIPs contain only pinned source, guides, tests
and invented examples, excluding runtimes, installed dependencies, browser binaries,
profiles, stores, screenshots, traces and generated reports. See [validation and
operational limits](docs/VALIDATION.md) and [origins](docs/ORIGINS.md).
