# Metrics and traces methodology

These offline checks describe explicitly supplied records. Start with a selected
run, exact revisions, metric definitions and trace expectations before interpreting
any result. No telemetry is collected and no application is instrumented.

| Term | Plain-language meaning | Exact meaning in these tools |
| --- | --- | --- |
| Metric definition | Rules for a named measurement | Selected kind, opaque unit, label keys, numeric limits and ordered bucket boundaries, bound by revision and normalized hash. |
| Counter | A declared nonnegative scalar | Minimum is exactly zero; this snapshot check does not establish monotonic growth, rates or reset handling. |
| Gauge | A declared scalar at a selected point | Numeric-string value checked against any inclusive minimum/maximum. Missing is never converted to zero. |
| Histogram | Counts in explicitly defined value ranges | Disjoint buckets (-infinity,b0], (b0,b1], ..., (last,+infinity); counts are not cumulative. Their sum must equal count. Empty bounds gives one unbounded bucket. |
| Series | One explicitly selected metric/label combination | Exact metric revision/hash and label keys/values, plus required flag. Unselected label combinations are never inferred. |
| Run and clock basis | The selected execution label and time scale | Exact run ID/revision/hash with inclusive integer bounds. Units, UTC conversion and clock synchronization are caller declarations. |
| Point | One supplied series value for one run | One identity per (series,run), not a time series. Counter/gauge use value; histogram uses count, sum and disjoint bucket counts. |
| Span and trace | A declared operation interval and its graph | Exact trace bindings, optional parent, start/end, one root, no parent cycles, and explicit expected span IDs. Overlap and children outliving parents are permitted. |
| Coverage | Accounting against a selected expectation | Required series/run slots, expected span IDs, or selected points requiring a link. It does not prove real-world collection completeness. |
| Correlation link | A caller-declared point/span association | Full normalized point/span pins, same exact run, link time equal to point time and inside [span.start,span.end). Start is included; end is excluded; a zero-duration span has no link window. |
| Pin and receipt | A reproducible binding and its consistency report | SHA-256 of normalized sorted-key compact escaped ASCII JSON plus LF; cohorts sort by ID. Input hash separately binds exact bytes. Neither is a signature or anonymization. |
| PASS | The selected tool's declaration rules were met | Definition consistency, valid required snapshots, declared trace structure/coverage, or consistent required links. It never establishes causation or actual production health. |
| REVIEW_REQUIRED | Findings need interpretation | CLI exit 1. Structural failures withhold assessments/pins. Logical snapshot/trace findings retain diagnostics/pins; any source finding withholds the correlation assessment. Logical link findings retain diagnostics/pins and withhold qualified scope. |
| Fixed refusal | The requested input cannot be assessed | Malformed outer input or exceeded limits: CLI exit 2; library raises a fixed refusal. No sampled/truncated result substitutes for a complete selected scope. |
| Independent package | One tool can be installed and called alone | A versioned wheel, CLI, embedded fictional demo and check(raw_json_bytes) API. The collection pins all four exact versions. |

## Apply the method

1. Declare metric types, labels and symbolic units, then bind selected series to
   exact definition revisions. Numeric strings normalize trailing fractional zeros
   and negative zero; calculations use exact rational arithmetic.
2. Supply complete selected run snapshots. Check required coverage, limits and
   bucket accounting. A supplied histogram sum is not reconstructed from samples;
   even PASS does not verify its nonempty sum feasibility or actual observations.
3. Declare expected traces/spans and review missing/extra spans and interval
   structure. Do not sum overlapping child durations into an invented elapsed total.
4. Select points that require links. Recompute source contracts before checking
   pinned point/span identity, run and half-open time membership. A valid link
   establishes declared consistency, not causation or semantic relevance.

The [installed exercise](../integrations/metrics-traces/exercise.py) shares one
fictional report-run scope across all four tools. It demonstrates disjoint bucket
accounting, missing metrics, missing spans, a stale pin, inclusive link start and
exclusive link end. The [component guide](../integrations/metrics-traces/components.json)
provides exact APIs, formats, example paths, result fields and limits for people
and AI callers. Source guides retain the full bounded JSON and I/O contracts.

Real IDs, measurements, timing, traces and reports stay private. These tools
echo selected record details; hashes do not make operational data anonymous.
