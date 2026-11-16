# Methodology and interpretation

## Abstract ordinal evidence

The caller declares previous/proposed integer ordinals and explicitly selects two
lists: expected batch declarations and receipt snapshots. The checker neither
polls a source nor establishes the previous ordinal's authority. Ordinals are not
time, database offsets or externally verified watermarks. An issue-free positive
window returns the proposed value for explicit review. Equal empty windows return
the same value with eligibility false. Any issue withholds the whole suggestion
as null, with no fallback prefix or automatic persistence.

Accepted expected sequences must cover every integer in `(previous, proposed]`
and remain inside that interval. Every accepted expected ID needs an exact
committed receipt with suitable declared counts. An accepted receipt group whose
embedded batch ID is absent from accepted expected batch IDs is unexpected,
even when its history is committed. Matching checks exact batch
metadata before status, then source-count suitability. Earlier failures do not
invent later diagnostics. An orphan's failed/uncertain status adds no outcome/history
diagnostic; an otherwise valid orphan produces UNEXPECTED_RECEIPT. Independent
stream/alias issues can still apply.

## Three counters are not eligibility

missing_receipts counts accepted expected batch IDs without matching accepted
receipt groups, while unexpected_receipts counts accepted receipt groups whose
embedded batch IDs are absent from accepted expected batch IDs.
Neither counts absent ordinal positions. A coverage gap can have zero missing
receipts, and all expected ordinals can exist while a receipt is missing. Multiple
missing ordinal positions deduplicate to one CHECKPOINT_GAP at expected position 0.

resolved_committed_batches counts exact committed pairs with suitable declared
counts, even when another global condition is wrong. Wrong-stream or outside-
window rows and alias cases can retain positive resolved counts while the entire
suggestion is null and eligibility false. This counter is descriptive, not a
commit-authority, source-completeness or advancement permission signal.

## Grouping, list accounting and source declarations

Expected groups use batch ID; receipt groups use embedded batch ID. Complete
normalized snapshots compare by canonical JSON. Identical snapshots count once
plus duplicates. A different snapshot withholds all valid members of the group,
including identical repeats. Conflicting receipts are removed before matching,
so a candidate can become missing without an outcome diagnostic for an already-
withheld receipt. No latest-status selection or arbitrary winner is inferred.

Observed expected/receipt-list counts conserve every JSON row as accepted,
duplicate, rejected or conflicting. Cross-reference checks use accepted
representatives and their first logical positions; duplicate positions remain
accounted without repeating every alias issue. Alias, stream and window issues
do not reclassify structurally accepted rows. Issues deduplicate by side/position/
code and sort in that order. Position 0 is reserved here for the coverage diagnostic.

Embedded source-record counts are separately supplied integer declarations. Their
sum and bounds are checked, but source records and referenced source/map/preview/
receipt bytes are never loaded or independently counted/authenticated. Thus
row_counts_recomputed=false does not negate actual observed JSON-list accounting.
Syntactically valid zero-filled pins and a declared committed status are not trust
proofs. Suitable declared counts do not establish real data quality or business
approval. Receipt and previous-checkpoint authority stay unverified.

## Independent examples and privacy

The guide authors full report bytes, counts, counters, issues, suggested values
and eligibility without check/prepare/rows/reconcile/report as matching oracles.
Fixtures cover all three counters, ordinal limits, unmasked matching precedence,
gaps versus missing IDs, full 1,000-position coverage, invalid declarations and
no-change windows. The accepted identifier-boundary fixture uses a separate valid
receipt ID; one identifier's maximum length does not extend another's limit.
The raw input hash binds exact JSON bytes, so formatting or a UTF-8 BOM can change
the fingerprint without changing the interpreted coverage.

Reports export ordinals, counters, positions/codes and input fingerprints, not
raw snapshots, ID/advice lists, stream or individual declared pins as fields.
Coincidentally equal text may remain in fixed keys/codes. Omission is not general
substring redaction or anonymization. Metadata can correlate a known input; keep
real snapshots, reports, hashes and ledgers private. No real source, authenticated
transaction, previous authority, safe advancement or exactly-once behavior is proven.

## Native/runtime limits

Actual CLI entry-point children run with selected C XMLParser/TreeBuilder affinity
checks before and in finally after execution, while audit hooks refuse extraction,
remote and process actions. Product inputs are JSON. XML/compression identities
support shared-toolkit boundary evidence, without an arithmetic context or
independent library-build claim. A separate controlled backend fault leaves an
unconfirmed five-byte prefix; it is not another CLI or a completed report.

Every case preserves prior files and checks input/report hashes, observation rows
and manifest readback. Native output creation requires a new external name and
refuses existing leaves/source destinations. Failed writes can retain partial
output, with no automatic deletion, rollback or silent reuse. Windows ACLs inherit
from the parent. Byte and Python-character budgets differ. Trusted quiescent
inputs/parents are required; cooperative limits, audit hooks, process timeouts
and sampled metadata do not provide OS isolation, atomic snapshots, hostile-writer
containment, full metadata preservation or crash/power-loss durability.
