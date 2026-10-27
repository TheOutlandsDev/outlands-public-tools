# Verified Transfers I/O checks

Python 3.12+, standard library only. On Windows keep `transfer.py` and
`transfer_windows.py` in the existing `tools/verified-transfers` layout; the
collection root is derived from that layout. POSIX does not load the Windows
backend. The backend retains this collection's public MIT native functions
and adds destination-location and streamed-creation adapters.

## Preserved formats and decisions

`reviewed-source-package-v1` and `opaque-data-handoff-v1`, manifest/checksum
serialization, external pin behavior, accepted pin case, inventory ordering,
limits, name/case-collision rules, source exclusions and UTF-8/BOM/NUL rules
are preserved. Source packaging copies only the explicit reviewed inventory;
unselected source files and control directories are not traversed or copied.
Payloads are never imported or executed.

The shared I/O helpers also serve private opaque backup/restore. Their stopped
assertions, optional verification pin, mandatory restore pin, format restrictions
and no-overwrite decisions remain. The stopped flag is an operator assertion,
not a process check. Synthetic round trips do not establish consistency for a
real application, database, service or backup.

The tool creates files. Destinations and required top-level parents must be
selected explicitly; the parent must already exist and the destination must be
new, outside the checkout and disjoint from the source. Only directories below
that new destination are created for payload paths. Existing destinations and
files are never replaced. No source data, old backup or partial output is deleted.

## Filesystem boundary

Windows rejects UNC/device, drive-relative, root-relative, alternate-stream,
reserved-device, invalid Unicode and trailing-dot/space paths before native
access. Native normalized names, identities, reparse attributes, types and link
counts supplement lexical checks. Existing ancestors of missing destinations
are checked without creating them. Native names check destination/source
separation and checkout exclusion. Observed short-name aliases and nonlocal
drive types are refused. These Windows path restrictions are stricter than the
previous metadata checks.

Checked native file/ancestor handles are retained during reads. A binary,
noninheritable CRT descriptor is matched with the native file identity. Root
and enumerated-directory scopes retain checked ancestors. New writes retain
checked parents and a validated creation descriptor. Selecting an ordinary
file neither reads nor changes its other streams; named stream arguments are
refused. Links/reparse points and hard-linked regular files remain unsupported.

POSIX retains available no-follow/nonblocking flags, rejects links/nonregular
files before opening, uses noninheritable descriptors, and resamples ancestor
identities. Reads are bounded to the applicable limit plus one byte and reject
observed early EOF, growth or identity/metadata changes. Text decoding remains
incremental, including BOM and split multibyte characters.

## Output verification and failure handling

All new regular files use exclusive creation. Short writes are completed;
zero/invalid writes fail. Written files are flushed, read back and compared
against the intended length and SHA-256 before success, with file/path identity
and link checks. File mode 0600 and directory mode 0700 are requested where
meaningful; encryption, source ACL preservation and Windows ACL privacy are
not established.

A read, text, hash, write, flush, verification or final-guard failure can leave
partial or complete **unconfirmed new** output. Keep it private for inspection;
existence, parseability or a manifest alone does not prove successful completion.
Retries require a different new destination. There is no automatic cleanup,
repair, merge, replacement, pruning or transactional rollback.

CLI failures retain fixed `TRANSFER_REFUSED_OR_FAILED`/exit 2 without input
paths or native error text. Windows help uses a fixed program name; handled
Windows interruption reports `TRANSFER_INTERRUPTED`/130 and retained partial
output. Library and POSIX interruption propagation remain. Native exceptions,
successful summaries, bundle filenames/hashes and manifests are private data;
they are not anonymized output or source-rights approval.

## Evidence and limits

The original 39 transfer methods remain unchanged, including fictional opaque
round trips and closed disposable SQLite bytes. New fixtures comprise 55
methods: 27 portable, ten POSIX and 18 Windows. Windows/Ubuntu Python 3.12/3.13
CI requires original native tests and additional hardlink/symlink/junction
cases; platform and optional short-name availability skips are recorded.

Local Windows/Python 3.12.7: original 37 passes/two unavailable native skips;
new 36 passes/19 skips (ten POSIX and nine unavailable native link cases).
Optional short-name rejection ran locally. A copied two-file runtime passed 24
fresh processes. Across 100 fictional source trees, result and bundle bytes
matched frozen public source, including cross-verification. Ten invented opaque
backup/restore round trips also matched. Runtime/input bytes stayed unchanged
without bytecode. Comparisons are retained privately with runtime hashes.
Exact-commit CI evidence is reviewed before merge.

Use one operator and quiescent trusted local trees. Sampled guards and retained
handles are not a content freeze, atomic multi-file snapshot, hostile-filesystem
sandbox or I/O deadline. Concurrent hostile mutation, drive rebinding, arbitrary
mounts, network/cloud providers, all-stream inspection, ACL privacy, power-loss
recovery and application-specific consistency remain outside acceptance.
No installed server/game, operational record or real backup is used for tests.

Real source inventories, package origins, records, credentials, deployment paths,
configurations, manifests, bundles, restores, logs, audit markers and captures
stay private. Hash agreement proves agreement with selected bytes, not authorship,
redistribution rights, absence of secrets or malware, or safe restoration.
