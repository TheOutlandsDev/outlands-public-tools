# Import mapping, batch and progress-review methodology

These offline tools inspect supplied mappings and batch/receipt declarations.
Select the complete scope for each check before interpreting its result.

| Term | Plain-language meaning | Exact meaning here |
| --- | --- | --- |
| Mapping | Rules that assign source columns to typed target fields | The public outlands-table-map-v1 declaration: ordered fields, exact target IDs, required flags, identity targets and unknown-column policy. Mapping Diff validates declarations, not records. |
| Mapping difference | A descriptive change requiring interpretation | Exact target-ID matching, fixed change codes and ordered field/identity comparisons. A target-name change is removal/addition, not an inferred rename. Valid differences retain changes on REVIEW_REQUIRED. |
| Batch | One explicitly selected unit of declared intake work | ID, sequence, source/mapping/preview SHA-256 values and five declared counts. The batch tools do not load the pinned source or preview bytes. |
| Stream and sequence | A selected cohort label and ordering position | Symbolic stream ID and integer sequence 1..1,000,000,000. Positions are abstract ordinals, not timestamps, database offsets or source watermarks. |
| Receipt | One selected declaration about a batch outcome | receipt_id, stream, complete batch snapshot, status and a supplied evidence pin. One selected snapshot per batch ID; this is not an event log. Evidence bytes are not loaded. |
| Committed, failed, uncertain | Caller-declared outcome labels | committed can qualify only with an exact clean batch match. failed/uncertain block review conclusions in their applicable scope; a label does not verify a target transaction. |
| Qualified source counts | The supplied count declaration meets narrow rules | input = accepted + duplicate + rejected + conflict; positive input and accepted counts, zero rejected/conflict. Balanced counts alone do not qualify a batch. Counts are not recomputed. |
| Duplicate declaration versus duplicate source row | Two different accounting levels | Identical batch/receipt snapshots count once plus outer duplicate_rows. Inner source duplicate_rows remain part of a batch's declared counts and are summed once per matched batch. |
| Replay plan | Advice about selected candidate snapshots | Exact declared committed match gives SKIP_ALREADY_COMMITTED; no supplied receipt gives MANUAL_REVIEW_NEW_BATCH. Every execution_authorized flag remains false. No retry is performed. |
| Checkpoint | A proposed ordinal progress marker | Every position in (previous,proposed] needs one expected batch and exact declared committed receipt. Any gap withholds the whole suggestion; no partial advancement is proposed. |
| No-change checkpoint | A proposal that does not advance progress | Equal previous/proposed with empty expected/receipt lists can PASS, while advancement_eligible_for_explicit_review is false. Nothing is persisted. |
| Run coverage | Accounting for the explicitly selected expected cohort | Every expected batch needs an exact declared committed receipt, and no unexpected receipt is allowed. Coverage does not require consecutive sequences. Any finding withholds all declared totals. |
| Pin and receipt boundary | A reproducible declaration binding | Mapping Diff pins validated sorted-key compact escaped ASCII JSON plus LF; input pin covers exact raw outer JSON. Batch source/mapping/preview/evidence pins are supplied assertions, not signatures or independently verified facts. |
| PASS | The selected declaration rules were met | Identical mappings; an advisory replay plan; eligible checkpoint review; or complete selected declaration coverage. It does not establish actual commits, safe replay or exactly-once behavior. |
| REVIEW_REQUIRED | Findings need interpretation | CLI exit 1. Mapping Diff retains valid descriptive changes; batch tools withhold their complete plan/checkpoint/totals while retaining counts and fixed diagnostics. |
| Fixed refusal | The requested scope cannot be assessed | CLI exit 2; malformed outer input, invalid mappings, checkpoint bounds or parser limits refuse entirely. Library operations raise the fixed refusal. |
| Independent package | One tool can be installed and called alone | Its own wheel/version, CLI, embedded fictional demo and actual compare/plan/check operation. The collection pins exact versions of all four. |

## Apply the method

1. Compare explicit mapping revisions before a separate intake decision. Source
   headers are compared but omitted from reports; target IDs and changes can still
   disclose private information. A mapping change is not a compatibility verdict.
2. Select candidate batches and reviewed receipt snapshots. Replay review may
   include other selected history; failed or uncertain history anywhere in that
   scope blocks the whole plan, even outside the candidate set. Absence of a receipt
   is only absence from the supplied snapshots, never permission to rerun.
3. For progress review, select exactly the ordinal window and all required receipts.
   Preserve gaps, aliases, stale metadata and uncertainty. The proposed ordinal and
   previous checkpoint are assertions, not independently verified source state.
4. Reconcile run coverage separately. A selected nonconsecutive cohort can have
   complete declarations while failing a checkpoint proposal across the gap.
   Duplicate declarations do not inflate totals, and no incomplete total is emitted.

The [installed exercise](../integrations/ingestion-control/exercise.py) shares
fictional mapping/batch snapshots across all four tools and demonstrates these
scope differences, uncertainty, duplicates, rejected counts and stale metadata.
The [component guide](../integrations/ingestion-control/components.json) gives
people and AI callers exact operations, formats, examples, result fields and limits.
Existing source CLI acceptance separately runs the public intake/reconciler on
invented CSV to produce and bind actual pins/counts. The batch tools still treat
those values and committed statuses as declarations, not target-store proof.

At most 1,000 expected and 1,000 receipt rows are accepted; count fields are bounded
to 0..1,000 per batch, and a proposed checkpoint window spans at most 1,000 positions.
The source guides define complete row accounting, identity/content alias checks,
parser bounds and I/O guards. Real mappings, source records, receipts, progress,
workspace journals and reports stay private. Hashes do not anonymize them or
authorize publication, imports, retries or progress changes.
