# Batch Replay Planner 0.1.0

Describe manual-review or skip advice from explicitly selected batch declarations
and receipt snapshots. This independent MIT CLI/library has standard-library
dependencies only. Qualification targets Windows and Ubuntu with the exact
CPython 3.12–3.15 distributions in [PYTHON-LOCK.json](PYTHON-LOCK.json).

It never performs a replay, retry, import, dispatch or target write. A PASS means
the supplied declarations permit an advisory plan; it does not authorize execution,
authenticate a commit or establish safe replay, idempotency or exactly-once behavior.
No live store, real record, workbook or external service is needed.

## Start with invented snapshots

From the complete tool directory, in PowerShell 5.1 or a POSIX shell:

```text
python -E -s -B replay.py --input examples/input.json
python -E -s -B replay.py --input examples/needs-review.json
```

The first yields skip advice for `batch-a` and manual-review advice for `batch-b`
(exit 0). The second intentionally requires review (exit 1) and withholds the
whole plan. See the independent, executable [walkthrough](USAGE.md) for exact
reports, list accounting, history blockers, aliases and native file refusals.
Optional `--out` requires a fresh path outside the source tree under a trusted
existing parent. Nothing is imported or retried.

Library entry: `replay.plan(raw_json_bytes)`. The outer JSON object has exactly
`format: outlands-batch-replay-v1`, `stream`, `expected` and `receipts`. Select the
candidate list and reviewed receipt snapshots explicitly. They are not an event
log, complete-history proof or automatic latest-status selection.

## Advice and whole-plan withholding

An exact candidate/declared-committed receipt match yields `SKIP_ALREADY_COMMITTED`.
A candidate with no supplied matching receipt yields `MANUAL_REVIEW_NEW_BATCH`.
Absence is relative to the provided snapshots only, never proof that an import
did not happen or that executing again would be safe. Healthy unrelated committed
history from the same stream can be included. Advice sorts by sequence then ID;
different accepted IDs sharing a sequence instead block the plan.

Any issue withholds the entire plan as `null`, including a malformed/conflicting
candidate or receipt, wrong stream, metadata mismatch, alias, unsuitable declared
source counts, or failed/uncertain history anywhere in the supplied scope. This
includes history not among the candidates. No latest receipt wins. A conflicting
receipt group is withheld first and produces conflict diagnostics; it need not
also produce a history-status diagnostic. If no candidate remains structurally
accepted, an `EMPTY_BATCH_COHORT` issue is added at logical position 0.

Every comparison report has `plan_only: true`, `retry_performed: false` and
`execution_authorized: false`. Every populated advice row also has
`execution_authorized: false`, even on PASS. REVIEW_REQUIRED retains accounting
and fixed diagnostics, never a partial executable plan.

## Batch declarations, receipts and accounting

Each batch has exactly `id`, `sequence`, `source_sha256`, `mapping_sha256`,
`preview_sha256` and `counts`. ID/stream/receipt ID match
`[a-z][a-z0-9_-]{0,47}`. Sequence is an actual integer 1–1,000,000,000. Pins are
64 lowercase hexadecimal characters. Declared source counts have exactly
`input_rows`, `accepted_records`, `duplicate_rows`, `rejected_rows`, `conflict_rows`,
each an actual integer 0–1,000, with input equal to the sum of the other four.
Booleans and numeric coercion are refused. Planning requires declared positive
source input/accepted counts and zero rejected/conflicting source rows.

A receipt has exactly `receipt_id`, `stream`, `batch`, `status` and
`receipt_sha256`. `batch` is the complete object above; status is exactly
`committed`, `failed` or `uncertain`. All source/map/preview/receipt pins and
source-record counts are declarations. Referenced bytes are not opened, hashes
are not recomputed against those bytes and commit authority is not authenticated.
Reports keep `row_counts_recomputed`, `receipt_authority_verified` and
`exactly_once_verified` false.

Separately, the tool computes accounting for each supplied JSON list, with at
most 1,000 candidate rows and 1,000 receipt rows. Identity is batch ID within the
selected stream; receipt identity is its embedded batch ID. Identical normalized
snapshots count once plus duplicates. Different snapshots under one identity
withhold every group member, including identical repeats inside that conflicting
group. The observed list invariant is:

```text
input_rows = accepted_records + duplicate_rows + rejected_rows + conflict_rows
```

This observed JSON-list accounting does not recompute the source-record counts
declared inside a batch. Cross-reference issues do not reclassify structurally
accepted list rows. Alias checks use accepted representatives and their first
positions. Different IDs cannot share a sequence or the complete source/map/
preview pin tuple across the supplied candidate/history scope. Different accepted
receipt snapshots cannot share a receipt ID across batch IDs. A candidate and
its receipt can share metadata under the same ID, but every batch field must match.
Changed mapping/preview pins under a new ID may avoid an exact tuple alias and
yield manual review; that is not proof that rerunning is safe.

## Evidence, files and privacy

The required archive matrix preserves all 63 original methods and adds exactly
30 copied-runtime CLI cases per lane: 93 selections, 744 across eight Windows/
Ubuntu Python lanes. Actual passes and finite skips are measured in validation
records; skipped safeguards are not passed safeguards. Four runtime files contain
57 non-generator definitions. Only the Windows exclusive-create safeguard changes;
56 definitions, three other runtime files, original tests, two fictional JSON
examples and three historical records remain preserved. No generator exists.
See [qualification](docs/QUALIFICATION.md) and [methodology](docs/METHODOLOGY.md).

One explicit ordinary single-link JSON file is read, at most 4 MiB. Shared JSON
limits reject duplicate keys, floats/nonfinite values, invalid Unicode, strings
over 4,096 characters, depth over 32, over 100,000 nodes and integers outside ±10^18.
Output is escaped ASCII JSON, bounded to 8 MiB. Invalid outer contracts/list bounds
refuse entirely; invalid list rows are accounted, diagnosed and withhold the plan.

Default stdout is private. IDs, sequence values, decisions, counts, positions and
exact input fingerprints can identify a known snapshot. Source records and raw
rejected values are not serialized as fields; coincidental text may still appear
in retained IDs or fixed codes. This is not general substring redaction or
anonymization. Reports do not authenticate an import, reserve an idempotency key
or establish rights to publish a real input.

Use trusted, quiescent inputs and fully spelled parents. Native `--out` creation
refuses name reuse and source-tree outputs; failed writes may retain unconfirmed
partial bytes. Preserve them and choose a new filename. Shell redirection does
not inherit these protections. Cooperative limits and sampled file checks are
not an OS sandbox, atomic snapshot, hostile-writer guarantee, rollback, complete
metadata preservation or hardware durability. Exit 0 PASS, 1 REVIEW_REQUIRED,
2 fixed refusal, 130 handled interruption.

See [filesystem boundaries](IO-SAFETY.md), [origins](ORIGINS.md),
[historical validation](VALIDATION.md), [changes](CHANGELOG.md) and
[notices](THIRD-PARTY-NOTICES.txt).
