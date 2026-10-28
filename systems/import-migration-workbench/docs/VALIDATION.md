# Validation boundaries

Fictional core tests cover CSV multiline/BOM/header/width behavior, JSONL duplicate
keys and invalid numbers, explicit mappings, exact decimals, null/whitespace rules,
unknown-field accounting, key conflicts, deduplicated provenance, source/plan pins,
bounded rows/inputs, stale heads, competing requests, schema/hash/type tampering,
fixed-schema SQLite readback, repeat protection, partial failure, retained output,
private export hashes, display CSV escaping and metadata-only index backups.

An actual owned child is killed after a durable started event and partial output.
Tests require stale-session refusal, pending-job blocking, explicit stopped recovery,
retained partial bytes, no adoption/replay and unchanged fictional input bytes.
An additional test interrupts after a physical READY marker but before the terminal
journal event; that output remains unregistered. A lost completed response is
checked against history and exact-repeat refusal. These are controlled interruption
checks, not power-loss or storage-hardware evidence.

Seven native fixtures cover hardlinked input, metadata database, preview and
destination store; symlink input/parent; and a selected input-directory link. The
last uses a real Windows junction through PowerShell 7 or POSIX directory symlink.
Local filesystems may skip unsupported fixture creation. CI sets
`WORKBENCH_REQUIRE_LINKS=1`, requiring every native fixture to work and be refused.
Only the opposite-platform FIFO or stream-name case skips in the required matrix.

Actual Chromium workflows cover complete preview/import/verification/private export,
mapping edits, visible provenance/rejections, required review and rejection consent,
conflict/repeat blocking, changed sources, preview/store tampering, stale heads,
draft retention, review resets, failed reads, uncertain write response without retry,
literal markup, partial failures, history, narrow keyboard layout and owned shutdown.

The required Windows/Ubuntu Python 3.12/3.13 matrix also checks the full fictional
CLI demo, JavaScript syntax, source inventory, documentation and deterministic ZIP.
Before publication the exact ZIP must be extracted and walked through independently:
copied setup commands, normalization/provenance SQL oracles, report manifests, journal
backup replay, rejection/conflict/repeat boundaries and unchanged inputs. All four
CI source archive hashes must match the reviewed package.

No original importer, corpus, conversation, customer record, operating database,
source mapping, private endpoint, external service or real model is exercised.
Tests do not establish production suitability, semantic deduplication, hostile
concurrent filesystem resistance, encryption, signed attestation, atomic live-input
consistency, full disaster recovery or long-term/hardware reliability. All future
instance data and reports remain private.
