# Ingestion Run Coverage Checker 0.1.0

Reconcile an explicitly selected, nonempty cohort of batch declarations against
saved receipt snapshots, and total their declared source counts. This MIT
CLI/library uses the standard library only. Windows/Ubuntu qualification targets
the exact CPython 3.12–3.15 builds in [PYTHON-LOCK.json](PYTHON-LOCK.json).
It does not inspect a store, import records or authenticate a declared commit.

## Start with invented declarations

From the complete tool directory, in PowerShell 5.1 or a POSIX shell:

```text
python -E -s -B coverage.py --input examples/input.json
python -E -s -B coverage.py --input examples/needs-review.json
```

The first returns PASS and declared totals of six input rows, four accepted and
two duplicates (exit 0). The second requires review (exit 1). Optional `--out`
writes a fresh external report under a trusted existing parent. See the complete
independent fictional exercise in [USAGE.md](USAGE.md).

Library entry: `coverage.check(raw_json_bytes)`. The filename can collide with an
unrelated installed coverage package; use the actual script or an explicit file
loader, and keep qualification environments free of third-party distributions.
Exact outer fields are `format: outlands-ingestion-run-coverage-v1`, `stream`,
`expected` and `receipts`. No records, CSV or workbook is an application input.

## Cohort coverage and global withholding

At least one expected batch must survive row validation and conflict withholding.
Noncontiguous sequences are allowed: this is selected-cohort reconciliation, not
contiguous ordinal coverage or upstream-completeness verification. Every accepted
expected batch needs an exact committed receipt with suitable declared counts.
Accepted receipt groups' embedded batch IDs must match accepted expected batch
IDs. The separate `receipt_id` is not the batch-matching key.

Any issue makes `declared_totals` null and `cohort_complete` false. There are no
partial totals, even when several pairs resolve successfully. Empty, all-invalid
or wholly conflicted expected cohorts require review with `EMPTY_BATCH_COHORT`.
An issue-free result sums each unique matched batch's declared count fields once.
It does not certify that the supplied cohort represents a complete ingestion run.

`missing_receipts` counts accepted expected batch IDs lacking accepted receipt
groups; `unexpected_receipts` counts accepted receipt groups whose embedded batch
IDs are absent from accepted expected batch IDs. `resolved_committed_batches`
counts exact committed pairs with suitable declared counts. It can stay positive
under stream or alias issues, so it is not proof that the cohort is complete.

Matching checks exact batch metadata, then committed status, then source-count
suitability. Earlier failures do not invent later diagnostics. An otherwise valid
orphan produces `UNEXPECTED_RECEIPT`; its failed/uncertain status adds no outcome
code. Independent stream or alias issues may still apply. Conflicted groups are
withheld before matching; a conflicted receipt group can leave an expected batch
missing without an outcome diagnostic for the already-withheld receipts.

## Declarations versus observed list accounting

Each batch has exactly `id`, `sequence`, `source_sha256`, `mapping_sha256`,
`preview_sha256`, `counts`. IDs, stream and receipt IDs match
`[a-z][a-z0-9_-]{0,47}`. Sequence is an actual integer 1–1,000,000,000. Pins are
64 lowercase hexadecimal characters. Source counts have exactly `input_rows`,
`accepted_records`, `duplicate_rows`, `rejected_rows`, `conflict_rows`, each an
actual integer 0–1,000, with input equal to the sum of the other four. Suitable
declared counts have positive input/accepted counts and zero rejected/conflict
counts. Booleans and coercion are refused.

Each receipt has exactly `receipt_id`, `stream`, `batch`, `status`,
`receipt_sha256`. Its embedded batch is the complete object above; status is
`committed`, `failed` or `uncertain`. Referenced source/map/preview/receipt bytes
are not opened or authenticated. Source records and actual store contents are not
independently counted. `row_counts_recomputed`, `receipt_authority_verified`,
`exactly_once_verified`, `target_changes_performed` and
`actual_store_contents_verified` remain false.

Separately, the tool computes accounting for the supplied expected and receipt
JSON lists, each at most 1,000 rows. Complete identical normalized snapshots count
once plus duplicates. Differing snapshots withhold every valid member of that
group, including identical repeats; no latest snapshot wins. Each observed list
obeys input = accepted + duplicate + rejected + conflict. These observed duplicate
rows are distinct from source-row duplicates declared inside each batch.

Cross-reference checks use accepted representatives at their first one-based
list positions and do not reclassify structurally accepted rows. Different batch
IDs cannot share a sequence or full source/map/preview pin tuple across both
lists. Accepted receipt groups cannot share a receipt ID. Same-ID batch/receipt
pairs may share sequence/content but must match every batch field. Position 0
identifies the empty-cohort diagnostic, not an input row.

## Qualification, limits and privacy

The archive matrix selects 63 preserved original methods plus exactly 30 copied
CLI methods per lane: 93 selections, 744 across eight Windows/Ubuntu Python lanes.
Pass/skip totals are measured; skipped safeguards are not passed safeguards.
Four runtime files contain 57 non-generator definitions. Only the Windows
exclusive-create safeguard changes; 56 definitions, three other runtime files,
all original tests, two invented JSON examples and three historical records stay
preserved. No generator exists. See [qualification](docs/QUALIFICATION.md),
[methodology](docs/METHODOLOGY.md) and [changes](CHANGELOG.md).

The explicit ordinary single-link JSON input is bounded to 4 MiB. JSON checks
refuse duplicate keys, floats/nonfinite values, invalid Unicode, strings over
4,096 characters, depth over 32, more than 100,000 nodes and integers outside
±10^18. Reports are escaped ASCII JSON bounded to 8 MiB. Invalid outer/list
contracts refuse entirely; invalid rows are accounted and require review.

Reports disclose declared totals, list/resolution counters, issue positions/codes
and the exact input fingerprint. They omit raw batch/receipt objects, stream,
batch/receipt ID lists and individual declared pin fields. Fixed keys/codes may
coincide with input text. Omission is not anonymization: counts and fingerprints
remain private. Keep operational inputs and reports private.

Use trusted quiescent inputs and fully spelled parents. Native output creation
refuses existing leaves and source-tree destinations. Failed writes may retain
unconfirmed partial output; preserve it and choose a new name. Shell redirection
does not inherit native guards. Cooperative bounds and sampled metadata are not
an OS sandbox, atomic snapshot, hostile-writer guarantee, rollback or hardware
durability. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption.
See [IO-SAFETY.md](IO-SAFETY.md), [ORIGINS.md](ORIGINS.md),
[historical validation](VALIDATION.md) and [notices](THIRD-PARTY-NOTICES.txt).
