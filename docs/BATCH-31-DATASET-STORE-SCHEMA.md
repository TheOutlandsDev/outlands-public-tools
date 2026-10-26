# Dataset Review store/schema hardening

Only existing public MIT mechanisms, SQLite standard-library APIs and invented
stores are selected. No actual database, schema from a held system, dataset,
reviewer, credential, endpoint, configuration, archive, corpus, capture, DLL or
third-party implementation is published. TheOutlandsDev remains the MIT identity;
required notices, held original rights and release assets remain unchanged.

The public canonical schema and record/review/deduplication/provenance/holdout/
export algorithms stay unchanged. Canonical unversioned rollback-journal stores
are accepted without migration/stamping. Strict store paths, single-link policy,
sidecar/WAL refusal, exact schema/metadata checks and stored FK consistency are
new acceptance requirements. Custom/equivalent DDL and foreign version markers
are refused explicitly. Existing data is not repaired, converted or overwritten.

Stores gain retained file/parent guards, bounded header checks, read-only
preflight and repeated validation before writable application access. Trusted
in-memory DDL defines the reference; selected schema SQL is never executed by
the application. Initialization is exclusive with transactional DDL and retained
unconfirmed output on failure. SQLite owns its handles/locking; supported engine
configuration and validation progress limits are checked separately.

Local Windows/Python 3.12.7/SQLite 3.45.3: original 12 methods passed; JSONL
40-method suite had 27 passes/13 skips; schema 41-method suite had 28 passes/
13 skips. The skips in each suite are eight unavailable native link/junction
cases and five POSIX-only methods. Local short-name rejection ran. Windows/
Ubuntu Python 3.12/3.13 CI requires native links/junctions with optional aliases/
platform skips explicit. Other runtime builds remain unverified.

The old JSONL tests keep their expected behavior; descriptor instrumentation now
selects the export path so added store descriptors do not masquerade as output
descriptors. The original combined 47-method regression file remains unchanged.
Exact-commit walkthrough and publication evidence are reviewed separately.

A copied three-file package passed 33 fresh processes (28 direct CLI, five
controlled failures). A hash-verified frozen initializer seeded 100 legacy
stores: new/old workflow results, logical SQL rows and exact export bytes matched.
Generated review timestamps were excluded from equality and validated as UTC.
Source/runtime bytes stayed unchanged without bytecode. Local combined suite:
46 passes/one native-symlink skip; collection: 532 passes/27 skips; documentation/
JSON: 449 checks passed.

Read the [store/schema contract](../systems/dataset-review/docs/STORE-SCHEMA.md).
Actual stores/sidecars, generated fixtures, SQL snapshots, reviewer/provenance
records, logs, reports, markers and captures stay private. Publication uses exact
hashes, independent frozen/current auditors and manual content review.

These are sampled checks for one operator on quiescent trusted local storage,
not hostile-database/VFS protection, recovery, full forensic validation, total
resource quotas or power-loss acceptance. Approval and structural validity do
not independently establish sharing rights, anonymity or secrecy.
