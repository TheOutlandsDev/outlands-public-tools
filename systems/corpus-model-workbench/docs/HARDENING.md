# Corpus and Model Workbench hardening

This pass changes the existing public application only. It adds newly authored
source and fictional tests. No original private implementation, instance,
configuration, corpus, conversation, credentials, paths, operational benchmark,
model file or third-party asset was selected or opened for the implementation.
Existing public source origins and MIT notices are preserved.

## Content and compatibility

Approvals require exactly four boolean checks plus a bounded reviewer and note.
Each new approval records a materialized-message hash in its existing review JSON.
SFT export requires the latest approval hash to match the currently materialized
messages. Changed, missing, over-limit or previously unpinned content is skipped
with a fixed reason. Review the current context again to authorize a new export.
This leaves the schema and record IDs unchanged. It does not recall old exports.
RAG documents retain their immutable stored text and current review/split checks.

Loading benchmarks applies exact prompt holdouts to existing records and their
linked groups. Both import orders are tested. Embeddings already in the database
cannot bypass a later review revocation or holdout promotion during retrieval.
This is exact matching, not semantic leakage or privacy detection.

JSONL provenance hashes and parsing use the same bounded input bytes. Gzip source
hashes identify the compressed input. Strict message shape and count checks stop
malformed input transactionally. Materialization limits apply with or without
supplemental context. Failed buffer construction writes no successful manifest or
export event. A later write failure may leave a partial private new directory.

## Windows, POSIX and service lifecycle

Existing native no-follow/reparse, single-link and exclusive-output helpers are
unchanged. Added native fixtures cover workspace metadata hard links and linked
export parents (Windows junctions, POSIX directory symlinks). Existing fixtures
cover input/database links, ancestors, special files and stream selectors.

Missing schema-version metadata yields a fixed refusal. Model catalogs require
bounded unique names, digests and object shapes before database changes. Models
and their digests remain caller-provided declarations, not independent proof.

The UI keeps Host, token, Origin, escaping and no-store protections. It rejects
ambiguous POST framing, uses bounded socket reads, and sends no-referrer. Lost
write responses and unknown jobs require explicit reload/reconciliation; browser
code does not automatically repeat a mutation. Normal stop refuses active jobs.
Ctrl+C drains owned background jobs while retaining the instance lock. This can
wait for bounded backend operations; it does not cancel inference on a backend.
A forced kill leaves a stale lock and unfinished database runs for manual recovery.

## Acceptance boundary

The real Chromium suite covers empty-store import, benchmark ordering, all review
checks, context display, approval/revocation, separate SFT/RAG/review exports,
independent file hashes, backup, model comparisons/manual scores, discussions,
pending generated candidates, embedding/search revocation, literal markup,
invalid input, reload, lost response, busy jobs and narrow layouts. Every fixture
and model response is invented. No network request to an actual model is made.
This proves application orchestration and UI behavior, not inference quality,
training, production hosting, hostile storage or real-data migration.
