# Checkpoint Progression Checker 0.1.0

Check a proposed abstract ordinal against contiguous declared committed batch
coverage. This standalone MIT CLI/library uses the standard library only.
Qualification targets Windows and Ubuntu with the exact CPython 3.12–3.15 builds
in [PYTHON-LOCK.json](PYTHON-LOCK.json). It does not write a checkpoint or verify
a source watermark, prior checkpoint authority, receipt authority or real commit.

## Start with invented declarations

From the complete tool directory, in PowerShell 5.1 or a POSIX shell:

```text
python -E -s -B checkpoints.py --input examples/input.json
python -E -s -B checkpoints.py --input examples/needs-review.json
```

The first checks positions 1 and 2 and suggests ordinal 2 for explicit review
(exit 0). The second has missing ordinal coverage and withholds the suggestion
(exit 1). A PASS never authorizes a real advancement, authenticates a transaction
or proves upstream completeness. The full independent fictional walkthrough is
in [USAGE.md](USAGE.md). Optional `--out` writes a fresh external report under a
trusted existing parent; no checkpoint is persisted.

Library entry: `checkpoints.check(raw_json_bytes)`. Exact outer fields are
`format: outlands-checkpoint-progression-v1`, `stream`, `previous`, `proposed`,
`expected` and `receipts`. Previous/proposed are actual integers 0–1,000,000,000,
with previous ≤ proposed and width at most 1,000. They are abstract sequence
positions, not time, database offsets or independently established watermarks.

## Contiguous coverage and global withholding

Every integer in `(previous, proposed]` needs an accepted expected batch and an
exact matching receipt declaring `committed` with suitable declared source counts.
All expected batches must be inside that interval. Accepted receipt groups must
have an embedded batch ID matching an accepted expected batch ID; extra history
is not silently tolerated here.
Metadata, aliases, stream, status, source-count, malformed/conflicting row and
coverage issues all withhold the entire `suggested_checkpoint` as null. There is
no partial advancement across a gap or fallback to a plausible prefix.

An issue-free positive-width window returns the proposed ordinal and
`advancement_eligible_for_explicit_review: true`, for manual review only. An equal
previous/proposed with empty expected/receipt lists is a no-change PASS: it returns
that same ordinal with eligibility false. Nonempty equal windows require review.
Every comparison report keeps `checkpoint_written`,
`previous_checkpoint_authority_verified` and `target_changes_performed` false,
and `plan_only` true. The prior checkpoint is an input declaration, not reverified.

The report distinguishes three counters. `missing_receipts` counts accepted
expected batch IDs without a matching accepted receipt group; `unexpected_receipts`
counts accepted receipt groups whose embedded batch IDs are absent from accepted
expected batch IDs. `resolved_committed_batches`
counts exact committed pairs with suitable declared counts. It can remain
positive despite stream, alias or outside-window issues, so it is not eligibility
proof. A coverage gap can have zero missing receipts, and missing receipts can
occur with complete expected ordinal coverage. Repeated gap diagnostics collapse
to one fixed `CHECKPOINT_GAP` at expected position 0, not one exported gap per ordinal.

Matching checks have an order: exact batch metadata, then committed status, then
declared source-count suitability. An earlier mismatch does not fabricate later
status/count issues. An accepted orphan group yields `UNEXPECTED_RECEIPT`.
Its failed/uncertain status adds no outcome/history code; independent stream or
alias issues can still apply.
Conflicting receipt groups are withheld before matching, so their candidate can
become missing without an outcome code for an already-withheld receipt.

## Declarations and observed accounting

Each batch has exactly `id`, `sequence`, `source_sha256`, `mapping_sha256`,
`preview_sha256` and `counts`. ID/stream/receipt ID match
`[a-z][a-z0-9_-]{0,47}`. Sequence is an actual integer 1–1,000,000,000. Pins are
64 lowercase hexadecimal characters. Source counts have exactly `input_rows`,
`accepted_records`, `duplicate_rows`, `rejected_rows` and `conflict_rows`, each an
actual integer 0–1,000, with input equal to the sum of the other four. Suitable
declared counts have positive input/accepted values and zero rejected/conflicting
source rows. Booleans and numeric coercion are refused.

A receipt has exactly `receipt_id`, `stream`, `batch`, `status`, `receipt_sha256`.
Its batch is the full object above; status is `committed`, `failed` or `uncertain`.
All referenced source/map/preview/receipt bytes and source-record counts remain
caller declarations: those bytes are not loaded or authenticated, and the actual
source records are not independently counted. The report keeps
`row_counts_recomputed`, `receipt_authority_verified` and `exactly_once_verified`
false. No safe-advancement, exactly-once or business-approval guarantee follows.

Separately, the tool computes accounting for each supplied JSON list, at most
1,000 expected rows and 1,000 receipt rows. Group identity is expected batch ID,
or the receipt's embedded batch ID, within the selected stream. Equal normalized
snapshots count once plus duplicates. Differing snapshots withhold all valid
members of that group, including identical repeats. Each observed list obeys:

```text
input_rows = accepted_records + duplicate_rows + rejected_rows + conflict_rows
```

Cross-reference checks use accepted representatives and their first logical
positions; they do not reclassify structurally accepted rows. Different IDs cannot
share a sequence or the complete source/map/preview pin tuple across both lists.
Accepted receipt groups cannot share a receipt ID. A same-ID candidate/receipt
pair may share sequence/content but must match every batch field. Row positions
are one-based JSON list positions; position 0 denotes a coverage issue.

## Evidence, limits and privacy

The archive matrix preserves 64 original methods and adds exactly 30 copied-runtime
CLI cases per lane: 94 selections, 752 across eight Windows/Ubuntu Python lanes.
Actual pass/skip totals are measured; skipped safeguards are not passed safeguards.
Four runtime files contain 57 non-generator definitions. Only the Windows
exclusive-create safeguard changes; 56 definitions, three other runtime files,
all original tests, two invented JSON examples and three historical records remain
preserved. No generator exists. See [qualification](docs/QUALIFICATION.md) and
[methodology](docs/METHODOLOGY.md), including retained fixture-correction evidence.

One explicit ordinary single-link JSON file is read, at most 4 MiB. Shared JSON
checks refuse duplicate keys, floats/nonfinite values, invalid Unicode, strings
over 4,096 characters, depth over 32, over 100,000 nodes and integers outside ±10^18.
Reports are escaped ASCII JSON bounded to 8 MiB. Invalid outer contracts, ordinal
bounds and list bounds refuse entirely. Invalid list rows are accounted and require
review with a withheld suggestion.

Reports serialize ordinals, list/resolution counters, issue positions/codes and
the exact input hash. They do not export a plan/ID list, raw batch/receipt objects,
stream or individual declared pins as fields. Coincidental text can still occur
in fixed keys/codes. Metadata and fingerprints remain private, not anonymized or
complete-source evidence. Keep real snapshots and reports private.

Use trusted quiescent inputs and fully spelled parents. Native `--out` refuses
existing leaves and source-tree destinations. Failed writes may retain unconfirmed
partial output; preserve it and choose a new name. Shell redirection does not
inherit these guards. Cooperative bounds and sampled metadata are not an OS
sandbox, atomic snapshot, hostile-writer guarantee, rollback, full metadata
preservation or hardware durability. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal,
130 handled interruption. See [filesystem boundaries](IO-SAFETY.md),
[origins](ORIGINS.md), [historical validation](VALIDATION.md),
[changes](CHANGELOG.md) and [notices](THIRD-PARTY-NOTICES.txt).
