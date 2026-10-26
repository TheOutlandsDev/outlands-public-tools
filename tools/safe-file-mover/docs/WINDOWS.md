# Windows CLI and engine contract

This addition adapts only existing public MIT source and native file mechanisms.
It includes no original operational code/data, journal, runtime log, recovery
copy, game asset or third-party runtime. Python's existing `>=3.12.7,<3.13`
declaration remains. GUI, macOS, live network-share and power-loss acceptance
are separate from these local Windows CLI/engine fixtures.

## Paths, topology and selected objects

Windows paths are checked before normalization or resolution can erase their
spelling. Paths are bounded at 4,096 characters, 64 components and 255 characters
per component. Parent traversal, drive-relative/root-relative forms, device
prefixes including forward-slash spellings, alternate streams in ordinary path
arguments, reserved names and trailing dots/spaces are refused. UNC host/share
parts receive lexical checks too. Named streams are accessed only through their
separate validated manifest mechanism.

Observed ancestors use native metadata handles and normalized NT-volume names.
This avoids relying on DOS mount-name resolution. Each component must match its
parent's observed native name plus the selected component. Static drive aliases
use native-volume path keys for topology comparisons. Unsupported native names
or unusable identities fail closed; this does not certify drive/mount rebinding.
Remote-provider names are supported only when required metadata is available;
no real share was used or accepted by this review.

Reparse ancestors, junctions and unsupported reparse tags are refused. Controlled
symlink leaves are opened as reparse points and checked for the actual symlink
tag/name. They are copied as links without traversing targets. Windows directory
link recreation uses the link's own directory attribute rather than probing its
target, including dangling directory links. Link targets can retain private
names and can refer outside the selected tree; target contents are not included
in the link manifest.

Regular source opens use native no-follow handles and noninheritable binary CRT
descriptors, checking identity and observations around reads. Parent handles
remain during regular reads. Ordinary data writers are allowed by sharing;
size, identity and captured hashes detect observed changes. Sharing is per
stream, so holding the primary file does not freeze named-stream writers.
These are bounded observations, not an atomic snapshot or hostile-filesystem
sandbox. Data files may have multiple hard links; topology is not preserved.
The known same-file managed recovery case remains supported.

## Named streams and mutation boundaries

File and directory named `$DATA` streams are enumerated, hashed, copied and
verified. Names/types, controls, lengths, duplicates and sizes are validated.
Documented end-of-enumeration/no-stream status is distinct from unsupported or
failed enumeration; unsupported provider results are not silently treated as
an empty stream set. Enumeration closure failures also fail the check.

Hash/copy loops reject observed growth beyond the recorded stream size before
hashing or writing the excess chunk. Reads can capture up to a chunk beyond the
expected bound before refusal; they are not a blocked-I/O deadline. The original
bounded additive-stream rebaseline workflow remains, and changed existing bytes
do not qualify as additions. State, lock, rollback and reservation files must
not have named streams.

Copy bases and commit paths are rechecked at mutation boundaries. After the
pre-commit callbacks, source/staging or committed-destination/source checks run
again before Windows renames. Native no-replace rename retains its existing
nonreplacement flags. Existing conflicts are retained. Purge still re-verifies
the destination after its last callback; recursive removal first inspects
observed descendants for unsupported entries. External mutation can still occur
after a check. No fixture proves all-or-nothing recovery, power-loss durability,
application-consistent backup or safe movement of live application state.

## State, SQLite and cooperating processes

Choose an explicitly private local state directory. Windows rejects reparse
ancestors and requires ordinary single-link database, lock and reservation
files. Rollback-journal objects receive corresponding checks. WAL/SHM sidecars,
including empty ones, are refused; nonempty databases must have the supported
non-WAL header before SQLite opens them. Refused storage is retained. The tool
does not migrate, delete or repair unsupported journals to make a check pass.

SQLite pathname opening still follows sampled guards; these checks are not a
custom atomic VFS. Windows connections close explicitly if PRAGMA configuration
fails. Successful connections retain normal ownership, DELETE journaling and
the existing recovery schema. Cooperating processes use the existing byte-range
operation lock; it does not prevent an untrusted owner editing the journal.
Manifest hashes are not signatures or authorization.

Windows directory/database/lock/staging permissions inherit from their selected
parents. There is no POSIX 0700/0600 equivalent or full ACL/owner-confidentiality
audit. Existing POSIX ownership, mode, link and staging checks are preserved.
Basic source metadata may change final staging permissions; full ACLs, ownership,
sparse allocation and hard-link relationships are not preserved. Requested file
flushes do not prove directory-entry, controller or server persistence. Windows
directory flush behavior remains outside this implementation's guarantee.

## Privacy, execution evidence and remaining scope

Move, restore, abandon and purge intentionally change files; purge deletes
retained data. The tests use generated disposable trees only. Source/destination
bytes and allowed fixture mutations are verified; they are not all expected to
remain unchanged. All actual journals, logs and recovery copies stay private.

Valid CLI output, runtime errors and operation history intentionally retain paths
and operational details. Argument errors/static help preserve the existing
privacy boundary; the program is not an anonymizer or secret detector. Keep real
state, console captures and source/recovery data outside the public repository.
Unexpected runtime tracebacks can reveal additional local context.

The [Batch 23 review](../../../docs/BATCH-23-FILE-MOVER-WINDOWS.md) records
separate original/new-suite and fresh-process results. Windows CI requires real
hardlink/symlink/junction and original named-stream fixture execution; skips are
reported explicitly. No GUI, live SMB/provider or real-data test is implied.
Use stable trusted local inputs/parents and an independent backup for important
data. Neither matching hashes nor source publication establishes production
readiness, sharing rights or permission to act on someone else's files.
