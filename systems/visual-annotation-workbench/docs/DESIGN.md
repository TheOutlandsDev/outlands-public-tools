# Design and thought process

Keep the visual review loop complete: import pixels, retain a proposal, edit class geometry, save correction, record review, partition related views together, and export exactly the approved latest state. A model is not needed to demonstrate or test that loop.

Public implementation is separate from private instance data. Fresh workspaces contain SQLite, canonical images, inbox, reports and backups. Existing public native I/O guards preserve Windows/POSIX protections. Outputs do not replace existing files or enter source/Git directories. An empty session marker detects normal concurrent instance use; recovery requires a stopped-process assertion without automatic replay or purge.

A narrow PNG decoder checks structure, CRC, dimensions, bounded decompression, filters and sample format. Canonical RGBA contains IHDR/IDAT/IEND only. Metadata removal retains supported raw sample values, without preserving colorimetric interpretation or anonymizing visible content. Unsupported variants are refused explicitly.

Independent binary masks preserve overlapping classes. Integer edges and exact rational scanlines make the convention reproducible. Tests use an independent point-in-polygon oracle and literal expected pixels. Zero denominator yields null IoU/Dice rather than invented perfect agreement.

Proposals and corrections have immutable versions and optimistic parent hashes. Review belongs to one version with its own optimistic counter. Later geometry never inherits approval. Immutable split policy groups specimen views; it cannot detect mislabeled duplicates or establish representative sampling.

Browser mapping uses the current canvas bounding rectangle to recover native pixel edges at any zoom/scroll position. Pointer drawing, vertex moves, coordinate entry, JSON editing and bounded undo share a draft. API refusal retains it; panels are temporarily inert during requests to prevent response-driven loss of concurrent edits. Reload explicitly discards the draft. Review/export require saved geometry. Undo is not persisted recovery state.

All API/image reads require a session token. Images use authenticated fetch and local object URLs. Root HTML supplies the token locally; it is not identity authentication or protection from a malicious local process. Host/Origin, no-store, CSP and loopback rules reduce accidental cross-origin access. Orderly shutdown waits for handlers. An application lock serializes export selection and commits. Append-only triggers and exact schema checks support consistency, not hostile-user security.

Reports are fresh directories with manifest last; failure may retain partial files. Imports may retain orphan immutable images after a later transaction failure. Database backups explicitly omit images. Retain the full workspace for recovery. Hostile filesystems/SQLite, crash-during-write durability, multiuser operation and production backup recovery remain outside acceptance.
