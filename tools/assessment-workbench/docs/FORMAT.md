# Neutral record and store format

The workbench uses the public Assessment Record Contract Checker's record
format, with one extension: all three record lists may be empty for an empty
workspace. That extension reports `REVIEW_REQUIRED` and `EMPTY_WORKSPACE`, with
no checker report. Other ledgers use the bundled public checker unchanged.

## Ledger JSON

The exact root is:

```json
{"schema_version": 1, "submissions": [], "findings": [], "retests": []}
```

Nonempty ledgers contain 1 to 128 submissions, 0 to 128 findings and 0 to 128
retests, with at most 256 records combined. Every record has exactly these fields:

| Record | Fields |
| --- | --- |
| Submission | `id`, `series_id`, `revision` |
| Finding | `id`, `submission_id`, `state`, `selected_retest_id` |
| Retest | `id`, `finding_id`, `submission_id`, `outcome` |

IDs, references and series labels follow `[a-z][a-z0-9_-]{0,39}`. Entity IDs are
globally unique across the three collections. Series labels have a separate
namespace and group submissions. Revisions are actual integers from 1 through
1000000000, excluding booleans; `(series_id, revision)` pairs are unique.

Finding state is `open`, `retest_pending` or `closure_claimed`. Selection is null
or a valid ID. Retest outcome is `not_run`, `still_present`, `not_observed` or
`inconclusive`. There is only one retest summary per
`(finding_id, submission_id)` pair. Retest summaries are not execution history.

Unknown fields, duplicate JSON keys, wrong types, duplicate IDs/pairs, invalid
enums and nonstandard JSON constants are refused. No defaults, normalization,
coercion or environment expansion is applied. External inputs are bounded to
64 KiB, and canonical compact ledger bytes are also bounded to 64 KiB.

## Consistency rules

A finding names its original submission. A retest names a finding and a
replacement submission in the same series and at a strictly later declared
revision. All retests are checked, including unselected historical summaries.

- Open findings require null selection; historical outcomes do not force closure.
- Pending findings require a valid selected retest for that finding with outcome
  `not_run`.
- Closure claims require a valid selected retest for that finding with outcome
  `not_observed`.
- Pending and closure selections must name the highest declared revision in the
  original series, including submissions with no retest. This is an integer
  ordering rule, not proof of the real current build or latest execution.

Missing links and invalid dependencies block affected checks; direct semantic
mismatches fail. Outcomes, actual builds, authorization and isolation remain
unverified. See the [public checker's format and limits](../../assessment-record-checker/README.md).

Schema-valid inconsistent ledgers can be stored as review drafts. The workbench
never repairs links, cascades removal or advances states automatically. Applying
a desktop form only changes its in-memory draft. Saving commits a complete
snapshot using the expected current store revision; stale mutations are refused.

## Saved snapshots and exports

Each save appends a sequence to a SQLite schema-1 store. Revision 0 is the
initial empty, demo or imported snapshot. At most 128 snapshots are retained;
there is no migration or pruning. Removing a current record leaves plaintext
in earlier snapshots. Exact database schema, bounded canonical ledgers,
contiguous sequences and the internal checksum chain are validated on load.

Before opening SQLite, a bounded header check requires the supported SQLite
signature, 4096-byte pages and rollback-format read/write versions. WAL-format
stores are refused before a connection can create WAL/shared-memory artifacts.
Existing sidecars are refused and preserved, not cleaned up automatically.
Storage APIs serialize operations within the process and reject reentrant
store/JSON I/O while an owned connection is live. Use these public APIs as the sole
SQLite access in the process; external SQLite connections in that same process
are unsupported. These safeguards do not create an atomic filesystem boundary.

The SHA-256 chain is implementation integrity metadata, not a ledger field,
signature, trusted author identity or tamper-proof evidence. External consistent
rewrites can pass. Do not modify the database manually or treat internal digests
as permission to publish its records.

JSON export contains only the complete saved ledger. Import starts a NEW store
at revision 0 and does not import old history or merge IDs. Clone/recover copies
validated history through a chosen sequence to a NEW store. The entire source
must validate; the operation does not repair corrupt databases or hot journals.
All records, sidecars, exports, clones and history remain private.
