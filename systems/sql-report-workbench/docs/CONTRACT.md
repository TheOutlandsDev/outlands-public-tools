# Data, revision, execution and export contracts

## Neutral dataset

Exact fields: `format`, `dataset_id`, `title`, `tables`. Format is `outlands-sql-dataset-v1`. IDs are portable ASCII tokens beginning with a letter, at most 64 characters, excluding reserved Windows device names/trailing dots. SQL identifiers are lowercase letters/digits/underscore beginning with a letter, at most 48 characters; the `sqlite_` prefix is reserved.

Each table has `name`, `columns`, `rows`. Columns have exactly `name`, `type`, `nullable`: unique names, integer/real/text types and strict Boolean nullability. Rows are arrays matching the declared column count. Integers are strict integers in ±10^12; reals are finite numbers in the same range and normalize to float; Booleans are not numbers. Text allows 1000 characters with tab/newline but no other ASCII controls, and must encode to UTF-8. Each canonical row is at most 8192 bytes. Null requires a nullable column.

Limits: eight tables, 16 columns/table, 1000 rows/table and 5000 total rows. Tables sort by name; column and row order remain significant. Canonical JSON uses ASCII escapes, sorted keys and compact separators. Existing dataset IDs are immutable; identical content is idempotent. Snapshot files are created from this contract only, with tables and inserted values but no views, triggers or external bindings. State records bind the dataset JSON hash and the generated file hash. Physical SQLite bytes may differ between platforms; each instance verifies its own exact file before execution.

## Query and report revisions

Query definition fields: `format`, `query_id`, `title`, `sql`, `parameters`; format is `outlands-sql-query-v1`. SQL is at most 16 KiB UTF-8. Parameter definitions exactly match named colon placeholders outside masked strings/comments, up to 32; types are integer/real/text. Values may be null; otherwise they must satisfy their declared type. Positional, `@` and `$` placeholders are outside this subset. Bindings must contain exactly the declared names; no coercion/interpolation occurs.

Save-query request: `definition`, `expected_sha256`. For a new ID the expected hash is null. For an existing ID it must match latest. Identical latest content is idempotent. Each changed revision binds kind, definition, parent hash and version; maximum 200 versions per ID and 100 IDs per document kind.

Save-report request: `report_id`, `title`, `xml`, `expected_sha256`. The bounded inspector accepts the neutral `urn:outlands:offline-report:v1` namespace and declared 2008/2010/2016 RDL report-definition namespaces, with one Report root and same-namespace elements. Report parameters support Integer/Float/String. Dataset queries use Text commands, named placeholders, explicit parameter links of the form `=Parameters!name.Value`, and ordered Field/DataField mappings. Other expressions, defaults, known external bindings/executable elements and unsupported types are refused. This is not full RDL conformance. The stored revision contains extracted data and the original byte hash; source XML stays out of state/export.

File-based report import additionally requires an explicit expected source hash. It checks native-guarded path containment and bytes before decoding, adapting the original authored boundary. A supplied hash proves equality with the caller's pin, not source authenticity or permission to share.

## Jobs and artifacts

Run request: `query_id`, `expected_query_sha256`, `dataset_id`, `expected_dataset_sha256`, `bindings`. Latest revision and immutable dataset pins must match before starting. Report-validation request substitutes `report_id`, `expected_report_sha256` and binds every report parameter. These requests capture immutable definitions and values before background execution; later editor changes cannot alter the captured job.

One active job per instance. An owned child receives validated control data through a private pipe, not command-line values. Query status is completed/refused/budget_exceeded/cancelled. Completed previews contain ordered columns/row arrays, an explicit truncation flag, and execution scope. Report inspection uses zero-row wrapping and a bounded plan; declared fields must exactly equal inspected output columns in order. Validation completes with `valid: true/false`; completing inspection does not imply the fields passed or a report rendered.

Each completed job attempt creates a distinct random artifact ID bound into its payload/hash, even for identical requests/results. Runs therefore never inherit another run's approval. Failed/cancelled artifacts retain fixed reasons without raw database errors, host paths or worker stderr. At most 200 persisted artifacts and 20 recent in-memory job records are retained; completed in-memory records may expire, while persisted artifacts remain. Losing a process can lose an unfinished job without replay. Partial snapshots/reports can remain after later failures; new random paths allow an explicit retry without replacement or automatic deletion.

## Review, comparison and export

Review fields: `artifact_id`, `artifact_sha256`, `expected_version`, `status`, `actor`, `note`, `checks`. Status is pending/approved/rejected; checks are strict Booleans quality/privacy/rights/context, all required for approval. Only completed artifacts can be approved. A completed validation with findings may be reviewed, but `valid: false` remains in the artifact/export. Reviewer identity/rights are unverified assertions. Stale hashes/versions refuse writes; row version begins at zero and review records append only, with 5000-record limit.

Comparison requires two completed query artifacts. It reports query/dataset/binding equality, ordered columns/rows and returned counts. `comparison_complete` is false if either preview is truncated. Different row order, inputs or bindings are not a causal interpretation.

Approved query exports have six payload files plus manifest; validation exports have five payload files plus manifest. `outlands-sql-export-v1` binds artifact, review version, kind, truncation/validation status and per-file bytes/hashes; `public_release_authorized` is false. HTML is escaped and bounded to an explicitly labeled twenty-row sample with text clipping; JSON/CSV retain returned preview values. CSV prefixes strings beginning with formula markers (after whitespace) or tab/newline with an apostrophe; null becomes an empty CSV field while JSON preserves null. This is not universal spreadsheet safety.

The manifest is written last in a new private directory. Existing files are never replaced; failed exports retain partial files. State backups omit snapshot/inbox/report files and are not full-instance recovery. Runtime input/output limits and schema/hash checks are consistency controls, not hostile-local-user security or disclosure clearance.
