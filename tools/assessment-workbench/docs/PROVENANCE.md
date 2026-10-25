# Provenance and licensing

The workbench is fresh neutral code implementing local record editing,
persistence and history over an already public record contract. It does not
export the held assessment application, its private schema, records, operational
configuration or evidence. No held application source or data was read or copied
for this implementation. The private source family remains outside this review.

`record_contract.py` bundles the public checker from
[Assessment Record Contract Checker at commit 2dff9246054e4ad6c9bf59b91d6d9fa3b2cbcf67](https://github.com/TheOutlandsDev/outlands-public-tools/blob/2dff9246054e4ad6c9bf59b91d6d9fa3b2cbcf67/tools/assessment-record-checker/assessment_check.py).
Its source path is `tools/assessment-record-checker/assessment_check.py`. That
code is original public MIT material attributed to TheOutlandsDev. Bundling
keeps this app standalone without importing a selected project or private schema.
The empty-workspace allowance belongs to the workbench wrapper, not the checker.

The bounded JSON reader and private-path patterns adapt reviewed public code.
The CLI, desktop, persistence, tests and fictional demo are selected original
material under [MIT](../LICENSE), attributed to TheOutlandsDev. This grant does
not relicense operator inputs or third-party material and does not independently
establish ownership of every held historical project.

Python, SQLite and Tcl/Tk are supplied by the installed runtime. No interpreter,
database engine, Tk runtime, third-party package, evidence payload, external asset
or historical database is bundled. See [third-party notices](../THIRD-PARTY-NOTICES.txt).

Public examples contain only invented IDs, series labels, revisions, states and
outcomes. Real stores, histories, exports, backups, audit mappings and publication
receipts remain outside the public source package. Internal checksum metadata
is not signed provenance of operator records.

See the [collection batch review](../../../docs/BATCH-14-ASSESSMENT-WORKBENCH.md)
for the reviewed publication scope and actual validation limits.
