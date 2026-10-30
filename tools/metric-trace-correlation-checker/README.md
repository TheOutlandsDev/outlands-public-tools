# OUTLANDS | Metric-to-Trace Correlation Checker

Check explicit metric-point/span references and declared run/time consistency without inferring causation. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/video-game/AI/software declarations; offline and advisory.

From this complete tool directory:

```text
python -B correlations.py --input examples/input.json
python -B correlations.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `correlations.check(raw_json_bytes)`.

## Contract

Input exactly `{format,definitions,series,runs,points,traces,spans,requirements,links}`;
format `outlands-metric-trace-correlations-v1`. The tool independently recomputes the
complete metric-snapshot and trace-structure contracts above. Any source finding,
including missing required metrics, partial trace declarations or logical scalar/bucket
errors, withholds the entire correlation assessment and every scope pin. No supplied
PASS marker/report is accepted as a substitute for source records. Runs are shared
and parsed once. All source bounds/coverage requirements remain in force.

Requirements are `{id,point,point_sha256}` bound to full normalized selected point rows.
The nonempty requirement cohort declares exactly which points need at least one
consistent link. Different requirement IDs for the same point are ambiguous. Links
are `{id,point,point_sha256,span,span_sha256,at}`. Full point/span record hashes must
match selected records; every linked point must be explicitly selected by a requirement.
One identity per (point,span) slot: alias links are ambiguous even at different times.
Different spans may be linked to one point. Links may be empty to expose missing coverage.

For structurally valid sources/references, require the point and selected span's trace
to bind the same exact run. Identical clock labels on different runs do not permit a
link. at must equal the selected point's at and lie in [span.start,span.end), including
start and excluding end. Zero-duration spans confer no correlation window. This is
a narrow point-time model, not aggregation-window exemplar interpretation. No timestamp
conversion, synchronization or fuzzy matching. A malformed/stale reference or unselected
point withholds the whole assessment. Run/time discrepancies are logical findings with
diagnostics/pins retained and no qualified scope.

Report every link's failed_criteria and each requirement's complete consistent_link_ids
and covered flag. One valid link cannot erase an invalid extra link; overall review
remains even if required coverage is present. Pins cover definitions, series, runs,
points, traces, spans, requirements and links. semantic_relationship_verified,
clock_synchronization_verified and causation_inferred are false. A consistent declared
time/reference link does not establish actual observations, causal impact or true latency.

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
