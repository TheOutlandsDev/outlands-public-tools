# Batch 50: Offline Backup & Recovery Workbench

This complete selected application adapts the generic approved-source archive,
inventory comparison and completion-record method into guarded independent full
snapshots, per-file SHA-256 manifests, fresh restore drills, conservative advisory
retention, manual holds, private reports and interruption review.

A durable started event precedes payload writes. New-only copies preserve primary
file bytes and empty directories; source inventory/identity/hash checks precede
verified completion markers and journal registration. Failed and interrupted jobs
retain partial output without automatic resume, deletion or adoption. Typed journal
replay and exact schema checks guard private metadata.

The app can restore a separately reviewed complete snapshot copy in a fresh instance
with an independently retained manifest pin. This does not import old journal
history or silently register the snapshot. Metadata index backups contain no payload
bytes. Retention rechecks both snapshot and matching restore evidence before using
that proof. It is advisory and offers no delete or cleanup operation.

The original archive helper was read only and remains unchanged/unexecuted. Actual
source sets, paths, schedules, operating configuration, backups, logs, credentials,
user/customer records and third-party/game assets remain private. All included
file trees, contents, labels, actors and recovery requests are newly invented.
The broader original application family remains separately held.

Validation covers exact bytes/manifests, empty directories, exclusions, source
change, tampering, partial failures, fresh-index pinned recovery, received-path
traversal refusal, retention proof, typed journal history and actual owned-child
interruption. Windows/Ubuntu Python 3.12/3.13 and actual Chromium exercise the
selected implementation. Six native link fixtures are mandatory in CI, including
a real Windows junction or a POSIX directory link. The source ZIP must be extracted
and its CLI/setup, private reports, receipts and independent byte oracles verified.

These are bounded copies of quiescent primary file bytes, not atomic live-filesystem,
hot-database, permission, OS or hardware recovery. Sources/parents must be trusted;
checks do not defeat a hostile concurrent editor. No scheduling, archive extraction,
external-service integration, payload execution, encryption, signed attestation or
production suitability is claimed. Future instance data/reports remain private.

First-party source is MIT, copyright TheOutlandsDev. See the [application guide](../systems/backup-recovery-workbench/README.md),
[safety boundaries](../systems/backup-recovery-workbench/docs/SAFETY.md) and
[validation scope](../systems/backup-recovery-workbench/docs/VALIDATION.md).
