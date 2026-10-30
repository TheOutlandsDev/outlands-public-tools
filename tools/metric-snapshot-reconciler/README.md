# OUTLANDS | Metric Snapshot Reconciler

Reconcile exact supplied scalar and histogram snapshots with explicit required-series coverage. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/video-game/AI/software declarations; offline and advisory.

From this complete tool directory:

```text
python -B snapshots.py --input examples/input.json
python -B snapshots.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `snapshots.check(raw_json_bytes)`.

## Contract

Input exactly `{format,definitions,series,runs,points}`; format
`outlands-metric-snapshots-v1`. Definitions/series/runs must be nonempty; points may
be empty to expose missing coverage. A point is exactly
`{id,series,series_sha256,run,run_revision,run_sha256,at,value,count,sum,buckets}`.
series_sha256 binds the full normalized selected series row; the run reference binds
its exact revision/full hash. at is an integer 0..10^12 in the declared run clock basis.
One point identity per (series,run): multiple timestamps or alias IDs for the same
slot are structural ambiguity, not latest-value or time-series selection.

Counter/gauge points require a numeric-string value, null count/sum and empty buckets.
Histogram points require null value, integer count 0..10^12, numeric-string sum and
exactly len(definition.bounds)+1 nonnegative integer bucket counts, each <=10^12.
Malformed kind-specific payloads, bad references, alias slots or rejected/conflicting
rows withhold the whole assessment/scope pins. No coercion of numeric types or arrays.

For valid shape, check inclusive run.minimum_at<=at<=run.maximum_at; exact scalar
minimum/maximum limits; histogram sum(buckets)==count; and sum==0 when count==0.
Bucket counts are disjoint, never cumulative. Signed histogram sums are allowed.
The underlying observations, sample membership, nonempty histogram-sum feasibility
and observed distribution are not verified or reconstructed. No rates, reset handling,
interpolation, aggregation across units/labels or inferred values.

Assess every selected series/run pair: valid, invalid, required_missing or optional_absent,
with explicit point_id or null. No missing point becomes zero or healthy. An all-optional
scope can PASS with explicit absence; this does not prove measurements exist. Logical
findings retain source pins/diagnostics with qualified scope null. assessment.points
retains supplied normalized values/count/sum/buckets and failed_criteria. Runs * selected
series <=20,000, otherwise a fixed refusal. definitions_sha256, series_sha256,
runs_sha256 and points_sha256 bind the declared scope. underlying_observations_verified
is false. No real collection, freshness or monitoring coverage is established.

## Shared definitions, records and trust limits

This collection uses custom bounded JSON declarations. Protocol interchange and live
instrumentation compatibility remain unvalidated. All data is caller supplied.

Metric definition exactly
`{id,revision,kind,unit,label_keys,bounds,minimum,maximum}`. kind is counter, gauge or
histogram; unit is an opaque symbolic ID. label_keys has 0..8 distinct IDs, normalized
by sorting. Bounds has 0..16 numeric strings in strictly increasing numeric order.
Counter/gauge require empty bounds. Counter minimum must normalize to "0"; maximum
is null or nonnegative. Gauge minimum/maximum are null or numeric strings, with
minimum<=maximum when both supplied. Histogram minimum/maximum must be null.

Histogram buckets are disjoint intervals (-infinity,b0], (b0,b1], ...,
(last_bound,+infinity). There is always one overflow bucket; empty bounds means one
unbounded bucket. Counts must follow this definition order, not cumulative boundary
totals. Numeric strings have an optional minus, 1..12 integer digits (no extra leading
zero) and optional 1..6 fractional digits. No exponent, plus sign, float or nonfinite
coercion. Normalize trailing fractional zeros and negative zero; use exact rational
arithmetic internally. Sums are declarations, not reconstructed hidden measurements.

Series exactly `{id,metric,metric_revision,metric_sha256,labels,required}`. required
is an exact boolean. labels is a map of <=8 symbolic ID keys to symbolic ID values;
its keys must exactly match the selected metric's label_keys. IDs are labels, never
paths, addresses, regex patterns or code. Metric revisions and full normalized hashes
are exact bindings. No unselected series or label combinations are inferred.

Run exactly `{id,revision,clock,minimum_at,maximum_at}`, with integer bounds 0..10^12,
minimum_at<=maximum_at and a symbolic clock-basis ID. There are no collected timestamps,
implicit units/time zones or synchronized-clock assertions. Point times and span bounds
use their selected run's caller-declared basis. Same run IDs have one selected revision;
conflicting identities are not separate silently chosen snapshots.

All IDs match `[a-z][a-z0-9_-]{0,47}`; revisions are integers 1..1,000,000; SHA-256 values
are 64 lowercase hex. Booleans never substitute for integers. Each identity cohort has
<=1,000 raw rows. Identical normalized ID rows count once; conflicting groups exclude
all members. Accounting retains accepted/duplicate/conflict/rejected-row counts.
Different identities claiming unique series/point/link slots are structural ambiguity.
No latest/best selection, implicit replacement or hidden skipped rows.

Declaration pins hash sorted-key compact escaped ASCII JSON plus LF. Set-like labels/
expected-span IDs normalize by sorting; cohort rows sort by ID. Normalize records
before using their full snapshot hashes. input_sha256 separately hashes exact input
bytes. qualified_scope_sha256 is present only with no findings. Structural ambiguity
withholds complete assessments/scope pins; logical findings retain diagnostics/pins.
Fixed parser/outer-shape/size/scope refusals return errors, not sampled or truncated
results. Pins are consistency receipts, not signatures, authenticity or authority.

No collectors, network/exporters, endpoint probing, instrumentation, log watching,
service discovery, model calls, actual job execution, clock collection or target changes.
telemetry_collected, services_contacted, clocks_read, instrumentation_executed,
artifact_bytes_verified, metrics_emitted, causation_inferred, records_changed and
target_changes_performed are false. PASS establishes limited declared consistency,
not real telemetry, production health, privacy, rights, completeness or causation.
Reports expose supplied IDs, values, counts, times and hashes: keep actual inputs/
reports private. Hashes do not anonymize or encrypt low-entropy declarations. These
tools are not sanitizers, redactors or secret scanners.

One explicit JSON input <=4 MiB. Strict parsing rejects duplicate keys, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and integers outside
+/-10^18. Escaped ASCII output <=8 MiB. Default stdout JSON; --out needs an absolute
fresh external destination under an existing trusted parent outside source. No
overwrite, traversal or mkdir. Ordinary single-link inputs and trusted quiescent storage
required. [Public Windows/POSIX I/O guards](IO-SAFETY.md) preserve POSIX retained parent
descriptors/no-follow checks and native Windows reparse/hardlink/change checks. They
do not sandbox hostile concurrent writers or guarantee inherited parent ACL confidentiality.
Failed writes can leave partial/unconfirmed output: inspect privately and choose a
fresh filename. Shell redirection lacks these output guards. Exit 0 PASS,
1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Errors omit supplied paths/values.

Each complete directory uses Python 3.12/3.13 standard library with no sibling runtime
imports. Only fresh generic logic, fictional HVAC/video-game/AI/software metadata and
reviewed public MIT helpers are included. Original private code, schemas, policies,
real logs/captures, user/customer records, paths, credentials, endpoints and deployment
details were not consulted or selected. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
