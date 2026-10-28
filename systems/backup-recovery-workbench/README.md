# Offline Backup & Recovery Workbench

A complete local CLI/browser application for verified independent full snapshots,
fresh-directory restore drills, advisory retention, manual holds, private metadata
reports and interrupted-job review. MIT, copyright TheOutlandsDev. Python 3.12/3.13
with SQLite; standard-library runtime. Optional Chromium acceptance uses separately
installed hash-pinned test dependencies. Windows native junction tests also use
PowerShell 7; the application itself does not require PowerShell.

## Try the complete fictional workflow

Extract the focused source ZIP and open a terminal in that directory. Choose fresh
private sibling directories outside source and Git. The file guards refuse literal
parent traversal, so construct absolute sibling paths first.

PowerShell:

```text
$backupParent = Split-Path -Parent (Get-Location).Path
$backupDemo = Join-Path $backupParent 'private-backup-demo'
$backupPrivate = Join-Path $backupParent 'private-backup-ui'
$backupArchive = Join-Path $backupParent 'backup-recovery-workbench-source.zip'
python -B workbench.py --workspace "$backupDemo" demo
python -B workbench.py --workspace "$backupPrivate" init
python -B workbench.py --workspace "$backupPrivate" serve
```

Ubuntu shell:

```text
backupParent="$(dirname "$PWD")"
backupDemo="$backupParent/private-backup-demo"
backupPrivate="$backupParent/private-backup-ui"
backupArchive="$backupParent/backup-recovery-workbench-source.zip"
python -B workbench.py --workspace "$backupDemo" demo
python -B workbench.py --workspace "$backupPrivate" init
python -B workbench.py --workspace "$backupPrivate" serve
```

The demo creates two full snapshots from separately seeded fictional input trees,
performs a restore and a verification job, exercises manual holds, reviews retention,
exports seven private metadata-report files and verifies an index backup. Each
snapshot contains three files totaling 39 bytes, three directories including an
empty directory, and one matched excluded subtree. One older, restored snapshot
becomes an advisory candidate; the latest remains protected. Nothing is deleted.

Open the printed ephemeral loopback URL on the same computer. The fictional source
folders are already available. Assert quiescence, create a snapshot, inspect its
manifest, reverify its bytes and run a fresh restore drill. Retention and report
review are explicit. Actor and reason fields are private operator assertions.
Use **Stop local server** before using CLI commands against that instance.

## Source selection and stored files

The app reads only an explicitly selected tree below the private instance's `inbox/`.
It does not scan drives, discover user folders, read original operational
configuration or launch received files. Bring a separately reviewed quiescent copy
into a named inbox folder before selecting it. Input source file contents are never
modified by the application. Exclusions are explicit case-insensitive relative path
prefixes; excluded subtrees are recorded at the skipped root and never traversed.
An excluded-root count is not the number of all files inside that subtree.

The instance has `workspace.json`, `inbox/`, `snapshots/`, `restores/`, `database/`,
`reports/`, and `index-backups/`. Treat every instance file as private. Paths, file
hashes, source labels, actor assertions and job records may disclose operational
information even when file payloads are absent from a report.

Each registered snapshot has `files/`, `manifest.json`, and `COMMITTED.json`.
Its manifest records selected relative file paths, byte sizes, SHA-256 hashes,
directories and exclusion coverage. A completion marker is written after copying,
source-change checks and byte verification. A completed journal event is also
required before normal restore or retention considers it registered. Inspecting a
manifest alone explicitly reports `payload_reverified: false`.

Each restore drill creates a new `restores/<generated-id>/files/` tree and writes
`RESTORED.json` only after verification. Existing destinations are never replaced.
Snapshots retain primary file bytes and directory structure. They do not preserve
ACLs, ownership, timestamps, extended attributes, NTFS alternate streams, hardlinks,
symlinks, device files or executable permissions.

## CLI requests

```text
python -B workbench.py --workspace "$backupPrivate" overview
python -B workbench.py --workspace "$backupPrivate" snapshot --file inbox/snapshot-request.json
python -B workbench.py --workspace "$backupPrivate" restore --file inbox/restore-request.json
python -B workbench.py --workspace "$backupPrivate" verify --file inbox/verify-request.json
python -B workbench.py --workspace "$backupPrivate" manifest --id SNAPSHOT_ID
python -B workbench.py --workspace "$backupPrivate" retention --file inbox/retention-request.json
python -B workbench.py --workspace "$backupPrivate" export --file inbox/report-review.json
python -B workbench.py --workspace "$backupPrivate" history
python -B workbench.py --workspace "$backupPrivate" backup-index
```

Request files must already be selected inside the private instance. Snapshot,
restore and verify requests contain `expected_head`, `actor`, `reason`, `request`.
Use the current journal head from `overview`; the empty journal uses 64 zeroes.
Snapshot request data is:

```json
{
  "source": "inbox/sample-files-v1",
  "exclusions": ["cache"],
  "quiescent": true
}
```

Restore/verify request data is an object containing only `snapshot_id`. Hold requests
have `expected_head`, `actor`, `reason`, `snapshot_id`, `hold`. Retention requests
have `expected_head`, `policy`; policy has integer `keep_last` and Boolean
`protect_untested`. Reports additionally require actor/reason and exact Boolean
`quality`, `privacy`, `rights`, `context` checks, all true. See the [contract](docs/CONTRACT.md).

## Recovery in a fresh instance

Keep the complete snapshot folder and its independently retained manifest SHA-256
together with your private recovery procedure. The trusted pin can come from the
reviewed journal/index or a separately retained report; a hash offered only by an
untrusted package is not an independent trust source.

For recovery without the old index, copy a reviewed complete snapshot folder into
the fresh instance's `inbox/reviewed-snapshot`. Use **Restore reviewed snapshot
copy**, or `restore-imported --file inbox/imported-restore-request.json`. Its
`request` has only `source` and `manifest_sha256`, with the usual current head,
actor and reason. The app verifies the exact manifest pin, marker, inventory and
every file before a fresh restore drill. It does not extract archives, register
the imported snapshot, replace the original index or adopt old journal records.

## Retention, reports and interruption

Retention is advisory. Latest snapshots, manual holds, failed current verification,
unfinished jobs and the chosen restore-drill rule protect records. With
`protect_untested: true`, a successful past drill is not enough: an existing
matching restore tree is reverified before it supplies current proof. There is no
delete, purge, cleanup, scheduling, compression or incremental-backup command.
Manual space reclamation requires a separately reviewed procedure; it is not
performed by this app.

Metadata report exports use a fresh directory containing overview, hash-linked
journal, retention and review JSON, individual snapshot-manifest reports, and a
byte manifest. Corrupt/missing records remain visible as failures. These reports
contain private metadata but no file payloads. Their manifest always says
`public_release_authorized: false` and `includes_snapshot_bytes: false`.

**Back up metadata index only** copies and validates the SQLite journal. It does
not contain snapshot bytes or replace a full instance recovery procedure. Preserve
the complete snapshot folders and independently trusted pins. There is no automatic
database restore or journal compaction.

A started job is committed to the journal before payload writes. Failed jobs retain
partial outputs; interrupted jobs block new writes until explicit stopped-instance
review. A physical completion marker without a completed journal record is not
automatically adopted. After verifying every instance process is stopped:

```text
python -B workbench.py --workspace "$backupPrivate" recover --confirm-stopped
```

Recovery clears only an unchanged empty session-lock directory and marks pending
jobs interrupted. It does not resume, delete, overwrite or adopt their outputs.
After an uncertain/lost write response, reload the journal and inspect the job
before another deliberate request. The browser never automatically retries a write.

## Limits and validation boundaries

256 files, 128 directories, 1024 visited entries, eight relative path components,
240 characters per relative path, 4 MiB per file and 32 MiB per tree. Only the
documented portable ASCII name subset is accepted; case collisions, reserved names,
links/reparse points and special files in included content are refused. Excluded
subtrees are not followed. There are at most 64 jobs and 256 journal events per
instance. At a cap, retain the old instance and use a fresh instance plus reviewed
snapshot copies/pins for further recovery drills. Individual JSON/report/source
messages are capped at 4 MiB and the metadata store at 64 MiB. These are operation
bounds, not a global disk quota; retained failed outputs and repeated reports or
index backups also consume space.

Sources must be quiescent. The assertion and repeated source checks do not create
an atomic filesystem snapshot, VSS integration, application-consistent database
backup, immutable storage, encryption, malware isolation or authenticated identity.
Hashes detect differences from the retained pins; they are not signatures. A local
attacker who rewrites the entire journal and data can forge a consistent history.
Trusted parents and no hostile concurrent filesystem editor are assumed. File,
browser and OS activity is not guaranteed to have zero external side effects;
mapped filesystems follow the operator's selected workspace configuration.

## Check and package source

```text
python -B -W error run_checks.py
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install --with-deps chromium
python -B -W error run_browser_checks.py
python -B release_source.py check
python -B release_source.py package --output "$backupArchive"
```

The deterministic new-only source ZIP contains only inventoried code, docs, tests
and invented fixture specifications. It excludes all instances, actual backups,
logs, reports, runtime binaries and operational records. See [copy/recovery rules](docs/SAFETY.md),
[origins](docs/ORIGINS.md) and [validation](docs/VALIDATION.md).
