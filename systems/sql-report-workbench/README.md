# Offline SQL & Report Workbench

A complete local browser/CLI application for neutral SQLite snapshots, named query parameters, immutable query/report revisions, bounded owned workers, result history, report-field validation, local review, comparisons and checked private exports.

Selected owner-authored SQL masking/preflight code is retained from the original Developer Studio; the neutral runtime and browser application are new. Original business queries, reports, schemas, connections, saved passwords, runtime bundles and IDE/service launchers remain excluded. Runtime uses the Python standard library only, targeting Windows x64/Ubuntu x86_64 with CPython 3.12/3.13. No ODBC driver, database server, Qt runtime or report server is required or bundled.

## Start with a complete fictional workspace

From this directory choose a fresh private path outside the source checkout. It must not exist for `init` or `demo`.

```sh
python -B workbench.py --workspace ../fictional-sql-instance demo
python -B workbench.py --workspace ../fictional-sql-instance serve
```

Open the printed loopback URL. The demo materializes invented groups/items, runs joins and sums with bound values, validates a neutral report definition, records two query versions and four artifacts, compares previews, approves/exports one result, and verifies a database backup. Initial totals are alpha 8/beta 11; filtering quantities below 4 gives alpha 5/beta 11; a revised expression gives alpha 9/beta 12. No external system is contacted and no report is rendered.

For a blank instance, use `init` instead of `demo`, then `serve`.

## Browser workflow

1. Load or paste neutral dataset JSON and import it. The application creates its own immutable SQLite snapshot; it does not open existing operating databases. The schema view identifies the selected dataset and content hash.
2. Edit SQL, parameter types and a separate bindings JSON. Save a query revision before running. Saving performs preflight only. A changed draft must be saved or explicitly reloaded; stale revisions are refused without discarding drafts. New query IDs start new history.
3. Run the saved query against the selected snapshot. The owned worker returns at most 200 rows, explicitly marking truncation. Bindings are passed to SQLite, never interpolated into SQL. Cancel operates only on the application's owned worker. Editing another draft does not change an already captured request.
4. Import a supported offline Report XML definition. Inspect its dataset SQL and parameter/field mappings. **Validate saved report** checks the stored definition against the selected snapshot; XML draft edits take effect after saving. **Replace query draft with dataset SQL** is explicit and does not execute or save it.
5. Inspect a saved artifact, compare returned rows, then record quality/privacy/rights/context assertions. Each execution has a distinct artifact identity and begins pending, including identical reruns. Incomplete/failed/cancelled artifacts cannot be approved. Review is not authenticated identity or publication clearance.
6. Export an approved artifact inside the private workspace. A query export includes JSON, CSV and a bounded HTML preview; a validation export contains JSON and an HTML summary. The manifest is written last. Report findings remain findings even if an operator approves their review.

Result selection is separate from editor drafts. Loading a saved artifact or completing a new job replaces its review form; editor drafts remain separate. Unsaved drafts/notes are browser memory only. The report catalog retains extracted metadata/SQL and the source hash, not the original XML text. Keep the original private input if you need to revise it later. Historical query versions can be inspected through CLI; copy to a new query ID to run a fork rather than silently rebinding a stale revision.

## CLI

```sh
python -B workbench.py --workspace ../fictional-sql-instance datasets
python -B workbench.py --workspace ../fictional-sql-instance list --kind query
python -B workbench.py --workspace ../fictional-sql-instance show --kind query --id sample-summary --version 1
python -B workbench.py --workspace ../fictional-sql-instance history --kind query --id sample-summary
python -B workbench.py --workspace ../fictional-sql-instance artifacts
python -B workbench.py --workspace ../fictional-sql-instance backup
```

For a blank initialized instance, `import --file inbox/sample-dataset.json` and `save-query --file inbox/sample-query.json` use copied fictional templates. `save-query --expected` is required when revising an existing ID. `save-report` reads an explicit private file and requires `--source-sha`, `--id`, `--title` and optional expected revision hash. Its hash/path boundary adapts the authored report catalog method.

`run --file`, `validate-report --file` and `review --file` read JSON requests inside the workspace; [contracts](docs/CONTRACT.md) define exact fields. Request files keep values out of process command lines. `show --kind artifact --id`, `compare --left --right` and `export --artifact` use IDs returned by execution/history. No command automatically approves, publishes or replays a request.

Stop the server before another CLI command uses the instance. After an interrupted process, independently stop every process using that workspace, then:

```sh
python -B workbench.py --workspace ../fictional-sql-instance recover --confirm-stopped
```

Recovery removes only a verified empty session marker. It does not replay lost jobs or repair a damaged store. Ordered shutdown cancels and reaps owned work. A hard parent-process kill can lose an in-memory job; no active-write crash durability is claimed. State backups include definitions/artifacts/reviews but **omit SQLite snapshots, inbox and report files**. Retain the full private workspace for complete recovery.

## SQL, XML and resource boundaries

- The retained SELECT/CTE preflight is conservative text inspection, not a SQL parser or security boundary. It may reject otherwise valid SQL. Actual execution uses a separate process, read-only immutable SQLite connection, query-only mode, disabled extension loading, permitted-table/function authorization and bounded SQLite settings. Mutation, attachment, host/catalog introspection and unlisted functions are refused. SQLite syntax is not SQL Server compatibility.
- Workers use a 64 MiB SQLite heap limit, roughly two million VM steps in 1000-step checks, a two-second progress deadline and a four-second parent timeout with kill/reap. These are application controls, not a complete OS sandbox or a total process-memory quota. Trusted local storage/runtime remains required.
- Query preview: 200 rows, 32 columns, 4000 text characters per cell and 1 MiB encoded worker result. Blobs and nonfinite results are refused. A truncated preview is not a complete export or a complete comparison. No unordered-row equivalence or causation is inferred.
- XML: UTF-8 only, 512 KiB, 5000 elements, depth 40, bounded attributes/text. DTD/entity declarations, mixed element namespaces, known external binding/executable elements and unsupported parameter expressions are refused. Supported Report/RDL namespaces are a structural subset only. Inspection wraps dataset SQL with `LIMIT 0` and records a query plan; it does not render layout or validate the full report-server schema.
- Dataset: eight tables, 16 columns each, 1000 rows/table, 5000 total rows; bounded integer/real/text/null values. Inputs are at most 4 MiB, each generated snapshot 32 MiB, state database 64 MiB. Limits also cover document/revision/artifact/review counts; see [contracts](docs/CONTRACT.md).

Future SQL, literals/comments, bindings, table/column names, results, original-file hashes, reviewer notes, snapshots and backups can identify people or operations. They remain private. Known XML element rejection and CSV formula-prefixing are not universal credential detection, anonymization or spreadsheet guarantees. JSON retains original returned values. Actual exports require a separate content/rights review before sharing.

Read [design](docs/DESIGN.md), [validation](docs/VALIDATION.md) and [source origins](docs/ORIGINS.md). [MIT](LICENSE), copyright TheOutlandsDev. [Collection index](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/systems).

## Tests and reviewed source package

```sh
python -B -W error run_checks.py
python -B release_source.py check
python -B release_source.py package --output ../sql-report-workbench-source.zip
```

For browser acceptance, create/activate a separate development venv, then:

```sh
python -m pip install --require-hashes --only-binary=:all: -r requirements-browser.txt
python -m playwright install chromium
python -B -W error run_browser_checks.py
```

Ubuntu may need system libraries through `python -m playwright install --with-deps chromium`. Installation uses network access; application/demo do not need external services. Browser tests start fresh local instances and refuse external requests. Windows/Ubuntu CI requires native link fixtures and actual UI workflows; local filesystem skips are not passes. The focused source ZIP includes the exact manifest-pinned text files, excluding every private database, query history, report, screenshot and runtime/dependency binary.
