# Methodology and interpretation

## A declared selected cohort

The caller selects expected batch declarations and saved receipt snapshots. The
tool requires a nonempty accepted expected cohort, but does not require contiguous
sequence values. It does not discover batches, poll a source/store or establish
whether the selected cohort includes every real ingestion batch.

Both lists undergo row validation and complete-snapshot grouping. Identical
normalized snapshots count once plus duplicates. Conflicting groups withhold all
their valid members, including identical repeats, without choosing a latest row.
Receipt grouping and expected matching use the receipt's embedded batch ID;
`receipt_id` is a separate field checked for reuse across accepted receipt groups.
Cross-reference checks use first accepted positions and leave structural list
accounting unchanged. Position 0 is the empty-cohort diagnostic.

## Ordered reconciliation and a global gate

Each accepted expected batch needs an accepted receipt group with identical batch
metadata, committed status and suitable declared source counts. The checks occur
in that order: a mismatch suppresses later outcome/count checks for that pair.
An accepted receipt group whose embedded batch ID lacks an accepted expected
batch ID is unexpected. Its failed/uncertain status adds no outcome diagnostic;
independent stream/alias issues remain possible. Withheld conflicting groups do
not participate in matching, so missing or unexpected counterparts can result.

Any issue globally sets `declared_totals` to null and `cohort_complete` false.
There is no partial-total fallback. An issue-free nonempty cohort sums each unique
matched batch's five declared source-count fields once. Identical repeated list
rows do not multiply those declarations. Rejected/conflicting source counts, zero
input or zero accepted source counts require review rather than healthy coverage.

`resolved_committed_batches` counts internally exact healthy pairs; it can be
positive under separate stream/alias issues. Missing/unexpected counters describe
accepted batch-ID counterparts, not missing source records or sequence gaps.
`cohort_complete` describes only the supplied declarations passing this gate.

## Two kinds of accounting

Observed list accounting is computed from the supplied JSON rows: input equals
accepted plus duplicates plus rejected plus conflict. Source-record count fields
inside each batch are separately caller-supplied declarations with checked shape,
bounds and arithmetic consistency. Their bytes, record population, units and
actual store are not independently inspected. Syntactically valid source/map/
preview/receipt hashes are not evidence of authenticated bytes or commit authority.
No run, import, retry, target modification or exactly-once operation is performed.

## Independent evidence and limits

The fictional guide hand-authors whole expected JSON reports, counts, issue lists
and totals. It uses SHA-256 only for known authored bytes, never the application's
checker/shared reconciliation/report functions as matching oracles. Both early
semantic reviews precede formal execution. Every prior workspace entry and input
is rechecked after each case; all artifacts and a complete manifest are retained.
Actual script entry points execute with C XML bindings checked before/finally;
the direct partial-write control is separate from CLI counts. Product inputs are
JSON only and no arithmetic/Decimal-product qualification is claimed.

JSON bounds use bytes for the 4 MiB input and 8 MiB encoded output, Python string
characters for the 4,096 limit, depth 32 and node count 100,000. Each supplied list
has at most 1,000 rows; each source-count field is an integer 0–1,000 and sequence
is 1–1,000,000,000. These cooperative caps are not hostile-input OS isolation.

Reports omit raw snapshots and individual identifiers/pins as fields but retain
declared totals, metadata and fingerprints. That is not anonymization. Native
fresh-output guards and sampled metadata checks assume trusted quiescent inputs,
not atomic snapshots or transactional rollback. A failed write can retain an
unconfirmed partial file; preserve it and select a fresh destination. There is no
hardware-durability, store-correctness or production-workflow claim.
