# Design and source methodology

Retain the authored workflow where useful: mask literals/comments for conservative query preflight, browse report datasets, verify source hashes and separate validation from execution. Replace the operating bindings with a neutral snapshot contract and a complete local browser/CLI application. Original IDE launchers, report upload, ODBC connections, credential retrieval, generated operating catalogs and business queries stay outside selection.

## Separate database state from query targets

The state database holds immutable definitions, revisions, artifacts and reviews. Query workers never open it. Dataset JSON materializes an independent SQLite snapshot with validated identifiers and bound inserted values. It contains only caller-declared ordinary tables; no input database, trigger, view or executable object is imported. Random snapshot paths prevent failed imports blocking a later explicit retry. A later state-budget failure can leave an orphan snapshot, which remains private for manual review.

Dataset/source hashes, file hashes and native single-link/reparse/symlink checks support consistent selected inputs. They are not signed provenance or protection against a hostile process rewriting the private filesystem. Runtime behavior requires trusted local storage and a supplied SQLite build with the required controls.

## Defense in layers for SQL

The two retained preflight functions are unchanged authored source. They understand escaped single quotes, line comments and nested block-comment masking, then conservatively reject non-SELECT/CTE, stacked and mutation-looking text. This is not a complete parser; SQLite has different comment/dialect rules and benign identifiers can be rejected. It is never the sole read-only boundary.

An isolated standard-library child opens only the generated snapshot with read-only/immutable URI flags, query-only mode and disabled extension loading. A deny-by-default authorizer permits SELECT/recursive processing, reads of registered snapshot tables, and a small function allowlist. SQLite may report a null database name for a registered table when no column is read, including `COUNT(*)` and unused join columns; that case is allowed only for the same registered tables. Catalog reads, attachments, mutation and unlisted functions remain denied. See the [primary authorizer API](https://www.sqlite.org/c3ref/set_authorizer.html).

Lowered expression/column/SQL/variable/function/bytecode limits, a 64 MiB SQLite heap limit, progress-step/time checks and bounded fetch/output reduce resource use. The parent uses a four-second communication deadline, then kills and reaps a stalled owned child. Cancellation never accepts a caller PID or command. Ordered shutdown cancels and joins owned work. The child is not a full operating-system sandbox; Python overhead, OS scheduling and hostile/shared filesystem races are outside a total-memory/time guarantee. No arbitrary Python, shell, plugin, extension or provider execution is offered.

Parameter definitions and values stay separate. The [Python SQLite binding interface](https://docs.python.org/3/library/sqlite3.html) passes a dictionary rather than SQL string interpolation. Query results preserve duplicate column labels through ordered arrays. Truncation is explicit and never promoted into a complete-result claim.

## Offline report scope

Parse UTF-8 XML only after rejecting DTD/entity declarations. Bound raw size, nodes, depth and text, reject mixed element namespaces and known external/executable elements, then extract dataset SQL, explicit parameter links and ordered fields. Unknown layout content is not rendered or executed; extraction is not a general secret scanner or full RDL schema validator.

Validation wraps each saved dataset query with `LIMIT 0` and records an SQLite query plan in the same controlled worker. This checks the declared output-column contract, not layout, provider compatibility or a live report server. Query transfer from the catalog to the editor is an explicit unsaved draft, preserving the authored browse/send pattern without automatically executing anything.

## Review and reports

Revision hashes bind content and parents. Every execution gets a separate artifact identity so a prior approval cannot transfer to an identical rerun. Optimistic review counters refuse stale writes. Approval is a local assertion about the current immutable artifact, distinct from technical validation results or publication permission.

UI state keeps editor drafts separate from saved results. Failed saves retain drafts; starting a job captures the saved revision and bindings. Callers are rendered as literal DOM text, not HTML. Exports carry JSON with exact returned values, a formula-prefixed CSV preview and an escaped bounded HTML summary. Header/cell prefixing reduces common spreadsheet formula interpretation but does not anonymize or guarantee every spreadsheet behavior. Manifest-last output exposes partial failures without purging evidence.

The source release contains code, invented templates, tests and notes only. Private workspace records, snapshots, result exports, local screenshots, runtime dependencies and original business material never enter the source manifest. Required public catalog updates are separate from older immutable toolkit downloads.
