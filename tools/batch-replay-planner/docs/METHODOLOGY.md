# Methodology and interpretation

## Selected evidence, not an event log

The caller chooses one stream and two lists: candidate batch declarations and
reviewed receipt snapshots. The planner never discovers history, selects a latest
receipt, contacts a target, reserves an idempotency key or retries an action.
A declared committed receipt is not an authenticated transaction. An absent
receipt is absent only from the supplied snapshots, not proof that execution
never happened. SKIP_ALREADY_COMMITTED and MANUAL_REVIEW_NEW_BATCH are labels for
explicit review, always with execution_authorized false.

Healthy unrelated committed history can be included. Accepted failed/uncertain,
unclean or wrong-stream history anywhere in scope blocks the whole plan, including
noncandidate history. Invalid or conflicting history also blocks through its own
row diagnostics. Conflicting groups are withheld before the history-status loop;
do not invent a HISTORY status issue for a row that never reached that loop. The
report is REVIEW_REQUIRED with plan null for any issue. A partially plausible
advice list is never returned around a blocker.

## Two accounting scopes and identity rules

Batch IDs identify candidate groups; a receipt group uses its embedded batch ID.
Complete normalized snapshots match by canonical JSON. Identical rows count once
plus duplicates. Any different snapshot in one group withholds every valid member,
including identical repeats. There is no arbitrary winner or latest-status rule.
The tool computes observed list counts for candidates and receipts and conserves
every supplied list row as accepted, duplicate, rejected or conflicting.

Separately, source-record counts inside each batch are supplied declarations.
They must be exact bounded integers with a valid sum; planning requires positive
declared input/accepted counts and zero rejected/conflicting source counts. Their
record bytes, map/preview bytes and receipt-evidence bytes are never loaded or
authenticated. row_counts_recomputed=false refers to those source counts, not the
observed JSON-list accounting. A structurally accepted batch-list row can still
have unsuitable declared source counts and block advice without becoming rejected
in the list accounting.

Cross-reference checks run on accepted representatives and use their first logical
list positions. Duplicate positions are still counted but need not repeat an
alias diagnostic. Different accepted IDs cannot share a sequence or the complete
source/map/preview hash tuple across candidates and receipts. Different receipt
groups cannot share a receipt ID. An ID present in both lists must match all batch
metadata/counts; an exact same-ID sequence/content match is not itself an alias.
Alias/stream/metadata issues do not reclassify structurally accepted list rows.

Issues are deduplicated by side/position/code and sorted in that order. Positions
are one-based logical list rows; position 0 denotes the empty-candidate cohort
issue. Advice sorts by sequence then ID, but sequence ties between different
accepted IDs are blockers rather than a way to choose an arbitrary order/winner.
A new ID with changed mapping/preview pins may avoid an exact tuple alias and
receive manual review; that never proves a rerun safe.

## Independent examples and privacy

The executable guide authors complete reports, list counts, fixed issues and
advice directly, without using replay.plan or control_core.prepare/rows/report as
an expected-results oracle. Explicit fixtures cover selected and unrelated
history, duplicate/conflict groups, malformed declarations, cross-list aliases,
source-count holds, empty cohorts and accepted bounds. Hash labels are invented
declarations, not source-file attestations. The sole input pin hashes exact outer
JSON bytes, so formatting or a UTF-8 BOM can change it without changing advice.
No generator, source-record reconciliation or external-writer integration is used.

IDs, sequences, advice, counts, positions and exact fingerprints can correlate a
known snapshot. Source records and rejected raw fields are not serialized as
fields, but equal text may coincide with a retained ID or fixed code. Omission is
not general substring redaction, anonymization, complete-history evidence or
permission to publish an operational snapshot. Keep inputs, reports and ledgers
private. No compatibility, migration, safe-replay, idempotency or exactly-once
guarantee follows from a PASS or a declared commit.

## Native and runtime boundaries

Actual CLI entry-point children run with selected C XMLParser/TreeBuilder affinity
checks before and in finally after execution, and with extraction/remote/process
actions refused by audit hooks. Product inputs remain JSON; XML/compression
components are measured for the shared-toolkit boundary envelope. This is selected
complete-Python identity, not independent library certification or an arithmetic
context claim. A separate controlled backend fault creates an unconfirmed five-byte
prefix; it is not another CLI or a completed report.

Every case checks prior files, input hashes, report bytes, observation rows and
manifest readback. Fresh native output creation refuses existing leaves and source
destinations. Failed writes retain unconfirmed output, with no automatic deletion,
rollback or silent reuse. Windows ACLs inherit from the trusted parent. Byte and
Python-character budgets are distinct. Use trusted quiescent inputs and parents;
cooperative bounds, process timeouts and sampled file checks are not OS isolation,
an atomic snapshot, hostile-writer containment, full metadata preservation or a
crash/power-loss durability guarantee.
