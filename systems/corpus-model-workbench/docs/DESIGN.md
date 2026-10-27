# Implementation and methods

The original authored corpus engine, model workflow, relational schema and
browser interface form one application. New instance bootstrap and guarded file
boundaries separate this reusable implementation from actual operating data.

## Data flow

1. Create a new private workspace with neutral settings and invented fixtures.
2. Load declared benchmark cases, then import explicitly selected JSONL or gzip
   JSONL. Normalize messages, deduplicate exact canonical content and retain
   source hashes plus row provenance. No directory discovery or original-data
   migration runs automatically.
3. Link duplicate conversation groups, promote linked splits toward test, and
   put exact benchmark prompts in test. Pending records require four human checks.
4. Search with SQLite FTS5. Review records with a reviewer and evidence note.
   Materialized context reads only explicitly referenced private instance files.
5. Export approved examples to separate SFT split files, approved train documents
   to RAG, or pending records to a review queue. Include file hashes and provenance.
6. Optionally discover models from an explicit loopback service, pin reported
   digests, compare identical benchmark requests and record timing/completion.
   Quality scores remain manual. Routing requires at least three distinct scored
   cases by default; a completed inference is not evidence of correctness.
7. Planner, coder and reviewer roles exchange bounded text. Model critique is
   labelled unverified. No tools or code execution are enabled. Completed answers
   return to the pending corpus review queue, not directly to training exports.

## Boundaries

`workbench/corpus.py` retains corpus/review/export algorithms;
`workbench/models.py` retains model comparison and discussion logic;
`workbench/schema.sql` retains the relational/FTS5 schema;
`workbench/ui.html` and `web.py` expose the local review workflow.
`runtime.py` supplies explicit instances, canonical schema checks, bounded I/O,
exclusive writes, serialized database operations and the loopback model client.
The source packager verifies its own selected source inventory.

New files use reviewed first-party Windows/POSIX helpers. Windows handles check
reparse points, hard links and file identity; POSIX uses no-follow guarded opens
and ancestor/identity checks. Existing SQLite stores must have the exact trusted
schema, single-link ordinary file metadata, rollback-journal headers, no sidecars
and the expected version. Nested reads reuse the same transaction. SQLite
extensions are disabled. A known schema does not prove that stored data is safe.

The model client has three allowed endpoints, literal loopback destinations,
disabled proxies/redirects, bounded requests/responses, finite bounded vectors
and a configurable timeout. The browser API checks Host, a random session token
on reads and writes, and Origin on writes. Error responses use fixed codes.
The original escaped rendering remains; required inline scripts/styles remain
in the local UI's content security policy.

## Explicit limits

Each input/export buffer is at most 16 MiB, JSONL rows at most 1 MiB and imports
at most 10,000 physical lines. JSON depth is limited to 64; duplicate keys,
invalid UTF-8 and non-finite numbers are refused. Gzip decompression is bounded.
Model JSON responses are at most 2 MiB and requests at most 1 MiB. Native store
guards cap SQLite files at 64 MiB; backup hashing currently uses the 16 MiB read
cap, so larger backups may remain private without a success receipt. Exports
can leave incomplete new folders on failure; inspect or retain them for recovery.

Store contents, context, metadata and exports are private and can contain any
operator-supplied text. Pattern flags are limited heuristics, not a sanitizer.
SFT holdout exports exist for evaluation; only train files should feed training.
Context reconstruction excludes tool messages and does not prove completeness.
Import selection hashes and parsing are separate guarded reads, not a snapshot
against concurrent writers. Keep inputs and all ancestors stable and trusted.

Single operator, trusted local storage only. No multiuser authorization, secure
erasure, hostile-filesystem race guarantee, hostile SQLite acceptance, inference
sandbox, actual training, real-model quality measurement, power-loss proof or
production deployment is claimed. The standard-library HTTP server is for local
use. Stop jobs before leaving the application; interrupting may require recovery.
