# Dataset Review store/schema acceptance

Python 3.12+, SQLite 3.33+ and standard library only. Keep `review_store.py` and
`review_store_guard.py` in the existing `systems/dataset-review` layout; Windows
also needs `review_io_windows.py`. No installer, migration or recovery service
is added. Only existing public mechanisms and generated fictional stores are
selected; actual databases, records and credentials stay private.

## Compatibility contract

The original public schema, canonical record/JSONL format, review assertions,
credential guard, exact deduplication, provenance, aliases, holdouts and export
rules are preserved. Original unversioned stores created by that implementation
remain supported when they use the canonical DDL, zero `user_version` and
`application_id`, ordinary single-link files, rollback-journal header format,
and have no journal/WAL/SHM sidecars. No format stamp or migration is written.
Independent SQLite backups retaining that format are accepted.

This is deliberately strict acceptance, not equivalence inference: hand-edited
or reconstructed DDL, extra indexes/statistics/tables/views/triggers, altered
columns/defaults/constraints, foreign version markers and stored foreign-key
violations are refused. Even semantically equivalent custom DDL can be refused.
Malformed/unsupported files are not repaired or overwritten. Extra hard links,
parent traversal, observed symlink/reparse/short-name aliases and repository
output aliases are refused under the documented platform path rules.

Any existing `-journal`, `-wal` or `-shm` entry is refused before SQLite opens
the main file, without following/deleting/replaying it. WAL header mode is also
refused before opening: read-only SQLite can create WAL sidecars. No automatic
checkpoint, journal-mode conversion or recovery is attempted. Stop all other
operators and preserve affected files for a separately authorized recovery.
These restrictions are explicit compatibility changes for previously unchecked
store states, not changes to record/review policy.

## File and connection checks

The store must be outside `PACKAGE` with a stable existing parent. New files
are created exclusively, requesting mode 0600 where meaningful, with no
replacement or automatic cleanup. Creation identity is checked before SQLite
initialization. DDL runs inside an explicit transaction; ordinary SQL failure
rolls it back and leaves a new unconfirmed file. Interruption after commit can
leave a valid-looking unconfirmed store. File existence never proves init
success; an existing file cannot be silently reinitialized.

POSIX uses available no-follow/nonblocking flags, checked ancestors and a
retained noninheritable read descriptor. Windows retains checked parent/native
main-file handles, requests attributes for its primary main-file handle and
compares it with a binary CRT descriptor. SQLite retains its own handles and
locking. Legitimate file size/time changes are permitted; observed identity,
name, type and link-count changes fail. Root/parent/name checks are sampled,
not a custom SQLite VFS or write freeze. Existing ACLs are not modified/audited.

The first 100 header bytes are checked before SQLite access. The existing
64 MiB pre-operation limit remains, not a hard storage quota. Existing stores
are first validated through `mode=ro`/query-only, then validated again through
`mode=rw` before application SQL. Read-only metadata checks do not import,
evaluate or execute selected schema SQL as application code; SQLite itself
still parses database metadata.

Loadable extensions are disabled when the API exists, `trusted_schema` is off,
foreign keys are on, and defensive configuration is enabled where available.
An in-memory reference executes only the bundled trusted schema. Declared
objects/DDL and table/foreign-key/index metadata are compared with that reference;
root page numbers are not compared. Selected schema SQL is never passed to
`executescript`. Object/SQL/metadata results are bounded. Validation uses a
SQLite VM progress budget of 100,000 callbacks at 1,000-opcode intervals, removed
after validation. This is not a native I/O, parser, memory or wall-clock quota.

## Evidence and practical limits

Local Windows/Python 3.12.7/SQLite 3.45.3: the original 12 dataset methods passed;
the retained JSONL suite had 27 passes/13 skips from 40 methods; new schema
suite had 28 passes/13 skips from 41. Each local suite's skips comprise eight
unavailable native link/junction cases and five POSIX-only methods. Local
short-name rejection ran. Windows/Ubuntu Python 3.12/3.13 CI requires native
links/junctions and reports optional short-name/platform availability. Other
versions/builds remain unverified. Exact-commit evidence is reviewed separately.

A copied three-file package passed 33 fresh processes (28 direct CLI, five
controlled failures). Against a hash-verified frozen public initializer, 100
legacy-seeded workflows matched returned results, logical SQL rows and export
bytes. Generated review timestamps were excluded from equality and validated
as UTC. Source/runtime bytes stayed unchanged without bytecode. Local combined
suite had 46 passes/one native-symlink skip; collection had 532 passes/27 skips;
documentation/JSON checks: 449 passed.

All actual stores, sidecars, records, reviewer identities, provenance, exports,
logs, markers, reports and captures remain private. Fixed CLI failures remain
`REVIEW_OPERATION_FAILED`/2; Windows handled interruption remains the recorded
fixed error/130. Library/POSIX interruption semantics and JSONL I/O rules remain.
Public sharing still requires a separate exact export/content/rights review.

One operator and quiescent trusted local storage are required. Concurrent
writers, hostile path or file mutation, drive rebinding, live/remote/cloud
providers, damaged-database recovery, full page/content/forensic validation,
backups, power loss and complete secrecy/IP clearance are outside acceptance.
Post-operation failure can follow committed changes; no multi-file or hardware
atomicity is promised. This is not a hostile-database sandbox.

Primary behavior references: [SQLite schema table](https://www.sqlite.org/schematab.html),
[PRAGMA settings](https://www.sqlite.org/pragma.html),
[database header](https://www.sqlite.org/fileformat.html) and
[Python SQLite API](https://docs.python.org/3.12/library/sqlite3.html).
