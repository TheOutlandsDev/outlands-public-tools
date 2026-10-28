# Batch 51: Offline Data Import & Migration Workbench

This complete selected application adapts explicit source registration, row
provenance, normalization/deduplication, visible errors and pending human review
into a fresh generic CSV/JSONL mapping and local SQLite import workflow.

A canonical pinned preview separates analysis from import. It retains accepted
records, duplicate provenance, rejection codes and conflicting variants. Every
conflicting key blocks import; invalid rows require explicit acceptance before
importing only accepted records. Repeated exact successful fingerprints are refused.
Input order is canonicalized. Contract/source changes require another preview.

Reviewed imports create exclusive fresh SQLite stores with fixed schema, bound
values and complete logical readback against the pinned preview. Source bytes are
rechecked before and after construction. Completed markers plus journal registration
are required; neither failed partial outputs nor orphan completion markers are
adopted. Durable attempts, explicit stopped recovery, private handoffs, metadata-only
index backups, browser UI and CLI make this a complete local application.

The original importer was read only and remains unchanged/unexecuted. No original
source file, corpus, conversation archive, source mapping, customer schema,
configuration, database, model asset, credential or operating record is included.
All included contracts, values, labels and row references are invented. The broader
original application family remains separately held.

Fictional Windows/Ubuntu Python 3.12/3.13 qualification covers exact normalization,
CSV/JSONL rules, deduplication/provenance, key conflicts, source/preview/store pins,
schema/hash/type tampering, reviewed import/export, repeat prevention, partial
failures and an actual owned-child interruption. Seven native link fixtures are
mandatory in CI, including a real Windows junction or POSIX directory link. Actual
Chromium acceptance checks the complete user workflow, stale/lost responses, draft
retention, literal markup, required review and narrow keyboard layout. Source ZIP,
copied setup, independent SQLite/JSON oracles and report hashes must be verified.

Instance content and exports remain private. Reports include normalized values and
provenance; display CSV escaping is limited, while JSONL preserves types and nulls.
Human assertions are not anonymization, rights clearance or publication permission.
This is not an in-place database-schema migration, arbitrary SQL engine, external
service, automatic rollback, complete instance backup or atomic live-source capture.
Trusted parents are assumed; hostile concurrent filesystem, power-loss/hardware,
long-term retention and production suitability are unverified.

First-party source is MIT, copyright TheOutlandsDev. See the
[application guide](../systems/import-migration-workbench/README.md),
[contract](../systems/import-migration-workbench/docs/CONTRACT.md),
[safety boundaries](../systems/import-migration-workbench/docs/SAFETY.md) and
[validation scope](../systems/import-migration-workbench/docs/VALIDATION.md).
