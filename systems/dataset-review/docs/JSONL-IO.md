# Dataset Review JSONL I/O contract

Python 3.12+, standard library only. Keep `review_io_windows.py` beside
`review_store.py` in the existing `systems/dataset-review` repository layout;
all platforms also require `review_store_guard.py` for store acceptance.
The existing `PACKAGE` calculation defines this package's output exclusion root.
POSIX JSONL I/O does not need the Windows backend.

## Preserved rules and scope

Canonical schema, canonicalization, review,
listing, credential guard, four approval assertions, exact deduplication,
provenance, group aliases and strongest holdout rules are preserved. Import row
parsing/normalization, pending status, export filtering/fields/order, UTF-8/LF
bytes and expected hash summaries remain. The original combined 47-method
regression file is unchanged, including all 12 dataset methods.

The earlier JSONL update preserved SQLite lifecycle code. Current store opening/
initialization is governed by the [store/schema contract](STORE-SCHEMA.md):
canonical sidecar-free rollback-journal stores are checked without migration,
while WAL/recovery/custom-schema states are refused. The 64 MiB pre-operation
size check remains. JSONL data handles are not held across store connections;
new store metadata handles are. Hostile-database, multi-user, full recovery and
whole-store backup acceptance remain outside scope.

## Import and export

Imports check ordinary stable files before/during/after bounded reads, before
existing parsing or import store access. The 4 MiB input and 64 KiB normalized
record limits remain. BOM/blank-line handling, row numbering, raw-byte hashes,
JSON decoder behavior, text normalization and group/split rules are preserved.
No new JSON constant/duplicate-key policy is introduced. Short reads complete
or fail; early EOF, growth and observed same-size mutation fail. One excess
rejection byte can be consumed; excess is not parsed. Source hard links remain
allowed. Observed links/reparse paths, special files and traversal components
are refused. Inputs are not modified/executed; reads can affect access metadata.

Export collection uses the existing connection, which closes before writing.
The encoded 16 MiB limit remains. An existing private parent outside `PACKAGE`
is required; parents are not created. New files use exclusive creation,
short-write progress handling, requested flush and observed ordinary-file
identity/name/size/link-count checks. Bytes are read back and compared before
success. Empty exports remain new empty files; output must retain one hard link.
Existing entries are never replaced.

Failure/interruption retains partial or complete-looking unconfirmed output.
No automatic recursive cleanup/rollback occurs. Parsable JSONL, matching hashes
or approved records do not prove command success or authorize sharing. Review
retained output privately before retrying with a new destination. Flushes do
not promise parent-directory, hardware/power-loss or multi-file durability.

## Platform checks

POSIX adds available no-follow/nonblocking flags, noninheritable descriptors,
ancestor/link checks and sampled file/path identity checks. New files request
0600; OS permissions/ACL confidentiality still need separate review. Repository
containment is lexical plus sampled link checks, not mount/bind-alias protection.

Windows adapts public native local-volume/path/reparse/name checks and retained
handles with binary CRT descriptor comparison. Preflight and actual write scope
compare normalized native output/repository names to reject observed aliases.
These checks cover JSONL output, not SQLite store/sidecar paths. UNC/device/ADS
forms, drive/root-relative spellings, traversal, reserved names, trailing dots/
spaces, invalid controls, surrogate text and observed short-name aliases are
refused. Bounds: 4,096 characters, 64 components, 255/component; local fixed/
removable volumes only. Use fully spelled private paths. Relative child paths
remain supported. Named streams, ACLs, ownership and full metadata are outside
read/backup scope. Windows confidentiality depends on inherited OS/Python ACL
behavior and is not audited by Unix mode arguments.

API interruption propagates while owned resources close. Handled Windows CLI
interruption returns 130 with `ERROR` / `REVIEW_OPERATION_INTERRUPTED`; POSIX
CLI interruption behavior is preserved. Other CLI failures retain fixed
`REVIEW_OPERATION_FAILED` / exit 2 without exception values or paths. Successful
results still carry private IDs/groups/hashes. Fixed errors do not anonymize
caller tracebacks or retained exception objects.

## Evidence and limits

Only fictional JSONL and fresh disposable stores are used. Local Windows/Python
3.12.7: 12 original methods passed; new 40 methods had 27 passes/13 skips
(eight unavailable native link/junction cases and five POSIX-only methods).
Local short-name rejection ran. Windows/Ubuntu Python 3.12/3.13 CI requires
native Windows links/junctions and reports optional short-name/platform skips.
Other versions remain unverified. CI uses canonical temporary parents without
relaxing alias checks. Exact-commit evidence is reviewed separately.

A separate two-file package passed 28 fresh processes (24 direct CLI, four
controlled failures). A hash-verified frozen public baseline matched 100
fictional fresh-store workflows: returned results, logical SQL rows and exact
export bytes. Generated review timestamps were excluded from equality and
validated as UTC. Source/runtime bytes stayed unchanged without bytecode.
Local combined regression: 46 passes/one native-symlink skip; collection:
532 passes/27 skips; documentation/JSON: 447 passed.

Actual stores, imports, reviewers, notes, provenance, exports, mappings, markers,
reports and captures remain private. Approval assertions do not independently
establish rights, anonymity, correctness or secrecy. Only a separately reviewed
export may be shared. No original private schema/helper/archive/corpus is bundled.

Stable trusted local parents/storage and one operator remain required. Checks
are sampled with pathname/open windows, not atomic snapshots or hostile VFS
boundaries. Drive-map rebinding, hostile mutation, live/remote/cloud providers,
blocking I/O/database calls, power loss, total CPU/memory/time quotas, full
backups and complete secret/IP clearance remain outside acceptance. No deadline
covers every filesystem or database call.
