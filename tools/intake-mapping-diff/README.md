# OUTLANDS | Intake Mapping Diff

Compare revisions of the supported public intake mapping without applying changes. Independent MIT CLI/library, Python 3.12/3.13 standard library only.
Fresh generic code and fictional examples; no private implementation reused.

From this complete tool directory:

```text
python -B mapping_diff.py --input examples/input.json
python -B mapping_diff.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional
`--out ../fictional-new-report.json` requires a trusted existing parent outside
the collection and a destination that does not exist. Nothing is imported or retried.

## Contract and interpretation

Library: `mapping_diff.compare(raw_json_bytes)`. Exact top-level fields are
`format: outlands-intake-mapping-diff-v1`, `before`, `after`. Both embedded maps
use the existing public `outlands-table-map-v1` format. The byte-identical public
intake.py validates them: 1..32 fields, unique source headers/target IDs, supported
text/integer/decimal/boolean/date types, strict required booleans and 1..4 unique
identity targets that must be required fields. Unknown-column policy reject/ignore.
The included public module is used only for mapping validation by this CLI;
it does not read or parse a workbook, CSV or user record.

Match fields by exact target ID. Report added/removed targets and fixed codes for
changed source header, type or required flag. Report identity order/membership,
unknown-column policy and field order/membership changes. Target changes are
removal/addition, never inferred renames. Literal source header values are omitted;
symbolic target IDs and fixed codes remain private report information.
Any difference returns REVIEW_REQUIRED with the descriptive change list retained.
Identical maps return PASS; invalid maps refuse entirely. This differs from the
batch tools' withholding rule: a valid mapping difference is the intended result.
Object-key order is ignored by canonical encoding; field/identity list order is
significant. Mapping pins cover sorted-key compact ASCII JSON plus LF, not an
original standalone mapping file's formatting. Input pin covers exact outer JSON.
The changed example reports SOURCE_HEADER_CHANGED, TYPE_CHANGED, REQUIRED_CHANGED
for units. No records are validated, schema upgraded, alias inferred or mapping
modified. No compatibility or migration-safety verdict is established.

## Batch/receipt contract and evidence boundaries

The three batch tools use this exact batch object:
`{id, sequence, source_sha256, mapping_sha256, preview_sha256, counts}`.
ID/stream/receipt_id match `[a-z][a-z0-9_-]{0,47}`. Sequence is integer
1..1,000,000,000. Pins are 64 lowercase hex characters. Counts has exactly
input_rows/accepted_records/duplicate_rows/rejected_rows/conflict_rows, each an
exact integer 0..1,000, and input equals the sum of the other four. Booleans and
numeric coercion are refused. A qualified batch requires positive input and
accepted counts, with zero rejected/conflicting source rows.

A receipt is exactly `{receipt_id, stream, batch, status, receipt_sha256}`;
batch is the full object above and status is committed/failed/uncertain.
receipt_sha256 is a supplied evidence pin; its referenced bytes are not loaded.
All source/mapping/preview pins and counts here are declarations, not recomputed
facts. The snapshots do not authenticate an import or transaction. Every batch
tool reports row_counts_recomputed=false, receipt_authority_verified=false and
exactly_once_verified=false. A fictional CLI integration separately runs the
existing public intake/reconciler and binds those actual generated pins/counts;
the new tools still do not independently recompute them or verify a commit.

At most 1,000 expected rows and 1,000 receipt rows. Batch identity is ID within
the top-level stream; receipt snapshot identity is its embedded batch ID. Identical
rows count once plus duplicate rows. Any differing snapshot under one identity
conflicts and every group member is withheld, including identical repeats inside
that conflicting group. No latest-status/revision selection. Conflicting pending
and committed history must be explicitly reviewed before selecting a snapshot.

Different batch IDs cannot share a sequence or the same complete source/mapping/
preview fingerprint in the selected scope. One matching ID may appear in expected
and receipts, but all batch metadata/counts must match for reconciliation.
Different receipt snapshots cannot share a receipt ID across batch IDs. Alias
checks span both candidate and receipt lists; wrong-stream receipts block review
rather than being silently ignored. These are conservative declaration rules,
not globally enforced uniqueness or proof of complete historical coverage.

List accounting is always input_rows = accepted_records + duplicate_rows +
conflict_rows + rejected_rows. Positions are 1-based logical JSON rows; 0 denotes
a cohort/window issue. Rejected values are not echoed. Cross-reference issues
do not reclassify structurally accepted rows. Any issue withholds batch plans,
checkpoint suggestions or run totals; accounting and fixed diagnostics remain.
Reports contain no source records, literal source headers, operational paths or
credentials. Symbolic IDs, decisions, counts and hashes may still be private.

## CLI, limits and privacy

Read one explicit JSON file <=4 MiB. Unknown fields, duplicate JSON keys, floats,
nonfinite values, invalid Unicode, strings >4,096, depth >32, >100,000 nodes or
integers outside +/-10^18 are refused. Output is escaped ASCII JSON <=8 MiB.
No directory discovery, include, URI fetch, environment expansion, clock,
process execution, service/model load or target connection. Library entries take
raw JSON bytes. Invalid outer contracts/limits refuse entirely; malformed batch
rows receive fixed codes and require review. Mapping errors refuse entirely.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted, quiescent parents. No hostile filesystem/process sandbox.
Default output is private stdout. Optional --out exclusively creates a new report
under an existing external parent, outside the source tree; no overwrite or mkdir.
Failed writes may retain partial/unconfirmed output; inspect privately and select
a fresh path. Windows inherits parent ACLs, with no confidentiality guarantee.
Shell redirection does not inherit --out protections. Exit 0 PASS, 1 REVIEW_REQUIRED,
2 fixed refusal, 130 interruption; supplied paths/values are omitted from errors.
No credentials, private source implementation, records, deployment configuration
or assets are required. Real inputs/reports stay private; hashes/structure do not
anonymize them, establish rights or authorize publication/target execution.

See [origins](ORIGINS.md) and [validation limits](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
