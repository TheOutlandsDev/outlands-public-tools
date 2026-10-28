# Offline Data Import & Migration Workbench

A complete local CLI/browser application for mapping explicitly selected CSV and
JSONL into reviewed, fresh SQLite stores. Preview normalized records, duplicate
provenance, rejected rows and conflicting keys before importing. Durable attempts,
independent readback, private handoffs and interruption review are included.
MIT, copyright TheOutlandsDev. Python 3.12/3.13 with SQLite; standard-library runtime.
Optional Chromium acceptance installs separately pinned test dependencies. Windows
native junction fixtures use PowerShell 7; the application does not use PowerShell.

This is a bounded data-import workflow. It does not alter existing databases,
discover drive contents, connect to external services, execute received code or
perform database-schema upgrades. See [contracts](docs/CONTRACT.md),
[safety](docs/SAFETY.md), [origins](docs/ORIGINS.md) and [validation](docs/VALIDATION.md).

## Try the complete fictional workflow

Extract the focused source ZIP and open a terminal in its application directory.
Select fresh private sibling directories outside source control. Literal parent
traversal is refused, so construct absolute sibling paths first.

PowerShell:

```text
$migrationParent = Split-Path -Parent (Get-Location).Path
$migrationDemo = Join-Path $migrationParent 'private-migration-demo'
$migrationPrivate = Join-Path $migrationParent 'private-migration-ui'
$migrationArchive = Join-Path $migrationParent 'migration-rebuilt-source.zip'
python -B workbench.py --workspace "$migrationDemo" demo
python -B workbench.py --workspace "$migrationPrivate" init
python -B workbench.py --workspace "$migrationPrivate" serve
```

Ubuntu shell:

```text
migrationParent="$(dirname "$PWD")"
migrationDemo="$migrationParent/private-migration-demo"
migrationPrivate="$migrationParent/private-migration-ui"
migrationArchive="$migrationParent/migration-rebuilt-source.zip"
python -B workbench.py --workspace "$migrationDemo" demo
python -B workbench.py --workspace "$migrationPrivate" init
python -B workbench.py --workspace "$migrationPrivate" serve
```

The demo previews seven invented rows: three accepted records, two identical
duplicates retaining five accepted source locations, and two rejected rows. It
imports one fresh store, refuses an exact repeat, demonstrates a separate
three-row conflicting-key group, exports eight private handoff files and verifies
an index backup. There are three retained previews, one registered import and eight
journal events. Source bytes and existing destinations are not modified.

Open the printed ephemeral loopback URL on the same computer. Create a pinned
preview, inspect its values and provenance, make the explicit review assertions,
accept the documented rejection policy and create a fresh store. Verification
checks its schema, stored bytes, every normalized row and provenance entry. Use
**Stop local server** before CLI access to that instance.

## Inputs and mapping

Bring independently reviewed inputs into this instance's `inbox/`. Select each
relative path and its `csv` or `jsonl` format explicitly. No glob, directory walk,
automatic source discovery, compressed archive or source execution is supported.
The sample contract maps `id`, `quantity`, `amount`, `active` and nullable `note`.
You can edit the source/target names and types before creating another preview.

Contracts define a nonnullable text/integer key, unique source/target names,
`unknown_fields` (`reject` or recorded `ignore`), `trim_strings`, `empty_as_null`,
and a list of `source`, `target`, `type`, `nullable` mappings. Types are text,
integer, Boolean and exact decimal. Decimal results are canonical strings; JSON
floating-point values are refused for that type. No expressions, implicit dates,
locale-dependent numbers, schema inference or business-specific transformations
are evaluated. Detailed rules and limits are in the [contract](docs/CONTRACT.md).

Identical normalized rows for the same key become one record with all source
locations. Any differing variant for a key holds every row for that key as a
conflict; an import containing conflicts is blocked. Correct the input or mapping
and create a new preview. Invalid rows carry source hashes, physical line spans
and fixed rejection codes, without copying their raw rejected values into reports.
Accepted and conflicting values remain private and are visible in the preview.

## CLI requests and stored artifacts

```text
python -B workbench.py --workspace "$migrationPrivate" overview
python -B workbench.py --workspace "$migrationPrivate" plan --file inbox/preview-request.json
python -B workbench.py --workspace "$migrationPrivate" inspect-plan --id PLAN_ID
python -B workbench.py --workspace "$migrationPrivate" import --file inbox/import-request.json
python -B workbench.py --workspace "$migrationPrivate" inspect-import --id IMPORT_ID
python -B workbench.py --workspace "$migrationPrivate" export --file inbox/export-review.json
python -B workbench.py --workspace "$migrationPrivate" history
python -B workbench.py --workspace "$migrationPrivate" backup-index
```

The seeded `preview-request.json` is valid only for the empty journal. Every plan
and import request has `expected_head`, `actor`, `reason`, `request`. Obtain the
current head from `overview` or the previous successful response. Plan request data
contains only `sources` and `contract`. Import request data is:

```json
{
  "plan_id": "REPLACE_WITH_REVIEWED_PLAN_ID",
  "plan_sha256": "REPLACE_WITH_RETAINED_PREVIEW_HASH",
  "accept_rejections": true,
  "checks": {"quality": true, "privacy": true, "rights": true, "context": true}
}
```

These placeholder strings are not valid identifiers. Use the actual saved preview
ID/hash. All four checks must be exact true Booleans. `accept_rejections` must be
true when rejected rows exist; only accepted records are imported, and rejection
records remain visible. An empty accepted set or any conflicting key blocks import.
Successful exact fingerprints cannot be imported again in the same index. Selected
sources are ordered canonically, so reordering the source list is not a new plan.
Changing selectors, bytes or contracts can create a different fingerprint; this
is exact-repeat protection, not semantic duplicate detection across all instances.

The private instance contains `workspace.json`, `inbox/`, `database/`, `plans/`,
`stores/`, `reports/` and `index-backups/`. Each preview has `plan.json` and a final
`PLANNED.json` marker. Each fresh store has `data.sqlite3` and final `READY.json`.
Journal registration is additionally required; a marker alone is never adopted.
The SQLite store contains fixed `meta`, `records`, `sources`, `provenance` and
`rejected` tables. No user SQL or dynamic column SQL is executed.

Input bytes are checked again before and after database construction. Received
preview files are never automatically trusted. Destination verification can use
the retained pinned preview without rereading later input revisions. Inspecting
a preview explicitly says current source bytes were not reverified at that step.

## Private handoffs and recovery

Export requests have `expected_head`, `actor`, `reason`, `plan_id`, nullable
`import_id`, and the four review checks. An import selection must belong to that
preview and pass current store verification. The handoff includes the preview,
accepted JSONL, display CSV, rejection summaries, journal, review assertions,
receipt and file-hash manifest. **It contains normalized values and private
provenance.** Review assertions do not anonymize it or authorize publication.
The manifest always records `public_release_authorized: false`.

JSONL preserves types and nulls. Display CSV prefixes an apostrophe for formula-like
cells; it changes those displayed values and cannot distinguish null from empty
text. It is not the authoritative round-trip format or a universal spreadsheet
security guarantee. Raw rejected rows and original source bytes are not copied.

Every attempt starts durably before output creation. Failures retain partial
outputs and fixed error codes. A lost response is uncertain: reload the journal
and inspect the recorded result before another deliberate request. The browser
does not automatically retry writes. A pending attempt blocks new jobs.

After independently confirming every instance process is stopped:

```text
python -B workbench.py --workspace "$migrationPrivate" recover --confirm-stopped
```

This clears only an unchanged empty stale session lock and marks pending attempts
interrupted. It never resumes, deletes or adopts output. A retry uses a fresh job
directory. There is no automatic index restoration, migration rollback, compaction
or cleanup. Keep the complete instance if you need its history and artifacts.
**Metadata index backup only** excludes preview files and imported store bytes;
it is not a complete instance backup or disaster-recovery procedure.

## Bounds and source verification

At most eight selected 1 MiB input files, 1,000 total parsed data rows, 16 mapped
fields and 32 input columns/keys. Text results are at most 256 UTF-8 bytes. Preview
artifacts are at most 3 MiB, individual messages/reports at most 4 MiB, each fresh
SQLite store at most 8 MiB, and the metadata journal at most 64 MiB. An instance
has at most 64 attempts and 256 journal events. Retain capped instances; use a new
private instance for further work. These limits are not a global disk quota.
Repeated reports, index backups and retained failed outputs consume additional space.

```text
python -B -W error run_checks.py
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install --with-deps chromium
python -B -W error run_browser_checks.py
python -B release_source.py check
python -B release_source.py package --output "$migrationArchive"
```

The deterministic source ZIP inventories code, docs, tests and invented fixtures.
It excludes original programs/configuration, real corpora/conversations, instance
stores, source inputs, reports, logs, credentials and runtime binaries. Trusted
parents and no hostile concurrent filesystem editor are assumed. This release
does not establish production suitability, authenticated identity, encryption,
signed attestation, atomic live-source capture or power-loss/hardware recovery.
