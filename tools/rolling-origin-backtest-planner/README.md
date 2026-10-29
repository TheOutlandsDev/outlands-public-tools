# OUTLANDS | Rolling-Origin Backtest Planner

Plan explicit regular-grid training windows, gaps and multiple evaluation horizons without training. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and fictional series; no private original implementation reused.

From this complete tool directory:

```text
python -B backtests.py --input examples/input.json
python -B backtests.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional
`--out ../fictional-new-report.json` needs a trusted existing external parent and
a destination that does not exist. No original program, real dataset or model needed.

## Contract and interpretation

Library: `backtests.plan(raw_json_bytes)`. Exact fields:
format (`outlands-rolling-origin-plan-v1`), series, grid, training, horizons, stride.
Grid is `{start,end,step}`, inclusive and regular, at most 1,000 points. Training
is exactly `{min_points,max_points,gap_points}`: min 1..1,000, max null for expanding
history or an integer min..1,000, gap 0..1,000. Horizons is 1..16 unique integer
step counts in 1..365, sorted in output. Stride is a positive origin-index step
count <=1,000. Bounds are abstract ordinals; they do not discover observations.

For n grid points, origin index j runs from min_points-1+gap_points through
n-1-max(horizons), inclusive, stepping by stride. Training ends at j-gap_points;
it begins at zero for expanding history or max(0,end-max_points+1) for a capped
window. Start/end are inclusive. Gap counts grid points after training end through
origin; gap zero permits the origin observation in training. A target is origin
plus horizon*grid.step. Every emitted fold supports every requested horizon within
the declared grid; no partial-horizon tail fold. Overlapping folds/targets are
allowed and are not independent evaluation samples.

At most 4,096 fold/horizon pairs; excess refuses before output. A valid policy
with no evaluable fold returns REVIEW_REQUIRED and no plan. The example yields
origins 3,4,5, training windows [0,2], [0,3], [1,4], and horizon targets [4,5],
[5,6], [6,7]. No input observation/label availability, chronological split truth,
training execution, model selection, forecast accuracy or actual backtest is
verified. The returned plan needs separate observed-grid/as-of/lineage checks.
The separate public baseline is exercised only in synthetic collection tests;
it is not a runtime dependency or an automatically executed target.

## Shared data, identity and privacy boundaries

All periods, origins, targets, cutoffs and availability times are exact integer
ordinals 0..1,000,000,000. They have no implicit calendar, time zone, clock,
timestamp format or elapsed-time unit. Boolean/numeric coercion is refused.
IDs/series match `[a-z][a-z0-9_-]{0,47}`. Exact supplied cadence/cutoff semantics
remain the caller's responsibility; timing claims are not independently verified.

Resolver/lineage observations are exactly
`{id,series,period,revision,available_at,value,sha256}`. Revision is 1..1,000,000;
available_at>=period. This subset represents observations available at/after
their effective period, not known-future covariates. Value is a bounded decimal
string, absolute value <=10^12 with at most six fractional places. No exponent,
leading plus/whitespace/ambiguous zeros, nonfinite values or float coercion.
Trailing fractional zeros and negative zero normalize without caller decimal-
context rounding. SHA-256 must match canonical normalized payload without the
sha256 field: sorted-key compact ASCII JSON plus one LF (toolkit.encode).
Changing content, identity, timing or revision changes that pin. Input hashes
separately cover exact raw outer JSON. Hashes do not authenticate or anonymize.

Observation snapshot identity is (series,period,revision). ID must identify only
one accepted snapshot globally. Revisions for each series/period, sorted by
revision number, must have strictly increasing declared available_at. Ties or
reversals require review rather than guessed ordering. Future/unused invalid
snapshots also block resolver/lineage output. At most 1,000 observation rows.

For row lists, normalized identical identity snapshots become one accepted record
plus explicit duplicate_rows; conflicting identity groups withhold every member,
including identical repeats inside a conflicting group. Bad row shape/value/pin
is rejected with a fixed code and 1-based logical position. Every list satisfies
input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows.
Cross-reference/timing issues do not reclassify structurally accepted rows.
Row 0 denotes a cohort/policy issue. No silent truncation or latest conflict fix.

The grid checker intentionally retains coverage for valid quality findings, but
withholds it after malformed points. The other tools withhold their entire plan,
resolutions or lineage after any issue. Invalid outer contracts/policies/limits
refuse entirely. A PASS describes the supplied supported scope, never actual
availability, complete history, feature implementation, model quality or publication
approval. Real IDs, periods, gaps, references, counts and hashes can remain private.

## CLI and native file limits

Read one explicit JSON file <=4 MiB. Unknown fields, duplicate keys, JSON floats/
nonfinite values, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and
integers outside +/-10^18 are refused. Reports are escaped ASCII JSON <=8 MiB.
No source-system access, directory discovery, include/URI fetch, environment
expansion, clock, network, process/model launch, training, automatic forecast,
feature-value calculation or target action occurs in these tools.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted, quiescent parents. No hostile filesystem/process sandbox.
Default output is private stdout JSON. Optional --out exclusively creates a new
external report beneath an existing parent outside the source tree; no overwrite
or mkdir. Failed writes can retain partial/unconfirmed output; inspect privately
and select a fresh path. Windows inherits parent ACLs without a confidentiality
guarantee. Shell redirection lacks --out protections. Exit 0 PASS, 1 REVIEW_REQUIRED,
2 fixed refusal, 130 interruption; supplied paths/values are omitted from errors.

Reports omit observation values, but metadata is not anonymized. Keep real inputs
and reports private. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
