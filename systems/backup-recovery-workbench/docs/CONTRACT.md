# Private snapshot and journal contract

The instance format is `outlands-backup-recovery-workbench-v1`. All mutating requests
bind the exact current `expected_head` SHA-256, plus a private actor/reason assertion.
No identity is authenticated. Extra fields, duplicate JSON keys, invalid UTF-8,
nonfinite numbers, excessive nesting and wrong scalar types fail. IDs are generated
32-character lowercase hexadecimal strings; pins are 64-character lowercase hex.

Snapshot request data has `source`, `exclusions`, `quiescent`. Source is an explicit
`inbox/<named-tree>` selector. Absolute paths, parent traversal, alternate streams,
backslashes and unsupported portable names fail. Exclusions are up to 16 unique
case-insensitive relative prefixes. The assertion must be Boolean true. Included
entries must be single-link regular files or directories. Exclusions stop traversal
at the matched root and record that root, not its undiscovered descendants.

Snapshots are independent full primary-byte copies, not incremental chains. The
canonical `outlands-full-snapshot-v1` manifest has snapshot ID, relative source
selector, requested/matched exclusions, directories, file byte/hash entries and
total bytes. Directory parents must be declared, names cannot collide after case
folding, and typed size/count bounds apply. `COMMITTED.json` pins that manifest and
its verified counts. Normal operations additionally require a completed journal
record; a marker alone is not registration.

Restore/verify requests contain only `snapshot_id`. Restore targets are generated
fresh directories; users cannot nominate an overwrite destination. A restore
receipt pins the source manifest and restored counts. `restore-imported` request
data contains `source` and an independently trusted `manifest_sha256`. It accepts a
complete reviewed snapshot folder selected under the fresh instance's inbox. Its
snapshot ID comes from the pinned manifest; it is never automatically registered
or adopted into the new instance. The same portable paths, exact root inventory,
file hashes and completion-marker checks apply.

Each append-only event contains operation, actor, reason and data, inside a canonical
sequence/parent-hash payload. Operations are job started/completed/failed/interrupted
or hold changed. Replay validates exact types, order, parent hashes, request/result
pins, one pending job and legitimate terminal transitions. Filesystem work is never
performed during replay. A terminal-event slot is reserved before starting work.
The journal is an integrity check, not signed or immutable storage.

Hold changes require a registered snapshot and exact Boolean `hold`. Retention
policy has integer `keep_last` (1-16) and Boolean `protect_untested`. It rechecks
snapshot bytes, and matching registered restore drills when that proof is required.
Corrupt, missing, held, recent and unfinished-job records remain protected. Status
`candidate` is advisory; no deletion or space reclamation is implemented. Imported
recovery drills do not silently become registered-snapshot retention proof.

Reports bind the current head and exact Boolean quality/privacy/rights/context
checks. They contain metadata and individual manifest reports, not file payloads.
Export review does not authorize public publication. Index backups are metadata
only. Repeated reports and index backups are separate private artifacts.
