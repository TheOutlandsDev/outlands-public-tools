# Dataset Review JSONL I/O hardening review

Only existing public MIT review/native mechanisms and invented fixtures with
fresh disposable stores are selected. No actual dataset/store, reviewer, note,
provenance, credential, endpoint, operational configuration, original private
schema/helper, archive, corpus, capture, asset, DLL or third-party implementation
is exported. TheOutlandsDev remains the MIT identity; required notices, held
original rights and release assets remain unchanged.

Schema, selected-path/store connection/initialization, canonicalization, review
and listing remain preserved. Import parsing/normalization, approval/credential
checks, deduplication, provenance, aliases/holdouts, export fields/order/encoding/
hashes and size constants remain. The original combined 47-method regression
file, including 12 dataset methods, is unchanged. SQLite database/journal/WAL/
sidecar lifecycle retains its existing trusted-store/one-operator scope.

JSONL gains bounded ordinary-file reads before import store access, exclusive
guarded writes, requested flush and readback comparison after the connection
closes. POSIX uses available no-follow/nonblocking guards. Windows uses native
name/reparse/identity checks and observed output/repository overlap refusal.
Source hard links remain supported; output extra links fail. Failed output is
retained unconfirmed. Windows CLI interruption gains fixed error/130; API and
POSIX interruption behavior remain preserved.

Local Windows/Python 3.12.7: 12 original methods passed; new 40 methods had
27 passes/13 skips (eight unavailable native link/junction cases and five
POSIX-only methods). Local short-name rejection ran. Windows/Ubuntu Python
3.12/3.13 CI requires native links/junctions; optional short-name/platform
availability is explicit. Other versions remain unverified. Exact-commit
walkthrough/CI/publication evidence is recorded separately.

A separately copied two-file package passed 28 fresh processes (24 direct CLI,
four controlled write/flush/read/interruption cases). Against a hash-verified
frozen public baseline, 100 fictional fresh-store workflows matched returned
results, logical SQL rows and exact export bytes. Generated review timestamps
were excluded from equality and validated as UTC. Source/runtime bytes stayed
unchanged without bytecode. Local combined regression: 46 passes/one native-
symlink skip; collection: 532 passes/27 skips; documentation/JSON: 447 passed.

Publication uses selected-byte hashes, independently frozen/current public
auditors, private markers and manual review. Generated stores, JSONL, exports,
SQL snapshots, mappings, logs, reports, captures and ledger remain private.
Read the [JSONL I/O contract](../systems/dataset-review/docs/JSONL-IO.md).

Sampled checks require stable trusted local parents. No atomic/hostile database
or filesystem boundary, total resource quota, hardware/power-loss durability,
whole-store backup or complete secret/IP clearance is supplied. Approval does
not independently authorize public sharing.
